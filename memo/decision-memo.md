# Late deliveries: where they come from and what to fix first

**To:** Founder / Head of Marketplace Operations
**From:** Chinmay Kadli
**Data:** Olist public marketplace dataset, delivered orders Sep 2016 - May 2018
(case study; 77,867 orders analysed)

## Decision needed

Approve an 8-week pilot: a weekly seller review queue capped at 20 sellers,
plus recalibrated delivery promises on the three worst routes.
Do not throttle or remove sellers yet.

## Bottom line

- Late delivery is the clearest driver of bad reviews: the share of 1-2 star
  ratings goes from 9% on time to 81% at 8-14 days late.
- Most delay is carrier transit, not seller dispatch (21 extra days vs 3) -
  seller penalties alone cannot fix it.
- The seller early-warning score is not good enough to automate. Use it as a
  conversation queue, not a penalty list.

## What the data shows

On-time rate is 92.5%. Late orders (7.5%, 5,862 orders) run 11.1 days late on
average, against promises that are already generous (25.1 days promised vs
13.4 actual on average).

**Reviews.** Average review by lateness: on time 4.27; 1-3 days late 3.22;
4-7 days 2.08; 8-14 days 1.65. One caveat that matters: the survey goes out
when the estimated date passes, so 76% of late-order reviews were written
before the parcel arrived. Reviews written after delivery average about 3.4
for late orders - still well below the 4.27 on-time average, so lateness
still costs roughly a star, but the headline 1.65 overstates it.

**Where lateness comes from.** Splitting the journey: late orders average
6.0 days from purchase to carrier handover vs 3.1 on time (seller side), but
29.5 days in transit vs 8.5 (carrier side). The worst sellers are real -
the worst 10% of the 511 sellers with 30+ orders run a 19.2% late rate vs
6.8% for the rest - but they cause only 13% of all late orders. And past
lateness persists only at the tail: sellers in the worst 2017 decile ran
17.8% late in 2017 and 14.1% in 2018, still the worst group, while everyone
else sat at 6-12%.

**Routes.** Worst seller-state to customer-state lanes: SP to AL 23.7% late,
MA to SP 20.2%, SP to MA 18.9% - long hauls into the North-East with the
longest transit times and highest freight.

## Options

| Option | Late orders addressed | GMV exposed | Effort | Evidence it works | Main risk |
|---|---|---|---|---|---|
| Do nothing | 0 | none | none | - | review damage continues |
| Review queue (top 20/month) | catches 26% of bad seller-months (hit rate) | none | ~2 ops hrs/week | 1.4x lift vs random on holdout | 3 in 4 flags are false alarms |
| Throttle worst 5% (26 sellers) | 399, about 7% of late orders | R$276k GMV | low | weak: persistence is tail-only | removes sellers for a carrier problem |
| Remove | same as throttle | all their GMV | irreversible | none | irreversible |

## Recommendation

1. **Review queue, capped.** Seller Ops contacts the top-20 scored sellers
   each week, focused on one ask: hand over within the shipping limit. The
   score is a logistic model on trailing-90-day dispatch time, shipping-limit
   breach rate, late rate, review, cancellations and volume - hit rate 26%
   at top-20 vs an 18% base rate on months it was not trained on. Positive,
   weak, honest: a conversation queue, never automation.
2. **Route promises.** On the three worst routes, set customer estimates from
   the historical 80th percentile of delivery time: SP-AL 36 days (today's
   average promise misses a quarter of the time), SP-MA 29, MA-SP 26.
3. **Fix the survey trigger.** Send the satisfaction survey on delivery
   confirmation, not when the estimate passes. 76% of late-order reviews are
   written pre-arrival; that both distorts the metric and invites angry
   ratings the delivery might have softened.
4. **Data fixes.** Assign owners for the five defects the quality checks
   found (775 orders with no items, 443 payment mismatches, 610 uncategorised
   products, 8 missing delivery dates, 646 delivered orders with no review).

## Pilot design (8 weeks)

- Randomise flagged sellers into contact vs no-contact.
- Primary metric: shipping-limit breach rate and late rate over 60 days.
- Sizing: detecting a drop from 16% to 12% late needs ~1,200 orders per arm
  (two-proportion test, 80% power); seller clustering raises that, so treat
  as a floor.
- Scale only if the contacted group improves and good sellers' satisfaction
  holds.

## Cost of acting (assumptions labelled)

- Ops time: ~10 minutes per seller call x 20/week (assumption).
- Marketplace take rate: not in the dataset - R$276k is GMV exposed by the
  throttle option, never revenue saved.
- Longer promises on bad routes may cut conversion; not measurable here.
  Mitigation: pilot on one route first.

## Risks

- 3 in 4 queue flags are false alarms - keep it a conversation.
- Longer promises may hurt conversion.
- The data ends mid-2018; Jun-Aug 2018 excluded as right-censored.
- Associations, not causes: review scores have drivers beyond delivery.
- One country, 2016-2018: the method transfers, the numbers may not.

## KPI tree

- North star: share of 1-2 star reviews.
  - On-time rate against promise.
    - Seller shipping-limit breach rate (seller).
    - Transit days by route (carrier).
    - Promise accuracy (platform).
- Guardrails: GMV, seller retention.

The weekly report is these six numbers.

## What to watch next

Repeat-purchase behaviour by customers whose first order was late (deferred -
repeat buying is rare in this data, may be too small to measure); carrier
identity, which this dataset does not include and which would turn the
transit finding into a carrier scorecard.
