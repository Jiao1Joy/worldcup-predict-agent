from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


def _service(request: Request):
    service = getattr(request.app.state, "forecast_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="forecast service unavailable")
    return service


@router.get("/current")
async def current_forecast(request: Request):
    service = _service(request)
    try:
        return service.current()
    except KeyError:
        raise HTTPException(status_code=404, detail={"error_code": "forecast_not_found", "message": "Forecast was not found"})


@router.get("/{forecast_id}")
async def get_forecast(forecast_id: str, request: Request):
    service = _service(request)
    try:
        return service.get(forecast_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error_code": "forecast_not_found", "message": "Forecast was not found"})


@router.get("/{forecast_id}/matches/{match_id}")
async def get_match(forecast_id: str, match_id: str, request: Request):
    service = _service(request)
    try:
        forecast = service.get(forecast_id)
    except KeyError:
        raise HTTPException(status_code=404, detail={"error_code": "forecast_not_found", "message": "Forecast was not found"})
    for match in forecast.get("matches", []):
        if match.get("match_id") == match_id:
            return match
    raise HTTPException(status_code=404, detail={"error_code": "forecast_not_found", "message": "Forecast was not found"})


@router.get("/{forecast_id}/bracket")
async def get_bracket(forecast_id: str, request: Request):
    service = _service(request)
    forecast = service.get(forecast_id)
    return {"matches": [m for m in forecast.get("matches", []) if m.get("stage") != "group"]}


@router.get("/{forecast_id}/teams")
async def get_teams(forecast_id: str, request: Request):
    service = _service(request)
    forecast = service.get(forecast_id)
    return {"team_probabilities": forecast.get("team_probabilities", {})}
