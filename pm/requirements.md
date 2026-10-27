# Requirements — user stories and acceptance criteria

Format: story / acceptance criteria / status. Verified in uat-log.md.

1. **As the ops lead, I want one agreed definition of "late"** so every
   report uses the same number.
   - AC: definition written in README and implemented once, in
     `sql/03_views.sql` (`v_order_facts.is_late`). ✅
2. **As the ops lead, I want late rate by seller, category and route** so I
   can see where the problem sits.
   - AC: three outputs with minimum-volume guards (sellers ≥30 orders,
     categories ≥500, routes ≥100) in `outputs/`. ✅
3. **As the ops lead, I want to know what lateness costs in review scores**
   so I can prioritise.
   - AC: review by lateness band, like-for-like note (category mix) stated
     with the chart. ✅
4. **As the analyst, I want data quality checks as runnable queries** so
   issues are found by the pipeline, not by a reader.
   - AC: 11 checks in `sql/02_quality_checks.sql`, printed on every build;
     non-zero results logged in the RAID log. ✅
5. **As Seller Ops, I want a capped monthly call list tested on unseen
   months** so I can trust what it catches and see what it wrongly flags.
   - AC: queue cap (20/month) fixed from ops capacity before testing; rule
     chosen on 2017 only; hit rate with 95% CI, lift, AUC and a simple-sort
     baseline reported on the Jan-Jul 2018 holdout; 1-4 order months dropped
     from the label; one-month-gap sensitivity run. ✅
6. **As the business, I want a monthly order forecast with an honest error
   figure** so peak planning has a baseline.
   - AC: two candidate baselines compared on a Mar-Jul 2018 holdout; the
     winner and its MAPE reported per scope. ✅
7. **As a dashboard user, I want the findings and the operating view without
   running code.**
   - AC: `docs/index.html` (findings) and `docs/ops.html` (peaks, early
     warning, lanes, promise curve, call list, weekly KPIs) load from GitHub
     Pages; every note reads its numbers from `outputs/`. ✅
8. **As a reviewer, I want to rebuild everything from the README** so the
   work is checkable.
   - AC: `make all` from a clean checkout rebuilds outputs and dashboards and
     passes `scripts/check_numbers.py`. ✅
9. **As Logistics, I want an early signal of carrier slowdowns** so promises
   can be widened before reviews arrive.
   - AC: a weekly signal computable with no future data (`v_transit_ageing`),
     its lead over the delivered-late signal measured, and a promise
     guardrail backtested with its assumptions stated. ✅
10. **As Logistics, I want lanes ranked by where late orders actually are**
    so effort goes to the biggest problems.
    - AC: lane Pareto by late orders; lanes typed structural vs peak-driven;
      promise curve showing on-time rate per extra promise day. ✅
11. **As the founder, I want the cost of lateness in money terms** with its
    uncertainty.
    - AC: repeat-purchase effect from a logistic regression adjusted for
      state and cohort month, with odds ratio CI and lost repeat orders. ✅
12. **As the PM, I want the pilot sized before it is promised.**
    - AC: ICC estimated from the data, design effect applied, sellers per arm
      and the 8-week minimum detectable effect reported. ✅
