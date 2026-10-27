from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RouteUploadResponse(BaseModel):
    route_id: int
    name: str
    distance_km: float
    point_count: int
    status: str


class RouteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    route_id: int
    name: str
    distance_km: float
    point_count: int
    created_at: datetime | None = None


class ElevationPoint(BaseModel):
    distance_m: float
    elevation_m: float
    slope_percent: float | None = None


class ElevationProfileResponse(BaseModel):
    route_id: int
    point_count: int
    distance_km: float
    elevation_gain_m: float
    elevation_loss_m: float
    min_elevation_m: float
    max_elevation_m: float
    points: list[ElevationPoint]

class WindAnalysisRequest(BaseModel):
    wind_speed_ms: float = Field(ge=0, le=100)
    wind_direction_deg: float = Field(ge=0, le=360)

class WindPoint(BaseModel):
    distance_m: float
    travel_direction_deg: float | None = None
    wind_effect_percent: float | None = None
    wind_effect_ms: float | None = None


class WindProfileResponse(BaseModel):
    route_id: int
    point_count: int
    wind_speed_ms: float
    wind_direction_deg: float
    points: list[WindPoint]


class RouteStatsResponse(BaseModel):
    route_id: int
    name: str
    distance_m: float
    point_count: int

    min_elevation_m: float | None = None
    max_elevation_m: float | None = None
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None

    min_slope_percent: float | None = None
    max_slope_percent: float | None = None

    wind_speed_ms: float | None = None
    wind_direction_deg: float | None = None

    uphill_segments: int = 0
    downhill_segments: int = 0


class AnalysisResponse(BaseModel):
    route_id: int
    status: str
    message: str
    completed_at: datetime | None = None
    available_outputs: list[str] = Field(default_factory=list)


class GISExportResponse(BaseModel):
    route_id: int
    format: str = "GPKG"
    filename: str
    layers: list[str]
    download_url: str

