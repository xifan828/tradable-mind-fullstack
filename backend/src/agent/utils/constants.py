import datetime
#from backend.service.central_banks import FED, ECB, BOJ

# Get the current date
CURRENT_DATE = datetime.datetime.now()

# Format the date to "Month Year"
FORMATED_DATE = CURRENT_DATE.strftime("%B %Y")

CURRENCY_PAIRS = ["EUR/USD", "USD/JPY", "GBP/USD", "USD/CNH"]

CURRENCIES = ["EUR", "USD", "JPY", "GBP", "CNH"]

#CURRENCY_PAIRS = ["EUR/USD", "USD/JPY"]

PAIRS = [i.replace("/", "_").lower() for i in CURRENCY_PAIRS]

ECONOMIC_INDICATORS_WEBSITES = {
    "USD": {
        "Fed Fund Rate": "https://tradingeconomics.com/united-states/interest-rate",
        "Core PCE YoY": "https://tradingeconomics.com/united-states/core-pce-price-index-annual-change",
        "PCE YoY": "https://tradingeconomics.com/united-states/pce-price-index-annual-change",
        "GDP QoQ": "https://tradingeconomics.com/united-states/gdp-growth",
        "ISM Manufacturing PMI": "https://tradingeconomics.com/united-states/business-confidence",
        "ISM Services PMI": "https://tradingeconomics.com/united-states/non-manufacturing-pmi",
        "Retail Sales MoM": "https://tradingeconomics.com/united-states/retail-sales",
        "Unemployment Rate": "https://tradingeconomics.com/united-states/unemployment-rate",
        "NFP": "https://tradingeconomics.com/united-states/non-farm-payrolls",
        "Average Hourly Earnings MoM": "https://tradingeconomics.com/united-states/average-hourly-earnings",
        "Balance of Trade": "https://tradingeconomics.com/united-states/balance-of-trade"
},

    "EUR": {
        "ECB Rate (Deposit Facility Rate)": "https://tradingeconomics.com/euro-area/interest-rate",
        "Core HICP YoY": "https://tradingeconomics.com/euro-area/core-inflation-rate",
        "HICP YoY": "https://tradingeconomics.com/euro-area/inflation-cpi",
        "GDP QoQ": "https://tradingeconomics.com/euro-area/gdp-growth",
        "HCOB Manufacturing PMI": "https://tradingeconomics.com/euro-area/manufacturing-pmi",
        "HCOB Services PMI": "https://tradingeconomics.com/euro-area/services-pmi",
        "Unemployment Rate": "https://tradingeconomics.com/euro-area/unemployment-rate",
        "Negotiated Wage Growth": "https://tradingeconomics.com/euro-area/negotiated-wage-growth",
        "Balance of Trade": "https://tradingeconomics.com/euro-area/balance-of-trade"
},

    "JPY": {
        "BOJ Rate": "https://tradingeconomics.com/japan/interest-rate",
        "Core CPI YoY": "https://tradingeconomics.com/japan/core-inflation-rate",
        "CPI YoY": "https://tradingeconomics.com/japan/inflation-cpi",
        "GDP QoQ": "https://tradingeconomics.com/japan/gdp-growth",
        "Jibun Bank Manufacturing PMI": "https://tradingeconomics.com/japan/manufacturing-pmi",
        "Jibun Bank Services PMI": "https://tradingeconomics.com/japan/services-pmi",
        "Retail Sales YoY": "https://tradingeconomics.com/japan/retail-sales-annual",
        "Unemployment Rate": "https://tradingeconomics.com/japan/unemployment-rate",
        "Wage Growth": "https://tradingeconomics.com/japan/wage-growth",
        "Balance of Trade": "https://tradingeconomics.com/japan/balance-of-trade"
},

    "GBP": {
        "BOE Rate": "https://tradingeconomics.com/united-kingdom/interest-rate",
        "Core CPI YoY": "https://tradingeconomics.com/united-kingdom/core-inflation-rate",
        "CPI YoY": "https://tradingeconomics.com/united-kingdom/inflation-cpi",
        "GDP QoQ": "https://tradingeconomics.com/united-kingdom/gdp-growth",
        "S&P Manufacturing PMI": "https://tradingeconomics.com/united-kingdom/manufacturing-pmi",
        "S&P Services PMI": "https://tradingeconomics.com/united-kingdom/services-pmi",
        "Retail Sales": "https://tradingeconomics.com/united-kingdom/retail-sales",
        "Unemployment Rate": "https://tradingeconomics.com/united-kingdom/unemployment-rate",
        "Average Weekly Earnings Growth": "https://tradingeconomics.com/united-kingdom/wage-growth",
        "Balance of Trade": "https://tradingeconomics.com/united-kingdom/balance-of-trade"
},

    "CNH": {
        "China Loan Prime Rate": "https://tradingeconomics.com/china/interest-rate",
        "Core CPI YoY": "https://tradingeconomics.com/china/core-inflation-rate",
        "CPI YoY": "https://tradingeconomics.com/china/inflation-cpi",
        "GDP QoQ": "https://tradingeconomics.com/china/gdp-growth",
        "NBS Manufacturing PMI": "https://tradingeconomics.com/china/business-confidence",
        "Caixin Manufacturing PMI": "https://tradingeconomics.com/china/manufacturing-pmi",
        "Retail Sales YoY": "https://tradingeconomics.com/china/retail-sales-annual",
        "Industrial Production YoY": "https://tradingeconomics.com/china/industrial-production",
        "Unemployment Rate": "https://tradingeconomics.com/china/unemployment-rate",
        "Balance of Trade": "https://tradingeconomics.com/china/balance-of-trade",
        "Export": "https://tradingeconomics.com/china/exports-yoy",
        "Import": "https://tradingeconomics.com/china/imports-yoy"
    }
}

