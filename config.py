# -------------------------------------------------Level Config--------------------------------------------------------+
level_tf = '1h'               # The timeframe for searching levels. Can be '1h' '4h' '1d'
limit = 100                   # Number of bars for searching levels
volume_sma_period = 24        # SMA period for volume.
vol_coeff = 2                 # The coefficient by how much the volume in one of the bars of the candlestick pattern should be higher than the SMA
percent_move_from_level = 3   # By what percentage should the price move away from the level for its validation
level_width = 1               # The Level's width in a percent of instrument

# --------------------------------------------------Big orders---------------------------------------------------------+
min_orders_qty = 3            # Minimal quantity of the big orders
min_vol_order = 100_000       # One order's minimal volume
request_period_sec = 20       # The frequency of requests
validate_order_sec = 60       # How long must the orders standing to be considered valid
range_width = 2               # The max width of the range for placed big orders


