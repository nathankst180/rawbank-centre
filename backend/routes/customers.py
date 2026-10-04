"""
Customers route for Rawbank Sentient Command Centre.
"""
from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Query
from database import query, query_one
from models import CustomerListResponse, CustomerSummary

router = APIRouter()
log = logging.getLogger("sentient.api")


@router.get("/customers", response_model=CustomerListResponse)
def get_customers(
    customer_type: Optional[str] = Query(None),
    kyc_risk_band: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    alerts_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        clauses = ["1=1"]
        params = []

        if customer_type:
            clauses.append("UPPER(TRIM(customer_type)) = UPPER(?)")
            params.append(customer_type)
        if kyc_risk_band:
            clauses.append("UPPER(TRIM(kyc_risk_band)) = UPPER(?)")
            params.append(kyc_risk_band)
        if segment:
            clauses.append("UPPER(TRIM(customer_segment)) = UPPER(?)")
            params.append(segment)
        if search:
            like = f"%{search}%"
            clauses.append("(customer_id ILIKE ? OR customer_name ILIKE ?)")
            params.extend([like, like])

        where = " AND ".join(clauses)
        having = ""
        if alerts_only:
            having = "HAVING COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) > 0"

        offset = (page - 1) * page_size

        count_sql = f"""
            SELECT COUNT(*) AS cnt FROM (
                SELECT customer_id FROM kb
                WHERE {where}
                GROUP BY customer_id
                {having}
            ) sub
        """
        count_row = query_one(count_sql, params)
        total = count_row["cnt"] if count_row else 0

        rows = query(f"""
            SELECT
                customer_id,
                ANY_VALUE(customer_name)              AS customer_name,
                ANY_VALUE(customer_type)              AS customer_type,
                ANY_VALUE(customer_segment)           AS customer_segment,
                ANY_VALUE(kyc_risk_band)              AS kyc_risk_band,
                ANY_VALUE(pep_flag)                   AS pep_flag,
                ANY_VALUE(resident_status)            AS resident_status,
                ANY_VALUE(home_country)               AS home_country,
                ANY_VALUE(home_city)                  AS home_city,
                CAST(ANY_VALUE(monthly_inflow_usd_equiv) AS DOUBLE) AS monthly_inflow_usd_equiv,
                COUNT(*)                              AS transaction_count,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                MAX(CAST(alert_score AS INTEGER))     AS max_alert_score,
                SUM(CAST(amount_usd_equiv AS DOUBLE)) AS total_value_usd
            FROM kb
            WHERE {where}
            GROUP BY customer_id
            {having}
            ORDER BY alert_count DESC, max_alert_score DESC
            LIMIT {page_size} OFFSET {offset}
        """, params)

        items = []
        for r in rows:
            r['pep_flag'] = str(r.get('pep_flag', '')).upper() in ('TRUE', '1')
            items.append(CustomerSummary(**r))

        return CustomerListResponse(total=total, page=page, page_size=page_size, items=items)
    except Exception:
        log.exception("Customer query error")
        raise HTTPException(status_code=500, detail="Customer query error - see server logs")


@router.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    try:
        row = query_one(f"""
            SELECT
                customer_id,
                ANY_VALUE(customer_name)              AS customer_name,
                ANY_VALUE(customer_type)              AS customer_type,
                ANY_VALUE(customer_segment)           AS customer_segment,
                ANY_VALUE(age_band)                   AS age_band,
                ANY_VALUE(occupation_industry)        AS occupation_industry,
                ANY_VALUE(resident_status)            AS resident_status,
                ANY_VALUE(home_country)               AS home_country,
                ANY_VALUE(home_province)              AS home_province,
                ANY_VALUE(home_city)                  AS home_city,
                ANY_VALUE(relationship_tenure_days)   AS relationship_tenure_days,
                ANY_VALUE(kyc_risk_band)              AS kyc_risk_band,
                ANY_VALUE(pep_flag)                   AS pep_flag,
                CAST(ANY_VALUE(monthly_inflow_usd_equiv) AS DOUBLE) AS monthly_inflow_usd_equiv,
                ANY_VALUE(account_id)                 AS account_id,
                ANY_VALUE(account_type)               AS account_type,
                ANY_VALUE(account_currency)           AS account_currency,
                ANY_VALUE(product_package)            AS product_package,
                ANY_VALUE(card_product)               AS card_product,
                ANY_VALUE(illicocash_enabled)         AS illicocash_enabled,
                ANY_VALUE(rawbank_online_enabled)     AS rawbank_online_enabled,
                COUNT(*)                              AS transaction_count,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                MAX(CAST(alert_score AS INTEGER))     AS max_alert_score,
                SUM(CAST(amount_usd_equiv AS DOUBLE)) AS total_value_usd,
                COUNT(DISTINCT device_id)             AS distinct_devices,
                COUNT(DISTINCT CASE WHEN beneficiary_id IS NOT NULL AND beneficiary_id != '' THEN beneficiary_id END) AS distinct_beneficiaries,
                SUM(CASE WHEN is_cross_border::VARCHAR IN ('TRUE','true','1') THEN 1 ELSE 0 END) AS cross_border_count,
                CAST(AVG(CAST(customer_median_txn_usd_90d AS DOUBLE)) AS DOUBLE) AS avg_median_txn
            FROM kb
            WHERE customer_id = ?
            GROUP BY customer_id
        """, [customer_id])

        if not row:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

        row['pep_flag'] = str(row.get('pep_flag', '')).upper() in ('TRUE', '1')
        row['illicocash_enabled'] = str(row.get('illicocash_enabled', '')).upper() in ('TRUE', '1')
        row['rawbank_online_enabled'] = str(row.get('rawbank_online_enabled', '')).upper() in ('TRUE', '1')
        return row
    except HTTPException:
        raise
    except Exception:
        log.exception("Customer detail error")
        raise HTTPException(status_code=500, detail="Customer detail error - see server logs")


@router.get("/customers/{customer_id}/transactions")
def get_customer_transactions(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        offset = (page - 1) * page_size
        count_row = query_one(
            "SELECT COUNT(*) AS cnt FROM kb WHERE customer_id = ?",
            [customer_id]
        )
        total = count_row["cnt"] if count_row else 0

        rows = query(f"""
            SELECT
                transaction_id,
                CAST(event_timestamp_local AS VARCHAR) AS event_timestamp_local,
                direction,
                CAST(amount AS DOUBLE) AS amount,
                currency,
                CAST(amount_usd_equiv AS DOUBLE) AS amount_usd_equiv,
                channel, transaction_status,
                alert_generated_flag::VARCHAR IN ('TRUE','true','1') AS alert_generated_flag,
                CAST(alert_score AS INTEGER) AS alert_score,
                alert_severity, alert_primary_pattern,
                beneficiary_name, narration
            FROM kb
            WHERE customer_id = ?
            ORDER BY event_timestamp_local DESC
            LIMIT {page_size} OFFSET {offset}
        """, [customer_id])

        return {"customer_id": customer_id, "total": total, "page": page, "page_size": page_size, "items": rows}
    except Exception:
        log.exception("Customer transactions error")
        raise HTTPException(status_code=500, detail="Customer transactions error - see server logs")
