# Rawbank Sentient Command Centre

> **Academic simulation only.** All data is synthetic. This does not represent Rawbank's real customers, transactions, fraud detection systems, internal rules, or proprietary information. This is Use Case 01 of the iTech Pre-Sales Technical Build Assignment.

---

## What Is This?

The **Rawbank Sentient Command Centre** is an enterprise fraud-intelligence operations dashboard prototype built for a synthetic Rawbank banking environment. It enables a fraud/risk/operations analyst to:

```
Monitor → Prioritise → Analyse → Drill Down
```

This is **System 1 of 2** in the iTech Pre-Sales Technical Build Assignment. The companion system — **Rawbank Sentient Fraud Investigation Copilot** — is a separate repository that connects via a lightweight investigation handoff.

---

## Architecture

```
┌─────────────────────┐
│ RAWBANK_SENTIENT_KB │
│ .csv (2,500 rows)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   DuckDB (in-memory)│
│   + Python/Pandas   │
└──────────┬──────────┘
           │
     ┌─────┴──────┐─────────────┐
     ▼            ▼             ▼
 KPI Engine  Alert Analytics  Entity Analytics
     │            │             │
     └────────────┼─────────────┘
                  │
                  ▼
        ┌─────────────────┐
        │   FastAPI REST  │
        └────────┬────────┘
                 │  JSON
                 ▼
     ┌──────────────────────┐
     │   Next.js Dashboard  │
     │   React + TypeScript │
     │   Recharts           │
     └──────────────────────┘
```

---

## Technology Stack

| Layer    | Technology                            |
|----------|---------------------------------------|
| Frontend | Next.js 16, React 19, TypeScript, Recharts |
| Backend  | FastAPI, Pydantic v2, Python 3.11+   |
| Data     | DuckDB (in-memory), Pandas            |
| Styling  | Vanilla CSS, Google Fonts (Inter, Space Grotesk) |

---

## Dataset

- **Source:** `backend/data/RAWBANK_SENTIENT_KB.csv`
- **Rows:** ~2,500 synthetic transactions
- **Columns:** 110
- **Customers:** ~120 synthetic customers
- **Beneficiaries:** ~175 synthetic beneficiaries
- **Devices:** ~133 synthetic devices
- **Date range:** ~90 days
- **QA:** 34/34 tests passing (alert rate, severity, channel, geographic, fraud rule coverage)

> ⚠️ `RAWBANK_SENTIENT_GROUND_TRUTH.csv` is **NOT** in this repository. It exists only for evaluator-side testing and must never be loaded by this application.

---

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Command Centre** | Executive operational overview — KPIs, trends, top risk customers |
| **Fraud Intelligence** | Pattern analysis, channel risk, geography, velocity, cross-border |
| **Alert Operations** | Searchable/filterable alert queue |
| **Transactions** | All transactions with channel/status/alert filters |
| **Customers** | Customer risk profiles with KYC, segment, alert filters |
| **Beneficiaries** | Beneficiary risk view with mule indicators |
| **Devices** | Device footprint with shared-device risk indicators |
| **Cases** | Open/escalated case management view |
| **Transaction Detail** | Full drill-down — all 110 fields, evidence, related activity, Copilot handoff |
| **Customer Detail** | Customer profile + transaction history |
| **Beneficiary Detail** | Beneficiary + FR-14 mule indicator |
| **Device Detail** | Device + FR-13 shared device indicator |

---

## Environment Variables

### Backend (`backend/.env`)

