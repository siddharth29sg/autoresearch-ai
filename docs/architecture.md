# Architecture: Domain Design

## 1. What is a "Research" in our system?
A Research is the core domain entity of the application. It represents a single autonomous research task initiated by a user. The system plans the research strategy, gathers information from multiple sources, evaluates the collected information, synthesizes the findings, and produces one or more output artifacts.

An active Research object contains:
* Identity & Metadata: Unique ID, User ID (optional for anonymous users), Created / Updated timestamps.
* Configuration: Original query, Research depth, Selected data sources, Output format, Language, Model configuration.
* State & Tracking: Current status, Progress information, Search results, Retrieved documents, Generated artifacts.
* Metrics: Execution time, Token usage, Estimated cost, Error information (if any).

---

## 2. Inputs & Internal Fields

### Client Inputs
| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| query | string | ✅ | Research question or prompt |
| depth | enum | ❌ | quick / standard / deep |
| sources | list | ❌ | web, arxiv, pdf, youtube |
| max_results | integer | ❌ | Maximum number of sources to pull |
| output_format| enum | ❌ | markdown / pdf / json |
| language | string | ❌ | Target output language |
| webhook_url | string | ❌ | Callback URL after async completion |

### Internal-Only Fields (System Managed)
* research_id, status
* created_at, updated_at
* execution_time, token_usage, estimated_cost
* artifacts, retrieved_documents, search_results, error_details

---

## 3. Outputs & Artifacts
The system produces one or more structured deliverables alongside execution metadata.

Generated Artifacts:
* Markdown / PDF / JSON reports
* Executive summary & Key findings
* Suggested agent-generated follow-up questions
* References & Citation metadata

Returned Metadata:
* Research ID & Status
* Performance metrics: Time taken, Token usage, Cost estimate, Number of sources used

---

## 4. Research Lifecycle

Created

↓

Validating (check query, auth, rate limits)

↓

Planning (agent decides which sources to search)

↓

Searching (Tavily/Arxiv queries running)

↓

Reading (documents fetched and parsed)

↓

Synthesizing (LLM summarizing findings)

↓

Writing (final report generation)

↓

Completed

↓

Archived (after X days)

---

## 5. Failure States & Error Mapping

| Failure Scenario | System Status |
| :--- | :--- |
| Invalid client request | VALIDATION_FAILED |
| Authentication failed | AUTH_FAILED |
| User quota exceeded | QUOTA_EXCEEDED |
| Search provider (Tavily, etc.) unavailable | SEARCH_FAILED |
| No relevant sources found | EMPTY_RESULTS |
| LLM rate limited | SYNTHESIS_PAUSED |
| LLM generation failed | GENERATION_FAILED |
| Report export failed | EXPORT_FAILED |
| Request timed out | TIMED_OUT |
| Generic internal server error | FAILED |

---

## 6. High-Level Components
* Frontend: React
* Backend: FastAPI Backend
* Orchestration Layer: LangGraph Orchestrator
  * *Agents:* Planner Agent, Research Agent, Critic Agent, Report Generator
* Services: Export Service, Database
* External Tools: Tavily, ArXiv, PDF Reader, Web Scraper

---

## 7. Project Roadmap (Version 1 Scope)

### 🟩 In Scope
* Multi-agent research workflow (Plan ➔ Search ➔ Critique)
* Web & ArXiv integration
* AI-generated research reports with citation support
* Markdown & PDF exports
* Live progress updates & basic research history

### 🟥 Out of Scope (Future Phases)
* Authentication & multi-tenant billing
* Team collaboration features
* Multiple concurrent LLM providers
* Browser extensions or mobile applications

---

## 8. Core Design Principles
* API-First Architecture: Clean, well-documented endpoints drive the UI.
* Separation of Concerns: Business logic is entirely independent of the FastAPI routing layer.
* Extensible Agent Design: The multi-agent workflow should allow new specialized agents to be added easily.
* Async by Default: Long-running research tasks are processed out-of-band to keep the API responsive.