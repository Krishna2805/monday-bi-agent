# Monday.com Business Intelligence Agent

> A natural language conversational BI interface powered by Google Gemini and FastAPI, providing pre-calculated, data-caveated analytics over Monday.com Work Orders and Deals Pipeline boards.

---

## 📌 Executive Summary

Executive leadership at geospatial and drone survey companies need instant clarity on sales pipelines, revenue billing, collections, accounts receivable (AR), and project execution status. Existing dashboards require manual filtering or static spreadsheet exports.

The **Monday.com BI Agent** allows founders to ask natural language questions like:

- *"How's our Mining pipeline looking?"*
- *"What's our total AR outstanding and which accounts are delayed?"*
- *"Show me revenue breakdown by sector."*
- *"Which projects are currently ongoing vs completed?"*

### Core Architectural Doctrine: "Zero Math by LLM"

Language models are probabilistic text generators, not deterministic calculation engines. Forcing an LLM to sum columns or compute win rates leads to financial hallucinations.

**Our Architecture Enforces**:

1. **Gemini performs zero calculations** — 100% of mathematical aggregations, probability weightings, and win rates are executed in pure Python.
2. **Gemini sees zero raw data rows** — Only normalized, pre-aggregated KPI summaries or clean filtered records are passed to the model.
3. **Transparent Data Quality** — Missing values, Excel import bugs, and system placeholders are explicitly tracked and reported as `⚠️ Data note:` caveats.

---

## 🏗️ Architecture & Data Flow

```
User Query (React Frontend)
       │
       ▼  HTTP POST /chat
FastAPI Backend
       │
       ├─► Intent Classifier (Keyword Fallback Safety Net: pipeline / revenue / operations)
       │
       ▼
Google Gemini API (Flash Model)
       │  Tool Selection (2 exposed tools: query_deals / query_work_orders)
       ▼
Tool Handler (Python)
       │
       ├─► Monday.com GraphQL API (httpx Async Client + Cursor Pagination)
       │
       ├─► Normalization Layer (Excel date epoch fix, placeholder removal, regex quantity parsing)
       │
       └─► Deterministic Analytics Engine (Internal analytics chaining: pipeline / revenue summaries)
       │
       ▼ Structured Pre-Aggregated Summary JSON + Data Quality Caveats
Google Gemini API (Natural Language Explanation & Formatting)
       │
       ▼
React Frontend UI (Markdown formatting, starter query chips, caveats panel)
```

---

## 🛠️ Technology Stack & Trade-Off Rationale

| Component                    | Choice                                | Reason & Defense                                                                                                                                      |
| ---------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LLM Interface**      | Google Gemini API (Flash Family)      | High instruction-following accuracy, function calling support, fast execution speed, and model name configurable via env var without code changes.    |
| **Backend API**        | Python 3.11 + FastAPI                 | Async-native runtime prevents slow external HTTP calls from blocking concurrent client requests. Built-in Pydantic validation and auto OpenAPI specs. |
| **HTTP Client**        | `httpx`                             | Non-blocking async client supporting concurrent GraphQL request execution and automatic retry logic.                                                  |
| **Data Normalization** | `pandas` + `re` + `datetime`    | Resolves Lotus 1-2-3 / Excel epoch date bugs, parses mixed quantity strings, and detects placeholder amounts.                                         |
| **Caching Layer**      | `cachetools` (TTL Cache)            | 10-minute in-memory cache on Monday.com board queries to protect against the 60 req/min free-tier rate limit.                                         |
| **Frontend**           | React 18 + Tailwind CSS               | Modern, responsive chat UI featuring starter query chips, markdown response rendering, and a collapsible caveats panel.                               |
| **Deployment**         | Railway (Backend) & Vercel (Frontend) | Isolated containerized deployment with secure environment variable management.                                                                        |

---

## 📊 Data Audit & Normalization Strategy

The Monday.com boards originate from legacy Excel imports containing known data quality defects. The normalization layer (`backend/normalizer/`) cleans all data dynamically in memory on every request:

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

Instead of exposing 4 separate retrieval and compute tools to Gemini, we expose **only 2 tools**:

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

## 📐 Assumptions & Trade-Offs

1. **Currency**: All financial values are assumed to be in Indian Rupees (INR). Multi-currency conversion is out of scope.
2. **GST Standard**: Flat 18% GST assumed across all work orders.
3. **Fiscal Year**: Indian financial year (April to March).
4. **Read-Only Access**: The agent has read-only access to Monday.com boards; write/update operations are disabled by design.
5. **Tool Simplification**: Chaining analytics inside `tool_handler.py` reduces LLM decision overhead at the cost of slightly rigid aggregation combinations.

---

## 🎯 Challenges Faced & Solutions

| Challenge                                     | Solution                                                                                                                                              |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Excel serial date bug**               | Implemented`parse_date()` using epoch `1899-12-30` and serial range validation.                                                                   |
| **LLM tool selection hesitation**       | Reduced tools exposed to Gemini from 4 to 2, handling computation chaining internally in Python.                                                      |
| **Vague queries missing keywords**      | Implemented 3-category intent fallback (`pipeline`, `revenue`, `operations`) to force tool execution if Gemini returns text without tool calls. |
| **Monday.com rate limits (60 req/min)** | Added`cachetools` TTL caching (10 min) and exponential backoff retry logic (`2s → 4s → 8s`) in `httpx` client.                                |

---

## 🔮 Future Improvements

1. **Write Actions**: Support creating draft deals or updating work order execution status via Monday.com GraphQL mutations.
2. **PDF / Brief Generation**: Add `/report` endpoint for generating executive summaries formatted for PDF export.
3. **Webhook Subscriptions**: Listen to real-time Monday.com webhooks for instant cache invalidation on item edits.

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Setup Backend

```bash
git clone https://github.com/your-username/monday-bi-agent.git
cd monday-bi-agent/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` in `backend/`:

```env
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash
MONDAY_API_TOKEN=eyJ...
MONDAY_WO_BOARD_ID=1234567890
MONDAY_DEALS_BOARD_ID=0987654321
```

### 3. Discover Monday.com Column IDs (One-time setup)

```bash
python -m monday.column_maps
```

Paste the printed column IDs into `monday/column_maps.py`.

### 4. Run Backend

```bash
uvicorn main:app --reload --port 8000
```

API Documentation: `http://localhost:8000/docs`
Health Check: `http://localhost:8000/health`
