# One command rebuild: make all   (needs: pip install -r requirements.txt)
PY ?= python

.PHONY: all data db analysis dashboard check clean

all: data db analysis dashboard check

data:
	@test -f data/olist_orders_dataset.csv || ./scripts/download_data.sh

db:
	$(PY) analysis/build_db.py

analysis:
	$(PY) analysis/run_analysis.py
	$(PY) analysis/scorecard_backtest.py
	$(PY) analysis/lanes_analysis.py

dashboard:
	$(PY) dashboard/build_dashboard.py
	$(PY) dashboard/build_ops.py

check:
	$(PY) scripts/check_numbers.py

clean:
	rm -f olist.duckdb olist.duckdb.wal
