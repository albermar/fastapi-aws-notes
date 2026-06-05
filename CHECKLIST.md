# AWS + CI/CD — Checklist de aprendizaje práctico
## Proyecto: FastAPI + S3 + Lambda + GitHub Actions

El objetivo es hacer esto **una vez de principio a fin** y entenderlo.
Después de completarlo podrás decir: "Tengo un pipeline CI/CD que despliega automáticamente a AWS Lambda."

---

## LA APP QUE VAS A CONSTRUIR

Una API de gestión y análisis de notas/documentos:

```
POST   /documents/upload          → sube un documento a S3
GET    /documents                  → lista todos los documentos en S3
GET    /documents/{key}            → lee el contenido de un documento
DELETE /documents/{key}            → borra un documento de S3
POST   /documents/{key}/analyze    → analiza el documento con LLM (1 llamada)
                                     devuelve: resumen + puntos clave + próximas acciones
```

La parte LLM es intencionalmente simple: una sola llamada con output estructurado (Pydantic).
El foco de este proyecto es AWS + CI/CD, no la complejidad del LLM.

Stack: FastAPI + boto3 + Mangum + OpenAI + Lambda + S3 + GitHub Actions

---

## PARTE 1 — AWS: CUENTA Y PERMISOS

### [ ] 1.1 Crear cuenta AWS
- Ir a aws.amazon.com → Create an AWS Account
- Necesitas tarjeta de crédito (no cobra si usas free tier)
- Activa MFA en el root user: click en tu nombre → Security credentials → MFA

### [ ] 1.2 Crear IAM User para trabajar (no uses el root)
- Busca IAM en la consola → Users → Create user
- Nombre: `dev-user`
- Activa acceso a consola web: sí
- Permisos: Attach policies directly → selecciona `AdministratorAccess`
- Guarda las credenciales (solo las ves una vez): `Access Key ID` + `Secret Access Key`

### [ ] 1.3 Instalar herramientas locales
```bash
pip install boto3 awscli
aws configure
# Te pide:
#   AWS Access Key ID: (la que guardaste)
#   AWS Secret Access Key: (la que guardaste)
#   Default region: eu-west-1    ← o us-east-1, elige una y mantén siempre la misma
#   Output format: json
```

### [ ] 1.4 Verificar que funciona
```bash
aws sts get-caller-identity
# Debes ver tu UserId, Account y Arn. Si salen, todo bien.
```

---

## PARTE 2 — S3: EL ALMACÉN

### [ ] 2.1 Crear el bucket desde consola
- Busca S3 en la consola → Create bucket
- Nombre: `mi-app-documents-[tu-nombre]` (debe ser único globalmente)
- Region: la misma que configuraste en aws configure
- Deja todo lo demás por defecto → Create bucket

### [ ] 2.2 Probar S3 con Python (antes de construir la app)
```python
import boto3

BUCKET = "mi-app-documents-[tu-nombre]"
s3 = boto3.client("s3")

# Subir
s3.put_object(Bucket=BUCKET, Key="test/hello.txt", Body=b"Hola mundo")

# Listar
response = s3.list_objects_v2(Bucket=BUCKET)
for obj in response.get("Contents", []):
    print(obj["Key"])

# Leer sin descargar
obj = s3.get_object(Bucket=BUCKET, Key="test/hello.txt")
print(obj["Body"].read().decode("utf-8"))

# Borrar
s3.delete_object(Bucket=BUCKET, Key="test/hello.txt")
```
Ejecuta esto, verifica que funciona. No sigas hasta que funcione.

---

## PARTE 3 — EL PROYECTO FASTAPI

### [ ] 3.1 Estructura de carpetas
```
fastapi-aws-rag/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── documents.py
│   │   └── qa.py
│   └── services/
│       ├── __init__.py
│       ├── s3_service.py
│       └── llm_service.py
├── tests/
│   ├── __init__.py
│   ├── test_documents.py
│   └── test_qa.py
├── .github/
│   └── workflows/
│       └── deploy.yml
├── requirements.txt
└── .env.example
```

### [ ] 3.2 requirements.txt
```
fastapi
mangum
boto3
openai
python-multipart
pytest
httpx
python-dotenv
```

