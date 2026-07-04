from .technical_indicator import TechnicalIndicatorService
from .session_context import SessionContextService
from .market_statistics import MarketStatisticsService

# =========== Example Usage of TechnicalIndicatorService ===========
# svc = TechnicalIndicatorService(
#     asset_type="commodity",
#     symbol="XAU/USD",
#     timezone="UTC",
#     interval="1h"
# )
# df_daily = svc.get_daily_bars(days=20)

# print(df_daily)

# =========== Example Usage of SessionContextService and StatsService ===========
session_svc = SessionContextService()

for sym, atype in [("EUR/USD", "forex"), ("XAU/USD", "commodity"), ("BTC/USD", "crypto"), ("AAPL", "stock")]:
    snap = session_svc.get_snapshot(sym, atype)
    stats_svc = MarketStatisticsService(symbol=sym, timezone="UTC", asset_type=atype)
    stats = stats_svc.get_daily_range_context(lookback=20, is_live=snap.is_live)
    print("<session-context>")
    print(snap.summary)
    print("</session-context>")
    print("")
    print("<range-context>")
    print(stats.summary)
    print("</range-context>")
    print("=" * 60)
    print("")

