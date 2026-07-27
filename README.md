# Monday.com Business Intelligence Agent

> A natural language conversational BI system powered by Groq Llama 3.3 70B, FastAPI, and React 18, delivering pre-calculated, data-caveated business insights directly over Monday.com Work Orders and Deals Pipeline boards.

---

## 📌 Executive Summary

Founders and executive leadership at drone survey and geospatial service companies require immediate visibility into sales pipelines, revenue billing, cash collections, accounts receivable (AR), and operational project execution. Static dashboards and manual spreadsheet exports are slow and introduce human error.

The **Monday.com BI Agent** enables leadership to ask natural language questions such as:

- *"How's our Mining sales pipeline looking?"*
- *"What's our total AR outstanding and which accounts are overdue?"*
- *"Show me revenue breakdown by sector."*
- *"Which projects are currently ongoing vs completed or delayed?"*

### Core Architectural Doctrine: "Zero Math by LLM"

Language models are probabilistic text engines, not calculation engines. Forcing an LLM to sum columns, calculate win rates, or compute risk-weighted forecasts leads to financial hallucinations.

**Our Architecture Enforces**:

1. **Zero Arithmetic by LLM** — 100% of sums, weighted forecasts, win rates, and AR totals are computed deterministically in pure Python.
2. **Zero Raw Rows to LLM** — Only normalized, pre-aggregated KPI summaries or curated filtered records enter the model's context window.
3. **Transparent Data Quality** — Missing values, Excel import defaults, and unparseable dates are explicitly tracked and surfaced as `⚠️ Data note:` caveats.

---

## 🏗️ Architecture & Data Flow

```
                     ┌────────────────────────────────────────┐
                     │          React 18 Frontend UI          │
                     │  (Starter Chips, Executive Brief,      │
                     │   Markdown Renderer, Caveats Panel)    │
                     └───────────────────┬────────────────────┘
                                         │ HTTP POST /chat
                                         ▼
                     ┌────────────────────────────────────────┐
                     │          FastAPI Backend API           │
                     │     (Pydantic Validation & CORS)       │
                     └───────────────────┬────────────────────┘
                                         │
                                         ▼
                     ┌────────────────────────────────────────┐
                     │  Intent Classifier (Keyword Safety Net)│
                     │  (pipeline / revenue / operations)     │
                     └───────────────────┬────────────────────┘
                                         │
                                         ▼
                     ┌────────────────────────────────────────┐
                     │   Groq LLM API (Llama 3.3 70B Engine)  │
                     │ (Tool Selection: query_deals / query_wo)│
                     └───────────────────┬────────────────────┘
                                         │ Dispatch Tool Call
                                         ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           Python Tool Handler                             │
│                                                                           │
│  ┌───────────────────────┐   ┌─────────────────────┐   ┌───────────────┐  │
│  │ Monday.com GraphQL API│──►│ Normalization Layer │──►│ Analytics     │  │
│  │ (httpx + TTL Cache)   │   │ (Dates, Amounts)    │   │ Engine        │  │
│  └───────────────────────┘   └─────────────────────┘   └───────┬───────┘  │
└────────────────────────────────────────────────────────────────┼──────────┘
                                                                 │
                                                                 ▼
                                                Pre-Aggregated KPI Summary JSON
                                                    + Data Quality Caveats
                                                                 │
                                                                 ▼
                                                Groq LLM (Natural Language Answer)
                                                                 │
                                                                 ▼
                                                      React Markdown Response
```

---

## 🛠️ Technology Stack & Trade-Off Rationale

| Layer | Choice | Rationale & Defense |
| --- | --- | --- |
| **LLM Interface** | Groq API (`llama-3.3-70b-versatile`) | ~300ms ultra-fast inference, high instruction-following accuracy, zero rate-limit quota crashes, and model name configurable via env var without code changes. |
| **Backend API** | Python 3.11 + FastAPI | Async-native runtime prevents slow external API calls from blocking concurrent client requests. Includes auto OpenAPI docs (`/docs`). |
| **HTTP Client** | `httpx` | Non-blocking async client with Monday.com GraphQL cursor pagination and exponential backoff retry logic (`2s → 4s → 8s`). |
| **Data Processing** | Native Python (`re` + `datetime`) | Resolves Excel epoch date bugs, parses mixed quantity strings, detects placeholder values, and executes fast in-memory aggregations. |
| **Caching Layer** | `cachetools` (`TTLCache`) | 10-minute in-memory cache on Monday.com board queries to protect against the 60 req/min free-tier rate limit. |
| **Frontend UI** | React 18 + Vite + Tailwind CSS | Dark-mode executive UI featuring starter query chips, executive brief generator, markdown rendering, and collapsible caveats panel. |
| **Deployment** | Railway (Backend) & Vercel (Frontend) | Isolated containerized deployment with secure environment variable management. |

