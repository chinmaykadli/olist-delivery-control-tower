"""Build the operations page (docs/ops.html): peaks and promises, carrier
early warning, lane Pareto, promise curve, the seller exception queue and the
weekly KPI report.

Run after: lanes_analysis.py
Usage: python dashboard/build_ops.py
"""
import json
import pathlib
import sys

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
from page import render  # noqa: E402

OUT, DOCS = ROOT / "outputs", ROOT / "docs"
ln = json.load(open(OUT / "lanes_summary.json"))
weeks = pd.read_csv(OUT / "weekly_promise_vs_late.csv", parse_dates=["purchase_week"])
age = pd.read_csv(OUT / "transit_ageing.csv", parse_dates=["as_of_date"])
age = age[age.handed_10_30d_ago >= 500]          # skip thin early-2017 weeks
deliv = pd.read_csv(OUT / "weekly_late_share_of_deliveries.csv", parse_dates=["delivered_week"])
guard = pd.read_csv(OUT / "guardrail_backtest.csv")
pareto = pd.read_csv(OUT / "lane_pareto.csv")
var = pd.read_csv(OUT / "lane_variability.csv")
curve = pd.read_csv(OUT / "promise_curve.csv")
queue = pd.read_csv(OUT / "exception_queue.csv")
kpis = pd.read_csv(OUT / "weekly_kpis.csv", parse_dates=["purchase_week"])
cens = pd.read_csv(OUT / "censoring_bound.csv")

LATE_RED, OK_BLUE, ACCENT, GREY = "#c0392b", "#2c7fb0", "#e67e22", "#95a5a6"
secs = []


def keep(fig_or_html, title, note):
    h = fig_or_html if isinstance(fig_or_html, str) else pio.to_html(fig_or_html, full_html=False, include_plotlyjs=False)
    secs.append((h, title, note))


def table(df: pd.DataFrame, pct: tuple = (), dec: tuple = ()) -> str:
    df = df.copy()
    for c in pct:
        df[c] = (df[c] * 100).round(1).astype(str) + "%"
    for c in dec:
        df[c] = df[c].round(1)
    return df.to_html(index=False, border=0, escape=True)


# 1. weekly promise vs late
f = go.Figure()
f.add_scatter(x=weeks.purchase_week, y=weeks.late_rate * 100, name="late rate % (purchase week)",
              line=dict(color=LATE_RED, width=2), mode="lines+markers")
f.add_scatter(x=weeks.purchase_week, y=weeks.promised_days, name="avg promised days",
              line=dict(color=OK_BLUE, width=2), mode="lines+markers", yaxis="y2")
f.update_layout(yaxis=dict(title="late rate %"), yaxis2=dict(title="promised days", overlaying="y", side="right"),
                legend=dict(orientation="h", y=1.12), height=380, margin=dict(t=40))
lo, hi = ln["feb_mar_2018_weekly_promise_range"][1], ln["feb_mar_2018_weekly_promise_range"][0]
keep(f, "Promises moved the wrong way in Feb-Mar 2018",
     f"Weekly promises fell from {hi} to {lo} days while the weekly late rate climbed to "
     f"{ln['feb_mar_2018_weekly_late_peak']:.0%}. After Black Friday 2017 promises were widened and lateness fell. "
     "Why promises changed is not in the data.")

# 2. early warning
f = go.Figure()
f.add_scatter(x=age.as_of_date, y=age.share_still_in_transit * 100, name="in-transit ageing % (as of Monday)",
              line=dict(color=ACCENT, width=2))
f.add_scatter(x=deliv.delivered_week, y=deliv.late_share_of_deliveries * 100,
              name="late share of that week's deliveries %", line=dict(color=LATE_RED, width=1.5))
f.add_hline(y=ln["ageing_alarm_threshold"] * 100, line_dash="dash", line_color=GREY,
            annotation_text=f"alarm {ln['ageing_alarm_threshold']:.0%}")
f.update_layout(yaxis=dict(title="%"), legend=dict(orientation="h", y=1.12), height=380, margin=dict(t=40))
keep(f, "Early warning: in-transit ageing leads late deliveries",
     f"Share of parcels handed to the carrier 10-30 days earlier and still undelivered, knowable each Monday. In 2018 it "
     f"crossed {ln['ageing_alarm_threshold']:.0%} on {ln['ageing_first_alarm_2018']}, "
     f"{ln['ageing_lead_weeks_vs_delivered_signal']} weeks before the late share of deliveries passed 10% "
     f"({ln['delivered_late_share_first_10pct_week_2018']}). Threshold set in-sample on two episodes; "
     "the May 2017 alarms preceded only a mild rise.")

# 3. guardrail backtest
f = go.Figure(go.Bar(x=guard.extra_days, y=guard.late_now - guard.late_with_guardrail, marker_color=OK_BLUE))
f.update_layout(xaxis=dict(title="days added to promises in alarm weeks"),
                yaxis=dict(title="late orders avoided"), height=320, margin=dict(t=30))
g5 = ln["guardrail_plus5d"]
keep(f, "Promise guardrail backtest",
     f"Rule: when ageing is at or above {ln['ageing_alarm_threshold']:.0%}, add k days to every promise made that week "
     f"({ln['guardrail_alarm_weeks']} alarm weeks, {g5['orders_covered']:,} orders). +5 days would have turned "
     f"{g5['late_avoided']:,} late orders on time, {g5['share_of_all_window_late_orders']:.0%} of all late orders in the "
     "window. Assumes delivery is unchanged by the promise; conversion cost is not measurable here.")

