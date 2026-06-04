#!/usr/bin/env python3
"""
Send compensation reminder iMessages to all SkinQueens Batch 2 candidates.
Usage: python3 tools/send-compensation-reminder.py [--dry-run] [--start N]
"""
import subprocess
import time
import sys
import os
import tempfile

INVITE_LINK = "https://app.sideshift.app/program-invite/29eb9611-7de8-4fd3-ab30-51f675f96c87"
CALENDAR_LINK = "https://calendar.app.google/yHuW8GUYoURd8jy99"
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


def build_message(name):
    return (
        f"Hi {name} — following up on my earlier message about the SkinQueens campaign.\n\n"
        "I wanted to share the full compensation breakdown so you know exactly what you're signing up for:\n\n"
        "COMPENSATION\n\n"
        "Model: Monthly Retainer + Performance Bonus\n\n"
        "Base Pay: $20/video — 30 videos/month\n"
        "60 posts total (30 TikTok + 30 Instagram) = $10/post\n"
        "→ $600/month guaranteed base\n\n"
        "Performance Bonuses:\n"
        "• $50 for any video that hits 50K+ views\n"
        "• $100 for any video that hits 100K+ views\n\n"
        "(Rates are negotiable based on your existing audience and content quality.)\n\n"
        "PAYMENT SCHEDULE\n\n"
        "Monthly — payouts on the 1st of each month for the prior month's content. "
        "Approval required before payout triggers.\n\n"
        "CREATOR REQUIREMENTS\n\n"
        "• TikTok + Instagram (both required)\n"
        "• 400+ views/video (ideal: 1,000+)\n"
        "• 3%+ engagement rate on TikTok\n"
        "• Niche: Skincare / Beauty / Wellness / Lifestyle\n"
        "• English-speaking, US-based preferred\n"
        "• Active posting history, real personal account\n"
        "• Response time: under 24 hours\n\n"
        "If this sounds like a fit, you can join the campaign here:\n\n"
        f"{INVITE_LINK}\n\n"
        "Any questions? Reply here or book a quick call:\n\n"
        f"{CALENDAR_LINK}\n\n"
        "Best,\n\n"
        "Ruben Lovera\n"
        "UGC Manager — The Viral App\n"
        "ruben@theviralapp.com"
    )


def send_imessage(name, phone, message, dry_run=False):
    if dry_run:
        print(f"  [DRY RUN] Would send to {phone}")
        return True, ""

    lines = message.split("\n")
    as_parts = []
    for line in lines:
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

    total = len(CREATORS)
    sent = 0
    failed = []

    for i, (name, phone) in enumerate(CREATORS[start_idx:], start=start_idx + 1):
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
    print(f"Sent: {sent}/{total - start_idx}")
    if failed:
        print(f"Failed ({len(failed)}):")
        for name, phone, err in failed:
            print(f"  {name} {phone} — {err}")


if __name__ == "__main__":
    main()