---

## 📂 Project Structure

```
monday-bi-agent/
├── backend/
│   ├── agent/
│   │   ├── groq_client.py       # Groq Llama 3.3 70B inference engine & agent loop
│   │   ├── intent_fallback.py   # Deterministic 3-category keyword fallback safety net
│   │   ├── system_prompt.py     # Persona, Indian currency formatting, & guardrails
│   │   └── tool_handler.py      # Central tool dispatcher & internal analytics chaining
│   ├── analytics/
│   │   ├── aggregator.py        # Generic filtering (AND logic) & group-by helpers
│   │   ├── pipeline.py          # Deal pipeline metrics (weighted value, win rate, stages)
│   │   └── revenue.py           # Revenue & ops metrics (excl/incl GST, AR, status)
│   ├── monday/
│   │   ├── client.py            # Async httpx client with cursor pagination & TTL cache
│   │   ├── column_maps.py       # Monday.com column ID to semantic field mappings
│   │   └── queries.py           # GraphQL query definitions (GET_BOARD_ITEMS, etc.)
│   ├── normalizer/
│   │   ├── amount_fix.py        # Safe sums ("nulls != 0") & placeholder detection
│   │   ├── date_fix.py          # Excel serial date resolution (epoch 1899-12-30)
│   │   ├── deals_fix.py         # Embedded header row removal & deal status inference
│   │   ├── normalize.py         # Master item normalizers & record formatters
│   │   └── quantity_fix.py      # Mixed quantity string parsing via regex
│   ├── config.py                # Environment variable loader & startup assertions
│   ├── main.py                  # FastAPI application entry point & CORS configuration
│   ├── models.py                # Pydantic request/response schemas for /chat
│   ├── requirements.txt         # Python backend dependencies
│   └── Dockerfile               # Production containerization configuration
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── chat.js          # API client helper for backend communication
│   │   ├── components/
│   │   │   ├── CaveatsPanel.jsx # Collapsible data quality warning panel
│   │   │   ├── ChatInput.jsx    # Textarea & prompt controls
│   │   │   ├── Header.jsx       # Navigation header & health indicator
│   │   │   ├── MessageBubble.jsx# Markdown response renderer
│   │   │   └── StarterChips.jsx # Preset executive query chips
│   │   ├── App.jsx              # Main React application container & state
│   │   ├── App.css              # Custom styling & glassmorphism utilities
│   │   ├── index.css            # Tailwind CSS imports
│   │   └── main.jsx             # React entry point
│   ├── package.json             # Frontend dependencies & build scripts
│   └── vite.config.js           # Vite dev & build configuration
├── Decision_Log.md              # Technical trade-offs & design choices
├── README.md                    # Master documentation
└── railway.json                 # Railway deployment manifest
```

---

## 📊 Data Audit & Normalization Strategy

The Monday.com boards originate from legacy Excel imports containing known data defects. The normalization layer (`backend/normalizer/`) cleans all data dynamically in memory on every request:

1. **Excel Serial Date Resolution (`date_fix.py`)**:
   - Excel stores dates as serial integers (e.g. `45757`).
   - Excel uses epoch **December 30, 1899** (not Jan 1, 1900) because Lotus 1-2-3 mistakenly treated 1900 as a leap year. Using Jan 1 causes a 2-day date shift.
   - All serials and ISO strings are normalized to `YYYY-MM-DD`.

2. **Placeholder Amount Detection (`amount_fix.py`)**:
   - System defaults (`1.2332` and `1.455176`) used for POC / Not-Billable rows are detected via float tolerance (`abs(val - target) < 0.0001`) and converted to `None`.

3. **"Nulls Are Not Zeros" (`safe_sum`)**:
   - Missing financial amounts return `None`, not `0.0`.
   - `safe_sum()` returns `(sum, null_count)` so missing values are tracked and reported in data quality notes.

4. **Mixed Quantity Parsing (`quantity_fix.py`)**:
   - Strings like `"5360 HA"`, `"57.55 HA"`, `"2 location"` are parsed via regex (`^([\d,]+\.?\d*)\s*(.*)$`) into numeric values and unit labels.

5. **Embedded Header Row Removal (`deals_fix.py`)**:
   - Repeated header rows from Excel imports (e.g. row named `"Nezuko"` with `"Deal Status"` in cell text) are detected by inspecting field contents and dropped.

---

