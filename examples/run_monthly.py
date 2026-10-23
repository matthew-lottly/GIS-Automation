"""Monthly county market maps: set the parameters, run, done."""
from county_market import Config, Pipeline

# 1. Which counties to map
AREAS = [
    "Harris", "Fort Bend", "Montgomery", "Brazoria",
    "Galveston", "Waller", "Liberty", "Chambers",
]

# 2. What to map, and for which period
METRIC = "median_sale_price"
PERIOD = "latest"            # or a date such as "2026-02-28"

# 3. Quality rule: ZIPs with fewer sales are flagged, not mapped
MIN_SALES = 10

# Everything else is automatic: spatial join, QA checks,
# one map per county, summary table, change log, run.log
Pipeline(Config(AREAS, METRIC, PERIOD, MIN_SALES)).run()
