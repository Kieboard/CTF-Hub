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
    "holidayhack":       "SANSHolidayHack",
}

DIFFICULTY_FOLDERS = {
    "easy":   "Easy",
    "medium": "Medium",
    "hard":   "Hard",
    "insane": "Insane",
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
    "pwn.college":     {"emoji": "🎓", "desc": "pwn.college challenge writeups. Binary exploitation and system security."},
    "CTFtime":         {"emoji": "🏁", "desc": "General CTF competition writeups from various events on CTFtime."},
    "SANSHolidayHack": {"emoji": "🎄", "desc": "SANS Holiday Hack Challenge writeups. Annual CTF with real-world scenarios."},
}

DIFF_EMOJI = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴", "Insane": "💀"}
DIFF_DESC  = {
    "Easy":   "Beginner-friendly rooms focusing on core methodology and common vulnerabilities.",
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
        "date":       datetime.now().strftime("%B %d, %Y"),
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

    # Icon URL — check "Icon URL" (url type) or "Files" (files type) property
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
    """
    Get the room icon. Tries in order:
    1. Direct URL from Notion (Files or Icon URL property)
    2. og:image scrape from the platform page URL
    Saves as RoomName.png. Returns filename if saved, else empty string.
    """
    room_clean = re.sub(r'[^\w\-]', '', room_name.replace(" ", ""))
    filename   = f"{room_clean}.png"

    # Try direct URL from Notion first
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
            print(f"   ⚠️  Could not fetch page for icon (status {resp.status_code})")
            return ""

        # Try og:image first
        og_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', resp.text)
        if not og_match:
            og_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', resp.text)

        # TryHackMe S3 room icon fallback pattern
        if not og_match:
            s3_match = re.search(r'https://tryhackme-images\.s3\.amazonaws\.com/room-icons/[^\s"\']+', resp.text)
            if s3_match:
                icon_url = s3_match.group(0)
            else:
                print("   ⚠️  No room icon found on page")
                return ""
        else:
            icon_url = og_match.group(1)

        # Download the icon
        icon_resp = requests.get(icon_url, headers=headers, timeout=15)
        if icon_resp.status_code == 200:
            room_clean = re.sub(r'[^\w\-]', '', room_name.replace(" ", ""))
            filename   = f"{room_clean}.png"
            icon_path  = dest_folder / filename
            icon_path.write_bytes(icon_resp.content)
            print(f"   ✅ Icon saved: {filename}")
            return filename
        else:
            print(f"   ⚠️  Icon download returned status {icon_resp.status_code}")
            return ""

    except Exception as e:
        print(f"   ⚠️  Could not fetch room icon: {e}")
        return ""


def set_notion_page_icon(page_id: str, icon_url: str):
    """Set the Notion page icon to an external URL."""
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
            else:
                print(f"   ⚠️  Screenshot {i} returned status {resp.status_code}")
        except Exception as e:
            print(f"   ⚠️  Could not download screenshot {i}: {e}")
    return saved


# ─────────────────────────────────────────────
# CLAUDE FORMATTING
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are a cybersecurity writeup formatter for a professional CTF portfolio.

You receive:
1. Raw rough notes from the hacker (Kieran)
2. Room description scraped from the CTF platform

Combine both to produce a clean, structured, professional writeup.

RULES:
- Keep Kieran's voice — don't make it sound corporate or AI-generated
- Show thinking and methodology — explain WHY things worked
- Use past tense ("I ran nmap", "I found", "This revealed")
- Code blocks must use proper fencing with language tags (```bash, ```python etc)
- Preserve ALL image references exactly as given (e.g. ![Screenshot 1](screenshot_01.png))
- Don't invent flags, IPs, or details not in the notes
- Don't pad with fluff — be concise and precise
- If a section has no content, omit it entirely

OUTPUT: Pure markdown only. No preamble. No explanation. Start directly with the metadata block."""


def format_with_claude(raw_notes: str, room_info: str, meta: dict, saved_screenshots: list, icon_filename: str) -> str:
    url_line = (
        f'    <b>URL:</b> <a href="{meta["url"]}">{meta["room_name"]}</a><br>\n'
        if meta["url"] else ""
    )
    all_tags = list(dict.fromkeys(
        [f"#{meta['platform'].lower().replace(' ', '')}",
         f"#{meta['difficulty'].lower()}"] +
        [f"#{t.lower().replace(' ', '-')}" for t in meta["tags"]]
    ))
    tags_str = " ".join(all_tags)

    icon_line = f'    <b>Icon:</b> <img src="{icon_filename}" width="32"><br>\n' if icon_filename else ""

    metadata_block = f"""<p align="right">
  <sub>
    <b>Platform:</b> {meta["platform"]}<br>
    <b>Difficulty:</b> {meta["difficulty"]}<br>
    <b>Status:</b> Completed ✅<br>
{url_line}{icon_line}    <b>Date:</b> {meta["date"]}<br>
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

Then use this structure:
# {meta["room_name"]}
## 🧠 Overview
## 🎯 Objectives
## 🔍 Reconnaissance & Initial Analysis
## ⚙️ Exploitation
## 🔐 Privilege Escalation (omit if not applicable)
## 🏁 Flags / Proof
## 🧩 Key Takeaways
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


def update_difficulty_readme(diff_dir: Path, platform: str, difficulty: str, meta: dict, icon_filename: str):
    """Add a row for this writeup to the difficulty README table."""
    readme = diff_dir / "README.md"
    if not readme.exists():
        ensure_difficulty_readme(diff_dir, platform, difficulty)

    content    = readme.read_text(encoding="utf-8")
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))

    # If room already has a row, remove it so we can re-add with updated info
    if f"]({room_clean}/" in content:
        lines   = content.split("\n")
        content = "\n".join(l for l in lines if f"]({room_clean}/" not in l)
        print(f"   ℹ️  Updating existing {meta['room_name']} row in README table")

    # Icon cell — use saved icon if available
    if icon_filename:
        icon_cell = f'<img src="{room_clean}/{icon_filename}" width="32" alt="{meta["room_name"]}">'
    else:
        icon_cell = ""

    # Tags cell — cap at 4 for readability
    auto_tags = [
        f"`#{meta['platform'].lower().replace(' ', '')}`",
        f"`#{meta['difficulty'].lower()}`"
    ]
    extra_tags = [f"`#{t.lower().replace(' ', '-')}`" for t in meta["tags"]]
    all_tags   = list(dict.fromkeys(auto_tags + extra_tags))[:4]
    tags_cell  = " ".join(all_tags)

    room_link = f"[{meta['room_name']}]({room_clean}/{room_clean}.md)"
    new_row   = f"| {icon_cell} | {room_link} | {tags_cell} | {meta['date']} |"

    # Replace placeholder or append
    # Match either 3-cell or 4-cell placeholder variants
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
    """Delete all blocks on the page with retry to ensure full clearance."""
    for attempt in range(3):  # retry up to 3 times to handle large pages
        cursor = None
        deleted = 0
        while True:
            if cursor:
                response = notion.blocks.children.list(block_id=page_id, page_size=100, start_cursor=cursor)
            else:
                response = notion.blocks.children.list(block_id=page_id, page_size=100)
            blocks = response.get("results", [])
            if not blocks:
                break
            for block in blocks:
                try:
                    notion.blocks.delete(block_id=block["id"])
                    deleted += 1
                    time.sleep(0.1)
                except Exception:
                    pass
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
            time.sleep(0.3)
        if deleted == 0:
            break  # nothing left to delete
        time.sleep(1)  # wait before checking again