## 📈 Deterministic Analytics Engine

All calculations live in `backend/analytics/` as pure, deterministic Python functions:

### Deal Pipeline Metrics (`pipeline.py`)

- **Total Pipeline**: Sum of `deal_value` for all open deals.
- **Weighted Pipeline**: $\sum (\text{deal\_value} \times \text{weight})$ where $\text{High}=0.8$, $\text{Medium}=0.5$, $\text{Low}=0.2$.
- **Win Rate**: $\frac{\text{Won Deals}}{\text{Won Deals} + \text{Dead Deals}} \times 100$ (excludes unresolved open deals).
- **Stage Breakdown**: Count of open deals at each sales stage ($A \rightarrow N$).

### Revenue & Operational Metrics (`revenue.py`)

- **PO Value & Billed**: Evaluated Excl-GST (revenue earned by company).
- **Collections & Accounts Receivable**: Evaluated Incl-GST (actual cash flow & client debt).
- **Billing Percentage**: $\frac{\text{Billed Excl GST}}{\text{PO Value Excl GST}} \times 100$.
- **Collection Percentage**: $\frac{\text{Collected Incl GST}}{\text{Billed Excl GST} \times 1.18} \times 100$.
- **Operational Execution**: Counts by status (`Completed`, `Ongoing`, `Not Started`, `Pause/struck`).

---

## 🤖 AI Tooling & System Prompt Design

### Tool Simplification (2 Exposed Tools)

Instead of exposing multiple separate retrieval and compute tools to the LLM, we expose **only 2 tools**:

- `query_deals`: All questions regarding the Deals Pipeline.
- `query_work_orders`: All questions regarding Work Orders (financials & operations).

Each tool accepts an `output_format` parameter:

- `"summary"` (default): Automatically chains Python analytics and returns pre-calculated KPIs.
- `"records"`: Returns clean, individual deal or work order rows for listing queries.

### System Prompt Guardrails (`system_prompt.py`)

- Enforces Indian number formatting (Lakhs: ₹1L = 100,000; Crores: ₹1Cr = 10,000,000).
- Strict negative instructions ("YOU MUST NEVER calculate", "NEVER invent data").
- Enforces structured response formatting: Direct Answer → Supporting Details → `⚠️ Data note:`.

---

## 🚀 Quickstart & Setup Guide

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Groq API Key** (from [console.groq.com](https://console.groq.com))
- **Monday.com API Token & Board IDs**

---

### 1. Backend Setup (FastAPI & Groq Engine)

```bash
# Navigate to backend
cd monday-bi-agent/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Configure Environment Variables

Create `.env` in `backend/`:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile

MONDAY_API_TOKEN=eyJ_your_monday_api_token_here
MONDAY_WO_BOARD_ID=1234567890
MONDAY_DEALS_BOARD_ID=0987654321
```

#### Column ID Discovery (One-Time Setup)

```bash
python -m monday.column_maps
```
*(Paste the printed column IDs into `monday/column_maps.py` if setting up new boards).*

#### Start Backend Server

```bash
uvicorn main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Check Endpoint: `http://localhost:8000/health`

---

### 2. Frontend Setup (React 18 & Vite)

```bash
# Navigate to frontend
cd monday-bi-agent/frontend

# Install dependencies
npm install
```

#### Configure Environment Variables

Create `.env` in `frontend/`:

```env
VITE_API_URL=http://localhost:8000
```

#### Start Frontend Development Server

```bash
npm run dev
```

- Local UI App: `http://localhost:5173`

#### Production Frontend Build

```bash
npm run build
```

---

## 🎯 Challenges Faced & Technical Solutions

| Challenge | Solution |
| --- | --- |
| **Excel serial date bug** | Implemented `parse_date()` using epoch `1899-12-30` and serial range validation. |
| **LLM tool selection hesitation** | Reduced tools exposed to LLM from 4 to 2, handling computation chaining internally in Python. |
| **Vague queries missing keywords** | Implemented 3-category intent fallback (`pipeline`, `revenue`, `operations`) to force tool execution if LLM returns text without tool calls. |
| **Monday.com rate limits (60 req/min)** | Added `cachetools` TTL caching (10 min) and exponential backoff retry logic (`2s → 4s → 8s`) in `httpx` client. |

---

## 🔮 Future Improvements

1. **Write Actions**: Support creating draft deals or updating work order execution status via Monday.com GraphQL mutations.
2. **PDF / Executive Report Generation**: Add `/report` endpoint for generating downloadable executive PDFs.
3. **Webhook Subscriptions**: Listen to real-time Monday.com webhooks for instant cache invalidation on item edits.
