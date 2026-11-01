# JobRadar — High-Level Design (HLD)

_Oct 7, 2026_

## Summary and scope

JobRadar is a single self-hosted Python service built as an event-driven pipeline: sources push raw messages into a SQLite-backed queue, a chain of idempotent workers turns them into jobs, and sinks write results to Notion, the local dashboard and email.

Two principles shape the pipeline:

- **Free first.** Links, duplicates and ads are handled by rules. Job details come from structured page data and the post's own labels before any model is called; an LLM is a fallback, not the default.
- **Judgments, not prose, for decisions.** Whether a job fits the user is answered by **Jev**, TypeSafe's System One model, as typed answers (Choice, Score, yes/no) with calibrated confidence. Code combines them into a match score and decides what to hide, what to show and what to email. Only strong, confident matches interrupt the user.

Notion is both the dashboard and the control panel: a Status change there is read back, and the user's Shortlisted/Skipped choices tune the alert threshold.

This HLD covers v1.0 as defined in the [PRD](PRD.md): Telegram ingestion, dedupe, layered extraction, Jev matching, the Notion and local dashboards, and email alerts. WhatsApp is an optional experimental source behind the same interface.

## Architecture

Messages flow down through one service. Notion sends the user's choices back up.

```mermaid
flowchart TB
    subgraph Sources
        direction LR
        TG["Telegram (Telethon)"]
        EM["Email forwards (IMAP)"]
        WA["WhatsApp (experimental)"]
    end

    subgraph Service["JobRadar service (one process, one container)"]
        direction TB
        subgraph Ingest["Ingest · free rules"]
            direction LR
            L["Links + short-link<br/>expansion"] --> D["Dedupe +<br/>ad filter"]
        end
        subgraph Understand["Understand · cheapest first"]
            direction LR
            F["Fetch page"] --> X1["1 · JSON-LD /<br/>job-board API"] --> X2["2 · Post labels"] --> X3["3 · Candidates,<br/>Jev picks"] --> X4["4 · LLM, only if<br/>role/company missing"]
        end
        subgraph Decide["Match and decide"]
            direction LR
            M["Match provider<br/>Jev → LLM → skills rule"] --> C["Composite score<br/>weights in code"] --> DEC["Decide<br/>hide · alert · inbox"]
        end
        DB[("SQLite<br/>jobs · match results · task queue")]
        D --> F
        X4 --> M
    end

    P[/"profile.yaml<br/>compact view: no name, email, phone"/] --> M

    subgraph Outputs
        direction LR
        N["Notion dashboard"]
        A["Email alerts + digests"]
    end

    EXT["External calls: job websites · TypeSafe Jev · Gemini / Groq via LiteLLM"]

    Sources -- "raw messages" --> L
    D -- "row in ~1 s" --> N
    DEC -- "score, reason, status" --> N
    DEC -- "strong + confident" --> A
    N -- "Shortlisted / Skipped" --> DEC
    Service -.-> EXT

    style N fill:#e3eefc,stroke:#3b82f6,color:#111
    style M fill:#e3eefc,stroke:#3b82f6,color:#111
    style A fill:#dcf1e4,stroke:#23774a,color:#111
    style EXT fill:none,stroke:#888,stroke-dasharray: 5 5
```

Every pipeline step reads and writes the SQLite store through the task queue, so steps can retry independently and an alert is never sent twice. A job's Notion row appears as soon as it is found; details, the match score and the status follow. Notion is both an output and an input: the poller reads Status changes and collects Shortlisted/Skipped choices for threshold suggestions.

## Components and responsibilities

| Component | Responsibility | Input → Output |
|---|---|---|
| Source adapters | Listen to Telegram (Telethon), read jobs you forward to an email folder (IMAP) and optionally WhatsApp; normalise messages | Platform events → `RawMessage` rows |
| Link extractor | Pull URLs from text, entities and buttons; expand short links; strip tracking params; OCR images | RawMessage → candidate URLs + text |
| Deduper | Canonical-URL hash and company+role+location fingerprint; attach extra sources to existing jobs | Candidates → new Job or merge |
| Fetcher | Download page with httpx; fall back to Playwright for JavaScript pages; skip login walls | URL → cleaned page text |
| Extractor (layered) | Fill the `JobPosting` fields cheapest first: structured page data, the post's "Label: value" lines, rules that find candidate values with Jev choosing among them, and an LLM only when role or company is missing. Records the source of each field | Page + post → structured job |
| Matcher | Ask one Jev request per job: eligibility, role alignment, skills coverage, seniority and location fit, overall fit, each with probability/confidence. Falls back to an LLM, then a skills-overlap rule | Job + compact profile → stored answers |
| Scorer | Combine stored answers with configurable weights into a 0–100 Match Score and a reason line; scam heuristics | Answers → score, confidence, reason |
| Decider | Apply policy in order: confidently ineligible → Hidden; high scam risk → flagged, never emailed; low confidence → Inbox "unsure"; strong and confident → alert; else Inbox | Score + answers → status, alert |
| Notion sync | Upsert job pages (write); poll for Status changes (read) | Job ↔ Notion page |
| Notifier | Email alerts (one per job, batched within 10 minutes, daily cap), closing-soon reminders and a twice-daily digest over SMTP | Events → emails |
| Tuner | Re-score open jobs when the profile changes; suggest an alert threshold from Shortlisted/Skipped jobs | Profile + Notion choices → suggestions |
| Scheduler and queue | Run workers, retries with backoff, periodic jobs (Notion poll, digest, cleanup) | Tasks → executions |
| Store | SQLite: messages, jobs, sources, fetched pages, match results, LLM cache, tasks | Shared state |

