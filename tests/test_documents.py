from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
import io

client = TestClient(app)


@patch("app.services.s3_services.s3")
def test_upload_document(mock_s3):
    mock_s3.put_object = MagicMock()
    content = b"Contenido de prueba"
    response = client.post(
        "/documents/upload",
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
    )
    assert response.status_code == 200
    assert "subido correctamente" in response.json()["message"]


@patch("app.services.s3_services.s3")
def test_list_documents(mock_s3):
    mock_s3.list_objects_v2.return_value = {
        "Contents": [{"Key": "doc1.txt"}, {"Key": "doc2.txt"}]
    }
    response = client.get("/documents")
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 2


@patch("app.services.s3_services.s3")
def test_delete_document(mock_s3):
    mock_s3.delete_object = MagicMock()
    response = client.delete("/documents/doc1.txt")
    assert response.status_code == 200