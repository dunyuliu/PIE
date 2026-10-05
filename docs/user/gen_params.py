#! /usr/bin/env python3
"""
Generates two pages' generated sections from pie/globalvar.py -- the one
module every entry point (pie.main, the scheduler, robust_runner) imports
its solver constants, physical bounds, and error codes from:

  - docs/user/parameters.md's parameter-reference list (module-level
    solver constants and physical bounds).
  - docs/user/troubleshooting.md's per-radius error-code table (the
    ErrorCode enum and its ERROR_CODE_DESCRIPTIONS).

Both reference cannot describe a knob/code that does not exist, or drift
silently on a default/description that changed underneath them.

WHAT IS EXTRACTED, and what is deliberately not (parameters.md).
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

WHAT IS EXTRACTED (troubleshooting.md's error-code table).
  Every member of `pie/globalvar.py`'s `ErrorCode` enum, in declaration
  order, paired with its own entry in `ERROR_CODE_DESCRIPTIONS` (the same
  dict `pie/main.py`/README's own error-code table are built from, so this
  page's table cannot say something different from the code's own
  authoritative description). The enum member's source comment is NOT
  used for the generated "meaning" column -- several of those comments cite
  internal board items (filtered by the same INTERNAL_MARKERS check, logged
  not silently dropped, consistent with the parameters table above) and in
  any case `ERROR_CODE_DESCRIPTIONS` is the one description this codebase
  already treats as user-facing truth. Extra operational guidance (what to
  try when a code shows up) is hand-written prose in a clearly-labelled
  section below the generated table, not claimed as generated.

Usage:
  python3 docs/user/gen_params.py            # regenerate both pages in place
  python3 docs/user/gen_params.py --check     # exit 1 if either committed
                                               # page would change; write nothing
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(ROOT, 'pie', 'globalvar.py')
HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, 'parameters.md')
ERROR_TARGET = os.path.join(HERE, 'troubleshooting.md')

BEGIN = ('<!-- BEGIN PARAMETER REFERENCE (generated from pie/globalvar.py '
          'by docs/user/gen_params.py; do not edit by hand) -->')
END = '<!-- END PARAMETER REFERENCE -->'

ERROR_BEGIN = ('<!-- BEGIN ERROR CODES (generated from pie/globalvar.py\'s '
               'ErrorCode enum and ERROR_CODE_DESCRIPTIONS by '
               'docs/user/gen_params.py; do not edit by hand) -->')
ERROR_END = '<!-- END ERROR CODES -->'

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


def extract_error_codes(source_text=None):
    """Returns (rows, filtered_log).
    rows -- [(code, name, meaning)] in declaration order.
    """
    text = source_text if source_text is not None else open(SOURCE).read()
    lines = text.splitlines()
    tree = ast.parse(text)

    cls = next((n for n in tree.body
                if isinstance(n, ast.ClassDef) and n.name == 'ErrorCode'), None)
    if cls is None:
        raise RuntimeError("gen_params: pie/globalvar.py has no 'ErrorCode' class "
                            "-- troubleshooting.md's generated table has nothing to read")

    members = []  # (code, name, source comment, lineno)
    for node in cls.body:
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        code = ast.literal_eval(node.value)
        inline = ''
        line = lines[node.lineno - 1]
        if '#' in line:
            inline = line.split('#', 1)[1].strip()
        members.append((code, target.id, inline, node.lineno))

    desc_node = next((n for n in tree.body
                       if isinstance(n, ast.Assign)
                       and isinstance(n.targets[0], ast.Name)
                       and n.targets[0].id == 'ERROR_CODE_DESCRIPTIONS'), None)
    if desc_node is None or not isinstance(desc_node.value, ast.Dict):
        raise RuntimeError("gen_params: pie/globalvar.py has no "
                            "'ERROR_CODE_DESCRIPTIONS' dict literal -- "
                            "troubleshooting.md's generated table has nothing to read")

    descriptions = {}
    for key_node, val_node in zip(desc_node.value.keys, desc_node.value.values):
        key_name = ast.unparse(key_node).rsplit('.', 1)[-1]  # "ErrorCode.FOO" -> "FOO"
        descriptions[key_name] = ast.literal_eval(val_node)

    rows = []
    filtered_log = []
    for code, name, inline, lineno in members:
        owner = 'ErrorCode.%s (pie/globalvar.py line %d)' % (name, lineno)
        if name not in descriptions:
            raise RuntimeError(
                "gen_params: %s has no entry in ERROR_CODE_DESCRIPTIONS -- "
                "troubleshooting.md's generated table would silently omit it" % owner)
        meaning = descriptions[name]
        if _is_internal(meaning):
            raise RuntimeError(
                'gen_params: %s ERROR_CODE_DESCRIPTIONS entry trips an '
                'internal-reference marker -- refusing to emit a user-facing '
                'doc with it: %r' % (owner, meaning))
        if inline and _is_internal(inline):
            filtered_log.append('%s: source comment not used (cites internal '
                                 'reference): %r' % (owner, inline))
        rows.append((code, name, meaning))

    rows.sort(key=lambda r: r[0])
    return rows, filtered_log


def render_error_codes(rows, filtered_log):
    out = [ERROR_BEGIN, '',
           "PIE does not stop a sweep on the first failed radius: each trial "
           "inner-core radius either converges or fails with one of the codes "
           "below, recorded in that radius's row of `pMetaData_<chi_Si>.csv` "
           "(`error_code` column) and in `solverLog_<chi_Si>.jsonl`. See "
           "[Output Files](outputs.md) for the full row/column layout.", '',
           '| code | name | meaning |', '|-----:|------|---------|']
    for (code, name, meaning) in rows:
        out.append('| %d | `%s` | %s |' % (code, name, meaning))
    out += ['', ERROR_END]
    return '\n'.join(out)


def _check_or_update_page(target, begin, end, extract_fn, render_fn, label, update):
    if not os.path.exists(target):
        return ['%s does not exist (run without --check to create it)' % label]
    s = open(target, errors='replace').read()
    if begin not in s or end not in s:
        return ['%s has no generated section (run without --check to insert one)' % label]
    head, rest = s.split(begin, 1)
    _, tail = rest.split(end, 1)
    current = begin + rest.split(end, 1)[0] + end
    rows, filtered_log = extract_fn()
    for f in filtered_log:
        print('  filtered: %s' % f)
    wanted = render_fn(rows, filtered_log)
    if current == wanted:
        return []
    if update:
        open(target, 'w').write(head + wanted + tail)
        print('  %s regenerated (%d entries)' % (label, len(rows)))
        return []
    return ["%s no longer matches pie/globalvar.py -- rerun "
            "'python3 docs/user/gen_params.py'" % label]


def check_or_update(update):
    problems = []
    problems += _check_or_update_page(
        TARGET, BEGIN, END, extract, render,
        "docs/user/parameters.md's parameter reference", update)
    problems += _check_or_update_page(
        ERROR_TARGET, ERROR_BEGIN, ERROR_END, extract_error_codes, render_error_codes,
        "docs/user/troubleshooting.md's error-code table", update)
    return problems


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
