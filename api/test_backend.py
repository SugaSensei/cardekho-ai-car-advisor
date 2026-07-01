import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from api.index import app
from db_importer import import_csv_to_sqlite

client = TestClient(app)

def test_db_importer():
    """Verify that db_importer correctly parses the CSV and creates cardekho_cars.db."""
    success = import_csv_to_sqlite()
    assert success is True
    assert os.path.exists('cardekho_cars.db')
    
    # Query database directly to verify structure and rows
    conn = sqlite3.connect('cardekho_cars.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cars")
    count = cursor.fetchone()[0]
    assert count > 15000  # Verify dataset size is intact
    
    cursor.execute("SELECT car_name, brand, selling_price FROM cars LIMIT 1")
    row = cursor.fetchone()
    assert len(row) == 3
    conn.close()

def test_health_endpoint():
    """Verify the FastAPI health check endpoint resolves and responds with DB status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_exists"] is True

def test_chat_without_api_keys(monkeypatch):
    """Verify that the API returns a clear 400 error when both API Keys are missing."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    import api.index
    # Temporarily remove both clients to mock unconfigured state
    orig_openai = api.index.openai_client
    orig_gemini = api.index.gemini_client
    
    api.index.openai_client = None
    api.index.gemini_client = None
    
    response = client.post("/api/chat", json={"message": "Show me petrol cars under 5 lakhs"})
    assert response.status_code == 400
    assert "No AI Provider configured" in response.json()["detail"]
    
    # Restore original clients
    api.index.openai_client = orig_openai
    api.index.gemini_client = orig_gemini
