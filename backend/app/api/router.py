from fastapi import APIRouter
from app.api.v1 import research

router = APIRouter(prefix="/api/v1")
router.include_router(research.router)