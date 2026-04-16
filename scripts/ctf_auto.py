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
# CENTRALISED TAG BUILDER
# ─────────────────────────────────────────────

def build_tags_cell(meta: dict, topic_tags: list) -> str:
    """Build a consistent 4-tag cell string used across ALL README tables.

    Fixed order: #type #topic1 #topic2 #topic3

    Platform and difficulty are omitted — they are redundant given the page
    hierarchy (platform README, difficulty README etc). The type tag provides
    the bridge between context and content.

    Examples:
      #machine #file-upload #suid #privilege-escalation
      #challenge #phishing #email-analysis #osint
    """
    room_type = meta.get("room_type", "")
    type_tag  = [f"`#{room_type.lower()}`"] if room_type else []

    # Always exactly 3 topic tags from suggest_topic_tags
    topics = [f"`#{t}`" for t in (topic_tags or [])[:3]]
    while len(topics) < 3:
        topics.append("`#misc`")

    combined = list(dict.fromkeys(type_tag + topics))
    return " ".join(combined[:4])


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

# ─────────────────────────────────────────────
# WRITEUP SYSTEM PROMPTS — TYPE AWARE
# ─────────────────────────────────────────────

SYSTEM_PROMPT_REDTEAM = """You are a cybersecurity writeup formatter for a professional offensive security portfolio.

You receive raw notes and a room description. Produce a clean, narrative-driven, professional red team writeup.

WRITING STYLE:
- Write like you are talking someone through the box — narrative, not a checklist
- Keep Kieran's voice — direct, technical, no fluff
- Use past tense ("I ran", "This revealed", "I found")
- Explain WHY things worked, not just WHAT you ran
- Highlight key discoveries with bold labels e.g. **Key Finding:** or **Critical Discovery:**
- Short punchy sentences. No waffle.

CODE BLOCKS:
- Every command in a fenced code block with correct language tag (```bash, ```python, ```xml etc)
- Never put commands inline in prose
- Brief context line BEFORE each block, **Result:** note AFTER key blocks
- All shell commands must include terminal prompt:
  - TryHackMe: kie@kiepc:~/THM/{RoomName}$
  - HackTheBox: kie@kiepc:~/HTB/{RoomName}$
  - OffSec/ProvingGrounds: kie@kiepc:~/PG/{RoomName}$
  - Other: kie@kiepc:~/{Platform}/{RoomName}$

STRUCTURE (in this order, omit empty sections):
## 🧠 Overview
## 🎯 Objectives
## 🔍 Reconnaissance & Initial Analysis
## ⚙️ Exploitation
## 🔐 Privilege Escalation (omit if not applicable)
## 🏁 Flags / Proof
## 🧩 Key Takeaways
## ⛓️ Attack Chain Summary
(numbered list, one line per step, full path from recon to root)
## 🔎 Detection Strategies
### Offensive Indicators
### Defensive Mitigations
## 🛠️ Tools & References

RULES:
- Preserve ALL image references exactly as given
- Don't invent flags, IPs, or details not in the notes

OUTPUT: Pure markdown only. No preamble. Start directly with the metadata block."""


SYSTEM_PROMPT_BLUETEAM = """You are a cybersecurity writeup formatter for a professional blue team / DFIR portfolio.

You receive raw notes and a lab/challenge description. Produce a clean, analytical, professional blue team writeup.

WRITING STYLE:
- Write like a SOC analyst documenting an investigation — methodical, evidence-based
- Keep Kieran's voice — direct, technical, no fluff
- Use past tense ("I identified", "The logs showed", "Analysis revealed")
- Explain WHY each finding matters from a defensive perspective
- Highlight key findings with bold labels e.g. **IOC Found:** or **Key Evidence:**
- Short punchy sentences. No waffle.

CODE BLOCKS:
- Any queries, commands, or scripts in fenced code blocks with correct language tag
- Brief context BEFORE each block, **Finding:** note AFTER key blocks
- No terminal prompts needed — blue team work is tool-based not shell-based

STRUCTURE (in this order, omit empty sections):
## 🧠 Overview
## 🎯 Objectives
## 🔍 Evidence & Initial Analysis
## 🔬 Investigation
## 🚨 Findings
## 🗺️ MITRE ATT&CK Mapping
(list relevant techniques with IDs e.g. T1566.001 - Spearphishing Attachment)
## 🧩 Key Takeaways
## 🛡️ Defensive Recommendations
## 🛠️ Tools & References

RULES:
- Preserve ALL image references exactly as given
- Don't invent IOCs, timestamps, or details not in the notes

OUTPUT: Pure markdown only. No preamble. Start directly with the metadata block."""