ECONOMIC_INDICATORS = {
    "rate": {
        "USD": ["Fed Fund Rate"],
        "EUR": ["ECB Rate (Deposit Facility Rate)"],
        "JPY": ["BOJ Rate"],
        "GBP": ["BOE Rate"],
        "CNH": ["China Loan Prime Rate"]
    },

    "inflation": {
        "USD": ["Core PCE YoY", "PCE YoY"],
        "EUR": ["Core HICP YoY", "HICP YoY"],
        "JPY": ["Core CPI YoY", "CPI YoY"],
        "GBP": ["Core CPI YoY", "CPI YoY"],
        "CNH": ["Core CPI YoY", "CPI YoY"]
    },

    "growth": {
        "USD": ["GDP QoQ", "ISM Manufacturing PMI", "ISM Services PMI", "Retail Sales MoM"],
        "EUR": ["GDP QoQ", "HCOB Manufacturing PMI", "HCOB Services PMI"],
        "JPY": ["GDP QoQ", "Jibun Bank Manufacturing PMI", "Jibun Bank Services PMI", "Retail Sales YoY"],
        "GBP": ["GDP QoQ", "S&P Manufacturing PMI", "S&P Services PMI", "Retail Sales"],
        "CNH": ["GDP QoQ", "NBS Manufacturing PMI", "Caixin Manufacturing PMI", "Retail Sales YoY", "Industrial Production YoY"]
    },

    "employment": {
        "USD": ["Unemployment Rate", "NFP", "Average Hourly Earnings MoM"],
        "EUR": ["Unemployment Rate", "Negotiated Wage Growth"],
        "JPY": ["Unemployment Rate", "Wage Growth"],
        "GBP": ["Unemployment Rate", "Average Weekly Earnings Growth"],
        "CNH": ["Unemployment Rate"]
    },

    # "trade": {
    #     "USD": ["Balance of Trade"],
    #     "EUR": ["Balance of Trade"],
    #     "JPY": ["Balance of Trade"],
    #     "GBP": ["Balance of Trade"],
    #     "CNH": ["Balance of Trade", "Export", "Import"]
    # },
}

FED_WATCH_WEBSITE = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"

NEWS_ROOT_WEBSITE = {
    "EUR/USD": "https://www.tradingview.com/symbols/EURUSD/news/",
    "USD/JPY": "https://www.tradingview.com/symbols/USDJPY/news/",
    "GBP/USD": "https://www.tradingview.com/symbols/GBPUSD/news/",
    "USD/CNH": "https://www.tradingview.com/symbols/USDCNH/news/",
}

INVESTING_NEWS_ROOT_WEBSITE = {
    "EUR/USD": "https://cn.investing.com/currencies/eur-usd-news",
    "USD/JPY": "https://cn.investing.com/currencies/usd-jpy-news",
    "GBP/USD": "https://cn.investing.com/currencies/gbp-usd-news",
    "USD/CNH": "https://cn.investing.com/currencies/usd-cnh-news",
}

TECHNICAL_INDICATORS_WEBSITES = {
    "EUR/USD": {
        "indicator": "https://www.tradingview.com/symbols/EURUSD/technicals/?exchange=FX",
        "calender": "https://www.tradingview.com/symbols/EURUSD/economic-calendar/?exchange=FX",
    },
    "USD/JPY": {
        "indicator": "https://www.tradingview.com/symbols/USDJPY/technicals/?exchange=FX",
        "calender": "https://www.tradingview.com/symbols/USDJPY/economic-calendar/?exchange=FX",
    },
    "GBP/USD": {
        "indicator": "https://www.tradingview.com/symbols/GBPUSD/technicals/?exchange=FX",
        "calender": "https://www.tradingview.com/symbols/GBPUSD/economic-calendar/?exchange=FX",
    },

    "USD/CNH": {
        "indicator": "https://www.tradingview.com/symbols/USDCNH/technicals/?exchange=FX",
        "calender": "https://www.tradingview.com/symbols/USDCNH/economic-calendar/?exchange=FX",
    }
}

