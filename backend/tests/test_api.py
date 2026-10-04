"""API vs CSV consistency + scenario tests. Run: cd backend && pytest -q
Every expected value is recomputed independently with pandas from the canonical CSV."""
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import app  # noqa: E402

CSV = Path(__file__).resolve().parents[1] / "data" / "RAWBANK_SENTIENT_KB.csv"
df = pd.read_csv(CSV, keep_default_na=False)
df["_alert"] = df.alert_generated_flag.astype(str).str.upper() == "TRUE"
alerts = df[df._alert]
client = TestClient(app)


def get(path, **params):
    return client.get("/api" + path, params=params)


def test_ground_truth_not_loaded():
    assert not any("ground" in c.lower() for c in df.columns)
    assert not list(CSV.parent.glob("*GROUND_TRUTH*"))


def test_kpis_match_csv():
    k = get("/kpis").json()
    assert k["total_transactions"] == len(df)
    assert k["alert_count"] == len(alerts)
    assert k["alert_rate"] == round(len(alerts) / len(df) * 100, 2)
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        assert k[f"{sev.lower()}_alerts"] == (alerts.alert_severity == sev).sum()
    assert k["potential_exposure_usd"] == pytest.approx(pd.to_numeric(alerts.potential_exposure_usd).sum(), abs=0.01)
    assert k["total_value_usd"] == pytest.approx(pd.to_numeric(df.amount_usd_equiv).sum(), abs=0.01)
    assert k["escalations"] == (df.escalation_required_flag.astype(str).str.upper() == "TRUE").sum()
    open_ids = df[df.case_status.isin(["NEW", "IN_REVIEW", "ESCALATED"])].case_id.nunique()
    assert k["open_cases"] == open_ids


def test_severity_and_exposure_breakdowns():
    sev = {r["severity"]: r["count"] for r in get("/analytics/alerts-by-severity").json()}
    assert sev == alerts.alert_severity.value_counts().to_dict()
    exp = sum(r["exposure_usd"] for r in get("/analytics/exposure").json())
    assert exp == pytest.approx(pd.to_numeric(alerts.potential_exposure_usd).sum(), abs=0.01)


@pytest.mark.parametrize("filt,mask", [
    ({"severity": "critical"}, lambda a: a.alert_severity == "CRITICAL"),
    ({"channel": "card"}, lambda a: a.channel == "CARD"),
    ({"score_min": 70, "score_max": 90}, lambda a: pd.to_numeric(a.alert_score).between(70, 90)),
    ({"escalation": "true"}, lambda a: a.escalation_required_flag.astype(str).str.upper() == "TRUE"),
    ({"case_status": "closed"}, lambda a: a.case_status == "CLOSED"),
])
def test_alert_filters(filt, mask):
    assert get("/alerts", page_size=1, **filt).json()["total"] == mask(alerts).sum()


def test_alert_pagination_is_disjoint():
    p1 = [i["transaction_id"] for i in get("/alerts", page=1, page_size=50).json()["items"]]
    p2 = [i["transaction_id"] for i in get("/alerts", page=2, page_size=50).json()["items"]]
    assert len(p1) == 50 and not set(p1) & set(p2)


def test_sql_injection_is_inert():
    r = get("/alerts", search="'; DROP TABLE kb; --")
    assert r.status_code == 200 and r.json()["total"] == 0
    assert get("/kpis").json()["total_transactions"] == len(df)


@pytest.mark.parametrize("path", ["/transactions/NOPE", "/customers/NOPE", "/devices/NOPE",
                                  "/beneficiaries/NOPE", "/transactions/NOPE/related"])
def test_unknown_ids_404(path):
    r = get(path)
    assert r.status_code == 404 and "Traceback" not in r.text


def test_malformed_filters_422():
    assert get("/alerts", score_min="abc").status_code == 422
    assert get("/transactions", page=0).status_code == 422


def test_transaction_detail_matches_csv():
    row = alerts.sort_values("alert_score", ascending=False).iloc[0]
    d = get(f"/transactions/{row.transaction_id}").json()
    assert d["customer_id"] == row.customer_id
    assert d["alert_reason_codes"] == row.alert_reason_codes
    assert d["amount_usd_equiv"] == pytest.approx(float(row.amount_usd_equiv))


def test_related_includes_device_and_beneficiary_links():
    """Regression: same-customer rows used to hide same-device / same-beneficiary links."""
    for _, a in alerts.head(40).iterrows():
        exp_dev = ((df.device_id == a.device_id) & (df.transaction_id != a.transaction_id)).sum()
        exp_ben = ((df.beneficiary_id == a.beneficiary_id) & (a.beneficiary_id != "")
                   & (df.transaction_id != a.transaction_id)).sum()
        rel = get(f"/transactions/{a.transaction_id}/related").json()
        if rel["truncated"]:
            continue  # capped at 100 rows; completeness only checkable when not truncated
        got_dev = sum("SAME_DEVICE" in r["relationships"] for r in rel["related"])
        got_ben = sum("SAME_BENEFICIARY" in r["relationships"] for r in rel["related"])
        assert got_dev == exp_dev, a.transaction_id
        assert got_ben == exp_ben, a.transaction_id


def test_customer_beneficiary_device_aggregates():
    cid = df.customer_id.iloc[0]
    c = get(f"/customers/{cid}").json()
    assert c["transaction_count"] == (df.customer_id == cid).sum()
    bid = df[df.beneficiary_id != ""].beneficiary_id.value_counts().index[0]
    assert get(f"/beneficiaries/{bid}").json()["transaction_count"] == (df.beneficiary_id == bid).sum()
    did = df.device_id.value_counts().index[0]
    assert get(f"/devices/{did}").json()["transaction_count"] == (df.device_id == did).sum()


def test_risky_filters_exclude_institutional_entities():
    devs = get("/devices", risky_only="true", page_size=200).json()["items"]
    assert devs and all(d["device_type"] not in ("ATM_TERMINAL", "POS_TERMINAL") for d in devs)
    bens = get("/beneficiaries", high_risk_only="true", page_size=200).json()["items"]
    assert bens and all(b["beneficiary_type"] != "MERCHANT" for b in bens)


def test_legitimate_high_value_is_visible_not_hidden():
    """Counter-evidence scenario: high-value transactions that did NOT alert must be queryable."""
    hv = df[(pd.to_numeric(df.amount_usd_equiv) > 5000) & (~df._alert)]
    assert len(hv) > 0
    r = get("/transactions", search=hv.iloc[0].transaction_id).json()
    assert r["total"] == 1 and r["items"][0]["alert_generated_flag"] is False
