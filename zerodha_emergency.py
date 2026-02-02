from kiteconnect import KiteConnect

def emergency_exit_fno(kite: KiteConnect):
    print("🛑 Cancelling F&O orders...")

    orders = kite.orders()
    for o in orders:
        if (
            o["exchange"] == "NFO" and
            o["status"] in ("OPEN", "TRIGGER PENDING")
        ):
            kite.cancel_order(
                variety=o["variety"],
                order_id=o["order_id"]
            )

    print("🛑 Squaring off F&O positions...")

    positions = kite.positions()["net"]
    for p in positions:
        if (
            p["exchange"] == "NFO" and
            p["quantity"] != 0
        ):
            kite.place_order(
                variety=KiteConnect.VARIETY_REGULAR,
                exchange="NFO",
                tradingsymbol=p["tradingsymbol"],
                transaction_type=(
                    KiteConnect.TRANSACTION_TYPE_SELL
                    if p["quantity"] > 0
                    else KiteConnect.TRANSACTION_TYPE_BUY
                ),
                quantity=abs(p["quantity"]),
                order_type=KiteConnect.ORDER_TYPE_MARKET,
                product=p["product"]  # MIS / NRML
            )

    print("✅ F&O Emergency exit completed")
