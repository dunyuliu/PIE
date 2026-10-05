#! /usr/bin/env python3
"""
Generates docs/user/parameters.md's parameter-reference list from
pie/globalvar.py -- the one module every entry point (pie.main, the
scheduler, robust_runner) imports its solver constants and physical bounds
from. This reference cannot describe a knob that does not exist, or drift
silently on a default that changed underneath it.

WHAT IS EXTRACTED, and what is deliberately not.
  pie/globalvar.py is a flat module, not a defaults class: it mixes CLI-
  derived state (CMR2, light_element, ...; these come from sys.argv, not a
  default, so they are NOT extracted -- they're documented by hand in
  Running a Case instead), per-run output paths, and a handful of genuine
  solver constants and physical bounds a user might reasonably want to
  know about or override. Only the latter are extracted, by an explicit
  ALLOWED_NAMES allowlist below (the opposite choice from an excludelist --
  a new unrelated module-level assignment in globalvar.py does not silently
  become a "parameter" on this page just by existing).

  For each allowed name, this script records its literal default value and
  a short NOTE built only from:
    - the comment on the assignment's own line, and
    - a contiguous comment block immediately above it (stopping at a
      blank line or a non-comment line),
  excluding any note that trips the same internal-reference markers used
  to keep developer-only commentary (board item numbers, commit SHAs,
  agent names) out of this public-facing page. A filtered note is PRINTED
  at generation time -- never silently dropped.

Usage:
  python3 docs/user/gen_params.py            # regenerate parameters.md in place
  python3 docs/user/gen_params.py --check     # exit 1 if the committed page
                                               # would change; write nothing
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(ROOT, 'pie', 'globalvar.py')
TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parameters.md')

BEGIN = ('<!-- BEGIN PARAMETER REFERENCE (generated from pie/globalvar.py '
          'by docs/user/gen_params.py; do not edit by hand) -->')
END = '<!-- END PARAMETER REFERENCE -->'

# Only these module-level names become reference entries (see docstring).
ALLOWED_NAMES = {
    'dr', 'max_Si_Steinbruegge2020', 'max_Si_Edmund2022',
    'xtol', 'ftol', 'maxit',
    'MFeS', 'MFeSi', 'MFe',
}

# Same class of internal reference EQdyna's gen_params.py refuses in a
# user-facing document, applied here: a comment citing a board item, a
# commit SHA, or an internal agent name is a developer-rationale citation,
# not user content.
INTERNAL_MARKERS = [
    re.compile(r'\bPR\s*#\d+|\(#\d+\)'),
    re.compile(r'\brules?\s+\d+[a-z]?\b', re.I),
    re.compile(r'pathway_forward|board item|\bitem\s+\d+', re.I),
    re.compile(r'\b(mira|iris|lars|kai|haruto|nadia|sophia|zofia|victor|'
               r'wei-lin|wei lin|dunyu-liu|anya|marta|priya)\b', re.I),
    re.compile(r'(?<![\w/.-])(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])'
               r'(?:[0-9a-f]{7,12}|[0-9a-f]{40})(?![\w/.-])'),
    re.compile(r'\.(py|f90|sh|md|yml|txt):\d+'),
]


def _is_internal(line):
    return any(rx.search(line) for rx in INTERNAL_MARKERS)


def _strip_comment(line):
    return line.strip().lstrip('#').strip()


def _leading_comment_block(lines, start):
    """Contiguous comment-only lines immediately above `start` (0-indexed),
    in reading order, stopping at a blank or non-comment line."""
    out = []
    i = start - 1
    while i >= 0 and lines[i].strip().startswith('#'):
        out.append(lines[i])
        i -= 1
    out.reverse()
    return out


def extract(source_text=None):
    """Returns (rows, filtered_log).
    rows -- [(lineno, name, default_repr, note)] in source order.
    """
    text = source_text if source_text is not None else open(SOURCE).read()
    lines = text.splitlines()
    tree = ast.parse(text)

    rows = []
    filtered_log = []

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            names = [target.id]
        else:
            continue  # tuple/subscript targets: none of ALLOWED_NAMES use these

        if names[0] not in ALLOWED_NAMES:
            continue
        name = names[0]

        lineno0, endlineno0 = node.lineno - 1, node.end_lineno - 1
        inline = ''
        if '#' in lines[endlineno0]:
            inline = lines[endlineno0].split('#', 1)[1].strip()

        lead = _leading_comment_block(lines, lineno0)
        owner = '%s (pie/globalvar.py line %d)' % (name, node.lineno)

        try:
            default = repr(ast.literal_eval(node.value))
        except Exception:
            default = ast.get_source_segment(text, node.value)

        note_parts = []
        lead_texts = [_strip_comment(l) for l in lead]
        lead_texts = [t for t in lead_texts if t]
        if lead_texts:
            joined = ' '.join(lead_texts)
            if _is_internal(joined):
                filtered_log.append('%s: dropped leading block %r' % (owner, joined))
            else:
                note_parts.append(joined)
        if inline:
            if _is_internal(inline):
                filtered_log.append('%s: filtered inline %r' % (owner, inline))
            else:
                note_parts.append(inline)

        note = ' '.join(note_parts)
        if _is_internal(note):
            raise RuntimeError(
                'gen_params: %s note still trips an internal-reference marker '
                'after filtering -- the joiner has a bug, refusing to emit a '
                'user-facing doc with it: %r' % (owner, note))
        rows.append((node.lineno, name, default, note))

    rows.sort(key=lambda r: r[0])
    return rows, filtered_log


def render(rows, filtered_log):
    out = [BEGIN, '',
           'Every entry below is a module-level constant in `pie/globalvar.py`, '
           'read by the present-day solver (`pie/shootp.py`, `pie/driverp.py`) '
           'and the Newton iteration it drives. These are solver constants and '
           'physical bounds, not per-run inputs -- CMR2, CMC, the light-element '
           'choice, the liquidus equation, and `chi_Si_icb` are supplied on the '
           'command line instead; see [Running a Case](running-a-case.md).', '']
    for (_, name, default, note) in rows:
        header = '* **`%s`** -- default `%s`' % (name, default)
        out.append(header)
        if note:
            out += ['', '  ' + note]
        out.append('')
    out.append(END)
    return '\n'.join(out)


def check_or_update(update):
    if not os.path.exists(TARGET):
        return ['docs/user/parameters.md does not exist (run without --check to create it)']
    s = open(TARGET, errors='replace').read()
    if BEGIN not in s or END not in s:
        return ['docs/user/parameters.md has no generated parameter-reference '
                'section (run without --check to insert one)']
    head, rest = s.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    current = BEGIN + rest.split(END, 1)[0] + END
    rows, filtered_log = extract()
    for f in filtered_log:
        print('  filtered: %s' % f)
    wanted = render(rows, filtered_log)
    if current == wanted:
        return []
    if update:
        open(TARGET, 'w').write(head + wanted + tail)
        print('  docs/user/parameters.md parameter reference regenerated '
              '(%d entries)' % len(rows))
        return []
    return ["docs/user/parameters.md's parameter reference no longer matches "
            "pie/globalvar.py -- rerun 'python3 docs/user/gen_params.py'"]


def main():
    check = '--check' in sys.argv
    problems = check_or_update(update=not check)
    if problems:
        print('FAIL gen_params:')
        for p in problems:
            print(' -', p)
        return 1
    print('SUCCESS gen_params' + (' (check only, no write)' if check else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
