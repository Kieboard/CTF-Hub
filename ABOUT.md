# ⚙️ About This Repo

## How It Works

Every writeup in this repo is authored in Notion and published automatically via a custom CI/CD pipeline. Here's what happens under the hood:

### The Pipeline

```
Notion (notes + metadata)
        ↓
  GitHub Actions (trigger: every 30 mins or manual)
        ↓
  Python script (ctf_auto.py)
        ↓
  ┌─────────────────────────────────────┐
  │ 1. Query Notion API                 │
  │    → Find Completed + Unpublished   │
  │ 2. Extract notes and metadata       │
  │ 3. Fetch room icon from platform    │
  │ 4. Scrape room description          │
  │ 5. Send to Claude AI for formatting │
  │ 6. Save markdown + icon to GitHub   │
  │ 7. Update difficulty README table   │
  │ 8. Update main README stats         │
  │ 9. Write formatted writeup → Notion │
  │ 10. Set Notion page icon            │
  │ 11. Tick Published checkbox         │
  └─────────────────────────────────────┘
        ↓
  Git commit + push → Live on GitHub
```

### Tech Stack

| Component | Purpose |
|-----------|---------|
| **Notion API** | Source of truth for notes and metadata |
| **GitHub Actions** | Scheduled CI/CD runner (every 30 mins) |
| **Python** | Core automation script |
| **Claude AI (Anthropic)** | Formats rough notes into professional writeups |
| **GitHub** | Version control and public portfolio |

### Notion Database Schema

Each room entry in Notion requires:

| Property | Type | Description |
|----------|------|-------------|
| Note Title | Title | Room name |
| Platform | Select | TryHackMe, HackTheBox, etc. |
| Difficulty | Select | Easy, Medium, Hard, Insane |
| URL | URL | Link to the room |
| Icon URL | URL | Room icon image URL |
| Tags | Multi-select | e.g. #web, #sqli, #privesc |
| Completed | Checkbox | Triggers the pipeline when ticked |
| Published | Checkbox | Auto-ticked after publish |

### Folder Structure

```
CTF-Hub/
├── writeups/
│   ├── TryHackMe/
│   │   ├── README.md
│   │   ├── Easy/
│   │   │   ├── README.md          ← auto-updated table
│   │   │   └── RoomName/
│   │   │       ├── RoomName.md    ← formatted writeup
│   │   │       ├── RoomName.png   ← room icon
│   │   │       └── screenshot_01.png
│   │   ├── Medium/
│   │   └── Hard/
│   └── HackTheBox/
│       └── ...
├── Cheatsheets/
├── Templates/
├── scripts/
│   ├── ctf_auto.py        ← main pipeline script
│   └── generate_readmes.py
└── .github/workflows/
    └── ctf-publisher.yml  ← GitHub Actions workflow
```

### Cost

- GitHub Actions: free (public repo)
- Notion API: free
- Claude API: ~£0.01–0.02 per writeup
- Scheduled runs with nothing to process: £0

---

*Built by [Kieboard](https://github.com/Kieboard)*
