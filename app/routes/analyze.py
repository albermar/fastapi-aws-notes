from fastapi import APIRouter, HTTPException
from app.services import s3_services, llm_service

router = APIRouter(prefix="/documents", tags=["analyze"])


@router.post("/{key}/analyze")
def analyze_document(key: str):
    try:
        content = s3_services.read_document(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    result = llm_service.analyze_document(content)
    return {"key": key, **result.model_dump()}