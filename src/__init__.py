"""PIE source directory (board item 28e: package marker only).

The modules here still import each other as bare top-level names and must be
loaded with `src/` itself on `sys.path` -- `cd src && python main.py ...`
(README), testsys/conftest.py's `import_src()`, and util/plot|run's
`sys.path` shims all do this. Do NOT import them as `src.<module>`: their
bare sibling imports (`from globalvar import ...`) do not resolve under that
name, and mixing both forms would load each module twice. Switching to
package-relative imports requires changing all three entry paths together
(e.g. `python -m`), which is deferred as a follow-up to item 28(e).
"""
