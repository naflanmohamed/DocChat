"""Documents API — implemented in Phase 3."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/documents")
async def list_documents():
    return {"documents": [], "total_count": 0}