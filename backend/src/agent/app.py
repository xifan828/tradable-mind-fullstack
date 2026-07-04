# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from agent.services.technical.technical_indicator import TechnicalIndicatorService
from agent.utils.twelve_data import AssetType

# Define the FastAPI app
app = FastAPI()


@app.get("/api/time-series")
def get_time_series(
    symbol: str,
    interval: str,
    asset_type: AssetType | None = None,
):
    """Fetch asset OHLC time series with technical indicators from TwelveData."""
    service = TechnicalIndicatorService(
        symbol=symbol,
        timezone="UTC",
        interval=interval,
        asset_type=asset_type,
    )
    try:
        df = service.get_data_from_td()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data returned for the given parameters.")

    df = df.reset_index()
    # Serialize any datetime columns to ISO strings for JSON output.
    for col in df.columns:
        if str(df[col].dtype).startswith("datetime"):
            df[col] = df[col].astype(str)

    return {
        "symbol": symbol,
        "interval": interval,
        "asset_type": asset_type,
        "data": df.to_dict(orient="records"),
    }


@app.get("/api/pivot-levels")
def get_pivot_levels(
    symbol: str,
    asset_type: AssetType | None = None,
):
    """Calculate pivot levels from the previous completed session's OHLC."""
    service = TechnicalIndicatorService(
        symbol=symbol,
        timezone="UTC",
        interval="1day",
        asset_type=asset_type,
    )
    try:
        pivot_levels = service.get_pivot_levels()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if pivot_levels is None:
        raise HTTPException(status_code=404, detail="Could not compute pivot levels.")

    return {
        "symbol": service.symbol,
        "interval": service.interval,
        "pivot_levels": pivot_levels,
    }


# @app.get("/app")
# async def redirect_app_root():
#     return RedirectResponse(url="/app/")


def create_frontend_router(build_dir="frontend_dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy app if build isn't ready
        from starlette.applications import Starlette
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Starlette(routes=[Route("/{path:path}", endpoint=dummy_frontend)])

    return StaticFiles(directory=build_path, html=True)


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
