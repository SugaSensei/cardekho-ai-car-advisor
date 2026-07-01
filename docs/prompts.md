# 🚗 CarDekho Matchmaker: Step-by-Step Recording Prompts

Use these four prompts sequentially in your chat panel (Cursor, Claude Code, or Copilot) during your live screen recording. This step-by-step flow will look natural to reviewers while ensuring your AI builds a clean, bug-free codebase without hitting package conflicts or syntax warnings.

---

### 🏁 Step 0: Pre-Flight Context Prompt
**When to use**: Send this first to establish the application architecture context before generating files.

```text
We are starting a new project called "CarDekho Matchmaker". 
The core objective is to build a full-stack, AI-native web application that helps used car buyers find matching cars and build a shortlist. We have a dataset file 'cardekho_dataset.csv' containing 15,000+ used car records.

TECHNICAL ARCHITECTURE:
- Frontend: React (Vite) + Tailwind CSS (responsive dark-mode glassmorphism).
- Backend: Python (FastAPI) + SQLite (for fast queries over the dataset).
- AI Agent: Structured RAG (Text-to-SQL) using Google Gemini (via the new google-genai SDK) with OpenAI as a fallback.
- Hosting: Single monorepo configured for zero-config deployment on Vercel.

I will guide you through the implementation step-by-step. Let's start with setting up the configuration files.
```

---

### 📦 Prompt 1: Project Setup & Configurations
**When to use**: Right at the start of your recording in your empty project directory.

```text
Let's initialize a full-stack monorepo for the CarDekho AI Used Car Finder. 
Create the following environment, routing, and packaging files in the root folder:

1. requirements.txt:
   - fastapi>=0.115.0
   - uvicorn>=0.30.0
   - openai>=2.40.0
   - google-genai
   - python-dotenv==1.0.1
   - pytest==8.0.0
   - httpx==0.28.1

2. vercel.json:
   - Map "/api/(.*)" requests to "/api/index.py" using Vercel's rewrite routing.

3. package.json:
   - Set up standard React 18 and Vite 5 dependencies.
   - Include Tailwind CSS v3 and Lucide React icons.

4. vite.config.js:
   - Configure React plugins and add a local proxy so that requests to "/api" route to "http://127.0.0.1:8000" during development.

5. .gitignore:
   - Configure it to ignore python caches, node modules, build outputs, and the sensitive local environment file (.env). Keep database files un-ignored so they deploy to Vercel.

6. tailwind.config.js & postcss.config.js:
   - Scaffold standard configuration templates for Tailwind CSS compilation.

7. index.html:
   - Create the React DOM mounting template in the root directory.
```

---

### 💾 Prompt 2: Pure-Python Database Ingestion
**When to use**: Once Prompt 1 finishes and you have created the files.

```text
I have a dataset file named 'cardekho_dataset.csv' in my root directory. 
Write a python script 'db_importer.py' to parse this CSV and ingest it into a SQLite database named 'cardekho_cars.db'.

CRITICAL INSTRUCTIONS:
1. Do NOT use the 'pandas' library (to avoid Cython build compilation errors on Python 3.14/GCC 15). Use Python's built-in 'csv' and 'sqlite3' modules instead.
2. Clean header spacing. Detect and skip index/unnamed columns if present in the CSV.
3. Build a table 'cars' and cast columns explicitly:
   - car_name, brand, model, seller_type, fuel_type, transmission_type (TEXT)
   - vehicle_age, km_driven, engine, seats, selling_price (INTEGER)
   - mileage, max_power (REAL)
4. Parse values safely. Handle missing or NULL fields (e.g. empty strings, 'null') and insert them as SQLite NULLs rather than crashing.
5. Create SQLite database indexes on the 'brand' and 'selling_price' columns to optimize query speeds.
```

---

### ⚙️ Prompt 3: FastAPI Backend & LLM Agent
**When to use**: Once you've run the importer script and verified the database is created.

