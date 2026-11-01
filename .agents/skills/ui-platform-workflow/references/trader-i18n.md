# Trader VI/EN copy changes

Use for localization/copy changes in Naqex Trader. Resolve the affected component
and its existing copy mechanism before editing; this task does not justify an
i18n migration or a second catalog.

The shared system catalog is
[testing-copy.json](../../../../projects/trader/foundation_v2/web/src/testing-copy.json),
with status families in
[testing-enums.json](../../../../projects/trader/foundation_v2/web/src/testing-enums.json).
Keep each testing-copy entry on one line, CRLF, no duplicate keys. Shared copy
has one writer during parallel work; give that owner proposed keys/values.
Preserve interpolation names in both locales and in a templated key. The
[focused copy test](../../../../projects/trader/foundation_v2/web/tests/testingCopy.test.mjs)
checks locale coverage, interpolation contracts and displayed PnL spelling;
it does not detect every formatting or duplicate-key error after JSON parsing.

AI components also use local say(vi, english), selected from the existing
language state. Update both branches where the component already uses this
pattern. Do not assume testing-copy covers AI labels, accessible names, loading,
empty/error states or tooltips. Keep user text, provider IDs, configuration and
raw diagnostic detail intact.

Run from projects/trader/foundation_v2/web:

```powershell
node --test tests/testingCopy.test.mjs
```

Then verify the affected rendered state in VI and EN through the project QA
workflow. A catalog test does not establish browser or embedded-app parity.
For Paperclip translation/host synchronization, read the current
[integration guide](../../../../tooling/paperclip/README.md) and fork localization
contract linked there; the host and upstream namespaces have separate owners.
