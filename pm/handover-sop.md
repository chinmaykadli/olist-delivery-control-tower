# Handover SOP: how to run and refresh the control tower

## Rebuild from scratch
```bash
git clone <this-repo> && cd olist-delivery-control-tower
pip install -r requirements.txt
make all     # data -> DB + 14 quality checks -> analyses -> dashboards -> number check
```
`make all` stops if `scripts/check_numbers.py` finds a quoted number that no
longer matches `outputs/`. Open `docs/index.html` and `docs/ops.html`, or
serve `docs/` with GitHub Pages.

## Weekly operating rhythm (if this were live)
1. **Monday 09:00, data:** refresh the load and read the quality-check output
   first. Any new non-zero check goes on the RAID log before anything else.
2. **Monday, carrier watch:** read in-transit ageing (`v_transit_ageing`). At
   20% or above, apply the promise guardrail to new orders that week and tell
   CX. Two alarm weeks in a row: escalate to Logistics with the lane split
   (`v_lane_variability`).
3. **Seller call list:** work the month's 20 sellers from `v_exception_queue`,
   about 5 a week, starting with "misses own shipping limit" and "slow
   handover". Expected hit rate about a third (Jan-Jul 2018 backtest); it is a
   conversation, not a penalty. Log outcome and status in the queue.
4. **Weekly KPI report:** the six numbers in `v_weekly_kpis`.
5. **Monthly:** re-run the forecast and log MAPE; widen promises ahead of any
   forecast peak; re-check the queue rule against its baseline.

## Where each number comes from (data lineage)
| Number | Source |
|---|---|
| Late rate, on-time rate | `v_order_facts` / `v_monthly_metrics` -> `outputs/kpi_summary.json` |
| Peak months, peak share | `v_month_flags` -> `outputs/lanes_summary.json` |
| Weekly promise vs late | `outputs/weekly_promise_vs_late.csv` |
| In-transit ageing, guardrail backtest | `v_transit_ageing`, `v_guardrail_backtest` |
| Lane Pareto, lane types, promise curve | `v_lane_pareto`, `v_lane_variability`, `v_promise_curve` |
| Promise accuracy | `v_promise_accuracy` -> `outputs/promise_accuracy.csv` |
| Seller late rates, persistence | `v_order_seller_facts` -> `outputs/seller_performance.csv`, `lanes_summary.json` |
| Seller call list backtest | `v_seller_features` -> `outputs/scorecard_summary.json`, `scorecard_comparison.csv`, `scorecard_per_month.csv` |
| Exception queue | `v_exception_queue` -> `outputs/exception_queue.csv` |
| Reviews by answer timing | `outputs/review_vs_lateness.csv`, `review_by_answer_timing.csv` |
| Repeat-purchase cost | `outputs/lanes_summary.json` (logistic regression in `analysis/lanes_analysis.py`) |
| Pilot power | `outputs/lanes_summary.json` (`pilot_*` keys) |
| Censoring bound | `v_censoring_bound` -> `outputs/censoring_bound.csv` |
| Forecast and MAPE | `outputs/forecast_vs_actual.csv` |
