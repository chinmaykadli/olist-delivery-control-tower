"""Seller early-warning queue: one-line ranking rules vs a logistic model.

Question: if Seller Ops can call 20 sellers a month (about 5 a week), which
ranking puts the most next-month problem sellers on that list?

Features and labels come from SQL (v_seller_features in 04_lane_views.sql):
trailing 90-day (three calendar months before M) late rate, shipping-limit
breach rate, dispatch days, review and volume, for sellers with 10+ orders.
Label: in month M the seller has 5+ orders AND (late rate >= 15% OR average
review <= 3.0). Months with 1-4 orders are dropped, not labelled good.

Candidates, all ranked within each month and capped at K:
  A. sort by trailing late rate (ties: volume)
  B. sort by the Wilson 95% lower bound of trailing late rate (penalises
     sellers with few orders, where 2 late out of 10 is mostly noise)
  C. logistic regression on the five standardised features (comparison only)
The queue rule (A or B) is chosen on the 2017 TRAIN months only, then
everything is reported on the Jan-Jul 2018 test months.

Also reported: Wilson CI on hit rate at K, AUC with a seller-cluster
bootstrap CI, a per-month table, and the same test with a one-month gap
between features and label (v_seller_features_gap1).

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
from scipy.stats import rankdata
from statsmodels.stats.proportion import proportion_confint

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
IMG = ROOT / "docs" / "img"
OUT.mkdir(exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)

QUEUE_K = 20                      # fixed from ops capacity BEFORE testing
TRAIN = ("2017-04-01", "2017-12-01")
FEATURES = ["late_rate_90d", "review_90d", "dispatch_90d", "breach_90d", "orders_90d"]
SEED = 7

con = duckdb.connect(str(ROOT / "olist.duckdb"), read_only=True)
window_end = con.execute("SELECT window_end FROM v_params").fetchone()[0]
TEST = ("2018-01-01", str(window_end))


def load(view: str) -> pd.DataFrame:
    df = con.execute(f"""
        SELECT * FROM {view}
        WHERE label_month BETWEEN DATE '{TRAIN[0]}' AND DATE '{TEST[1]}'
    """).df()
    df["label_month"] = pd.to_datetime(df.label_month)
    df["label_bad"] = df.label_bad.astype(bool)
    df["review_90d"] = df.review_90d.fillna(df.review_90d.median())
    df["split"] = np.where(df.label_month < TEST[0], "train", "test")
    return df


def wilson_lower(p: pd.Series, n: pd.Series, z: float = 1.96) -> pd.Series:
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (centre - margin) / denom


def auc(y: np.ndarray, s: np.ndarray) -> float:
    r = rankdata(s)
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def add_scores(df: pd.DataFrame):
    df = df.copy()
    df["score_A_late_rate"] = df.late_rate_90d + df.orders_90d * 1e-6   # volume breaks ties
    df["score_B_wilson_lb"] = wilson_lower(df.late_rate_90d, df.orders_90d)
    train = df[df.split == "train"]
    mu, sd = train[FEATURES].mean(), train[FEATURES].std()
    X = sm.add_constant((train[FEATURES] - mu) / sd)
    model = sm.Logit(train.label_bad.astype(int), X).fit(disp=0)
    df["score_C_model"] = model.predict(sm.add_constant((df[FEATURES] - mu) / sd))
    return df, model


def hit_at_k(df: pd.DataFrame, score: str, k: int) -> dict:
    rk = df.groupby("label_month")[score].rank(ascending=False, method="first")
    picked = df[rk <= k]
    hits, n = int(picked.label_bad.sum()), len(picked)
    lo, hi = proportion_confint(hits, n, method="wilson") if n else (np.nan, np.nan)
    base = float(df.label_bad.mean())
    return {"k": k, "picked": n, "hits": hits, "hit_rate": hits / n if n else np.nan,
            "ci_low": lo, "ci_high": hi, "base_rate": base,
            "lift": (hits / n) / base if n and base else np.nan,
            "share_of_bad_caught": hits / df.label_bad.sum()}


def auc_with_ci(df: pd.DataFrame, score: str, reps: int = 400) -> tuple[float, float, float]:
    point = auc(df.label_bad.astype(int).values, df[score].values)
    rng = np.random.default_rng(SEED)
    groups = {s: g for s, g in df.groupby("seller_id")}
    sellers = np.array(list(groups))
    draws = []
    for _ in range(reps):
        sample = pd.concat([groups[s] for s in rng.choice(sellers, len(sellers))])
        y = sample.label_bad.astype(int).values
        if 0 < y.sum() < len(y):
            draws.append(auc(y, sample[score].values))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return point, float(lo), float(hi)


SCORES = {"A: sort by trailing late rate": "score_A_late_rate",
          "B: sort by Wilson lower bound": "score_B_wilson_lb",
          "C: logistic model (5 features)": "score_C_model"}

ev, model = add_scores(load("v_seller_features"))
train, test = ev[ev.split == "train"], ev[ev.split == "test"]

# --- choose the queue rule on TRAIN only (A vs B; C is the comparison)
train_hits = {name: hit_at_k(train, col, QUEUE_K)["hit_rate"]
              for name, col in SCORES.items() if not name.startswith("C")}
queue_rule = max(train_hits, key=train_hits.get)

# --- test-set comparison
rows = []
for name, col in SCORES.items():
    a, a_lo, a_hi = auc_with_ci(test, col)
    for k in [5, 10, 20, 50]:
        r = hit_at_k(test, col, k)
        r.update({"rule": name, "auc": a, "auc_ci_low": a_lo, "auc_ci_high": a_hi})
        rows.append(r)
comparison = pd.DataFrame(rows)[["rule", "k", "picked", "hits", "hit_rate", "ci_low", "ci_high",
                                 "base_rate", "lift", "share_of_bad_caught", "auc",
                                 "auc_ci_low", "auc_ci_high"]].round(3)
comparison.to_csv(OUT / "scorecard_comparison.csv", index=False)

# --- per-month view for the chosen rule and the model
per_month = []
for name in [queue_rule, "C: logistic model (5 features)"]:
    col = SCORES[name]
    for m, g in test.groupby("label_month"):
        r = hit_at_k(g, col, QUEUE_K)
        per_month.append({"rule": name, "month": m.date(), "sellers_scored": len(g),
                          "base_rate": round(r["base_rate"], 3), "hit_rate_at_20": round(r["hit_rate"], 3)})
pd.DataFrame(per_month).to_csv(OUT / "scorecard_per_month.csv", index=False)

# --- sensitivity: one-month gap between features and label
ev_gap, _ = add_scores(load("v_seller_features_gap1"))
test_gap = ev_gap[ev_gap.split == "test"]
gap = {name: round(hit_at_k(test_gap, col, QUEUE_K)["hit_rate"], 3) for name, col in SCORES.items()}

# --- chart: hit rate at K by rule, with base rate
fig, ax = plt.subplots(figsize=(8, 4.5))
colours = {"A": "#2c7fb0", "B": "#16a085", "C": "#95a5a6"}
for name in SCORES:
    sub = comparison[comparison.rule == name]
    ax.errorbar(sub.k, sub.hit_rate * 100,
                yerr=[(sub.hit_rate - sub.ci_low) * 100, (sub.ci_high - sub.hit_rate) * 100],
                marker="o", capsize=3, label=name, color=colours[name[0]])
ax.axhline(test.label_bad.mean() * 100, color="#c0392b", ls="--", lw=1,
           label=f"base rate {test.label_bad.mean():.0%} (random pick)")
ax.set_xlabel("queue cap K (sellers per month)"); ax.set_ylabel("hit rate % (95% CI)")
ax.set_title("Who to call: one-line rules vs a 5-feature model, Jan-Jul 2018 holdout")
ax.legend(fontsize=8); fig.tight_layout()
fig.savefig(IMG / "scorecard_lift.png"); plt.close(fig)

chosen = comparison[(comparison.rule == queue_rule) & (comparison.k == QUEUE_K)].iloc[0]
modelrow = comparison[(comparison.rule.str.startswith("C")) & (comparison.k == QUEUE_K)].iloc[0]
summary = {
    "question": "which ranking fills a 20-seller monthly call list with next-month problem sellers",
    "label": "month M: >=5 orders AND (late rate >= 0.15 OR avg review <= 3.0); 1-4 order months dropped",
    "features": FEATURES,
    "train_months": f"{TRAIN[0]} to {TRAIN[1]}", "test_months": f"{TEST[0]} to {TEST[1]}",
    "queue_cap_per_month": QUEUE_K,
    "train_hit_rate_at_k": {k: round(v, 3) for k, v in train_hits.items()},
    "queue_rule": queue_rule,
    "test_rows": int(len(test)), "test_base_rate": round(float(test.label_bad.mean()), 3),
    "queue_hit_rate_at_k": float(chosen.hit_rate),
    "queue_hit_rate_ci": [float(chosen.ci_low), float(chosen.ci_high)],
    "queue_lift_at_k": float(chosen.lift),
    "queue_share_of_bad_caught": float(chosen.share_of_bad_caught),
    "queue_auc": [float(chosen.auc), float(chosen.auc_ci_low), float(chosen.auc_ci_high)],
    "model_hit_rate_at_k": float(modelrow.hit_rate),
    "model_hit_rate_ci": [float(modelrow.ci_low), float(modelrow.ci_high)],
    "model_auc": [float(modelrow.auc), float(modelrow.auc_ci_low), float(modelrow.auc_ci_high)],
    "model_coefficients": {k: round(float(v), 3) for k, v in model.params.items()},
    "model_pvalues": {k: round(float(v), 3) for k, v in model.pvalues.items()},
    "gap1_sensitivity_hit_rate_at_k": gap,
}
json.dump(summary, open(OUT / "scorecard_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
print(comparison[comparison.k == QUEUE_K].to_string(index=False))
