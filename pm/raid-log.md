# RAID log

Live log. Raised dates shown; status as of the 27-28 Oct rebuild.

| # | Type | Item | Raised | Status / mitigation |
|---|---|---|---|---|
| 1 | Risk | Dataset covers 2016-2018, one country | 27 Oct | Open - memo frames the method, not the numbers, as the deliverable |
| 2 | Risk | Review score has causes beyond lateness | 27 Oct | Mitigated - survey-timing split done; association stated, not proof |
| 3 | Risk | Scope grows (NLP, maps, extra models) | 27 Oct | Mitigated - parked in backlog |
| 4 | Risk | Threshold scorecard near-random (1.2x lift, 46% of seller-months flagged) | 27 Oct | **Closed** - rebuilt as logistic score + capped top-20 queue with lift curve; reported honestly (26% hit vs 18% base) |
| 5 | Assumption | Late = delivered after estimated delivery DATE | 27 Oct | Written in README + views; date-granularity cast verified |
| 6 | Assumption | Revenue-at-risk rates are assumptions | 27 Oct | GMV exposed only; take rate labelled as not-in-dataset |
| 7 | Issue | 8 delivered orders missing delivery timestamp | 27 Oct | Excluded from late rate (quality check Q3) |
| 8 | Issue | 775 orders have no order items | 27 Oct | Excluded from order facts (Q4); memo data-fix item |
| 9 | Issue | 443 orders: payment total != items + freight | 27 Oct | Order-level analysis unaffected (Q10); memo data-fix item |
| 10 | Issue | 610 products missing category | 27 Oct | Bucketed "unknown" (Q6); memo data-fix item |
| 11 | Issue | 646 delivered orders have no review | 27 Oct | Review metrics on reviewed orders only (Q9) |
| 12 | Dependency | Dashboard tool free on macOS | 27 Oct | Closed - Plotly + GitHub Pages |
| 13 | Issue | YoY seasonal forecast fails on ramp-up base year | 27 Oct | Closed - forecast moved to appendix, naive + MA baselines, winner by holdout MAPE |
| 14 | Issue | Right-censoring: Jun-Aug 2018 late rates biased down | 27 Oct | **Closed** - analysis window cut at May 2018; documented in README Limits |
| 15 | Issue | Worst-decile p-value was circular (selected then tested) | 27 Oct | **Closed** - deleted; replaced with 2017->2018 persistence table |
| 16 | Issue | Survey timing: 76% of late-order reviews pre-delivery | 28 Oct | **Closed** - split reported; memo recommendation 3 |
| 17 | Issue | Multi-seller orders (1.2%) misattribute carrier handover | 27 Oct | **Closed** - excluded from seller metrics |
| 18 | Issue | March 2018 late-rate spike (19%) unexplained | 28 Oct | Open - visible in trend chart; no carrier data to diagnose |
| 19 | Risk | "OTIF" overclaims (in-full not measured) | 27 Oct | **Closed** - renamed on-time rate everywhere |
