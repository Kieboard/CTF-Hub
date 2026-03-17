# ⚙️ About This Repo

## How It Works

Every writeup in this repo is authored in Notion and published automatically via a custom CI/CD pipeline. Here's what happens under the hood:

### The Pipeline

```
Notion (notes + metadata)
        ↓
  GitHub Actions (trigger: 6pm UTC daily or manual)
        ↓
  Python script (ctf_auto.py)
        ↓
  ┌─────────────────────────────────────┐
  │ 1. Query Notion API                 │
  │    → Find Completed + Unpublished   │
  │ 2. Extract notes and metadata       │
  │ 3. Fetch room icon from platform    │
  │ 4. Scrape room description          │
  │ 5. Auto-detect OS (Linux/Win/Other) │
  │ 6. Generate topic tags via Claude   │
  │ 7. Send to Claude AI for formatting │
  │ 8. Save markdown + icon to GitHub   │
  │ 9. Update OS-level README table     │
  │ 10. Update difficulty README table  │
  │ 11. Update platform README table    │
  │ 12. Update main README stats        │
  │ 13. Write formatted writeup → Notion│
  │ 14. Set Notion page icon            │
  │ 15. Tick Published checkbox         │
  └─────────────────────────────────────┘
        ↓
  Git commit + push to main
        ↓
  Sync workflow copies writeups/ → gitbook branch
        ↓
  GitBook picks up changes automatically
```

### Tech Stack

| Component | Purpose |
|-----------|---------|
| **Notion API** | Source of truth for notes and metadata |
| **GitHub Actions** | Scheduled CI/CD runner (6pm UTC daily) |
| **Python** | Core automation script |
| **Claude AI (Anthropic)** | Formats rough notes into professional writeups |
| **GitHub** | Version control and public portfolio |
| **GitBook** | Public-facing writeup site |

### Notion Database Schema

Each room entry in Notion requires:

| Property | Type | Description |
|----------|------|-------------|
| Note Title | Title | Room name |
| Platform | Select | TryHackMe, HackTheBox, LetsDefend, etc. |
| Difficulty | Select | Easy, Medium, Hard, Insane, Beginner |
| Type | Select | Machine, Sherlock, Challenge, Lab |
| OS | Select | Linux, Windows, Other |
| URL | URL | Link to the room |
| Icon URL | URL | Room icon image URL |
| Tags | Multi-select | e.g. #web, #sqli, #privesc |
| Completed | Checkbox | Mark when notes are ready |
| Published | Checkbox | Auto-ticked after publish |

### Folder Structure

```
CTF-Hub/
├── writeups/
│   ├── TryHackMe/
│   │   ├── README.md              ← platform overview + all writeups
│   │   ├── Easy/
│   │   │   ├── README.md          ← difficulty overview + OS links
│   │   │   ├── Linux/
│   │   │   │   ├── README.md      ← auto-updated table
│   │   │   │   └── RoomName/
│   │   │   │       ├── RoomName.md    ← formatted writeup
│   │   │   │       ├── RoomName.png   ← room icon
│   │   │   │       └── screenshot_01.png
│   │   │   ├── Windows/
│   │   │   └── Other/
│   │   ├── Medium/
│   │   └── Hard/
│   ├── HackTheBox/
│   │   ├── Machines/
│   │   ├── Sherlocks/
│   │   └── Challenges/
│   ├── LetsDefend/
│   └── Cheatsheets/
├── scripts/
│   ├── ctf_auto.py        ← main pipeline script
│   └── generate_readmes.py
└── .github/workflows/
    ├── ctf-publisher.yml      ← daily publish pipeline
    └── sync-to-gitbook.yml    ← syncs writeups/ to gitbook branch
```

### Branch Structure

| Branch | Purpose |
|--------|---------|
| `main` | Source of truth — scripts, workflows, all content |
| `gitbook` | Auto-synced from main — GitBook reads from here |

The `gitbook` branch only ever receives the `writeups/` folder. Scripts, workflows and root files stay on `main` only.

### Queue System

The pipeline publishes **one writeup per day** at 6pm UTC. If multiple writeups are queued in Notion, they drip out one per day automatically. Trigger manually via GitHub Actions to publish immediately.

### Cost

- GitHub Actions: free (public repo)
- Notion API: free
- Claude API: ~£0.01–0.02 per writeup
- Scheduled runs with nothing to process: £0

---

*Built by [Kieboard](https://github.com/Kieboard) · Live at [kieboard.gitbook.io/ctf-hub](https://kieboard.gitbook.io/ctf-hub)*
