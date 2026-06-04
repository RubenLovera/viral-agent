#!/usr/bin/env python3
"""
Send personalized iMessages to SkinQueens Batch 2 candidates.
Usage: python3 tools/send-imessages.py [--dry-run] [--start N]
"""
import json
import subprocess
import time
import sys
import os
import tempfile
from pathlib import Path

INVITE_LINK = "https://app.sideshift.app/program-invite/29eb9611-7de8-4fd3-ab30-51f675f96c87"
CREATOR_KIT = "https://obsidian-beauty-f48.notion.site/SkinQueens-Creator-Kit-362ffc8b9a2080569cfdc60b93f807c2"
DELAY_SECONDS = 3

CREATORS = [
    ("Mackenzi", "+19038055445"),
    ("Tina", "+19545312263"),
    ("Alexa", "+17273088925"),
    ("Lily", "+12488021234"),
    ("Lexi", "+16266898016"),
    ("Chandni", "+17033713467"),
    ("Mckenzie", "+16159691767"),
    ("Taylor", "+18324172356"),
    ("Gracie", "+13869568297"),
    ("Natalie", "+16179552445"),
    ("Javeria", "+16475699131"),
    ("Ashley", "+12677184983"),
    ("Alina", "+17272209970"),
    ("Nina", "+12672544445"),
    ("Abby", "+13038037568"),
    ("Madison", "+17279023568"),
    ("Kavya", "+14793191630"),
    ("Mia", "+13137134614"),
    ("Aleaya", "+15623602099"),
    ("Jada", "+13082497477"),
    ("Haily", "+14754224909"),
    ("Bryana", "+14147084175"),
    ("Karissa", "+16418710726"),
    ("Emmanuela", "+17204722679"),
    ("Ava", "+16473279227"),
    ("Christina", "+12768065608"),
    ("Keytonya", "+13344985599"),
    ("Kayla", "+14136873168"),
    ("Kimora", "+14438420071"),
    ("Megan", "+12766186333"),
    ("Kathryn", "+16269776696"),
    ("Katie", "+19312131631"),
    ("Malaika", "+15072191447"),
    ("Aaniyah", "+16106984893"),
    ("Danielle", "+14079123073"),
    ("Janiya", "+13148852723"),
    ("Gia", "+14243944364"),
    ("Susan", "+19292536600"),
    ("Briana", "+12404447929"),
    ("Cassandra", "+15148176083"),
    ("Audrey", "+13057905339"),
    ("Noha", "+12064209953"),
    ("Isabella", "+19519634416"),
    ("Jazmyne", "+15617291664"),
    ("Dulce", "+19088090649"),
    ("Lauren", "+17033043469"),
    ("Naysa", "+19418554005"),
    ("Rachel", "+15613066338"),
    ("Grace", "+15308308289"),
    ("Barbara", "+19292507248"),
    ("Rujala", "+16506807299"),
    ("Isabella", "+13218065707"),
    ("Carrie", "+13869166331"),
    ("Nasia", "+14438212205"),
    ("Tabbie", "+14342351868"),
    ("Nicole", "+14169188221"),
    ("Gigi", "+19254887421"),
    ("Sara", "+19493150649"),
    ("Brianna", "+13369299767"),
    ("Hailey", "+17035477744"),
    ("My", "+14803345033"),
]


def load_active_phones() -> set[str]:
    """Return set of phone numbers already active in SideShift (sideshift=True in creators DB)."""
    db_path = Path(__file__).parent.parent / 'creators' / 'creators.json'
    if not db_path.exists():
        return set()
    try:
        data = json.loads(db_path.read_text())
        creators = data.get('creators', [])
        return {
            c['phone'].strip()
            for c in creators
            if c.get('sideshift') is True and c.get('phone') and not c.get('archived') and not c.get('blacklisted')
        }
    except Exception as e:
        print(f'⚠️  Could not load creators DB: {e}')
        return set()


def build_message(name):
    return (
        f"Hi {name},\n\n"
        "My name is Ruben Lovera — I'm a UGC Manager at The Viral App. "
        "I found your contact through our creator database, as you've previously collaborated with TVA, "
        "and I genuinely think you'd be a great fit for one of our new clients.\n\n"
        "Please join the SkinQueens campaign here as soon as you receive this communication:\n\n"
        f"{INVITE_LINK}\n\n"
        "Once you're in, I also put together a Creator Kit with an intro video from me, "
        "the full content brief, brand assets, and a step-by-step onboarding guide so you "
        "can get fully up to speed before our call:\n\n"
        "Creator Kit:\n\n"
        f"{CREATOR_KIT}\n\n"
        "If you'd like to chat before getting started, you can also book a call with me here:\n\n"
        "https://calendar.app.google/yHuW8GUYoURd8jy99\n\n"
        "That said, the Creator Kit is pretty complete — everything you need to join the campaign "
        "and start creating is already in there.\n\n"
        "If you have any questions, feel free to reply here. See you soon!\n\n"
        "Best regards,\n\n"
        "Ruben Lovera\n"
        "UGC Manager — The Viral App\n"
        "ruben@theviralapp.com"
    )


def send_imessage(name, phone, message, dry_run=False):
    if dry_run:
        print(f"  [DRY RUN] Would send to {phone}")
        return True, ""

    # Build AppleScript with proper line breaks
    lines = message.split("\n")
    as_parts = []
    for i, line in enumerate(lines):
        escaped = line.replace('\\', '\\\\').replace('"', '\\"')
        as_parts.append(f'"{escaped}"')

    msg_as = " & return & ".join(as_parts)

    script = f'''tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "{phone}" of targetService
    set theMessage to {msg_as}
    send theMessage to targetBuddy
end tell'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False) as f:
        f.write(script)
        fname = f.name

    try:
        result = subprocess.run(
            ['osascript', fname],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        os.unlink(fname)


def main():
    dry_run = "--dry-run" in sys.argv
    start_idx = 0
    for arg in sys.argv[1:]:
        if arg.startswith("--start="):
            start_idx = int(arg.split("=")[1]) - 1

    if dry_run:
        print("DRY RUN — no messages will be sent\n")

    active_phones = load_active_phones()
    if active_phones:
        print(f"Guard: {len(active_phones)} phones already active in SideShift — will skip them\n")

    total = len(CREATORS)
    sent = 0
    skipped = []
    failed = []

    for i, (name, phone) in enumerate(CREATORS[start_idx:], start=start_idx + 1):
        if phone.strip() in active_phones:
            print(f"[{i}/{total}] {name} ({phone}) — SKIP (already in SideShift)")
            skipped.append((name, phone))
            continue
        msg = build_message(name)
        print(f"[{i}/{total}] {name} ({phone})...", end=" ", flush=True)

        success, err = send_imessage(name, phone, msg, dry_run=dry_run)

        if success:
            print("✓")
            sent += 1
        else:
            print(f"✗  {err}")
            failed.append((name, phone, err))

        if i < total and not dry_run:
            time.sleep(DELAY_SECONDS)

    print(f"\n{'='*40}")
    print(f"Sent: {sent}/{total - start_idx - len(skipped)}")
    if skipped:
        print(f"Skipped — already in SideShift ({len(skipped)}):")
        for name, phone in skipped:
            print(f"  {name} {phone}")
    if failed:
        print(f"Failed ({len(failed)}):")
        for name, phone, err in failed:
            print(f"  {name} {phone} — {err}")


if __name__ == "__main__":
    main()
