# CarDekho Matchmaker: AI Car Advisor 🚗🤖

A full-stack, AI-native web application designed to help used car buyers navigate a dataset of 15,000+ vehicles, build a shortlist, compare options, and receive real-time streaming conversational advice powered by Gemini or OpenAI.

* **GitHub Repository**: [SugaSensei/cardekho-ai-car-advisor](https://github.com/SugaSensei/cardekho-ai-car-advisor)
* **Live Deployment**: [Vercel Application Link](https://cardekho-ai-car-advisor-kappa.vercel.app/)

---

## 🛠️ The Tech Stack & Rationale

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend** | React 18 (Vite) | Chosen for fast hot module replacement (HMR), component-driven state, and optimized production bundle loading. |
| **Styling** | Tailwind CSS v3 | Delivers sleek, premium dark-mode glassmorphic aesthetics with minimal CSS bundle sizes. |
| **Backend** | FastAPI (Python) | High-performance async microframework with native support for StreamingResponses (ideal for token streams) and automatic Pydantic type safety. |
| **Database** | SQLite3 | Fast, relational, file-based database. Allows zero-cost deployment alongside the serverless function on Vercel without requiring third-party database hosting. |
| **AI Models** | Google Gemini & OpenAI | Dual-SDK integration (`google-genai` and `openai`) supporting fallback mechanisms and custom model overrides (defaulting to GPT-4o). |

---

## 💡 What was Built & Why?

1. **AI Chat Consultant (Text-to-SQL + Structured RAG)**:
   - Natural language queries are parsed into structured SQL statements dynamically.
   - The query runs against SQLite, returns matching records, and feeds the results back to the LLM to generate a conversational recommendation.
2. **Self-Healing LLM Retry Loop**:
   - If the generated SQL fails Pydantic schema validation or database execution, the exact traceback error is captured and fed back to the LLM.
   - The LLM automatically heals and corrects the query (capped at 3 attempts total).
3. **Token Streaming (SSE JSON Protocol)**:
   - Real-time word-by-word conversational recommendations stream to the UI, providing a high-end, responsive chat experience.
4. **Shortlist Comparison Dashboard**:
   - Buyers can add matching vehicles to a comparison drawer and see specs side-by-side (Engine CC, Max Power, Seats, mileage, and prices) to finalize decisions.
5. **Interactive "Why this?" Breakdown**:
   - A dedicated drawer fetches contextual arguments from the AI explain endpoint explaining why a specific model matches the buyer's query.
6. **SQL & Execution Debugger**:
   - Collapsible panel showing the exact, sanitized SQL query executed against SQLite, building trust and transparency.

---

## ✂️ What was Deliberately Cut?
* **Server-side shortlists & user accounts**: Replaced with client-side state hooks. This avoids database write contention, reduces user friction, and fits Vercel’s read-only serverless architecture.
* **External Search Indexes (Meilisearch/ElasticSearch)**: Replaced with index-optimized local SQLite database structures (indexes on `brand` and `selling_price`), reducing external service dependencies and startup latency.
* **Heavy Pandas Dependencies**: Used Python's native `csv` stream for ingestion to keep backend dependencies small and prevent out-of-memory errors on deployment.

---

## 🤖 AI Tool Delegation vs. Manual Implementation

* **Delegated to AI**:
  - Boilerplate FastAPI endpoint configurations and standard schemas.
  - Setup of CSS layout styles (Vibrant gradient colors and responsive Tailwind grid layouts).
  - Creating mock test configurations for endpoint request wrappers.
* **Implemented Manually**:
  - **The Self-Healing Loop**: Coding the exception catcher, prompt feedback injection, and attempt limit mechanisms.
  - **SQL Sanitizer & Security**: Implementing the keyword blacklists (`DROP`, `DELETE`) and read-only mode connection variables (`?mode=ro`).
  - **Stream Protocol**: Handling line-delimited JSON chunks on the client side (`ReadableStreamDefaultReader` + `TextDecoder`).
* **Where AI helped most**: Rapid UI styling iterations, building helper utilities, and converting tabular specs to layouts.
* **Where AI got in the way**: Mismatched ES module import paths vs CommonJS `require()` statements in Node, and references to columns that did not exist in the database (which prompted us to create Pydantic-based schemas).

---

## 🎯 If I Had Another 4 Hours, I Would Add:
1. **Hybrid Vector Retrieval (RAG)**: Store semantic vectors of user reviews and match them alongside raw SQL filter logic.
2. **Shortlist Exporting**: Allow users to export their shortlisted vehicle comparison reports as a PDF.
3. **Price Negotiations Estimator**: Train a micro-model using historical dataset properties to suggest target offer prices based on age and driven kilometers.

---

## 🚀 Running Locally

### 1. Ingest Dataset & Setup Database
Ensure Python 3.10+ is installed:
```bash
# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Import dataset to SQLite
python db_importer.py
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API keys:
```text
OPENAI_API_KEY="sk-proj-..."
AI_PROVIDER="openai"
OPENAI_MODEL="gpt-4o"
```

### 3. Launch Backend Server
```bash
uvicorn api.index:app --reload
```

### 4. Run Frontend App
In a separate terminal:
```bash
npm install
npm run dev
```

### 5. Running Tests
```bash
# Run backend test suite
pytest api/test_backend.py

# Run frontend parser test suite
node src/test_parser.js
```
