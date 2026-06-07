# Document Assistant API

Upload any text document and let the API act as your assistant: it stores it, reads it, and on demand extracts a summary, the key points, and the next actions to take — structured and ready to consume.

Built with **FastAPI** and deployed serverless on **AWS Lambda** + **API Gateway**, with documents stored in **S3** and analysis powered by **OpenAI**. Fully automated CI/CD via **GitHub Actions** — tests gate every deploy.

**Live API:** `https://zmkujfdrp3.execute-api.eu-north-1.amazonaws.com/default`

---

## Architecture

```
Client → API Gateway (HTTP API) → Lambda (FastAPI + Mangum) → S3
                                           ↓
                                       OpenAI API
```

Every push to `main` triggers GitHub Actions: tests run first, deploy only on green.

---

## Endpoints

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/documents/upload` | Upload a document to S3 |
| `GET` | `/documents` | List all documents |
| `GET` | `/documents/{key}` | Read document content |
| `DELETE` | `/documents/{key}` | Delete a document |
| `POST` | `/documents/{key}/analyze` | Analyze document with LLM |

### Analyze response

```json
{
  "key": "notes.txt",
  "summary": "...",
  "key_points": ["...", "..."],
  "next_actions": ["...", "..."]
}
```

---

## Usage

```bash
BASE=https://zmkujfdrp3.execute-api.eu-north-1.amazonaws.com/default

# Upload
curl -X POST $BASE/documents/upload -F "file=@notes.txt"

# List
curl $BASE/documents

# Read
curl $BASE/documents/notes.txt

# Analyze
curl -X POST $BASE/documents/notes.txt/analyze

# Delete
curl -X DELETE $BASE/documents/notes.txt
```

---

## Stack

- **Runtime:** Python 3.14, FastAPI, Mangum
- **Cloud:** AWS Lambda, S3, API Gateway, IAM
- **LLM:** OpenAI gpt-4o-mini with Pydantic structured output
- **CI/CD:** GitHub Actions — pytest (mocked AWS) gates every deploy
- **Infrastructure:** Serverless, zero-maintenance

---

## Local development

```bash
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

Create a `.env` file with:
```
S3_BUCKET=your-bucket-name
OPENAI_API_KEY=sk-...
```

```bash
uvicorn app.main:app --reload
# Docs at http://localhost:8000/docs
```

## Tests

```bash
pytest tests/ -v
```
