"""
Devices route for Rawbank Sentient Command Centre.
"""
from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Query
from database import query, query_one
from models import DeviceListResponse, DeviceSummary

router = APIRouter()
log = logging.getLogger("sentient.api")


@router.get("/devices", response_model=DeviceListResponse)
def get_devices(
    device_type: Optional[str] = Query(None),
    trusted_only: Optional[bool] = Query(None),
    risky_only: bool = Query(False, description="Customer devices used across 3+ accounts (FR-13). ATM/POS terminals are excluded unless include_terminals=true"),
    include_terminals: bool = Query(False),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        clauses = ["device_id IS NOT NULL AND device_id != ''"]
        params = []

        if device_type:
            clauses.append("UPPER(TRIM(device_type)) = UPPER(?)")
            params.append(device_type)
        if trusted_only is not None:
            val = 'TRUE' if trusted_only else 'FALSE'
            clauses.append(f"device_trusted_flag::VARCHAR IN ('{val}', '{val.lower()}')")
        if search:
            like = f"%{search}%"
            clauses.append("device_id ILIKE ?")
            params.append(like)

        where = " AND ".join(clauses)
        having = ""
        if risky_only and not include_terminals:
            clauses.append("UPPER(TRIM(device_type)) NOT IN ('ATM_TERMINAL','POS_TERMINAL')")
            where = " AND ".join(clauses)
        if risky_only:
            having = "HAVING MAX(CAST(device_accounts_seen_30d AS INTEGER)) >= 3"

        offset = (page - 1) * page_size

        count_sql = f"""
            SELECT COUNT(*) AS cnt FROM (
                SELECT device_id FROM kb WHERE {where}
                GROUP BY device_id {having}
            ) sub
        """
        count_row = query_one(count_sql, params)
        total = count_row["cnt"] if count_row else 0

        rows = query(f"""
            SELECT
                device_id,
                ANY_VALUE(device_type)              AS device_type,
                ANY_VALUE(device_os)                AS device_os,
                ANY_VALUE(device_trusted_flag)      AS device_trusted_flag,
                MAX(CAST(device_accounts_seen_30d AS INTEGER)) AS accounts_seen,
                COUNT(*)                             AS transaction_count,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                ANY_VALUE(vpn_proxy_flag)            AS vpn_proxy_flag,
                MAX(CAST(ip_risk_score AS INTEGER))  AS ip_risk_score_max
            FROM kb
            WHERE {where}
            GROUP BY device_id
            {having}
            ORDER BY accounts_seen DESC, alert_count DESC
            LIMIT {page_size} OFFSET {offset}
        """, params)

        items = []
        for r in rows:
            r['device_trusted_flag'] = str(r.get('device_trusted_flag', '')).upper() in ('TRUE', '1')
            r['vpn_proxy_flag'] = str(r.get('vpn_proxy_flag', '')).upper() in ('TRUE', '1')
            items.append(DeviceSummary(**r))

        return DeviceListResponse(total=total, page=page, page_size=page_size, items=items)
    except Exception:
        log.exception("Device query error")
        raise HTTPException(status_code=500, detail="Device query error - see server logs")


@router.get("/devices/{device_id}")
def get_device(device_id: str):
    try:
        row = query_one(f"""
            SELECT
                device_id,
                ANY_VALUE(device_type)              AS device_type,
                ANY_VALUE(device_os)                AS device_os,
                ANY_VALUE(device_trusted_flag)      AS device_trusted_flag,
                ANY_VALUE(device_first_seen_days)   AS device_first_seen_days,
                MAX(CAST(device_accounts_seen_30d AS INTEGER)) AS accounts_seen,
                COUNT(*)                             AS transaction_count,
                COUNT(DISTINCT customer_id)          AS distinct_customers,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                ANY_VALUE(vpn_proxy_flag)            AS vpn_proxy_flag,
                MAX(CAST(ip_risk_score AS INTEGER))  AS ip_risk_score_max,
                ANY_VALUE(ip_country)               AS ip_country,
                ANY_VALUE(ip_city)                  AS ip_city
            FROM kb
            WHERE device_id = ?
            GROUP BY device_id
        """, [device_id])

        if not row:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        row['device_trusted_flag'] = str(row.get('device_trusted_flag', '')).upper() in ('TRUE', '1')
        row['vpn_proxy_flag'] = str(row.get('vpn_proxy_flag', '')).upper() in ('TRUE', '1')

        # Customers who used this device
        customers = query("""
            SELECT DISTINCT customer_id, ANY_VALUE(customer_name) AS customer_name,
                COUNT(*) AS txn_count
            FROM kb WHERE device_id = ?
            GROUP BY customer_id
            ORDER BY txn_count DESC
        """, [device_id])
        row['customers'] = customers

        # Recent transactions
        txns = query(f"""
            SELECT
                transaction_id,
                CAST(event_timestamp_local AS VARCHAR) AS event_timestamp_local,
                customer_id, customer_name,
                CAST(amount_usd_equiv AS DOUBLE) AS amount_usd_equiv,
                currency, channel, transaction_status,
                alert_generated_flag::VARCHAR IN ('TRUE','true','1') AS alert_generated_flag,
                CAST(alert_score AS INTEGER) AS alert_score
            FROM kb WHERE device_id = ?
            ORDER BY event_timestamp_local DESC LIMIT 20
        """, [device_id])
        row['recent_transactions'] = txns

        return row
    except HTTPException:
        raise
    except Exception:
        log.exception("Device detail error")
        raise HTTPException(status_code=500, detail="Device detail error - see server logs")
