# Changelog

All notable changes to JobRadar are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions will follow [Semantic Versioning](https://semver.org/) from the first release.

## [Unreleased]

### Removed
- **The resume, the ATS check, the apply kit, the application and interview tracking are gone.** JobRadar now finds, ranks and tells you about jobs; applying is yours. Deleted with them: the `resume/`, `kit/` and `storage/` packages (the builder, the LaTeX template, the PDF text check, the Google Drive upload), the `jobradar resume` command, the `jobradar followups` and `jobradar sources` commands, the follow-up reminders, the reader for replies from companies, the **Interviews by source** list, the **Applications** board and its funnel, the resume panel and follow-up draft on a job's page, the `artifact` table, the `resume` and `storage` settings, `scoring.auto_resume_above`, `notify.followups`, `notify.followup_after_days` and `notify.company_replies`, and the **Resume**, **Cover Letter** and **Followed Up** Notion columns.
- The email buttons are now **Shortlist** and **Not interested** (they were **I applied** and **Not interested**), and the statuses are New, Shortlisted, Skipped and Hidden. A job that still carries an old status (Applied, Interview, Offer, Rejected, Resume ready) becomes Shortlisted or Skipped the first time the database is opened; an old Notion Status option is read the same way.
- The dashboard is now Today, All jobs, Skills, the Digest and a page per job. `pypdf` is no longer a dependency.

### Added

**Local model servers (no API key)**
- JobRadar can now run the model on your own machine, so you never have to enter an API key. `jobradar llm setup --cookies <file>` installs two local servers: Gemini Web, which answers through your signed-in Gemini session, and DeepSeek Web, which does the same for DeepSeek and waits as the fallback when Gemini can't answer. Both speak the OpenAI API on 127.0.0.1, so extraction and matching read exactly as they did with a hosted key.
- `jobradar llm` shows the whole chain in one view (the model, the writer model, the fallback) and what each server offers right now. `jobradar llm use <provider/model>` switches the model in config.yaml without touching your comments, `jobradar llm test` asks one small question so you can watch it answer, and `jobradar llm start` / `stop` run the servers. `jobradar run` starts them for you when config.yaml points at one, so nothing has to be started by hand after a restart.
- The fallback chain is part of the model call now: when the model in use can't answer (the server is down, the cookie expired), the next model in `llm.fallback_models` answers instead. Only when every model fails does the job go back in the queue.

**Türkiye daily gig finder**
- A new mode for the same agent: find work that pays by the day, the hour, the task or the project, in Ankara or remote, and say so the moment it appears. `jobradar gig scan` reads every source, reads each new ad, and keeps only the short-paid ones. While `jobradar run` is up the same scan runs every `gig.every_minutes` (30 by default) and the new gigs are emailed as they appear (`notify.dry_run` still saves the email as a preview instead of sending it).
- The payment model is read from the ad's own words, not from "part-time": a daily wage, an hourly rate, a fee per task and a fee per project are kept apart, and an ad that says nothing about pay goes to its own *uncertain* pile instead of being called a gig. Full-time, monthly-only and heavy-lifting work is dropped with the reason kept, remote work counts wherever the company is, and work on site outside Ankara is dropped.
- The same ad on two sites keeps one row (title, company, pay and place make the fingerprint), the ad's own structured data (schema.org JobPosting: date posted, company, place, pay) is used before the prose, and a known ad is never read twice.
- 28 sources, one adapter each, in the brief's order: Eleman.net (Ankara and the daily listings), İşin Olsun, Telegram (public channel previews), R10, Upwork, DataForce, OneForma, RWS TrainAI, OpenTrain AI, Bionluk, Armut, Facebook, WhatsApp, Sahibinden, Kariyer.net, SecretCV, Indeed, LinkedIn, the Ankara city hall, Contra, Mindrift, Corpshore, Rise Data Labs, TELUS Digital and Rasyonel Kariyer.
- `jobradar gig validate` runs the nine source checks (reachable, listing, ad details, link, date, pay, the Ankara filter, dedupe, and a second scan finding the same ads) and prints what each source can do. `jobradar gig sources` shows how each source has been doing; `jobradar gig list` shows the gigs, the uncertain ones or the dropped ones. The run of 1 November 2026: 14 sources work, 12 are blocked and 2 are manual ([docs/GIG_SOURCES.md](docs/GIG_SOURCES.md)).
- Nothing is scraped around a block: a source that answers 403, a bot challenge page, a robots.txt rule or a missing page is reported as blocked and left alone. Facebook and WhatsApp groups need an account, so their ads come in by hand through `jobradar gig add`.
- **A gigs page on the dashboard** (`/gigs`): the short-paid work with what it pays, where it is and when it was posted, plus a count in the sidebar.
- **Stricter rules, from what the first real scans showed:** "günlük raporlama" (daily reporting) and "haftalık toplantı" (a weekly meeting) are not payment models, so "günlük" and "haftalık" only count as one when the money is next to them; a bare number next to the unit has to be a wage, not a headcount ("günlük 3 kişi"); an ad that says "tam zamanlı" is out even when it also says "günlük", unless it states a daily pay. The board's own data is used first where it exists: the schema.org JobPosting of the ad (date, company, place, pay) and the ItemList of the listing page (the real title, instead of "Apply now").


**Dashboard (read-only, first step)**
- `jobradar web` opens your jobs on a page at http://127.0.0.1:8080, read from JobRadar's own database: **Today** (good matches from the last 3 days you haven't acted on, best first), **All jobs** (search by company or role, filter by status, 50 per page) and a page for each job (score reasons, details, where it was posted, your status history, the page text JobRadar read). Install once with `uv sync --extra web` (FastAPI and Uvicorn, an optional extra). Read-only for now; statuses still change from the email buttons or Notion.
- Blip lives in the dashboard: the sidebar shows whether it's watching (it read something in the last 20 minutes, with a pulsing dot) or asleep ("wake it with `jobradar run`"), and Today opens with Blip greeting you by your profile's first name and naming the best match (poke it for tips; it hops and waves). Each job page has "Blip's take", the score reason as a sentence. Score rings, company initials, live counts in the sidebar (Today, All jobs), a numbers strip (good matches, shortlisted, jobs found, closing in 48 h), a light / dark / system theme switch, and `/` to search.
- More detail, all from data JobRadar already keeps: Today shows a 14-day chart (jobs found per day, and how many scored `alert_above`+) and where your good matches came from (each Telegram chat; company boards as one line); quick filters (Eligible, Remote or hybrid, Internships, Closing this week). Each job page shows how the score was made (each weighted part as a bar with its share, whether it's open to you, how sure the AI was), the job's skills marked green when they're on your profile and red when required and missing, and a deadline countdown. `Ctrl+K` jumps to any job by company or role; `j` / `k` move down a list and `Enter` opens; `g` then `t` / `j` / `s` / `d` goes to a page.
- Today's list, reworked: a toolbar with filters (All, Eligible, Remote or hybrid, Internships, Closing soon) that each show how many jobs they'd leave, a search box that narrows the list as you type (role, company or place), and a sort (best match, newest first, closing soonest), all working together; your choice is remembered, and the filter is in the address (`/#internship`) so you can bookmark it. Cards show a coloured score stripe, a "New" badge for jobs first seen in the last 6 hours, how long ago each was seen, the deadline countdown, and **Open job** / **Details** buttons; the whole card opens the job. A filter that leaves nothing says why, with one click back to all. Fixed: after an update the browser could keep running the old `app.js` (so the filters did nothing); the CSS and JS addresses now change whenever the files do.
- **Digest** page: the morning and evening digest on the dashboard. It opens on the latest one that went out, with chips for the ones before it (8 in all) and **So far** for what the next one will say. Blip's summary, the numbers (new jobs, scored 75+, still in your inbox, alerts emailed, closing soon), new jobs best first, closing soon, jobs from company boards, skills you keep missing, what was hidden and why, AI spend and failed tasks. **See it as emailed** opens the exact email. An earlier digest leaves out jobs, alerts and status changes that came after it. `g` then `d` opens it.
- Sort by time: Today adds **Oldest first** next to Newest first; All jobs gets a sort (Newest first, Oldest first, Best match) that applies as soon as you pick it, and keeps it across pages.
- Change a status from the dashboard: **Shortlist** and **Not interested** on new jobs (the card slides out of Today), and on each job's page a **Your move** panel with a **Change status** menu that sets any status (for fixing a mistake). A toast confirms each change with **Undo**. Buttons only move a job forward, by the same rules as the email buttons (now one shared module); Change status goes anywhere. Every change is in your status history and Notion follows through the queue. Each request must carry a secret only the dashboard's own pages have, and requests from another site are refused. Without JavaScript the buttons still work as plain forms.
- When an email button can't change anything (say **Not interested** on a job you've already skipped), JobRadar now emails you back with the reason and a link to change it in the dashboard, instead of only writing a log line.
- `jobradar run` starts the dashboard too, so there's one thing to start (`web.enabled: false` leaves it out; if its port is taken or the web extra isn't installed, JobRadar runs without it and says why). Your clicks wake the worker at once, so the Notion write starts right away. Alert and digest emails get a **View in dashboard** button on each job.
- **Skills** page: what your good matches ask for that your profile lacks and what it has, over 7, 30 or 90 days, with bars, each skill's share of jobs, the change from the window before (once there is one), and the best jobs behind each. **I know …** adds the skill to profile.yaml's one-line `additional: [...]` list: only that line changes, a backup is kept, and the file is checked after the edit and put back if it doesn't read the same.
- **The dashboard on your phone:** [docs/PHONE.md](docs/PHONE.md) shares it over your own Tailscale network in about ten minutes. Set `web.url` to the Tailscale address and the dashboard accepts requests for that name (and still refuses every other), and email links open there.
- **What exactly they want**, for each skill (`/skills/<skill>`), opening with a roll call: one tile per job, strictest first (filled when the job needs the skill, outlined when your skills already cover it), so the answer shows before you read a word. Below it: every job's own lines about it, sorted into must have, one of a few ("AWS, Azure or GCP"), nice to have, and covered ("Python, Java or C++" when you have Python or Java); what they name with it (AWS: Lambda, S3, DynamoDB, certification…; C++: STL, multithreading, Linux systems…; also Azure, Google Cloud, Linux, Kubernetes, Docker and generative AI); and the other skills asked for alongside. A missing skill's count on the Skills page now leaves out the jobs your skills already cover, so C++ no longer ranks high just because jobs list it next to Java.
- All jobs searches the **whole job**: page text, posts, skills and places, with matches highlighted in a snippet and a Most relevant sort (SQLite full-text search, brought up to date before each search). New filters: score, first seen within, place, remote or hybrid, and source (each Telegram chat, board or page).
- On phones: a bottom tab bar, bigger buttons, the Applications board swipes sideways a column at a time, and on Today you can swipe a card right to **Shortlist** or left for **Not interested** (Undo in the toast).
- Only this computer can open it: it listens on 127.0.0.1, refuses requests naming any other host (so a website can't pose as localhost), and pages can't be framed or load anything from the internet. `web.host: 0.0.0.0` is refused. If port 8080 is busy the next free one up to 8089 is used and logged; `web.port` sets another.

**Website**
- `site/`: a one-page site published to GitHub Pages by `.github/workflows/pages.yml`, in light and dark themes (follows the system, with a switch). It tells one real night from my log (15 Oct, 22:15 to 22:25) with the real timestamps: two Telegram posts, a finance job hidden as a weak match (29), Rubrik scored 79 and emailed six seconds later, QualComm scored 92 and held for the 10 minute pause, US sales roles skipped from the company boards. Blip, the mascot, annotates each moment in handwriting. Visitors can forward a post to Blip, which highlights each line it understands by field, dims the noise and underlines the skills you have or lack (read in the browser with the post-label rules, nothing sent), Static HTML, CSS and JS. The numbers section plots every alert sent so far (time from post to inbox, from the local database), the share of Telegram jobs read without AI, the 58 boards and the test count; "Arriving at JobRadar" shows planned work from PLAN.md on an Indian Railways departure board (feature, arriving next / expected soon / scheduled later, and the platform where you'll see it: Browser, Email, Digest, Notion…; your own dashboard is arriving next); tapping a row plays its station announcement; the night log ends with the weekly "Skills you keep missing" digest section with the owner's real counts; the setup section shows what each command prints on a first run.


**Skills you keep missing**
- Once a week the digest lists the skills your good matches asked for that your profile doesn't, with how many jobs named each ("AWS in 7 good matches, Google Cloud in 6, Kubernetes in 5"). `jobradar skills` shows it any time. No AI call: it reads each job's stated skills and the technology names in its own page and post (words like Go or Spring only from stated lists), counting synonyms once.
- New warning: a skill in profile.yaml cut in two by a comma inside brackets (`[Machine Learning (feature engineering, model training), ...]`) made matching miss it. JobRadar now says so at start and in `jobradar skills`; quote the item to fix it.

**Update jobs from your inbox, not Notion**
- Every job card in alert, digest and closing-reminder emails has **Shortlist** and **Not interested** buttons. Tap one and press Send on the email it opens: within 2 minutes JobRadar sets the job to Shortlisted or Skipped, in Notion too, and archives that email.
- JobRadar reads only these emails from your inbox over IMAP, with the login that already sends alerts. Each button's subject carries the job and a signature only your JobRadar can make, and must come from your own address, so nobody else can change your jobs. Statuses only move forward (a late **Shortlist** never undoes a **Not interested**).
- `jobradar replies --check` reads the inbox once now; `notify.email_actions: false` turns the buttons off.



**More places to find jobs**
- Workday career sites (`sources.boards.workday`, e.g. `NVIDIA: nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`): India postings only, read at most every 30 minutes. Only postings Workday dates within the last 3 days count as new, and at most 10 are passed on per read. A site with more postings than one read takes, in an order that changes between reads (Accenture), passes nothing on; `jobradar boards` says why.
- Oracle Recruiting Cloud career sites (`sources.boards.oracle`, e.g. `Zensar: fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com/CX_1`, or the careers link): India postings only, at most every 30 minutes, the same 3-day and 10-per-read rules. Oracle lists newest first, so a site with more India postings than one read takes (Kotak, EXL) still passes on new ones from the top. Oracle job pages are JavaScript only, so JobRadar reads the job's public detail data instead: the description, experience and posting date are found with no AI call, and the still-open check covers Oracle links.
- freehire (`sources.freehire`, off by default): freehire.me's public job search across about 90 hiring systems, filtered by `countries`, `seniority` and `categories`, at most every 15 minutes. Its postings go through the normal pipeline and the still-open check.
- Hiring-drive pages (`sources.pages.watch`, `jobradar pages add <name> <url>`): pages that announce drives instead of listing jobs are read every 1 to 6 hours and new lines become a post. robots.txt is obeyed, nothing is logged into, and a page that keeps refusing is paused until `jobradar pages resume`.

**Fewer wrong alerts**
- Experience is read from the job page's own description, so "Minimum 5 years" on a board posting now counts (8 Accenture alerts for 5-year roles reached a fresher before this).
- A job whose page couldn't be read, with a post under 300 characters and no stated requirements, never alerts: a title alone isn't enough to score it.
- One role across cities is one job: the same company and role seen again within 30 days (Pune, Bengaluru, Hyderabad) joins the first job instead of alerting again.
- Job age: each job keeps its publish date from the company's page or board (never guessed by the AI). Notion gets a **Posted On** column, alerts show "Posted 2 Sep", and a posting published more than `notify.old_posting_days` (30) ago doesn't alert.


**Still-open check, sources and reminders**
- Before a job is matched, JobRadar asks its hiring site whether the posting is still open, for links to Greenhouse, Lever, Ashby and SmartRecruiters postings. A closed one is hidden ("posting closed on the hiring site") with no Gemini call. Only a definite answer hides a job: a 404/410, or the posting missing from an Ashby board that was read fine. Timeouts, rate limits, redirects and other sites change nothing. Requests go only to the platforms' fixed API hosts.
- New Notion column **Source**: where each job was seen ("Telegram · Freshershunt", "Greenhouse · Stripe", "Added by you"). JobRadar adds the column to your database on start and fills it in on existing pages; group a view by Source to see jobs per channel or board.
- Alerts say which board a job came from ("posted 4 min ago on Stripe's Greenhouse board"), and the digest lists new jobs from company boards in their own section.
- Closing-soon reminder: one email when a job you shortlisted closes today or tomorrow, sent between 08:00 and 22:00, once per job. A posting that has already closed on its hiring site is skipped. Turn it off with `notify.closing_reminders: false`.
- `jobradar boards add <link>` (or `<ats> <board>`) adds a board to config.yaml after checking that it exists and showing how many of its postings pass your filters; `jobradar boards remove <name>` takes one out. Your comments and layout in config.yaml are kept.

**Company job boards (job feeds)**
- JobRadar reads company job boards directly through their public APIs (Greenhouse, Lever, Ashby, SmartRecruiters), every 20 minutes per board, so new postings arrive minutes after they go up instead of when a channel reposts them. List them in `sources.boards` under their hiring system as `Name: board name`, e.g. `greenhouse: {Stripe: stripe}` (a board link works too).
- The first read of a board only records what's there: no alerts for old postings. Later reads pass new postings in India (or remote with no other country named), with a tech title and not clearly senior, into the normal pipeline as posts from "Greenhouse · Stripe": dedupe, free extraction, matching, alerts and digest work as for Telegram.
- A posting that leaves its board hides its job ("closed on the company board") if it's still untouched in your Inbox.
- Errors never look like an empty board: a 404 counts towards "board gone" (3 in a row: retried after 30 days), any other error changes nothing, and a board that suddenly lists nothing is ignored for that round.
- `jobradar boards` shows each board's health and its newest posting with what the filters made of it; `jobradar boards --check` reads them all now.
- Every new board posting is logged as `board posting passed` or `board posting skipped` with the reason (not in India, remote but not open to India, not a tech role, too senior).
- Existing databases get the new "board" source type through a one-time table upgrade, with a backup written first (`jobradar.db.before-board-sources.bak`).

**Your statuses from Notion**
- Every 2 minutes JobRadar reads the Status you set in Notion (Shortlisted, Skipped, Hidden, or New to un-hide) and keeps a dated history of it. An older database's Applied, Interview, Offer, Rejected or Resume ready map to Shortlisted or Skipped.
- A job you've set yourself is never hidden, re-decided or alerted on by JobRadar again; its score still updates.
- The digest shows "Your shortlist: 15 shortlisted (+2 shortlisted since then)".
- `jobradar stats` shows your shortlist, alerts sent, and suggests `scoring.alert_above` from the scores of the jobs you shortlisted.

**Readable emails**
- Alerts, digests and the test email share a new design built for email clients: a card per job with a coloured score tile, role and company, labels for fit, eligibility, freshness and deadline, "You have / Missing" skill rows, and Apply / Open in Notion buttons. The digest opens with four numbers (new, in your Inbox, hidden, alerts) and has clear sections. Plain-text versions are tidier too.
- The digest is named by time of day (morning, afternoon, evening).

**Instant alerts**
- The first alert is emailed as soon as the job is matched, about 30 seconds after the post. Strong jobs arriving within `notify.alert_batch_minutes` of an email are grouped into one follow-up at the end of that window, so a burst of posts doesn't flood your inbox.
- Each alert says when and where the job was posted ("posted 3 min ago in Freshershunt").
- Fast lane: work for jobs first seen in the last hour runs before catch-ups, re-matches and backfills (new `task.priority` column, added automatically).
- `scoring.alert_above` defaults to 75.

**Daily digest**
- A summary email at each `notify.digest_times` slot (09:00 and 19:00 by default) covering everything since the previous one: new jobs, the top 5 still in your Inbox with score and reason, jobs closing in the next 2 days, what was hidden and why, alerts sent, failed tasks and Gemini spend. A window with nothing to report sends nothing.
- Dry run applies: digests are saved to `data/alerts/digest-*.html` instead.
- `jobradar digest --now` sends the digest for the current window right away.

**v0.2 part B2: decide and email alerts**
- After matching, each job is decided in order: not eligible or an excluded company → hidden; likely scam → flagged, never emailed; unsure → Inbox; score below `scoring.hide_below` → hidden ("weak match"); strong, clearly eligible and confident → email alert; otherwise → Inbox.
- With `matching.branch_strict: true`, jobs limited to branches that clearly exclude yours are hidden. Close branches (Electrical with Electronics, "or related branches") still count.
- Scam check (Scam Risk column): deposits, training or kit fees, "pay to confirm your offer" → high; an application fee in the post, a personal-email-only contact, pay per day or week, pressure to hurry → points. No false alarms on the first 132 real jobs.
- Email alerts over SMTP to `NOTIFY_TO`: once per job, batched within `notify.alert_batch_minutes`, at most `notify.max_alerts_per_day`. **Dry run is the default**: alerts are saved to `data/alerts/*.html` instead of sent.
- JobRadar never overwrites a Notion Status you set yourself (Shortlisted, Skipped…) when it hides a job.
- Alerts only for fresh, open jobs: first seen within `notify.alert_max_age_days` (default 2) and the deadline not yet passed. Skipped alerts are logged with the reason.
- `jobradar alerts --test` sends you one test email (even in dry run) to check that Gmail sending works.
- Only a job's first match can alert: the startup catch-up and re-matching after a profile or prompt change never do, so old jobs can't flood your inbox. Changing the match prompt re-matches open jobs.

**v0.2 part B1: Match Score**
- Every read job is matched against `config/profile.yaml` and gets a 0-100 **Match Score** in Notion, with a reason line at the top of the JobRadar toggle, e.g. "Good fit · 86 · eligible ✓ · Python, SQL ✓ · missing Docker · Pune ✓".
- Batch years and maximum experience (`filters`) are checked in code first; a job that fails them is marked "Not eligible: batch 2023-2024 only" without any LLM call.
- The LLM answers fixed questions (eligible, location, role alignment, skills coverage, seniority, overall fit) as levels; code turns them into the score with `matching.weights`. Answers are stored, so new weights re-score for free at the next start, and editing the profile re-matches open jobs.
- `matching.branch_strict: true` treats "CSE/IT only" jobs as not eligible.
- Only education, skills, experience and project bullets, preferences and filters are sent for matching: never your name, email, phone, links or form answers.
- No LLM key: `skills_rule` scores by skill overlap (shown as "skills only").

**v0.2 part B4a: free extraction first, LLM as fallback**
- Job details are read from the job page's schema.org JobPosting data and the post's own "Company: / Role: / Batch: …" lines (decorative bold text included) before any LLM call. The LLM is asked only when role or company is still missing (`llm.extract_mode: fallback`, the default; `always` keeps the old behaviour of reading every job with the LLM, which also fills summaries and skills).
- Jobs are read even without an LLM key, from page data and post labels alone.
- Each job records which layer filled each field (`_sources` in its data).
- `jobradar extract --compare [--refetch] [--examples N]` checks the free layers against what the LLM extracted earlier, field by field. On the first 136 real jobs, 68% needed no LLM call; company agreed 99% and role 93%.
- New columns on existing tables are now added automatically when JobRadar starts.

**v0.2 part A: reading jobs**
- Job pages are downloaded and their main text extracted, with robots.txt respected, one request per second per site, a public-address check on every redirect, and login-wall detection. Optional JavaScript rendering with Playwright (`--extra browser`).
- Gemini (through LiteLLM) extracts company, role, location, work mode, experience, skills, salary, deadline and apply link. Answers are validated, cached, and capped by a daily budget (`llm.daily_budget_inr`).
- Notion rows get their columns filled, the title becomes "Role @ Company", and the "JobRadar" toggle shows a summary, eligibility and skills.
- `jobradar extract --missing` reads jobs that were listed before an LLM key was set.

**v0.1: Telegram to Notion**
- Read-only Telegram reader with catch-up from the last message read and live updates.
- Link cleanup: short links expanded, tracking parameters removed, non-job hosts ignored, configurable `links.deny` and `links.extra_shorteners`.
- One Notion row per job, however many groups post it, with a "Seen In" count.
- Channel ads (links attached to posts about several different jobs) hidden automatically.
- SQLite task queue with retries, backoff and crash recovery.
- Commands: `init`, `run`, `chats`, `add`, `stats`, `retry --failed`.

**Project**
- Design documents (PRD, HLD, LLD), plan, README, wiki, security policy, code of conduct and contribution guide.

### Changed
- **Notion is optional:** `notion.enabled: false` stops every Notion call; no Notion key is needed, and emails link to the dashboard instead ("more in Today on the dashboard", "find them on the dashboard: All jobs, Show hidden"). Tasks already queued for Notion are dropped. On by default.
- **Telegram is optional too:** with `sources.telegram.enabled: false`, `jobradar run` and `jobradar init` no longer ask for Telegram keys or a login.
- The digest's "skills you keep missing" counts only the jobs that need a skill, like the Skills page: "Python, Java or C++" no longer counts against you for C++.
- Notifications will be sent by email instead of a Telegram bot.
- The default extraction model is `gemini/gemini-flash-lite-latest`.

### Fixed
- Security: pypdf 6.21.2 (three ways a malformed PDF could make reading it take very long) and virtualenv 21.14.13 (twelve issues in the developer tools behind `pre-commit`; the app itself doesn't use it). filelock stays at 3.32.7: the fixed 4.x needs a newer litellm, and JobRadar doesn't use the affected `ReadWriteLock` or Windows soft locks.
- Security: certifi (the list of certificate authorities JobRadar trusts for HTTPS) is updated to 2026.10.23. Older versions trusted emSign roots whose intermediate keys were stolen, so someone on your network could have faked a site JobRadar talks to, such as Gemini or Notion ([GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2)).
- `jobradar run` stopped right after starting when `sources.telegram.enabled` was false: the switched-off source finished at once and ended the run.
- Handled button emails (I applied, Not interested…) stayed in the Gmail inbox, only marked read: Gmail accepts taking the Inbox label off while the inbox is open but ignores it. They're now moved to All Mail, which is what Gmail's Archive does, and a failure is logged instead of passing silently.
- Oracle career sites (Zensar, Cummins…) often state the years of experience only in their own fields ("Minimum Experience (In Years)": 4) or a short summary, not in the description, so a 4-7 year Java Developer job looked open to freshers and was emailed. Those fields are now read, and `max_experience_years` hides such jobs.
- `jobradar stats` called every hidden job an ad. It now breaks hidden jobs down by reason (not eligible, weak match, not a job, hidden by you, ad or promo link) and lists only real ads as ads.
- An ad with a company name but no role (a "free webinar" post) no longer counts as a job; the matcher hides any that got through.
- A match whose answers contradict each other (a 99 score with the verdict "Not a fit") is marked unsure and never emailed.
- Notion rejected long posts with emoji, because it counts them as two characters.
- `go.acciojob.com` links weren't expanded, so a course ad became a fake job.
- Telegram "Apply" buttons were missed with the newer Telegram API layer.
- Configuration errors pointed at the wrong setting when a section was missing.

[Unreleased]: https://github.com/ThePlator/JobRadar/commits/main
