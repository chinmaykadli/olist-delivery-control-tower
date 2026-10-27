"""Lane-specific analyses: peaks and promises, carrier early warning, lanes,
cost of lateness, persistence and pilot power.

Reads the views in sql/04_lane_views.sql and writes:
  outputs/lanes_summary.json      - every number quoted in README / memo
  outputs/*.csv                   - the table behind each chart
  docs/img/*.png                  - static charts for the README

All results are a case study on Olist's public data. Promise-change
backtests assume delivery times would not change when the promise changes,
and the data says nothing about conversion.

Usage: python analysis/lanes_analysis.py   (after build_db.py)
"""
import json
import pathlib

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import spearmanr
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_confint, proportion_effectsize

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT, IMG = ROOT / "outputs", ROOT / "docs" / "img"
OUT.mkdir(exist_ok=True); IMG.mkdir(parents=True, exist_ok=True)
LATE_RED, OK_BLUE, ACCENT, GREY = "#c0392b", "#2c7fb0", "#e67e22", "#95a5a6"
plt.rcParams.update({"figure.figsize": (9, 4.5), "figure.dpi": 110,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "font.size": 10})

con = duckdb.connect(str(ROOT / "olist.duckdb"), read_only=True)
q = lambda sql: con.execute(sql).df()
W0, W1 = [str(x) for x in con.execute("SELECT window_start, window_end FROM v_params").fetchone()]
S = {"window": f"{W0} to {W1}"}

# ------------------------------------------------------------ 1. peaks
months = q("SELECT * FROM v_month_flags WHERE orders >= 100 ORDER BY purchase_month")
months.to_csv(OUT / "month_flags.csv", index=False)
months["late_orders"] = months.late_rate * months.orders
peak = months[months.is_peak]
S["peak_rule"] = "marketplace late rate >= 10% in the purchase month"
S["peak_months"] = [str(m)[:7] for m in peak.purchase_month]
S["peak_share_of_orders"] = round(float(peak.orders.sum() / months.orders.sum()), 3)
S["peak_share_of_late_orders"] = round(float(peak.late_orders.sum() / months.late_orders.sum()), 3)
pp = q("""
  SELECT m.is_peak, AVG(f.promised_days) promised, AVG(f.transit_days) transit,
         AVG(f.dispatch_days) dispatch, AVG(f.is_late::INT) late_rate
  FROM v_order_facts f JOIN v_month_flags m USING (purchase_month)
  WHERE m.orders >= 100 AND f.purchase_month >= DATE '2017-01-01'
  GROUP BY 1""").set_index("is_peak")
S["promise_days_normal_vs_peak"] = [round(float(pp.loc[False, "promised"]), 1), round(float(pp.loc[True, "promised"]), 1)]
S["transit_days_normal_vs_peak"] = [round(float(pp.loc[False, "transit"]), 1), round(float(pp.loc[True, "transit"]), 1)]
S["late_rate_normal_vs_peak"] = [round(float(pp.loc[False, "late_rate"]), 3), round(float(pp.loc[True, "late_rate"]), 3)]

weeks = q("""
  SELECT date_trunc('week', purchase_date)::DATE AS purchase_week, COUNT(*) AS orders,
         AVG(promised_days) AS promised_days, AVG(is_late::INT) AS late_rate
  FROM v_order_facts
  WHERE purchase_date BETWEEN DATE '2017-10-30' AND DATE '2018-04-29'
  GROUP BY 1 ORDER BY 1""")
weeks.to_csv(OUT / "weekly_promise_vs_late.csv", index=False)
fig, ax = plt.subplots()
ax.plot(weeks.purchase_week, weeks.late_rate * 100, color=LATE_RED, marker="o", label="late rate % (purchase week)")
ax2 = ax.twinx(); ax2.spines.right.set_visible(True)
ax2.plot(weeks.purchase_week, weeks.promised_days, color=OK_BLUE, marker="s", label="avg promised days")
ax.set_ylabel("late rate %"); ax2.set_ylabel("promised days")
ax.set_title("Promises were cut while lateness rose (Feb-Mar 2018), and widened after Black Friday")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(IMG / "peaks_promise_vs_late.png"); plt.close(fig)
feb = weeks[(weeks.purchase_week >= pd.Timestamp("2018-02-05")) & (weeks.purchase_week <= pd.Timestamp("2018-03-12"))]
S["feb_mar_2018_weekly_promise_range"] = [round(float(feb.promised_days.max()), 1), round(float(feb.promised_days.min()), 1)]
S["feb_mar_2018_weekly_late_peak"] = round(float(feb.late_rate.max()), 3)

