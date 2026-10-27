"""Build the findings page (docs/index.html) from the analysis outputs.

Every number in a chart note is read from outputs/*.json, never typed in.
Run after: build_db.py, run_analysis.py, scorecard_backtest.py, lanes_analysis.py
Usage: python dashboard/build_dashboard.py
"""
import json
import pathlib
import sys

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
from page import render  # noqa: E402

OUT, DOCS = ROOT / "outputs", ROOT / "docs"
kpi = json.load(open(OUT / "kpi_summary.json"))
sc = json.load(open(OUT / "scorecard_summary.json"))
ln = json.load(open(OUT / "lanes_summary.json"))
con = duckdb.connect(str(ROOT / "olist.duckdb"), read_only=True)
monthly = con.execute("""SELECT m.*, f.is_peak FROM v_monthly_metrics m JOIN v_month_flags f USING (purchase_month)
                         WHERE m.purchase_month >= DATE '2017-01-01' ORDER BY 1""").df()
review_band = pd.read_csv(OUT / "review_vs_lateness.csv")
seller_perf = pd.read_csv(OUT / "seller_performance.csv")
comparison = pd.read_csv(OUT / "scorecard_comparison.csv")
dt = pd.read_csv(OUT / "dispatch_vs_transit.csv")

LATE_RED, OK_BLUE, ACCENT, GREY = "#c0392b", "#2c7fb0", "#e67e22", "#95a5a6"
figs = []


def keep(fig, title, note):
    figs.append((pio.to_html(fig, full_html=False, include_plotlyjs=False), title, note))


# --- peaks: late rate by month with peak months marked
f = go.Figure()
f.add_bar(x=monthly.purchase_month, y=monthly.late_rate * 100, name="late rate %",
          marker_color=[LATE_RED if p else GREY for p in monthly.is_peak])
f.add_scatter(x=monthly.purchase_month, y=monthly.avg_promised_days, name="avg promised days",
              line=dict(color=OK_BLUE, width=2), mode="lines+markers", yaxis="y2")
f.update_layout(yaxis=dict(title="late rate %"), yaxis2=dict(title="promised days", overlaying="y", side="right"),
                legend=dict(orientation="h", y=1.12), height=380, margin=dict(t=40))
keep(f, "Lateness is a peak problem first",
     f"Peak months (red; rule: marketplace late rate of 10% or more) hold {ln['peak_share_of_orders']:.0%} of orders "
     f"but {ln['peak_share_of_late_orders']:.0%} of late orders. In peaks the average promise was "
     f"{ln['promise_days_normal_vs_peak'][1]} days against {ln['promise_days_normal_vs_peak'][0]} normally, while "
     f"transit took {ln['transit_days_normal_vs_peak'][1]} days against {ln['transit_days_normal_vs_peak'][0]}.")

# --- where the delay sits
d_on, d_late = dt[dt.is_late == False].iloc[0], dt[dt.is_late == True].iloc[0]
f = go.Figure()
f.add_bar(x=["dispatch (purchase -> carrier)", "transit (carrier -> customer)"],
          y=[d_on.avg_dispatch, d_on.avg_transit], name="on-time orders", marker_color=OK_BLUE)
f.add_bar(x=["dispatch (purchase -> carrier)", "transit (carrier -> customer)"],
          y=[d_late.avg_dispatch, d_late.avg_transit], name="late orders", marker_color=LATE_RED)
f.update_layout(barmode="group", yaxis=dict(title="average days"),
                legend=dict(orientation="h", y=1.12), height=360, margin=dict(t=40))
keep(f, "Where the delay sits: mostly with the carrier",
     f"Late orders wait {d_late.avg_dispatch - d_on.avg_dispatch:.0f} extra days for handover but spend "
     f"{d_late.avg_transit - d_on.avg_transit:.0f} extra days in transit. Seller penalties alone cannot fix lateness.")

# --- review vs lateness with answer-timing split
f = go.Figure()
f.add_bar(x=review_band.lateness_band.astype(str), y=review_band.avg_review_answered_after_delivery,
          name="answered after delivery", marker_color=OK_BLUE)
f.add_bar(x=review_band.lateness_band.astype(str), y=review_band.avg_review_answered_before_delivery,
          name="answered before delivery", marker_color=ACCENT)
f.update_layout(barmode="group", yaxis=dict(title="avg review score", range=[0, 5]),
                xaxis=dict(title="delivery vs estimate"), legend=dict(orientation="h", y=1.15),
                height=380, margin=dict(t=40))