## Key flows

Every job lands in Notion. Only strong, confident matches send an email.

```mermaid
flowchart TB
    subgraph FA["Flow A · new post to Notion and email"]
        direction TB
        A1["Post saved to SQLite"] --> A2["Links · dedupe · ad filter"]
        A2 --> A3["Notion row<br/>title = post's first line"]
        A2 --> A4["Fetch page"] --> A5["Extract<br/>free layers, LLM fallback"] --> A6["Jev match<br/>eligible · role · skills · location · fit"]
        A6 --> A7{"Decide"}
        A7 -- "confidently ineligible" --> A8["Hidden, with reason"]
        A7 -- "strong + confident<br/>+ not scam" --> A9["Email alert<br/>once per job"]
        A7 -- "otherwise" --> A10["Inbox, sorted by<br/>Match Score"]
        A2 -.- N2>"duplicate: add sighting · ad: hide"]
        A4 -.- N4>"login wall: use the post"]
    end

    subgraph FC["Flow C · keeping scores right"]
        direction TB
        C1["profile.yaml edited"] --> C2["Re-score open jobs<br/>(cached per job + profile version)"]
        C3["User marks Shortlisted / Skipped"] --> C4["Suggest alert threshold<br/>(user confirms in config)"]
    end

    style A9 fill:#dcf1e4,stroke:#23774a,color:#111
    style A10 fill:#e3eefc,stroke:#3b82f6,color:#111
    style B6 fill:#e3eefc,stroke:#3b82f6,color:#111
    classDef note fill:none,stroke:none,color:#888
    class N2,N4 note
```

Flow A runs for every post within about 2 minutes. Flow B runs only for strong matches and jobs the user shortlists, which keeps LLM cost tied to likely applications. Flow C changes no thresholds on its own: re-weighting uses stored answers, and the alert threshold only changes when the user confirms it.

## Data model overview

SQLite is the source of truth; Notion is a projection of it. Full column definitions are in the [LLD](LLD.md).

```mermaid
erDiagram
    source ||--o{ raw_message : "receives"
    raw_message ||--o{ job_source : "seen as"
    job ||--o{ job_source : "posted in"
    job ||--o| fetched_page : "page text"
    job ||--o{ match_result : "scored per profile version"

    source {
        int id PK
        text platform
        text chat_id
        text title
        int last_msg_id
    }
    raw_message {
        int id PK
        int source_id FK
        text message_id
        text text
        text urls_json
        int processed
    }
    job {
        text id PK "sha1(clean URL)"
        text canonical_url
        text company
        text role
        text deadline
        text data_json "fields + source per field"
        int score
        text status
        text notion_page_id
    }
    job_source {
        text job_id FK
        int raw_message_id FK
    }
    fetched_page {
        text job_id PK
        text final_url
        text text
        text note
    }
    match_result {
        text job_id FK
        text profile_version
        text provider "jev | llm | rules"
        text answers_json
        real score
        real confidence
        real eligible
    }
    task {
        int id PK
        text type
        text key
        text status
        int attempts
        text run_after
    }
```

| Entity | Key fields | Notes |
|---|---|---|
| `source` | id, platform, chat_id, title, enabled | One per watched channel or group |
| `raw_message` | id, source_id, message_id, text, urls, received_at, processed | Unique on (source_id, message_id) |
| `job` | id (hash), canonical_url, fingerprint, company, role, deadline, data_json, score, status, notion_page_id | One row per real job |
| `job_source` | job_id, raw_message_id | Every place a job was seen |
| `fetched_page` | job_id, final_url, title, text, note | Main text of the job page between fetch and extract |
| `match_result` | job_id, profile_version, provider, answers_json, score, confidence, eligible | Raw match answers per profile version; weights and thresholds re-rank without new model calls |
| `llm_cache` | key, output, cost_inr | Model answers by model + prompt version + input, and their estimated cost |
| `task` | id, type, key, payload, status, attempts, run_after, last_error | Durable work queue; unique (type, key) |