# 4. lane pareto
top = pareto.head(15).iloc[::-1]
f = go.Figure(go.Bar(y=top.lane, x=top.late_orders, orientation="h", marker_color=LATE_RED,
                     text=(top.late_rate * 100).round(1).astype(str) + "% late", textposition="outside"))
f.update_layout(xaxis=dict(title="late orders", range=[0, top.late_orders.max() * 1.18]),
                height=480, margin=dict(t=30, l=90))
keep(f, "Lane Pareto: rank lanes by late orders, not late rate",
     f"{ln['top2_lanes'][0]} and {ln['top2_lanes'][1]} carry {ln['top2_lanes_share_of_late']:.0%} of late orders; "
     f"{ln['lanes_for_half_of_late']} of {ln['lanes_total']} lanes carry half. "
     f"SP -> RJ is peak-driven: {ln['lane SP -> RJ']['late_normal']:.1%} late in normal months, "
     f"{ln['lane SP -> RJ']['late_peak']:.1%} in peaks.")

keep(table(var.sort_values("orders", ascending=False).head(15)[
    ["lane", "orders", "avg_promised_days", "transit_p50", "transit_p90", "late_rate_normal_months",
     "late_rate_peak_months", "lane_type"]],
    pct=("late_rate_normal_months", "late_rate_peak_months"), dec=("avg_promised_days", "transit_p90")),
    "Lane types: structural vs peak-driven (15 largest lanes)",
    "Structural = 8%+ late even in normal months (fix the promise). Peak-driven = late rate triples in peaks "
    "(fix peak capacity and peak promises). p90/p50 transit shows how unpredictable each lane is.")

# 5. promise curve
f = go.Figure()
for lane, c in [("SP -> AL", LATE_RED), ("SP -> RJ", ACCENT), ("SP -> BA", OK_BLUE), ("ALL LANES", GREY)]:
    sub = curve[curve.lane == lane]
    if len(sub):
        f.add_scatter(x=sub.extra_days, y=sub.on_time_rate * 100, mode="lines+markers", line=dict(color=c),
                      name=f"{lane} (today {sub.avg_promised_days.iloc[0]:.0f}d)")
f.update_layout(xaxis=dict(title="days added to every promise on the lane"), yaxis=dict(title="on-time rate %"),
                legend=dict(orientation="h", y=1.15), height=380, margin=dict(t=40))
al = ln["sp_al_on_time_by_extra_days"]
keep(f, "Promise curve: what each extra day buys",
     f"SP -> AL is {al['0']:.0%} on time at today's {ln['sp_al_promise_today_days']}-day promise; +3 days gives "
     f"{al['3']:.0%}, +5 gives {al['5']:.0%}, and reaching 93% needs +{ln['sp_al_days_to_reach_93pct']} days. Meanwhile the median "
     f"order arrives {ln['median_promise_slack_days_window']:.0f} days early: promises are mis-calibrated, not uniformly short.")

# 6. exception queue
keep(table(queue[["queue_rank", "seller_id", "main_lane", "orders_90d", "late_rate_90d", "breach_90d",
                  "dispatch_90d", "review_90d", "reason_code", "owner", "status"]],
           pct=("late_rate_90d", "breach_90d"), dec=("dispatch_90d", "review_90d")),
     "Seller exception queue: week of 6 Aug 2018",
     "Built from May-Jul 2018 purchases with the one-line rule (trailing late rate). Reason code = first seller-side "
     "failure that applies (shipping-limit breach 25%+, dispatch 5+ days, review 3.5 or less), otherwise the lane or "
     "carrier. Seller IDs are Olist's anonymised hashes.")

# 7. weekly KPI report (last 8 weeks of the window)
keep(table(kpis.tail(8).assign(purchase_week=lambda d: d.purchase_week.dt.date),
           pct=("on_time_rate", "share_1_2_star", "breach_rate_single_seller"),
           dec=("avg_transit_days", "avg_promise_slack_days")),
     "Weekly KPI report (the six numbers)",
     "By purchase week; outcomes as recorded in the final dataset, so in live use the latest weeks would be incomplete.")

# 8. censoring bound
keep(table(cens, pct=("observed_late_rate", "worst_case_late_rate")),
     "Right-censoring check",
     "Worst case: every order still open at the data cut-off counted as late. Jun-Jul 2018 move by about one point at "
     "most, so they are kept; Aug 2018 onwards is excluded.")

html = render(
    title="Olist delivery control tower: operations",
    intro="Peaks and promises, a carrier early-warning signal, lanes ranked by late orders, the promise trade-off "
          "curve and the seller call list. Case study on Olist's public data.",
    cards=[("late orders in peak months", f"{ln['peak_share_of_late_orders']:.0%}"),
           ("early-warning lead (2018)", f"{ln['ageing_lead_weeks_vs_delivered_signal']} weeks"),
           ("late orders avoided, +5d guardrail", f"{g5['late_avoided']:,}"),
           ("top-2 lanes share of late", f"{ln['top2_lanes_share_of_late']:.0%}"),
           ("median days delivered early", f"{ln['median_promise_slack_days_window']:.0f}")],
    sections=secs, active="ops.html")
(DOCS / "ops.html").write_text(html)
print(f"wrote {DOCS / 'ops.html'} ({len(html)/1024:.0f} KB, {len(secs)} sections)")
