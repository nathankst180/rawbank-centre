"""
Beneficiaries route for Rawbank Sentient Command Centre.
"""
from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Query
from database import query, query_one
from models import BeneficiaryListResponse, BeneficiarySummary

router = APIRouter()
log = logging.getLogger("sentient.api")


@router.get("/beneficiaries", response_model=BeneficiaryListResponse)
def get_beneficiaries(
    beneficiary_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    high_risk_only: bool = Query(False, description="Individual beneficiaries receiving from 5+ customers (FR-14). Merchants excluded unless include_merchants=true"),
    include_merchants: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        clauses = ["beneficiary_id IS NOT NULL AND beneficiary_id != '' AND beneficiary_id != 'NONE'"]
        params = []

        if beneficiary_type:
            clauses.append("UPPER(TRIM(beneficiary_type)) = UPPER(?)")
            params.append(beneficiary_type)
        if search:
            like = f"%{search}%"
            clauses.append("(beneficiary_id ILIKE ? OR beneficiary_name ILIKE ?)")
            params.extend([like, like])

        where = " AND ".join(clauses)
        having = ""
        if high_risk_only and not include_merchants:
            clauses.append("UPPER(TRIM(beneficiary_type)) <> 'MERCHANT'")
            where = " AND ".join(clauses)
        if high_risk_only:
            having = "HAVING MAX(CAST(beneficiary_distinct_sender_count_30d AS INTEGER)) >= 5"

        offset = (page - 1) * page_size

        count_sql = f"""
            SELECT COUNT(*) AS cnt FROM (
                SELECT beneficiary_id FROM kb WHERE {where}
                GROUP BY beneficiary_id {having}
            ) sub
        """
        count_row = query_one(count_sql, params)
        total = count_row["cnt"] if count_row else 0

        rows = query(f"""
            SELECT
                beneficiary_id,
                ANY_VALUE(beneficiary_name)          AS beneficiary_name,
                ANY_VALUE(beneficiary_type)          AS beneficiary_type,
                COUNT(*)                             AS transaction_count,
                MAX(CAST(beneficiary_distinct_sender_count_30d AS INTEGER)) AS distinct_sender_count,
                SUM(CAST(amount_usd_equiv AS DOUBLE)) AS total_received_usd,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count
            FROM kb
            WHERE {where}
            GROUP BY beneficiary_id
            {having}
            ORDER BY distinct_sender_count DESC, alert_count DESC
            LIMIT {page_size} OFFSET {offset}
        """, params)

        items = [BeneficiarySummary(**r) for r in rows]
        return BeneficiaryListResponse(total=total, page=page, page_size=page_size, items=items)
    except Exception:
        log.exception("Beneficiary query error")
        raise HTTPException(status_code=500, detail="Beneficiary query error - see server logs")


@router.get("/beneficiaries/{beneficiary_id}")
def get_beneficiary(beneficiary_id: str):
    try:
        row = query_one(f"""
            SELECT
                beneficiary_id,
                ANY_VALUE(beneficiary_name)          AS beneficiary_name,
                ANY_VALUE(beneficiary_type)          AS beneficiary_type,
                ANY_VALUE(beneficiary_relationship)  AS beneficiary_relationship,
                COUNT(*)                             AS transaction_count,
                COUNT(DISTINCT customer_id)          AS distinct_senders,
                MAX(CAST(beneficiary_distinct_sender_count_30d AS INTEGER)) AS distinct_sender_count_30d,
                SUM(CAST(amount_usd_equiv AS DOUBLE)) AS total_received_usd,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                MAX(CAST(alert_score AS INTEGER))    AS max_alert_score
            FROM kb
            WHERE beneficiary_id = ?
            GROUP BY beneficiary_id
        """, [beneficiary_id])

        if not row:
            raise HTTPException(status_code=404, detail=f"Beneficiary {beneficiary_id} not found")

        # Recent transactions for this beneficiary
        txns = query(f"""
            SELECT
                transaction_id,
                CAST(event_timestamp_local AS VARCHAR) AS event_timestamp_local,
                customer_id, customer_name,
                CAST(amount_usd_equiv AS DOUBLE) AS amount_usd_equiv,
                currency, channel, transaction_status,
                alert_generated_flag::VARCHAR IN ('TRUE','true','1') AS alert_generated_flag,
                CAST(alert_score AS INTEGER) AS alert_score
            FROM kb
            WHERE beneficiary_id = ?
            ORDER BY event_timestamp_local DESC
            LIMIT 20
        """, [beneficiary_id])

        row['recent_transactions'] = txns
        return row
    except HTTPException:
        raise
    except Exception:
        log.exception("Beneficiary detail error")
        raise HTTPException(status_code=500, detail="Beneficiary detail error - see server logs")
