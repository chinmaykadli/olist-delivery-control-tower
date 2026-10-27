-- 04_lane_views.sql
-- Lane-specific analysis layer (supply chain, analyst, PM, commercial).
-- Runs after 03_views.sql. Every view respects v_params unless stated.
--
-- DuckDB notes (read before editing the window views):
--   * RANGE frames with INTERVAL need ONE ORDER BY column of type DATE or
--     TIMESTAMP. purchase_month is a DATE at the first of the month, so
--     "INTERVAL 3 MONTH PRECEDING" lands exactly on a month start. On
--     arbitrary dates, month arithmetic clamps (31 Mar - 1 month = 28 Feb).
--   * RANGE, not ROWS: a seller with no orders in a month has no row. ROWS 3
--     PRECEDING would then reach back further than 90 days; RANGE counts
--     calendar months whatever rows exist.
--   * The frame ends at 1 MONTH PRECEDING, so the label month never feeds
--     its own features. An empty frame gives NULL sums, and the WHERE
--     filter (orders_90d >= 10) drops those rows because NULL >= 10 is not
--     true. Use COALESCE if you ever need zeros instead.
--   * Outcome availability: an order bought in M-1 may not be delivered (or
--     reviewed) by the first day of M. v_seller_features_gap1 shifts the
--     frame one month further back as a sensitivity check.
--   * ASOF is a reserved word in DuckDB (ASOF joins): a column named "asof"
--     fails to parse, hence as_of_date below.
--   * "/" is floating-point division in DuckDB; the ::DOUBLE casts are there
--     for readers coming from Postgres, where integer / integer truncates.

-- Peak months by rule, not by hand: marketplace late rate of 10% or more.
CREATE OR REPLACE VIEW v_month_flags AS
SELECT m.purchase_month, m.orders, m.late_rate, m.avg_promised_days,
       m.avg_transit_days, (m.late_rate >= 0.10) AS is_peak
FROM v_monthly_metrics m, v_params p
WHERE m.purchase_month BETWEEN p.window_start AND p.window_end;

-- Seller x month aggregates used by the trailing-feature windows.
CREATE OR REPLACE VIEW v_seller_month_sums AS
SELECT seller_id, purchase_month,
       COUNT(*)                                AS orders,
       COUNT(*) FILTER (is_late)               AS late_orders,
       COUNT(*) FILTER (shipping_limit_breach) AS breaches,
       SUM(dispatch_days)                      AS dispatch_sum,
       COUNT(dispatch_days)                    AS dispatch_n,
       SUM(review_score)                       AS review_sum,
       COUNT(review_score)                     AS review_n
FROM v_order_seller_facts
GROUP BY 1, 2;

-- Trailing 90-day features for each seller-month, plus the label.
-- Label ("bad month"): seller has >= 5 orders in month M AND
-- (late rate >= 15% OR average review <= 3.0). Months with 1-4 orders are
-- NOT labelled good; they are dropped as too thin to judge.
CREATE OR REPLACE VIEW v_seller_features AS
WITH w AS (
  SELECT *,
    SUM(orders)       OVER t AS orders_90d,
    SUM(late_orders)  OVER t AS late_90d,
    SUM(breaches)     OVER t AS breaches_90d,
    SUM(dispatch_sum) OVER t AS dispatch_sum_90d,
    SUM(dispatch_n)   OVER t AS dispatch_n_90d,
    SUM(review_sum)   OVER t AS review_sum_90d,
    SUM(review_n)     OVER t AS review_n_90d
  FROM v_seller_month_sums
  WINDOW t AS (PARTITION BY seller_id ORDER BY purchase_month
               RANGE BETWEEN INTERVAL 3 MONTH PRECEDING AND INTERVAL 1 MONTH PRECEDING)
)
SELECT seller_id, purchase_month AS label_month, orders_90d,
       late_90d::DOUBLE / orders_90d                 AS late_rate_90d,
       breaches_90d::DOUBLE / orders_90d             AS breach_90d,
       dispatch_sum_90d / NULLIF(dispatch_n_90d, 0)  AS dispatch_90d,
       review_sum_90d / NULLIF(review_n_90d, 0)      AS review_90d,
       orders                                        AS label_orders,
       (late_orders::DOUBLE / orders >= 0.15
        OR review_sum / NULLIF(review_n, 0) <= 3.0)  AS label_bad