CURRENCY_TICKERS = {
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "USDJPY=X",
    "GBP/USD": "GBPUSD=X",
    "USD/CNH": "USDCNH=X",
}

# CENTRAL_BANKS = {
#     "EUR": ECB(), "USD": FED(), "JPY": BOJ()
# }

INVESTING_ASSETS = {
    "general": {
        "S&P 500": "https://www.investing.com/indices/us-spx-500",
        "Nasdaq": "https://www.investing.com/indices/nq-100",
        "STOXX50": "https://www.investing.com/indices/eu-stoxx50",
        "MSCI EM": "https://www.investing.com/indices/msci-em",
        "DXY": "https://www.investing.com/currencies/us-dollar-index",
        "Gold": "https://www.investing.com/commodities/gold",
        "Brent Oil": "https://www.investing.com/commodities/brent-oil",
        "VIX": "https://www.investing.com/indices/volatility-s-p-500"
    },

    "EUR": {
        "EUR/USD": "https://www.investing.com/currencies/eur-usd",
        "Germany 2Y Yield": "https://www.investing.com/rates-bonds/germany-2-year-bond-yield",
        "Germany 10Y Yield": "https://www.investing.com/rates-bonds/germany-10-year-bond-yield",
    },

    "USD": {
        "US 2Y Yield": "https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield",
        "US 10Y Yield": "https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield",
    },

    "JPY": {
        "USD/JPY": "https://www.investing.com/currencies/usd-jpy",
        "Japan 2Y Yield": "https://www.investing.com/rates-bonds/japan-2-year-bond-yield",
        "Japan 10Y Yield": "https://www.investing.com/rates-bonds/japan-10-year-bond-yield",
    },

    "GBP": {
        "GBP/USD": "https://www.investing.com/currencies/gbp-usd",
        "UK 2Y Yield": "https://www.investing.com/rates-bonds/uk-2-year-bond-yield",
        "UK 10Y Yield": "https://www.investing.com/rates-bonds/uk-10-year-bond-yield",
    },

    "CNH": {
        "USD/CNH": "https://www.investing.com/currencies/usd-cnh",
        "China 2Y Yield": "https://www.investing.com/rates-bonds/china-2-year-bond-yield",
        "China 10Y Yield": "https://www.investing.com/rates-bonds/china-10-year-bond-yield",
    }
}

PIP_INTERVALS = {
            "EUR/USD": {'5min': 5 / 10000, '15min': 5 / 10000, '1h': 20 / 10000, '4h': 50 / 10000, "1day": 200 / 10000},
            "USD/JPY": {'5min': 10 / 100, '15min': 10 / 100, '1h': 50 / 100, '4h': 50 / 100, "1day": 200 / 100},
            "GBP/USD": {'5min': 5 / 10000, '15min': 5 / 10000, '1h': 20 / 10000, '4h': 50 / 10000, "1day": 200 / 10000},
            "AUD/USD": {'5min': 5 / 10000, '15min': 5 / 10000, '1h': 20 / 10000, '4h': 50 / 10000, "1day": 200 / 10000},
            "USD/CNH": {'5min': 0.01, '15min': 0.01, '1h': 0.02, '4h': 0.04, "1day": 0.1},
            "XAU/USD": {'5min': 0.5, '15min': 1, '1h': 2, '4h': 5, "1day": 20},
            "BTC/USD": {'5min': 20, '15min': 50, '1h': 100, '4h': 200, "1day": 500},
        }

DECIMAL_PLACES = {
            "EUR/USD": 4,
            "USD/JPY": 2,
            "GBP/USD": 4,
            "AUD/USD": 4,
            "USD/CNH": 2,
            "XAU/USD": 1,
            "BTC/USD": 0,
        }


def get_decimal_places(symbol: str) -> int:
    """Get decimal places for a symbol.

    First checks static lookup table, then falls back to metadata service
    which queries TwelveData API.
    """
    if symbol in DECIMAL_PLACES:
        return DECIMAL_PLACES[symbol]
    # Fall back to metadata service for unknown symbols
    from src.services.asset_metadata import get_metadata_service
    return get_metadata_service().get_decimal_places(symbol)


def get_pip_interval(symbol: str, interval: str) -> float:
    """Get pip/tick interval for a symbol and timeframe.

    First checks static lookup table, then computes a sensible default
    based on decimal places.
    """
    if symbol in PIP_INTERVALS and interval in PIP_INTERVALS[symbol]:
        return PIP_INTERVALS[symbol][interval]
    # Compute a sensible default based on decimal places
    decimal_places = get_decimal_places(symbol)
    # Default to minimum tick size
    return 10 ** (-decimal_places)