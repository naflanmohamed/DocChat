"""Upload API — implemented in Phase 3."""
from fastapi import APIRouter
router = APIRouter()

@router.post("/upload")
async def upload_document():
    return {"message": "Upload endpoint — coming in Phase 3"}