FROM w
WHERE orders_90d >= 10 AND orders >= 5;

-- Same features with a one-month gap (frame = M-4 .. M-2): sensitivity check
-- for outcomes that were not yet observable at the start of month M.
CREATE OR REPLACE VIEW v_seller_features_gap1 AS
WITH w AS (
  SELECT *,
    SUM(orders)       OVER t AS orders_90d,
    SUM(late_orders)  OVER t AS late_90d,
    SUM(breaches)     OVER t AS breaches_90d,
    SUM(dispatch_sum) OVER t AS dispatch_sum_90d,
    SUM(dispatch_n)   OVER t AS dispatch_n_90d,
    SUM(review_sum)   OVER t AS review_sum_90d,
    SUM(review_n)     OVER t AS review_n_90d
  FROM v_seller_month_sums
  WINDOW t AS (PARTITION BY seller_id ORDER BY purchase_month
               RANGE BETWEEN INTERVAL 4 MONTH PRECEDING AND INTERVAL 2 MONTH PRECEDING)
)
SELECT seller_id, purchase_month AS label_month, orders_90d,
       late_90d::DOUBLE / orders_90d                 AS late_rate_90d,
       breaches_90d::DOUBLE / orders_90d             AS breach_90d,
       dispatch_sum_90d / NULLIF(dispatch_n_90d, 0)  AS dispatch_90d,
       review_sum_90d / NULLIF(review_n_90d, 0)      AS review_90d,
       orders                                        AS label_orders,
       (late_orders::DOUBLE / orders >= 0.15
        OR review_sum / NULLIF(review_n, 0) <= 3.0)  AS label_bad
FROM w
WHERE orders_90d >= 10 AND orders >= 5;

-- Lane Pareto: lanes ranked by LATE ORDERS (volume x rate), not by rate.
CREATE OR REPLACE VIEW v_lane_pareto AS
SELECT seller_state || ' -> ' || customer_state AS lane,
       orders, late_orders, late_rate, avg_promised_days, avg_transit_days,
       freight_share,
       late_orders::DOUBLE / SUM(late_orders) OVER () AS share_of_late,
       SUM(late_orders) OVER (ORDER BY late_orders DESC, lane
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)::DOUBLE
         / SUM(late_orders) OVER ()                    AS cum_share_of_late,
       ROW_NUMBER() OVER (ORDER BY late_orders DESC, lane) AS lane_rank
FROM v_route_facts;

-- Lane lead-time variability and peak sensitivity (lanes with 300+ orders).
-- Structural lane: late outside peak months. Peak lane: late mostly inside.
CREATE OR REPLACE VIEW v_lane_variability AS
SELECT f.seller_state || ' -> ' || f.customer_state AS lane,
       COUNT(*)                                          AS orders,
       AVG(f.promised_days)                              AS avg_promised_days,
       quantile_cont(f.transit_days, 0.5)                AS transit_p50,
       quantile_cont(f.transit_days, 0.9)                AS transit_p90,
       quantile_cont(f.transit_days, 0.9)
         / NULLIF(quantile_cont(f.transit_days, 0.5), 0) AS transit_p90_p50_ratio,
       AVG(f.is_late::INT) FILTER (WHERE NOT m.is_peak)  AS late_rate_normal_months,
       AVG(f.is_late::INT) FILTER (WHERE m.is_peak)      AS late_rate_peak_months
FROM v_order_seller_facts f
JOIN v_month_flags m USING (purchase_month)
GROUP BY 1
HAVING COUNT(*) >= 300;

