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

def test_sql_sanitizer():
    """Verify that the SQL query sanitizer blocks mutating queries and non-SELECTs."""
    from api.index import sanitize_and_validate_sql
    
    # Normal SELECT queries should pass
    assert sanitize_and_validate_sql("SELECT * FROM cars WHERE brand = 'Maruti'") == "SELECT * FROM cars WHERE brand = 'Maruti'"
    
    # Mutating keywords should raise ValueError
    with pytest.raises(ValueError, match="Forbidden SQL operation detected"):
        sanitize_and_validate_sql("SELECT * FROM cars; DROP TABLE cars;")
        
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        sanitize_and_validate_sql("DELETE FROM cars")
        
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        sanitize_and_validate_sql("INSERT INTO cars (car_name) VALUES ('Alto')")

def test_pydantic_column_validation():
    """Verify that the SQL validator rejects queries containing non-existent columns."""
    from api.index import sanitize_and_validate_sql
    
    # Valid columns should pass
    sanitize_and_validate_sql("SELECT car_name, selling_price, brand FROM cars")
    
    # Unrecognized columns should raise ValueError
    with pytest.raises(ValueError, match="does not exist in the 'cars' table schema"):
        sanitize_and_validate_sql("SELECT * FROM cars WHERE color = 'Blue'")
        
    with pytest.raises(ValueError, match="does not exist in the 'cars' table schema"):
        sanitize_and_validate_sql("SELECT * FROM cars WHERE seating_capacity >= 5")
        
    with pytest.raises(ValueError, match="does not exist in the 'cars' table schema"):
        sanitize_and_validate_sql("SELECT * FROM cars ORDER BY year DESC")

def test_db_read_only_mode():
    """Verify that SQLite connection enforces read-only mode for write operations."""
    assert os.path.exists('cardekho_cars.db')
    
    # Connect in read-only mode exactly as the API does
    conn = sqlite3.connect("file:cardekho_cars.db?mode=ro", uri=True)
    cursor = conn.cursor()
    
    # SELECT queries should work fine
    cursor.execute("SELECT 1 FROM cars LIMIT 1")
    cursor.fetchone()
    
    # Attempting write operations should raise OperationalError due to read-only mode
    with pytest.raises(sqlite3.OperationalError, match="attempt to write a readonly database|readonly database"):
        cursor.execute("UPDATE cars SET km_driven = 10000 LIMIT 1")
        conn.commit()
        
    conn.close()

def test_explain_without_api_keys(monkeypatch):
    """Verify that the /api/explain endpoint responds with 400 when API keys are missing."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    import api.index
    orig_openai = api.index.openai_client
    orig_gemini = api.index.gemini_client
    
    api.index.openai_client = None
    api.index.gemini_client = None
    
    response = client.post("/api/explain", json={
        "car": {"car_name": "Maruti Alto", "selling_price": 120000},
        "rank": 1,
        "history": [],
        "query": "Show me Alto"
    })
    assert response.status_code == 400
    assert "No AI Provider configured" in response.json()["detail"]
    
    api.index.openai_client = orig_openai
    api.index.gemini_client = orig_gemini

