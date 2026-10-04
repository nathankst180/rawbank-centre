"""
DuckDB database singleton for Rawbank Sentient Command Centre.
Loads RAWBANK_SENTIENT_KB.csv once and serves all analytical queries.
This is synthetic academic data only - NOT Rawbank's real internal data.
"""
import os
import threading
import duckdb
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_con: duckdb.DuckDBPyConnection | None = None
_CSV_PATH: str = ""
_db_lock = threading.Lock()


def _get_csv_path() -> str:
    data_path = os.getenv("DATA_PATH", "data/RAWBANK_SENTIENT_KB.csv")
    # Resolve relative to the backend directory
    base = Path(__file__).parent
    resolved = base / data_path
    if not resolved.exists():
        raise FileNotFoundError(
            f"Canonical dataset not found at: {resolved}. "
            "Ensure RAWBANK_SENTIENT_KB.csv is present in backend/data/."
        )
    return str(resolved)


def get_db() -> duckdb.DuckDBPyConnection:
    global _con, _CSV_PATH
    if _con is None:
        with _db_lock:
            if _con is None:
                _CSV_PATH = _get_csv_path()
                _con = duckdb.connect(database=":memory:")
                # Load CSV into a persistent in-memory table for efficient querying
                _con.execute(f"""
                    CREATE TABLE kb AS
                    SELECT * FROM read_csv_auto('{_CSV_PATH.replace(chr(92), '/')}', 
                        header=true, 
                        null_padding=true,
                        ignore_errors=false
                    )
                """)
                # Create useful indices / views
                _con.execute("""
                    CREATE VIEW alerts_view AS
                    SELECT * FROM kb
                    WHERE alert_generated_flag = TRUE OR alert_generated_flag = 'TRUE'
                """)
                print(f"[DB] Loaded {_con.execute('SELECT COUNT(*) FROM kb').fetchone()[0]} records from CSV.")
    return _con


def query(sql: str, params: list = None):
    """Execute a SQL query and return list of dicts."""
    con = get_db()
    with _db_lock:
        if params:
            result = con.execute(sql, params)
        else:
            result = con.execute(sql)
        cols = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(cols, row)) for row in rows]


def query_one(sql: str, params: list = None):
    """Execute a SQL query and return a single dict or None."""
    results = query(sql, params)
    return results[0] if results else None


def query_scalar(sql: str, params: list = None):
    """Execute a SQL query and return a single scalar value."""
    con = get_db()
    with _db_lock:
        if params:
            result = con.execute(sql, params)
        else:
            result = con.execute(sql)
        row = result.fetchone()
        return row[0] if row else None

