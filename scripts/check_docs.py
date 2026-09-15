#!/usr/bin/env python3
"""
Documentation checks — structural integrity of the mkdocs site under docs/.

Run from the repo root before merging to master:

    python scripts/check_docs.py

Four checks, all of which have caught real defects:

1. LINKS + ANCHORS — every relative markdown link resolves to a file that
   exists, and every `#fragment` resolves to a heading in the target page.
   Honours explicit attr_list ids (`### Core Credit {#core-credit}`).

2. NAV COVERAGE — mkdocs.yml nav and docs/ agree exactly. A page on disk but
   not in the nav is unreachable; a nav entry with no file 404s.

3. DEMO-DATA BOUNDARY — demo-tenant identifiers (personas, seeded order and
   part numbers, the demo password) must not appear in reference prose.

   They are legitimate and useful inside a Demo-labelled admonition
   (`!!! example "Demo: ..."`), inside a code fence, and anywhere under
   training/ or getting-started/, which teach against the demo tenant on
   purpose. They are NOT legitimate in body prose, where a real user reads
   "Delphi Fuel Systems is in tightened state" as a fact about their own
   plant. This checks the boundary, not the presence.

   If you add a demo illustration, put it in an admonition whose title
   contains "Demo".

4. PERMISSION NAMES — every `codename` the docs quote in backticks exists in
   the Django permission registry. Six invented names were found the first
   time this ran, including one file that listed `approve_document` as an
   action permission and then said, eighty lines later, that document
   approvals have no dedicated `approve_*` permission.

   The registry is derived from the app registry rather than the Permission
   table, so this needs `django.setup()` but no database. If Django cannot be
   imported the check is skipped with a note rather than failing, so the other
   three still run anywhere.

Exit codes:
    0 — all checks pass
    1 — one or more violations (printed with file and line)
"""
import io
import os
import re
import sys

DOCS = 'docs'
MKDOCS = 'mkdocs.yml'

# --- 3. demo-data boundary -------------------------------------------------

DEMO_ALLOWED_PREFIXES = ('training/', 'getting-started/')

DEMO_PATTERNS = {
    'demo credential': r'demo123',
    'demo account': r'@demo\.ambac\.com',
    'demo order': r'\bORD-2024-\d+',
    'demo work order': r'\bWO-(?:2024-\d+|QA-INSPECT|SHOWCASE)',
    'demo part': r'\bINJ-(?:0042|0038|QA-INSPECT)-\d+',
    'demo disposition': r'\bDISP-(?:QAI|TRAIN|ASSESS)-',
    'demo QR': r'\bQR-00(?:42|38)-\d+',
    'demo CAPA': r'\bCAPA-(?:2024-\d+|TRAIN|ASSESS)',
    'demo assessment': r'\bASSESS-[A-Z]+-\d+',
    'demo persona': (r'\b(?:Mike Rodriguez|Sarah Chen|Maria Santos'
                     r'|Jennifer Walsh|Alex Demo|Tom Bradley|Lisa Park)\b'),
    'demo company': r'\b(?:Midwest Fleet|Delphi Fuel Systems|Northern Trucking)\b',
}

ADMONITION = re.compile(r'^\s*(?:!!!|\?\?\?)')


def _read(path):
    return io.open(path, encoding='utf-8', errors='ignore').read()


def _md_files():
    out = {}
    for root, _dirs, files in os.walk(DOCS):
        for name in sorted(files):
            if name.endswith('.md'):
                path = os.path.join(root, name).replace(os.sep, '/')
                out[path] = _read(path)
    return out


def _slug(text):
    text = re.sub(r'[`*_]', '', text).strip().lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'\s+', '-', text)


def _anchors(body):
    found = set()
    for m in re.finditer(r'^#{1,6}\s+(.+)$', body, re.M):
        heading = m.group(1)
        explicit = re.search(r'\{#([\w-]+)\}', heading)
        if explicit:
            found.add(explicit.group(1))
            heading = heading[:explicit.start()]
        found.add(_slug(heading))
    return found


def check_links(files):
    anchors = {p: _anchors(b) for p, b in files.items()}
    bad = 0
    for path, body in files.items():
        for m in re.finditer(r'\[[^\]]*\]\(([^)#\s]*)(#[^)\s]*)?\)', body):
            target, frag = m.group(1), m.group(2)
            if target.startswith(('http', 'mailto:')):
                continue
            if not target:
                dest = path
            else:
                dest = os.path.normpath(
                    os.path.join(os.path.dirname(path), target)
                ).replace(os.sep, '/')
            if dest not in files:
                if not os.path.exists(dest):
                    line = body[:m.start()].count('\n') + 1
                    print('DEAD LINK    %s:%d -> %s' % (path, line, target))
                    bad += 1
                continue
            if frag and frag[1:] not in anchors[dest]:
                line = body[:m.start()].count('\n') + 1
                print('DEAD ANCHOR  %s:%d -> %s%s' % (path, line, target, frag))
                bad += 1
    return bad


