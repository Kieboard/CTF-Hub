"""
CTF Auto Publisher — Full Pipeline
Kieran Rorrison — CTF-Hub

Triggered by: GitHub Actions (every 30 mins)
Flow:
  1. Query Notion for pages where Completed=True and Published=False
  2. Read rough notes from the Notion page
  3. Fetch room info from the THM/HTB URL
  4. Send both to Claude → get professional writeup
  5. Update the Notion page with formatted writeup
  6. Download screenshots from Notion
  7. Commit + push to GitHub
  8. Mark page as Published=True in Notion
"""

import os
import re
import sys
import time
import shutil
import hashlib
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from notion_client import Client
import anthropic

# ─────────────────────────────────────────────
# CONFIG — loaded from environment / GitHub Secrets
# ─────────────────────────────────────────────
NOTION_TOKEN       = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
CTFHUB_REPO_PATH   = os.environ.get("CTFHUB_REPO_PATH", ".")

notion  = Client(auth=NOTION_TOKEN)
claude  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────────
# PLATFORM / DIFFICULTY MAPPINGS
# ─────────────────────────────────────────────
PLATFORM_FOLDERS = {
    "tryhackme":  "TryHackMe",
    "thm":        "TryHackMe",
    "hackthebox": "HackTheBox",
    "htb":        "HackTheBox",
    "vulnhub":    "VulnHub",
    "pwnedlabs":  "PwnedLabs",
    "picoctf":    "PicoCTF",
    "rootme":     "RootMe",
    "root-me":    "RootMe",
}

