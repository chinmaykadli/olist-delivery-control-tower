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
--   dispatch days   = purchase -> carrier handover (seller-controllable).
--   transit days    = carrier handover -> customer delivery (carrier).
--   shipping-limit breach = carrier handover after the item's
--                     shipping_limit_date (the seller's own deadline).
--   ANALYSIS WINDOW = purchases Sep 2016 - May 2018. Jun-Aug 2018 is excluded:
--                     its late orders were still in transit at the data
--                     cut-off (deliveries stop 2018-10-17), so its late rate
--                     is biased down (right-censoring).

CREATE OR REPLACE VIEW v_order_facts AS
WITH order_rollup AS (
  SELECT order_id, SUM(price) AS items_value, SUM(freight_value) AS freight_value,
         COUNT(*) AS n_items, COUNT(DISTINCT seller_id) AS n_sellers
  FROM order_items GROUP BY 1
),
order_review AS (
  SELECT order_id, AVG(review_score::DOUBLE) AS review_score,
         MIN(review_creation_date)::date AS first_review_date
  FROM order_reviews GROUP BY 1
),
order_category AS (
  SELECT order_id, category_en FROM (
    SELECT i.order_id,
           COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_en,
           ROW_NUMBER() OVER (PARTITION BY i.order_id ORDER BY i.price DESC) AS rn
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
  (o.order_delivered_customer_date::date - o.order_purchase_timestamp::date) AS delivery_days,
  (o.order_delivered_carrier_date::date - o.order_purchase_timestamp::date)   AS dispatch_days,
  (o.order_delivered_customer_date::date - o.order_delivered_carrier_date::date) AS transit_days,
  CASE WHEN o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date
       THEN TRUE ELSE FALSE END                             AS is_late,
  GREATEST(o.order_delivered_customer_date::date - o.order_estimated_delivery_date::date, 0) AS days_late,
  r.review_score,
  CASE WHEN r.first_review_date < o.order_delivered_customer_date::date
       THEN TRUE ELSE FALSE END                             AS review_before_delivery,
  ru.items_value, ru.freight_value, ru.n_items, ru.n_sellers, cat.category_en
FROM orders o
JOIN order_rollup ru USING (order_id)
LEFT JOIN order_review r USING (order_id)
LEFT JOIN order_category cat USING (order_id)
LEFT JOIN customers c USING (customer_id)
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;

-- Order x seller for SINGLE-SELLER orders (delivered).
-- Carrier handover and review are order-level facts, so multi-seller orders
-- cannot be attributed to one seller and are excluded from seller metrics.
CREATE OR REPLACE VIEW v_order_seller_facts AS
SELECT
  f.purchase_date, f.purchase_month, f.order_status,
  f.carrier_date, f.delivered_date, f.estimated_date,
  f.is_late, f.days_late, f.delivery_days, f.dispatch_days, f.transit_days,
  f.review_score, f.customer_state,
  i.seller_id, s.seller_state,
  i.shipping_limit_date::date AS shipping_limit,
  CASE WHEN f.carrier_date > i.shipping_limit_date::date
       THEN TRUE ELSE FALSE END AS shipping_limit_breach,
  SUM(i.price + i.freight_value) AS seller_order_value,
  SUM(i.freight_value) AS seller_freight_value
FROM v_order_facts f
JOIN order_items i USING (order_id)
JOIN sellers s USING (seller_id)
WHERE f.n_sellers = 1
GROUP BY ALL;

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

-- Route facts: seller state -> customer state (single-seller delivered orders).
CREATE OR REPLACE VIEW v_route_facts AS
SELECT
  seller_state, customer_state,
  COUNT(*)                                        AS orders,
  COUNT(*) FILTER (is_late)::DOUBLE / COUNT(*)    AS late_rate,
  AVG(delivery_days)                              AS avg_delivery_days,
  AVG(transit_days)                               AS avg_transit_days,
  AVG(seller_freight_value)                       AS avg_freight
FROM v_order_seller_facts
GROUP BY 1, 2;

-- Monthly marketplace-level metrics (control tower headline numbers).
CREATE OR REPLACE VIEW v_monthly_metrics AS
SELECT
  purchase_month,
  COUNT(*)                                        AS orders,
  COUNT(*) FILTER (is_late)::DOUBLE / COUNT(*)    AS late_rate,
  AVG((NOT is_late)::INT)                         AS on_time_rate,
  AVG(review_score)                               AS avg_review,
  SUM(items_value)                                AS items_gmv,
  SUM(freight_value)                              AS freight_gmv
FROM v_order_facts
GROUP BY 1 ORDER BY 1;

-- Cancellation rate per seller x month (single-seller orders; cancelled
-- orders are counted from the orders table, delivered ones from the facts).
CREATE OR REPLACE VIEW v_seller_cancellations AS
SELECT
  i.seller_id,
  date_trunc('month', o.order_purchase_timestamp)::date AS purchase_month,
  COUNT(*) AS orders,
  COUNT(*) FILTER (o.order_status = 'canceled') AS canceled
FROM orders o
JOIN order_items i USING (order_id)
WHERE o.order_status IN ('delivered', 'canceled')
  AND (SELECT COUNT(DISTINCT seller_id) FROM order_items x WHERE x.order_id = o.order_id) = 1
GROUP BY 1, 2;
