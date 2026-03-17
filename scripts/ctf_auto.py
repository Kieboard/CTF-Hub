"""
CTF Auto Publisher — Full Pipeline
Kieran Rorrison — CTF-Hub
"""

import os
import re
import sys
import time
import shutil
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from notion_client import Client
import anthropic


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
NOTION_TOKEN       = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
CTFHUB_REPO_PATH   = os.environ.get("CTFHUB_REPO_PATH", ".")
WRITEUPS_PATH      = Path(CTFHUB_REPO_PATH) / "writeups"

notion = Client(auth=NOTION_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────────
# MAPPINGS
# ─────────────────────────────────────────────
PLATFORM_FOLDERS = {
    "tryhackme":         "TryHackMe",
    "thm":               "TryHackMe",
    "hackthebox":        "HackTheBox",
    "htb":               "HackTheBox",
    "vulnhub":           "VulnHub",
    "pwnedlabs":         "PwnedLabs",
    "picoctf":           "PicoCTF",
    "rootme":            "RootMe",
    "root-me":           "RootMe",
    "offsec":            "OffSec",
    "offensivesecurity": "OffSec",
    "provinggrounds":    "ProvingGrounds",
    "proving grounds":   "ProvingGrounds",
    "pg play":           "ProvingGrounds",
    "pg practice":       "ProvingGrounds",
    "pwn.college":       "pwn.college",
    "pwncollege":        "pwn.college",
    "ctftime":           "CTFtime",
    "ctf":               "CTFtime",
    "sansholidayhack":   "SANSHolidayHack",
    "sans holiday hack": "SANSHolidayHack",
    "letsdefend":        "LetsDefend",
    "lets defend":       "LetsDefend",
    "holidayhack":       "SANSHolidayHack",
}

DIFFICULTY_FOLDERS = {
    "easy":      "Easy",
    "medium":    "Medium",
    "hard":      "Hard",
    "insane":    "Insane",
    "beginner":  "Beginner",
}

# Platforms that get Linux/Windows OS subfolder
OS_SPLIT_PLATFORMS = {"TryHackMe", "HackTheBox"}

# Type sections for platform READMEs
TYPE_SECTIONS = {
    "Machine":    {"emoji": "🖥️",  "header": "Machines"},
    "Sherlock":   {"emoji": "🔵",  "header": "Sherlocks"},
    "Challenge":  {"emoji": "🏴",  "header": "Challenges"},
    "Walkthrough":{"emoji": "📖",  "header": "Walkthroughs"},
    "CTF":        {"emoji": "🏁",  "header": "CTF Events"},
    "Dojo":       {"emoji": "🎓",  "header": "Dojos"},
    "Lab":        {"emoji": "🧪",  "header": "Labs"},
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

NOTION_CODE_LANGUAGES = {
    "abap","abc","agda","arduino","ascii art","assembly","bash","basic","bnf",
    "c","c#","c++","clojure","coffeescript","coq","css","dart","dhall","diff",
    "docker","ebnf","elixir","elm","erlang","f#","flow","fortran","gherkin",
    "glsl","go","graphql","groovy","haskell","hcl","html","idris","java",
    "javascript","json","julia","kotlin","latex","less","lisp","livescript",
    "llvm ir","lua","makefile","markdown","markup","matlab","mathematica",
    "mermaid","nix","notion formula","objective-c","ocaml","pascal","perl",
    "php","plain text","powershell","prolog","protobuf","purescript","python",
    "r","racket","reason","ruby","rust","sass","scala","scheme","scss","shell",
    "smalltalk","solidity","sql","swift","toml","typescript","vb.net","verilog",
    "vhdl","visual basic","webassembly","xml","yaml","java/c/c++/c#"
}

PLATFORM_INFO = {
    "TryHackMe":       {"emoji": "🔴", "desc": "TryHackMe rooms organised by difficulty."},
    "HackTheBox":      {"emoji": "🟢", "desc": "HackTheBox machine and challenge writeups."},
    "VulnHub":         {"emoji": "🟣", "desc": "VulnHub vulnerable machine writeups."},
    "PwnedLabs":       {"emoji": "🔵", "desc": "PwnedLabs cloud and AD challenge writeups."},
    "PicoCTF":         {"emoji": "🏴", "desc": "PicoCTF challenge writeups."},
    "RootMe":          {"emoji": "⚫", "desc": "Root-Me challenge writeups."},
    "OffSec":          {"emoji": "🟠", "desc": "OffSec Proving Grounds Play and Practice machines. OSCP-relevant content."},
    "ProvingGrounds":  {"emoji": "🟠", "desc": "OffSec Proving Grounds machines. Direct OSCP preparation and practice."},
    "LetsDefend":      {"emoji": "🛡️", "desc": "Blue team SOC challenges. Threat hunting, log analysis, and incident response.", "difficulties": ["Beginner", "Easy", "Medium", "Hard"]},
    "pwn.college":     {"emoji": "🎓", "desc": "pwn.college challenge writeups. Binary exploitation and system security."},
    "CTFtime":         {"emoji": "🏁", "desc": "General CTF competition writeups from various events on CTFtime."},
    "SANSHolidayHack": {"emoji": "🎄", "desc": "SANS Holiday Hack Challenge writeups. Annual CTF with real-world scenarios."},
}

DIFF_EMOJI = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴", "Insane": "💀"}
DIFF_DESC  = {
    "Easy":   "Beginner-friendly rooms. Focus on core methodology, enumeration fundamentals, and common vulnerabilities.",
    "Medium": "Intermediate rooms requiring chained exploits and deeper enumeration.",
    "Hard":   "Advanced rooms involving complex attack chains and deep technical knowledge.",
    "Insane": "Expert-level machines requiring advanced exploitation techniques.",
}

# ─────────────────────────────────────────────
# NOTION HELPERS
# ─────────────────────────────────────────────

def query_completed_unpublished():
    print("🔍 Querying Notion for completed unpublished writeups...")
    response = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        filter={
            "and": [
                {"property": "Completed", "checkbox": {"equals": True}},
                {"property": "Published", "checkbox": {"equals": False}},
            ]
        }
    )
    pages = response.get("results", [])
    print(f"   Found {len(pages)} page(s) to process")
    return pages


def get_page_properties(page: dict) -> dict:
    props = page.get("properties", {})
    meta = {
        "page_id":    page["id"],
        "room_name":  "",
        "platform":   "",
        "difficulty": "",
        "url":        "",
        "icon_url":   "",
        "tags":       [],
        "room_type":  "",
        "os":         "",      # NEW: Linux / Windows / Other
        "date":       datetime.now().strftime("%b %d, %Y"),
    }

    for title_key in ("Note Title", "Name", "Title", "Room", "Task"):
        title_prop = props.get(title_key, {})
        title_list = title_prop.get("title", [])
        if title_list:
            meta["room_name"] = title_list[0].get("plain_text", "Unknown")
            break

    platform_prop = props.get("Platform", {})
    ptype = platform_prop.get("type", "")
    if ptype == "select" and platform_prop.get("select"):
        meta["platform"] = platform_prop["select"]["name"]
    elif ptype == "multi_select":
        opts = platform_prop.get("multi_select", [])
        if opts:
            meta["platform"] = opts[0]["name"]

    diff_prop = props.get("Difficulty", {})
    if diff_prop.get("type") == "select" and diff_prop.get("select"):
        meta["difficulty"] = diff_prop["select"]["name"]

    url_prop = props.get("URL", {})
    if url_prop.get("type") == "url":
        meta["url"] = url_prop.get("url") or ""
    elif url_prop.get("type") == "rich_text":
        texts = url_prop.get("rich_text", [])
        if texts:
            meta["url"] = texts[0].get("plain_text", "")

    tags_prop = props.get("Tags", {})
    if tags_prop.get("type") == "multi_select":
        meta["tags"] = [t["name"] for t in tags_prop.get("multi_select", [])]

    # Category property
    for cat_key in ("Category", "Type"):
        cat_prop = props.get(cat_key, {})
        if cat_prop.get("type") == "select" and cat_prop.get("select"):
            meta["room_type"] = cat_prop["select"]["name"]
            break

    # OS property — NEW
    os_prop = props.get("OS", {})
    if os_prop.get("type") == "select" and os_prop.get("select"):
        meta["os"] = os_prop["select"]["name"]

    # Icon URL
    for icon_key in ("Icon URL", "Icon", "Files"):
        icon_prop = props.get(icon_key, {})
        itype = icon_prop.get("type", "")
        if itype == "url" and icon_prop.get("url"):
            meta["icon_url"] = icon_prop["url"]
            break
        elif itype == "files":
            files = icon_prop.get("files", [])
            if files:
                f = files[0]
                if f.get("type") == "external":
                    meta["icon_url"] = f["external"]["url"]
                elif f.get("type") == "file":
                    meta["icon_url"] = f["file"]["url"]
                break

    return meta


def extract_blocks_as_text(page_id: str):
    blocks_text = []
    image_urls  = []
    cursor      = None

    while True:
        if cursor:
            response = notion.blocks.children.list(block_id=page_id, page_size=100, start_cursor=cursor)
        else:
            response = notion.blocks.children.list(block_id=page_id, page_size=100)

        blocks = response.get("results", [])

        for block in blocks:
            btype = block.get("type", "")

            if btype == "paragraph":
                texts = block["paragraph"].get("rich_text", [])
                line  = "".join(t.get("plain_text", "") for t in texts)
                if line.strip():
                    blocks_text.append(line)

            elif btype in ("heading_1", "heading_2", "heading_3"):
                texts = block[btype].get("rich_text", [])
                level = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}[btype]
                line  = "".join(t.get("plain_text", "") for t in texts)
                if line.strip():
                    blocks_text.append(f"{level} {line}")

            elif btype == "bulleted_list_item":
                texts = block["bulleted_list_item"].get("rich_text", [])
                line  = "".join(t.get("plain_text", "") for t in texts)
                if line.strip():
                    blocks_text.append(f"- {line}")

            elif btype == "numbered_list_item":
                texts = block["numbered_list_item"].get("rich_text", [])
                line  = "".join(t.get("plain_text", "") for t in texts)
                if line.strip():
                    blocks_text.append(f"1. {line}")

            elif btype == "code":
                texts    = block["code"].get("rich_text", [])
                language = block["code"].get("language", "")
                code     = "".join(t.get("plain_text", "") for t in texts)
                blocks_text.append(f"```{language}\n{code}\n```")

            elif btype == "quote":
                texts = block["quote"].get("rich_text", [])
                line  = "".join(t.get("plain_text", "") for t in texts)
                if line.strip():
                    blocks_text.append(f"> {line}")

            elif btype == "image":
                img = block["image"]
                if img.get("type") == "file":
                    img_url = img["file"]["url"]
                elif img.get("type") == "external":
                    img_url = img["external"]["url"]
                else:
                    img_url = None
                if img_url:
                    image_urls.append(img_url)
                    idx = len(image_urls)
                    blocks_text.append(f"![Screenshot {idx}](screenshot_{idx:02d}.png)")

            elif btype == "divider":
                blocks_text.append("---")

        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")

    return "\n\n".join(blocks_text), image_urls