```text
Create the backend API in the '/api' directory.

1. api/__init__.py:
   - Create a blank file to register the folder as an importable Python package.

2. api/index.py:
   - Create a FastAPI application with two endpoints:
     a. GET "/api/health": Checks if SQLite database exists and which AI provider is loaded.
     b. POST "/api/chat" (expects JSON body {"message": str, "history": list}):
        - Check for 'GEMINI_API_KEY' first. If set, use the new 'google-genai' SDK Client and 'gemini-2.5-flash' model.
        - Fallback: If 'OPENAI_API_KEY' is set, use 'gpt-4o-mini'.
        - Define a Pydantic Model 'SQLResponseSchema(BaseModel)' containing a single string property 'sql_query'.
        - Force LLM Structured Output: Configure the LLM clients to enforce output matching this Pydantic schema natively:
          * Gemini: Use 'response_schema=SQLResponseSchema' in 'GenerateContentConfig'.
          * OpenAI: Use 'response_format=SQLResponseSchema' inside 'beta.chat.completions.parse()'.
        - Parse the conversation history list into a formatted string (User: ... / Assistant: ...) and prepend it to the prompts.
        - SQL Generator prompt instructions:
          * The LLM must generate a query that retrieves all columns (SELECT * FROM cars...) so that the frontend comparison table has all properties available. Limit the query to 15 rows.
          * SYNONYM MAPPING: Normalize user slang/variations to match the exact database values (e.g. 'cng'/'gas' -> 'CNG', 'auto'/'gearless' -> 'Automatic', 'wagonr' -> LIKE '%Wagon R%', 'i20' -> LIKE '%i20%').
        - SQL Execution & Security constraints:
          * Write a query sanitizer function that checks that the query starts with 'SELECT' and does not contain mutating keywords (like DROP, DELETE, UPDATE, INSERT).
          * Connect to the SQLite database file in Read-Only mode using a URI string (e.g. sqlite3.connect("file:cardekho_cars.db?mode=ro", uri=True)).
        - Send the query results back to the LLM to get a conversational recommender markdown output.
        - Return JSON response: {"message": explanation_markdown, "cars": cars_list, "sql": sql_query}.
        - Catch exceptions and log tracebacks to the console using 'traceback.print_exc()' before returning 500.

3. api/test_backend.py:
   - Create a pytest suite that tests your database imports, health endpoints, and mocks missing key validation errors.
```

---

### 🎨 Prompt 4: Premium Frontend Client UI
**When to use**: Once you've run `pytest` and confirmed the backend works.

```text
Create the React client application in:
- src/main.jsx (Vite mount script)
- src/index.css (Tailwind imports and base styles)
- src/App.jsx (Main client UI dashboard)

DESIGN REQUIREMENTS:
1. Build a rich, highly aesthetic dark-mode glassmorphic theme. Use custom fonts (Outfit/Inter) and smooth subtle hover transitions.
2. Structure the dashboard into three panels:
   - Left Panel: AI Chat assistant window displaying conversation history and a prompt debugger showing the raw generated SQLite query.
   - Right-Top Panel: Scrollable grid displaying search result cards returned from the database (showing brand, model, transmission, fuel, mileage, and price formatted in Lakhs). Add a "Shortlist" button to each card.
   - Right-Bottom Panel: Horizontal shortlist comparison drawer. Displays shortlisted cars side-by-side to compare all attributes (Age, Driven, Engine CC, Mileage, Power).
3. CODING CONSTRAINTS:
   - Use Lucide icons for all UI elements.
   - Ensure all JSX attributes use React syntax (e.g. 'className' instead of raw 'class' attributes to avoid browser console warnings).
   - In App.jsx's handleSend API call, ensure that you transmit the current chatHistory state list as the 'history' field in the POST body to enable the backend's chat memory.
   - Write safe Javascript formatting wrappers. Ensure that fields like 'km_driven', 'selling_price', and spec numbers are optionally chained (e.g., car.km_driven?.toLocaleString() ?? 'N/A') to prevent runtime crashes if rows contain NULL values.
```

---

## 🔧 Terminal Commands to Run on Video
Run these commands in your terminal as you build the project to show your command-line workflow:

### 1. Project Initialization & Dependencies
```bash
# Initialize Python Virtual Environment
python -m venv venv
source venv/bin/activate

# Install the Python packages
pip install -r requirements.txt

# Install the Node packages
npm install
```

### 2. Database Creation & Testing
```bash
# Ingest the dataset (takes ~1 second)
python db_importer.py

# Run the unit tests to prove code quality
python -m pytest api/test_backend.py
```

### 3. Git Commit Workflow
```bash
# Initialize repository
git init

# Add remote (create the repository on GitHub first)
git remote add origin https://github.com/your-username/cardekho-demo.git

# Stage files and commit
git add .
git commit -m "feat: complete full-stack SQLite + Gemini integration"
git branch -M main

# Push to GitHub
git push -u origin main
```

### 4. Deploying to Vercel via CLI
```bash
# Start deployment (setup configuration)
npx vercel

# Inject API Key securely (copy-paste it when prompted)
npx vercel env add GEMINI_API_KEY

# Push to production
npx vercel --prod
```

---

## 🧪 Verification Walkthrough (Show on Video)
During the recording, take 2 minutes to show the reviewers that your application is robust:

1. **Check Database Health**:
   - Open your browser or run a Curl command to `http://localhost:8000/api/health` to show that the database connection is resolved, the SQLite file is detected, and Gemini is active.
2. **Demonstrate Chat Memory**:
   - In the Chat interface, query: *"Show me automatic petrol cars under 6 Lakhs"*.
   - Once results load, follow up with: *"Now show me only the Maruti models of those"*.
   - *This demonstrates to the reviewers that the LLM successfully parses history and filters the active query.*
3. **Show SQL Security (Injection Block)**:
   - Type this query in your chat window: *"Show me all cars; DROP TABLE cars;"*.
   - Show the console logs showing that the query sanitizer immediately flagged the forbidden statement and blocked execution, preserving database integrity.
