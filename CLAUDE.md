# CLAUDE.md

## Contents

[Project Overview](#project-overview) · [Structure](#structure) ·
[Chart types](#chart-types) · [Run](#run) · [Test](#test) ·
[Lint & format](#lint--format) · [Type check](#type-check) ·
[Release](#release) · [Hooks](#hooks) · [Conventions](#conventions)

Per-type design detail — why each type is built the way it is, what the library
silently drops, and which calls were settled by rendering — lives in
[`docs/chart-types.md`](docs/chart-types.md). **Read it before adding or changing a
chart type.** This file carries the commands, the file map, and the rules that
apply to every type at once.

## Project Overview

`highcharts-studio` is a Streamlit application for building data visualizations
with Highcharts. Every chart is produced by the Highcharts for Python toolkit
(`highcharts-core`) — the app uses no native Streamlit charts.

## Structure

- `streamlit_app.py` — the Streamlit UI: data source (sample datasets or CSV
  upload), chart-type/column controls (pills for the Y series, falling back to
  `st.multiselect` on wide CSVs, plus the type-specific extra column selectors),
  caching, a KPI metric row (its third metric adapts to the chart type via
  `MARK_METRICS` — see [Chart types](#chart-types)), the render-mode selector
  (interactive iframe / static PNG), reading the active light/dark theme
  (`st.context.theme.type`) so charts render theme-aware, the chart embed, and a
  toggle revealing the generated Highcharts config (JS). The **no-plottable-columns
  gate** runs *below* the chart-type selectbox and is **type-aware**: xrange's
  start/end are coordinates and may be dates, and a date column is object dtype, so
  a canonical Gantt CSV has no numeric columns at all and a `select_dtypes("number")`
  gate would `st.stop()` it before the picker was drawn.
- `highcharts_builder.py` — pure, Streamlit-free helpers that turn a DataFrame into
  a Highcharts options `dict`, a `Chart`, and embeddable HTML or PNG bytes. It also
  owns the **diagnosis** of its own failures, so a message can't drift from the
  error it stands in for: `explain_export_failure()` (a failed PNG export — duck-typed
  on `exc.response.status_code` rather than importing `requests`, which this project
  never declares), `explain_tree_error()` (a malformed sunburst hierarchy),
  `explain_xrange_error()` (a start/end column pair that can place a bar on no axis,
  or two that disagree about which), and `explain_gauge_error()` (a dial whose max
  does not sit above its min — the one that reads no frame at all). And it owns the
  **options** the app's widgets offer, for the same reason: `coordinate_columns()`,
  `GAUGE_AGGREGATIONS`, and `gauge_dial()` — the last applying that rule to a widget's
  *value* rather than its options. Plus `count_marks()`, which returns how many marks
  `build_options` will draw, reusing the same drop predicates (or, for sunburst and
  xrange, the whole build) so the KPI can't drift from the chart. Independently
  importable and unit-testable.
- `sample_data.py` — pure (Streamlit-free) built-in sample datasets and the `SAMPLES`
  registry the app offers when no CSV is uploaded. Every sample leads with a
  **category column**, and that is load-bearing rather than tidy: the app opens on
  `line` with the first column as X, so a numeric first column would trip the x-in-y
  guard the moment the dataset was selected. Samples are designed as **mirrors** —
  e.g. the columnrange, arearange, bullet, variwide and dumbbell samples all carry
  two magnitude columns and mean something different by them, so reading them side by
  side shows that "two magnitude columns" is a data *shape*, not a chart. Per-sample
  rationale is in [`docs/chart-types.md`](docs/chart-types.md).
- `tests/test_smoke.py` — builder unit tests (every chart type, the missing-data and
  edge cases, the validation guards, and an end-to-end pass driving every supported
  type through `Chart.from_options` / `to_js_literal`) and `sample_data` unit tests,
  plus headless `AppTest` interaction tests. The AppTests find widgets by **label**,
  not by position — `_pick_sample(app, chart_type)` is the shared body of the seven
  `_pick_*_sample` helpers, each keeping its own name and its own argument for why
  that type needs a dedicated sample rather than the landing dataset.
- `tests/test_hooks.py` — unit tests for the `.claude/hooks/` scripts: the pure
  decision functions (`protected_reason`, `is_python_target`, `has_dirty_python`)
  plus a black-box check of the exit-code contract for `guard_paths.py` and
  `post_edit_py.py` (2 blocks, 0 allows) without spawning the toolchain.
- `tests/test_release.py` — unit tests for `.github/scripts/release.py` (CI's release
  tooling, the `test_hooks.py` sibling): the pure functions that read the current
  version, list the changelog's versions, slice a `CHANGELOG.md` section out
  *verbatim* (bounded by its two `## [` headings, blank lines stripped, the oldest
  running to EOF, a missing/empty section raising — and a heading with no trailing
  newline reading as *empty* rather than absent), and decide which versions sit above
  the latest-release watermark (empty
  on a no-bump push, the one new version after one bump, **both** oldest-first after
  two bumps in one push — the headline fix). It also pins `main()`'s CLI contract,
  since the workflow parses its stdout: `version` prints *only* the version, bad args
  exit 2 writing nothing to stdout — so a stray print can't corrupt a tag name.
- `tests/test_packaging.py` — unit tests guarding the licensing metadata: the
  `pyproject.toml` SPDX `license`/`license-files` fields, the `LICENSE` file's
  pristine MIT text (nothing appended, so GitHub detects it as MIT), and the `NOTICE`
  third-party notice naming both proprietary layers, kept in sync with the README
  `## License` section — plus the README's header badges and its `## Contents` table
  of contents (pinned to the real `##` headings), and `CHANGELOG.md`'s newest entry
  (pinned to `pyproject.toml`'s `version`). That last one closed the suite's own blind
  spot: `version` was the single packaging fact with *no second home*, so unlike every
  other it could neither drift nor be checked — and it duly went stale, five chart
  types shipping under `0.6.0` because nothing asked the number to move. It reads the
  files directly (no build step), the same mechanical-sync idea as
  `test_theme_colors_stay_in_sync_with_config`.
- `.streamlit/config.toml` — project Streamlit theme: the bundled **financial-dashboard**
  template, as a **single `[theme]`** (plus `[theme.sidebar]`). That shape is the decision,
  not an omission — defining both `[theme.light]` and `[theme.dark]` is what unlocks the
  in-app light/dark toggle, so a lone `[theme]` locks the app to one mode, here **dark**.
  Pinned by `test_app_theme_is_a_single_mode_with_no_light_dark_toggle`, because re-adding a
  subtable is a change nothing else would object to. The chart colors are themed separately
  (see Conventions) since charts render in an iframe the shell theme can't reach — and that
  includes the theme's own `chartCategoricalColors`, which Streamlit applies only to its own
  Vega/Plotly charts, of which this app has none.
- `.claude/settings.json` + `.claude/hooks/*.py` — committed Claude Code hooks that
  mirror the CI gates (see [Hooks](#hooks)). `.claude/settings.local.json` holds
  per-developer overrides and is gitignored.
- `pyproject.toml` — dependencies + the `dev` group, the project license (MIT, via the
  PEP 639 `license`/`license-files` fields), and the Ruff/ty config.
- `.github/workflows/ci.yml` — GitHub Actions: four jobs. Three gates (pytest, Ruff
  lint/format, ty) that `uv sync --locked` then run the same checks the hooks mirror,
  on every push to `main` and every PR; then a `release` job that `needs` all three,
  runs on a push to `main` only, and — under a job-scoped `contents: write` over the
  top-level read-only token — cuts a `v{version}` tag + GitHub release for **every**
  `CHANGELOG.md` version above the latest released one (the watermark). Releasing
  *every* untagged version rather than only the current one is load-bearing: two bumps
  in a single push (exactly how `0.10.0` and `0.11.0` both reached `main` before either
  was released) would otherwise leave the intermediate one un-released forever. Each
  version is tagged at the commit that declares it (HEAD for the current one, else the
  bump commit found by a `git log -S` pickaxe over `pyproject.toml` — which is why the
  checkout is `fetch-depth: 0`), notes are sliced out of `CHANGELOG.md` *verbatim*, and
  only the highest gets `--latest`. Idempotent, so it stays silent on pushes that don't
  bump. The top-level `concurrency` cancels superseded runs for **PRs only** — main
  pushes serialize instead, so a release job can't be killed mid-run and strand a
  pushed tag with no release.
- `.github/scripts/release.py` — the pure, stdlib-only reader CI's `release` job calls:
  `version`, `notes VERSION` (raising if the section is absent or empty so a release is
  never cut blank), and `to-release LATEST_TAG` (oldest-first; just the current version
  when the repo has no releases, so it never back-fills the deliberately release-less
  `0.1.0`–`0.6.0` tags). It only *reads* facts already pinned elsewhere by
  `test_changelog_documents_the_current_version` — which now reuses this module's
  `changelog_versions` rather than re-encoding the heading regex — so the notes
  cannot drift from the changelog. Pure logic + a thin `main()`, the `.claude/hooks/`
  pattern applied to release tooling; the impure parts stay in the workflow.
- `LICENSE` — MIT for this project's own code, kept *pristine* (no text appended) so
  GitHub's license detector classifies the repo as MIT rather than "Other".
- `NOTICE` — the third-party notice, split out of `LICENSE` for that reason: the two
  proprietary layers it renders with (Highcharts JS/the export server, and the
  `highcharts-core` wrapper) are separately licensed and not covered by the MIT grant.
  Both files are declared to packaging tools via `pyproject.toml`'s
  `license`/`license-files`; guarded against drift by `tests/test_packaging.py`.
- `CHANGELOG.md` — the release notes, newest first (Keep a Changelog format). Its top
  `## [x.y.z]` heading is `version`'s **second home**, so a bump that ships without
  notes fails the suite. Everything below `0.7.0` is *reconstructed from git history*,
  which is why the file says so.
- `docs/chart-types.md` — the per-type design record. See [Chart types](#chart-types).

## Chart types

29 supported types. The public API:

```python
# build_options() -> Chart.from_options() -> set container, in one call:
chart = make_chart(df, chart_type, x_col, y_cols, title=title)

# interactive: get_script_tags() + to_js_literal() wrapped as HTML for st.iframe
html = build_chart_html(df, chart_type, x_col, y_cols, height=height, title=title)

# static: rendered server-side to PNG bytes via the export server, for st.image
png = build_chart_png(df, chart_type, x_col, y_cols, title=title)

# ...and, when that raises, why — a build error, an unreachable server, or an HTTP
# answer (a 4xx rejection is worth saying out loud: the server is plainly reachable).
message = explain_export_failure(exc)  # plain markdown; the module stays Streamlit-free
```

All three take an optional `dark=` flag (default `False`) theming the chart chrome;
the app derives it from `st.context.theme.type` and threads it through the cached
renderers, so it is part of their cache key.

Beyond `x_col`/`y_cols`, a type may take one of **9 extra column kwargs**, and
which types share one is a deliberate claim — *a link is a link, but a goal is not a
high*. Reusing a kwarg leaves the cache layer untouched; a new one costs three
wrappers and three call sites, and that cost is paid whenever the **role** differs even
though the dtype and picker source match. It costs no test edit: `_FORWARDED` is
**derived** from the builders' signatures, so the cache-layer checks pick a new kwarg up
automatically — but the kwarg **table above** is pinned by name, so a new row here is not
optional.

| Kwarg | Control label | Types |
|---|---|---|
| `size_col` | Size (Z) | bubble |
| `target_col` | Target (to) / Manager (to) | sankey, dependencywheel, networkgraph, organization |
| `parent_col` | Parent | sunburst |
| `end_col` | End | xrange (a **coordinate**, may be a date) |
| `high_col` | High (top) | columnrange, arearange (a **magnitude**) |
| `title_col` | Title | organization |
| `goal_col` | Goal (target) | bullet (a **reference**, not a far end) |
| `width_col` | Width | variwide (the mark's **other dimension**) |
| `after_col` | After | dumbbell (the same quantity **later** — the one ORDERED pair) |

The gauge family (`solidgauge`, `gauge`) takes the two that are **not** column names:
`agg=` (one of `GAUGE_AGGREGATIONS`) and `dial=` an explicit `(min, max)`, derived from
the **readings** by `gauge_dial` when `None`. It is why `x_col` is `str | None` on all
five signatures — the family has no label channel, so every *other* type raises when
`x_col` is omitted. The two **unweighted node-link types** (`networkgraph`,
`organization`) are its mirror, taking an **empty** `y_cols`.

The KPI's third metric adapts by `MARK_METRICS` membership, so the KPI stays one branch
however many such types there are:

| Noun | Types |
|---|---|
| Cells / Tiles / Stages | heatmap · treemap · funnel, pyramid |
| Flows / Links / Reports | sankey, dependencywheel · networkgraph · organization |
| Boxes / Steps / Sectors | boxplot · waterfall · sunburst |
| Bars / Ranges / Points | xrange, variwide · columnrange · arearange |
| Measures / Changes | bullet · dumbbell |

Absent types report "Series plotted". Gauge's absence is a *decision*: its marks **are**
its series, so an entry would restate `len(y_cols)` — the can't-drift rule run backwards.

**Everything else about a type — its null policy, its `_themed` hooks, its module
resolution, its tooltip token, its guards, and the argument for each — is in
[`docs/chart-types.md`](docs/chart-types.md).** Those arguments are load-bearing, not
history: they are what the next type will be reasoned from.

## Run

```bash
uv run streamlit run streamlit_app.py
```

`.streamlit/config.toml` themes the shell and enables `runOnSave`, so saves
auto-rerun. When a stale chart is suspected, flush the four `@st.cache_data`
caches (the CSV loader plus the three chart renderers) with
`uv run streamlit cache clear`; verify config with `uv run streamlit config show`.
A *blank* chart is usually a network issue instead: interactive mode loads
Highcharts from the CDN (`code.highcharts.com`), static mode from the export
server (`export.highcharts.com`).

**Verify by rendering** (the methodology this project cites everywhere — a new type's
`_themed` hook, null/edge-case geometry, and light↔dark / interactive↔PNG parity are
*decided by looking*, never inferred from a base class): render one chart to a file with
`build_chart_html(df, type, …, dark=…)`, serve it over `http://localhost`
(`python3 -m http.server PORT --directory <dir>` in the background — `file://` is blocked
by the Claude-in-Chrome extension), then screenshot it in a browser in **both** themes.
Run scratchpad scripts with `PYTHONPATH=<repo> uv run python …` — the script's own dir,
not the cwd, is on `sys.path`, so a bare `import highcharts_builder` fails otherwise.

**Verify a new test by breaking the code** — the mutation counterpart to the above, and
the "a vacuous pass is worse than no test" rule turned into a procedure. Copy the source,
make the one edit the test claims to catch (delete the `_themed` hook, flip the null policy,
swap the two slots of a point array, revert a call site to positional), run *that test alone*,
restore, and diff to confirm the source came back byte-identical. A test that stays green is
pinning nothing. Read the failure, not just the exit code: a mutant caught by `SyntaxError`
rather than by the intended assertion is still a hole. It has already caught a dark-mode test
asserting `"#f1f5f9" in js` — that is `_DARK_CHROME["text"]`, which `_themed` writes to the
title, both axis labels and the tooltip on *every* dark chart, so the test passed with the hook
it existed for deleted outright.

## Test

```bash
uv run pytest
```

`tests/test_smoke.py` exercises the pure builder (`build_options`) parametrized across
every supported chart type, then drives the full app headless via Streamlit's `AppTest`
(switching controls, revealing the generated config, the KPI metric row, the wide-CSV
`st.multiselect` fallback, the render-mode selector's two modes, and the guard messages).
Per-type test inventory: [`docs/chart-types.md`](docs/chart-types.md).

Three **sweeps** are what cover a newly added type on the day it is added, rather than
whenever someone remembers — prefer extending a sweep to writing a per-type test:

- `test_no_supported_type_emits_a_non_finite_js_literal` — the value channel.
- `test_missing_or_non_finite_label_drops_the_row_in_every_type` — the label channel.
  The gauge family is *excluded* (keyed on `GAUGE_TYPES`): it would pass **vacuously**,
  reading as a pin on a policy the family deliberately does not have.
- `test_row_less_frame_draws_an_empty_chart_in_every_type`, with
  `test_count_marks_casts_every_mask_not_just_the_label_one` (which promotes warnings to
  errors — the only way the non-label casts are observable at all).

The app's **cache layer** is the part the ordinary AppTests barely reach.
`cached_chart_html`/`cached_chart_js` are covered only *indirectly*, and
`cached_chart_png` was for a long time executed by **nothing**: the AppTests stay on the
network-free interactive path. It is now pinned from **two** directions, because the
network and the wiring are separable and only the network was ever worth avoiding:

- **Statically**, by two `ast` tests that read `streamlit_app.py` as source: every cached
  wrapper forwards each column/policy argument under its **own** name, and all three call
  sites pass them by keyword. Static because `import streamlit_app` **executes the whole
  Streamlit script** — and because it catches what the keyword form cannot:
  `goal_col=high_col` type-checks, caches and renders the wrong column.
- **Dynamically**, by `test_app_static_png_mode_executes_the_cached_png_wrapper`, which
  selects Static PNG for real with `highcharts_builder.build_chart_png` monkeypatched to a
  recorder — so the wrapper actually runs and its forwarding is observed as **values**,
  while no export server is contacted. It clears the `@st.cache_data` caches on the way
  **out** as well as in: `monkeypatch` restores the function but not the cached *value*,
  so a stand-in PNG left behind would be served to any later Static PNG render, which
  would then pass without calling the builder at all.

The set of arguments both layers check is **derived** from the three builders' signatures
(`_forwarded_arguments`), not hand-listed, so a new kwarg is covered the day it is added.

## Lint & format

Ruff does both; config is in `pyproject.toml`. (CI and the hooks run these same
gates — see Structure's `ci.yml` bullet and Hooks.)

```bash
uv run ruff check --fix . && uv run ruff format .   # fix + format
uv run ruff check . && uv run ruff format --check .  # verify (as CI does)
```

## Type check

[ty](https://docs.astral.sh/ty/) (Astral's type checker, pinned in
`pyproject.toml`) needs the project venv to resolve imports, so run it through
`uv run`:

```bash
uv run ty check
```

A few highcharts-core stub mismatches (Optional `options`/`chart`,
`to_js_literal` typed `str | None`) are suppressed inline with
`# ty: ignore[rule]`, not by downgrading rules globally — so the rules still
catch the same problems in our own code.

## Release

Releases are cut by CI, never by hand. To ship a version, bump `version` in
`pyproject.toml` **and** add a matching `## [x.y.z]` section to `CHANGELOG.md`
(pinned together by `test_changelog_documents_the_current_version`, so a bump
without notes fails the suite). On the next push to `main`, the `release` job in
`ci.yml` cuts the annotated tag + GitHub release from that section — for every
version above the latest release, so two bumps in one push both ship — and marks
only the highest `--latest`. It is idempotent (a push that doesn't bump the
version cuts nothing), so do not tag or `gh release create` by hand.

Bumping `version` also makes the next `uv run` rewrite `uv.lock`'s own
`highcharts-studio` version line; commit that with the bump (the `guard_paths.py` hook
blocks *manual* `uv.lock` edits, but uv's own re-sync is expected, not a stray change).

## Hooks

`.claude/settings.json` wires three project hooks (committed; the per-developer
`.claude/settings.local.json` stays gitignored) that mirror the CI gates so edits
stay green before a push. Each is a stdlib-only Python script under
`.claude/hooks/`, run via `uv run --project "$CLAUDE_PROJECT_DIR" python …` so it
executes on the project's pinned 3.12 interpreter — the same one the tests use,
not the machine's system `python3` — and keeps its decision logic in a pure,
importable function that `tests/test_hooks.py` covers. The scripts are themselves held
to those gates: `ruff check .` and `uv run ty check` include `.claude/hooks/` (dot-dirs
aren't excluded), so the tooling that enforces the app enforces the hooks too.

- `post_edit_py.py` (PostToolUse on `Edit`/`Write`/`MultiEdit`) — on a `.py`
  edit, runs `ruff check --fix` + `ruff format` in place, then `ty check`; exits
  2 on type errors so the diagnostics feed back to fix. Mirrors the Ruff and ty
  gates. Gotcha: since this runs `ruff check --fix` after **every** `.py` edit, add a
  new import and its first use in the **same** edit (or the use first) — split across
  two edits, the fix prunes the not-yet-used import and the next `ty` pass fails on the
  now-undefined name. `Edit` replaces exactly one region, so when the import and its first
  use are far apart (an import block at the top, a use 200 lines down) *no* pair of Edits
  can satisfy this — land both with a single `Write`, or a one-shot script that does the
  two replacements in one pass.
- `pytest_stop.py` (Stop) — runs `uv run pytest` when the working tree has
  uncommitted `.py` changes (app, test, or the hook scripts under
  `.claude/hooks/`); exits 2 on a real failure (pytest exit 1/2) to feed the
  output back, treating a tooling/env failure as a no-op, with a
  `stop_hook_active` guard so it can't loop. Mirrors the test gate.
- `guard_paths.py` (PreToolUse) — blocks direct edits to `uv.lock`,
  `.streamlit/secrets.toml`, and `.git/` internals.

Adding or changing a hook triggers Claude Code's one-time hook-review prompt
before it runs.

## Conventions

Each rule below is stated with its mechanism. The per-type worked examples are in
[`docs/chart-types.md`](docs/chart-types.md) (see its Appendix for these same
conventions in their original, fully-enumerated form).

- When working with Python, invoke the relevant Astral skill (`/astral:uv`,
  `/astral:ty`, `/astral:ruff`) for uv, ty, and ruff to ensure best practices
  are followed.
- Keep chart-building logic (DataFrame → Highcharts) in `highcharts_builder.py`,
  free of Streamlit imports, so it stays unit-testable.
- Keep each hook's decision logic in a pure, importable function in `.claude/hooks/`
  (as the builder is), so `tests/test_hooks.py` can cover it without subprocesses; the
  `main()` wrapper handles the stdin/exit-code plumbing and any impure subprocess
  orchestration (ruff/ty/pytest/git). `.github/scripts/release.py` follows the same
  split for CI, tested by `tests/test_release.py`; both load their script by file path
  via `tests/conftest.py`'s `load_script`.
- The `release` job in `ci.yml` carries real bash, so validate edits before pushing:
  `shellcheck -s bash` the extracted `run:` block and structure-check the file with
  `uv run --with pyyaml` (neither is a project dep). Exercise the script on the
  interpreter the job uses:
  `uv run --no-project --python 3.12 python .github/scripts/release.py to-release vX.Y.Z`.
- **Adding a chart type falsifies prose nobody edited.** The docs are dense with
  uniqueness claims, and each is a claim about *every other type* — including ones that
  don't exist yet — so a new type can make a sentence false in a passage no diff touched,
  locally correct on both sides, with only the *pair* contradicting. Nothing mechanical
  can see it. After adding a type, sweep **both `CLAUDE.md` and `docs/chart-types.md`**
  (and the builder's own comments, which carry the same claims):

  ```bash
  grep -noE 'the (one|only) [a-zA-Z*`_.]+ [a-zA-Z*`_.]+' CLAUDE.md docs/chart-types.md
  grep -noE 'the (first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)' \
      CLAUDE.md docs/chart-types.md
  ```

  Check each hit against the code. The sweep catches **pre-existing** drift too, not only
  what you just added — fix what it finds, not only what your diff caused. Note the second
  regex is itself a tally that goes stale: each new type can push an ordinal past the end of
  the alternation, so extend it rather than assuming it still covers the top of the range.

  **Bare CARDINALS ("the four extra column selectors") are deliberately *not* swept.** They
  are the same bug — a number in prose is a fact about the code with no second home — and
  they have drifted twice, in `docs/chart-types.md` and in `tests/test_smoke.py`'s AppTest
  preamble, both saying "the four"/"the three" long after there were nine. But a sweep is the
  wrong instrument: widened to cardinals it turns up ~59 hits across the docs and the source
  against ~1 real one, because almost every cardinal is structurally fixed ("the two ends of a
  bar", "the three builders"). A signal rate that low does not survive being run by hand.
  So the counts that **scale with chart types** are pinned mechanically instead, by the
  docs-count tests in `tests/test_smoke.py` (a rule, not a tally — this sentence would
  otherwise need editing every time one was added): they pin the supported-type count in
  both docs, the extra-column kwarg count, and the kwarg table below checked **by name**,
  so a rename cannot pass by keeping the total the same. Adding a type or a kwarg fails them on the day it lands.
  Two consequences for prose: a count that scales needs no sweep but **must** appear in a
  form one of those tests reads, and new prose about a type-scaled set should prefer a rule
  ("one selector per extra column kwarg") to a tally — a rule cannot go stale.
- Render every visualization with Highcharts (`highcharts-core`); do not use native
  Streamlit charts.
- Use `EnforcedNull` (from `highcharts_core.constants`) for missing data points in dict
  configs fed to highcharts-core, **not** Python `None`. **There is exactly ONE exception,
  and it is exactly one slot wide: a bullet point's GOAL — the second element of its
  `[measure, goal]` array — must be Python `None`.** Do not "fix" it back.
  `options/series/data/bullet.py`'s `target` setter runs
  `validators.numeric(value, allow_empty=True)`, which admits `None` and rejects
  `EnforcedNullType` with `CannotCoerceError` — raised at `Chart.from_options`, **one layer
  below `build_options`**. So the whole options-dict suite stays **green** while the chart
  cannot be built at all, and the app's interactive path (which does not catch builder
  errors) shows a bare traceback naming neither `target` nor `bullet`. Pinned by a test that
  drives `make_chart` rather than `build_options` — the only layer at which the failure is
  observable.
- A **row-less** frame (columns, no rows — a CSV with a header and no data) is a legitimate
  input and must draw an **empty chart, not raise**. Every `Series.map(...)` used as a mask
  must therefore be `.astype(bool)`-cast: `.map()` infers its result dtype from the values it
  produced, and with no rows there are none, so it returns an empty **non-boolean** Series.
  That breaks three ways — a DataFrame indexed by a non-boolean Series is read as a list of
  **column names** (one shared line, so this killed *every* type at once, and a new type
  inherits the bug the day it is added unless the cast is there); `.sum()` of an empty string
  mask is `''`, so `int()` raises; and `&` between two of them raises out of the Arrow kernel,
  while `bool & str` merely *warns* today but is deprecated and will raise in pandas 4.
- Treat a **non-finite** number as a missing one. `pd.isna(inf)` is `False`, but an infinity
  can't be serialized: `to_js_literal` emits the bare token `inf`, which is not a JavaScript
  identifier (JS spells it `Infinity`), so the chart call dies with a `ReferenceError` and the
  iframe renders blank; the export server, sent the non-standard JSON literal `Infinity`,
  answers `400`. Each type applies its own missing-data policy to a non-finite **value** —
  keep-the-slot types via `_num`, drop-the-row types via `_plottable`, the aggregating types
  via `_finite_values` — and the same policy governs the **label** column via `_label_ok`.
  Reachable from a plain CSV: `inf`, `Infinity`, `-inf` and `1e400` (which silently
  overflows), and a blank cell (`nan`). One trap is pandas', not Highcharts': an **empty**
  column sums to `0.0`, the additive **identity** — a confident claim of "the total is zero"
  where the truth is "there is no data" — so `_gauge_value` tests for empty **above** the
  reducer. Only `sum` lies, which makes it worse rather than better.
- `build_chart_html` pins the chart's `color-scheme` to `only light`
  (`_LIGHT_COLOR_SCHEME_CSS`, on the `.highcharts-root` `<svg>`, **not** `html`: Highcharts
  declares `color-scheme: light dark` on the `.highcharts-container` div between them, and
  since the property inherits, that shadows an `html` rule for the SVG subtree — so the pin
  must sit at or below the container to win). Highcharts ≥ 13 expresses its own defaults as
  `light-dark()` CSS variables, so any color we *don't* set would follow the **viewer's
  browser**, not the `dark` flag. The export server already rasterizes with the light
  resolution, so this makes the two render modes agree and leaves `_themed` the single source
  of truth for dark mode. Anything a new chart type wants themed must go through
  `build_options`, never through a Highcharts default.
- Theme charts via `highcharts_builder.DEFAULT_COLORS` (applied by `build_options` to every
  chart, so the iframe and PNG paths are themed too). It **is** `.streamlit/config.toml`'s
  `chartCategoricalColors`, copied by hand because no theme CSS reaches an iframe or a
  server-side PNG; `_DARK_CHROME`'s `bg`/`text`/`muted`/`grid` are likewise its
  `backgroundColor`/`textColor`/`grayColor`/`borderColor`, and `_HEATMAP_GRADIENT_DARK`'s two
  endpoints come off its `chartSequentialColors`. All of it is guarded by
  `test_theme_colors_stay_in_sync_with_config`, so the copy fails the suite rather than
  drifting. The palette's **order** is load-bearing beyond its hues — `_WATERFALL_*` and
  `_BOXPLOT_OUTLIER_COLOR` index into it, so a reshuffle repaints "a rise" and "a loss".
  The palette is shared across light/dark; only the chart chrome flips, via
  `build_options(..., dark=...)` / `_DARK_CHROME`. The app itself now resolves to dark for
  every viewer, but `dark=False` stays a supported builder input and stays covered.
  Two exceptions: `heatmap` colors its cells by a sequential `colorAxis` rather than the
  categorical palette, and `bullet`'s goal crossbar is the only place a **mark** flips rather
  than chrome — it necessarily crosses both the bar and the background, so a fixed colour
  cannot work *in principle*. Invent no new colors: alias existing ones
  (`_NEEDLE_PIVOT_COLOR = _SUNBURST_ROOT_COLOR`) so paired values cannot drift.
