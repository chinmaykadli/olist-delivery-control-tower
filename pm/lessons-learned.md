# Lessons learned

1. **The backtest is the deliverable, not the rule.** The first scorecard
   flagged 46% of seller-months at 1.2x lift. The rebuilt logistic queue is
   better (1.4x at top-20) but still weak - and saying so, with a lift curve,
   is the analysis. A weak rule shipped as automation would have burned
   seller trust.
2. **Follow the delay, not the org chart.** The project started as "which
   sellers are bad" and the data said "mostly the carrier". The memo leads
   with where the delay physically sits (dispatch 3 extra days, transit 21).
3. **Check your evaluation before your model.** Right-censoring depressed
   the final months' late rates - which were also the holdout. Cut the
   window at May 2018.
4. **Circular significance tests fool people.** Ranking sellers by late rate
   and then testing whether the top decile has a high late rate proves
   nothing. Persistence (worst 2017 decile measured in 2018) is the honest
   version - and it shows real, tail-only persistence.
5. **Read the survey instrument.** 76% of late-order reviews were written
   before the parcel arrived. The metric was partly measuring a survey
   trigger, not just delivery.
6. **Check seasonality before trusting seasonal models.** The YoY model
   overshot 50-290% on a ramp-up base year; naive and moving-average
   baselines won on holdout MAPE.
7. **Data quality findings belong in the plan.** Five of eleven checks found
   real issues; each changed a metric or the memo.

## Close-out: plan vs actual
| Item | Planned | Actual | Variance |
|---|---|---|---|
| Build effort | 30-40h over 4 weeks | core build + peer-review rebuild in 2 days | ahead of baseline |
| Forecast MAPE (all orders) | < 15% | 4.3% (naive, Mar-May 2018) | ahead |
| Scorecard | exploratory | 1.4x lift at top-20 | reported honestly, recommendation adjusted |
