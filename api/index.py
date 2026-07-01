from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Import Google GenAI (New SDK)
from google import genai
from google.genai import types

# Load local environment variables from .env if present
load_dotenv()

app = FastAPI()

# Check which API key is configured
openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

# Configuration via environment variables with defaults
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").strip().lower()  # "openai" or "gemini"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Initialize clients
openai_client = OpenAI(api_key=openai_key) if openai_key else None
gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

# Check database path
DB_PATH = 'cardekho_cars.db'
if not os.path.exists(DB_PATH):
    DB_PATH = '../cardekho_cars.db'

class ChatRequest(BaseModel):
    message: str
    history: list = []

class SQLResponseSchema(BaseModel):
    sql_query: str

class ExplanationRequest(BaseModel):
    car: dict
    rank: int
    history: list = []
    query: str = ""

from pydantic import Field

class CarSchema(BaseModel):
    car_name: str = Field(description="string (e.g. 'Maruti Alto', 'Hyundai Grand')")
    brand: str = Field(description="string (e.g. 'Maruti', 'Hyundai', 'Honda', 'Ford', 'Skoda', 'Volkswagen', 'Toyota', 'Renault', 'Mahindra', 'Tata')")
    model: str = Field(description="string (e.g. 'Alto', 'Grand', 'i20', 'Wagon R', 'Rapid', 'City', 'Civic', 'Ecosport')")
    vehicle_age: int = Field(description="integer (age in years, e.g. 9, 5)")
    km_driven: int = Field(description="integer (e.g. 120000, 20000)")
    seller_type: str = Field(description="string ('Individual', 'Dealer', 'Trustmark Dealer')")
    fuel_type: str = Field(description="string ('Petrol', 'Diesel', 'CNG', 'LPG', 'Electric')")
    transmission_type: str = Field(description="string ('Manual', 'Automatic')")
    mileage: float = Field(description="float (km per liter, e.g. 19.7, 18.9)")
    engine: int = Field(description="integer (CC engine size, e.g. 796, 1197)")
    max_power: float = Field(description="float (BHP power, e.g. 46.3, 82.0)")
    seats: int = Field(description="integer (e.g. 5, 7)")
    selling_price: int = Field(description="integer (price in Indian Rupees, e.g. 120000, 550000)")

# Programmatically construct the database schema description from CarSchema fields to ensure a single source of truth.
schema_lines = []
for name, field in CarSchema.model_fields.items():
    desc = field.description or ""
    schema_lines.append(f"- {name}: {desc}")

DB_SCHEMA = "Table Name: cars\nColumns:\n" + "\n".join(schema_lines)

SQL_SYSTEM_PROMPT = """
You are an expert database assistant converting user queries about used cars into SQLite queries.
Use this database schema:
{DB_SCHEMA}

RULES:
1. You must write a valid SQLite query.
2. Case-insensitive searches for strings must use LIKE. (e.g., brand LIKE '%maruti%')
3. Always include a LIMIT clause (max 15 rows) to avoid overwhelming the system.
4. If the user asks for general recommendations, search by popular filters (e.g., low price, low age, high mileage).
5. Always select all columns (SELECT * FROM cars ...) so that the frontend comparison table has all properties available.
6. SYNONYM MAPPING: Normalize user slang/shorthand to exact database values:
   - 'cng' or 'gas' -> fuel_type = 'CNG'
   - 'petrol' -> fuel_type = 'Petrol'
   - 'diesel' -> fuel_type = 'Diesel'
   - 'auto' or 'gearless' -> transmission_type = 'Automatic'
   - 'manual' or 'gear' -> transmission_type = 'Manual'
   - If they specify models without spaces (e.g. 'wagonr', 'i20', 'grand'), map them using LIKE (e.g. model LIKE '%Wagon R%' or model LIKE '%i20%' or model LIKE '%Grand%').
7. COLUMN MAPPING: Always use the column 'selling_price' for any queries involving price, budget, cost, or lakhs. The column 'price' does NOT exist in the database; generating 'price' will result in a SQLite syntax error.
8. AGE/YEAR MAPPING: The database contains 'vehicle_age' (age in years), NOT 'year'. To sort by newest cars or filter by year, use 'vehicle_age' (e.g., sort by 'vehicle_age ASC' to get the newest cars first). There is no 'year' column.
9. FORBIDDEN COLUMNS: Do NOT query columns that are not in the schema (e.g. 'color', 'owner', 'location', 'city', 'variant'). If a user filters by these, ignore those filters in the SQL query. The assistant will address those preferences in the text response instead.
10. SEATS MAPPING: The column containing the number of seats is 'seats', NOT 'seating_capacity' or 'capacity'. If the user asks for a family car, passenger capacity, or a specific number of seats, use the 'seats' column (e.g., seats >= 5).
"""