The user profile lives in `profile.yaml`, not the database, so it can be edited and versioned by hand. Its hash is the `profile_version` that match results are stored under.

## External integrations

| Service | How | Auth | Limits to respect |
|---|---|---|---|
| Telegram (reading) | Telethon user client over MTProto | api_id + api_hash from my.telegram.org, session file | FloodWait errors; read-only, no auto-join |
| Email (notify + forwards) | SMTP (aiosmtplib, STARTTLS) to send; IMAP (imap-tools) to read one folder | Email address + app password | Provider send limits (Gmail about 500/day); alerts are batched, so a few dozen emails a day |
| WhatsApp (experimental) | Node sidecar with whatsapp-web.js or Baileys, posts messages to JobRadar over local HTTP | QR login | Unofficial; ban risk; off by default |
| Matching | **TypeSafe Jev** through the `typesafe-sdk` Python package (`system_one` with Choice / Score / Noul questions) | `TYPESAFE_API_KEY` | Early access; at most 255 options per Choice; per-account limits; cache by job + profile version |
| LLM (fallback) | LiteLLM: **Gemini (default) or Groq**; other hosted providers possible through LiteLLM config; no local models in v1 | `GEMINI_API_KEY` or `GROQ_API_KEY` | Provider rate limits and free-tier quotas; daily budget; cache by model + prompt version + input |
| Notion | Official REST API over httpx, `Notion-Version: 2025-09-03` (data sources) | Internal integration token, database shared with it | About 3 requests/second; 2,000 characters per text item; 100 blocks per append |
| Job websites | httpx, Playwright (Chromium) | None | 1 request/second per domain; obey robots.txt; skip login walls |

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+, asyncio | Best libraries for Telegram, email, scraping and LLMs |
| Telegram | Telethon | Mature, async user client |
| Email | aiosmtplib, imap-tools | Works with any provider; no bot or app to install |
| HTTP / browser | httpx, Playwright, trafilatura (main-text extraction) | Fast path plus a JavaScript fallback |
| OCR | Tesseract via pytesseract (optional: vision LLM) | Free, offline |
| Matching | TypeSafe `typesafe-sdk` (Jev) | Typed answers with calibrated confidence; about ₹0.01 per job at the published price |
| LLM (fallback) | LiteLLM + Pydantic schemas with our own validation; Gemini / Groq | Any provider, validated JSON, cheap defaults |
| Storage | SQLite (WAL mode) + SQLModel | Zero setup, enough for one user |
| Config | pydantic-settings, YAML + .env | Typed and validated at start |
| Dashboard | Notion REST API (httpx) | No frontend to build or host; pinning the API version ourselves avoids waiting on SDK support |
| Packaging | Docker + docker compose, uv for dependencies | One-command install |
| Quality | pytest, ruff, mypy, GitHub Actions | Standard for open source |

## Deployment

One `docker compose up -d` starts everything on a laptop, a home server or a small VPS (1 vCPU, 1 GB RAM is enough with a hosted LLM).

```mermaid
flowchart LR
    subgraph Host["Docker host"]
        J["jobradar<br/>Python app, all workers,<br/>Tesseract"]
        B["browser<br/>Playwright Chromium"]
        W["wa-bridge<br/>Node WhatsApp sidecar"]
        V1[("./data<br/>SQLite, sessions")]
        V3[("./config<br/>config.yaml, profile.yaml")]
    end
    J --> B
    W -. experimental profile .-> J
    J --- V1 & V3
    style W stroke-dasharray: 5 5
```

| Container | Contents | Required |
|---|---|---|
| `jobradar` | Python app, all workers, Tesseract | Yes |
| `browser` | Playwright Chromium (or bundled in `jobradar`) | Yes, for JavaScript pages |
| `wa-bridge` | Node WhatsApp sidecar | No, experimental profile |

**Volumes:** `./data` (SQLite, session files), `./config` (`config.yaml`, `profile.yaml`).

**First run:** `jobradar init` creates config from examples, logs in to Telegram (code sent to the app), and checks the Notion database schema.

## Reliability, scaling and cost

### Reliability

- Every message is written to SQLite before any processing, so a crash loses nothing.
- Each step is a durable task row; workers are idempotent (keyed by message id or job id), so retries are safe.
- Retries use exponential backoff (30 s, 2 min, 10 min, 1 h); after 5 failures the task is marked failed and shown in a Notion "Errors" view or log.
- On restart, Telethon catches up from the last stored message id per chat.

### Scaling

