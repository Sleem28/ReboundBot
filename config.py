# ------------------------------Level Config-------------------------------------+
level_tf = '1h'  # Can be '1h' '4h' '1d'
limit = 92  # Quantity of candles required for calculation levels
volume_sma_period = 24
vol_coeff = 2
percent_move_from_level = 3
level_width = 1  # The Level's width in a percent of instrument
# -----------------------------------Big orders----------------------------------+
min_orders_qty = 3  # Minimal quantity of big orders
min_vol_order = 50_000  # a one order's minimal volume
request_period_sec = 20  # a frequency of requests
validate_order_sec = 60  # how many seconds the order has got standing
range_width = 2  # the max width of the range for placed big orders
# ---------------------------Cluster option--------------------------------------+
cluster_tf = '5m'
cluster_price_in_line = 1
cluster_qty = 3