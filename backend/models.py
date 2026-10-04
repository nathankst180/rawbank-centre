"""
Pydantic v2 models for Rawbank Sentient Command Centre API responses.
All data is synthetic / academic. Not Rawbank's real internal data.
"""
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator


class KPIs(BaseModel):
    total_transactions: int
    total_value_usd: float
    alert_count: int
    alert_rate: float
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    potential_exposure_usd: float
    open_cases: int
    escalations: int
    distinct_customers: int
    distinct_beneficiaries: int
    distinct_devices: int
    cross_border_transactions: int


class AlertSummary(BaseModel):
    transaction_id: str
    event_timestamp_local: Optional[str]
    customer_id: Optional[str]
    customer_name: Optional[str]
    customer_type: Optional[str]
    customer_segment: Optional[str]
    amount_usd_equiv: Optional[float]
    currency: Optional[str]
    channel: Optional[str]
    alert_score: Optional[int]
    alert_severity: Optional[str]
    alert_primary_pattern: Optional[str]
    alert_reason_codes: Optional[str]
    potential_exposure_usd: Optional[float]
    case_id: Optional[str]
    case_status: Optional[str]
    analyst_queue: Optional[str]
    human_disposition: Optional[str]
    escalation_required_flag: Optional[bool]
    escalation_tier: Optional[str]
    transaction_status: Optional[str]
    is_cross_border: Optional[bool]


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AlertSummary]


class TransactionDetail(BaseModel):
    # Record
    transaction_id: str
    event_timestamp_local: Optional[str]
    batch_id: Optional[str]
    data_quality_flag: Optional[str]
    # Customer
    customer_id: Optional[str]
    customer_name: Optional[str]
    customer_type: Optional[str]
    customer_segment: Optional[str]
    age_band: Optional[str]
    occupation_industry: Optional[str]
    resident_status: Optional[str]
    home_country: Optional[str]
    home_province: Optional[str]
    home_city: Optional[str]
    relationship_tenure_days: Optional[int]
    kyc_risk_band: Optional[str]
    pep_flag: Optional[Any]
    monthly_inflow_usd_equiv: Optional[float]
    # Account
    account_id: Optional[str]
    account_type: Optional[str]
    account_currency: Optional[str]
    account_status: Optional[str]
    product_package: Optional[str]
    card_product: Optional[str]
    card_status: Optional[str]
    illicocash_enabled: Optional[Any]
    rawbank_online_enabled: Optional[Any]
    alert_banking_enabled: Optional[Any]
    available_balance_before_usd: Optional[float]
    available_balance_after_usd: Optional[float]
    # Transaction
    transaction_type: Optional[str]
    direction: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    fx_rate_to_usd: Optional[float]
    amount_usd_equiv: Optional[float]
    channel: Optional[str]
    channel_action: Optional[str]
    payment_rail: Optional[str]
    transaction_status: Optional[str]
    failure_reason: Optional[str]
    is_cross_border: Optional[Any]
    origin_country: Optional[str]
    destination_country: Optional[str]
    destination_city: Optional[str]
    narration: Optional[str]
    recurring_or_scheduled_flag: Optional[Any]
    corporate_payment_flag: Optional[Any]
    # Beneficiary
    beneficiary_id: Optional[str]
    beneficiary_name: Optional[str]
    beneficiary_type: Optional[str]
    beneficiary_relationship: Optional[str]
    beneficiary_age_days: Optional[int]
    beneficiary_prior_txn_count: Optional[int]
    beneficiary_distinct_sender_count_30d: Optional[int]
    merchant_id: Optional[str]
    merchant_name: Optional[str]
    merchant_category: Optional[str]
    card_entry_mode: Optional[str]
    # Location
    touchpoint_id: Optional[str]
    touchpoint_type: Optional[str]
    txn_province: Optional[str]
    txn_city: Optional[str]
    session_id: Optional[str]
    # Device
    device_id: Optional[str]
    device_type: Optional[str]
    device_os: Optional[str]
    device_trusted_flag: Optional[Any]
    device_first_seen_days: Optional[int]
    device_accounts_seen_30d: Optional[int]
    ip_country: Optional[str]
    ip_city: Optional[str]
    ip_risk_score: Optional[int]
    vpn_proxy_flag: Optional[Any]
    # Auth
    login_failures_30m: Optional[int]
    password_reset_hours_ago: Optional[float]
    sim_swap_days_ago: Optional[float]
    auth_method: Optional[str]
    auth_success_flag: Optional[Any]
    approvals_required: Optional[int]
    approvals_completed: Optional[int]
    # Behaviour
    customer_median_txn_usd_90d: Optional[float]
    customer_avg_txn_usd_30d: Optional[float]
    amount_to_median_ratio: Optional[float]
    txn_count_10m: Optional[int]
    txn_count_1h: Optional[int]
    outbound_amount_1h_usd: Optional[float]
    minutes_since_prev_txn: Optional[float]
    previous_txn_city: Optional[str]
    geo_distance_from_home_km: Optional[float]
    impossible_travel_flag: Optional[Any]
    unusual_time_flag: Optional[Any]
    behavioral_deviation_score: Optional[int]
    new_beneficiary_flag: Optional[Any]
    new_device_flag: Optional[Any]
    # Risk
    alert_generated_flag: Optional[Any]
    alert_id: Optional[str]
    alert_score: Optional[int]
    alert_severity: Optional[str]
    alert_primary_pattern: Optional[str]
    alert_reason_codes: Optional[str]
    potential_exposure_usd: Optional[float]
    case_id: Optional[str]
    case_status: Optional[str]
    analyst_queue: Optional[str]
    human_disposition: Optional[str]
    disposition_reason: Optional[str]
    escalation_required_flag: Optional[Any]
    escalation_tier: Optional[str]