def fetch_room_description(url: str) -> str:
    if not url:
        return ""
    print(f"   → Fetching room info from: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""
        text  = resp.text
        clean = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>',  '', clean, flags=re.DOTALL)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:3000]
    except Exception as e:
        print(f"   ⚠️  Could not fetch room page: {e}")
        return ""


def fetch_room_icon(direct_url: str, page_url: str, dest_folder: Path, room_name: str) -> str:
    room_clean = re.sub(r'[^\w\-]', '', room_name.replace(" ", ""))
    filename   = f"{room_clean}.png"

    if direct_url:
        try:
            print(f"   → Downloading icon from Notion Files property...")
            resp = requests.get(direct_url, timeout=15)
            if resp.status_code == 200:
                icon_path = dest_folder / filename
                icon_path.write_bytes(resp.content)
                print(f"   ✅ Icon saved: {filename}")
                return filename
        except Exception as e:
            print(f"   ⚠️  Direct icon download failed: {e}")

    url = page_url
    if not url:
        return ""
    print(f"   → Fetching room icon from: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return ""

        og_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', resp.text)
        if not og_match:
            og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', resp.text)

        if not og_match:
            s3_match = re.search(r'https://tryhackme-images\.s3\.amazonaws\.com/room-icons/[^\s"\']+', resp.text)
            if s3_match:
                icon_url = s3_match.group(0)
            else:
                return ""
        else:
            icon_url = og_match.group(1)

        icon_resp = requests.get(icon_url, headers=headers, timeout=15)
        if icon_resp.status_code == 200:
            icon_path = dest_folder / filename
            icon_path.write_bytes(icon_resp.content)
            print(f"   ✅ Icon saved: {filename}")
            return filename
        return ""

    except Exception as e:
        print(f"   ⚠️  Could not fetch room icon: {e}")
        return ""


def set_notion_page_icon(page_id: str, icon_url: str):
    try:
        notion.pages.update(
            page_id=page_id,
            icon={"type": "external", "external": {"url": icon_url}}
        )
        print("   ✅ Notion page icon updated")
    except Exception as e:
        print(f"   ⚠️  Could not set Notion icon: {e}")


def download_screenshots(image_urls: list, dest_folder: Path) -> list:
    saved = []
    for i, url in enumerate(image_urls, start=1):
        filename = f"screenshot_{i:02d}.png"
        dest     = dest_folder / filename
        try:
            print(f"   → Downloading screenshot {i}/{len(image_urls)}...")
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                dest.write_bytes(resp.content)
                saved.append(filename)
                print(f"   ✅ {filename}")
        except Exception as e:
            print(f"   ⚠️  Could not download screenshot {i}: {e}")
    return saved


# ─────────────────────────────────────────────
# CLAUDE FORMATTING
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are a cybersecurity writeup formatter for a professional CTF/HTB portfolio.

You receive:
1. Raw rough notes from the hacker (Kieran)
2. Room description scraped from the CTF platform

Combine both to produce a clean, narrative-driven, professional writeup in the style of top HTB writeup authors.

WRITING STYLE:
- Write like you are talking someone through the box — narrative, not a checklist
- Keep Kieran's voice — direct, technical, no fluff
- Use past tense ("I ran", "This revealed", "I found")
- Explain WHY things worked, not just WHAT you ran
- Highlight key discoveries with bold labels e.g. **Key Finding:** or **Critical Discovery:**
- Short punchy sentences. No waffle.

CODE BLOCKS:
- Every single command must be in a fenced code block with the correct language tag (```bash, ```python, ```xml etc)
- Never put commands inline in prose — always block
- Add a brief line of context BEFORE each code block explaining what it does
- Add a brief **Result:** or **Output:** note AFTER key code blocks explaining what came back
- IMPORTANT: All bash/shell commands must include a terminal prompt prefix in this format:
  - TryHackMe rooms: kie@kiepc:~/THM/{RoomName}$
  - HackTheBox rooms: kie@kiepc:~/HTB/{RoomName}$
  - LetsDefend rooms: kie@kiepc:~/LetsDefend/{RoomName}$
  - Other platforms: kie@kiepc:~/{Platform}/{RoomName}$
  Example: kie@kiepc:~/THM/RootMe$ nmap -sV 10.10.110.118
  Do NOT add the prompt to code that is output/results — only to commands being run.

STRUCTURE RULES:
- Keep Kieran's voice — don't make it sound corporate or AI-generated
- Preserve ALL image references exactly as given (e.g. ![Screenshot 1](screenshot_01.png))
- Don't invent flags, IPs, or details not in the notes
- If a section has no content, omit it entirely
- The Attack Chain Summary should be a numbered list of concise one-liners covering the full path
- Detection Strategies should have two subsections: Offensive Indicators and Defensive Mitigations

OUTPUT: Pure markdown only. No preamble. No explanation. Start directly with the metadata block."""


def format_with_claude(raw_notes: str, room_info: str, meta: dict, saved_screenshots: list, icon_filename: str) -> str:
    url_line = (
        f'    <b>URL:</b> <a href="{meta["url"]}">{meta["room_name"]}</a><br>\n'
        if meta["url"] else ""
    )
    os_line = (
        f'    <b>OS:</b> {meta["os"]}<br>\n'
        if meta.get("os") else ""
    )
    all_tags = list(dict.fromkeys(
        [f"#{meta['platform'].lower().replace(' ', '')}",
         f"#{meta['difficulty'].lower()}"] +
        [f"#{t.lower().replace(' ', '-')}" for t in meta["tags"]]
    ))
    tags_str = " ".join(all_tags)

    metadata_block = f"""<p align="right">
  <sub>
    <b>Platform:</b> {meta["platform"]}<br>
    <b>Difficulty:</b> {meta["difficulty"]}<br>
{os_line}    <b>Status:</b> Completed ✅<br>
{url_line}    <b>Date:</b> {meta["date"]}<br>
    <b>Tags:</b> {tags_str}
  </sub>
</p>

---"""

    screenshots_note = ""
    if saved_screenshots:
        screenshots_note = f"\n\nScreenshots available: {', '.join(saved_screenshots)}"

    user_message = f"""Format a CTF writeup for: "{meta["room_name"]}"

Use this metadata block exactly at the top:
{metadata_block}

Then use this structure — keep sections in this order, omit any section with no content:
## 🧠 Overview
## 🎯 Objectives
## 🔍 Reconnaissance & Initial Analysis
## ⚙️ Exploitation
## 🔐 Privilege Escalation (omit if not applicable)
## 🏁 Flags / Proof
## 🧩 Key Takeaways
## ⛓️ Attack Chain Summary
(numbered list, one line per step, full attack path from recon to root)
## 🔎 Detection Strategies
### Offensive Indicators
### Defensive Mitigations
## 🛠️ Tools & References

---
ROOM DESCRIPTION (from platform):
{room_info if room_info else "Not available — use notes only"}

---
ROUGH NOTES FROM KIERAN:
{raw_notes}
{screenshots_note}
---

Return ONLY the formatted markdown. Nothing else."""

    print("   → Sending to Claude...")
    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    print("   ✅ Claude formatting complete")
    return message.content[0].text


def suggest_topic_tags(raw_notes: str, room_info: str, room_name: str) -> list:
    prompt = f"""You are tagging a CTF room for a portfolio. Based on the room name, description and notes below, suggest exactly 2-3 short topic tags that describe what the room is about technically.

Rules:
- Tags must be lowercase, no spaces (use hyphens), no # symbol
- Be specific and technical e.g. prompt-injection, sqli, privilege-escalation, buffer-overflow, file-upload, lfi, rce, active-directory, web, forensics, crypto, osint, reversing, steganography, dfir, malware
- Do NOT include platform names (tryhackme, htb) or difficulty (easy, medium, hard)
- Do NOT include type names (machine, sherlock, challenge, walkthrough, ctf, dojo)
- Return ONLY a comma separated list of tags, nothing else. Example: prompt-injection,ai-security,web

Room: {room_name}
Description: {room_info[:500] if room_info else "Not available"}
Notes summary: {raw_notes[:500]}"""

    try:
        message = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip().lower()
        tags = [t.strip().replace(" ", "-") for t in raw.split(",") if t.strip()]
        tags = [re.sub(r"[^a-z0-9\-]", "", t) for t in tags]
        tags = [t for t in tags if t][:3]
        print(f"   ✅ Topic tags: {tags}")
        return tags
    except Exception as e:
        print(f"   ⚠️  Could not generate topic tags: {e}")
        return []


# ─────────────────────────────────────────────
# AUTO-DETECT OS — NEW
# ─────────────────────────────────────────────

def auto_detect_os(platform: str, room_info: str, room_name: str, url: str) -> str:
    """Detect OS (Linux/Windows/Other) for platforms that use the OS split.
    Only called for TryHackMe and HackTheBox."""

    prompt = f"""You are detecting the operating system of a CTF machine for a portfolio tracker.

Based on the platform, room name, URL and description below, determine the OS.

Rules:
- Reply with ONLY one of: Linux, Windows, Other
- If the description mentions Windows, Active Directory, SMB, RDP, WinRM, PowerShell, .NET, IIS → Windows
- If the description mentions Linux, Ubuntu, Debian, Apache, SSH, bash, sudo, SUID → Linux
- If it's a challenge/forensics/crypto with no machine OS → Other
- If unsure, default to Linux

Platform: {platform}
Room: {room_name}
URL: {url}
Description: {room_info[:800] if room_info else "Not available"}

Reply with ONLY: Linux, Windows, or Other"""

    try:
        message = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        os_result = message.content[0].text.strip()
        valid = {"Linux", "Windows", "Other"}
        if os_result in valid:
            print(f"   ✅ Auto-detected OS: {os_result}")
            return os_result
        else:
            print(f"   ⚠️  Unexpected OS '{os_result}', defaulting to Linux")
            return "Linux"
    except Exception as e:
        print(f"   ⚠️  Could not auto-detect OS: {e}")
        return "Linux"


def write_os_to_notion(page_id: str, os_value: str):
    """Write the auto-detected OS back to the Notion OS property."""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "OS": {"select": {"name": os_value}}
            }
        )
        print(f"   ✅ Notion OS set to: {os_value}")
    except Exception as e:
        print(f"   ⚠️  Could not set Notion OS: {e}")


# ─────────────────────────────────────────────
# README MANAGEMENT
# ─────────────────────────────────────────────

def ensure_platform_readme(platform_dir: Path, platform: str):
    readme = platform_dir / "README.md"
    if readme.exists():
        return
    info    = PLATFORM_INFO.get(platform, {"emoji": "📁", "desc": f"{platform} writeups."})
    content = f"""# {info['emoji']} {platform}

{info['desc']}

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""
    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Created {platform}/README.md")


def ensure_difficulty_readme(diff_dir: Path, platform: str, difficulty: str):
    readme = diff_dir / "README.md"
    if readme.exists():
        return
    emoji   = DIFF_EMOJI.get(difficulty, "📁")
    desc    = DIFF_DESC.get(difficulty, f"{difficulty} difficulty writeups.")
    content = f"""# {emoji} {platform} — {difficulty}

{desc}

---

## 📋 Writeups

| Icon | Room | Tags | Date |
|------|------|------|------|
| *Auto-populated as writeups are added* | | | |

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""
    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Created {platform}/{difficulty}/README.md")


def ensure_os_readme(os_dir: Path, platform: str, difficulty: str, os_name: str):
    """Create README for OS-level subdirectory (Linux/Windows) if it doesn't exist."""
    readme = os_dir / "README.md"
    if readme.exists():
        return
    emoji = "🐧" if os_name == "Linux" else "🪟" if os_name == "Windows" else "💻"
    content = f"""# {emoji} {platform} — {difficulty} — {os_name}

{difficulty} difficulty {os_name} machines.

---

## 📋 Writeups

| Icon | Room | Tags | Date |
|------|------|------|------|
| *Auto-populated as writeups are added* | | | |

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""
    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Created {platform}/{difficulty}/{os_name}/README.md")


def update_platform_readme(platform_dir: Path, platform: str, meta: dict, icon_filename: str, topic_tags: list):
    readme = platform_dir / "README.md"
    info   = PLATFORM_INFO.get(platform, {"emoji": "📁", "desc": f"{platform} writeups."})

    content = readme.read_text(encoding="utf-8") if readme.exists() else ""

    # Preserve GitBook frontmatter if present
    frontmatter = ""
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx != -1:
            frontmatter = content[:end_idx + 3] + "\n"
            content = content[end_idx + 3:].lstrip("\n")

    room_type      = meta.get("room_type", "") or "Other"
    section        = TYPE_SECTIONS.get(room_type, {"emoji": "📁", "header": room_type or "Other"})
    section_header = f"## {section['emoji']} {section['header']}"
    table_header   = "| Icon | Room | Difficulty | Tags | Date |\n|------|------|------------|------|------|"

    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    diff_dir   = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])

    # Build path with OS subfolder if applicable
    os_name = meta.get("os", "")
    if platform in OS_SPLIT_PLATFORMS and os_name and os_name != "Other":
        room_link  = f"[{meta['room_name']}]({diff_dir}/{os_name}/{room_clean}/{room_clean}.md)"
        icon_rel   = f"{diff_dir}/{os_name}/{room_clean}/{icon_filename}" if icon_filename else ""
    else:
        room_link  = f"[{meta['room_name']}]({diff_dir}/{room_clean}/{room_clean}.md)"
        icon_rel   = f"{diff_dir}/{room_clean}/{icon_filename}" if icon_filename else ""

    icon_cell = f'<img src="{icon_rel}" width="32" alt="{meta["room_name"]}">' if icon_rel else ""

    redundant = {"thm", "htb", "tryhackme", "hackthebox", "easy", "medium", "hard", "insane"}
    type_tag  = [f"`#{room_type.lower()}`"] if room_type else []
    ai_tags   = [f"`#{t}`" for t in topic_tags]
    user_tags = [f"`#{t.lower().replace(' ', '-')}`" for t in meta["tags"]
                 if t.lower().replace(" ", "") not in redundant]
    all_tags  = list(dict.fromkeys(type_tag + ai_tags + user_tags))[:5]
    tags_cell = " ".join(all_tags)

    diff_badge = f"`{meta['difficulty']}`"
    new_row    = f"| {icon_cell} | {room_link} | {diff_badge} | {tags_cell} | {meta['date']} |"

    # Remove old row if it exists
    search_path = f"{diff_dir}/"
    if search_path in content and room_clean in content:
        lines   = content.split("\n")
        content = "\n".join(l for l in lines if not (search_path in l and room_clean in l))

    if section_header in content:
        lines        = content.split("\n")
        section_idx  = next(i for i, l in enumerate(lines) if l.strip() == section_header)
        last_row_idx = section_idx
        for i in range(section_idx + 1, len(lines)):
            if lines[i].startswith("| ") and "---" not in lines[i]:
                last_row_idx = i
            elif lines[i].startswith("## ") and i > section_idx + 1:
                break
        lines.insert(last_row_idx + 1, new_row)
        content = "\n".join(lines)
    else:
        new_section = f"\n{section_header}\n\n{table_header}\n{new_row}\n"
        footer_variants = [
            "> Writeups drafted in Notion and auto-published via a custom Python pipeline using the Claude API.",
            "> Writeups authored in Notion, auto-published via CTF Publisher.",
        ]
        footer_found = None
        for fv in footer_variants:
            if fv in content:
                footer_found = fv
                break
        if footer_found:
            content = content.replace(
                footer_found,
                new_section + b"\n---\n\n" + footer_found
            )
        else:
            content = content.rstrip() + new_section

    # Update stats line — count rows in All Writeups table
    lines = content.split("\n")
    writeup_rows = [l for l in lines if l.startswith("| [") and "Auto-populated" not in l]
    total = len(writeup_rows)
    today = meta["date"]
    new_stats = f"> **{total} room{'s' if total != 1 else ''} completed · {total} flag{'s' if total != 1 else ''} captured · Last updated {today}**"
    import re as _re
    if _re.search(r'> \*\*\d+ rooms? completed', content):
        content = _re.sub(r'> \*\*\d+ rooms? completed.*?\*\*', new_stats.strip(">").strip(), content)
        content = _re.sub(r'> \*\*', '> **', content)
    elif "**" in content and "completed" not in content:
        pass  # no stats line yet, skip

    if frontmatter:
        content = frontmatter + "\n" + content.lstrip("\n")
    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Updated {platform}/README.md — added to {section['header']} section")


def update_difficulty_readme(diff_dir: Path, platform: str, difficulty: str, meta: dict, icon_filename: str, topic_tags: list = None):
    readme = diff_dir / "README.md"
    if not readme.exists():
        ensure_difficulty_readme(diff_dir, platform, difficulty)

    content    = readme.read_text(encoding="utf-8")
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    os_name    = meta.get("os", "")
    platform_f = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])

    # Build path with OS subfolder if applicable
    if platform_f in OS_SPLIT_PLATFORMS and os_name and os_name != "Other":
        room_path = f"{os_name}/{room_clean}/{room_clean}.md"
        icon_path = f"{os_name}/{room_clean}/{icon_filename}" if icon_filename else ""
    else:
        room_path = f"{room_clean}/{room_clean}.md"
        icon_path = f"{room_clean}/{icon_filename}" if icon_filename else ""

    # Remove old row if present
    if room_clean in content:
        lines   = content.split("\n")
        content = "\n".join(l for l in lines if room_clean not in l or not l.startswith("|"))

    icon_cell = f'<img src="{icon_path}" width="32" alt="{meta["room_name"]}">' if icon_path else ""

    redundant  = {"thm", "htb", "tryhackme", "hackthebox", "easy", "medium", "hard", "insane"}
    room_type  = meta.get("room_type", "")
    type_tag   = [f"`#{room_type.lower()}`"] if room_type else []
    auto_tags  = [
        f"`#{meta['platform'].lower().replace(' ', '')}`",
        f"`#{meta['difficulty'].lower()}`"
    ]
    ai_tags    = [f"`#{t}`" for t in (topic_tags or [])]
    user_tags  = [f"`#{t.lower().replace(' ', '-')}`" for t in meta["tags"]
                  if t.lower().replace(" ", "") not in redundant]
    all_tags   = list(dict.fromkeys(auto_tags + type_tag + ai_tags + user_tags))[:6]
    tags_cell  = " ".join(all_tags)

    room_link = f"[{meta['room_name']}]({room_path})"
    new_row   = f"| {icon_cell} | {room_link} | {tags_cell} | {meta['date']} |"

    for placeholder in [
        "| *Auto-populated as writeups are added* | | | |",
        "| *Auto-populated as writeups are added* | | |",
    ]:
        if placeholder in content:
            content = content.replace(placeholder, new_row)
            break
    else:
        lines        = content.split("\n")
        last_row_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("| ") and "---" not in line:
                last_row_idx = i
        if last_row_idx >= 0:
            lines.insert(last_row_idx + 1, new_row)
            content = "\n".join(lines)
        else:
            content += f"\n{new_row}\n"

    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Added {meta['room_name']} to {platform}/{difficulty}/README.md")


def update_os_readme(os_dir: Path, platform: str, difficulty: str, os_name: str, meta: dict, icon_filename: str, topic_tags: list = None):
    """Update the OS-level README table (only for HTB/THM)."""
    readme = os_dir / "README.md"
    if not readme.exists():
        ensure_os_readme(os_dir, platform, difficulty, os_name)

    content    = readme.read_text(encoding="utf-8")
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    icon_path  = f"{room_clean}/{icon_filename}" if icon_filename else ""

    if room_clean in content:
        lines   = content.split("\n")
        content = "\n".join(l for l in lines if room_clean not in l or not l.startswith("|"))

    icon_cell = f'<img src="{icon_path}" width="32" alt="{meta["room_name"]}">' if icon_path else ""

    redundant  = {"thm", "htb", "tryhackme", "hackthebox", "easy", "medium", "hard", "insane"}
    room_type  = meta.get("room_type", "")
    type_tag   = [f"`#{room_type.lower()}`"] if room_type else []
    ai_tags    = [f"`#{t}`" for t in (topic_tags or [])]
    user_tags  = [f"`#{t.lower().replace(' ', '-')}`" for t in meta["tags"]
                  if t.lower().replace(" ", "") not in redundant]
    all_tags   = list(dict.fromkeys(type_tag + ai_tags + user_tags))[:6]
    tags_cell  = " ".join(all_tags)

    room_link = f"[{meta['room_name']}]({room_clean}/{room_clean}.md)"
    new_row   = f"| {icon_cell} | {room_link} | {tags_cell} | {meta['date']} |"

    for placeholder in [
        "| *Auto-populated as writeups are added* | | | |",
        "| *Auto-populated as writeups are added* | | |",
    ]:
        if placeholder in content:
            content = content.replace(placeholder, new_row)
            break
    else:
        lines        = content.split("\n")
        last_row_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("| ") and "---" not in line:
                last_row_idx = i
        if last_row_idx >= 0:
            lines.insert(last_row_idx + 1, new_row)
            content = "\n".join(lines)
        else:
            content += f"\n{new_row}\n"

    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Added {meta['room_name']} to {platform}/{difficulty}/{os_name}/README.md")


# ─────────────────────────────────────────────
# NOTION WRITE-BACK
# ─────────────────────────────────────────────

def markdown_to_notion_blocks(markdown: str) -> list:
    blocks = []
    lines  = markdown.split("\n")
    i      = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            lang       = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block", "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language":  lang if lang in NOTION_CODE_LANGUAGES else "plain text"
                }
            })
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif re.match(r'^\d+\. ', line):
            content = re.sub(r'^\d+\. ', '', line)
            blocks.append({"object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}})
        elif line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.startswith("> "):
            blocks.append({"object": "block", "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("!["):
            match = re.match(r'!\[([^\]]*)\]\(([^\)]+)\)', line)
            if match:
                blocks.append({"object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text",
                        "text": {"content": f"📸 {match.group(1)} ({match.group(2)})"},
                        "annotations": {"italic": True, "color": "gray"}}]}})
        elif line.strip().startswith("<p align") or line.strip().startswith("<sub>"):
            blocks.append({"object": "block", "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": "Writeup auto-generated by CTF Publisher ✅"}}],
                    "icon":      {"type": "emoji", "emoji": "🤖"},
                    "color":     "gray_background"
                }})
            while i < len(lines) and lines[i].strip() != "---":
                i += 1
        elif line.strip():
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[:2000]}}]}})

        i += 1

    return blocks


