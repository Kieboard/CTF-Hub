"""
Migration script — move existing TryHackMe and HackTheBox writeups
into OS subfolders (Linux / Windows / Other).

Run once from the root of your CTF-Hub repo:
    python scripts/migrate_os_folders.py

Kieran Rorrison — CTF-Hub
"""

import os
import re
import shutil
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent
WRITEUPS     = REPO_ROOT / "writeups"

# Manually define OS for each existing room
# Format: "Platform/Difficulty/RoomName": "Linux" | "Windows" | "Other"
ROOM_OS_MAP = {
    "TryHackMe/Easy/RootMe":   "Linux",
    "TryHackMe/Easy/CupidBot": "Other",
}

def update_readme_paths(readme_path: Path, old_room: str, new_room_path: str):
    """Update any links in a README that reference the old room path."""
    if not readme_path.exists():
        return
    content = readme_path.read_text(encoding="utf-8")
    if old_room in content:
        content = content.replace(old_room, new_room_path)
        readme_path.write_text(content, encoding="utf-8")
        print(f"   ✅ Updated links in {readme_path.relative_to(REPO_ROOT)}")


def migrate():
    print("\n🚀 Starting OS folder migration...\n")

    for room_rel, os_name in ROOM_OS_MAP.items():
        parts        = room_rel.split("/")
        platform     = parts[0]
        difficulty   = parts[1]
        room_name    = parts[2]

        src = WRITEUPS / platform / difficulty / room_name
        dst = WRITEUPS / platform / difficulty / os_name / room_name

        if not src.exists():
            print(f"⚠️  Source not found, skipping: {src.relative_to(REPO_ROOT)}")
            continue

        if dst.exists():
            print(f"ℹ️  Already migrated, skipping: {dst.relative_to(REPO_ROOT)}")
            continue

        # Create OS subfolder
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Move the room folder
        shutil.move(str(src), str(dst))
        print(f"✅ Moved: {src.relative_to(REPO_ROOT)} → {dst.relative_to(REPO_ROOT)}")

        # Create OS-level README if it doesn't exist
        os_readme = dst.parent / "README.md"
        if not os_readme.exists():
            emoji = "🐧" if os_name == "Linux" else "🪟" if os_name == "Windows" else "💻"
            os_readme.write_text(
                f"# {emoji} {platform} — {difficulty} — {os_name}\n\n"
                f"{difficulty} difficulty {os_name} machines.\n\n---\n\n"
                f"## 📋 Writeups\n\n"
                f"| Icon | Room | Tags | Date |\n"
                f"|------|------|------|------|\n"
                f"| *Auto-populated as writeups are added* | | | |\n\n---\n\n"
                f"> Writeups authored in Notion, auto-published via CTF Publisher.\n",
                encoding="utf-8"
            )
            print(f"   ✅ Created {os_readme.relative_to(REPO_ROOT)}")

        # Update links in the difficulty README
        diff_readme = WRITEUPS / platform / difficulty / "README.md"
        update_readme_paths(diff_readme, f"]({room_name}/", f"]{os_name}/{room_name}/")

        # Update links in the platform README
        platform_readme = WRITEUPS / platform / "README.md"
        update_readme_paths(platform_readme, f"/{difficulty}/{room_name}/", f"/{difficulty}/{os_name}/{room_name}/")

    print("\n✅ Migration complete.")
    print("\n📌 Next steps:")
    print("   1. Review the moved folders in File Explorer to confirm")
    print("   2. git add .")
    print('   3. git commit -m "migrate: move existing writeups into OS subfolders"')
    print("   4. git push")


if __name__ == "__main__":
    migrate()
