# UAT log

Scenarios run against the rebuilt pipeline, 27-28 Oct 2026. Trace = the
number seen by a reader matches the number produced by the SQL layer.

| # | Scenario | Method | Expected | Actual | Result |
|---|---|---|---|---|---|
| UAT-1 | Orders analysed KPI traces | `COUNT(*) FROM v_order_facts` inside `v_params` window | 90,119 | 90,119 | PASS |
| UAT-2 | Late definition | delivered date > estimated date, date granularity | 6,141 late (6.8%) | 6,141 (6.8%) | PASS |
| UAT-3 | Censoring test | `v_censoring_bound`: every open order counted late | Jun/Jul 2018 move by about 1 point at most | Jun 1.2% -> 1.9%, Jul 3.4% -> 4.5% | PASS |
| UAT-4 | Dashboard charts = views | chart notes read `outputs/*.json`; no typed numbers | identical | identical | PASS |
| UAT-5 | Forecast holdout | Mar-Jul 2018, 6 scopes x 2 methods | winner and MAPE per scope | naive, 5.4% all orders | PASS |
| UAT-6 | Scorecard leakage | features from months M-3 to M-1 only (RANGE window); gap sensitivity M-4 to M-2 | hit rate holds | 34% -> 30% with gap | PASS |
| UAT-7 | Queue cap | picks per month = 20 for each of 7 test months | 140 | 140 | PASS |
| UAT-8 | Quality checks run | 14 checks; 6 PASS + 8 logged to RAID | as expected | as expected | PASS |
| UAT-9 | Clean rebuild | fresh checkout: `make all` | no errors, check_numbers passes | PASS | PASS |
| UAT-10 | No employer data in repo | grep employer names in data/code/docs | none | none | PASS |
| UAT-11 | Seller metrics exclude multi-seller | `v_order_seller_facts` rows = single-seller orders | 95,195 = 95,195 | verified | PASS |
| UAT-12 | One row per order in seller facts | `COUNT(*) = COUNT(DISTINCT order_id)` | equal | equal | PASS |
| UAT-13 | Survey field | pre-delivery share uses `review_answer_timestamp` | 72% | 72% | PASS |
| UAT-14 | Ageing uses no future data | `v_transit_ageing` reads only handover <= as-of and delivery > as-of | code-inspected | code-inspected | PASS |
| UAT-15 | Every quoted number | `scripts/check_numbers.py` | 0 mismatches, 0 stale phrases | see build log | PASS |