DIFFICULTY_FOLDERS = {
    "easy":   "Easy",
    "medium": "Medium",
    "hard":   "Hard",
    "insane": "Insane",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

# ─────────────────────────────────────────────
# NOTION HELPERS
# ─────────────────────────────────────────────

def query_completed_unpublished():
    """Find all pages where Completed=True and Published=False."""
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
    """Extract all useful properties from a Notion page."""
    props = page.get("properties", {})
    meta = {
        "page_id":   page["id"],
        "room_name": "",
        "platform":  "",
        "difficulty": "",
        "url":       "",
        "tags":      [],
        "date":      datetime.now().strftime("%B %d, %Y"),
    }

    # Room name (title property)
    title_prop = props.get("Name") or props.get("Title") or props.get("Room") or {}
    title_list = title_prop.get("title", [])
    if title_list:
        meta["room_name"] = title_list[0].get("plain_text", "Unknown")

    # Platform
    platform_prop = props.get("Platform", {})
    if platform_prop.get("type") == "select" and platform_prop.get("select"):
        meta["platform"] = platform_prop["select"]["name"]
    elif platform_prop.get("type") == "multi_select":
        opts = platform_prop.get("multi_select", [])
        if opts:
            meta["platform"] = opts[0]["name"]

    # Difficulty
    diff_prop = props.get("Difficulty", {})
    if diff_prop.get("type") == "select" and diff_prop.get("select"):
        meta["difficulty"] = diff_prop["select"]["name"]

    # URL
    url_prop = props.get("URL", {})
    if url_prop.get("type") == "url":
        meta["url"] = url_prop.get("url") or ""
    elif url_prop.get("type") == "rich_text":
        texts = url_prop.get("rich_text", [])
        if texts:
            meta["url"] = texts[0].get("plain_text", "")

    # Tags (multi-select)
    tags_prop = props.get("Tags", {})
    if tags_prop.get("type") == "multi_select":
        meta["tags"] = [t["name"] for t in tags_prop.get("multi_select", [])]

    return meta


def extract_blocks_as_text(page_id: str) -> tuple[str, list]:
    """
    Read all blocks from a Notion page.
    Returns (plain_text, image_urls_list)
    """
    blocks_text = []
    image_urls  = []
    cursor      = None

    while True:
        kwargs = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor

        response = notion.blocks.children.list(**kwargs)
        blocks   = response.get("results", [])

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
    """Fetch the room/challenge description from THM or HTB page."""
    if not url:
        return ""

    print(f"   → Fetching room info from: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"   ⚠️  Could not fetch room page (status {resp.status_code})")
            return ""

        text = resp.text

        # Extract meaningful text — strip HTML tags
        clean = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Return first 3000 chars — enough for room description
        return clean[:3000]

    except Exception as e:
        print(f"   ⚠️  Could not fetch room page: {e}")
        return ""


def download_screenshots(image_urls: list, dest_folder: Path) -> list:
    """Download screenshots from Notion's CDN to local folder."""
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


def format_with_claude(raw_notes: str, room_info: str, meta: dict, saved_screenshots: list) -> str:
    """Send notes + room info to Claude, get back formatted writeup."""

    # Build metadata block
    url_line = f'    <b>URL:</b> <a href="{meta["url"]}">{meta["room_name"]}</a><br>\n' if meta["url"] else ""
    all_tags = list(dict.fromkeys(
        [f"#{meta['platform'].lower().replace(' ','')}", f"#{meta['difficulty'].lower()}"] +
        [f"#{t.lower().replace(' ','-')}" for t in meta["tags"]]
    ))
    tags_str = " ".join(all_tags)

    metadata_block = f"""<p align="right">
  <sub>
    <b>Platform:</b> {meta["platform"]}<br>
    <b>Difficulty:</b> {meta["difficulty"]}<br>
    <b>Status:</b> Completed ✅<br>
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
# NOTION WRITE-BACK
# ─────────────────────────────────────────────

def clear_page_content(page_id: str):
    """Delete all existing blocks from the page."""
    cursor = None
    while True:
        kwargs = {"block_id": page_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = notion.blocks.children.list(**kwargs)
        blocks   = response.get("results", [])
        for block in blocks:
            try:
                notion.blocks.delete(block_id=block["id"])
            except Exception:
                pass
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
        time.sleep(0.3)


def markdown_to_notion_blocks(markdown: str) -> list:
    """Convert markdown text back into Notion block objects."""
    blocks = []
    lines  = markdown.split("\n")
    i      = 0

    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.startswith("```"):
            lang    = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang if lang else "plain text"
                }
            })

        # Headings
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})

        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})

        elif line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})

        # Bullet points
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})

        # Numbered list
        elif re.match(r'^\d+\. ', line):
            content = re.sub(r'^\d+\. ', '', line)
            blocks.append({"object": "block", "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": content}}]}})

        # Divider
        elif line.strip() == "---":
            blocks.append({"object": "block", "type": "divider", "divider": {}})

        # Quote
        elif line.startswith("> "):
            blocks.append({"object": "block", "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})

        # Image references — add as paragraph with italic text
        elif line.startswith("!["):
            match = re.match(r'!\[([^\]]*)\]\(([^\)]+)\)', line)
            if match:
                alt_text = match.group(1)
                filename = match.group(2)
                blocks.append({"object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text",
                        "text": {"content": f"📸 {alt_text} ({filename})"},
                        "annotations": {"italic": True, "color": "gray"}}]}})

        # HTML metadata block — wrap in callout
        elif line.strip().startswith("<p align"):
            # Collect entire HTML block
            html_lines = [line]
            while i + 1 < len(lines) and not lines[i+1].strip().startswith("#"):
                i += 1
                html_lines.append(lines[i])
                if lines[i].strip() == "---":
                    break
            # Put metadata in a callout
            blocks.append({"object": "block", "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": "Writeup auto-generated by CTF Publisher ✅"}}],
                    "icon": {"type": "emoji", "emoji": "🤖"},
                    "color": "gray_background"
                }})

        # Regular paragraph
        elif line.strip():
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}})

        i += 1

    return blocks


def write_back_to_notion(page_id: str, formatted_content: str):
    """Replace page content with the formatted writeup."""
    print("   → Clearing old Notion content...")
    clear_page_content(page_id)
    time.sleep(1)

    print("   → Writing formatted writeup to Notion...")
    blocks = markdown_to_notion_blocks(formatted_content)

    # Notion API limit: 100 blocks per request
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        notion.blocks.children.append(block_id=page_id, children=chunk)
        time.sleep(0.5)

    print("   ✅ Notion page updated")


def mark_as_published(page_id: str):
    """Set Published=True on the Notion page."""
    notion.pages.update(
        page_id=page_id,
        properties={"Published": {"checkbox": True}}
    )
    print("   ✅ Marked as Published in Notion")


# ─────────────────────────────────────────────
# GITHUB
# ─────────────────────────────────────────────

def get_destination_folder(meta: dict) -> Path:
    """Build CTF-Hub/Platform/Difficulty/RoomName/"""
    platform   = PLATFORM_FOLDERS.get(meta["platform"].lower().replace(" ", ""), meta["platform"])
    difficulty = DIFFICULTY_FOLDERS.get(meta["difficulty"].lower(), meta["difficulty"])
    room_clean = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    return Path(CTFHUB_REPO_PATH) / platform / difficulty / room_clean


def git_commit_push(room_name: str, platform: str):
    """Stage all changes, commit, and push."""
    print("   → Committing to GitHub...")
    try:
        subprocess.run(["git", "add", "."],
            cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)

        commit_msg = f"writeup: Add {platform} - {room_name}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=CTFHUB_REPO_PATH, capture_output=True, text=True)

        if "nothing to commit" in result.stdout:
            print("   ℹ️  Nothing new to commit")
            return

        subprocess.run(["git", "push"],
            cwd=CTFHUB_REPO_PATH, check=True, capture_output=True)
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

    # 1. Read rough notes from Notion
    print("   → Reading notes from Notion...")
    raw_notes, image_urls = extract_blocks_as_text(meta["page_id"])
    print(f"   ✅ Got {len(raw_notes)} chars of notes, {len(image_urls)} image(s)")

    # 2. Fetch room description from URL
    room_info = fetch_room_description(meta["url"])

    # 3. Create destination folder
    dest_folder = get_destination_folder(meta)
    dest_folder.mkdir(parents=True, exist_ok=True)

    # 4. Download screenshots
    saved_screenshots = []
    if image_urls:
        print(f"   → Downloading {len(image_urls)} screenshot(s)...")
        saved_screenshots = download_screenshots(image_urls, dest_folder)

    # 5. Format with Claude
    formatted = format_with_claude(raw_notes, room_info, meta, saved_screenshots)

    # 6. Save markdown to GitHub repo
    room_clean  = re.sub(r'[^\w\-]', '', meta["room_name"].replace(" ", "-"))
    output_file = dest_folder / f"{room_clean}.md"
    output_file.write_text(formatted, encoding="utf-8")
    print(f"   ✅ Writeup saved: {output_file}")

    # 7. Write formatted content back to Notion
    write_back_to_notion(meta["page_id"], formatted)

    # 8. Commit + push to GitHub
    git_commit_push(meta["room_name"], meta["platform"])

    # 9. Mark as published in Notion
    mark_as_published(meta["page_id"])

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
