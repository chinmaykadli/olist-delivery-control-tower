"""Core analysis for the Olist supplier & delivery control tower.

Reads the DuckDB views built by build_db.py and writes:
  outputs/*.csv          - every table behind a memo or dashboard number
  outputs/kpi_summary.json
  docs/img/*.png         - static charts for the README / dashboard

Analysis window: purchases Sep 2016 - May 2018. Jun-Aug 2018 is excluded
because its late orders were still in transit at the data cut-off
(right-censoring; see README "Limits").

Usage: python analysis/build_db.py && python analysis/run_analysis.py
"""
import json
import pathlib

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
IMG = ROOT / "docs" / "img"
OUT.mkdir(exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)

WINDOW_END = "2018-05-01"   # last purchase month analysed (censoring cut)

plt.rcParams.update({
    "figure.figsize": (9, 4.5), "figure.dpi": 110,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3, "font.size": 10,
})
LATE_RED, OK_BLUE, ACCENT, GREY = "#c0392b", "#2c7fb0", "#e67e22", "#95a5a6"

con = duckdb.connect(str(ROOT / "olist.duckdb"), read_only=True)
facts = con.execute(
    "SELECT * FROM v_order_facts WHERE purchase_month <= ?", [WINDOW_END]).df()
seller_facts = con.execute(
    "SELECT * FROM v_order_seller_facts WHERE purchase_month <= ?", [WINDOW_END]).df()
routes = con.execute("SELECT * FROM v_route_facts").df()
monthly = con.execute(
    "SELECT * FROM v_monthly_metrics WHERE purchase_month BETWEEN '2017-01-01' AND ? ORDER BY 1",
    [WINDOW_END]).df()

for c in ["purchase_date", "purchase_month", "carrier_date", "delivered_date",
          "estimated_date", "shipping_limit"]:
    for df in (facts, seller_facts):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c])
monthly["purchase_month"] = pd.to_datetime(monthly["purchase_month"])

# ---------------------------------------------------------------- headline
late = facts[facts.is_late]
kpi = {
    "analysis_window": f"{facts.purchase_date.min():%b %Y} - {facts.purchase_date.max():%b %Y}",
    "orders_analysed": int(len(facts)),
    "late_orders": int(len(late)),
    "late_rate": round(float(facts.is_late.mean()), 4),
    "on_time_rate": round(float((~facts.is_late).mean()), 4),
    "avg_review": round(float(facts.review_score.mean()), 2),
    "avg_delivery_days": round(float(facts.delivery_days.mean()), 1),
    "avg_promised_days": round(float(facts.promised_days.mean()), 1),
    "avg_days_late_when_late": round(float(late.days_late.mean()), 1),
    "items_gmv_brl": round(float(facts.items_value.sum()), 0),
    "freight_gmv_brl": round(float(facts.freight_value.sum()), 0),
    "late_items_gmv_brl": round(float(late.items_value.sum()), 0),
    "multiseller_share_of_orders": round(float((facts.n_sellers > 1).mean()), 4),
}

# ----------------------------------------- dispatch vs transit: where delay sits
dt = (facts[facts.carrier_date.notna()].groupby("is_late")
      .agg(avg_dispatch=("dispatch_days", "mean"), avg_transit=("transit_days", "mean"))
      .round(1))
dt.to_csv(OUT / "dispatch_vs_transit.csv")
kpi["dispatch_vs_transit"] = {
    "on_time": {"dispatch": float(dt.loc[False, "avg_dispatch"]), "transit": float(dt.loc[False, "avg_transit"])},
    "late": {"dispatch": float(dt.loc[True, "avg_dispatch"]), "transit": float(dt.loc[True, "avg_transit"])},
}

fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(2); w = 0.35
ax.bar(x - w/2, [dt.loc[False, "avg_dispatch"], dt.loc[False, "avg_transit"]], w,
       label="on-time orders", color=OK_BLUE)
ax.bar(x + w/2, [dt.loc[True, "avg_dispatch"], dt.loc[True, "avg_transit"]], w,
       label="late orders", color=LATE_RED)
ax.set_xticks(x); ax.set_xticklabels(["dispatch\n(seller -> carrier)", "transit\n(carrier -> customer)"])
ax.set_ylabel("average days"); ax.legend()
ax.set_title("Where the delay sits: 3 extra days with the seller, 20 with the carrier")
for xi, v in zip(x - w/2, [dt.loc[False, "avg_dispatch"], dt.loc[False, "avg_transit"]]):
    ax.text(xi, v + 0.4, f"{v:.1f}", ha="center")
for xi, v in zip(x + w/2, [dt.loc[True, "avg_dispatch"], dt.loc[True, "avg_transit"]]):
    ax.text(xi, v + 0.4, f"{v:.1f}", ha="center")
fig.tight_layout(); fig.savefig(IMG / "dispatch_vs_transit.png"); plt.close(fig)

