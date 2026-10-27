-- 03_views.sql
-- Analytics layer. Every number in the memo and dashboard traces to one of
-- these views.
--
-- Metric definitions (also in README):
--   late            = delivered to the customer on a LATER CALENDAR DATE than
--                     the estimated delivery date (the estimate has no time
--                     component; a delivery on the estimated day is on time).
--                     Delivered orders only, so cancelled orders never count
--                     against a seller.
--   on-time rate    = share of delivered orders that are not late.
--   dispatch days   = purchase -> carrier handover (seller side; includes
--                     payment approval, ~0.5 days on average).
--   transit days    = carrier handover -> customer delivery (carrier).
--   shipping-limit breach = carrier handover after the item's
--                     shipping_limit_date (the seller's own deadline).
--   review answered before delivery = review_answer_timestamp earlier than
--                     the delivery timestamp. (review_creation_date is the
--                     date the survey was SENT, not answered.)
--   ANALYSIS WINDOW = purchases Sep 2016 - Jul 2018, defined once in v_params.
--                     Aug 2018 onwards is excluded: the data cut-off
--                     (deliveries stop 2018-10-17) leaves too little time for
--                     late orders to land. Jun-Jul 2018 are kept; the
--                     worst-case open-order bound is in v_censoring_bound
--                     (04_lane_views.sql).

-- Single source of truth for the analysis window. Scripts read it from here.
CREATE OR REPLACE VIEW v_params AS
SELECT DATE '2016-09-01' AS window_start,
       DATE '2018-07-01' AS window_end;      -- last purchase MONTH included

CREATE OR REPLACE VIEW v_order_facts AS
WITH order_rollup AS (
  SELECT order_id, SUM(price) AS items_value, SUM(freight_value) AS freight_value,
         COUNT(*) AS n_items, COUNT(DISTINCT seller_id) AS n_sellers
  FROM order_items GROUP BY 1
),
order_review AS (
  SELECT order_id, AVG(review_score::DOUBLE) AS review_score,
         MIN(review_creation_date)    AS survey_sent_ts,
         MIN(review_answer_timestamp) AS first_answer_ts
  FROM order_reviews GROUP BY 1
),
order_category AS (
  SELECT order_id, category_en, weight_g FROM (
    SELECT i.order_id,
           COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_en,
           p.product_weight_g AS weight_g,
           ROW_NUMBER() OVER (PARTITION BY i.order_id ORDER BY i.price DESC, i.order_item_id) AS rn
    FROM order_items i
    LEFT JOIN products p USING (product_id)
    LEFT JOIN category_translation t USING (product_category_name)
  ) WHERE rn = 1
)
SELECT
  o.order_id, o.customer_id, c.customer_unique_id, c.customer_state, o.order_status,
  o.order_purchase_timestamp::date                          AS purchase_date,
  date_trunc('month', o.order_purchase_timestamp)::date     AS purchase_month,
  o.order_delivered_carrier_date::date                      AS carrier_date,
  o.order_delivered_customer_date::date                     AS delivered_date,
  o.order_estimated_delivery_date::date                     AS estimated_date,
  (o.order_delivered_customer_date::date - o.order_purchase_timestamp::date)  AS delivery_days,
  (o.order_estimated_delivery_date::date - o.order_purchase_timestamp::date)  AS promised_days,
  (o.order_delivered_carrier_date::date - o.order_purchase_timestamp::date)   AS dispatch_days,
  (o.order_delivered_customer_date::date - o.order_delivered_carrier_date::date) AS transit_days,
  (o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date) AS is_late,
  GREATEST(o.order_delivered_customer_date::date - o.order_estimated_delivery_date::date, 0) AS days_late,
  (o.order_estimated_delivery_date::date - o.order_delivered_customer_date::date) AS promise_slack_days,
  r.review_score,
  COALESCE(r.first_answer_ts < o.order_delivered_customer_date, FALSE) AS review_before_delivery,
  COALESCE(r.survey_sent_ts::date < o.order_delivered_customer_date::date, FALSE) AS survey_sent_before_delivery,
  ru.items_value, ru.freight_value, ru.n_items, ru.n_sellers, cat.category_en, cat.weight_g
FROM orders o
JOIN order_rollup ru USING (order_id)
LEFT JOIN order_review r USING (order_id)
LEFT JOIN order_category cat USING (order_id)
LEFT JOIN customers c USING (customer_id)
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;

-- Order x seller for SINGLE-SELLER orders (delivered). One row per order.
-- Carrier handover and review are order-level facts, so multi-seller orders
-- cannot be attributed to one seller and are excluded from seller metrics.
-- order_id is in the grouping: without it, two orders from one seller with
-- identical dates and score collapse into one row (476 orders were lost).
CREATE OR REPLACE VIEW v_order_seller_facts AS
WITH seller_items AS (
  SELECT order_id, seller_id,
         MAX(shipping_limit_date)::date AS shipping_limit,
         SUM(price + freight_value)     AS seller_order_value,
         SUM(freight_value)             AS seller_freight_value
  FROM order_items
  GROUP BY 1, 2
)
SELECT
  f.order_id, f.customer_unique_id,
  f.purchase_date, f.purchase_month, f.order_status,
  f.carrier_date, f.delivered_date, f.estimated_date, f.promised_days,
  f.is_late, f.days_late, f.delivery_days, f.dispatch_days, f.transit_days,
  f.review_score, f.customer_state, f.category_en, f.weight_g,
  si.seller_id, s.seller_state, si.shipping_limit,
  (f.carrier_date > si.shipping_limit) AS shipping_limit_breach,
  si.seller_order_value, si.seller_freight_value
FROM v_order_facts f
JOIN seller_items si USING (order_id)
JOIN sellers s USING (seller_id)
WHERE f.n_sellers = 1;

-- Seller x month rollup (single-seller orders, delivered).
CREATE OR REPLACE VIEW v_seller_month AS
SELECT
  seller_id, purchase_month,
  COUNT(*)                                        AS orders,
  COUNT(*) FILTER (is_late)                       AS late_orders,
  COUNT(*) FILTER (is_late)::DOUBLE / COUNT(*)    AS late_rate,
  COUNT(*) FILTER (shipping_limit_breach)::DOUBLE / COUNT(*) AS breach_rate,
  AVG(dispatch_days)                              AS avg_dispatch_days,
  AVG(review_score)                               AS avg_review,
  SUM(seller_order_value)                         AS gmv
FROM v_order_seller_facts
GROUP BY 1, 2;

-- Route (lane) facts inside the analysis window: seller state -> customer state.
CREATE OR REPLACE VIEW v_route_facts AS
SELECT
  seller_state, customer_state,
  COUNT(*)                                        AS orders,
  COUNT(*) FILTER (is_late)                       AS late_orders,
  COUNT(*) FILTER (is_late)::DOUBLE / COUNT(*)    AS late_rate,
  AVG(promised_days)                              AS avg_promised_days,
  AVG(delivery_days)                              AS avg_delivery_days,
  AVG(transit_days)                               AS avg_transit_days,
  AVG(seller_freight_value)                       AS avg_freight,
  SUM(seller_freight_value) / SUM(seller_order_value) AS freight_share
FROM v_order_seller_facts, v_params
WHERE purchase_month BETWEEN window_start AND window_end
GROUP BY 1, 2;

-- Monthly marketplace-level metrics (control tower headline numbers).
CREATE OR REPLACE VIEW v_monthly_metrics AS
SELECT
  purchase_month,
  COUNT(*)                                        AS orders,
  COUNT(*) FILTER (is_late)::DOUBLE / COUNT(*)    AS late_rate,
  AVG((NOT is_late)::INT)                         AS on_time_rate,
  AVG(review_score)                               AS avg_review,
  AVG(promised_days)                              AS avg_promised_days,
  AVG(transit_days)                               AS avg_transit_days,
  AVG(dispatch_days)                              AS avg_dispatch_days,
  SUM(items_value)                                AS items_gmv,
  SUM(freight_value)                              AS freight_gmv
FROM v_order_facts
GROUP BY 1 ORDER BY 1;

-- v_seller_cancellations was removed (28 Oct): it counted item rows, not
-- orders, and 603 of 609 'unavailable' and 164 of 625 'canceled' orders have
-- no items, so most failed orders cannot be attributed to a seller at all.
-- See README Limits.
