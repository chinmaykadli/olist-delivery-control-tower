-- 02_quality_checks.sql
-- Data quality checks written as queries. Each check returns a count;
-- a count of 0 means the check passes. Results are printed by build_db.py
-- and the non-zero ones are logged in the PM pack RAID log.

-- Q1. Duplicate order_ids (expect 0)
SELECT 'duplicate_order_ids' AS check_name, COUNT(*) - COUNT(DISTINCT order_id) AS failures FROM orders;

-- Q2. Duplicate seller_ids (expect 0)
SELECT 'duplicate_seller_ids' AS check_name, COUNT(*) - COUNT(DISTINCT seller_id) AS failures FROM sellers;

-- Q3. Delivered orders missing a delivery timestamp (known issue, logged)
SELECT 'delivered_orders_missing_delivery_date' AS check_name, COUNT(*) AS failures
FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

-- Q4. Orders with no items (orphan orders)
SELECT 'orders_with_no_items' AS check_name, COUNT(*) AS failures
FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.order_id);

-- Q5. Items referencing products not in the products table
SELECT 'items_with_unknown_product' AS check_name, COUNT(*) AS failures
FROM order_items i WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.product_id = i.product_id);

-- Q6. Products with no category name
SELECT 'products_missing_category' AS check_name, COUNT(*) AS failures
FROM products WHERE product_category_name IS NULL;

-- Q7. Review scores outside 1-5 (expect 0)
SELECT 'review_scores_out_of_range' AS check_name, COUNT(*) AS failures
FROM order_reviews WHERE review_score NOT BETWEEN 1 AND 5;

-- Q8. Reviews pointing at unknown orders
SELECT 'reviews_with_unknown_order' AS check_name, COUNT(*) AS failures
FROM order_reviews r WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.order_id = r.order_id);

-- Q9. Delivered orders with no review (known gap, reported on dashboard)
SELECT 'delivered_orders_without_review' AS check_name, COUNT(*) AS failures
FROM orders o WHERE o.order_status = 'delivered'
  AND NOT EXISTS (SELECT 1 FROM order_reviews r WHERE r.order_id = o.order_id);

-- Q10. Payments whose total does not cover item price + freight (tolerance 0.01)
SELECT 'payment_total_mismatch' AS check_name, COUNT(*) AS failures
FROM (
  SELECT o.order_id
  FROM orders o
  JOIN (SELECT order_id, SUM(price + freight_value) AS items_total FROM order_items GROUP BY 1) i USING (order_id)
  JOIN (SELECT order_id, SUM(payment_value) AS paid FROM order_payments GROUP BY 1) p USING (order_id)
  WHERE ABS(i.items_total - p.paid) > 0.01
) t;

-- Q11. Delivered orders delivered before they were purchased (expect 0)
SELECT 'delivered_before_purchase' AS check_name, COUNT(*) AS failures
FROM orders WHERE order_status = 'delivered'
  AND order_delivered_customer_date < order_purchase_timestamp;
