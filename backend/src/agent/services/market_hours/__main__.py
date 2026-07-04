from .market_hours import MarketHoursService, AssetType

service = MarketHoursService()
for asset_type in AssetType:
    print(service.get_status(asset_type).description)
    print("===" * 10)
