from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Endpoint de estado simple."""
    return {"status": "ok"}
