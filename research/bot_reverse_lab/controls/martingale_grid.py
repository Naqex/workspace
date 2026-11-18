"""Synthetic unsafe control, inspected only; never run this sample."""
if last_profit < 0:
    lot *= 2
    mt5.order_send({'type': 'BUY', 'volume': lot, 'sl': 0})