- Target load (2,000 messages, 300 unique jobs a day) fits one process with about 4 concurrent fetch workers.
- Dedupe runs before any fetch or LLM call, so cost scales with unique jobs, not messages.
- Heavier users can swap SQLite for Postgres behind the same repository layer.

### Cost control

- Free layers first: structured page data and the post's labels fill most fields at no cost.
- Jev for selection and matching (about ₹0.01 per job at TypeSafe's published price, which may be subsidised).
- An LLM only when role or company is still missing, and a stronger model only for job summaries.
- Changing weights or thresholds re-ranks from stored answers; no new model calls.
- Cache LLM results by job id and prompt version; never re-extract an unchanged job.
- Daily LLM budget in config; when hit, LLM tasks pause and the digest says so.

## Security and privacy

- **Secrets** (API keys, tokens, the email app password) only in `.env`, loaded by pydantic-settings; never logged; `.env.example` ships with placeholders.
- **Telegram session file** gives full account access: stored in `./data` with permissions 600 and listed in `.gitignore`; docs warn never to share it.
- **Personal data** (`profile.yaml`) stays local. Matching sends TypeSafe only job text and a **compact profile** (education, skills, experience bullets, preferences); never name, email or phone. Fallback extraction sends job text to the chosen LLM provider.
- **Untrusted input:** job pages and messages may contain prompt-injection text. They are passed to the LLM only as data inside delimiters, outputs are schema-validated, and the LLM has no tools or write access.
- **Email:** use an app password, not the account password; JobRadar sends only to `NOTIFY_TO`, reads only one folder, and accepts forwards only from your own address with DKIM/SPF pass.
- **Outbound requests:** fetcher blocks private IP ranges and `file://` URLs to avoid SSRF from malicious links.
- **Repository hygiene:** gitleaks secret scanning in CI; Dependabot for dependency updates.

## Extensibility (plugin model)

Four extension points, each a small Python interface registered by entry points (`jobradar.sources`, `jobradar.sinks`, `jobradar.site_adapters`, `jobradar.match_providers`). Contributors add a module and a line in `pyproject.toml`; the core does not change.

| Extension point | Interface | Built-in implementations | Examples contributors could add |
|---|---|---|---|
| Source | `async def run(emit)` | telegram, email_forward, whatsapp (experimental) | job-alert emails (LinkedIn, Naukri), RSS, Discord |
| Site adapter | `match(url)`, `extract(page)` | generic, google_forms | Greenhouse, Lever, Workday public pages |
| Sink | `upsert(job)`, `poll_changes()` | notion, email_notify | Telegram bot, Slack, Google Sheets, Airtable |
| Match provider | `match(job, profile) -> MatchAnswers` | jev, llm, skills_rule | other decision models, local embedding similarity |

LLM providers are pluggable through LiteLLM config.

## Design decisions and alternatives

| Decision | Chosen | Rejected alternative | Reason |
|---|---|---|---|
| License | MIT | AGPL-3.0 | Maximum adoption and contribution |
| Dashboard | Notion database | Custom React app, Streamlit | No frontend to build or host; duplicable template; works on phone |
| Telegram reading | User client (Telethon) | Bot API | Bots cannot read channels unless they are admins |
| Notifications | Email (SMTP) | Telegram bot | Every user already has email; no bot to create; digests read better as email and stay searchable; one less Telegram integration to secure |
| Manual job adds | Forward to an email folder (IMAP) | Forward to a Telegram bot | Same channel as notifications; works for jobs found anywhere, not just Telegram |
| Queue | SQLite task table | Redis + Celery | One user, one process; no extra service to run |
| Source of truth | SQLite, Notion as projection | Notion only | Notion is slow and rate-limited; local DB keeps dedupe fast and offline-safe |
| Extraction | Free layers first, LLM only for what's missing | LLM for every job | Most fields are already structured on the page or labelled in the post; saves cost and free-tier quota |
| Matching | Jev (TypeSafe): one request of typed questions, composite score in code | LLM score with a written reason; embedding similarity | Calibrated confidence lets alerts require certainty; per-dimension answers re-weight without new calls; embeddings ignore eligibility and are not calibrated |
| Alert rule | Strong score **and** high confidence **and** eligible **and** not scam | Score threshold only | Fewer, more trustworthy emails; uncertain jobs still reach the Inbox |
| Vendor dependence | Provider interface with LLM and rule fallbacks | Jev only | Jev is early access and proprietary; a failed match never emails |
| LLM access | LiteLLM, Gemini / Groq default | One provider SDK | Cheap or free defaults; users can still choose cost and privacy |
| Notion change detection | Polling every 2 minutes | Webhooks | Webhooks need a public URL; most users run at home |
| Applying | Human submits | Auto-fill and submit | Safer, honest, avoids bans and wrong submissions |
