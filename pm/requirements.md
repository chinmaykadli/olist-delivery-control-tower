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
5. **As the ops lead, I want a seller flagging rule tested on unseen
   months** so I can trust what it catches and see what it wrongly flags.
   - AC: model trained on 2017 only; hit rate at queue cap, lift curve and
     false-alarm share reported for the Jan-May 2018 holdout; label window
     does not overlap the feature window (no leakage). ✅
6. **As the business, I want a monthly order forecast with an honest error
   figure** so planning has a baseline.
   - AC: two candidate baselines compared on a Mar-Aug 2018 holdout; the
     winner and its MAPE reported per scope. ✅
7. **As a dashboard user, I want one page with the headline numbers** so I
   do not need to run code.
   - AC: `docs/index.html` loads from GitHub Pages with all six charts. ✅
8. **As a reviewer, I want to rebuild everything from the README** so the
   work is checkable.
   - AC: four commands from a clean checkout reproduce the dashboard data. ✅
