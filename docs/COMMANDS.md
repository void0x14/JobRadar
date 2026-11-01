# JobRadar commands

Every command you need to set up, run, watch, tune and develop JobRadar, with what it does. Run them from the project folder (`cd JobRadar`).

- [First-time setup](#first-time-setup)
- [Start, stop, restart](#start-stop-restart)
- [JobRadar commands](#jobradar-commands)
- [Watching what happens](#watching-what-happens)
- [Changing settings](#changing-settings)
- [Updating to a new version](#updating-to-a-new-version)
- [Files and folders](#files-and-folders)
- [Fixing common problems](#fixing-common-problems)
- [Development](#development)

## First-time setup

```bash
uv sync
```
Installs JobRadar and its dependencies into `.venv/`.

```bash
uv run jobradar init
```
Copies `config.example.yaml` → `config/config.yaml` and `profile.example.yaml` → `config/profile.yaml` if they don't exist yet, logs in to Telegram (a code arrives in your Telegram app; nothing is posted), and checks that your Notion database has the right columns. Fill in `.env` first (see `.env.example`).

```bash
uv run jobradar chats
```
Lists every Telegram chat your account can read, with the ids to paste into `sources.telegram.chats` in `config/config.yaml`.

```bash
uv run jobradar alerts --test
```
Sends you one example alert email, so you know Gmail sending works.

## Start, stop, restart

JobRadar runs inside a `tmux` session called `jobradar`, so it keeps running after you close the terminal.

| What | Command |
|---|---|
| Start | `tmux new -d -s jobradar "uv run jobradar run 2>&1 \| tee -a data/run.log"` |
| Stop | `tmux kill-session -t jobradar` |
| Restart (after a config change or update) | stop, then start |
| Is it running? | `tmux ls` (shows `jobradar: 1 windows …` when it is) |
| Look at it live | `tmux attach -t jobradar`, then leave with `Ctrl+b` then `d` |

Don't press `Ctrl+c` inside the attached session: that stops JobRadar.

To run it in the foreground instead (stops when you close the terminal):

```bash
uv run jobradar run
```

On every start, JobRadar catches up on Telegram posts it missed, re-scores open jobs if you changed weights or thresholds, re-matches them if you edited your profile, and schedules the next digest.

## JobRadar commands

| Command | What it does |
|---|---|
| `jobradar run` | Start everything: Telegram reader, page reading, matching, Notion sync, alerts, digests, and the dashboard at http://127.0.0.1:8080 (`web.enabled: false` leaves it out) |
| `jobradar web` | The dashboard at http://127.0.0.1:8080: today's good matches, your applications board, every job, the digest, and buttons to change a status (Notion follows). Needs `uv sync --extra web` |
| `jobradar init` | First-time setup (see above) |
| `jobradar chats` | List Telegram chats with their ids |
| `jobradar add <url>` | Process one job link by hand and add it to Notion |
| `jobradar extract --missing` | Read jobs that were only listed (from before page reading existed) |
| `jobradar extract --compare` | Check how well free reading (page data, post labels) agrees with earlier Gemini answers |
| `jobradar stats --days 7` | Posts received, jobs created, reposts merged, ads hidden, likely duplicates, failed tasks |
| `jobradar retry --failed` | Put failed tasks back in the queue; they run on the next `jobradar run` |
| `jobradar boards` | Company job boards you watch: postings, how many were passed on, last read, problems, and each board's newest posting with why it passed or was skipped |
| `jobradar boards --check` | Read every board now (the first read only records a baseline) |
| `jobradar boards add <link>` | Add a board to config.yaml after checking it exists, e.g. `jobradar boards add https://jobs.lever.co/meesho --name Meesho`, `jobradar boards add greenhouse stripe --name Stripe`, a Workday careers link (`jobradar boards add https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite --name NVIDIA`; it must have an India location filter), or an Oracle careers link (`jobradar boards add https://fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs --name Zensar`; sites with more India postings than one read takes still pass on new ones, which Oracle lists first). Shows how many postings pass your filters now. Restart to start watching it |
| `jobradar boards remove <name>` | Remove a board from config.yaml by its name, board name or link (`--ats lever` if the name is in several sections). Restart to stop reading it |
| `jobradar freehire` | freehire.me's job search (`sources.freehire`): on or off, last read, postings in the search, how many were passed on, the newest one and why it passed or was skipped |
| `jobradar freehire --check` | Read the search now (the first read only records a baseline) |
| `jobradar pages` | Pages you watch for announcements (hiring-drive pages): posts made, last read, last change, state (watching, backing off, paused, blocked) and the last problem |
| `jobradar pages --check` | Read every page now (the first read only records a baseline) |
| `jobradar pages add <name> <url>` | Watch a page, e.g. a company's hiring-drive page: reads it once (robots.txt obeyed) and adds it to `sources.pages.watch` in config.yaml. Pick the page that lists the drives, not the careers home page. Restart to start watching it |
| `jobradar pages remove <name>` | Stop watching a page (by its name or address). Restart to stop reading it |
| `jobradar pages resume <name>` | Read a paused page (refused 3 times, or needs a login) or a robots.txt-blocked page again from its next turn |
| `jobradar alerts --test` | Send yourself a test alert email (works even in dry run) |
| `jobradar digest --now` | Send the morning/evening digest for the current window right away |
| `jobradar skills` | Skills your good matches named in the last 7 days that your profile doesn't list (`--days 30` for longer) |
| `jobradar replies --check` | Read the inbox now for "Shortlist" / "Not interested" button emails and update the jobs |
| `jobradar llm` | The local model servers: which model is in use, which fallback is waiting, and what each server offers |
| `jobradar llm use <provider/model>` | Switch the model in config.yaml (`--slot extract` or `--slot writer` for one of them) |
| `jobradar doctor` | *Not built yet*: check keys, tools and access |

Prefix each with `uv run`, e.g. `uv run jobradar stats --days 3`.

### `jobradar add <url>`

```bash
uv run jobradar add "https://careers.example.com/jobs/123"
```
Treats the link as if it was posted in a channel: cleans it, reads the page, matches it against your profile and creates or updates its Notion row. A link JobRadar already knows only gets a new sighting.

### `jobradar extract`

```bash
uv run jobradar extract --missing
```
Queues every job that has no details yet. `jobradar run` then reads them from page data and post labels, asking Gemini only when those miss role or company.

```bash
uv run jobradar extract --compare --examples 5
```
Re-reads jobs Gemini read earlier with the free layers and prints, per field, how many were found and how often they agree. `--examples 5` shows up to 5 disagreements per field. Add `--refetch` to download the pages again first (slow: one request per second per site, with no progress output).

### `jobradar stats`

```bash
uv run jobradar stats --days 3
```
A report for the last N days: posts received, posts without a job link, jobs created, reposts merged, ads hidden, likely duplicates (same job under different links), per-chat counts and recent failures.

### `jobradar retry --failed`

```bash
uv run jobradar retry --failed
```
A task fails after 5 attempts (e.g. a site down for hours). This puts them back; they run the next time JobRadar is running.

### `jobradar skills`

```bash
uv run jobradar skills
```
Counts, across your good matches (score at or above `scoring.alert_above`) from the last 7 days, the technologies they name that your profile doesn't list: "AWS 7, Google Cloud 6, Kubernetes 5…", each counted once per job and shown when two or more jobs name it. A job's skills are its stated skill list plus known technology names in its page and post; words that are also plain English (Go, Spring, Express) count only from stated lists. The first digest of each week shows the same list (`notify.skill_gaps: false` turns that off). If you already know one, add it to `skills:` in profile.yaml so matching counts it. It also warns if a skill in profile.yaml was cut in two at a comma inside brackets.

### `jobradar llm`

```bash
uv run jobradar llm
```
Shows the model chain in config.yaml (the model, the writer model, the fallbacks), then every local server with its address, whether it answers and the models it offers.

```bash
uv run jobradar llm setup --cookies ~/cookies.json
```
Installs the two local servers in `services/` (git-ignored): Gemini Web (a local API that uses your signed-in Gemini session) and DeepSeek Web (the fallback). `--cookies` takes the cookie export from your browser; without it the Gemini server keeps the cookie it already has. The file needs the cookies `__Secure-1PSID` and `__Secure-1PSIDTS`. The Gemini server is patched to listen on 127.0.0.1 only, so nothing on your network can use your session. A new cookie needs a restart: `jobradar llm stop` and `jobradar llm start`.

```bash
uv run jobradar llm start        # both servers
uv run jobradar llm stop
uv run jobradar llm start gemini-web
```
Starts or stops them on 127.0.0.1 (4981 for Gemini Web, 9655 for DeepSeek Web). `jobradar run` starts them for you when config.yaml points at one and it is not up yet.

```bash
uv run jobradar llm use gemini-web/gemini-auto
uv run jobradar llm use gemini-web/gemini-auto --slot writer
```
Switches the model in config.yaml, keeping your comments and layout. It warns when the server does not offer that model. With no argument it lists what every server offers, and with a server name alone it lists that server's models.

```bash
uv run jobradar llm test
```
Asks each model in the chain one small question and prints who answered and how long it took.

```bash
uv run jobradar llm login
```
Opens a Chrome window for the DeepSeek login, which the fallback needs once. Log in there, send a short message, then press Enter in the terminal.

### `jobradar gig scan`

```bash
uv run jobradar gig scan
```
Reads every gig source (Eleman.net, İşin Olsun, Telegram channels, R10, Upwork, DataForce,
OneForma, OpenTrain AI, Bionluk, Armut, Kariyer.net, SecretCV, LinkedIn, Indeed, Sahibinden,
the Ankara city hall, Contra, Mindrift, Corpshore, Rise Data Labs, TELUS Digital, RWS) and
keeps the ads that are really short-paid work: a daily wage, an hourly rate, a fee per task
or a fee per project, in Ankara or remote.

What it does with each ad:

- the payment model is read from the ad's own words. "Part-time" on its own is not enough;
- an ad that says nothing about pay goes to the *uncertain* pile, not to the gigs;
- full-time, monthly-only and heavy-lifting work is dropped, with the reason kept;
- remote work counts wherever the company is; work on site outside Ankara is dropped;
- the same ad on two sites keeps one row;
- the ad's own structured data (when the page has it) is used before the prose: the date,
  the company, the place and the pay.

`--source <key>` scans only that source (`jobradar gig sources` lists the keys),
`--no-details` reads only the listing pages, `--no-notify` skips the email. While
`jobradar run` is up the same scan runs every `gig.every_minutes` (30 by default) and the
new gigs are emailed as they appear.

### `jobradar gig list`

```bash
uv run jobradar gig list
uv run jobradar gig list --verdict uncertain
```
The gigs found, one per line: title, company, pay, place, how long, and the link.
`--verdict gig|uncertain|excluded` picks another pile, `--source` one source, `--limit` how
many.

### `jobradar gig sources`

```bash
uv run jobradar gig sources
```
How each source is doing: the last time it was read, how many times it failed, how many ads
it gave and how many of them were gigs. A source that is blocked says so, with the reason.

### `jobradar gig validate`

```bash
uv run jobradar gig validate
```
Runs nine checks against every source: can we reach it, can we read a listing, an ad's
details, its link, its date, its pay, can the Ankara and remote filter be applied, do the
results dedupe, and does a second scan find the same ads instead of new ones. The report
names every source that is blocked and why. Nothing is worked around: a source that answers
403 or a bot challenge is reported, not forced.

### `jobradar gig add`

```bash
uv run jobradar gig add --text "Günlük 1.500 TL yevmiye, Ankara Çankaya" --url https://...
```
Adds an ad by hand. This is the path for Facebook groups and WhatsApp groups: they need an
account, so nothing is scraped from them; copy the ad (or forward it) and run this.

### `jobradar web`

```bash
uv sync --extra web
```
Installs the dashboard's two extra packages (FastAPI and Uvicorn), once.

```bash
uv run jobradar web
```
`jobradar run` starts the dashboard too and prints its address (normally http://127.0.0.1:8080); `jobradar web` opens it on its own, when the agent is off. It reads JobRadar's own database either way; changes you make wait in the queue until `jobradar run` is running. Pages:

- **Today**: good matches (score at or above `scoring.alert_above`) from the last 3 days that you haven't acted on, best first.
- **All jobs**: search everything about a job (its page, the posts about it, skills, places: "kafka" finds every job that mentions Kafka, with the words highlighted), filter by status, score, how recently it was first seen, place, remote or hybrid, and where it came from, and sort by newest, oldest, score or relevance.
- **Skills**: the skills your good matches ask for that your profile doesn't list, and the ones it does, over 7, 30 or 90 days, each with the jobs that asked; **What exactly do they want?** opens a skill's own page (which jobs must have it, which take it as one of a few like "AWS, Azure or GCP", which call it a plus, which take a skill you already have instead, and the services or topics they name with it). **I know …** adds a skill to `profile.yaml` (to the one-line `additional: [...]` list under `skills:`, with a backup next to it) so matching counts it after the next restart.
- **A job's page**: why it scored what it did, the job's details, the skills it asks for and which of them you have, where it was posted, your status history, and the page text JobRadar read.

Change a status right on the page: **Shortlist** and **Not interested** on new jobs (each button only moves a job forward, like the email buttons); and **Change status** on a job's page for any status, to fix a mistake. A toast offers **Undo**. Notion follows within a minute while `jobradar run` is running (the change waits in the queue until then), unless `notion.enabled: false`. Only this computer can open it (`web.host: 127.0.0.1`); to open it on your phone, share it over Tailscale and set `web.url` ([PHONE.md](PHONE.md)). If port 8080 is taken, it uses the next free one up to 8089 and says which; `web.port` sets another.

### `jobradar replies --check`

```bash
uv run jobradar replies --check
```
Every job card in alerts, digests and reminders has **Shortlist** and **Not interested** buttons. A button opens a ready email to yourself: press Send and, while `jobradar run` is running, JobRadar reads it from your inbox within 2 minutes (IMAP, with the same `EMAIL_ADDRESS` and app password that send alerts), sets the job to Shortlisted or Skipped in Notion, and archives that email. Only emails from a button JobRadar sent you count: each carries a signature only your JobRadar can make. `--check` reads the inbox once now. Gmail needs IMAP on (Settings, Forwarding and POP/IMAP); it usually is. Turn the buttons off with `notify.email_actions: false`.

### `jobradar alerts --test` and `jobradar digest --now`

```bash
uv run jobradar alerts --test
```
Sends "[JobRadar] Test email: alerts reach you" with an example job card to `NOTIFY_TO` (or `EMAIL_ADDRESS`).

```bash
uv run jobradar digest --now
```
Builds the digest for the time since the last slot (09:00 or 19:00) and sends it, or saves a preview in dry run. Prints "nothing new… not sent" when there is nothing to report.

## Watching what happens

Everything JobRadar does is written to `data/run.log`.

| What | Command |
|---|---|
| Follow the log live (`Ctrl+c` stops watching only) | `tail -f data/run.log` |
| Follow only the important lines | `tail -f data/run.log \| grep --line-buffered -E "new job\|job extracted\|job matched\|job hidden\|alert email\|would have emailed\|digest\|budget\|ERROR\|Traceback"` |
| What the company boards found, and why each posting was skipped | `grep -E "board posting (passed\|skipped)" data/run.log \| tail -20 \| cut -c1-200` |
| What freehire found, and why each posting was skipped | `grep -E "freehire posting (passed\|skipped)" data/run.log \| tail -20 \| cut -c1-200` |
| What the watched pages did | `grep -E "page (baseline\|changed\|refused\|redesigned\|unavailable\|not usable)" data/run.log \| tail -20 \| cut -c1-200` |
| Watch for alerts | `tail -f data/run.log \| grep --line-buffered -E "new job\|decision=alert\|alert skipped\|alert email sent\|could not send"` |
| Jobs hidden because their posting had already closed | `grep "posting closed on the hiring site" data/run.log \| tail -20 \| cut -c1-160` |
| Closing-soon reminders for jobs you shortlisted | `grep -E "closing reminder\|already closed; no reminder" data/run.log \| tail` |
| What was hidden today, and why | `grep "job hidden" data/run.log \| grep "$(date +%F)" \| cut -c1-160` |
| Emails sent | `grep -E "alert email sent\|digest sent" data/run.log \| tail` |
| Problems only | `grep -E "WARNING\|ERROR\|Traceback" data/run.log \| tail -20` |
| Jobs read without Gemini | `grep 'job extracted' data/run.log \| grep -c 'llm=False'` |
| Dry-run previews | `ls data/alerts/` (open any `.html` file in a browser) |

What the main log lines mean:

| Line | Meaning |
|---|---|
| `telegram listening chats=7` | Connected and waiting for posts |
| `new job` | A new job link arrived |
| `duplicate job, added sighting` | A repost of a job JobRadar already has |
| `link hidden … reason=promo` | A channel ad or promo link, hidden |
| `job extracted … llm=False` | Details read from page data or post labels, no Gemini call |
| `job matched score=86 … decision=inbox` | Scored and kept in your Notion Inbox |
| `job matched … decision=alert` | A strong match: an alert email is on its way |
| `alert skipped why=…` | Strong, but too old or its deadline passed |
| `job hidden why=not eligible: …` / `weak match (32)` | Hidden in Notion, with the reason |
| `alert email sent` / `digest sent` | An email went out |
| `dry run: would have emailed` | Dry run is on: a preview was saved instead |
| `kept your Notion status` | JobRadar wanted to hide a job you had already moved, and left it alone |
| `daily LLM budget reached` | Gemini work paused until midnight |
| `task error, will retry` | A temporary failure (site or Gemini busy); retried automatically |

## Changing settings

Settings live in `config/config.yaml`; secrets in `.env`; your profile in `config/profile.yaml`. **Restart JobRadar after any change.**

Check the config is valid before restarting:

```bash
uv run python -c "from jobradar.config import load_settings; s = load_settings(); print('config OK')"
```

Common changes (`config/config.yaml`):

| To… | Set |
|---|---|
| Get more or fewer alerts | `scoring.alert_above` (75 = more, 85 = only very strong) |
| Hide fewer or more weak jobs | `scoring.hide_below` (default 40) |
| Send real emails instead of previews | `notify.dry_run: false` |
| One email per job instead of grouping follow-ups | `notify.alert_batch_minutes: 0` |
| Limit emails per day | `notify.max_alerts_per_day` |
| Change digest times | `notify.digest_times: ["09:00", "19:00"]` |
| Turn the digest off | `notify.digest: false` |
| Let Gemini do more per day | `llm.daily_budget_inr` (an estimate at list price; ₹0 on the free tier) |
| Ask Gemini for every job (adds summaries and skills) | `llm.extract_mode: always` |
| Hide or keep "CSE/IT only" jobs | `matching.branch_strict: true` / `false` |
| Graduation years you accept | `filters.batch_years: [2025, 2026]` |
| Cities (empty = anywhere) | `filters.locations: []` |
| Never show a company | `filters.exclude_companies: ["Acme"]` |
| Re-weight the Match Score (free, no new Gemini calls) | `matching.weights` |
| Add or remove a channel | `sources.telegram.chats` (ids from `jobradar chats`) |
| Ignore a site or ad link | `links.deny: ["example.com/courses"]` |
| Stop using Notion (the dashboard keeps everything) | `notion.enabled: false` |
| Run without Telegram (boards, pages and forwarded email only) | `sources.telegram.enabled: false` |
| Open the dashboard on your phone | `web.url: https://laptop.tail1234.ts.net` ([PHONE.md](PHONE.md)) |

Editing `config/profile.yaml`, `filters` or `matching.branch_strict` re-matches all open jobs at the next start: about one Gemini call per job.

## Updating to a new version

```bash
git pull
```

```bash
uv sync
```

Then restart (stop, then start). New database columns and tables are added automatically on start.

## Files and folders

| Path | What it is | Safe to delete? |
|---|---|---|
| `config/config.yaml` | Your settings | No |
| `config/profile.yaml` | Your education, skills, experience, projects | No |
| `.env` | Keys and passwords | No, and never share or commit it |
| `data/jobradar.db` | Every job, match, alert and task | No: this is JobRadar's memory |
| `data/tg.session` | Your Telegram login | Only to log out (then run `jobradar init` again); never share it |
| `data/run.log` | The log | Yes (JobRadar starts a new one) |
| `data/alerts/` | Dry-run previews of alerts and digests | Yes |

Back up before risky changes:

```bash
cp -r data data-backup
```

## Fixing common problems

| Problem | What to do |
|---|---|
| `tmux kill-session` says "no server running" | JobRadar wasn't running. Just start it |
| No alert emails | Check `notify.dry_run` is `false`, run `jobradar alerts --test`, and check the log for `decision=alert`. Each job alerts once, only if first seen in the last 2 days with its deadline not passed |
| `email login rejected` | The Gmail app password in `.env` is wrong or revoked: create a new one. JobRadar doesn't retry, so your account can't get locked |
| `daily LLM budget reached` | Wait until midnight, or raise `llm.daily_budget_inr` and restart |
| The local model server doesn't answer | `jobradar llm` shows which one is down; `jobradar llm start` runs it again, and `jobradar llm setup --cookies <file>` gives it a fresh cookie. Its log is in `data/local-llm/` |
| The local model server says "not logged in" | The DeepSeek fallback needs one login: `jobradar llm login` |
| A good job was hidden | Look at its reason in the log or Notion; adjust `scoring.hide_below`, `matching.branch_strict` or `filters`, or tell us in an issue |
| An ad shows up as a job | Add its link to `links.deny`, or report it with the "Ad or link" issue template |
| Tasks failed | `jobradar retry --failed`, then make sure JobRadar is running |
| Config error on start | The message names the setting; YAML needs exactly 2 spaces per level |

## Development

```bash
uv run pytest -q
```
Runs the tests (no network, no real keys needed).

```bash
uv run ruff check .
```
```bash
uv run ruff format .
```
```bash
uv run mypy
```
Lint, format and type-check: CI runs the same.

```bash
uv run pre-commit install
```
Runs the checks (and secret scanning) on every commit.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full workflow.
