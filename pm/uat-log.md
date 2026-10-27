# UAT log

Scenarios run against the rebuilt pipeline, 27-28 Oct 2026. Trace = the
number seen by a reader matches the number produced by the SQL layer.

| # | Scenario | Method | Expected | Actual | Result |
|---|---|---|---|---|---|
| UAT-1 | Orders analysed KPI traces | `COUNT(*) FROM v_order_facts WHERE purchase_month <= '2018-05-01'` | 77,867 | 77,867 | PASS |
| UAT-2 | Late definition | delivered date > estimated date, date granularity | 5,862 late (7.5%) | 5,862 (7.5%) | PASS |
| UAT-3 | Censoring cut | Jun 2018 late rate would read 1.2% vs typical 5-7% | window ends May 2018 | applied in views + scripts | PASS |
| UAT-4 | Dashboard charts = views | `v_monthly_metrics` vs chart data | identical series | identical | PASS |
| UAT-5 | Forecast holdout | Mar-May 2018, 6 scopes x 2 methods | naive wins all-orders (4.3% MAPE) | matches | PASS |
| UAT-6 | Scorecard no leakage | features end before label month M | 90-day trailing, label = M | code-inspected | PASS |
| UAT-7 | Lift table sums | queue picks per K = 5 months x K | 25/50/100/250/500 | matches | PASS |
| UAT-8 | Quality checks run | 11 checks; 6 PASS + 5 logged to RAID | as expected | as expected | PASS |
| UAT-9 | Clean rebuild | fresh checkout: 4 commands complete | no errors | PASS (fresh venv + download) | PASS |
| UAT-10 | No employer data in repo | grep employer names in data/code/docs | none | none | PASS |
| UAT-11 | Seller metrics exclude multi-seller | `v_order_seller_facts` has n_sellers = 1 only | 1.2% of orders excluded | verified | PASS |
