"""
Alerts route for Rawbank Sentient Command Centre.
Serves filtered/paginated alert queue from RAWBANK_SENTIENT_KB.csv.
"""
from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Query
from database import query, query_one
from models import AlertListResponse, AlertSummary, TransactionDetail

router = APIRouter()
log = logging.getLogger("sentient.api")


def _build_alert_where(
    severity: Optional[str],
    pattern: Optional[str],
    channel: Optional[str],
    customer_id: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    score_min: Optional[int],
    score_max: Optional[int],
    case_status: Optional[str],
    analyst_queue: Optional[str],
    escalation: Optional[bool],
    search: Optional[str],
) -> tuple[str, list]:
    clauses = ["alert_generated_flag::VARCHAR IN ('TRUE','true','1')"]
    params = []

    if severity:
        clauses.append("UPPER(TRIM(alert_severity)) = UPPER(?)")
        params.append(severity.upper())
    if pattern:
        clauses.append("UPPER(TRIM(alert_primary_pattern)) = UPPER(?)")
        params.append(pattern.upper())
    if channel:
        clauses.append("UPPER(TRIM(channel)) = UPPER(?)")
        params.append(channel.upper())
    if customer_id:
        clauses.append("customer_id = ?")
        params.append(customer_id)
    if date_from:
        clauses.append("CAST(event_timestamp_local AS VARCHAR) >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("CAST(event_timestamp_local AS VARCHAR) <= ?")
        params.append(date_to + "T23:59:59")
    if score_min is not None:
        clauses.append("CAST(alert_score AS INTEGER) >= ?")
        params.append(score_min)
    if score_max is not None:
        clauses.append("CAST(alert_score AS INTEGER) <= ?")
        params.append(score_max)
    if case_status:
        clauses.append("UPPER(TRIM(case_status)) = UPPER(?)")
        params.append(case_status.upper())
    if analyst_queue:
        clauses.append("UPPER(TRIM(analyst_queue)) = UPPER(?)")
        params.append(analyst_queue.upper())
    if escalation is not None:
        val = 'TRUE' if escalation else 'FALSE'
        clauses.append(f"escalation_required_flag::VARCHAR IN ('{val}', '{val.lower()}')")
    if search:
        clauses.append(
            "(transaction_id ILIKE ? OR customer_name ILIKE ? OR customer_id ILIKE ? OR beneficiary_name ILIKE ?)"
        )
        like = f"%{search}%"
        params.extend([like, like, like, like])

    where = " AND ".join(clauses)
    return where, params


@router.get("/alerts", response_model=AlertListResponse)
def get_alerts(
    severity: Optional[str] = Query(None),
    pattern: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    score_min: Optional[int] = Query(None),
    score_max: Optional[int] = Query(None),
    case_status: Optional[str] = Query(None),
    analyst_queue: Optional[str] = Query(None),
    escalation: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    try:
        where, params = _build_alert_where(
            severity, pattern, channel, customer_id,
            date_from, date_to, score_min, score_max,
            case_status, analyst_queue, escalation, search
        )
        offset = (page - 1) * page_size

        count_row = query_one(f"SELECT COUNT(*) AS cnt FROM kb WHERE {where}", params)
        total = count_row["cnt"] if count_row else 0

        rows = query(f"""
            SELECT
                transaction_id,
                CAST(event_timestamp_local AS VARCHAR) AS event_timestamp_local,
                customer_id,
                customer_name,
                customer_type,
                customer_segment,
                CAST(amount_usd_equiv AS DOUBLE) AS amount_usd_equiv,
                currency,
                channel,
                CAST(alert_score AS INTEGER) AS alert_score,
                alert_severity,
                alert_primary_pattern,
                alert_reason_codes,
                CAST(potential_exposure_usd AS DOUBLE) AS potential_exposure_usd,
                case_id,
                case_status,
                analyst_queue,
                human_disposition,
                escalation_required_flag::VARCHAR IN ('TRUE','true','1') AS escalation_required_flag,
                escalation_tier,
                transaction_status,
                is_cross_border::VARCHAR IN ('TRUE','true','1') AS is_cross_border
            FROM kb
            WHERE {where}
            ORDER BY CAST(alert_score AS INTEGER) DESC, event_timestamp_local DESC
            LIMIT {page_size} OFFSET {offset}
        """, params)

        items = [AlertSummary(**r) for r in rows]
        return AlertListResponse(total=total, page=page, page_size=page_size, items=items)
    except Exception:
        log.exception("Alert query error")
        raise HTTPException(status_code=500, detail="Alert query error - see server logs")


@router.get("/alerts/{transaction_id}", response_model=TransactionDetail)
def get_alert_detail(transaction_id: str):
    """Returns full transaction detail for an alert."""
    from routes.transactions import get_transaction
    return get_transaction(transaction_id)