class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[dict]


class CustomerSummary(BaseModel):
    customer_id: str
    customer_name: Optional[str]
    customer_type: Optional[str]
    customer_segment: Optional[str]
    kyc_risk_band: Optional[str]
    pep_flag: Optional[Any]
    resident_status: Optional[str]
    home_country: Optional[str]
    home_city: Optional[str]
    monthly_inflow_usd_equiv: Optional[float]
    transaction_count: Optional[int]
    alert_count: Optional[int]
    max_alert_score: Optional[int]
    total_value_usd: Optional[float]


class CustomerListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CustomerSummary]


class BeneficiarySummary(BaseModel):
    beneficiary_id: str
    beneficiary_name: Optional[str]
    beneficiary_type: Optional[str]
    transaction_count: Optional[int]
    distinct_sender_count: Optional[int]
    total_received_usd: Optional[float]
    alert_count: Optional[int]


class BeneficiaryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[BeneficiarySummary]


class DeviceSummary(BaseModel):
    device_id: str
    device_type: Optional[str]
    device_os: Optional[str]
    device_trusted_flag: Optional[Any]
    accounts_seen: Optional[int]
    transaction_count: Optional[int]
    alert_count: Optional[int]
    vpn_proxy_flag: Optional[Any]
    ip_risk_score_max: Optional[int]


class DeviceListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DeviceSummary]


class AnalyticsSeverity(BaseModel):
    severity: str
    count: int


class AnalyticsPattern(BaseModel):
    pattern: str
    count: int
    total_exposure: float


class AnalyticsChannel(BaseModel):
    channel: str
    transaction_count: int
    alert_count: int
    total_value_usd: float


class AnalyticsTrend(BaseModel):
    date: str
    alert_count: int
    transaction_count: int


class AnalyticsGeography(BaseModel):
    province: str
    transaction_count: int
    alert_count: int
    total_value_usd: float


class AnalyticsVelocity(BaseModel):
    customer_id: str
    customer_name: str
    max_txn_count_10m: int
    max_txn_count_1h: int
    alert_count: int


class AnalyticsExposure(BaseModel):
    severity: str
    exposure_usd: float
    alert_count: int


class HealthResponse(BaseModel):
    status: str
    record_count: int
    data_source: str
    disclaimer: str
