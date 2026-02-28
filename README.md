# 🧠 CTF Hub

> Documenting my offensive security journey — one room at a time.

A structured knowledge base of CTF writeups, lab notes, and attack methodology built while working through the BSc Cyber Security degree.

All writeups are authored in Notion and auto-published here via a custom CI/CD pipeline built with GitHub Actions, the Notion API, and Claude AI.

---

## 📊 Progress

| Platform | Easy | Medium | Hard | Total |
|----------|------|--------|------|-------|
| 🔴 TryHackMe | 2 | — | — | 2 |
| 🟢 HackTheBox | — | 1 | — | 1 |
| **Total** | **2** | **1** | **0** | **3** |

---

## 📂 Platforms

### 🔴 [TryHackMe](./writeups/TryHackMe/)
Hands-on labs focused on fundamentals, methodology, and attack flow. Organised by difficulty for consistent progression.

### 🟢 [HackTheBox](./writeups/HackTheBox/)
Machine and challenge writeups covering real-world attack scenarios and advanced exploitation.

### 🟣 [VulnHub](./writeups/VulnHub/)
Offline vulnerable machine writeups for lab-based practice and methodology building.

### 🔵 [PwnedLabs](./writeups/PwnedLabs/)
Cloud and Active Directory focused challenges. Relevant to enterprise environments and red team operations.

### 🟠 [OffSec / Proving Grounds](./writeups/ProvingGrounds/)
OSCP-relevant machine writeups. Direct preparation for the PWK course and exam.

### 🎓 [pwn.college](./writeups/pwn.college/)
Binary exploitation and system security challenges. Lower-level skills development.

### 🏁 [CTFtime](./writeups/CTFtime/)
Writeups from open CTF competitions.

---

## 🧰 Supporting Material

- [`Templates/`](./writeups/Templates/) — Reusable writeup templates
- [`Cheatsheets/`](./Cheatsheets/) — Enumeration, privesc, and tool reference sheets *(in progress)*

---

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