RECOMMENDER_SYSTEM_PROMPT = """
You are a friendly, expert Used Car Advisor at CarDekho.
Given the user's request and the list of matching cars returned from the database, explain:
1. Why these cars fit their requirements.
2. The key highlights of these models (e.g. fuel type, transmission, cost-benefit).
3. Offer tips on negotiating or what details to inspect (mileage, age).

Keep your response conversational, concise, and formatted in clean Markdown.
If no cars are returned, explain kindly and suggest adjusting their parameters (e.g. budget, brand).
"""

def sanitize_and_validate_sql(query: str) -> str:
    """Validate that the query is a SELECT statement, blocks mutating keywords, and references only valid columns."""
    query_clean = query.strip()
    
    # Enforce SELECT only
    if not query_clean.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
        
    # Check for mutating keywords
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER", "REPLACE", "TRUNCATE"]
    import re
    for word in forbidden:
        if re.search(r'\b' + word + r'\b', query_clean.upper()):
            raise ValueError(f"Forbidden SQL operation detected: {word}")
            
    # Parse columns and validate against CarSchema
    allowed_cols = set(CarSchema.model_fields.keys())
    
    # Remove string literals to avoid matching words inside text search terms
    clean_query = re.sub(r"'[^']*'", "", query_clean)
    tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', clean_query)
    
    sql_keywords = {
        "select", "from", "where", "and", "or", "like", "order", "by", 
        "limit", "asc", "desc", "not", "in", "is", "null", "between", 
        "cars", "min", "max", "sum", "avg", "count", "group", "having",
        "as", "union", "all", "exists", "case", "when", "then", "else", "end",
        "abs", "round", "coalesce", "nullif"
    }
    
    for token in tokens:
        token_lower = token.lower()
        if token_lower not in sql_keywords:
            if token_lower not in allowed_cols:
                raise ValueError(
                    f"Column '{token}' does not exist in the 'cars' table schema. "
                    f"Allowed columns are: {', '.join(sorted(allowed_cols))}."
                )
                
    return query_clean

@app.get("/api/health")
def health():
    db_exists = os.path.exists(DB_PATH)
    active_provider = "Gemini" if (AI_PROVIDER == "gemini" and gemini_client) else "OpenAI"
    if active_provider == "Gemini" and not gemini_client:
        active_provider = "OpenAI" if openai_client else None
    elif active_provider == "OpenAI" and not openai_client:
        active_provider = "Gemini" if gemini_client else None
        
    return {
        "status": "healthy",
        "openai_configured": openai_client is not None,
        "gemini_configured": gemini_client is not None,
        "active_provider": active_provider,
        "openai_model": OPENAI_MODEL,
        "gemini_model": GEMINI_MODEL,
        "database_exists": db_exists,
        "database_path": os.path.abspath(DB_PATH) if db_exists else None
    }

