# 🧠 CTF Hub

> Documenting my offensive security journey — one room at a time.

A structured knowledge base of CTF writeups, lab notes, and attack methodology built while working through the BSc Cyber Security degree.

All writeups are authored in Notion and auto-published here via a custom CI/CD pipeline built with GitHub Actions, the Notion API, and Claude AI.

---

## 📊 Progress

| Platform | Easy | Medium | Hard | Total |
|----------|------|--------|------|-------|
| 🔴 TryHackMe | 2 | — | — | 2 |
| **Total** | **2** | **0** | **0** | **2** |


## ⚙️ Workflow

Writeups are created in Notion using a structured template. Once marked complete, a GitHub Actions workflow fires automatically:

1. Reads notes and metadata from Notion API
2. Scrapes room description from the platform page
3. Fetches and saves the room icon
4. Sends everything to Claude for professional formatting
5. Saves the writeup and icon to the correct folder in this repo
6. Updates the difficulty README table with a new row
7. Writes the formatted version back to Notion
8. Sets the Notion page icon automatically
9. Ticks the Published checkbox

Zero manual steps after writing the notes.

---

## 🎯 Goals

- [ ] CompTIA Security+
- [ ] Complete TryHackMe Pre-Security and Jr Penetration Tester paths
- [ ] 50 published writeups

---

*Built by [Kieboard](https://github.com/Kieboard)*
