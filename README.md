## Ads Analysis Agent

Minimal Chainlit app that turns a Facebook ads SQLite dataset into an interactive analytics assistant. It uses Gemini to translate natural language questions into SQL, runs them against `data/campaigns.db`, then returns explanations, tables, and Plotly-based charts in the UI.

### Architecture (Brief)

- **Entry point (`app.py`)**: Chainlit app with `@cl.on_chat_start` and `@cl.on_message` handlers. It initializes a global `CoordinatorAgent`, fetches basic stats for a welcome message, and orchestrates responses (text, table, chart).
- **Agents (`src/agents.py`)**:
  - `SQLAgent`: Uses Gemini + schema-aware prompts to generate and iteratively fix SQLite queries, then executes them against the database.
  - `VisualizationAgent`: Asks Gemini to emit Plotly code, executes it in a sandboxed namespace, and returns a `fig`.
  - `CoordinatorAgent`: Determines user intent (data, visualization, or both), calls the SQL + viz agents, and composes the final result (dataframe, SQL, figure, insight text).
- **Database layer (`src/database.py`)**: Thin wrapper over SQLite with a `DatabaseManager` that verifies `data/campaigns.db`, executes queries into Pandas DataFrames, exposes schema text, and computes high-level stats for the welcome banner.
- **Prompt templates (`src/prompts.py`)**: Centralized prompt builders for SQL generation, visualization code, intent classification, and insight generation.
- **Rendering (`src/renderers.py` + `public/elements`)**:
  - `HTMLRenderer`: Styles tables and Plotly charts as HTML.
  - Custom React elements (`Chart.jsx`, `DataTable.jsx`) used by Chainlit `CustomElement` to embed interactive charts and tables in the chat UI.

### Installation & Setup

- **Prerequisites**
  - Python 3.10+ recommended
  - A Google Gemini API key (`GOOGLE_API_KEY` env var)

- **1. Clone and create a virtual environment**

```bash
git clone <this-repo-url>
cd ads-analysis-agent
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
```

- **2. Install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

- **3. Configure environment variables**

Create a `.env` file in the project root:

```bash
Copy the contents from .env.example
```

- **4. Initialize the database**

This creates `data/campaigns.db` from the sample CSV:

```bash
python setup_db.py
```

- **5. Run the app**

```bash
chainlit run app.py
```

Then open the URL that Chainlit prints in the terminal and start asking questions about your Facebook ad campaigns.

