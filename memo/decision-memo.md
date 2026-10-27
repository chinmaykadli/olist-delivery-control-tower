# Late deliveries: where they come from and what to fix first

**To:** Founder / Head of Marketplace Operations
**From:** Chinmay Kadli
**Data:** Olist public marketplace dataset, delivered orders Sep 2016 - Jul 2018
(case study; 90,119 orders analysed, 6.8% late)

## Decision needed

Approve three changes, in this order:

1. **Peak-aware promises with a guardrail:** widen delivery promises ahead of
   known peaks, and automatically when in-transit ageing crosses 20%.
2. **A 20-seller monthly call list** ranked by trailing late rate, run by
   Seller Ops (about 5 calls a week).
3. **Send the review survey on delivery confirmation**, not when the estimate
   passes.

Do not throttle or remove sellers.

## Bottom line

- Lateness is a peak problem first: three months hold 23% of orders but 51%
  of late orders, and in those months promises got shorter while carriers got
  slower.
- Most delay is carrier transit, not seller dispatch (21 extra days vs 3), so
  seller penalties alone cannot fix it.
- The seller call list works modestly (1.59x random) and a one-line rule does
  as well as a model. It is a conversation list, not a penalty list.

## What the data shows

**Peaks.** Peak months (rule: marketplace late rate of 10% or more) were Nov
2017, Feb 2018 and Mar 2018. In peaks the average promise was 23.6 days
against 25.3 normally, while transit took 12.5 days against 8.7. In Feb-Mar
2018 weekly promises fell from 27.7 to 22.9 days as the weekly late rate
climbed to 26%. Why promises changed is not in the data.

**Early warning.** The share of parcels handed over 10-30 days ago and still
undelivered, knowable every Monday, crossed 20% on 2018-02-19, 3 weeks before
the late share of deliveries passed 10%.

**Where lateness comes from.** Late orders take 6.0 vs 3.1 days from purchase
to carrier handover, but 29.2 vs 8.1 days in transit. The worst 10%
of the 581 sellers with 30+ orders run 17.2% late against 6.2% for the rest,
and account for 13% of all late orders. Year-on-year persistence is moderate
(Spearman 0.28 across 260 sellers).

**Lanes.** Two lanes (SP -> SP and SP -> RJ) carry 38% of late orders.
SP -> RJ is peak-driven: 7.5% late in normal months, 37.7% in peaks. SP -> AL
is structural: only 75% on time at today's 32.9-day promise.

**Promises.** The median order arrives 13 days early, yet long and peak lanes
miss. Promises are mis-calibrated, not uniformly short.

**Reviews and repeat purchase.** 72% of late-order reviews were answered
before the parcel arrived. Late orders reviewed after arrival average 3.69
stars against 4.28 on time. Customers whose first order was late repeat at
2.92% vs 4.05% (adjusted odds ratio 0.80, 95% CI 0.65 to 0.97): roughly 29
lost repeat orders. The cost of lateness shows up in reviews far more than in
measurable repeat revenue.

## Options

| Option | Late orders addressed | GMV exposed | Effort | Evidence it works | Main risk |
|---|---|---|---|---|---|
| Do nothing | 0 | none | none | - | review damage continues each peak |
| Promise guardrail (+5 days in alarm weeks) | 727 late orders in backtest, 12% of all late orders | none | promise logic change | backtest on 13 alarm weeks | longer promises may cut conversion (not measured) |
| Seller call list (20/month) | 34% of listed sellers turn bad vs 21% random | none | about 3 ops hours/month | out-of-time backtest, 1.59x lift | 2 in 3 calls go to sellers who would have been fine |
| Throttle worst 5% (30 sellers) | 440, about 7% of late orders | R$310k GMV | low | weak: persistence is moderate | removes sellers for a mostly carrier problem |
| Remove | same as throttle | all their GMV | irreversible | none | irreversible |

## Recommendation

1. **Promises.** Widen promises ahead of the Black Friday peak, and add a
   guardrail: when in-transit ageing is at or above 20% on a Monday, add days
   to new promises that week and block promise cuts. Start with +3 days (469
   late orders avoided in the backtest) and review conversion weekly. On
   structural lanes such as SP -> AL, test +3 days (75% -> 78% on time); reaching
   93% would need +12 days, which is a commercial decision, not an analytical one.
2. **Seller call list.** Seller Ops calls the top 20 sellers each month by
   trailing 90-day late rate, with a reason code (shipping-limit breach, slow
   handover, low reviews, or lane/carrier). The one-line rule was chosen on
   2017 and tested on Jan-Jul 2018: 34% of listed sellers turned bad
   (95% CI 26% to 42%) against a 21% base. A 5-feature model did no better.
3. **Survey trigger.** Send the satisfaction survey on delivery confirmation.
   This changes the measurement, not the experience, so judge it on delivery
   times and repeat purchase, not on the review score.
4. **Data fixes.** Assign owners for the defects the quality checks found (775
   orders with no items, 443 payment mismatches, 610 uncategorised products,
   20 carrier handovers after delivery, 646 delivered orders with no review).

## Pilot design

- **Promise guardrail:** run on one peak-driven lane (SP -> RJ) first, with a
  matched lane as comparison; primary metric on-time rate, guardrail metric
  conversion.
- **Seller call list:** randomise listed sellers into call vs no call. Power
  is the constraint: within-seller correlation (ICC 0.024) and about 15 orders
  per seller in 60 days mean detecting a drop from 12.8% to 9.6% late needs
  136 sellers per arm, about 14 months of intake at 10 per arm per month. An
  8-week pilot can only detect a drop to 5.3%. So run the call list as
  standard practice with monitoring, and test on the shipping-limit breach
  rate, which moves faster, rather than claim a powered experiment.
- Write the scale or stop rule down before the pilot starts.

## Cost of acting (assumptions labelled)

- Ops time: about 10 minutes per seller call x 20 a month (assumption).
- Longer promises may cut conversion; the data has no conversion figures.
- Take rate and margin are not in the data: GMV exposed is reported, never
  revenue saved.

## Risks

- The 20% ageing threshold was set in-sample on two episodes.
- Promise backtests assume delivery times do not change with the promise.
- Associations, not causes; carrier identity is not in the data.
- One country, 2016-2018: the method transfers, the numbers may not.

## KPI tree

- North star: share of 1-2 star reviews.
  - On-time rate against promise.
    - In-transit ageing (carrier, leading).
    - Transit days by lane (carrier).
    - Seller shipping-limit breach rate (seller).
    - Promise slack (platform calibration).
- Guardrails: GMV, conversion (when available), seller retention.

The weekly report is in `outputs/weekly_kpis.csv` and on the operations dashboard.