-- Promise curve: on-time rate if every promise on a lane were k days longer.
-- Assumes delivery times do not change when the promise changes, and says
-- nothing about conversion (not in the data).
CREATE OR REPLACE VIEW v_promise_curve AS
WITH base AS (
  SELECT f.seller_state || ' -> ' || f.customer_state AS lane,
         f.delivery_days, f.promised_days
  FROM v_order_seller_facts f, v_params p
  WHERE f.purchase_month BETWEEN p.window_start AND p.window_end
),
lanes AS (SELECT lane FROM base GROUP BY 1 HAVING COUNT(*) >= 150)
SELECT b.lane, r.k AS extra_days, COUNT(*) AS orders,
       AVG(b.promised_days) + r.k AS avg_promised_days,
       AVG((b.delivery_days <= b.promised_days + r.k)::INT) AS on_time_rate
FROM base b JOIN lanes USING (lane), range(0, 21) r(k)
GROUP BY 1, 2
UNION ALL
SELECT 'ALL LANES', r.k, COUNT(*), AVG(b.promised_days) + r.k,
       AVG((b.delivery_days <= b.promised_days + r.k)::INT)
FROM base b, range(0, 21) r(k)
GROUP BY 1, 2;

-- Promise accuracy by month: how far the estimate sits from reality.
-- slack = estimated - delivered (positive = delivered early).
CREATE OR REPLACE VIEW v_promise_accuracy AS
SELECT f.purchase_month,
       AVG(f.promise_slack_days)                     AS mean_slack_days,
       median(f.promise_slack_days)                  AS median_slack_days,
       AVG(ABS(f.promise_slack_days))                AS mean_abs_error_days,
       AVG((f.promise_slack_days >= 14)::INT)        AS share_14plus_days_early,
       AVG(f.is_late::INT)                           AS late_rate,
       AVG(f.promised_days)                          AS avg_promised_days
FROM v_order_facts f, v_params p
WHERE f.purchase_month BETWEEN p.window_start AND p.window_end
GROUP BY 1 ORDER BY 1;

-- In-transit ageing: as of each Monday d, of the orders handed to the
-- carrier 10-30 days earlier, what share is still undelivered? Knowable on
-- day d with no future information, so it can act as an early warning.
CREATE OR REPLACE VIEW v_transit_ageing AS
WITH days AS (
  SELECT range::DATE AS as_of_date
  FROM range(DATE '2017-01-02', DATE '2018-08-06', INTERVAL 7 DAY)
)
SELECT d.as_of_date,
       COUNT(*)                                       AS handed_10_30d_ago,
       AVG((f.delivered_date > d.as_of_date)::INT)          AS share_still_in_transit,
       COUNT(*) FILTER (WHERE f.delivered_date > d.as_of_date
                          AND f.estimated_date < d.as_of_date) AS overdue_now
FROM days d
JOIN v_order_facts f
  ON f.carrier_date BETWEEN d.as_of_date - 30 AND d.as_of_date - 10
GROUP BY 1 ORDER BY 1;

-- Promise guardrail backtest: when ageing >= 20% on a Monday, add k days to
-- every promise made in the following 7 days. Counts late orders avoided.
-- Same assumptions as v_promise_curve.
CREATE OR REPLACE VIEW v_guardrail_backtest AS
WITH alarms AS (
  SELECT as_of_date FROM v_transit_ageing WHERE share_still_in_transit >= 0.20
),
covered AS (
  SELECT f.*
  FROM v_order_facts f, v_params p
  WHERE f.purchase_month BETWEEN p.window_start AND p.window_end
    AND EXISTS (SELECT 1 FROM alarms a
                WHERE f.purchase_date >= a.as_of_date AND f.purchase_date < a.as_of_date + 7)
)
SELECT r.k AS extra_days,
       COUNT(*)                                                  AS orders_covered,
       COUNT(*) FILTER (WHERE delivery_days > promised_days)     AS late_now,
       COUNT(*) FILTER (WHERE delivery_days > promised_days + r.k) AS late_with_guardrail,
       (SELECT COUNT(*) FROM alarms)                             AS alarm_weeks
