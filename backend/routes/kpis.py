"""
KPI route for Rawbank Sentient Command Centre.
Calculates all dashboard KPIs from RAWBANK_SENTIENT_KB.csv via DuckDB.
"""
import logging
from fastapi import APIRouter, HTTPException
from database import query_one
from models import KPIs

router = APIRouter()
log = logging.getLogger("sentient.api")


@router.get("/kpis", response_model=KPIs)
def get_kpis():
    try:
        row = query_one("""
            SELECT
                COUNT(*)                                                            AS total_transactions,
                COALESCE(SUM(CAST(amount_usd_equiv AS DOUBLE)), 0)                 AS total_value_usd,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END)  AS alert_count,
                ROUND(
                    COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) * 100.0
                    / NULLIF(COUNT(*), 0), 2
                )                                                                   AS alert_rate,
                COUNT(CASE WHEN UPPER(TRIM(alert_severity)) = 'CRITICAL' THEN 1 END) AS critical_alerts,
                COUNT(CASE WHEN UPPER(TRIM(alert_severity)) = 'HIGH'     THEN 1 END) AS high_alerts,
                COUNT(CASE WHEN UPPER(TRIM(alert_severity)) = 'MEDIUM'   THEN 1 END) AS medium_alerts,
                COUNT(CASE WHEN UPPER(TRIM(alert_severity)) = 'LOW'      THEN 1 END) AS low_alerts,
                COALESCE(SUM(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1')
                    THEN CAST(potential_exposure_usd AS DOUBLE) ELSE 0 END), 0)     AS potential_exposure_usd,
                COUNT(DISTINCT CASE WHEN UPPER(TRIM(case_status)) IN ('NEW','IN_REVIEW','ESCALATED')
                    THEN case_id END)                                               AS open_cases,
                COUNT(CASE WHEN escalation_required_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS escalations,
                COUNT(DISTINCT customer_id)                                         AS distinct_customers,
                COUNT(DISTINCT CASE WHEN beneficiary_id IS NOT NULL AND beneficiary_id != ''
                    THEN beneficiary_id END)                                        AS distinct_beneficiaries,
                COUNT(DISTINCT device_id)                                           AS distinct_devices,
                COUNT(CASE WHEN is_cross_border::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS cross_border_transactions
            FROM kb
        """)
        if not row:
            raise HTTPException(status_code=500, detail="Failed to compute KPIs: query returned empty")
        return KPIs(**row)
    except HTTPException:
        raise
    except Exception:
        log.exception("KPI computation error")
        raise HTTPException(status_code=500, detail="KPI computation error - see server logs")

