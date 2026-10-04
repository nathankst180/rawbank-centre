"""
Analytics routes for Rawbank Sentient Command Centre.
All visualisation data endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException
from database import query
from models import (
    AnalyticsSeverity, AnalyticsPattern, AnalyticsChannel,
    AnalyticsTrend, AnalyticsGeography, AnalyticsVelocity, AnalyticsExposure
)
from typing import List

router = APIRouter()
log = logging.getLogger("sentient.api")


@router.get("/analytics/alerts-by-severity", response_model=List[AnalyticsSeverity])
def alerts_by_severity():
    try:
        rows = query("""
            SELECT
                COALESCE(NULLIF(TRIM(alert_severity), ''), 'NONE') AS severity,
                COUNT(*) AS count
            FROM kb
            WHERE alert_generated_flag::VARCHAR IN ('TRUE','true','1')
            GROUP BY alert_severity
            ORDER BY
                CASE alert_severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END
        """)
        return [AnalyticsSeverity(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/alerts-by-pattern", response_model=List[AnalyticsPattern])
def alerts_by_pattern():
    try:
        rows = query("""
            SELECT
                COALESCE(NULLIF(TRIM(alert_primary_pattern), ''), 'OTHER') AS pattern,
                COUNT(*) AS count,
                COALESCE(SUM(CAST(potential_exposure_usd AS DOUBLE)), 0) AS total_exposure
            FROM kb
            WHERE alert_generated_flag::VARCHAR IN ('TRUE','true','1')
              AND alert_primary_pattern IS NOT NULL
              AND TRIM(alert_primary_pattern) NOT IN ('NONE', '')
            GROUP BY alert_primary_pattern
            ORDER BY count DESC
        """)
        return [AnalyticsPattern(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/alerts-by-channel", response_model=List[AnalyticsChannel])
def alerts_by_channel():
    try:
        rows = query("""
            SELECT
                channel,
                COUNT(*) AS transaction_count,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                COALESCE(SUM(CAST(amount_usd_equiv AS DOUBLE)), 0) AS total_value_usd
            FROM kb
            GROUP BY channel
            ORDER BY alert_count DESC
        """)
        return [AnalyticsChannel(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/alert-trend", response_model=List[AnalyticsTrend])
def alert_trend():
    try:
        rows = query("""
            SELECT
                CAST(DATE_TRUNC('day', CAST(event_timestamp_local AS TIMESTAMP)) AS VARCHAR) AS date,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                COUNT(*) AS transaction_count
            FROM kb
            GROUP BY DATE_TRUNC('day', CAST(event_timestamp_local AS TIMESTAMP))
            ORDER BY date ASC
        """)
        return [AnalyticsTrend(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/geography", response_model=List[AnalyticsGeography])
def geography():
    try:
        rows = query("""
            SELECT
                COALESCE(NULLIF(TRIM(txn_province), ''), 'UNKNOWN') AS province,
                COUNT(*) AS transaction_count,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                COALESCE(SUM(CAST(amount_usd_equiv AS DOUBLE)), 0) AS total_value_usd
            FROM kb
            WHERE txn_province IS NOT NULL AND TRIM(txn_province) NOT IN ('', 'NONE', 'FOREIGN')
            GROUP BY txn_province
            ORDER BY alert_count DESC
        """)
        return [AnalyticsGeography(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/velocity", response_model=List[AnalyticsVelocity])
def velocity():
    try:
        rows = query("""
            SELECT
                customer_id,
                ANY_VALUE(customer_name) AS customer_name,
                MAX(CAST(txn_count_10m AS INTEGER)) AS max_txn_count_10m,
                MAX(CAST(txn_count_1h AS INTEGER)) AS max_txn_count_1h,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count
            FROM kb
            GROUP BY customer_id
            HAVING MAX(CAST(txn_count_10m AS INTEGER)) >= 3
                OR MAX(CAST(txn_count_1h AS INTEGER)) >= 5
            ORDER BY max_txn_count_10m DESC, max_txn_count_1h DESC
            LIMIT 30
        """)
        return [AnalyticsVelocity(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/exposure", response_model=List[AnalyticsExposure])
def exposure():
    try:
        rows = query("""
            SELECT
                COALESCE(NULLIF(TRIM(alert_severity), ''), 'NONE') AS severity,
                COALESCE(SUM(CAST(potential_exposure_usd AS DOUBLE)), 0) AS exposure_usd,
                COUNT(*) AS alert_count
            FROM kb
            WHERE alert_generated_flag::VARCHAR IN ('TRUE','true','1')
            GROUP BY alert_severity
            ORDER BY
                CASE alert_severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END
        """)
        return [AnalyticsExposure(**r) for r in rows]
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/top-risk-customers")
def top_risk_customers():
    try:
        rows = query("""
            SELECT
                customer_id,
                ANY_VALUE(customer_name) AS customer_name,
                ANY_VALUE(customer_segment) AS customer_segment,
                ANY_VALUE(kyc_risk_band) AS kyc_risk_band,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                MAX(CAST(alert_score AS INTEGER)) AS max_alert_score,
                COALESCE(SUM(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1')
                    THEN CAST(potential_exposure_usd AS DOUBLE) ELSE 0 END), 0) AS total_exposure_usd
            FROM kb
            GROUP BY customer_id
            HAVING COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) > 0
            ORDER BY max_alert_score DESC, alert_count DESC
            LIMIT 10
        """)
        return rows
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")


@router.get("/analytics/cross-border")
def cross_border():
    try:
        rows = query("""
            SELECT
                origin_country,
                destination_country,
                COUNT(*) AS transaction_count,
                COUNT(CASE WHEN alert_generated_flag::VARCHAR IN ('TRUE','true','1') THEN 1 END) AS alert_count,
                COALESCE(SUM(CAST(amount_usd_equiv AS DOUBLE)), 0) AS total_value_usd
            FROM kb
            WHERE is_cross_border::VARCHAR IN ('TRUE','true','1')
            GROUP BY origin_country, destination_country
            ORDER BY alert_count DESC, transaction_count DESC
            LIMIT 20
        """)
        return rows
    except Exception:
        log.exception("analytics query failed")
        raise HTTPException(status_code=500, detail="Analytics query failed - see server logs")
