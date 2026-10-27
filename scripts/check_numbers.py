"""Fail the build if a number quoted in the README or memo drifts from outputs/.

Each claim below is rendered FROM the JSON outputs and must appear verbatim in
the listed documents. A second list of stale phrases (numbers from earlier
versions) must appear nowhere. Run: python scripts/check_numbers.py
Exit code 0 = all claims match; 1 = at least one mismatch.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
k = json.load(open(OUT / "kpi_summary.json"))
s = json.load(open(OUT / "scorecard_summary.json"))
ln = json.load(open(OUT / "lanes_summary.json"))

README, MEMO = "README.md", "memo/decision-memo.md"
BOTH = (README, MEMO)
pct = lambda x: f"{x * 100:.0f}%"
pct1 = lambda x: f"{x * 100:.1f}%"
g3, g5 = ln["guardrail_plus3d"], ln["guardrail_plus5d"]
d = k["dispatch_vs_transit"]

CLAIMS = [
    (BOTH, f"{k['orders_analysed']:,}", "orders analysed"),
    (BOTH, f"{pct1(k['late_rate'])} late", "late rate"),
    (BOTH, f"{pct(ln['peak_share_of_orders'])} of orders", "peak share of orders"),
    (BOTH, f"{pct(ln['peak_share_of_late_orders'])}", "peak share of late orders"),
    (BOTH, f"{ln['promise_days_normal_vs_peak'][1]} days against {ln['promise_days_normal_vs_peak'][0]}", "promise peak vs normal"),
    (BOTH, f"{ln['transit_days_normal_vs_peak'][1]} days against {ln['transit_days_normal_vs_peak'][0]}", "transit peak vs normal"),
    (BOTH, f"from {ln['feb_mar_2018_weekly_promise_range'][0]} to {ln['feb_mar_2018_weekly_promise_range'][1]} days", "Feb-Mar promise cut"),
    (BOTH, f"climbed to {pct(ln['feb_mar_2018_weekly_late_peak'])}", "weekly late peak"),
    (BOTH, f"{d['late']['dispatch']} vs {d['on_time']['dispatch']}", "dispatch late vs on time"),
    (BOTH, f"{d['late']['transit']}", "transit late"),
    (BOTH, ln["ageing_first_alarm_2018"], "first 2018 ageing alarm"),
    (BOTH, f"{ln['ageing_lead_weeks_vs_delivered_signal']} weeks", "early-warning lead"),
    (BOTH, f"{g5['late_avoided']} late orders", "guardrail +5 late avoided"),
    (BOTH, f"{pct(g5['share_of_all_window_late_orders'])} of", "guardrail +5 share"),
    (README, f"{ln['guardrail_alarm_weeks']} alarm weeks", "alarm weeks"),
    (MEMO, f"{g3['late_avoided']}", "guardrail +3 late avoided"),
    (BOTH, f"{ln['median_promise_slack_days_window']:.0f} days early", "median slack"),
    (BOTH, f"+{ln['sp_al_days_to_reach_93pct']} days", "SP-AL days to 93%"),
    (BOTH, f"{pct(ln['sp_al_on_time_by_extra_days']['0'])} on time", "SP-AL on time today"),
    (BOTH, f"{pct(ln['top2_lanes_share_of_late'])} of late orders", "top-2 lane share"),
    (BOTH, f"{pct1(ln['lane SP -> RJ']['late_normal'])} late in normal months", "SP-RJ normal"),
    (BOTH, f"{pct1(ln['lane SP -> RJ']['late_peak'])} in peaks", "SP-RJ peak"),
    (BOTH, f"{pct(k['late_reviews_answered_before_delivery'])} of late-order reviews", "answered before delivery"),
    (BOTH, f"{k['avg_review_late_answered_after_delivery']}", "late review after delivery"),
    (BOTH, f"{k['avg_review_on_time']} on time", "on-time review"),
    (BOTH, f"{ln['repeat_rate_on_time_vs_late_first_order'][1] * 100:.2f}% vs "
           f"{ln['repeat_rate_on_time_vs_late_first_order'][0] * 100:.2f}%", "repeat rates"),
    (BOTH, f"{ln['repeat_adjusted_odds_ratio_late'][0]:.2f}", "adjusted odds ratio"),
    (BOTH, f"{ln['repeat_adjusted_odds_ratio_late'][1]:.2f} to {ln['repeat_adjusted_odds_ratio_late'][2]:.2f}", "odds ratio CI"),
    (BOTH, f"{ln['lost_repeat_orders_estimate'][0]} lost repeat orders", "lost repeat orders"),
    (BOTH, f"{pct(s['queue_hit_rate_at_k'])}", "queue hit rate"),
    (BOTH, f"{pct(s['queue_hit_rate_ci'][0])} to {pct(s['queue_hit_rate_ci'][1])}", "queue hit CI"),
    (BOTH, f"{pct(s['test_base_rate'])}", "test base rate"),
    (BOTH, f"{s['queue_lift_at_k']}x", "queue lift"),
    (README, f"({pct(s['model_hit_rate_at_k'])})", "model hit rate"),
    (MEMO, f"{k['sellers_analysed_min30_orders']} sellers", "sellers with 30+ orders"),
    (MEMO, f"{pct1(k['worst_10pct_late_rate'])} late against {pct1(k['rest_late_rate'])}", "worst decile vs rest"),
    (MEMO, f"Spearman {ln['persistence_spearman'][0]} across {ln['persistence_spearman'][1]} sellers", "persistence"),
    (MEMO, f"ICC {ln['pilot_icc']}", "pilot ICC"),
    (MEMO, f"{pct1(ln['pilot_control_late_rate_queued_sellers'])} to {pct1(ln['pilot_target_late_rate'])}", "pilot effect"),
    (MEMO, f"{ln['pilot_sellers_per_arm']} sellers per arm", "pilot sellers per arm"),
    (MEMO, f"about {ln['pilot_months_of_intake_at_10_per_arm']} months", "pilot months"),
    (MEMO, f"drop to {pct1(ln['pilot_8wk_minimum_detectable_late_rate'])}", "8-week MDE"),
    (README, f"June {pct1(ln['censoring_jun_jul_2018']['2018-06'][0])} -> {pct1(ln['censoring_jun_jul_2018']['2018-06'][1])}", "June bound"),
    (README, f"July {pct1(ln['censoring_jun_jul_2018']['2018-07'][0])} -> {pct1(ln['censoring_jun_jul_2018']['2018-07'][1])}", "July bound"),
]

STALE = ["77,867", "5,862", "1.42x", "76% of late", "Mar-May 2018", "Jan-May 2018",
         "80th percentile", "written before the parcel", "17.1% to 11.5%", "3.4 stars", "R$276k",
         "(26 sellers)", "~1,200 orders per arm"]
STALE_FILES = [README, MEMO] + [str(p.relative_to(ROOT)) for p in (ROOT / "pm").glob("*.md")] + \
              [str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.html")]

fails = 0
# Normalise whitespace so a phrase wrapped across lines still matches.
text = {f: " ".join((ROOT / f).read_text().split()) for f in set(STALE_FILES) | set(BOTH)}
CLAIMS = [((f,) if isinstance(f, str) else f, p, l) for f, p, l in CLAIMS]
for files, phrase, label in CLAIMS:
    for f in files:
        if phrase not in text[f]:
            print(f"FAIL  {f}: expected '{phrase}'  ({label})"); fails += 1
for f in STALE_FILES:
    for phrase in STALE:
        if phrase in text[f]:
            print(f"STALE {f}: contains '{phrase}'"); fails += 1
n_checks = sum(len(f) for f, _, _ in CLAIMS) + len(STALE) * len(STALE_FILES)
print(f"{n_checks - fails} of {n_checks} checks passed")
sys.exit(1 if fails else 0)