# ------------------------------------------------------ review vs lateness
bins = [-0.5, 0.5, 3.5, 7.5, 14.5, np.inf]
labels = ["on time", "1-3 days", "4-7 days", "8-14 days", "15+ days"]
rev = facts.dropna(subset=["review_score"]).copy()
rev["lateness_band"] = pd.cut(rev.days_late, bins=bins, labels=labels)
review_band = (rev.groupby("lateness_band", observed=True)
               .agg(orders=("review_score", "size"), avg_review=("review_score", "mean"),
                    share_1_2_star=("review_score", lambda s: (s <= 2).mean())).round(3))
split = (rev.groupby(["lateness_band", "review_before_delivery"], observed=True)
         .review_score.mean().unstack().round(2))
split.columns = ["avg_review_written_after_delivery", "avg_review_written_before_delivery"]
review_band = review_band.join(split)
pct_before = (rev.groupby("lateness_band", observed=True).review_before_delivery.mean() * 100).round(1)
review_band["pct_reviews_written_before_delivery"] = pct_before
review_band.to_csv(OUT / "review_vs_lateness.csv")

fig, ax = plt.subplots()
xi = np.arange(len(review_band)); w = 0.35
ax.bar(xi - w/2, review_band.avg_review_written_after_delivery, w,
       label="review written after delivery", color=OK_BLUE)
ax.bar(xi + w/2, review_band.avg_review_written_before_delivery, w,
       label="review written before delivery", color=ACCENT)
ax.axhline(rev.review_score.mean(), color=LATE_RED, ls="--", lw=1,
           label=f"all orders: {rev.review_score.mean():.2f}")
ax.set_xticks(xi); ax.set_xticklabels(review_band.index.astype(str))
ax.set_ylim(0, 5); ax.set_ylabel("average review score")
ax.set_xlabel("delivery vs estimate"); ax.legend(fontsize=9)
ax.set_title("Later delivery, lower reviews - and many late reviews are written before the parcel arrives")
fig.tight_layout(); fig.savefig(IMG / "review_vs_dayslate.png"); plt.close(fig)

# ------------------------------------------------- seller performance + breach
seller_perf = (seller_facts.groupby("seller_id")
               .agg(orders=("is_late", "size"), late_orders=("is_late", "sum"),
                    late_rate=("is_late", "mean"),
                    breach_rate=("shipping_limit_breach", "mean"),
                    avg_dispatch_days=("dispatch_days", "mean"),
                    avg_review=("review_score", "mean"),
                    gmv=("seller_order_value", "sum"))
               .query("orders >= 30").sort_values("late_rate", ascending=False).round(4))
seller_perf.to_csv(OUT / "seller_performance.csv")

n10 = max(1, int(np.ceil(len(seller_perf) * 0.10)))
worst10_share_within = seller_perf.late_orders.head(n10).sum() / seller_perf.late_orders.sum()
all_late_single = seller_facts.is_late.sum()
worst10_share_all = seller_perf.late_orders.head(n10).sum() / all_late_single
kpi["sellers_analysed_min30_orders"] = int(len(seller_perf))
kpi["worst_10pct_sellers_share_of_late_orders_within_group"] = round(float(worst10_share_within), 3)
kpi["worst_10pct_sellers_share_of_all_late_orders"] = round(float(worst10_share_all), 3)
kpi["worst_10pct_late_rate"] = round(float(seller_perf.late_orders.head(n10).sum() / seller_perf.orders.head(n10).sum()), 4)
kpi["rest_late_rate"] = round(float(seller_perf.late_orders.iloc[n10:].sum() / seller_perf.orders.iloc[n10:].sum()), 4)

pareto = seller_perf.late_orders.values
pareto_cum = np.cumsum(pareto) / pareto.sum() * 100
fig, ax = plt.subplots()
ax.plot(np.arange(1, len(pareto_cum) + 1) / len(pareto_cum) * 100, pareto_cum, color=OK_BLUE)
ax.axvline(10, color=LATE_RED, ls="--", lw=1)
ax.text(11, 20, f"worst 10% = {worst10_share_within:.0%} of the group's late orders\n"
        f"(only {worst10_share_all:.0%} of all late orders)", color=LATE_RED)
ax.set_xlabel("% of sellers (ranked by late orders)"); ax.set_ylabel("cumulative % of late orders")
ax.set_title("Seller concentration is real but modest - no small group to blame")
fig.tight_layout(); fig.savefig(IMG / "seller_pareto.png"); plt.close(fig)

# ------------------------------------ persistence test (replaces the circular p-value)
p17 = (seller_facts[seller_facts.purchase_month < "2018-01-01"].groupby("seller_id")
       .agg(n17=("is_late", "size"), lr17=("is_late", "mean")).query("n17 >= 20"))
p17["decile"] = pd.qcut(p17.lr17.rank(method="first"), 10, labels=False) + 1
p18 = (seller_facts[seller_facts.purchase_month >= "2018-01-01"].groupby("seller_id")
       .agg(n18=("is_late", "size"), lr18=("is_late", "mean")))
pers = p17.join(p18, how="inner").groupby("decile").agg(
    sellers=("n17", "size"), late_2017=("lr17", "mean"), late_2018=("lr18", "mean"),
    orders_2018=("n18", "sum")).round(4)
