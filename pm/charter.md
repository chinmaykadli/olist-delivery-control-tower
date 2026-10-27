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
**In:** delivered orders in the Olist public dataset (Sep 2016 - Aug 2018);
SQL metric layer; seller scorecard with out-of-time backtest; monthly order
forecast; static dashboard; decision memo; this PM pack.
**Out:** geolocation/mapping analysis (state level is enough); NLP on review
text; real-time alerting; any claim that Olist is an employer or client.

## Success measures
| Measure | Target | Result |
|---|---|---|
| Every memo number traces to a SQL view | 100% | met (see UAT log) |
| Early-warning score reports hit rate, lift AND false alarms | all three | met: 26% hit at top-20 vs 18% base, 1.4x lift, on 2018 holdout |
| Stranger can rebuild from README | four commands | met (verified on a clean rebuild) |
| Plan vs actual compared at close | close-out section | met (pm/lessons-learned.md) |

## Constraints
- Public data only (Olist Brazilian E-Commerce, Kaggle). No employer data.
- Free tooling: DuckDB, Python, Plotly, GitHub Pages. No paid BI licence.
- macOS: Power BI Desktop is Windows-only, so the dashboard is a static
  Plotly site served from this repo (same result, cloneable).

## Assumptions
- "Late" = delivered to the customer on a later calendar date than the
  estimated delivery date (the estimate has no time component).
- "OTIF" = not late; item-level cancellation data does not exist, so
  "in full" is assumed.
- Revenue-at-risk figures in the memo are labelled assumptions with
  low/high cases; the dataset has no take-rate or contract terms.
