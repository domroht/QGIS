from fastapi import APIRouter

router = APIRouter(prefix="/test", tags=["test"])

@router.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "application": "OSM-Velo",
    }