SYSTEM_PROMPT_CHALLENGE = """You are a cybersecurity writeup formatter for a professional CTF challenge portfolio.

You receive raw notes and a challenge description. Produce a clean, technical, professional CTF writeup.

WRITING STYLE:
- Write like you are explaining your solution to another technical person
- Keep Kieran's voice — direct, technical, no fluff
- Use past tense ("I noticed", "This gave me", "Decoding revealed")
- Explain the thought process, not just the steps
- Highlight breakthroughs with bold labels e.g. **Key Insight:** or **Breakthrough:**
- Short punchy sentences. No waffle.

CODE BLOCKS:
- Every command/script/payload in a fenced code block with correct language tag
- Brief context BEFORE each block, **Output:** note AFTER key blocks
- Include terminal prompts where relevant

STRUCTURE (in this order, omit empty sections):
## 🧠 Overview
## 🎯 Objective
## 🔍 Analysis
## ⚙️ Solution
## 🏁 Flag / Proof
## 🧩 Key Concepts
## 🛠️ Tools & References

RULES:
- Preserve ALL image references exactly as given
- Don't invent flags or details not in the notes

OUTPUT: Pure markdown only. No preamble. Start directly with the metadata block."""


# Platform/type routing
BLUETEAM_PLATFORMS = {"LetsDefend"}
BLUETEAM_TYPES     = {"Sherlock", "Lab"}
CHALLENGE_TYPES    = {"Challenge"}

def get_system_prompt(platform: str, room_type: str) -> str:
    """Select the appropriate system prompt based on platform and room type.
    
    Priority:
    1. Platform overrides type — LetsDefend is always blue team
    2. Type-based routing for other platforms
    3. Default to red team
    """
    # Platform always wins — LetsDefend is always blue team regardless of type
    if platform in BLUETEAM_PLATFORMS:
        return SYSTEM_PROMPT_BLUETEAM
    # HTB Sherlocks and Labs are always blue team
    if room_type in BLUETEAM_TYPES:
        return SYSTEM_PROMPT_BLUETEAM
    # Standalone challenges (HTB Challenges, PicoCTF etc)
    if room_type in CHALLENGE_TYPES:
        return SYSTEM_PROMPT_CHALLENGE
    # Everything else — machines, walkthroughs etc
    return SYSTEM_PROMPT_REDTEAM

SYSTEM_PROMPT = SYSTEM_PROMPT_REDTEAM  # fallback


def format_with_claude(raw_notes: str, room_info: str, meta: dict, saved_screenshots: list, icon_filename: str) -> str:
    url_line = (
        f'    <b>URL:</b> <a href="{meta["url"]}">{meta["room_name"]}</a><br>\n'
        if meta["url"] else ""
    )
    os_line = (
        f'    <b>OS:</b> {meta["os"]}<br>\n'
        if meta.get("os") else ""
    )
    # Use same 6-tag structure as README tables — built from tags_cell already on meta
    # tags_cell uses backtick format; strip for plain metadata block
    tags_cell_str = meta.get("tags_cell", "")
    tags_str = tags_cell_str.replace("`", "") if tags_cell_str else (
        f"#{meta['platform'].lower().replace(' ', '')} "
        f"#{meta['difficulty'].lower()}"
    )

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

    user_message = f"""Format a cybersecurity writeup for: "{meta["room_name"]}"

Use this metadata block exactly at the top:
{metadata_block}

Follow the structure defined in the system prompt. Keep sections in order, omit any with no content.

---
ROOM DESCRIPTION (from platform):
{room_info if room_info else "Not available — use notes only"}

---
ROUGH NOTES FROM KIERAN:
{raw_notes}
{screenshots_note}
---

Return ONLY the formatted markdown. Nothing else."""

    # Select system prompt based on platform and room type
    system_prompt = get_system_prompt(meta.get("platform", ""), meta.get("room_type", ""))

    print("   → Sending to Claude...")
    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    print("   ✅ Claude formatting complete")
    return message.content[0].text


