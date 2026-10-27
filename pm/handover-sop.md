# Handover SOP — how to run and refresh the control tower

## Rebuild from scratch (four commands)
```bash
git clone <this-repo> && cd olist-delivery-control-tower
pip install -r requirements.txt
./scripts/download_data.sh            # 8 CSVs from Olist's public mirror
python analysis/build_db.py           # schema + quality checks + views
python analysis/run_analysis.py       # metrics, charts, forecast
python analysis/scorecard_backtest.py # scorecard + 2018 backtest
python dashboard/build_dashboard.py   # docs/index.html
```
Open `docs/index.html`, or enable GitHub Pages on `docs/` to serve it.

## Weekly operating rhythm (if this were live)
1. **Monday 09:00:** refresh data load; read the quality-check output first.
   Any new non-zero check goes on the RAID log before anything else.
2. **Review queue:** run the scorecard; work the month's top-20 scored
   sellers top-down by trailing GMV. Expected hit rate ~26% (2018 holdout,
   1.4x base) - a conversation queue, not an auto-action list.
3. **Leading indicator watch:** dispatch time is the strongest single signal
   (largest model coefficient). Late orders average 6.0 days to carrier
   handover vs 3.1 on time; shipping-limit breach rate is the
   seller-controllable KPI.
4. **Monthly:** re-run forecast; log MAPE against actuals; re-baseline if
   MAPE drifts above 15% for two consecutive months.

## Where each number comes from (data lineage)
| Number | Source |
|---|---|
| Late rate, OTIF | `v_order_facts` / `v_monthly_metrics` |
| Seller late rates, Pareto | `v_order_seller_facts` -> `outputs/seller_performance.csv` |
| Route rates | `v_route_facts` -> `outputs/late_by_route.csv` |
| Review by lateness | `outputs/review_vs_lateness.csv` |
| Forecast + MAPE | `outputs/forecast_vs_actual.csv` |
| Scorecard queue + lift | `outputs/scorecard_summary.json`, `outputs/scorecard_lift.csv` |
| Dispatch vs transit split | `outputs/dispatch_vs_transit.csv` |
| Seller persistence | `outputs/seller_persistence.csv` |
| Route promise percentiles | `outputs/route_delivery_percentiles.csv` |
