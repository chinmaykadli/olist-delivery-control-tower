"""Build the local DuckDB database from the raw CSVs.

Runs the SQL layer in order (schema, quality checks, views) and prints the
quality-check results. Usage: python analysis/build_db.py
"""
import pathlib
import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "olist.duckdb"

def main() -> None:
    con = duckdb.connect(str(DB))
    con.execute(f"SET threads TO 4")

    schema = (ROOT / "sql" / "01_schema.sql").read_text()
    checks = (ROOT / "sql" / "02_quality_checks.sql").read_text()
    views = (ROOT / "sql" / "03_views.sql").read_text()

    print("== 01_schema ==")
    con.execute(schema)
    for table in ["orders", "order_items", "order_payments", "order_reviews",
                  "customers", "sellers", "products", "category_translation"]:
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n:,} rows")

    print("== 02_quality_checks ==")
    for statement in [s.strip() for s in checks.split(";") if "SELECT" in s.upper()]:
        name, failures = con.execute(statement).fetchone()
        flag = "PASS" if failures == 0 else f"{failures:,}"
        print(f"  {name}: {flag}")

    print("== 03_views ==")
    con.execute(views)
    for view in ["v_order_facts", "v_order_seller_facts", "v_seller_month",
                 "v_route_facts", "v_monthly_metrics", "v_seller_cancellations"]:
        n = con.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0]
        print(f"  {view}: {n:,} rows")
    con.close()

if __name__ == "__main__":
    main()
