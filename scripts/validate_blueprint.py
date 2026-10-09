#!/usr/bin/env python3
"""Dependency-free structural checker. This does NOT test the Takshyra app."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md', 'AGENTS.md', 'CODEX_START_HERE.md', 'CODEX_MASTER_PROMPT.md',
    'docs/00_INDEX.md', 'docs/04_ARCHITECTURE.md', 'docs/05_DOMAIN_MODEL.md',
    'docs/06_STATES_AND_EVENTS.md', 'docs/08_DATA_QUALITY.md',
    'docs/11_POLICY_AND_ACTIONS.md', 'docs/17_SECURITY_AND_THREAT_MODEL.md',
    'docs/24_ROADMAP.md', 'docs/25_ACCEPTANCE_GATES.md',
    'docs/IMPLEMENTATION_STATUS.md', 'prompts/01_FOUNDATION.md',
    'prompts/10_HARDEN_RELEASE.md', '.env.example',
    'examples/events/sample_openlineage_event.json',
    'examples/scenarios/fault_catalog.json',
]
errors = []
for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        errors.append(f'MISSING: {rel}')

links = 0
for f in ROOT.rglob('*.md'):
    if 'archive' in f.parts:
        continue
    content = f.read_text(encoding='utf-8')
    for raw in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', content):
        link = raw.strip().split(' ', 1)[0].split('#')[0]
        if not link or re.match(r'^[a-z][a-z0-9+.-]*:', link, re.I) or link.startswith('/'):
            continue
        links += 1
        if not (f.parent / link).exists():
            errors.append(f'BROKEN LINK {f.relative_to(ROOT)} -> {raw}')
for f in (ROOT / 'examples').rglob('*.json'):
    try:
        json.loads(f.read_text(encoding='utf-8'))
    except (ValueError, UnicodeDecodeError) as exc:
        errors.append(f'INVALID JSON {f.relative_to(ROOT)}: {exc}')

if errors:
    print('BLUEPRINT VALIDATION FAILED')
    for e in errors:
        print(' -',e)
    sys.exit(1)
print(f'Blueprint check passed: {len(REQUIRED)} required files, {links} internal Markdown links, example JSON parsed.')
print('NOTE: Application features, Docker stack, cloud integration and production security are NOT tested.')