FROM covered, range(0, 11) r(k)
GROUP BY 1 ORDER BY 1;

-- Weekly KPI report (the "six numbers"), by purchase week. Outcomes are as
-- recorded in the final dataset, so recent weeks would be incomplete in live use.
CREATE OR REPLACE VIEW v_weekly_kpis AS
SELECT date_trunc('week', f.purchase_date)::DATE     AS purchase_week,
       COUNT(*)                                      AS orders,
       AVG((NOT f.is_late)::INT)                     AS on_time_rate,
       AVG((f.review_score <= 2)::INT)               AS share_1_2_star,
       AVG(s.shipping_limit_breach::INT)             AS breach_rate_single_seller,
       AVG(f.transit_days)                           AS avg_transit_days,
       AVG(f.promise_slack_days)                     AS avg_promise_slack_days
FROM v_order_facts f
LEFT JOIN v_order_seller_facts s USING (order_id)
CROSS JOIN v_params p
WHERE f.purchase_month BETWEEN p.window_start AND p.window_end
GROUP BY 1 ORDER BY 1;

-- Right-censoring bound by purchase month: treat every still-open order as
-- late and see how far the late rate could move.
CREATE OR REPLACE VIEW v_censoring_bound AS
WITH o AS (
  SELECT date_trunc('month', order_purchase_timestamp)::DATE AS purchase_month,
         COUNT(*) FILTER (WHERE order_status IN ('shipped','processing','invoiced','approved','created')) AS open_orders
  FROM orders GROUP BY 1
)
SELECT m.purchase_month, m.orders AS delivered_orders, o.open_orders,
       m.late_rate                                          AS observed_late_rate,
       (m.late_rate * m.orders + o.open_orders) / (m.orders + o.open_orders) AS worst_case_late_rate
FROM v_monthly_metrics m JOIN o USING (purchase_month)
WHERE m.purchase_month >= DATE '2018-01-01'
ORDER BY 1;

-- Exception queue: the review list Seller Ops would work in the week of
-- 6 Aug 2018, built from May-Jul 2018 purchases. Ranking = the one-line rule
-- (trailing late rate, ties broken by volume). Reason code = the first
-- seller-side failure that applies; otherwise the lane/carrier.
CREATE OR REPLACE VIEW v_exception_queue AS
WITH s AS (
  SELECT seller_id, any_value(seller_state) AS seller_state,
         COUNT(*)                                   AS orders_90d,
         AVG(is_late::INT)                          AS late_rate_90d,
         AVG(shipping_limit_breach::INT)            AS breach_90d,
         AVG(dispatch_days)                         AS dispatch_90d,
         AVG(review_score)                          AS review_90d,
         mode(customer_state)                       AS main_customer_state
  FROM v_order_seller_facts
  WHERE purchase_month BETWEEN DATE '2018-05-01' AND DATE '2018-07-01'
  GROUP BY 1
  HAVING COUNT(*) >= 10
)
SELECT ROW_NUMBER() OVER (ORDER BY late_rate_90d DESC, orders_90d DESC, seller_id) AS queue_rank,
       seller_id, seller_state || ' -> ' || main_customer_state AS main_lane,
       orders_90d, late_rate_90d, breach_90d, dispatch_90d, review_90d,
       CASE WHEN breach_90d >= 0.25 THEN 'misses own shipping limit'
            WHEN dispatch_90d >= 5  THEN 'slow handover to carrier'
            WHEN review_90d <= 3.5  THEN 'low reviews, check product or service'
            ELSE 'late in transit: lane or carrier' END AS reason_code,
       'Seller Ops' AS owner, 'to contact' AS status
FROM s
QUALIFY queue_rank <= 20;