def clear_page_content(page_id: str):
    print("   → Clearing Notion page content...")
    for attempt in range(5):
        all_blocks = []
        cursor = None
        while True:
            if cursor:
                response = notion.blocks.children.list(block_id=page_id, page_size=100, start_cursor=cursor)
            else:
                response = notion.blocks.children.list(block_id=page_id, page_size=100)
            blocks = response.get("results", [])
            all_blocks.extend(blocks)
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        if not all_blocks:
            print(f"   ✅ Page cleared ({attempt} pass(es))")
            return

        for block in all_blocks:
            try:
                notion.blocks.delete(block_id=block["id"])
                time.sleep(0.15)
            except Exception:
                pass

        time.sleep(2)

    print("   ⚠️  Could not fully clear page after 5 attempts — proceeding anyway")


def write_back_to_notion(page_id: str, formatted_content: str, original_notes: str):
    print("   → Clearing old Notion content...")
    clear_page_content(page_id)
    time.sleep(3)

    print("   → Writing formatted writeup to Notion...")
    formatted_blocks = markdown_to_notion_blocks(formatted_content)

    separator_blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": "📝 Original Notes — Your raw notes as written"}}],
                "icon":      {"type": "emoji", "emoji": "📝"},
                "color":     "yellow_background"
            }
        },
        {"object": "block", "type": "divider", "divider": {}},
    ]

    original_blocks = []
    for line in original_notes.split("\n"):
        if not line.strip():
            continue
        original_blocks.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[:2000]}}]}
        })

    all_blocks = formatted_blocks + separator_blocks + original_blocks
    for i in range(0, len(all_blocks), 100):
        chunk = all_blocks[i:i + 100]
        notion.blocks.children.append(block_id=page_id, children=chunk)
        time.sleep(0.5)

    print("   ✅ Notion page updated (formatted writeup + original notes preserved)")


