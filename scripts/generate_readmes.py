"""
Generate README.md files for all platform and difficulty folders in CTF-Hub.
Run once locally: python generate_readmes.py
"""

from pathlib import Path

# ─────────────────────────────────────────────
# PLATFORM CONFIGS
# ─────────────────────────────────────────────
PLATFORMS = {
    "TryHackMe": {
        "emoji": "🔴",
        "description": "TryHackMe rooms organised by difficulty. Focused on fundamentals, methodology, and attack flow.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "HackTheBox": {
        "emoji": "🟢",
        "description": "HackTheBox machine and challenge writeups covering real-world attack scenarios.",
        "difficulties": ["Easy", "Medium", "Hard", "Insane"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴", "Insane": "💀"},
    },
    "VulnHub": {
        "emoji": "🟣",
        "description": "VulnHub vulnerable machine writeups. Offline lab practice and methodology building.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "PwnedLabs": {
        "emoji": "🔵",
        "description": "PwnedLabs cloud and Active Directory focused challenge writeups.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "PicoCTF": {
        "emoji": "🏴",
        "description": "PicoCTF challenge writeups. Beginner-friendly CTF covering web, forensics, crypto and more.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "RootMe": {
        "emoji": "⚫",
        "description": "Root-Me challenge writeups covering web, network, and system exploitation.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "OffSec": {
        "emoji": "🟠",
        "description": "OffSec Proving Grounds Play and Practice machines. OSCP-relevant content and methodology.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "ProvingGrounds": {
        "emoji": "🟠",
        "description": "OffSec Proving Grounds machines. Direct OSCP preparation and practice.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "pwn.college": {
        "emoji": "🎓",
        "description": "pwn.college challenge writeups. Focused on binary exploitation, system security, and CTF fundamentals.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "CTFtime": {
        "emoji": "🏁",
        "description": "General CTF competition writeups from various events and competitions listed on CTFtime.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
    "SANSHolidayHack": {
        "emoji": "🎄",
        "description": "SANS Holiday Hack Challenge writeups. Annual CTF featuring real-world scenarios and creative challenges.",
        "difficulties": ["Easy", "Medium", "Hard"],
        "diff_emoji": {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"},
    },
}

REPO_ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────

def platform_readme(name: str, config: dict) -> str:
    emoji = config["emoji"]
    desc  = config["description"]
    diffs = config["difficulties"]
    de    = config["diff_emoji"]

    diff_table = "\n".join(
        f"| {de[d]} {d} | [`{d}/`](./{d}/) |"
        for d in diffs
    )

    return f"""# {emoji} {name}

{desc}

---

## 📂 Difficulty

| Level | Folder |
|-------|--------|
{diff_table}

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""


def difficulty_readme(platform: str, difficulty: str, config: dict) -> str:
    emoji     = config["emoji"]
    diff_emoji = config["diff_emoji"].get(difficulty, "📁")

    descriptions = {
        "Easy":   "Beginner-friendly rooms. Focus on core methodology, enumeration fundamentals, and common vulnerabilities.",
        "Medium": "Intermediate rooms requiring chained exploits, deeper enumeration, and creative thinking.",
        "Hard":   "Advanced rooms involving complex attack chains, custom exploits, and deep technical knowledge.",
        "Insane": "Expert-level machines requiring advanced exploitation techniques and deep system knowledge.",
    }

    desc = descriptions.get(difficulty, f"{difficulty} difficulty writeups.")

    return f"""# {diff_emoji} {platform} — {difficulty}

{desc}

---

## 📋 Writeups

| Icon | Room | Tags | Date |
|------|------|------|------|
| *Auto-populated as writeups are added* | | | |

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""


# ─────────────────────────────────────────────
# GENERATE
# ─────────────────────────────────────────────

def generate_all():
    created = 0

    for platform, config in PLATFORMS.items():
        platform_dir = REPO_ROOT / platform

        # Create platform folder if missing
        platform_dir.mkdir(exist_ok=True)

        # Platform README
        platform_readme_path = platform_dir / "README.md"
        platform_readme_path.write_text(platform_readme(platform, config), encoding="utf-8")
        print(f"✅ Created {platform}/README.md")
        created += 1

        # Difficulty folders + READMEs
        for difficulty in config["difficulties"]:
            diff_dir = platform_dir / difficulty
            diff_dir.mkdir(exist_ok=True)

            diff_readme_path = diff_dir / "README.md"
            diff_readme_path.write_text(
                difficulty_readme(platform, difficulty, config),
                encoding="utf-8"
            )
            print(f"✅ Created {platform}/{difficulty}/README.md")
            created += 1

    print(f"\n🎉 Done — {created} README(s) created")


if __name__ == "__main__":
    generate_all()
