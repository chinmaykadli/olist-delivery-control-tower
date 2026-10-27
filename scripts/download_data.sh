#!/usr/bin/env bash
# Downloads the Olist Brazilian E-Commerce public dataset CSVs.
# Source: Olist's own public mirror on GitHub (same files as the Kaggle dataset
# https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
# The geolocation file is skipped: the analysis works at state level and the
# file is ~40 MB of zip-prefix coordinates.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets"
FILES="olist_customers_dataset.csv olist_orders_dataset.csv olist_order_items_dataset.csv olist_order_payments_dataset.csv olist_order_reviews_dataset.csv olist_products_dataset.csv olist_sellers_dataset.csv product_category_name_translation.csv"
mkdir -p data
for f in $FILES; do
  echo "downloading $f"
  curl -sSL -o "data/$f" "$BASE/$f"
done
echo "done. Row counts:"
wc -l data/*.csv
