"""Seller early-warning score: logistic model + capped weekly review queue.

Claude-review redesign (27 Oct): the original threshold rule (late >= 8% or
review <= 3.8) flagged ~46% of seller-months for a 15.8% precision against a
13.2% base rate - barely better than random at that volume. Rebuilt as:

  1. Score each seller-month with a logistic regression on trailing-90-day
     features: late rate, avg review, avg dispatch days, shipping-limit
     breach rate, order volume, cancellation rate.
  2. Rank seller-months and cap the review queue (top K per month).
  3. Report hit rate at K against the base rate, plus a lift curve.

Label ("bad month"): in month M the seller has >= 5 orders AND
(late rate >= 15% OR avg review <= 3.0). Features use only data BEFORE M,
so there is no leakage.

Train: label months in 2017. Test: label months Jan-May 2018 (out-of-time;
Jun-Aug 2018 excluded for right-censoring).

Usage: python analysis/scorecard_backtest.py
"""
import json
import pathlib

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
IMG = ROOT / "docs" / "img"

MIN_ORDERS_90D = 10
BAD_LATE, BAD_REVIEW = 0.15, 3.0
TEST_START = pd.Timestamp("2018-01-01")
LABEL_END = pd.Timestamp("2018-05-01")   # censoring cut
QUEUE_K = 20                             # weekly review queue cap per month

con = duckdb.connect(str(ROOT / "olist.duckdb"), read_only=True)
sf = con.execute("""
    SELECT seller_id, purchase_month, is_late, review_score, dispatch_days,
           shipping_limit_breach
    FROM v_order_seller_facts
    WHERE purchase_month BETWEEN '2017-01-01' AND ?
""", [LABEL_END]).df()
canc = con.execute("""
    SELECT seller_id, purchase_month, orders, canceled
    FROM v_seller_cancellations
    WHERE purchase_month BETWEEN '2017-01-01' AND ?
""", [LABEL_END]).df()
for df in (sf, canc):
    df["purchase_month"] = pd.to_datetime(df["purchase_month"])

months = pd.date_range("2017-04-01", LABEL_END, freq="MS")
rows = []
for seller, g in sf.groupby("seller_id"):
    g = g.set_index("purchase_month")
    gc = canc[canc.seller_id == seller].set_index("purchase_month")
    for mth in months:
        trail = g[(g.index >= mth - pd.DateOffset(months=3)) & (g.index < mth)]
        tc = gc[(gc.index >= mth - pd.DateOffset(months=3)) & (gc.index < mth)]
        nxt = g[g.index == mth]
        if len(trail) < MIN_ORDERS_90D:
            continue
        cancel_rate = (tc.canceled.sum() / tc.orders.sum()) if len(tc) and tc.orders.sum() else 0.0
        rows.append({
            "seller_id": seller, "month": mth,
            "orders_90d": len(trail),
            "late_rate_90d": trail.is_late.mean(),
            "review_90d": trail.review_score.mean(),
            "dispatch_90d": trail.dispatch_days.mean(),
            "breach_90d": trail.shipping_limit_breach.mean(),
            "cancel_90d": cancel_rate,
            "next_orders": len(nxt),
            "next_bad": bool(len(nxt) >= 5 and
                             (nxt.is_late.mean() >= BAD_LATE or
                              nxt.review_score.mean() <= BAD_REVIEW)) if len(nxt) else np.nan,
        })
panel = pd.DataFrame(rows)
ev = panel.dropna(subset=["next_bad"]).copy()
ev["next_bad"] = ev.next_bad.astype(bool)
ev["split"] = np.where(ev.month < TEST_START, "train (2017)", "test (2018)")

FEATURES = ["late_rate_90d", "review_90d", "dispatch_90d", "breach_90d",
            "cancel_90d", "orders_90d"]
train = ev[ev.split == "train (2017)"]
X = sm.add_constant((train[FEATURES] - train[FEATURES].mean()) / train[FEATURES].std())
model = sm.Logit(train.next_bad.astype(int), X).fit(disp=0)