def write_back_to_notion(page_id: str, formatted_content: str, original_notes: str):
    print("   → Clearing old Notion content...")
    clear_page_content(page_id)
    time.sleep(1)

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

    platform_dir = Path(CTFHUB_REPO_PATH) / platform
    diff_dir     = platform_dir / difficulty

    platform_dir.mkdir(parents=True, exist_ok=True)
    ensure_platform_readme(platform_dir, platform)
    diff_dir.mkdir(parents=True, exist_ok=True)
    ensure_difficulty_readme(diff_dir, platform, difficulty)

    return diff_dir / room_clean


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
# MAIN PIPELINE
# ─────────────────────────────────────────────

def process_page(page: dict):
    meta = get_page_properties(page)
    print(f"\n{'='*50}")
    print(f"📝 Processing: {meta['room_name']}")
    print(f"   Platform: {meta['platform']} | Difficulty: {meta['difficulty']}")

    # 1. Read rough notes
    print("   → Reading notes from Notion...")
    raw_notes, image_urls = extract_blocks_as_text(meta["page_id"])
    print(f"   ✅ Got {len(raw_notes)} chars of notes, {len(image_urls)} image(s)")

    # 2. Create destination folder
    dest_folder = get_destination_folder(meta)
    dest_folder.mkdir(parents=True, exist_ok=True)

    platform   = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])
    difficulty = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])
    diff_dir   = Path(CTFHUB_REPO_PATH) / platform / difficulty

    # 3. Fetch room icon — from Notion Files property or platform page
    icon_filename = fetch_room_icon(meta.get("icon_url", ""), meta["url"], dest_folder, meta["room_name"])

    # 4. Fetch room description
    room_info = fetch_room_description(meta["url"])

    # 5. Download screenshots
    saved_screenshots = []
    if image_urls:
        print(f"   → Downloading {len(image_urls)} screenshot(s)...")
        saved_screenshots = download_screenshots(image_urls, dest_folder)

    # 6. Format with Claude
    formatted = format_with_claude(raw_notes, room_info, meta, saved_screenshots, icon_filename)

    # 7. Save markdown to GitHub
    room_clean  = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    output_file = dest_folder / f"{room_clean}.md"
    output_file.write_text(formatted, encoding="utf-8")
    print(f"   ✅ Writeup saved: {output_file}")

    # 8. Update difficulty README table
    update_difficulty_readme(diff_dir, platform, difficulty, meta, icon_filename)

    # 9. Write formatted content back to Notion
    try:
        write_back_to_notion(meta["page_id"], formatted, raw_notes)
    except Exception as e:
        print(f"   ⚠️  Notion write-back failed: {e}")

    # 10. Set Notion page icon using the Icon URL from Notion property
    if icon_filename and meta.get("icon_url"):
        set_notion_page_icon(meta["page_id"], meta["icon_url"])

    # 11. Commit + push to GitHub
    git_commit_push(meta["room_name"], meta["platform"])

    # 12. Mark as published
    try:
        mark_as_published(meta["page_id"])
    except Exception as e:
        print(f"   ⚠️  Could not mark as Published: {e}")

    print(f"🎉 Done: {meta['room_name']}\n")


def main():
    print("\n🚀 CTF Auto Publisher starting...")
    pages = query_completed_unpublished()

    if not pages:
        print("✅ Nothing to process — all caught up!")
        return

    for page in pages:
        try:
            process_page(page)
        except Exception as e:
            print(f"❌ Error processing page: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n✅ All done!")


if __name__ == "__main__":
    main()