def suggest_topic_tags(raw_notes: str, room_info: str, room_name: str) -> list:
    prompt = f"""You are tagging a CTF room for a portfolio. Based on the room name, description and notes below, suggest exactly 3 short topic tags that describe what the room is about technically.

Rules:
- Tags must be lowercase, no spaces (use hyphens), no # symbol
- Be specific and technical e.g. prompt-injection, sqli, privilege-escalation, buffer-overflow, file-upload, lfi, rce, active-directory, web, forensics, crypto, osint, reversing, steganography, dfir, malware, phishing, email-analysis
- Do NOT include platform names (tryhackme, htb, letsdefend) or difficulty (easy, medium, hard, beginner)
- Do NOT include type names (machine, sherlock, challenge, walkthrough, ctf, dojo, lab)
- You MUST return exactly 3 tags — no more, no fewer
- Return ONLY a comma separated list of 3 tags, nothing else. Example: prompt-injection,ai-security,web

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
        # Pad to 3 if model returned fewer
        while len(tags) < 3:
            tags.append("misc")
        print(f"   ✅ Topic tags: {tags}")
        return tags
    except Exception as e:
        print(f"   ⚠️  Could not generate topic tags: {e}")
        return ["misc", "misc", "misc"]


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

    room_type  = meta.get("room_type", "") or "Other"
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    diff_dir   = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])

    # Build path with OS subfolder if applicable
    os_name = meta.get("os", "")
    if platform in OS_SPLIT_PLATFORMS and os_name:
        room_link  = f"[{meta['room_name']}]({diff_dir}/{os_name}/{room_clean}/{room_clean}.md)"
        icon_rel   = f"{diff_dir}/{os_name}/{room_clean}/{icon_filename}" if icon_filename else ""
    else:
        room_link  = f"[{meta['room_name']}]({diff_dir}/{room_clean}/{room_clean}.md)"
        icon_rel   = f"{diff_dir}/{room_clean}/{icon_filename}" if icon_filename else ""

    icon_cell = f'<img src="{icon_rel}" width="32" alt="{meta["room_name"]}">' if icon_rel else ""

    tags_cell  = meta.get("tags_cell") or build_tags_cell(meta, topic_tags)
    diff_badge = f"`{meta['difficulty']}`"
    new_row    = f"| {icon_cell} | {room_link} | {diff_badge} | {tags_cell} | {meta['date']} |"

    # Remove old row if it exists
    search_path = f"{diff_dir}/"
    if search_path in content and room_clean in content:
        lines   = content.split("\n")
        content = "\n".join(l for l in lines if not (search_path in l and room_clean in l))

    # Always update "All Writeups" table — never create type sections
    all_writeups_headers = ["## All Writeups", "## 🖥️ Machines", "## 📋 Writeups"]
    section_found = None
    for h in all_writeups_headers:
        if h in content:
            section_found = h
            break

    # If a type section exists from a previous run, we still want All Writeups
    # Remove any orphan type section headers that shouldn't be there
    if section_found and section_found != "## All Writeups":
        # Check if All Writeups also exists - if so use that instead
        if "## All Writeups" in content:
            section_found = "## All Writeups"

    if section_found:
        # Remove placeholder row if present before inserting
        for placeholder in [
            "| *Auto-populated as writeups are added* | | | | |",
            "| *Auto-populated as writeups are added* | | | |",
            "| *Auto-populated as writeups are added* | | |",
        ]:
            if placeholder in content:
                content = content.replace(placeholder, new_row)
                break
        else:
            lines        = content.split("\n")
            section_idx  = next(i for i, l in enumerate(lines) if l.strip() == section_found)
            last_row_idx = section_idx
            for i in range(section_idx + 1, len(lines)):
                if lines[i].startswith("| ") and "---" not in lines[i]:
                    last_row_idx = i
                elif lines[i].startswith("## ") and i > section_idx + 1:
                    break
            lines.insert(last_row_idx + 1, new_row)
            content = "\n".join(lines)
    else:
        new_section = f"\n## All Writeups\n\n| Icon | Room | Difficulty | Tags | Date |\n|------|------|------------|------|------|\n{new_row}\n"
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
                new_section + "\n---\n\n" + footer_found
            )
        else:
            content = content.rstrip() + new_section

    # Update stats line — count rows in All Writeups table
    lines = content.split("\n")
    writeup_rows = [l for l in lines if (l.startswith("| [") or l.startswith("| !")) and "Auto-populated" not in l]
    total = len(writeup_rows)
    today = meta["date"]
    new_stats = f"> **{total} room{'s' if total != 1 else ''} completed · {total} flag{'s' if total != 1 else ''} captured · Last updated {today}**"
    import re as _re
    if _re.search(r'> \*\*\d+ rooms? completed', content):
        content = _re.sub(r'> \*\*\d+ rooms? completed[^*]*\*\*', new_stats[2:].strip(), content)
    elif _re.search(r'> \*\*\d+ labs? completed', content):
        content = _re.sub(r'> \*\*\d+ labs? completed[^*]*\*\*', new_stats[2:].strip(), content)

    if frontmatter:
        content = frontmatter + "\n" + content.lstrip("\n")
    readme.write_text(content, encoding="utf-8")
    print(f"   ✅ Updated {platform}/README.md — All Writeups table updated")


def update_difficulty_readme(diff_dir: Path, platform: str, difficulty: str, meta: dict, icon_filename: str, topic_tags: list = None):
    readme = diff_dir / "README.md"
    if not readme.exists():
        ensure_difficulty_readme(diff_dir, platform, difficulty)

    content    = readme.read_text(encoding="utf-8")
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    os_name    = meta.get("os", "")
    platform_f = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])

    # Build path with OS subfolder if applicable
    if platform_f in OS_SPLIT_PLATFORMS and os_name:
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

    tags_cell  = meta.get("tags_cell") or build_tags_cell(meta, topic_tags)

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

    # Normalise section header — strip "All " prefix if present
    import re as _re
    content = _re.sub(
        r'## All (Easy|Medium|Hard|Insane|Beginner) Writeups',
        r'## \1 Writeups',
        content
    )

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

    tags_cell  = meta.get("tags_cell") or build_tags_cell(meta, topic_tags)

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
    room_type  = meta.get("room_type", "")

    platform_dir = WRITEUPS_PATH / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    ensure_platform_readme(platform_dir, platform)

    # HTB uses type subfolder (Machines/Sherlocks/Challenges) before difficulty
    if platform == "HackTheBox" and room_type in ("Machine", "Sherlock", "Challenge"):
        type_folder = {"Machine": "Machines", "Sherlock": "Sherlocks", "Challenge": "Challenges"}[room_type]
        type_dir = platform_dir / type_folder
        diff_dir = type_dir / difficulty
        type_dir.mkdir(parents=True, exist_ok=True)
        diff_dir.mkdir(parents=True, exist_ok=True)
        ensure_difficulty_readme(diff_dir, platform, difficulty)
        if os_name:  # Machines have OS split
            os_dir = diff_dir / os_name
            os_dir.mkdir(parents=True, exist_ok=True)
            ensure_os_readme(os_dir, platform, difficulty, os_name)
            return os_dir / room_clean
        else:
            return diff_dir / room_clean
    else:
        diff_dir = platform_dir / difficulty
        diff_dir.mkdir(parents=True, exist_ok=True)
        ensure_difficulty_readme(diff_dir, platform, difficulty)
        # Insert OS subfolder for THM only
        if platform in OS_SPLIT_PLATFORMS and os_name:
            os_dir = diff_dir / os_name
            os_dir.mkdir(parents=True, exist_ok=True)
            ensure_os_readme(os_dir, platform, difficulty, os_name)
            return os_dir / room_clean
        else:
            return diff_dir / room_clean


def update_gitbook_branch(meta: dict):
    """Checkout gitbook branch, copy new writeup files, update SUMMARY.md and README tables, push."""
    platform   = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])
    difficulty = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    os_name    = meta.get("os", "")

    # Build the writeup path and SUMMARY indent level
    # HTB has a type subfolder (Machines/Sherlocks/Challenges) before difficulty
    room_type = meta.get("room_type", "")
    if platform == "HackTheBox" and room_type in ("Machine", "Sherlock", "Challenge"):
        type_folder = {"Machine": "Machines", "Sherlock": "Sherlocks", "Challenge": "Challenges"}[room_type]
        if os_name:  # Machines have OS split
            writeup_path = f"writeups/{platform}/{type_folder}/{difficulty}/{os_name}/{room_clean}/{room_clean}.md"
            parent_line  = f"        * [{os_name}](writeups/{platform}/{type_folder}/{difficulty}/{os_name}/README.md)"
            new_entry    = f"          * [{meta['room_name']}]({writeup_path})"
        else:  # Sherlocks/Challenges no OS
            writeup_path = f"writeups/{platform}/{type_folder}/{difficulty}/{room_clean}/{room_clean}.md"
            parent_line  = f"      * [{difficulty}](writeups/{platform}/{type_folder}/{difficulty}/README.md)"
            new_entry    = f"        * [{meta['room_name']}]({writeup_path})"
    elif platform in OS_SPLIT_PLATFORMS and os_name:
        writeup_path = f"writeups/{platform}/{difficulty}/{os_name}/{room_clean}/{room_clean}.md"
        parent_line  = f"    * [{os_name}](writeups/{platform}/{difficulty}/{os_name}/README.md)"
        new_entry    = f"      * [{meta['room_name']}]({writeup_path})"
    else:
        writeup_path = f"writeups/{platform}/{difficulty}/{room_clean}/{room_clean}.md"
        parent_line  = f"    * [{difficulty}](writeups/{platform}/{difficulty}/README.md)"
        new_entry    = f"      * [{meta['room_name']}]({writeup_path})"

    print("   → Updating SUMMARY.md on gitbook branch...")
    try:
        # Stash any uncommitted changes on main first
        subprocess.run(["git", "stash"], cwd=CTFHUB_REPO_PATH, capture_output=True)

        # Fetch gitbook branch (not fetched by default in Actions runner)
        subprocess.run(
            ["git", "fetch", "origin", "gitbook"],
            cwd=CTFHUB_REPO_PATH, capture_output=True
        )

        # Switch to gitbook branch
        subprocess.run(
            ["git", "checkout", "-B", "gitbook", "origin/gitbook"],
            cwd=CTFHUB_REPO_PATH, check=True, capture_output=True
        )

        summary_path = Path(CTFHUB_REPO_PATH) / "SUMMARY.md"
        if not summary_path.exists():
            print("   ⚠️  SUMMARY.md not found on gitbook branch — skipping")
            subprocess.run(["git", "checkout", "main"], cwd=CTFHUB_REPO_PATH, capture_output=True)
            subprocess.run(["git", "stash", "pop"], cwd=CTFHUB_REPO_PATH, capture_output=True)
            return

        content = summary_path.read_text(encoding="utf-8")

        # Don't add if already there — but still update READMEs below
        already_in_summary = writeup_path in content
        if already_in_summary:
            print(f"   ℹ️  {meta['room_name']} already in SUMMARY.md — skipping insert")

        # Insert the new room entry after the parent line (only if not already present)
        if not already_in_summary and parent_line in content:
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

        # Copy new writeup files from main
        import shutil
        room_clean_local = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))

        # Build correct paths accounting for HTB type subfolder
        if platform == "HackTheBox" and room_type in ("Machine", "Sherlock", "Challenge"):
            type_folder_gb = {"Machine": "Machines", "Sherlock": "Sherlocks", "Challenge": "Challenges"}[room_type]
            diff_dir_gb = Path(CTFHUB_REPO_PATH) / "writeups" / platform / type_folder_gb / difficulty
        else:
            diff_dir_gb = Path(CTFHUB_REPO_PATH) / "writeups" / platform / difficulty

        if platform in OS_SPLIT_PLATFORMS and os_name:
            src_folder = diff_dir_gb / os_name / room_clean_local
        else:
            src_folder = diff_dir_gb / room_clean_local

        # Update README tables on gitbook branch
        platform_dir_gb = Path(CTFHUB_REPO_PATH) / "writeups" / platform
        os_dir_gb = (diff_dir_gb / os_name) if (platform in OS_SPLIT_PLATFORMS and os_name) else None
        icon_fn = meta.get("icon_filename", "") or ""

        update_platform_readme(platform_dir_gb, platform, meta, icon_fn, [])
        update_difficulty_readme(diff_dir_gb, platform, difficulty, meta, icon_fn, [])
        if os_dir_gb:
            update_os_readme(os_dir_gb, platform, difficulty, os_name, meta, icon_fn, [])
        update_main_readme_stats()
        print("   ✅ README tables updated on gitbook branch")

        # Commit and push to gitbook
        subprocess.run(["git", "add", "."], cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"sync: Add {platform} - {meta['room_name']}"],
            cwd=CTFHUB_REPO_PATH, capture_output=True, text=True
        )
        if "nothing to commit" not in result.stdout:
            subprocess.run(["git", "push", "origin", "gitbook"], cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
            print("   ✅ Gitbook branch updated")

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
    difficulties = ["Beginner", "Easy", "Medium", "Hard", "Insane"]

    stats = {}
    total_easy = total_medium = total_hard = total_insane = 0

    for platform, emoji in platforms.items():
        platform_dir = WRITEUPS_PATH / platform
        if not platform_dir.exists():
            continue
        counts = {"Beginner": 0, "Easy": 0, "Medium": 0, "Hard": 0, "Insane": 0}
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
            total_easy   += counts["Beginner"] + counts["Easy"]
            total_medium += counts["Medium"]
            total_hard   += counts["Hard"]
            total_insane += counts["Insane"]

    grand_total = total_easy + total_medium + total_hard + total_insane

    rows = []
    for platform, data in stats.items():
        c = data["counts"]
        easy_count = c['Beginner'] + c['Easy']
        rows.append(f"| {data['emoji']} {platform} | {easy_count or '—'} | {c['Medium'] or '—'} | {c['Hard'] or '—'} | {data['total']} |")
    rows.append(f"| **Total** | **{total_easy}** | **{total_medium}** | **{total_hard}** | **{grand_total}** |")

    new_table = "| Platform | Easy | Medium | Hard | Total |\n|----------|------|--------|------|-------|\n" + "\n".join(rows)

    content = readme_path.read_text(encoding="utf-8")
    # Match both markdown and GitBook pipe-table formats
    pattern = r"\| Platform[ \t]*\| Easy[ \t]*\| Medium[ \t]*\| Hard[ \t]*\| Total[ \t]*\|.*?(?=\n\n|\n>|\n\*|\Z)"
    match   = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_table + content[match.end():]
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
    "LetsDefend":      "Lab",
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
    platform_dir = WRITEUPS_PATH / platform
    os_name      = meta.get("os", "")
    room_type    = meta.get("room_type", "")

    # Build diff_dir accounting for HTB type subfolder
    if platform == "HackTheBox" and room_type in ("Machine", "Sherlock", "Challenge"):
        type_folder = {"Machine": "Machines", "Sherlock": "Sherlocks", "Challenge": "Challenges"}[room_type]
        diff_dir = WRITEUPS_PATH / platform / type_folder / difficulty
    else:
        diff_dir = WRITEUPS_PATH / platform / difficulty

    # OS dir reference for README updates
    if platform in OS_SPLIT_PLATFORMS and os_name:
        os_dir = diff_dir / os_name
    else:
        os_dir = None

    # 6. Fetch room icon
    icon_filename = fetch_room_icon(meta.get("icon_url", ""), meta["url"], dest_folder, meta["room_name"])
    meta["icon_filename"] = icon_filename  # store for gitbook branch update

    # 7. Download screenshots
    saved_screenshots = []
    if image_urls:
        print(f"   → Downloading {len(image_urls)} screenshot(s)...")
        saved_screenshots = download_screenshots(image_urls, dest_folder)

    # 8. Generate topic tags and build canonical tags cell (used everywhere)
    topic_tags = suggest_topic_tags(raw_notes, room_info, meta["room_name"])
    meta["topic_tags"] = topic_tags  # store for metadata block
    meta["tags_cell"] = build_tags_cell(meta, topic_tags)  # canonical cell string
    print(f"   ✅ Tags cell: {meta['tags_cell']}")

    # 9. Format with Claude
    formatted = format_with_claude(raw_notes, room_info, meta, saved_screenshots, icon_filename)

    # 10. Save markdown to GitHub
    room_clean  = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    output_file = dest_folder / f"{room_clean}.md"
    gif_footer = "\n\n---\n\n<p align=\"center\"><img src=\"https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExaDdhdmt6N2dhazFqbTdsdmk0ZThkdTBrYjBoOGdobWF2NzRmbXBjeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8kDPdrfdBUP8k/giphy.gif\" width=\"300\"></p>\n"
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

    # 17. Update gitbook branch with new writeup files + SUMMARY + READMEs
    update_gitbook_branch(meta)

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