def mark_as_published(page_id: str):
    notion.pages.update(
        page_id=page_id,
        properties={"Published": {"checkbox": True}}
    )
    print("   ✅ Marked as Published in Notion")


# ─────────────────────────────────────────────
# GITHUB
# ─────────────────────────────────────────────

def get_destination_folder(meta: dict) -> Path:
    platform   = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])
    difficulty = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    os_name    = meta.get("os", "")

    platform_dir = WRITEUPS_PATH / platform
    diff_dir     = platform_dir / difficulty

    platform_dir.mkdir(parents=True, exist_ok=True)
    ensure_platform_readme(platform_dir, platform)
    diff_dir.mkdir(parents=True, exist_ok=True)
    ensure_difficulty_readme(diff_dir, platform, difficulty)

    # Insert OS subfolder for HTB and THM only
    if platform in OS_SPLIT_PLATFORMS and os_name and os_name != "Other":
        os_dir = diff_dir / os_name
        os_dir.mkdir(parents=True, exist_ok=True)
        ensure_os_readme(os_dir, platform, difficulty, os_name)
        return os_dir / room_clean
    else:
        return diff_dir / room_clean


def update_gitbook_summary(meta: dict):
    """Checkout gitbook branch, add the room to SUMMARY.md, commit and push, return to main."""
    platform   = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])
    difficulty = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    os_name    = meta.get("os", "")

    # Build the writeup path and SUMMARY indent level
    if platform in OS_SPLIT_PLATFORMS and os_name and os_name != "Other":
        writeup_path = f"writeups/{platform}/{difficulty}/{os_name}/{room_clean}/{room_clean}.md"
        # Find the OS line and indent one level deeper
        parent_line  = f"    * [{os_name}](writeups/{platform}/{difficulty}/{os_name}/README.md)"
        new_entry    = f"      * [{meta['room_name']}]({writeup_path})"
    elif platform in OS_SPLIT_PLATFORMS and os_name == "Other":
        writeup_path = f"writeups/{platform}/{difficulty}/Other/{room_clean}/{room_clean}.md"
        parent_line  = f"    * [Other](writeups/{platform}/{difficulty}/Other/README.md)"
        new_entry    = f"      * [{meta['room_name']}]({writeup_path})"
    else:
        writeup_path = f"writeups/{platform}/{difficulty}/{room_clean}/{room_clean}.md"
        parent_line  = f"  * [{difficulty}](writeups/{platform}/{difficulty}/README.md)"
        new_entry    = f"    * [{meta['room_name']}]({writeup_path})"

    print("   → Updating SUMMARY.md on gitbook branch...")
    try:
        # Stash any uncommitted changes on main first
        subprocess.run(["git", "stash"], cwd=CTFHUB_REPO_PATH, capture_output=True)

        # Switch to gitbook branch
        subprocess.run(
            ["git", "checkout", "gitbook"],
            cwd=CTFHUB_REPO_PATH, check=True, capture_output=True
        )

        summary_path = Path(CTFHUB_REPO_PATH) / "SUMMARY.md"
        if not summary_path.exists():
            print("   ⚠️  SUMMARY.md not found on gitbook branch — skipping")
            subprocess.run(["git", "checkout", "main"], cwd=CTFHUB_REPO_PATH, capture_output=True)
            subprocess.run(["git", "stash", "pop"], cwd=CTFHUB_REPO_PATH, capture_output=True)
            return

        content = summary_path.read_text(encoding="utf-8")

        # Don't add if already there
        if writeup_path in content:
            print(f"   ℹ️  {meta['room_name']} already in SUMMARY.md")
            subprocess.run(["git", "checkout", "main"], cwd=CTFHUB_REPO_PATH, capture_output=True)
            subprocess.run(["git", "stash", "pop"], cwd=CTFHUB_REPO_PATH, capture_output=True)
            return

        # Insert the new room entry after the parent line
        if parent_line in content:
            lines     = content.split("\n")
            insert_at = -1
            for i, line in enumerate(lines):
                if line.rstrip() == parent_line:
                    # Find the last child entry under this parent before next same-or-higher indent
                    indent = len(new_entry) - len(new_entry.lstrip())
                    for j in range(i + 1, len(lines)):
                        stripped = lines[j]
                        if not stripped.strip():
                            continue
                        line_indent = len(stripped) - len(stripped.lstrip())
                        if line_indent >= indent:
                            insert_at = j
                        else:
                            break
                    if insert_at == -1:
                        insert_at = i  # insert right after parent if no children yet
                    break

            if insert_at >= 0:
                lines.insert(insert_at + 1, new_entry)
                content = "\n".join(lines)
                summary_path.write_text(content, encoding="utf-8")
                print(f"   ✅ Added {meta['room_name']} to SUMMARY.md")
            else:
                print(f"   ⚠️  Could not find insert position for {meta['room_name']}")
        else:
            print(f"   ⚠️  Parent line not found in SUMMARY.md: {parent_line}")

        # Commit and push to gitbook
        subprocess.run(["git", "add", "SUMMARY.md"], cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"summary: Add {platform} - {meta['room_name']}"],
            cwd=CTFHUB_REPO_PATH, capture_output=True, text=True
        )
        if "nothing to commit" not in result.stdout:
            subprocess.run(["git", "push", "origin", "gitbook"], cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
            print("   ✅ SUMMARY.md pushed to gitbook branch")

    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  SUMMARY update error: {e.stderr}")
    finally:
        # Always return to main and restore stash
        subprocess.run(["git", "checkout", "main"], cwd=CTFHUB_REPO_PATH, capture_output=True)
        subprocess.run(["git", "stash", "pop"], cwd=CTFHUB_REPO_PATH, capture_output=True)


def git_commit_push(room_name: str, platform: str):
    print("   → Committing to GitHub...")
    try:
        subprocess.run(["git", "add", "."], cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
        commit_msg = f"writeup: Add {platform} - {room_name}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=CTFHUB_REPO_PATH, capture_output=True, text=True
        )
        if "nothing to commit" in result.stdout:
            print("   ℹ️  Nothing new to commit")
            return
        subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            cwd=CTFHUB_REPO_PATH, check=True, capture_output=True
        )
        subprocess.run(["git", "push"], cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
        print(f"   ✅ Pushed: {commit_msg}")
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Git error: {e.stderr}")


# ─────────────────────────────────────────────
# README STATS AUTO-UPDATE
# ─────────────────────────────────────────────

def update_main_readme_stats():
    readme_path = Path(CTFHUB_REPO_PATH) / "README.md"
    if not readme_path.exists():
        print("   ⚠️  Main README not found, skipping stats update")
        return

    platforms  = {
        "TryHackMe": "🔴", "HackTheBox": "🟢", "VulnHub": "🟣",
        "PwnedLabs": "🔵", "OffSec": "🟠", "ProvingGrounds": "🟠", "LetsDefend": "🛡️",
        "pwn.college": "🎓", "PicoCTF": "🏴", "RootMe": "⚫",
        "CTFtime": "🏁", "SANSHolidayHack": "🎄",
    }
    difficulties = ["Easy", "Medium", "Hard", "Insane"]

    stats = {}
    total_easy = total_medium = total_hard = total_insane = 0

    for platform, emoji in platforms.items():
        platform_dir = WRITEUPS_PATH / platform
        if not platform_dir.exists():
            continue
        counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Insane": 0}
        for difficulty in difficulties:
            diff_dir = platform_dir / difficulty
            if not diff_dir.exists():
                continue
            # Check both OS-split and flat structures
            if platform in OS_SPLIT_PLATFORMS:
                for os_dir in diff_dir.iterdir():
                    if os_dir.is_dir() and os_dir.name in {"Linux", "Windows", "Other"}:
                        for room_dir in os_dir.iterdir():
                            if room_dir.is_dir() and list(room_dir.glob("*.md")):
                                counts[difficulty] += 1
                    elif os_dir.is_dir() and list(os_dir.glob("*.md")):
                        # Legacy flat rooms still in diff_dir directly
                        counts[difficulty] += 1
            else:
                for room_dir in diff_dir.iterdir():
                    if room_dir.is_dir() and list(room_dir.glob("*.md")):
                        counts[difficulty] += 1

        total = sum(counts.values())
        if total > 0:
            stats[platform] = {"emoji": emoji, "counts": counts, "total": total}
            total_easy   += counts["Easy"]
            total_medium += counts["Medium"]
            total_hard   += counts["Hard"]
            total_insane += counts["Insane"]

    grand_total = total_easy + total_medium + total_hard + total_insane

    rows = []
    for platform, data in stats.items():
        c = data["counts"]
        rows.append(f"| {data['emoji']} {platform} | {c['Easy'] or '—'} | {c['Medium'] or '—'} | {c['Hard'] or '—'} | {data['total']} |")
    rows.append(f"| **Total** | **{total_easy}** | **{total_medium}** | **{total_hard}** | **{grand_total}** |")

    new_table = "| Platform | Easy | Medium | Hard | Total |\n|----------|------|--------|------|-------|\n" + "\n".join(rows)

    content = readme_path.read_text(encoding="utf-8")
    pattern = r"(\| Platform \| Easy \| Medium \| Hard \| Total \|.*?)(\n---|$)"
    match   = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_table + "\n" + content[match.end():]
        readme_path.write_text(content, encoding="utf-8")
        print(f"   ✅ Stats updated: {grand_total} total writeup(s)")
    else:
        print("   ⚠️  Could not find stats table in README to update")


# ─────────────────────────────────────────────
# AUTO-CATEGORISE
# ─────────────────────────────────────────────

def auto_categorise(platform: str, room_info: str, room_name: str) -> str:
    platform_defaults = {
        "VulnHub":         "Machine",
        "ProvingGrounds":  "Machine",
    "LetsDefend":      "Challenge",
        "OffSec":          "Machine",
        "pwn.college":     "Dojo",
        "PicoCTF":         "Challenge",
        "RootMe":          "Challenge",
        "CTFtime":         "CTF",
        "SANSHolidayHack": "CTF",
        "PwnedLabs":       "Lab",
    }
    if platform in platform_defaults:
        return platform_defaults[platform]

    prompt = f"""You are categorising a CTF room for a portfolio tracker.

Based on the platform, room name and description below, pick exactly ONE category from this list:
- Machine (a full virtual machine to root/own — typical HTB/THM box)
- Sherlock (a blue team/DFIR investigation challenge — HTB Sherlocks)
- Challenge (a single standalone challenge — web, crypto, pwn, forensics, misc etc)
- Walkthrough (a guided learning room with tasks and theory — typical THM walkthrough)
- CTF (a competition-style event with multiple challenges)
- Lab (a cloud or AD lab environment)
- Dojo (a structured learning dojo — pwn.college style)

Platform: {platform}
Room: {room_name}
Description: {room_info[:800] if room_info else "Not available"}

Reply with ONLY the single category word from the list above. Nothing else."""

    try:
        message = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        category = message.content[0].text.strip()
        valid = {"Machine", "Sherlock", "Challenge", "Walkthrough", "CTF", "Lab", "Dojo"}
        if category in valid:
            print(f"   ✅ Auto-category: {category}")
            return category
        else:
            print(f"   ⚠️  Unexpected category '{category}', defaulting to Challenge")
            return "Challenge"
    except Exception as e:
        print(f"   ⚠️  Could not auto-categorise: {e}")
        return "Challenge"


def write_category_to_notion(page_id: str, category: str):
    try:
        notion.pages.update(
            page_id=page_id,
            properties={"Category": {"select": {"name": category}}}
        )
        print(f"   ✅ Notion Category set to: {category}")
    except Exception as e:
        print(f"   ⚠️  Could not set Notion Category: {e}")


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def process_page(page: dict):
    meta = get_page_properties(page)
    print(f"\n{'='*50}")
    print(f"📝 Processing: {meta['room_name']}")
    print(f"   Platform: {meta['platform']} | Difficulty: {meta['difficulty']} | Type: {meta['room_type'] or 'Not set'} | OS: {meta['os'] or 'Not set'}")

    # 1. Read rough notes
    print("   → Reading notes from Notion...")
    raw_notes, image_urls = extract_blocks_as_text(meta["page_id"])
    print(f"   ✅ Got {len(raw_notes)} chars of notes, {len(image_urls)} image(s)")

    # 2. Fetch room description early — needed for OS and category detection
    room_info = fetch_room_description(meta["url"])

    # 3. Auto-categorise if not already set
    platform = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])
    if not meta.get("room_type"):
        meta["room_type"] = auto_categorise(platform, room_info, meta["room_name"])
        write_category_to_notion(meta["page_id"], meta["room_type"])
    else:
        print(f"   ℹ️  Category already set: {meta['room_type']}")

    # 4. Auto-detect OS for HTB and THM — NEW
    if platform in OS_SPLIT_PLATFORMS:
        if not meta.get("os"):
            meta["os"] = auto_detect_os(platform, room_info, meta["room_name"], meta["url"])
            write_os_to_notion(meta["page_id"], meta["os"])
        else:
            print(f"   ℹ️  OS already set: {meta['os']}")
    else:
        meta["os"] = ""  # Not applicable for other platforms

    # 5. Create destination folder (now OS-aware)
    dest_folder = get_destination_folder(meta)
    dest_folder.mkdir(parents=True, exist_ok=True)

    difficulty   = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])
    diff_dir     = WRITEUPS_PATH / platform / difficulty
    platform_dir = WRITEUPS_PATH / platform

    # OS dir reference for README updates
    os_name = meta.get("os", "")
    if platform in OS_SPLIT_PLATFORMS and os_name and os_name != "Other":
        os_dir = diff_dir / os_name
    else:
        os_dir = None

    # 6. Fetch room icon
    icon_filename = fetch_room_icon(meta.get("icon_url", ""), meta["url"], dest_folder, meta["room_name"])

    # 7. Download screenshots
    saved_screenshots = []
    if image_urls:
        print(f"   → Downloading {len(image_urls)} screenshot(s)...")
        saved_screenshots = download_screenshots(image_urls, dest_folder)

    # 8. Generate topic tags
    topic_tags = suggest_topic_tags(raw_notes, room_info, meta["room_name"])

    # 9. Format with Claude
    formatted = format_with_claude(raw_notes, room_info, meta, saved_screenshots, icon_filename)

    # 10. Save markdown to GitHub
    room_clean  = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    output_file = dest_folder / f"{room_clean}.md"
    gif_footer = "\n\n---\n\n![](https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExaDdhdmt6N2dhazFqbTdsdmk0ZThkdTBrYjBoOGdobWF2NzRmbXBjeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8kDPdrfdBUP8k/giphy.gif)\n"
    output_file.write_text(formatted + gif_footer, encoding="utf-8")
    print(f"   ✅ Writeup saved: {output_file}")

    # 11. Update difficulty README table
    update_difficulty_readme(diff_dir, platform, difficulty, meta, icon_filename, topic_tags)

    # 12. Update OS README table (HTB/THM only)
    if os_dir:
        update_os_readme(os_dir, platform, difficulty, os_name, meta, icon_filename, topic_tags)

    # 13. Update platform README with type section
    update_platform_readme(platform_dir, platform, meta, icon_filename, topic_tags)

    # 14. Write formatted content back to Notion
    try:
        write_back_to_notion(meta["page_id"], formatted, raw_notes)
    except Exception as e:
        print(f"   ⚠️  Notion write-back failed: {e}")

    # 15. Set Notion page icon
    if icon_filename and meta.get("icon_url"):
        set_notion_page_icon(meta["page_id"], meta["icon_url"])

    # 16. Update main README stats then commit + push
    update_main_readme_stats()
    git_commit_push(meta["room_name"], meta["platform"])

    # 17. Update SUMMARY.md on gitbook branch
    update_gitbook_summary(meta)

    # 18. Mark as published
    try:
        mark_as_published(meta["page_id"])
    except Exception as e:
        print(f"   ⚠️  Could not mark as Published: {e}")

    print(f"🎉 Done: {meta['room_name']}\n")