# ------------------------------------------- 2. carrier early warning
age = q("SELECT * FROM v_transit_ageing ORDER BY as_of_date")
age.to_csv(OUT / "transit_ageing.csv", index=False)
age = age[age.handed_10_30d_ago >= 500]          # thin early-2017 weeks are noise
deliv = q("""
  SELECT date_trunc('week', delivered_date)::DATE AS delivered_week,
         AVG(is_late::INT) AS late_share_of_deliveries, COUNT(*) AS n
  FROM v_order_facts WHERE delivered_date BETWEEN DATE '2017-01-02' AND DATE '2018-08-05'
  GROUP BY 1 HAVING COUNT(*) >= 200 ORDER BY 1""")
deliv.to_csv(OUT / "weekly_late_share_of_deliveries.csv", index=False)
ALARM = 0.20
first_feb_age = age[(age.as_of_date >= pd.Timestamp("2018-02-01")) & (age.share_still_in_transit >= ALARM)].as_of_date.min()
first_feb_deliv = deliv[(deliv.delivered_week >= pd.Timestamp("2018-02-01")) & (deliv.late_share_of_deliveries >= 0.10)].delivered_week.min()
S["ageing_alarm_threshold"] = ALARM
S["ageing_alarm_weeks"] = [str(d)[:10] for d in age[age.share_still_in_transit >= ALARM].as_of_date]
S["ageing_first_alarm_2018"] = str(first_feb_age)[:10]
S["delivered_late_share_first_10pct_week_2018"] = str(first_feb_deliv)[:10]
S["ageing_lead_weeks_vs_delivered_signal"] = int((pd.Timestamp(first_feb_deliv) - pd.Timestamp(first_feb_age)).days // 7)
fig, ax = plt.subplots()
ax.plot(age.as_of_date, age.share_still_in_transit * 100, color=ACCENT, label="in-transit ageing % (as of Monday)")
ax.plot(deliv.delivered_week, deliv.late_share_of_deliveries * 100, color=LATE_RED, alpha=0.7,
        label="late share of deliveries that week %")
ax.axhline(ALARM * 100, color=GREY, ls="--", lw=1, label=f"alarm at {ALARM:.0%}")
ax.set_ylabel("%"); ax.legend(fontsize=8)
ax.set_title("Early warning: parcels stuck 10-30 days after handover rise before late deliveries show up")
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(IMG / "transit_ageing.png"); plt.close(fig)

guard = q("SELECT * FROM v_guardrail_backtest ORDER BY extra_days")
guard.to_csv(OUT / "guardrail_backtest.csv", index=False)
window_late = int(con.execute("""SELECT COUNT(*) FROM v_order_facts, v_params
    WHERE purchase_month BETWEEN window_start AND window_end AND is_late""").fetchone()[0])
for k in (3, 5, 7):
    g = guard[guard.extra_days == k].iloc[0]
    S[f"guardrail_plus{k}d"] = {
        "orders_covered": int(g.orders_covered), "late_now": int(g.late_now),
        "late_with_guardrail": int(g.late_with_guardrail),
        "late_avoided": int(g.late_now - g.late_with_guardrail),
        "share_of_all_window_late_orders": round(float((g.late_now - g.late_with_guardrail) / window_late), 3)}
S["guardrail_alarm_weeks"] = int(guard.alarm_weeks.iloc[0])
S["guardrail_caveat"] = "threshold set in-sample on two episodes; promise change assumed not to change delivery or conversion"

# ------------------------------------------------------------ 3. lanes
pareto = q("SELECT * FROM v_lane_pareto ORDER BY lane_rank")
pareto.to_csv(OUT / "lane_pareto.csv", index=False)
S["top2_lanes"] = pareto.lane.head(2).tolist()
S["top2_lanes_share_of_late"] = round(float(pareto.cum_share_of_late.iloc[1]), 3)
S["lanes_for_half_of_late"] = int((pareto.cum_share_of_late < 0.5).sum() + 1)
S["lanes_total"] = int(len(pareto))
top = pareto.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.barh(top.lane, top.late_orders, color=LATE_RED)
for y, (lo, lr) in enumerate(zip(top.late_orders, top.late_rate)):
    ax.text(lo + 10, y, f"{lr:.0%} late", va="center", fontsize=8)
ax.set_xlabel("late orders (single-seller, analysis window)")
ax.set_title("Lane Pareto: rank by late ORDERS, not late rate")
fig.tight_layout(); fig.savefig(IMG / "lane_pareto.png"); plt.close(fig)

var = q("SELECT * FROM v_lane_variability")
var["lane_type"] = np.where(var.late_rate_normal_months >= 0.08, "structural",
                   np.where(var.late_rate_peak_months >= 3 * var.late_rate_normal_months, "peak-driven", "mixed"))
var.sort_values("orders", ascending=False).round(3).to_csv(OUT / "lane_variability.csv", index=False)
for lane in ["SP -> RJ", "SP -> SP", "SP -> AL", "SP -> BA"]:
    r = var[var.lane == lane]
    if len(r):
        r = r.iloc[0]
        S[f"lane {lane}"] = {"orders": int(r.orders), "late_normal": round(float(r.late_rate_normal_months), 3),
                             "late_peak": round(float(r.late_rate_peak_months), 3), "type": r.lane_type,
                             "transit_p50": float(r.transit_p50), "transit_p90": float(r.transit_p90)}

curve = q("SELECT * FROM v_promise_curve ORDER BY lane, extra_days")
curve.to_csv(OUT / "promise_curve.csv", index=False)
fig, ax = plt.subplots()
for lane, c in [("SP -> AL", LATE_RED), ("SP -> RJ", ACCENT), ("SP -> BA", OK_BLUE), ("ALL LANES", GREY)]:
    sub = curve[curve.lane == lane]
    ax.plot(sub.extra_days, sub.on_time_rate * 100, marker="o", ms=3, color=c,
            label=f"{lane} (today {sub.avg_promised_days.iloc[0]:.0f}d promise)")
ax.axhline(93, color=GREY, ls=":", lw=1)
ax.set_xlabel("days added to every promise on the lane"); ax.set_ylabel("on-time rate %")
ax.set_title("Promise curve: what each extra day of promise buys (delivery assumed unchanged)")
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(IMG / "promise_curve.png"); plt.close(fig)
al = curve[curve.lane == "SP -> AL"].set_index("extra_days")
S["sp_al_promise_today_days"] = round(float(al.avg_promised_days.loc[0]), 1)
S["sp_al_on_time_by_extra_days"] = {int(k): round(float(al.on_time_rate.loc[k]), 3) for k in (0, 3, 5, 10, 13)}
S["sp_al_days_to_reach_93pct"] = int(al[al.on_time_rate >= 0.93].index.min())

acc = q("SELECT * FROM v_promise_accuracy")
acc.round(3).to_csv(OUT / "promise_accuracy.csv", index=False)
S["median_promise_slack_days_window"] = float(con.execute("""SELECT median(promise_slack_days) FROM v_order_facts, v_params
    WHERE purchase_month BETWEEN window_start AND window_end""").fetchone()[0])
S["share_delivered_14plus_days_early"] = round(float(con.execute("""SELECT AVG((promise_slack_days >= 14)::INT) FROM v_order_facts, v_params
    WHERE purchase_month BETWEEN window_start AND window_end""").fetchone()[0]), 3)

wt = q("""
  SELECT CASE WHEN weight_g < 500 THEN '1: <0.5kg' WHEN weight_g < 2000 THEN '2: 0.5-2kg'
              WHEN weight_g < 10000 THEN '3: 2-10kg' ELSE '4: 10kg+' END AS weight_band,
         COUNT(*) orders, AVG(is_late::INT) late_rate, AVG(transit_days) transit_days,
         SUM(seller_freight_value) / SUM(seller_order_value) AS freight_share
  FROM v_order_seller_facts, v_params
  WHERE purchase_month BETWEEN window_start AND window_end AND weight_g IS NOT NULL
  GROUP BY 1 ORDER BY 1""")
wt.round(3).to_csv(OUT / "late_by_weight_band.csv", index=False)

# -------------------------------------------------- 4. cost of lateness
cust = q("""
  WITH f AS (
    SELECT customer_unique_id, customer_state, purchase_month, purchase_date, is_late,
           items_value + freight_value AS order_value,
           ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY purchase_date, order_id) AS rn,
           COUNT(*) OVER (PARTITION BY customer_unique_id) AS n_orders
    FROM v_order_facts)
  SELECT *, (n_orders > 1)::INT AS repeat FROM f
  WHERE rn = 1 AND purchase_date < DATE '2018-03-01'""")  # 5+ months to come back
cust["late"] = cust.is_late.astype(int)
cust["cohort"] = cust.purchase_month.astype(str)
raw = cust.groupby("late").repeat.agg(["mean", "size", "sum"])
logit = smf.logit("repeat ~ late + C(customer_state) + C(cohort)", data=cust).fit(disp=0, method="lbfgs", maxiter=500)
ci = np.exp(logit.conf_int().loc["late"]).tolist()
ame = logit.get_margeff(at="overall", dummy=True).summary_frame().loc["late"]
n_late_first = int(raw.loc[1, "size"])
aov = float(con.execute("SELECT AVG(items_value + freight_value) FROM v_order_facts").fetchone()[0])
S["repeat_rate_on_time_vs_late_first_order"] = [round(float(raw.loc[0, "mean"]), 4), round(float(raw.loc[1, "mean"]), 4)]
S["repeat_customers_n"] = [int(raw.loc[0, "size"]), n_late_first]
S["repeat_adjusted_odds_ratio_late"] = [round(float(np.exp(logit.params["late"])), 3), round(ci[0], 3), round(ci[1], 3)]
S["repeat_adjusted_p"] = round(float(logit.pvalues["late"]), 4)
S["repeat_marginal_effect_pp"] = [round(float(ame["dy/dx"]) * 100, 2), round(float(ame["Conf. Int. Low"]) * 100, 2),
                                  round(float(ame["Cont. Int. Hi."]) * 100, 2)]
S["lost_repeat_orders_estimate"] = [round(-float(ame[c]) * n_late_first) for c in ("dy/dx", "Cont. Int. Hi.", "Conf. Int. Low")]
S["avg_order_value_brl"] = round(aov, 1)
S["cost_caveat"] = "observational; adjusted for customer state and first-purchase month only; GMV, not margin"

rv = q("""
  SELECT is_late, review_before_delivery, COUNT(*) n, AVG(review_score) avg_review,
         stddev_samp(review_score) sd
  FROM v_order_facts, v_params
  WHERE purchase_month BETWEEN window_start AND window_end AND review_score IS NOT NULL
  GROUP BY 1, 2""")
rv["ci95"] = 1.96 * rv.sd / np.sqrt(rv.n)
rv.round(3).to_csv(OUT / "review_by_answer_timing.csv", index=False)

# --------------------------------------------------- 5. seller persistence
sy = q("""
  SELECT seller_id, CASE WHEN purchase_month < DATE '2018-01-01' THEN 2017 ELSE 2018 END AS yr,
         COUNT(*) n, AVG(is_late::INT) late_rate
  FROM v_order_seller_facts, v_params
  WHERE purchase_month BETWEEN DATE '2017-01-01' AND window_end
  GROUP BY 1, 2""").pivot(index="seller_id", columns="yr", values=["n", "late_rate"]).dropna()
sy = sy[(sy[("n", 2017)] >= 20) & (sy[("n", 2018)] >= 20)]
rho = spearmanr(sy[("late_rate", 2017)], sy[("late_rate", 2018)])
S["persistence_spearman"] = [round(float(rho.statistic), 3), int(len(sy))]

# -------------------------------------------------------- 6. pilot power
# One-way ANOVA estimator of the intraclass correlation of lateness within
# sellers (2018 single-seller orders, sellers with 10+ orders).
icc_df = q("""
  SELECT seller_id, is_late::INT AS y FROM v_order_seller_facts, v_params
  WHERE purchase_month BETWEEN DATE '2018-01-01' AND window_end""")
g = icc_df.groupby("seller_id").y.agg(["mean", "size"]); g = g[g["size"] >= 10]
d = icc_df[icc_df.seller_id.isin(g.index)]
k_groups, N = len(g), len(d)
grand = d.y.mean()
msb = (g["size"] * (g["mean"] - grand) ** 2).sum() / (k_groups - 1)
msw = (d.groupby("seller_id").y.apply(lambda s: ((s - s.mean()) ** 2).sum())).sum() / (N - k_groups)
n0 = (N - (g["size"] ** 2).sum() / N) / (k_groups - 1)
icc = max(0.0, float((msb - msw) / (msb + (n0 - 1) * msw)))
# Orders per flagged seller over a 60-day outcome window, from the data:
# median trailing-90-day volume of queued sellers in the test months x 2/3.
feat = q("""SELECT label_month, orders_90d, late_rate_90d,
                   ROW_NUMBER() OVER (PARTITION BY label_month ORDER BY late_rate_90d DESC, orders_90d DESC) AS rk
            FROM v_seller_features WHERE label_month >= DATE '2018-01-01'""")
queued = feat[feat.rk <= 20]
m_orders = max(1, int(round(float(queued.orders_90d.median()) * 2 / 3)))
p_ctrl = float(con.execute("""SELECT AVG(is_late::INT) FROM v_order_seller_facts f
    JOIN (SELECT seller_id, label_month FROM v_seller_features
          QUALIFY ROW_NUMBER() OVER (PARTITION BY label_month ORDER BY late_rate_90d DESC, orders_90d DESC) <= 20) qd
      ON f.seller_id = qd.seller_id AND f.purchase_month = qd.label_month
    WHERE qd.label_month >= DATE '2018-01-01'""").fetchone()[0])
p_trt = p_ctrl * 0.75                      # target: a quarter fewer late orders
analysis = NormalIndPower()
n_iid = analysis.solve_power(abs(proportion_effectsize(p_trt, p_ctrl)), alpha=0.05, power=0.8)
de = 1 + (m_orders - 1) * icc
sellers_needed = int(np.ceil(n_iid * de / m_orders))
# What an 8-week pilot can actually detect: 20 queued sellers a month split
# 10/10, two months of intake -> 20 sellers per arm.
sellers_8wk = 20
eff_n = sellers_8wk * m_orders / de
h = analysis.solve_power(nobs1=eff_n, alpha=0.05, power=0.8)
p_mde = float(np.sin(np.arcsin(np.sqrt(p_ctrl)) - h / 2) ** 2)
S["pilot_icc"] = round(icc, 3)
S["pilot_orders_per_seller_60d"] = m_orders
S["pilot_control_late_rate_queued_sellers"] = round(p_ctrl, 3)
S["pilot_target_late_rate"] = round(p_trt, 3)
S["pilot_orders_per_arm_iid"] = int(np.ceil(n_iid))
S["pilot_design_effect"] = round(de, 2)
S["pilot_orders_per_arm_clustered"] = int(np.ceil(n_iid * de))
S["pilot_sellers_per_arm"] = sellers_needed
S["pilot_months_of_intake_at_10_per_arm"] = int(np.ceil(sellers_needed / 10))
S["pilot_8wk_sellers_per_arm"] = sellers_8wk
S["pilot_8wk_minimum_detectable_late_rate"] = round(p_mde, 3)

# ------------------------------------------- 7. censoring + exception queue
q("SELECT * FROM v_censoring_bound").round(4).to_csv(OUT / "censoring_bound.csv", index=False)
cb = q("SELECT * FROM v_censoring_bound").set_index("purchase_month")
S["censoring_jun_jul_2018"] = {str(m)[:7]: [round(float(cb.loc[m, "observed_late_rate"]), 3),
                                            round(float(cb.loc[m, "worst_case_late_rate"]), 3)]
                               for m in cb.index if str(m)[:7] in ("2018-06", "2018-07")}
eq = q("SELECT * FROM v_exception_queue ORDER BY queue_rank")
eq.round(3).to_csv(OUT / "exception_queue.csv", index=False)
S["exception_queue_reason_counts"] = eq.reason_code.value_counts().to_dict()
q("SELECT * FROM v_weekly_kpis").round(4).to_csv(OUT / "weekly_kpis.csv", index=False)

json.dump(S, open(OUT / "lanes_summary.json", "w"), indent=2, default=str)
print(json.dumps(S, indent=2, default=str))
