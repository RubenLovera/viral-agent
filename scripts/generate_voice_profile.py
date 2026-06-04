#!/usr/bin/env python3
"""Generate voice_profile.json by analyzing Ruben's iMessage samples via Gemini API.

Input:  /tmp/ruben_messages.txt  (messages separated by ---)
Output: ~/VIRAL/data/voice_profile.json

Run locally — uses GEMINI_API_KEY from ~/VIRAL/.env or env.
"""
import json
import os
import re
import sys
from pathlib import Path

from google import genai

MESSAGES_FILE = Path('/tmp/ruben_messages.txt')
OUT_FILE = Path.home() / 'VIRAL/data/voice_profile.json'
MODEL = 'gemini-2.0-flash'

# Load ~/VIRAL/.env if present
_env_file = Path(__file__).parent.parent / '.env'
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

PROMPT_TEMPLATE = """\
You are a linguistic analyst specializing in personal communication styles.
Analyze these {count} authentic text messages written by one person and extract \
a structured voice profile capturing how they naturally communicate.

Look for consistent habits across ALL messages, not just a few examples.

Return ONLY valid JSON (no markdown fences, no explanation) with this exact structure:
{{
  "greetings": ["opening phrases/words they actually use"],
  "closings": ["closing phrases/words they actually use"],
  "emoji_patterns": {{
    "frequent": ["emojis used often, ordered by frequency"],
    "contextual": {{
      "excitement": ["emojis used when excited"],
      "affirmation": ["emojis used when agreeing/approving"],
      "casual": ["emojis used in casual context"]
    }}
  }},
  "language_mix": {{
    "english_ratio": 0.0,
    "spanish_ratio": 0.0,
    "code_switching_patterns": "describe when/how they switch languages"
  }},
  "formality_level": "casual|semi-formal|formal — pick one and explain briefly",
  "filler_words": ["words/phrases used as fillers or transitions"],
  "tone_descriptors": ["5-8 adjectives describing their style"],
  "sample_phrases": ["10 representative short phrases that capture their voice exactly as written"],
  "sentence_length": "short|medium|long",
  "punctuation_style": "describe their punctuation habits",
  "notes": "other distinctive patterns useful for message personalization"
}}

Messages to analyze:
---
{messages}
"""


def main():
    if not MESSAGES_FILE.exists():
        print(f'ERROR: {MESSAGES_FILE} not found. Run extract_voice_profile.py first.')
        sys.exit(1)

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print('ERROR: GEMINI_API_KEY not set. Add it to ~/VIRAL/.env or export it.')
        sys.exit(1)

    messages_text = MESSAGES_FILE.read_text(encoding='utf-8')
    msg_count = messages_text.count('---') + 1
    print(f'Analyzing {msg_count} messages with {MODEL}...')

    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(count=msg_count, messages=messages_text)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    raw = response.text.strip()
    # Strip markdown code fences if model wrapped it
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    profile = json.loads(raw)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f'\n✅ Voice profile saved → {OUT_FILE}')
    print('\nProfile summary:')
    print(f'  Formality: {profile.get("formality_level", "?")}')
    lm = profile.get('language_mix', {})
    print(f'  Language mix: EN {lm.get("english_ratio", 0):.0%} / ES {lm.get("spanish_ratio", 0):.0%}')
    print(f'  Tone: {", ".join(profile.get("tone_descriptors", [])[:4])}')
    top_emojis = profile.get('emoji_patterns', {}).get('frequent', [])
    print(f'  Top emojis: {" ".join(top_emojis[:6])}')
    print('  Sample phrases:')
    for phrase in profile.get('sample_phrases', [])[:3]:
        print(f'    • {phrase}')


if __name__ == '__main__':
    main()