def clean_json_response(text: str) -> str:
    """Helper to strip markdown wrappers like ```json ... ``` and leading/trailing whitespace."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500, 
            detail=f"Database file '{DB_PATH}' not found. Please run the ingestion script 'db_importer.py' first."
        )
        
    if not gemini_client and not openai_client:
        raise HTTPException(
            status_code=400,
            detail="No AI Provider configured. Please add GEMINI_API_KEY or OPENAI_API_KEY to your .env file."
        )
        
    try:
        query = None
        cars = []
        explanation = ""
        
        # Build conversational history string
        history_str = ""
        for msg in request.history:
            role = "User" if msg.get("sender") == "user" else "Assistant"
            text_val = msg.get("text", "")
            # Truncate exceptionally long text blocks if present
            if len(text_val) > 1000:
                text_val = text_val[:1000] + "... (truncated)"
            history_str += f"{role}: {text_val}\n"
        
        # Determine active provider
        use_gemini = (AI_PROVIDER == "gemini" and gemini_client is not None)
        use_openai = (AI_PROVIDER == "openai" and openai_client is not None)
        
        # Fallback if one is chosen but not available
        if AI_PROVIDER == "gemini" and not gemini_client and openai_client:
            use_openai = True
        elif AI_PROVIDER == "openai" and not openai_client and gemini_client:
            use_gemini = True
            
        if not use_gemini and not use_openai:
            raise HTTPException(
                status_code=400,
                detail="Selected AI Provider is not configured. Please add the required API key."
            )
            
        attempts = 3
        last_error = None
        
        for attempt in range(attempts):
            try:
                if use_gemini:
                    # === GOOGLE GEMINI (NEW SDK) EXECUTION ===
                    # Step 1: SQL Generation using Structured Output schemas
                    if attempt > 0:
                        sql_prompt = (
                            f"{SQL_SYSTEM_PROMPT.replace('{DB_SCHEMA}', DB_SCHEMA)}\n"
                            f"Conversation History:\n{history_str}\n"
                            f"User query: {request.message}\n\n"
                            f"CRITICAL: Your previous query '{query}' failed validation with error: {last_error}.\n"
                            f"Please correct the query by using only valid columns and valid syntax."
                        )
                    else:
                        sql_prompt = f"{SQL_SYSTEM_PROMPT.replace('{DB_SCHEMA}', DB_SCHEMA)}\nConversation History:\n{history_str}\nUser query: {request.message}"
                        
                    sql_response = gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=sql_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=SQLResponseSchema
                        )
                    )
                    sql_json = json.loads(sql_response.text)
                    query = sql_json.get("sql_query")
                    
                else:
                    # === OPENAI EXECUTION ===
                    # Step 1: SQL Generation using Structured Output parse client
                    if attempt > 0:
                        sql_generation_messages = [
                            {"role": "system", "content": SQL_SYSTEM_PROMPT.replace('{DB_SCHEMA}', DB_SCHEMA)},
                            {"role": "user", "content": (
                                f"Conversation History:\n{history_str}\n"
                                f"User query: {request.message}\n\n"
                                f"CRITICAL: Your previous query '{query}' failed validation with error: {last_error}.\n"
                                f"Please correct the query by using only valid columns and valid syntax."
                            )}
                        ]
                    else:
                        sql_generation_messages = [
                            {"role": "system", "content": SQL_SYSTEM_PROMPT.replace('{DB_SCHEMA}', DB_SCHEMA)},
                            {"role": "user", "content": f"Conversation History:\n{history_str}\nUser query: {request.message}"}
                        ]
                        
                    sql_response = openai_client.beta.chat.completions.parse(
                        model=OPENAI_MODEL,
                        messages=sql_generation_messages,
                        response_format=SQLResponseSchema
                    )
                    query = sql_response.choices[0].message.parsed.sql_query
                
                # Step 2: Validate SQL Query
                query = sanitize_and_validate_sql(query)
                
                # Step 3: Query SQLite database in Read-Only Mode
                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                try:
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    cars = [dict(r) for r in rows]
                except Exception as sql_err:
                    conn.close()
                    # Treat execution errors as validation errors to trigger a retry
                    raise ValueError(f"SQLite execution failed: {sql_err}")
                conn.close()
                
                # If we made it here without ValueError or SQLite errors, break out of loop!
                break
                
            except ValueError as e:
                last_error = str(e)
                print(f"[Attempt {attempt + 1}/{attempts}] SQL generation validation failed: {last_error}")
                if attempt == attempts - 1:
                    # Exhausted all attempts
                    return {
                        "message": f"I had trouble formulating a valid query. Try rephrasing your search request! (Last validation failure: {last_error})",
                        "cars": [],
                        "sql": query
                    }
        
        # Step 4: Explanation & Summary
        if use_gemini:
            recommender_prompt = f"{RECOMMENDER_SYSTEM_PROMPT}\nConversation History:\n{history_str}\nUser prompt: {request.message}\nDatabase results: {json.dumps(cars)}"
            recommender_response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=recommender_prompt
            )
            explanation = recommender_response.text
        else:
            recommender_messages = [
                {"role": "system", "content": RECOMMENDER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Conversation History:\n{history_str}\nUser prompt: {request.message}\nDatabase results: {json.dumps(cars)}"}
            ]
            recommender_response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=recommender_messages
            )
            explanation = recommender_response.choices[0].message.content
            
        return {
            "message": explanation,
            "cars": cars,
            "sql": query
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/explain")
async def explain_suggestion(request: ExplanationRequest):
    if not gemini_client and not openai_client:
        raise HTTPException(
            status_code=400,
            detail="No AI Provider configured. Please add GEMINI_API_KEY or OPENAI_API_KEY to your .env file."
        )
    
    try:
        # Format previous history
        history_str = ""
        for msg in request.history:
            role = "User" if msg.get("sender") == "user" else "Assistant"
            text_val = msg.get("text", "")
            if len(text_val) > 1000:
                text_val = text_val[:1000] + "... (truncated)"
            history_str += f"{role}: {text_val}\n"

        prompt = f"""
You are a friendly, expert Used Car Advisor at CarDekho.
A user is looking for a used car. Their query was: "{request.query}"
We found some matches from the SQLite database. This car was suggested at Rank #{request.rank}:
Car Details: {json.dumps(request.car)}

Based on the conversation history below:
{history_str}

Please write a concise 2-sentence explanation of why this specific car is a great fit for their query and is ranked #{request.rank}. Focus on concrete details (e.g. its price, transmission, mileage, or age) compared to their preferences.
Keep it direct, professional, and friendly. Do not use markdown titles or bullet points. Just return the direct explanation text.
"""
        
        # Determine active provider
        use_gemini = (AI_PROVIDER == "gemini" and gemini_client is not None)
        use_openai = (AI_PROVIDER == "openai" and openai_client is not None)
        
        # Fallback if one is chosen but not available
        if AI_PROVIDER == "gemini" and not gemini_client and openai_client:
            use_openai = True
        elif AI_PROVIDER == "openai" and not openai_client and gemini_client:
            use_gemini = True
            
        if use_gemini:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            explanation = response.text
        elif use_openai:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            explanation = response.choices[0].message.content
        else:
            raise HTTPException(
                status_code=400,
                detail="Selected AI Provider is not configured. Please add the required API key."
            )
            
        return {"explanation": explanation.strip()}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