LAST_PUBLISHED_FILE = Path(CTFHUB_REPO_PATH) / "scripts" / ".last_published"


def already_published_today() -> bool:
    if not LAST_PUBLISHED_FILE.exists():
        return False
    last = LAST_PUBLISHED_FILE.read_text(encoding="utf-8").strip()
    return last == datetime.now().strftime("%Y-%m-%d")


def mark_published_today():
    LAST_PUBLISHED_FILE.write_text(datetime.now().strftime("%Y-%m-%d"), encoding="utf-8")


def main():
    print("\n🚀 CTF Auto Publisher starting...")
    pages = query_completed_unpublished()

    if not pages:
        print("✅ Nothing to process — all caught up!")
        return

    if already_published_today():
        print(f"📅 Already published a writeup today — {len(pages)} writeup(s) queued for tomorrow onwards")
        return

    if len(pages) > 1:
        print(f"   📬 {len(pages)} writeups queued — publishing 1 today, rest will drip out one per day")

    page = pages[0]
    try:
        process_page(page)
        mark_published_today()
    except Exception as e:
        print(f"❌ Error processing page: {e}")
        import traceback
        traceback.print_exc()

    if len(pages) > 1:
        print(f"\n📅 {len(pages) - 1} writeup(s) remaining — next one publishes tomorrow")

    print("\n✅ All done!")


if __name__ == "__main__":
    main()