keep(f, "Later delivery, lower reviews, but most late reviews come before the parcel",
     f"{kpi['late_reviews_answered_before_delivery']:.0%} of late-order reviews were answered before delivery "
     f"(the survey is sent when the estimate passes). Late orders reviewed after arrival average "
     f"{kpi['avg_review_late_answered_after_delivery']} stars (n={kpi['n_late_answered_after_delivery']:,}) "
     f"against {kpi['avg_review_on_time']} on time. Customers who wait to answer may differ from those who do not.")

# --- seller pareto
sp = seller_perf.sort_values("late_orders", ascending=False).reset_index(drop=True)
cum = sp.late_orders.cumsum() / sp.late_orders.sum() * 100
f = go.Figure()
f.add_scatter(x=(sp.index + 1) / len(sp) * 100, y=cum, mode="lines", line=dict(color=OK_BLUE, width=2))
f.add_vline(x=10, line_dash="dash", line_color=LATE_RED)
f.update_layout(xaxis=dict(title="% of sellers (ranked by late orders)"),
                yaxis=dict(title="cumulative % of late orders", range=[0, 100]), height=340, margin=dict(t=30))
top10_by_count = float(cum.iloc[int(len(sp) * 0.10) - 1])
keep(f, "Seller concentration is real but modest",
     f"Ranked by late-order COUNT (chart), the top 10% of these sellers carry {top10_by_count:.0f}% of their late "
     f"orders. Ranked by late RATE, among "
     f"{kpi['sellers_analysed_min30_orders']} sellers with 30+ orders the worst 10% run "
     f"{kpi['worst_10pct_late_rate']:.1%} late against {kpi['rest_late_rate']:.1%} for the rest, and account for "
     f"{kpi['worst_10pct_sellers_share_of_all_late_orders']:.0%} of all late orders. Year-on-year persistence is "
     f"moderate (Spearman {ln['persistence_spearman'][0]} across {ln['persistence_spearman'][1]} sellers).")

# --- queue rules vs model
k20 = comparison[comparison.k == sc["queue_cap_per_month"]]
f = go.Figure(go.Bar(x=k20.rule, y=k20.hit_rate * 100, marker_color=[OK_BLUE, "#16a085", GREY],
                     error_y=dict(type="data", symmetric=False, array=(k20.ci_high - k20.hit_rate) * 100,
                                  arrayminus=(k20.hit_rate - k20.ci_low) * 100)))
f.add_hline(y=sc["test_base_rate"] * 100, line_dash="dash", line_color=LATE_RED,
            annotation_text=f"base rate {sc['test_base_rate']:.0%}")
f.update_layout(yaxis=dict(title="hit rate % at 20 sellers a month (95% CI)"), height=360, margin=dict(t=30))
keep(f, "Who to call: a one-line sort is as good as the model",
     f"Jan-Jul 2018 holdout. The queue ({sc['queue_rule']}, chosen on 2017 only) hits "
     f"{sc['queue_hit_rate_at_k']:.0%} (95% CI {sc['queue_hit_rate_ci'][0]:.0%} to {sc['queue_hit_rate_ci'][1]:.0%}) "
     f"against a {sc['test_base_rate']:.0%} base, {sc['queue_lift_at_k']}x random. The 5-feature logistic model "
     f"hits {sc['model_hit_rate_at_k']:.0%}. Good enough to decide who gets a call; never for throttling.")

html = render(
    title="Olist delivery control tower: findings",
    intro="Where do late deliveries come from, what do they cost, and what would catch problems early? "
          "A case study on Olist's public Brazilian marketplace dataset. Every number rebuilds from the repo's SQL and Python.",
    cards=[("orders analysed", f"{kpi['orders_analysed']:,}"), ("late rate", f"{kpi['late_rate']:.1%}"),
           ("late orders in peak months", f"{ln['peak_share_of_late_orders']:.0%}"),
           ("avg review", f"{kpi['avg_review']}"),
           ("delivery vs promise", f"{kpi['avg_delivery_days']}d vs {kpi['avg_promised_days']}d"),
           ("window", kpi["analysis_window"])],
    sections=figs, active="index.html")
(DOCS / "index.html").write_text(html)
print(f"wrote {DOCS / 'index.html'} ({len(html)/1024:.0f} KB, {len(figs)} charts)")
