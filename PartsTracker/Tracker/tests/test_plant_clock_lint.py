"""No new "today" on the wrong clock.

`timezone.now().date()` is the UTC day and `date.today()` the server's; a plant works on
`Tenant.default_timezone`. Every evening in a zone behind UTC they disagree — lots dated
tomorrow, certificates expired hours early, CAPAs overdue at 7 pm. Use
`Tracker.services.core.clock.tenant_today(tenant)` (or `tenant_now`).

This fails on any such call outside tests, migrations and the seed / demo-data commands
(whose relative sample dates don't care). A site that genuinely means the UTC or server
day goes in ALLOWED, with the reason.
"""
import os
import re

from django.test import SimpleTestCase

PATTERN = re.compile(r'timezone\.now\(\)\.date\(\)|(?<![\w.])date\.today\(\)|datetime\.date\.today\(\)'
                     r'|timezone\.localdate\(\)')

# "path/relative/to/Tracker.py:<text of the line, stripped>" -> why it's allowed.
ALLOWED: dict = {
    # Upload paths: the date only names the storage folder a file lands in — nobody
    # reads it as a date and no rule compares it.
    "models/core.py:today = date.today().isoformat()": "upload folder name",
    "models/qms.py:today = date.today().isoformat()": "upload folder name",
}


class PlantClockLintTests(SimpleTestCase):
    def test_no_utc_or_server_day_outside_tests_and_seeds(self):
        root = os.path.join(os.path.dirname(__file__), '..')
        found = []
        for dirpath, _, files in os.walk(root):
            rel_dir = os.path.relpath(dirpath, root)
            if any(part in rel_dir.split(os.sep) for part in ('tests', 'migrations', '__pycache__')) \
                    or rel_dir.startswith(os.path.join('management', 'commands')):
                continue
            for fn in files:
                if not fn.endswith('.py'):
                    continue
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root).replace(os.sep, '/')
                if rel == 'services/core/clock.py':
                    continue  # the helper, whose docstring names what it replaces
                with open(path, encoding='utf-8') as fh:
                    for n, line in enumerate(fh, start=1):
                        code = line.split('#', 1)[0]
                        if PATTERN.search(code) and f"{rel}:{line.strip()}" not in ALLOWED:
                            found.append(f"{rel}:{n}: {line.strip()}")
        self.assertFalse(found, (
            "Today on the UTC / server clock. Use Tracker.services.core.clock."
            "tenant_today(tenant) — the plant's day — or add the line to ALLOWED with why:\n  "
            + "\n  ".join(found)))
