"""
Transactions route for Rawbank Sentient Command Centre.
"""
from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Query
from database import query, query_one
from models import TransactionDetail, TransactionListResponse

router = APIRouter()
log = logging.getLogger("sentient.api")


def _row_to_detail(row: dict) -> TransactionDetail:
    """Convert a raw DB row to TransactionDetail, coercing types."""
    def _bool(v):
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        return str(v).strip().upper() in ('TRUE', '1', 'YES')

    bool_fields = [
        'pep_flag', 'illicocash_enabled', 'rawbank_online_enabled', 'alert_banking_enabled',
        'is_cross_border', 'recurring_or_scheduled_flag', 'corporate_payment_flag',
        'device_trusted_flag', 'vpn_proxy_flag', 'auth_success_flag',
        'impossible_travel_flag', 'unusual_time_flag',
        'new_beneficiary_flag', 'new_device_flag', 'alert_generated_flag',
        'escalation_required_flag'
    ]
    for f in bool_fields:
        if f in row:
            row[f] = _bool(row[f])

    int_fields = [
        'relationship_tenure_days', 'beneficiary_age_days', 'beneficiary_prior_txn_count',
        'beneficiary_distinct_sender_count_30d', 'device_first_seen_days',
        'device_accounts_seen_30d', 'ip_risk_score', 'login_failures_30m',
        'approvals_required', 'approvals_completed', 'txn_count_10m', 'txn_count_1h',
        'behavioral_deviation_score', 'alert_score'
    ]
    for f in int_fields:
        if f in row and row[f] is not None:
            try:
                row[f] = int(float(str(row[f])))
            except (ValueError, TypeError):
                row[f] = None

    float_fields = [
        'monthly_inflow_usd_equiv', 'available_balance_before_usd', 'available_balance_after_usd',
        'amount', 'fx_rate_to_usd', 'amount_usd_equiv', 'customer_median_txn_usd_90d',
        'customer_avg_txn_usd_30d', 'amount_to_median_ratio', 'outbound_amount_1h_usd',
        'minutes_since_prev_txn', 'geo_distance_from_home_km', 'potential_exposure_usd',
        'password_reset_hours_ago', 'sim_swap_days_ago'
    ]
    for f in float_fields:
        if f in row and row[f] is not None:
            try:
                row[f] = float(str(row[f]))
            except (ValueError, TypeError):
                row[f] = None

    # Empty string -> None for optional string fields
    for k, v in row.items():
        if isinstance(v, str) and v.strip() in ('', 'NONE', 'None'):
            row[k] = None

    return TransactionDetail(**row)