mu, sd = train[FEATURES].mean(), train[FEATURES].std()
Xs = sm.add_constant((ev[FEATURES] - mu) / sd)
ev["risk_score"] = model.predict(Xs)

# --- capped queue: top K per month by score
ev["rank_in_month"] = ev.groupby("month").risk_score.rank(ascending=False, method="first")
test = ev[ev.split == "test (2018)"].copy()
base_rate = float(test.next_bad.mean())

lift_rows = []
for k in [5, 10, 20, 50, 100]:
    picked = test[test.rank_in_month <= k]
    hit = float(picked.next_bad.mean()) if len(picked) else np.nan
    lift_rows.append({"k": k, "seller_months_picked": int(len(picked)),
                      "hit_rate": round(hit, 3), "base_rate": round(base_rate, 3),
                      "lift": round(hit / base_rate, 2) if base_rate else np.nan,
                      "share_of_bad_caught": round(float(picked.next_bad.sum() / test.next_bad.sum()), 3)})
lift = pd.DataFrame(lift_rows)
lift.to_csv(OUT / "scorecard_lift.csv", index=False)

k20 = lift[lift.k == QUEUE_K].iloc[0]
# threshold-rule comparison row (the old rule, for the memo's honesty)
old = test[(test.late_rate_90d >= 0.08) | (test.review_90d <= 3.8)]
old_prec = float(old.next_bad.mean()); old_rec = float(old.next_bad.sum() / test.next_bad.sum())

fig, ax = plt.subplots()
ax.plot(lift.k, lift.hit_rate * 100, marker="o", color="#2c7fb0",
        label="model queue hit rate")
ax.axhline(base_rate * 100, color="#c0392b", ls="--", lw=1,
           label=f"base rate {base_rate:.1%} (random)")
ax.set_xlabel("queue cap K (sellers flagged per month)")
ax.set_ylabel("hit rate % (flagged sellers who turn bad)")
ax.set_title("Scorecard lift on 2018 holdout (trained on 2017 only)")
ax.legend(); fig.tight_layout()
fig.savefig(IMG / "scorecard_lift.png"); plt.close(fig)

fig, ax = plt.subplots()
tt = test[test.rank_in_month <= QUEUE_K]
ax.scatter(test.late_rate_90d * 100, test.review_90d, s=10, alpha=0.25,
           color="#95a5a6", label="not in queue")
ax.scatter(tt[tt.next_bad].late_rate_90d * 100, tt[tt.next_bad].review_90d,
           s=22, color="#c0392b", label="queued, turned bad")
ax.scatter(tt[~tt.next_bad].late_rate_90d * 100, tt[~tt.next_bad].review_90d,
           s=22, color="#e67e22", label="queued, stayed ok")
ax.set_xlabel("trailing 90-day late rate %"); ax.set_ylabel("trailing 90-day avg review")
ax.set_title(f"Top-{QUEUE_K} monthly review queue on 2018 holdout")
ax.legend(fontsize=8); fig.tight_layout()
fig.savefig(IMG / "scorecard_queue.png"); plt.close(fig)

ev.to_csv(OUT / "scorecard_backtest.csv", index=False)
summary = {
    "model": "logistic regression (statsmodels), standardised trailing-90d features",
    "features": FEATURES,
    "label": f"next month: >=5 orders AND (late rate >= {BAD_LATE} OR avg review <= {BAD_REVIEW})",
    "queue_cap_per_month": QUEUE_K,
    "train_period": "label months 2017", "test_period": "label months Jan-May 2018",
    "coefficients": {k: round(float(v), 3) for k, v in model.params.items()},
    "test_base_rate": round(base_rate, 3),
    "queue_hit_rate_at_k": float(k20.hit_rate),
    "queue_lift_at_k": float(k20.lift),
    "share_of_bad_caught_at_k": float(k20.share_of_bad_caught),
    "old_threshold_rule_on_same_test": {"precision": round(old_prec, 3),
                                        "recall": round(old_rec, 3),
                                        "flagged_share": round(len(old) / len(test), 3)},
}
json.dump(summary, open(OUT / "scorecard_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
print()
print(lift.to_string(index=False))