### [ ] 3.3 app/services/s3_service.py
```python
import boto3
import os

BUCKET = os.environ["S3_BUCKET"]
s3 = boto3.client("s3")


def upload_document(key: str, content: bytes) -> None:
    s3.put_object(Bucket=BUCKET, Key=key, Body=content)


def list_documents() -> list[str]:
    response = s3.list_objects_v2(Bucket=BUCKET)
    return [obj["Key"] for obj in response.get("Contents", [])]


def read_document(key: str) -> str:
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


def delete_document(key: str) -> None:
    s3.delete_object(Bucket=BUCKET, Key=key)


def document_exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except s3.exceptions.ClientError:
        return False
```

### [ ] 3.4 app/services/llm_service.py
```python
import os
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


class DocumentAnalysis(BaseModel):
    summary: str
    key_points: list[str]
    next_actions: list[str]


def analyze_document(content: str) -> DocumentAnalysis:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Analiza el documento y devuelve: "
                    "un resumen breve, los puntos más importantes, "
                    "y las próximas acciones o tareas que se mencionan."
                ),
            },
            {"role": "user", "content": content},
        ],
        response_format=DocumentAnalysis,
    )
    return response.choices[0].message.parsed
```

### [ ] 3.5 app/routes/documents.py
```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import s3_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    s3_service.upload_document(file.filename, content)
    return {"message": f"Documento '{file.filename}' subido correctamente"}


@router.get("")
def list_documents():
    keys = s3_service.list_documents()
    return {"documents": keys}


@router.get("/{key}")
def read_document(key: str):
    try:
        content = s3_service.read_document(key)
        return {"key": key, "content": content}
    except Exception:
        raise HTTPException(status_code=404, detail="Documento no encontrado")


@router.delete("/{key}")
def delete_document(key: str):
    s3_service.delete_document(key)
    return {"message": f"Documento '{key}' borrado correctamente"}
```

### [ ] 3.6 app/routes/analyze.py
```python
from fastapi import APIRouter, HTTPException
from app.services import s3_service, llm_service

router = APIRouter(prefix="/documents", tags=["analyze"])


@router.post("/{key}/analyze")
def analyze_document(key: str):
    try:
        content = s3_service.read_document(key)
    except Exception:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    result = llm_service.analyze_document(content)
    return {"key": key, **result.model_dump()}
```

### [ ] 3.7 app/main.py
```python
from fastapi import FastAPI
from mangum import Mangum
from app.routes import documents, analyze

app = FastAPI(title="Document Assistant API")

app.include_router(documents.router)
app.include_router(analyze.router)

# Esta línea es la magia: convierte FastAPI en Lambda handler
handler = Mangum(app)
```

### [ ] 3.8 Probar localmente antes de subir a Lambda
```bash
pip install -r requirements.txt
export S3_BUCKET="mi-app-documents-[tu-nombre]"
export OPENAI_API_KEY="sk-..."
uvicorn app.main:app --reload
# Abre http://localhost:8000/docs y prueba los endpoints
```

---

## PARTE 4 — TESTS

### [ ] 4.1 tests/test_documents.py
```python
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)


@patch("app.services.s3_service.s3")
def test_upload_document(mock_s3):
    mock_s3.put_object = MagicMock()
    content = b"Contenido de prueba"
    response = client.post(
        "/documents/upload",
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 200
    assert "subido correctamente" in response.json()["message"]


@patch("app.services.s3_service.s3")
def test_list_documents(mock_s3):
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "doc1.txt"}, {"Key": "doc2.txt"}]
    }
    response = client.get("/documents")
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 2


@patch("app.services.s3_service.s3")
def test_delete_document(mock_s3):
    mock_s3.delete_object = MagicMock()
    response = client.delete("/documents/doc1.txt")
    assert response.status_code == 200
```

### [ ] 4.2 Verificar que los tests pasan localmente
```bash
pytest tests/ -v
# Todos deben pasar antes de seguir
```

---

## PARTE 5 — LAMBDA

### [ ] 5.1 Crear la Lambda desde la consola AWS
- Busca Lambda → Create function
- Nombre: `document-assistant`
- Runtime: Python 3.11
- Execution role: Create a new role with basic Lambda permissions

### [ ] 5.2 Dar permisos a la Lambda para leer/escribir S3
- En la Lambda → Configuration → Permissions → click en el rol que se creó
- Add permissions → Attach policies → `AmazonS3FullAccess`
- (En producción usarías una policy más restrictiva, pero para practicar vale)

