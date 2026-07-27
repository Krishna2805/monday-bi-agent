upd

# Decision Log --- Monday.com Business Intelligence Agent

## 1. Key Assumptions Made

### Data Source & Integration

1. **monday.com as the Source of Truth**

The provided Work Orders and Deals datasets are imported into separate
monday.com boards. The agent treats monday.com as the primary data
source after setup and retrieves data dynamically through the monday.com
API.

The original Excel files are only used during initial board population
and are not accessed during runtime.

---

### Data Quality Handling

1. **Missing Values**

Missing values are treated as unknown rather than zero. The agent avoids
making assumptions about unavailable information and highlights data
quality issues when missing values affect calculations or insights.

2. **Data Normalization**

The normalization layer handles inconsistent real-world business data by
converting:

- Different date formats into a standard representation
- Inconsistent text values into normalized categories
- Numeric fields into usable formats for calculations

3. **Financial Data Interpretation**

Financial calculations use the financial fields available in the
provided datasets. No additional business rules are introduced beyond
the information available.

4. **Pipeline Probability Mapping**

Qualitative probability labels are mapped to numerical weights only for
risk-adjusted pipeline estimation.

Example:

- High → 80%
- Medium → 50%
- Low → 20%

These values are configurable assumptions and can be adjusted according
to actual business forecasting practices.

---

# 2. Technical Trade-offs Chosen & Rationale

---

  Decision Area     Choice Made            Alternative       Rationale
                                           Considered

---

  LLM Tool Exposure Two high-level         Multiple          Reduces agent
                    retrieval tools        retrieval and     decision
                    (`query_deals`,        computation tools complexity while
                    `query_work_orders`)   exposed directly  keeping
                    with analytics handled to the LLM        calculations
                    internally in Python                     deterministic,
                                                             testable, and
                                                             easier to debug

  API Client        Async HTTP client      Synchronous       Allows cleaner
  Architecture      using `httpx`          request handling  API handling and
                                                             avoids blocking
                                                             operations during
                                                             external requests

  Schema Discovery  Explicit column        Runtime schema    Reduces
                    mappings with a        discovery on      unnecessary API
                    discovery utility      every request     calls and keeps
                                                             board mappings
                                                             transparent

  Intent Safety Net Lightweight keyword    Pure LLM-based    Provides a
                    fallback classifier    routing only      fallback when
                                                             free-tier models
                                                             fail to identify
                                                             the required data
                                                             source

Output Handling   Summary responses and  Summary-only      Supports both
                    detailed record-level  responses         executive
                    responses                                insights and
                                                             detailed data
                                                             exploration
------------------------------------------------------------------------

---

# 3. Interpretation of "Leadership Updates"

## Concept

Leadership updates are interpreted as generating an executive-level
summary by combining information across monday.com boards.

The goal is to provide a consolidated business overview without
requiring multiple separate queries.

## Implementation

The leadership update contains:

### Pipeline Overview

Includes:

- Total active pipeline value
- Risk-adjusted pipeline estimation
- Deal stage distribution
- Pipeline risks

### Revenue & Financial Overview

Includes:

- Project/contract value
- Billed revenue
- Collected amount
- Outstanding receivables where available

### Operational Overview

Includes:

- Completed projects
- Ongoing projects
- Delayed or incomplete work orders

### Data Quality Notes

Includes:

- Missing fields
- Incomplete records
- Limitations affecting analysis

---

# 4. What We Would Do Differently With More Time

## 1. Real-Time Data Synchronization

Replace periodic refresh strategies with monday.com webhooks to update
cached information whenever board data changes.

## 2. Improved Cross-Board Entity Resolution

Implement automated matching between Deals and Work Orders to better
track the lifecycle from sales opportunity to execution and revenue
collection.

## 3. Advanced Forecasting

Add predictive analytics capabilities for:

- Revenue forecasting
- Deal conversion prediction
- Pipeline trend analysis

## 4. Automated Leadership Report Distribution

Add scheduled generation and distribution of executive reports through
PDF or email summaries.

---

# Summary

The system prioritizes:

- Reliable monday.com integration
- Transparent data cleaning
- Deterministic business calculations
- Executive-friendly insights
- Clear communication of data limitations

The goal is to provide accurate business intelligence while avoiding
unsupported assumptions about company-specific processes.
