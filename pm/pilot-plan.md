# Pilot plan - seller review queue + route promises

The recommended 8-week pilot from the decision memo. Gantt and RACI describe
the ROLLOUT (the thing a founder would run), not the analysis build.

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b
    section Setup
    Confirm queue SOP + contact script      :a1, 2026-11-02, 3d
    Randomise flagged sellers to arms       :a2, 2026-11-04, 2d
    Baseline metrics snapshot               :a3, 2026-11-02, 5d
    section Pilot (8 weeks)
    Weekly top-20 seller contacts           :b1, 2026-11-09, 56d
    Route promise change (SP-AL first)      :b2, 2026-11-16, 14d
    Survey trigger change spec              :b3, 2026-11-23, 14d
    Weekly KPI report (6 numbers)           :b4, 2026-11-09, 56d
    section Review
    Mid-pilot check (week 4)                :milestone, 2026-12-04, 0d
    Readout + scale/stop decision           :milestone, 2027-01-04, 0d
```

## RACI

Roles: Seller Ops (contacts sellers), Logistics (carrier + routes), CX
(reviews, survey), Data (score, KPI report), Founder/Head of Marketplace
(decision).

| Activity | Seller Ops | Logistics | CX | Data | Founder |
|---|---|---|---|---|---|
| Weekly queue contacts | R/A | I | I | C | I |
| Route promise recalibration | I | R/A | C | C | A |
| Survey trigger change | I | I | R/A | C | A |
| Score refresh + lift monitoring | I | I | I | R/A | I |
| KPI weekly report | C | C | C | R/A | I |
| Scale/stop decision | C | C | C | C | R/A |

## Sizing note

Detecting a late-rate drop from 16% to 12% needs ~1,200 orders per arm
(two-proportion test, 80% power). Seller clustering raises this; treat as a
floor and report power with the readout.