def check_nav(files):
    nav = set(re.findall(r':\s*([\w./-]+\.md)\s*$', _read(MKDOCS), re.M))
    disk = {p[len(DOCS) + 1:] for p in files}
    bad = 0
    for missing in sorted(disk - nav):
        print('NOT IN NAV   %s (unreachable)' % missing)
        bad += 1
    for orphan in sorted(nav - disk):
        print('NAV ORPHAN   %s (no such file)' % orphan)
        bad += 1
    return bad


def _demo_exempt(lines):
    """True for each line inside a Demo-labelled admonition or a code fence."""
    out = [False] * len(lines)
    inside = False
    fenced = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith('```'):
            fenced = not fenced
            out[i] = True
            continue
        if fenced:
            out[i] = True
            continue
        if ADMONITION.match(line):
            inside = 'demo' in line.lower()
            out[i] = inside
            continue
        if inside:
            # Admonition content is indented; blank lines don't end the block.
            if line.strip() == '' or line.startswith(('    ', '\t')):
                out[i] = True
            else:
                inside = False
    return out


def check_demo_data(files):
    bad = 0
    for path, body in sorted(files.items()):
        rel = path[len(DOCS) + 1:]
        if rel.startswith(DEMO_ALLOWED_PREFIXES):
            continue
        lines = body.splitlines()
        exempt = _demo_exempt(lines)
        for i, line in enumerate(lines):
            if exempt[i]:
                continue
            for label, pattern in DEMO_PATTERNS.items():
                for m in re.finditer(pattern, line):
                    print('DEMO IN PROSE %s:%d  %s: %s'
                          % (rel, i + 1, label, m.group(0)))
                    bad += 1
    return bad


# --- 4. permission names ---------------------------------------------------

DJANGO_PROJECT = 'PartsTracker'
DJANGO_SETTINGS = 'PartsTrackerApp.settings'

# Backticked tokens that look like permission codenames but are not, and so
# would otherwise be reported forever.
NON_PERMISSIONS = {
    # An API field on the revision endpoint ("change_justification is required
    # when creating a revision"), quoted in the error text the docs reproduce.
    'change_justification',
    # Named by docs that state explicitly it does not exist. Keep them listed:
    # saying "there is no X permission" is useful and should not trip a check.
    'change_sso_settings',
    'view_analytics',
}

PERM_TOKEN = re.compile(
    r'`((?:view|add|change|delete|approve|close|respond|export'
    r'|manage|override|void|record|sign|verify)_[a-z_]+)`'
)


def _registry():
    """Every valid permission codename, or None if Django is unavailable.

    Derived from the model metadata rather than the Permission table -- the
    two were verified identical, and this way the check needs no database.
    """
    project = os.path.abspath(DJANGO_PROJECT)
    if not os.path.isdir(project):
        return None
    sys.path.insert(0, project)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', DJANGO_SETTINGS)
    try:
        import logging
        logging.disable(logging.CRITICAL)  # app-ready hooks are chatty
        import django
        django.setup()
        from django.apps import apps
    except Exception:
        return None
    finally:
        logging.disable(logging.NOTSET)
    codenames = set()
    for model in apps.get_models():
        meta = model._meta
        for action in meta.default_permissions:
            codenames.add('%s_%s' % (action, meta.model_name))
        for codename, _label in meta.permissions:
            codenames.add(codename)
    return codenames


def check_permissions(files):
    valid = _registry()
    if valid is None:
        print('NOTE  permission check skipped (Django not importable here)')
        return 0
    bad = 0
    for path, body in sorted(files.items()):
        for i, line in enumerate(body.splitlines(), 1):
            for m in PERM_TOKEN.finditer(line):
                codename = m.group(1)
                if codename in valid or codename in NON_PERMISSIONS:
                    continue
                print('NO SUCH PERM %s:%d  %s'
                      % (path[len(DOCS) + 1:], i, codename))
                bad += 1
    return bad


def main():
    if not os.path.isdir(DOCS):
        print('error: run from the repo root (no %s/ here)' % DOCS)
        return 1
    files = _md_files()
    total = 0
    total += check_links(files)
    total += check_nav(files)
    total += check_demo_data(files)
    total += check_permissions(files)
    print('\n%d markdown files checked, %d problem(s)' % (len(files), total))
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
