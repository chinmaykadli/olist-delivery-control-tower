# Project charter — Supplier & delivery control tower

**Sponsor (case-study role):** marketplace operations lead
**Project manager / analyst:** Chinmay Kadli
**Date:** 27 Oct 2026 · **Status:** delivered (analysis build); close-out review pending

> Case-study note: stakeholder roles are simulated for portfolio purposes.
> The data, code and numbers are real and reproducible from this repo.

## Problem
A marketplace sells through ~3,000 third-party sellers. Some sellers let
customers down — late deliveries, bad reviews — but operations cannot say
which sellers, what it costs, or what to do about it. Today there is no
shared definition of "late", no seller-level view, and no early-warning rule.

## Goal
One question, three answers:
1. Where do late deliveries come from (seller, category, route)?
2. What do they cost (review damage, revenue at risk)?
3. What rule catches a problem seller early — and how good is that rule
   really, tested on months it was not tuned on?

## Scope
**In:** delivered orders in the Olist public dataset (purchases Sep 2016 - Jul 2018);
SQL metric layer; seller scorecard with out-of-time backtest; monthly order
forecast; peak, lane and promise analysis with a carrier early-warning
signal; two static dashboard pages; decision memo; this PM pack.
**Out:** geolocation/mapping analysis (state level is enough); NLP on review
text; live alerting (the early-warning signal is backtested, not deployed); any claim that Olist is an employer or client.

## Success measures
| Measure | Target | Result |
|---|---|---|
| Every memo number traces to a SQL view | 100% | met (see UAT log) |
| Seller call list reports hit rate, lift, CI AND a simple baseline | all four | met: 34% hit at 20/month vs 21% base (95% CI 26% to 42%), 1.59x; one-line rule = model, on Jan-Jul 2018 holdout |
| Stranger can rebuild from README | one command (`make all`) | met (verified on a clean rebuild) |
| Every quoted number checked automatically | 0 mismatches | met (`scripts/check_numbers.py`) |
| Plan vs actual compared at close | close-out section | met (pm/lessons-learned.md) |

## Constraints
- Public data only (Olist Brazilian E-Commerce, Kaggle). No employer data.
- Free tooling: DuckDB, Python, Plotly, GitHub Pages. No paid BI licence.
- macOS: Power BI Desktop is Windows-only, so the dashboard is a static
  Plotly site served from this repo (same result, cloneable).

## Assumptions
- "Late" = delivered to the customer on a later calendar date than the
  estimated delivery date (the estimate has no time component).
- On-time rate = 1 - late rate. "In full" is not measurable (no item-level
  fulfilment data), so the project does not report OTIF.
- GMV figures are exposure, never revenue saved; the dataset has no take
  rate or margin. Promise backtests assume delivery times do not change
  with the promise.
