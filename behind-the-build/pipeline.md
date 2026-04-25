---
icon: pipe-collar
---

# Pipeline

Every writeup on this site starts as rough notes in Notion and ends up here — formatted, tagged, and published — without me touching GitBook once. Here's exactly how that happens.

---

## Overview

```
Notion (notes + metadata)
    ↓
ctf_auto.py (Python script)
    ↓
GitHub Actions (scheduled trigger)
    ↓
main branch (writeup files + READMEs)
    ↓
gitbook branch (force pushed, GitBook synced)
    ↓
CTF Hub (live)
```

One writeup per day, drip-fed automatically. If there's nothing queued, nothing happens.

---

## Notion — The Source of Truth

Every room gets a page in a Notion database with the following properties:

| Property | Type | Purpose |
| -------- | ---- | ------- |
| Note Title | Title | Room name |
| Platform | Select | TryHackMe, HackTheBox, LetsDefend etc |
| Difficulty | Select | Easy, Medium, Hard, Beginner, Insane |
| Category | Select | Machine, Sherlock, Challenge, Lab etc |
| OS | Select | Linux, Windows, Other |
| URL | URL | Link to the room |
| Tags | Multi-select | User-defined topic tags |
| Completed | Checkbox | Marks the room as done |
| Published | Checkbox | Marks it as pushed to GitHub |

The script queries for anything where `Completed = true` and `Published = false`. That's the publish queue.

---

## ctf_auto.py — The Engine

The script is the core of the whole thing. It runs top to bottom for one writeup per execution and handles everything:

### 1. Queue Check

```python
query_completed_unpublished()  # pulls from Notion API
```

If nothing is queued, it exits. If multiple writeups are queued, it takes the first and leaves the rest — one per day.

### 2. Auto-categorise + OS Detection

If the `Category` or `OS` fields aren't set in Notion, Claude infers them from the room name, URL, and description. These get written back to Notion automatically so the database stays clean.

```python
auto_categorise(platform, room_info, room_name)
auto_detect_os(platform, room_info, room_name, url)
```

### 3. Fetch Room Info + Icon

The script hits the room URL to scrape the description and pull the room icon via `og:image`. For THM, it also checks the S3 bucket directly. The icon gets saved into the writeup folder.

### 4. Download Screenshots

Any images embedded in the Notion page get downloaded and saved as `screenshot_01.png`, `screenshot_02.png` etc, and referenced in the markdown.

### 5. Generate Topic Tags

Claude gets a short prompt with the room name, description, and notes summary and returns exactly 3 topic tags:

```
prompt-injection, ai-security, llm
```

These get combined with the platform, difficulty, and type tags to build the full 6-tag set used across all README tables.

### 6. Format the Writeup

The raw notes get sent to Claude with a system prompt tailored to the room type:

- **Red team** (machines, walkthroughs) — narrative writeup, recon → exploit → privesc structure
- **Blue team** (Sherlocks, LetsDefend) — investigative writeup, evidence → findings → MITRE mapping
- **CTF challenges** — solution-focused, analysis → solve → flag structure

Terminal prompts are automatically formatted per platform:

```
kie@kiepc:~/THM/RoomName$       # TryHackMe
kie@kiepc:~/HTB/RoomName$       # HackTheBox
kie@kiepc:~/LetsDefend/RoomName$ # LetsDefend (blue team)
```

The formatted writeup gets written back to the Notion page as well, preserving the original rough notes in a collapsible section below.

### 7. Update README Tables

Every README in the hierarchy gets updated — platform, difficulty, OS level — with a new row for the writeup. The row format is consistent across all tables:

```
| Icon | Room | Difficulty | Tags | Date |
```

Tags are always 6: `#platform #difficulty #type #topic1 #topic2 #topic3`

### 8. Commit to Main Branch

```bash
git add .
git commit -m "writeup: Add TryHackMe - RoomName"
git push origin main
```

### 9. Sync to GitBook Branch

The script then checks out the `gitbook` branch, copies the new writeup files across, updates `SUMMARY.md` with the new entry, updates all README tables on that branch, commits, and force pushes:

```bash
git checkout -B gitbook origin/gitbook
# copy files, update SUMMARY.md and READMEs
git add .
git commit -m "sync: Add TryHackMe - RoomName"
git push origin gitbook  # force push always
```

The `gitbook` branch is always force pushed — it's a derived branch and never merged back into `main`.

### 10. Mark as Published

Finally, the `Published` checkbox gets ticked in Notion so the writeup doesn't get picked up again.

---

## GitHub Actions — The Trigger

The script runs on a cron schedule via GitHub Actions:

```yaml
on:
  schedule:
    - cron: '0 9 * * *'  # 09:00 UTC daily
  workflow_dispatch:       # manual trigger available
```

The workflow injects the required secrets as environment variables:

```yaml
env:
  NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
  NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

If there's nothing in the queue, the workflow exits cleanly in seconds. If there's something to publish, it runs the full pipeline.

---

## Branch Structure

| Branch | Purpose |
| ------ | ------- |
| `main` | Source of truth. Writeup files, scripts, READMEs. |
| `gitbook` | GitBook sync target. Always derived from main, never merged back. |

GitBook is connected to the `gitbook` branch only. Any changes GitBook tries to push back via PR are disabled — the branch is always overwritten by the pipeline.

---

## Tech Stack

| Tool | Role |
| ---- | ---- |
| Notion | Writeup database and note-taking |
| Python 3 | Pipeline script (`ctf_auto.py`) |
| Claude API | Writeup formatting and tag generation |
| GitHub Actions | Scheduled execution |
| GitHub | Version control and branch management |
| GitBook | Public-facing site, synced from `gitbook` branch |

---

> Source code available in the [CTF-Hub repo](https://github.com/Kieboard/CTF-Hub). The script is `scripts/ctf_auto.py`.
