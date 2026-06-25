"""Chat API — implemented in Phase 3."""
from fastapi import APIRouter
router = APIRouter()

@router.post("/chat")
async def chat():
    return {"message": "Chat endpoint — coming in Phase 3"}