```
DATA_PATH=data/RAWBANK_SENTIENT_KB.csv   # relative to backend/
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_COPILOT_URL=http://localhost:3001
```

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- pip

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/rawbank-sentient-command-centre.git
cd rawbank-sentient-command-centre
```

### 2. Dataset

The canonical dataset is at:

```
backend/data/RAWBANK_SENTIENT_KB.csv
```

Do **NOT** put `RAWBANK_SENTIENT_GROUND_TRUTH.csv` in this repository.

---

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at:
- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

---

## Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Backend health + record count |
| `GET /api/kpis` | All KPIs calculated from dataset |
| `GET /api/alerts` | Alert queue with filters + pagination |
| `GET /api/transactions` | Transaction list with filters |
| `GET /api/transactions/{id}` | Full transaction drill-down |
| `GET /api/transactions/{id}/related` | Related activity |
| `GET /api/customers` | Customer list with filters |
| `GET /api/customers/{id}` | Customer profile |
| `GET /api/customers/{id}/transactions` | Customer transaction history |
| `GET /api/beneficiaries` | Beneficiary list |
| `GET /api/beneficiaries/{id}` | Beneficiary detail |
| `GET /api/devices` | Device list |
| `GET /api/devices/{id}` | Device detail |
| `GET /api/analytics/alerts-by-severity` | Severity distribution |
| `GET /api/analytics/alerts-by-pattern` | Fraud pattern breakdown |
| `GET /api/analytics/alerts-by-channel` | Channel activity |
| `GET /api/analytics/alert-trend` | Daily alert/transaction counts |
| `GET /api/analytics/geography` | Provincial distribution |
| `GET /api/analytics/velocity` | High-velocity customers |
| `GET /api/analytics/exposure` | Potential exposure by severity |
| `GET /api/analytics/top-risk-customers` | Top 10 risk customers |
| `GET /api/analytics/cross-border` | Cross-border activity pairs |

---

## Synthetic Fraud Rules (Workshop Rules)

These are academic simulation rules — **not** Rawbank's actual internal fraud policies:

| Rule | Description |
|------|-------------|
| FR-01 | Amount ≥ 5× customer median |
| FR-02 | Amount ≥ 10× customer median |
| FR-03 | New beneficiary |
| FR-04 | New / untrusted device |
| FR-05 | 3+ failed logins in 30 minutes |
| FR-06 | Password reset within 24 hours |
| FR-07 | Recent SIM change |
| FR-08 | 4+ transactions in 10 minutes |
| FR-09 | Abnormal 1-hour outbound value |
| FR-10 | Impossible travel |
| FR-11 | Unusual country/location |
| FR-12 | VPN/proxy signal |
| FR-13 | Device used across 3+ accounts |
| FR-14 | Beneficiary receives from 5+ customers |
| FR-15 | Card-not-present + unusual behaviour |
| FR-16 | Unusual transaction time |
| FR-17 | New device + new beneficiary |
| FR-18 | Failed logins + reset + new device |
| FR-19 | New cross-border beneficiary + abnormal value |
| FR-20 | Incomplete corporate approval |

---

## Design Principles

The UI reflects Rawbank's current brand identity:

- **Bold black + yellow** — the Congolese leopard identity
- **Yellow** = vitality, optimism, prosperity, strength, innovation
- **Black typography** = solidity, reliability, trust
- **Information density** — serious fraud operations workstation
- **No decorative elements** — operational, not decorative
- **Clear severity states** — CRITICAL → HIGH → MEDIUM → LOW
- **Evidence-based** — supporting and counter-evidence displayed distinctly

---

## Copilot Handoff

The Command Centre is designed to hand off investigations to the **Rawbank Sentient Fraud Investigation Copilot** (separate repository). On every transaction drill-down page, there is:

> **"Investigate with Sentient Copilot →"**

This links to:
```
http://localhost:3001/investigate?transaction_id=<TRANSACTION_ID>
```

Configure the target via:
```
NEXT_PUBLIC_COPILOT_URL=http://localhost:3001
```

---

## Docker

```bash
docker-compose up --build
```

This starts:
- Backend on port 8000
- Frontend on port 3000

---

## Known Limitations

- Dataset is synthetic — academic prototype only
- Backend uses in-memory DuckDB (no persistence between restarts)
- No authentication — single analyst session
- Copilot integration requires the separate repository
- Desktop-first design — limited mobile support

---

## Validation

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

The suite recomputes every KPI, severity/exposure breakdown, filter count, drill-down and
relationship (customer / device / beneficiary) independently with pandas from the CSV and
compares it with the API. It also covers: unknown IDs (404), malformed filters (422), SQL-injection
input, the ground-truth-not-loaded guarantee, institutional-entity exclusion (ATM/POS, merchants)
and legitimate high-value transactions staying visible.

---

## Evidence model (supporting vs counter-evidence)

Supporting evidence on a transaction is derived from the rule codes the alert actually fired,
with the underlying values. Counter-evidence follows the ruleset section 6 (trusted device +
established beneficiary, recurring payment, diaspora cross-border, complete corporate approvals,
within-baseline behaviour) plus institutional context: ATM/POS terminals and merchants legitimately
touch many accounts/senders, so FR-13/FR-14 on them are shown with that caveat and excluded from the
"risky device / high-risk beneficiary" filters unless explicitly included.

---

## Repository Structure

```
rawbank-sentient-command-centre/
├── frontend/              # Next.js dashboard (port 3000)
├── backend/               # FastAPI + DuckDB (port 8000)
│   ├── data/RAWBANK_SENTIENT_KB.csv
│   ├── routes/  models.py  database.py  main.py
│   └── tests/test_api.py
├── docker-compose.yml
└── README.md
```

The Copilot lives in a **separate repository / application**:
`rawbank-sentient-fraud-investigation-copilot` (port 3001, backend 8001).
