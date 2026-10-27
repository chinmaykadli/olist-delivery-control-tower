"""Build the static dashboard (docs/index.html) from the analysis outputs.

Self-contained HTML with Plotly charts, served via GitHub Pages.
Run after: build_db.py, run_analysis.py, scorecard_backtest.py
Usage: python dashboard/build_dashboard.py
"""
import json
import pathlib

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT, DOCS = ROOT / "outputs", ROOT / "docs"
WINDOW_END = "2018-05-01"

kpi = json.load(open(OUT / "kpi_summary.json"))
sc = json.load(open(OUT / "scorecard_summary.json"))
con = duckdb.connect(str(ROOT / "olist.duckdb"), read_only=True)
monthly = con.execute(
    "SELECT * FROM v_monthly_metrics WHERE purchase_month BETWEEN '2017-01-01' AND ? ORDER BY 1",
    [WINDOW_END]).df()
forecast = pd.read_csv(OUT / "forecast_vs_actual.csv", parse_dates=["month"])
review_band = pd.read_csv(OUT / "review_vs_lateness.csv")
by_route = pd.read_csv(OUT / "late_by_route.csv")
seller_perf = pd.read_csv(OUT / "seller_performance.csv")
lift = pd.read_csv(OUT / "scorecard_lift.csv")
dt = pd.read_csv(OUT / "dispatch_vs_transit.csv")
pers = pd.read_csv(OUT / "seller_persistence.csv")

LATE_RED, OK_BLUE, ACCENT, GREY = "#c0392b", "#2c7fb0", "#e67e22", "#95a5a6"
figs = []

def keep(fig, title, note):
    figs.append((pio.to_html(fig, full_html=False, include_plotlyjs=False), title, note))

# --- where the delay sits
f = go.Figure()
f.add_bar(x=["dispatch (seller -> carrier)", "transit (carrier -> customer)"],
          y=[dt.loc[dt.is_late == False].avg_dispatch.iloc[0], dt.loc[dt.is_late == False].avg_transit.iloc[0]],
          name="on-time orders", marker_color=OK_BLUE)
f.add_bar(x=["dispatch (seller -> carrier)", "transit (carrier -> customer)"],
          y=[dt.loc[dt.is_late == True].avg_dispatch.iloc[0], dt.loc[dt.is_late == True].avg_transit.iloc[0]],
          name="late orders", marker_color=LATE_RED)
f.update_layout(barmode="group", yaxis=dict(title="average days"),
                legend=dict(orientation="h", y=1.12), height=380, margin=dict(t=40))
keep(f, "Where the delay sits: mostly the carrier, not the seller",
     "Late orders spend 3 extra days waiting for the seller to hand over, but 21 extra days in transit. "
     "Seller penalties alone cannot fix lateness - the memo leads with this.")

# --- control tower: late rate & review trend
f = go.Figure()
f.add_scatter(x=monthly.purchase_month, y=monthly.late_rate * 100, name="late rate %",
              line=dict(color=LATE_RED, width=2), mode="lines+markers")
f.add_scatter(x=monthly.purchase_month, y=monthly.avg_review, name="avg review",
              line=dict(color=OK_BLUE, width=2), mode="lines+markers", yaxis="y2")
f.update_layout(yaxis=dict(title="late rate %", rangemode="tozero"),
                yaxis2=dict(title="avg review", overlaying="y", side="right", range=[3.4, 4.6]),
                legend=dict(orientation="h", y=1.12), height=380, margin=dict(t=40))
keep(f, "Late rate and review score by month",
     "Window ends May 2018: later months are right-censored (their late orders were still in transit "
     "at the data cut-off). March 2018's 19% spike is real, not censoring.")

# --- review vs lateness with survey-timing split
f = go.Figure()
f.add_bar(x=review_band.lateness_band.astype(str), y=review_band.avg_review_written_after_delivery,
          name="review written after delivery", marker_color=OK_BLUE)
f.add_bar(x=review_band.lateness_band.astype(str), y=review_band.avg_review_written_before_delivery,
          name="review written before delivery", marker_color=ACCENT)
f.add_hline(y=kpi["avg_review"], line_dash="dash", line_color=LATE_RED,
            annotation_text=f"all-order average {kpi['avg_review']}")
f.update_layout(barmode="group", yaxis=dict(title="avg review score", range=[0, 5]),
                xaxis=dict(title="delivery vs estimate"), legend=dict(orientation="h", y=1.18),
                height=400, margin=dict(t=40))
keep(f, "Later delivery, lower reviews - with the survey-timing split",
     "76% of late-order reviews were written BEFORE the parcel arrived (the survey goes out when the "
     "estimated date passes). Written after delivery, late orders average about 3.4 stars, not 2.2. "
     "Recommendation: trigger the survey on delivery confirmation, not on the estimate.")

# --- seller pareto
sp = seller_perf.sort_values("late_orders", ascending=False).reset_index(drop=True)
cum = sp.late_orders.cumsum() / sp.late_orders.sum() * 100
f = go.Figure()
f.add_scatter(x=(sp.index + 1) / len(sp) * 100, y=cum, mode="lines",
              line=dict(color=OK_BLUE, width=2), name="cumulative share")
f.add_vline(x=10, line_dash="dash", line_color=LATE_RED,
            annotation_text=f"worst 10% = {kpi['worst_10pct_sellers_share_of_all_late_orders']:.0%} of ALL late orders")
