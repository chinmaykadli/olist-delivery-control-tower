# RAID log

Live log. Raised dates shown; status as of the 27-28 Oct rebuild.

| # | Type | Item | Raised | Status / mitigation |
|---|---|---|---|---|
| 1 | Risk | Dataset covers 2016-2018, one country | 27 Oct | Open - memo frames the method, not the numbers, as the deliverable |
| 2 | Risk | Review score has causes beyond lateness | 27 Oct | Mitigated - survey-timing split done; association stated, not proof |
| 3 | Risk | Scope grows (NLP, maps, extra models) | 27 Oct | Mitigated - parked in backlog |
| 4 | Risk | Threshold scorecard near-random (1.2x lift, 46% of seller-months flagged) | 27 Oct | **Closed** - capped 20/month call list; one-line sort chosen on 2017; 34% hit vs 21% base on Jan-Jul 2018 (CI 26% to 42%); model kept as comparison |
| 5 | Assumption | Late = delivered after estimated delivery DATE | 27 Oct | Written in README + views; date-granularity cast verified |
| 6 | Assumption | Revenue-at-risk rates are assumptions | 27 Oct | GMV exposed only; take rate labelled as not-in-dataset |
| 7 | Issue | 8 delivered orders missing delivery timestamp | 27 Oct | Excluded from late rate (quality check Q3) |
| 8 | Issue | 775 orders have no order items | 27 Oct | Excluded from order facts (Q4); memo data-fix item |
| 9 | Issue | 443 orders: payment total != items + freight | 27 Oct | Order-level analysis unaffected (Q10); memo data-fix item |
| 10 | Issue | 610 products missing category | 27 Oct | Bucketed "unknown" (Q6); memo data-fix item |
| 11 | Issue | 646 delivered orders have no review | 27 Oct | Review metrics on reviewed orders only (Q9) |
| 12 | Dependency | Dashboard tool free on macOS | 27 Oct | Closed - Plotly + GitHub Pages |
| 13 | Issue | YoY seasonal forecast fails on ramp-up base year | 27 Oct | Closed - forecast moved to appendix, naive + MA baselines, winner by holdout MAPE |
| 14 | Issue | Right-censoring: Jun-Aug 2018 late rates biased down | 27 Oct | **Closed (revised 28 Oct)** - open-order worst case moves Jun/Jul by about one point; Jun-Jul kept, Aug+ excluded; `v_censoring_bound` |
| 15 | Issue | Worst-decile p-value was circular (selected then tested) | 27 Oct | **Closed** - deleted; replaced with 2017->2018 persistence table |
| 16 | Issue | Survey timing: pre-delivery share measured on the send date, not the answer date | 28 Oct | **Closed** - now `review_answer_timestamp`: 72% answered before delivery; memo recommendation 3 |
| 17 | Issue | Multi-seller orders (1.3%) misattribute carrier handover | 27 Oct | **Closed** - excluded from seller metrics |
| 18 | Issue | Feb-Mar 2018 late-rate spike | 28 Oct | **Mitigated** - promises fell as lateness rose; in-transit ageing gave 3 weeks' warning; root cause (carrier) still not in data |
| 19 | Risk | "OTIF" overclaims (in-full not measured) | 27 Oct | **Closed** - renamed on-time rate everywhere |
| 20 | Issue | `v_order_seller_facts` GROUP BY without order_id merged 476 orders | 28 Oct | **Closed** - order_id added; one row per order (95,195) |
| 21 | Issue | Duplicate `delivery_days` column in `v_order_facts` | 28 Oct | **Closed** - removed |
| 22 | Issue | Cancellation feature counted item rows; most failed orders have no items | 28 Oct | **Closed** - feature and view removed; README Limits |
| 23 | Issue | Scorecard labelled 1-4 order months as good | 28 Oct | **Closed** - dropped from label; base rate 21% not 18% |
| 24 | Issue | 20 orders handed to carrier after delivery, 2 before purchase, 1 with no carrier date | 28 Oct | Open - checks Q12-Q14; excluded from nothing yet, too few to move a metric |
| 25 | Risk | Ageing alarm threshold (20%) set in-sample on two episodes | 28 Oct | Open - treat as a monitored hypothesis; May 2017 alarms were weak |
| 26 | Risk | Seller pilot underpowered at 20 sellers/month (needs 136 per arm) | 28 Oct | Open - run as standard practice with monitoring; test on breach rate |
| 27 | Risk | Stale numbers typed into docs | 28 Oct | **Closed** - `scripts/check_numbers.py` runs in `make all` |
