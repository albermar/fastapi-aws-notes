from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import s3_services

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    s3_services.upload_document(file.filename, content)
    return {"message": f"Documento '{file.filename}' subido correctamente"}


@router.get("")
def list_documents():
    keys = s3_services.list_documents()
    return {"documents": keys}


@router.get("/{key}")
def read_document(key: str):
    try:
        content = s3_services.read_document(key)
        return {"key": key, "content": content}
    except Exception:
        raise HTTPException(status_code=404, detail="Documento no encontrado")


@router.delete("/{key}")
def delete_document(key: str):
    s3_services.delete_document(key)
    return {"message": f"Documento '{key}' borrado correctamente"}