"""
Rawbank Sentient Command Centre — FastAPI Backend
Academic prototype using synthetic data. Not Rawbank's real internal data.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import get_db
from models import HealthResponse
from routes import kpis, alerts, transactions, customers, beneficiaries, devices, analytics

load_dotenv()

app = FastAPI(
    title="Rawbank Sentient Command Centre API",
    description=(
        "Academic fraud-intelligence operations API. "
        "All data is synthetic. Not Rawbank's real internal data."
    ),
    version="1.0.0",
)

# CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(kpis.router, prefix="/api", tags=["KPIs"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(transactions.router, prefix="/api", tags=["Transactions"])
app.include_router(customers.router, prefix="/api", tags=["Customers"])
app.include_router(beneficiaries.router, prefix="/api", tags=["Beneficiaries"])
app.include_router(devices.router, prefix="/api", tags=["Devices"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])


@app.on_event("startup")
def startup():
    """Pre-load the DuckDB database on startup."""
    try:
        get_db()
        print("[Sentient CC] Backend started — DuckDB loaded from RAWBANK_SENTIENT_KB.csv")
    except FileNotFoundError as e:
        print(f"[CRITICAL] {e}")


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def health():
    try:
        from database import query_scalar
        count = query_scalar("SELECT COUNT(*) FROM kb")
        return HealthResponse(
            status="ok",
            record_count=count or 0,
            data_source="RAWBANK_SENTIENT_KB.csv",
            disclaimer=(
                "Academic simulation only. All data is synthetic. "
                "Not Rawbank's real customer data or internal fraud systems."
            ),
        )
    except Exception:
        return HealthResponse(
            status="error",
            record_count=0,
            data_source="RAWBANK_SENTIENT_KB.csv",
            disclaimer="Dataset unavailable - see server logs.",
        )


@app.get("/")
def root():
    return {
        "service": "Rawbank Sentient Command Centre API",
        "version": "1.0.0",
        "docs": "/docs",
    }
