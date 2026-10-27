# Lessons learned

1. **The backtest is the deliverable, not the rule.** The first scorecard
   flagged 46% of seller-months at 1.2x lift. The rebuilt call list hits 34%
   against a 21% base (1.59x) on Jan-Jul 2018, and a one-line sort does as
   well as a 5-feature model. Shipping the simple rule, with the model as the
   comparison, is the analysis.
2. **Follow the delay, not the org chart.** The project started as "which
   sellers are bad". The data said "mostly the carrier, mostly in peaks", and
   that in peaks the marketplace shortened promises while carriers slowed.
3. **Check the label before the model.** Seller-months with 1-4 orders had
   been labelled "good" by default, which understated the base rate. They are
   now dropped as too thin to judge.
4. **Justify exclusions with data, not with the number that looks odd.** Jun
   2018's low late rate was first treated as censoring. Counting open orders
   showed the worst case moves June by under one point, so Jun-Jul 2018 are
   back in the window and the headline moved from 7.5% to 6.8%.
5. **Circular significance tests fool people.** Ranking sellers by late rate
   and then testing the top decile proves nothing. Year-on-year persistence
   (Spearman 0.28) is the honest version.
6. **Read the data dictionary for every timestamp.** `review_creation_date` is
   when the survey was sent; `review_answer_timestamp` is when the customer
   answered. The pre-delivery share is 72% on the right field.
7. **Rank by volume x rate.** Lanes ranked by late rate pointed at small lanes;
   ranked by late orders, two lanes carry 38% of the problem.
8. **Power the pilot before promising one.** At about 15 orders per seller in
   60 days, a seller-level experiment needs 136 sellers per arm. The plan now
   says so instead of implying an 8-week answer.
9. **Automate the trace.** `scripts/check_numbers.py` fails the build when a
   quoted number drifts from `outputs/`; it caught stale figures on the
   dashboard that had been typed in by hand.

## Close-out: plan vs actual
| Item | Planned | Actual | Variance |
|---|---|---|---|
| Forecast MAPE (all orders) | < 15% | 5.4% (naive, Mar-Jul 2018 holdout) | met |
| Seller call list | exploratory | 1.59x lift at 20/month, CI excludes random | reported with CI; simple rule shipped |
| Number traceability | manual UAT | automated (check_numbers.py) | improved |