@router.get("/transactions", response_model=TransactionListResponse)
def get_transactions(
    customer_id: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    transaction_status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    alerts_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        clauses = ["1=1"]
        params = []

        if customer_id:
            clauses.append("customer_id = ?")
            params.append(customer_id)
        if channel:
            clauses.append("UPPER(TRIM(channel)) = UPPER(?)")
            params.append(channel.upper())
        if transaction_status:
            clauses.append("UPPER(TRIM(transaction_status)) = UPPER(?)")
            params.append(transaction_status.upper())
        if date_from:
            clauses.append("CAST(event_timestamp_local AS VARCHAR) >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("CAST(event_timestamp_local AS VARCHAR) <= ?")
            params.append(date_to + "T23:59:59")
        if alerts_only:
            clauses.append("alert_generated_flag::VARCHAR IN ('TRUE','true','1')")
        if search:
            clauses.append(
                "(transaction_id ILIKE ? OR customer_name ILIKE ? OR narration ILIKE ?)"
            )
            like = f"%{search}%"
            params.extend([like, like, like])

        where = " AND ".join(clauses)
        offset = (page - 1) * page_size

        count_row = query_one(f"SELECT COUNT(*) AS cnt FROM kb WHERE {where}", params)
        total = count_row["cnt"] if count_row else 0

        rows = query(f"""
            SELECT
                transaction_id,
                CAST(event_timestamp_local AS VARCHAR) AS event_timestamp_local,
                customer_id, customer_name, customer_type, customer_segment,
                direction,
                CAST(amount AS DOUBLE) AS amount,
                currency,
                CAST(amount_usd_equiv AS DOUBLE) AS amount_usd_equiv,
                channel, channel_action, transaction_status,
                alert_generated_flag::VARCHAR IN ('TRUE','true','1') AS alert_generated_flag,
                CAST(alert_score AS INTEGER) AS alert_score,
                alert_severity, alert_primary_pattern,
                is_cross_border::VARCHAR IN ('TRUE','true','1') AS is_cross_border,
                txn_city, txn_province,
                narration,
                beneficiary_name
            FROM kb
            WHERE {where}
            ORDER BY event_timestamp_local DESC
            LIMIT {page_size} OFFSET {offset}
        """, params)

        return TransactionListResponse(total=total, page=page, page_size=page_size, items=rows)
    except Exception:
        log.exception("Transaction query error")
        raise HTTPException(status_code=500, detail="Transaction query error - see server logs")


@router.get("/transactions/{transaction_id}", response_model=TransactionDetail)
def get_transaction(transaction_id: str):
    try:
        row = query_one(
            "SELECT * FROM kb WHERE transaction_id = ?",
            [transaction_id]
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        # Cast timestamp to string
        if 'event_timestamp_local' in row and row['event_timestamp_local'] is not None:
            row['event_timestamp_local'] = str(row['event_timestamp_local'])
        return _row_to_detail(row)
    except HTTPException:
        raise
    except Exception:
        log.exception("Transaction detail error")
        raise HTTPException(status_code=500, detail="Transaction detail error - see server logs")


@router.get("/transactions/{transaction_id}/related")
def get_related_transactions(transaction_id: str):
    """Related activity. Each row carries *every* relationship it shares with the
    anchor (customer, device, beneficiary, merchant, session) as a list, so a
    same-customer row that is also same-device is not hidden."""
    try:
        anchor = query_one("SELECT * FROM kb WHERE transaction_id = ?", [transaction_id])
        if not anchor:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

        def _key(v):
            v = None if v is None else str(v).strip()
            return None if v in (None, "", "NONE", "None") else v

        cust = _key(anchor.get("customer_id"))
        dev = _key(anchor.get("device_id"))
        ben = _key(anchor.get("beneficiary_id"))
        mer = _key(anchor.get("merchant_id"))
        ses = _key(anchor.get("session_id"))

        rows = query("""
            SELECT * FROM (
                SELECT
                    transaction_id,
                    CAST(event_timestamp_local AS VARCHAR) AS event_timestamp_local,
                    customer_id, customer_name,
                    direction,
                    CAST(amount_usd_equiv AS DOUBLE) AS amount_usd_equiv,
                    currency, channel, transaction_status,
                    alert_generated_flag::VARCHAR IN ('TRUE','true','1') AS alert_generated_flag,
                    CAST(alert_score AS INTEGER) AS alert_score,
                    alert_severity,
                    COALESCE(customer_id = ?, FALSE) AS same_customer,
                    COALESCE(device_id = ?, FALSE) AS same_device,
                    COALESCE(beneficiary_id = ?, FALSE) AS same_beneficiary,
                    COALESCE(merchant_id = ?, FALSE) AS same_merchant,
                    COALESCE(session_id = ?, FALSE) AS same_session
                FROM kb
                WHERE transaction_id != ?
            ) t
            WHERE same_customer OR same_device OR same_beneficiary OR same_merchant OR same_session
            ORDER BY (same_device::INT + same_beneficiary::INT + same_merchant::INT + same_session::INT) DESC,
                     alert_generated_flag DESC, event_timestamp_local DESC
            LIMIT 100
        """, [cust, dev, ben, mer, ses, transaction_id])

        names = [("same_customer", "SAME_CUSTOMER"), ("same_device", "SAME_DEVICE"),
                 ("same_beneficiary", "SAME_BENEFICIARY"), ("same_merchant", "SAME_MERCHANT"),
                 ("same_session", "SAME_SESSION")]
        for r in rows:
            r["relationships"] = [lbl for col, lbl in names if r.pop(col)]
            r["relationship"] = " + ".join(r["relationships"])

        counts = {lbl: sum(1 for r in rows if lbl in r["relationships"]) for _, lbl in names}
        return {"transaction_id": transaction_id, "counts": counts, "truncated": len(rows) >= 100, "related": rows}
    except HTTPException:
        raise
    except Exception:
        log.exception("related transactions failed")
        raise HTTPException(status_code=500, detail="Related-activity lookup failed")