pers.to_csv(OUT / "seller_persistence.csv")

# ------------------------------------------------- late rate by cut of data
by_category = (facts.groupby("category_en")
               .agg(orders=("is_late", "size"), late_rate=("is_late", "mean"),
                    avg_review=("review_score", "mean"))
               .query("orders >= 500").sort_values("late_rate", ascending=False).round(4))
by_category.to_csv(OUT / "late_by_category.csv")

by_route = routes.query("orders >= 100").sort_values("late_rate", ascending=False).round(4)
by_route.to_csv(OUT / "late_by_route.csv", index=False)

# route promise recalibration: historical percentiles on the worst routes
worst_routes = by_route.head(3)[["seller_state", "customer_state"]]
pct_rows = []
for _, r in worst_routes.iterrows():
    d = seller_facts[(seller_facts.seller_state == r.seller_state) &
                     (seller_facts.customer_state == r.customer_state)].delivery_days.dropna()
    pct_rows.append({"route": f"{r.seller_state} -> {r.customer_state}", "orders": len(d),
                     "avg_days": round(float(d.mean()), 1),
                     "p50_days": float(d.quantile(0.5)), "p80_days": float(d.quantile(0.8)),
                     "p90_days": float(d.quantile(0.9))})
pd.DataFrame(pct_rows).to_csv(OUT / "route_delivery_percentiles.csv", index=False)

# ------------------------------------------------------------ late trend
m = monthly.set_index("purchase_month")
fig, ax = plt.subplots()
ax.plot(m.index, m.late_rate * 100, marker="o", color=LATE_RED, label="late rate")
ax2 = ax.twinx()
ax2.plot(m.index, m.avg_review, marker="s", color=OK_BLUE, label="avg review")
ax2.spines.right.set_visible(True); ax2.set_ylim(3.5, 4.6)
ax.set_ylabel("late rate %"); ax2.set_ylabel("avg review")
ax.set_title("Late rate and review score by month (censored Jun-Aug 2018 excluded)")
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(IMG / "late_trend.png"); plt.close(fig)

# ------------------------------------------------------- forecast (appendix)
hist = m.loc["2017-01-01":]
train_end, holdout_start = "2018-02-01", "2018-03-01"

def fc_naive(series, horizon):
    return np.repeat(series.iloc[-1], horizon)

def fc_ma(series, horizon):
    vals = list(series); out = []
    for _ in range(horizon):
        out.append(np.mean(vals[-3:])); vals.append(out[-1])
    return np.array(out)

forecast_rows = []
scopes = [("all orders", hist.orders)]
for cat in (facts.groupby("category_en").size().sort_values(ascending=False).head(5).index):
    s = (facts[facts.category_en == cat].groupby("purchase_month").size()
         .asfreq("MS", fill_value=0).loc["2017-01-01":WINDOW_END])
    scopes.append((cat, s))
for name, series in scopes:
    train = series.loc[:train_end]
    actual = series.loc[holdout_start:].values
    months = series.loc[holdout_start:].index
    if len(actual) == 0:
        continue
    for method, pred in [("naive last month", fc_naive(train, len(actual))),
                         ("3-month moving average", fc_ma(train, len(actual)))]:
        mape = float(np.mean(np.abs((actual - pred) / np.maximum(actual, 1))) * 100)
        for d, a, p_ in zip(months, actual, pred):
            forecast_rows.append({"scope": name, "method": method, "month": d.date(),
                                  "actual": int(a), "forecast": round(float(p_)),
                                  "mape_pct": round(mape, 1)})
forecast = pd.DataFrame(forecast_rows)
forecast.to_csv(OUT / "forecast_vs_actual.csv", index=False)
best = (forecast.groupby(["scope", "method"]).mape_pct.first()
        .groupby("scope").idxmin().apply(lambda t: t[1]))
kpi["forecast_appendix"] = {"holdout": "Mar-May 2018",
    "winning_method_by_scope": best.to_dict(),
    "mape_all_orders_pct": float(forecast[(forecast.scope == "all orders") &
        (forecast.method == best["all orders"])].mape_pct.iloc[0])}

fig, ax = plt.subplots()
sub = forecast[(forecast.scope == "all orders") & (forecast.method == best["all orders"])]
ax.plot(hist.index, hist.orders, marker="o", color=OK_BLUE, label="actual")
ax.plot(pd.to_datetime(sub.month), sub.forecast, marker="s", color=ACCENT,
        label=f"{best['all orders']} (MAPE {sub.mape_pct.iloc[0]}%)")
ax.set_title("Monthly orders: forecast vs actual (holdout Mar-May 2018)")
ax.set_ylabel("orders"); ax.legend()
fig.autofmt_xdate(); fig.tight_layout()
fig.savefig(IMG / "forecast_vs_actual.png"); plt.close(fig)

json.dump(kpi, open(OUT / "kpi_summary.json", "w"), indent=2)
print(json.dumps(kpi, indent=2))