f.update_layout(xaxis=dict(title="% of sellers (ranked by late orders)"),
                yaxis=dict(title="cumulative % of late orders", range=[0, 100]),
                height=380, margin=dict(t=40))
keep(f, "Seller concentration is real but modest",
     f"Among {kpi['sellers_analysed_min30_orders']} sellers with 30+ orders, the worst 10% run a "
     f"{kpi['worst_10pct_late_rate']:.1%} late rate vs {kpi['rest_late_rate']:.1%} for the rest - but they "
     f"cause only {kpi['worst_10pct_sellers_share_of_all_late_orders']:.0%} of all late orders. "
     "Persistence check: the worst 2017 decile cooled from 17.1% to 11.5% in 2018 (still above the 5-8% field).")

# --- scorecard lift
f = go.Figure()
f.add_scatter(x=lift.k, y=lift.hit_rate * 100, mode="lines+markers",
              line=dict(color=OK_BLUE, width=2), name="queue hit rate")
f.add_hline(y=sc["test_base_rate"] * 100, line_dash="dash", line_color=LATE_RED,
            annotation_text=f"base rate {sc['test_base_rate']:.1%} (random pick)")
f.update_layout(xaxis=dict(title="queue cap K (sellers flagged per month)"),
                yaxis=dict(title="hit rate %"),
                legend=dict(orientation="h", y=1.12), height=380, margin=dict(t=40))
keep(f, "Early-warning score: honest lift on the 2018 holdout",
     f"Logistic model on trailing-90-day dispatch, breach, late rate, review, cancellations and volume; "
     f"trained on 2017, tested on Jan-May 2018. Top-20 monthly queue: {sc['queue_hit_rate_at_k']:.0%} hit rate "
     f"vs {sc['test_base_rate']:.0%} base ({sc['queue_lift_at_k']}x lift). Positive but weak - good enough for a "
     "weekly conversation queue, never for automatic throttling.")

# --- routes
rt = by_route.head(15).iloc[::-1]
f = go.Figure(go.Bar(y=rt.seller_state + " -> " + rt.customer_state, x=rt.late_rate * 100,
                     orientation="h", marker_color=LATE_RED,
                     text=(rt.late_rate * 100).round(1).astype(str) + "%", textposition="outside"))
f.update_layout(xaxis=dict(title="late rate %"), height=480, margin=dict(t=40, l=90))
keep(f, "Worst seller-state to customer-state routes (100+ orders)",
     "Long-haul routes out of Sao Paulo to the North-East dominate late deliveries. "
     "Memo recommendation: recalibrate delivery promises on these routes to the historical 80th percentile.")

# ------------------------------------------------------------------- page
cards = "".join(
    f'<div class="card"><div class="k">{v}</div><div class="l">{k}</div></div>'
    for k, v in [
        ("orders analysed", f"{kpi['orders_analysed']:,}"),
        ("late rate", f"{kpi['late_rate']:.1%}"),
        ("on-time rate", f"{kpi['on_time_rate']:.1%}"),
        ("avg review", f"{kpi['avg_review']}"),
        ("delivery vs promise", f"{kpi['avg_delivery_days']}d vs {kpi['avg_promised_days']}d"),
        ("window", kpi["analysis_window"]),
    ])
sections = "".join(
    f'<section><h2>{t}</h2><p class="note">{n}</p>{h}</section>' for h, t, n in figs)

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Olist supplier &amp; delivery control tower</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin: 0; color: #1c2833; background: #f7f9fa; }}
 header {{ background: #1c2833; color: #fff; padding: 28px 32px; }}
 header h1 {{ margin: 0 0 6px; font-size: 22px; }}
 header p {{ margin: 0; opacity: .8; font-size: 14px; max-width: 900px; }}
 main {{ max-width: 1000px; margin: 0 auto; padding: 24px 16px 60px; }}
 .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 18px 0 8px; }}
 .card {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; padding: 12px 14px; }}
 .card .k {{ font-size: 19px; font-weight: 700; }}
 .card .l {{ font-size: 12px; color: #5d6d7e; margin-top: 2px; }}
 section {{ background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; padding: 18px 20px; margin-top: 18px; }}
 h2 {{ font-size: 17px; margin: 0 0 4px; }}
 .note {{ font-size: 13px; color: #5d6d7e; margin: 0 0 8px; }}
 footer {{ text-align: center; font-size: 12px; color: #7f8c8d; padding: 20px; }}
 a {{ color: {OK_BLUE}; }}
</style></head>
<body>
<header>
  <h1>Olist supplier &amp; delivery control tower</h1>
  <p>Where do late deliveries come from, what do they cost, and what rule would catch a problem seller early?
     A portfolio case study on Olist's public Brazilian marketplace dataset (about 100k real orders, 2016-2018).
     Every chart rebuilds from the repo's SQL and Python.</p>
</header>
<main>
  <div class="cards">{cards}</div>
  {sections}
</main>
<footer>Built with DuckDB, Python and Plotly. Data:
<a href="https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce">Olist Brazilian E-Commerce (Kaggle)</a>.
Case study - not work performed for Olist or any employer.</footer>
</body></html>"""

(DOCS / "index.html").write_text(html)
print(f"wrote {DOCS / 'index.html'} ({len(html)/1024:.0f} KB, {len(figs)} charts)")
