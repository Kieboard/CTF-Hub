"""
Generate README.md files for all platform and difficulty folders in CTF-Hub.
Run once locally: python generate_readmes.py
Kieran Rorrison — CTF-Hub
"""

from pathlib import Path

PLATFORMS = {
    "TryHackMe": {
        "description": "TryHackMe rooms organised by difficulty. Focused on fundamentals, methodology, and attack flow.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "HackTheBox": {
        "description": "HackTheBox machine and challenge writeups covering real-world attack scenarios.",
        "difficulties": ["Easy", "Medium", "Hard", "Insane"],
    },
    "VulnHub": {
        "description": "VulnHub vulnerable machine writeups. Offline lab practice and methodology building.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "PwnedLabs": {
        "description": "PwnedLabs cloud and Active Directory focused challenge writeups.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "PicoCTF": {
        "description": "PicoCTF challenge writeups. Beginner-friendly CTF covering web, forensics, crypto and more.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "RootMe": {
        "description": "Root-Me challenge writeups covering web, network, and system exploitation.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "OffSec": {
        "description": "OffSec Proving Grounds Play and Practice machines. OSCP-relevant content and methodology.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "ProvingGrounds": {
        "description": "OffSec Proving Grounds machines. Direct OSCP preparation and practice.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "pwn.college": {
        "description": "pwn.college challenge writeups. Focused on binary exploitation, system security, and CTF fundamentals.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "CTFtime": {
        "description": "General CTF competition writeups from various events and competitions listed on CTFtime.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "SANSHolidayHack": {
        "description": "SANS Holiday Hack Challenge writeups. Annual CTF featuring real-world scenarios and creative challenges.",
        "difficulties": ["Easy", "Medium", "Hard"],
    },
    "LetsDefend": {
        "description": "LetsDefend blue team SOC challenges. Threat hunting, log analysis, malware analysis, and incident response.",
        "difficulties": ["Beginner", "Easy", "Medium", "Hard"],
    },
}

REPO_ROOT = Path(__file__).parent.parent / "writeups"

DIFF_DESCRIPTIONS = {
    "Beginner": "Entry-level challenges. Focus on core SOC concepts and fundamental analysis techniques.",
    "Easy":     "Beginner-friendly rooms. Focus on core methodology, enumeration fundamentals, and common vulnerabilities.",
    "Medium":   "Intermediate rooms requiring chained exploits, deeper enumeration, and creative thinking.",
    "Hard":     "Advanced rooms involving complex attack chains, custom exploits, and deep technical knowledge.",
    "Insane":   "Expert-level machines requiring advanced exploitation techniques and deep system knowledge.",
}


def platform_readme(name: str, config: dict) -> str:
    desc  = config["description"]
    diffs = config["difficulties"]

    diff_table = "\n".join(
        f"| {d} | [{d}/](./{d}/) |"
        for d in diffs
    )

    return f"""# {name}

{desc}

---

## Difficulty

| Level | Folder |
|-------|--------|
{diff_table}

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""


def difficulty_readme(platform: str, difficulty: str) -> str:
    desc = DIFF_DESCRIPTIONS.get(difficulty, f"{difficulty} difficulty writeups.")

    return f"""# {platform} — {difficulty}

{desc}

---

## Writeups

| Icon | Room | Tags | Date |
|------|------|------|------|
| *Auto-populated as writeups are added* | | | |

---

> Writeups authored in Notion, auto-published via CTF Publisher.
"""


def generate_all():
    created = 0

    for platform, config in PLATFORMS.items():
        platform_dir = REPO_ROOT / platform
        platform_dir.mkdir(exist_ok=True)

        platform_readme_path = platform_dir / "README.md"
        platform_readme_path.write_text(platform_readme(platform, config), encoding="utf-8")
        print(f"Created {platform}/README.md")
        created += 1

        for difficulty in config["difficulties"]:
            diff_dir = platform_dir / difficulty
            diff_dir.mkdir(exist_ok=True)

            diff_readme_path = diff_dir / "README.md"
            diff_readme_path.write_text(
                difficulty_readme(platform, difficulty),
                encoding="utf-8"
            )
            print(f"Created {platform}/{difficulty}/README.md")
            created += 1

    print(f"\nDone — {created} README(s) created")


if __name__ == "__main__":
    generate_all()
