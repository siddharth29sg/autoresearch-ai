# Architecture: Domain Design

## 1. What is a "Research" in our system?

A Research is a unit of work that takes a user query,
autonomously gathers information from multiple sources,
synthesizes it, and produces a structured output.

**It contains:**
- A unique ID
- The original query (string)
- Configuration (sources, depth, model)
- Created/updated timestamps
- Current state
- Owner/user ID
- List of sources found
- List of documents read
- Final report (when completed)
- Error info (if failed)

**Lifecycle:** Created → Processing → Completed/Failed/Archived

---

## 2. Inputs

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| query | string | yes | The research question |
| depth | enum | no | quick / standard / deep |
| sources | list | no | arxiv, web, pdf, youtube |
| max_results | int | no | default 10 |
| output_format | enum | no | markdown / pdf / json |
| language | string | no | for future multilingual support |
| user_id | string | yes | for multi-user support later |
| webhook_url | string | no | notify when done (async) |

---

## 3. Outputs

- Structured report (markdown)
- PDF export
- List of sources with URLs and credibility score
- Key findings (bullet summary)
- Follow-up questions (suggested by agent)
- Token/cost usage metadata
- Time taken

---

## 4. Lifecycle

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

## 5. Failure States

| Failure | State |
|---------|-------|
| Tavily is down | SEARCH_FAILED |
| Groq rate limited | SYNTHESIS_PAUSED |
| PDF generation fails | EXPORT_FAILED |
| Query times out | TIMED_OUT |
| No results found | EMPTY_RESULTS |
| Invalid query | VALIDATION_FAILED |
| User quota exceeded | QUOTA_EXCEEDED |