### [ ] 5.3 Configurar variables de entorno en Lambda
- En la Lambda → Configuration → Environment variables
- Añade:
  - `S3_BUCKET` = `mi-app-documents-[tu-nombre]`
  - `OPENAI_API_KEY` = `sk-...`

### [ ] 5.4 Primer deploy manual (para verificar que funciona antes del CI/CD)
```bash
pip install -r requirements.txt -t package/
cp -r app/ package/
cd package
zip -r ../function.zip .
cd ..

aws lambda update-function-code \
  --function-name document-assistant \
  --zip-file fileb://function.zip \
  --region eu-west-1
```

### [ ] 5.5 Crear API Gateway para tener URL pública
- En la Lambda → Add trigger → API Gateway
- Selecciona: Create a new API → HTTP API → Open (sin auth por ahora)
- Guarda la URL que te genera — esa es tu API en producción

### [ ] 5.6 Probar el endpoint en producción
```bash
# Sustituye por tu URL real
curl https://xxxx.execute-api.eu-west-1.amazonaws.com/documents
```

---

## PARTE 6 — CI/CD CON GITHUB ACTIONS

### [ ] 6.1 Crear repo en GitHub y subir el proyecto
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/[tu-usuario]/fastapi-aws-rag.git
git push -u origin main
```

### [ ] 6.2 Añadir secrets en GitHub
- GitHub repo → Settings → Secrets and variables → Actions → New repository secret
- Añade dos secrets:
  - `AWS_ACCESS_KEY_ID` = tu access key
  - `AWS_SECRET_ACCESS_KEY` = tu secret key

### [ ] 6.3 Crear .github/workflows/deploy.yml
```yaml
name: CI/CD

on:
  push:
    branches: [main]

jobs:

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies into package folder
        run: pip install -r requirements.txt -t package/

      - name: Copy app code
        run: cp -r app/ package/

      - name: Create ZIP
        run: |
          cd package
          zip -r ../function.zip .

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-1

      - name: Deploy to Lambda
        run: |
          aws lambda update-function-code \
            --function-name document-assistant \
            --zip-file fileb://function.zip
```

### [ ] 6.4 Hacer push y verificar el pipeline
```bash
git add .github/
git commit -m "add CI/CD pipeline"
git push
```
- Ve a GitHub → pestaña Actions
- Debes ver el workflow corriendo: test → deploy
- Si todo va bien, verás dos checks verdes

### [ ] 6.5 Verificar que el deploy automático funciona
- Cambia algo pequeño en el código (un mensaje de respuesta)
- `git add . && git commit -m "test deploy" && git push`
- Ve a Actions → verifica que corre → verifica que el cambio aparece en tu API

### [ ] 6.6 Probar que los tests bloquean el deploy
- Rompe un test a propósito (cambia un assert a algo que falle)
- Haz push → ve a Actions → el job `test` debe fallar → `deploy` no debe ejecutarse
- Corrige el test y vuelve a hacer push

---

## RESUMEN: LO QUE HABRÁS CONSTRUIDO

```
Tu ordenador
    → git push a GitHub
    → GitHub Actions instala deps + corre pytest
    → Si tests pasan: empaqueta en ZIP + sube a Lambda
    → API disponible en tu URL de API Gateway

Tu API:
    S3 ← boto3 ← Lambda (FastAPI + Mangum) ← API Gateway ← Usuario
                      ↓
                   OpenAI API
```

## LO QUE PUEDES DECIR EN UNA ENTREVISTA

> "Tengo un pipeline CI/CD con GitHub Actions que despliega automáticamente
> a AWS Lambda cuando hago push a main. Los tests corren primero — si alguno
> falla, el deploy no ocurre. La API usa S3 para almacenamiento y OpenAI
> para procesamiento de documentos. Todo serverless, zero infraestructura
> que mantener."

---

## NOTAS IMPORTANTES

**Cold start**: La primera llamada a Lambda tras un tiempo sin uso tarda 2-4 segundos.
Normal en Lambda, no es un bug.

**Límite de Lambda**: El ZIP con dependencias no puede superar 250MB descomprimido.
Si usas muchas librerías, necesitarás Lambda Layers (tema para después).

**Credenciales**: Nunca en el código. Siempre variables de entorno o roles IAM.

**Región**: Usa siempre la misma región en todo (aws configure, bucket S3, Lambda,
API Gateway). Si mezclas regiones, las cosas no se ven entre sí.
