# CLAUDE.md

## Contents

[Project Overview](#project-overview) · [Quick start](#quick-start) ·
[Structure](#structure) · [Chart types](#chart-types) ·
[Adding a chart type](#adding-a-chart-type) · [Run](#run) · [Test](#test) ·
[Lint & format](#lint--format) · [Type check](#type-check) ·
[Release](#release) · [Hooks](#hooks) · [Conventions](#conventions)

Three docs, three jobs. **This file** carries the commands, the file map, and the rules
that apply to every type at once. [`docs/chart-types.md`](docs/chart-types.md) carries the
per-type design record — why each type is built the way it is, what the library silently
drops, and which calls were settled by rendering; it is long, so read the section you need
([How a chart is built](docs/chart-types.md#how-a-chart-is-built) plus the entry for the
nearest existing type) rather than the whole file.
[`docs/decisions.md`](docs/decisions.md) carries the argument and the incident behind
rules stated tersely here.

## Project Overview

`highcharts-studio` is a Streamlit application for building data visualizations
with Highcharts. Every chart is produced by the Highcharts for Python toolkit
(`highcharts-core`) — the app uses no native Streamlit charts.

One direction of flow, and every change lands somewhere on it:

```text
sample_data.py / CSV upload
  -> streamlit_app.py        widgets, guards, @st.cache_data wrappers, KPI row
  -> build_options()         DataFrame -> Highcharts options dict  (Streamlit-free)
  -> Chart.from_options()    via make_chart()
  -> build_chart_html()      iframe, Highcharts from the CDN        (interactive)
     build_chart_png()       bytes from the export server           (static)
```

## Quick start

```bash
uv sync                                   # Python 3.12; installs the dev group too
uv run streamlit run streamlit_app.py     # the app
uv run pytest && uv run ruff check . && uv run ty check   # the three gates
```

**No environment variables, no secrets, and no API keys are required.** The app reads
nothing from `st.secrets` or `os.environ`; `.streamlit/secrets.toml` appears only as a
`permissions.deny` rule, guarding a file this project does not use. The two network
dependencies are unauthenticated CDNs — `code.highcharts.com` (interactive) and
`export.highcharts.com` (static PNG).

## Structure

- `streamlit_app.py` — the Streamlit UI: data source (sample datasets or CSV upload),
  chart-type/column controls (pills for the Y series, falling back to `st.multiselect` on
  wide CSVs, plus one extra column selector per extra column kwarg), the `@st.cache_data`
  wrappers, a KPI metric row (its third metric adapts via `MARK_METRICS` — see
  [Chart types](#chart-types)), the render-mode selector (interactive iframe / static
  PNG), the chart embed, and a toggle revealing the generated Highcharts config (JS). The
  **no-plottable-columns gate** runs *below* the chart-type selectbox and is
  **type-aware**: xrange's start/end are coordinates and may be dates, and a date column
  is object dtype, so a canonical Gantt CSV has no numeric columns at all and a
  `select_dtypes("number")` gate would `st.stop()` it before the picker was drawn.
- `highcharts_builder.py` — pure, Streamlit-free helpers that turn a DataFrame into a
  Highcharts options `dict`, a `Chart`, and embeddable HTML or PNG bytes. Independently
  importable and unit-testable. It also owns three things that would otherwise drift from
  it: the **diagnosis** of its own failures (`explain_export_failure`, `explain_tree_error`,
  `explain_xrange_error`, `explain_gauge_error` — so a message can't drift from the error
  it stands in for; the first duck-types on `exc.response.status_code` rather than
  importing `requests`, which this project never declares), the **options** its widgets
  offer (`coordinate_columns`, `GAUGE_AGGREGATIONS`, `gauge_dial`), and `count_marks`,
  which reuses the same drop predicates — or, for sunburst and xrange, the whole build —
  so the KPI can't drift from the chart.
- `sample_data.py` — pure (Streamlit-free) built-in sample datasets and the `SAMPLES`
  registry the app offers when no CSV is uploaded. Every sample **but one** leads with a
  **category column**, and that is load-bearing rather than tidy: the app opens on `line`
  with the first column as X, so a numeric first column trips the x-in-y guard the moment
  the dataset is selected. The exception is the scatter sample (`Height vs weight`,
  leading with the int64 `height_cm`), which does exactly that — it is the standing
  counterexample, not a shape to copy. Samples are otherwise designed as **mirrors** —
  the columnrange, arearange, bullet, variwide and dumbbell samples all carry two
  magnitude columns and mean something different by them, so reading them side by side
  shows that "two magnitude columns" is a data *shape*, not a chart. Per-sample rationale:
  [`docs/chart-types.md`](docs/chart-types.md#the-sample-datasets).
- `tests/test_smoke.py` — builder unit tests (every chart type, the missing-data and edge
  cases, the validation guards, and an end-to-end pass driving every supported type
  through `Chart.from_options` / `to_js_literal`) and `sample_data` unit tests, plus
  headless `AppTest` interaction tests. Prefer finding a widget by **label** — positional
  indices (`app.selectbox[1]`) are still the majority idiom in the older AppTests and are
  fragile: one selectbox added above shifts every index at once. There is one
  `_pick_*_sample` helper per type that needs a non-landing dataset, each sharing
  `_pick_sample(app, chart_type)` as its body while keeping its own name and its own
  argument for why that type needs a dedicated sample.
- `tests/test_hooks.py` — unit tests for the `.claude/hooks/` scripts: the pure decision
  functions (`is_python_target`, `has_dirty_python`) plus a black-box check of
  `post_edit_py.py`'s exit-code contract (0 lets the edit through) without spawning the
  toolchain.
- `tests/test_release.py` — unit tests for `.github/scripts/release.py` (CI's release
  tooling, the `test_hooks.py` sibling): the pure functions that read the version, list
  the changelog's versions, slice a `CHANGELOG.md` section out *verbatim*, and decide
  which versions sit above the latest-release watermark. It also pins `main()`'s CLI
  contract, since the workflow parses its stdout: `version` prints *only* the version, bad
  args exit 2 writing nothing to stdout — so a stray print can't corrupt a tag name.
- `tests/test_packaging.py` — guards the licensing metadata (the `pyproject.toml` SPDX
  `license`/`license-files` fields, `LICENSE`'s pristine MIT text, `NOTICE`'s two
  proprietary layers kept in sync with the README's `## License` section), the README's
  header badges and `## Contents` table of contents, and `CHANGELOG.md`'s newest entry
  pinned to `pyproject.toml`'s `version` — the guard that closed the suite's own
  [blind spot](docs/decisions.md#packaging-the-fact-with-no-second-home). Reads the files
  directly, no build step.
- `.streamlit/config.toml` — project Streamlit theme: the bundled **financial-dashboard**
  template, as a **single `[theme]`** (plus `[theme.sidebar]`). That shape is the
  decision, not an omission: defining both `[theme.light]` and `[theme.dark]` is what
  unlocks the in-app light/dark toggle, so a lone `[theme]` locks the app to one mode,
  here **dark**. Pinned by `test_app_theme_is_a_single_mode_with_no_light_dark_toggle`,
  because re-adding a subtable is a change nothing else would object to. Chart colors are
  themed separately (see Conventions) since no theme CSS reaches an iframe or a
  server-side PNG.
- `.claude/settings.json` + `.claude/hooks/*.py` — committed Claude Code hooks that mirror
  the CI gates, plus the `permissions.deny` rules that protect `uv.lock`,
  `.streamlit/secrets.toml` and `.git/` (see [Hooks](#hooks)).
  `.claude/settings.local.json` holds per-developer overrides and is gitignored.
- `pyproject.toml` — dependencies + the `dev` group, the project license (MIT, via the
  PEP 639 `license`/`license-files` fields), and the Ruff/ty config.
- `.github/workflows/ci.yml` — GitHub Actions, two jobs. A `gates` job that
  `uv sync --locked` **once**, then runs the three checks the hooks mirror (Ruff
  lint/format, ty, pytest) as separate steps on every push to `main` and every PR — each
  guarded so that one failing step does not skip the rest, and Ruff/ty ahead of pytest so
  a lint or type error reports in seconds. Then a `release` job that `needs` it, runs on a
  push to `main` only, and — under a job-scoped `contents: write` over the top-level
  read-only token — cuts a `v{version}` tag + GitHub release for **every** `CHANGELOG.md`
  version above the latest released one (the watermark), marking only the highest
  `--latest`. Idempotent, so it stays silent on pushes that don't bump. Why
  [one job rather than three](docs/decisions.md#ci-one-gates-job-rather-than-three), and
  why [every version rather than the current one](docs/decisions.md#release-two-bumps-in-one-push)
  (plus the pickaxe, `fetch-depth: 0`, and `concurrency` cancelling PRs only).
- `.github/scripts/release.py` — the pure, stdlib-only reader CI's `release` job calls:
  `version`, `notes VERSION` (raising if the section is absent or empty so a release is
  never cut blank), and `to-release LATEST_TAG` (oldest-first, and **raising** rather than
  failing open on a watermark it does not recognize —
  [why](docs/decisions.md#release-the-watermark-that-failed-open)). It only *reads* facts
  already pinned by `test_changelog_documents_the_current_version`, which reuses this
  module's `changelog_versions` rather than re-encoding the heading regex, so the notes
  cannot drift from the changelog. Pure logic + a thin `main()`, the `.claude/hooks/`
  pattern applied to release tooling; the impure parts stay in the workflow.
- `LICENSE` / `NOTICE` — MIT for this project's own code, kept *pristine* (no text
  appended) so GitHub's detector classifies the repo as MIT; the third-party notice is
  split out because the two proprietary layers the app renders with (Highcharts JS / the
  export server, and the `highcharts-core` wrapper) are separately licensed and not
  covered by the MIT grant. Both are declared via `pyproject.toml`'s
  `license`/`license-files` and guarded by `tests/test_packaging.py`.
- `CHANGELOG.md` — the release notes, newest first (Keep a Changelog format). Its top
  `## [x.y.z]` heading is `version`'s **second home**, so a bump that ships without notes
  fails the suite. Everything below `0.7.0` is *reconstructed from git history*, which is
  why the file says so.
- `docs/chart-types.md` — the per-type design record. See [Chart types](#chart-types).
- `docs/decisions.md` — the argument and the incident behind rules stated tersely here.

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

None of them takes a mode flag: `_themed` applies the dark chrome unconditionally, because
`.streamlit/config.toml` is a single `[theme]` and every viewer therefore gets the dark
shell. The chart no longer *follows* the shell, it assumes it — which is why
`test_app_theme_is_a_single_mode_with_no_light_dark_toggle` is load-bearing. The removed
`dark=` flag and what its removal traded away:
[`docs/decisions.md`](docs/decisions.md#light-mode-and-its-removal).

Beyond `x_col`/`y_cols`, a type may take one of **9 extra column kwargs**, and which types
share one is a deliberate claim — *a link is a link, but a goal is not a high*. Reusing a
kwarg leaves the cache layer untouched; a new one costs three wrappers and three call
sites, and that cost is paid whenever the **role** differs even though the dtype and
picker source match. It costs no test edit: `_FORWARDED` is **derived** from the builders'
signatures, so the cache-layer checks pick a new kwarg up automatically — but the kwarg
**table below** is pinned by name, so a new row is not optional. Each row's middle cell is
the widget's label *verbatim*, parenthetical included.

| Kwarg | Control label | Types |
|---|---|---|
| `size_col` | Size (Z) | bubble |
| `target_col` | Target (to) / Manager (to) | sankey, dependencywheel, networkgraph, organization |
| `parent_col` | Parent (blank = top level) | sunburst |
| `end_col` | End | xrange (a **coordinate**, may be a date) |
| `high_col` | High (top) | columnrange, arearange (a **magnitude**) |
| `title_col` | Title | organization |
| `goal_col` | Goal (target) | bullet (a **reference**, not a far end) |
| `width_col` | Width | variwide (the mark's **other dimension**) |
| `after_col` | After | dumbbell (the same quantity **later** — the one ORDERED pair) |

The gauge family (`solidgauge`, `gauge`) takes the two that are **not** column names:
`agg=` (one of `GAUGE_AGGREGATIONS`) and `dial=` an explicit `(min, max)`, derived from
the **readings** by `gauge_dial` when `None`. It is why `x_col` is `str | None` on every
builder signature — the family has no label channel, so every *other* type raises when
`x_col` is omitted. The two **unweighted node-link types** (`networkgraph`,
`organization`) are its mirror, taking an **empty** `y_cols`.

The KPI's third metric adapts by `MARK_METRICS` membership, so the KPI stays one branch
however many such types there are. The table is pinned to the dict by
`test_claude_md_mark_metrics_table_matches_the_app`, so a new entry fails the suite until
it is documented:

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

## Adding a chart type

The project's dominant task, and the one that touches the most files. In order:

1. **Read** [How a chart is built](docs/chart-types.md#how-a-chart-is-built) and the entry
   for the nearest existing type — the shape it shares is usually the whole design.
2. **Build**: add the branch in `highcharts_builder.py`, applying the type's missing-data
   policy to values *and* labels, and `.astype(bool)`-casting every mask (see
   [Conventions](#conventions)).
3. **Theme**: add a `_themed` hook if the type needs one, and **verify by rendering** —
   never infer it from a base class.
4. **Count**: add a `count_marks` rule, and a `MARK_METRICS` entry when the mark count
   differs from `len(y_cols)`; add the row to the table above (the test requires it).
5. **Sample**: add a dataset to `sample_data.py` leading with a category column, and a
   `_pick_*_sample` helper if the landing dataset can't drive it.
6. **Wire**: add the selector in `streamlit_app.py` and any extra column widget, and
   forward it through all three cache wrappers **by keyword, under its own name**. A new
   kwarg also needs a row in the kwarg table above.
7. **Test**: extend the three [sweeps](#test) rather than writing a per-type test, and
   **verify the new test by breaking the code**.
8. **Sweep the prose**: run both `grep` sweeps in [Conventions](#conventions) over
   `CLAUDE.md` and `docs/chart-types.md`, and fix what they find — including drift you
   did not cause.
9. **Ship**: bump `version` in `pyproject.toml`, add the `CHANGELOG.md` section, and
   commit the `uv.lock` line uv rewrites.

## Run

```bash
uv run streamlit run streamlit_app.py
```

`.streamlit/config.toml` themes the shell and enables `runOnSave`, so saves auto-rerun.
Verify config with `uv run streamlit config show`.

When a stale chart is suspected, **restart the server** — that is what actually clears the
`@st.cache_data` caches (the CSV loader plus one per renderer). They are plain in-memory
caches, so `uv run streamlit cache clear` will *not* flush them: it exits 0 having cleared
only the on-disk persisted cache, and its own source says so. A `runOnSave` rerun does not
clear them either. In-process, `st.cache_data.clear()` or the app menu's **Clear cache**
does the job.

A *blank* chart is usually a network issue instead: interactive mode loads Highcharts from
the CDN (`code.highcharts.com`), static mode from the export server
(`export.highcharts.com`).

**Verify by rendering** (the methodology this project cites everywhere — a new type's
`_themed` hook, null/edge-case geometry, and interactive↔PNG parity are *decided by
looking*, never inferred from a base class): render one chart to a file with
`build_chart_html(df, type, …)`, serve it over `http://localhost`
(`python3 -m http.server PORT --directory <dir>` in the background — `file://` is blocked
by the Claude-in-Chrome extension), then screenshot it. Check it in both **browser** color
schemes: the chart is always dark, so a difference between them is a bug in the
`color-scheme` pin, not a theme. Run scratchpad scripts with
`PYTHONPATH=<repo> uv run python …` — the script's own dir, not the cwd, is on `sys.path`,
so a bare `import highcharts_builder` fails otherwise.

**Verify a new test by breaking the code** — the mutation counterpart to the above, and
the "a vacuous pass is worse than no test" rule turned into a procedure. Copy the source,
make the one edit the test claims to catch (delete the `_themed` hook, flip the null
policy, swap the two slots of a point array, revert a call site to positional), run *that
test alone*, restore, and diff to confirm the source came back byte-identical. A test that
stays green is pinning nothing. Read the failure, not just the exit code: a mutant caught
by `SyntaxError` rather than by the intended assertion is still a hole. It has already
caught a dark-mode test asserting `"#f1f5f9" in js` — that is `_DARK_CHROME["text"]`,
which `_themed` writes to the title, both axis labels and the tooltip on *every* chart, so
the test passed with the hook it existed for deleted outright.

## Test

```bash
uv run pytest
```

`tests/test_smoke.py` exercises the pure builder (`build_options`) parametrized across
every supported chart type, then drives the full app headless via Streamlit's `AppTest`
(switching controls, revealing the generated config, the KPI metric row, the wide-CSV
`st.multiselect` fallback, the render-mode selector's two modes, and the guard messages).
Per-type test inventory:
[`docs/chart-types.md`](docs/chart-types.md#the-test-suite-type-by-type).

Three **sweeps** are what cover a newly added type on the day it is added, rather than
whenever someone remembers — prefer extending a sweep to writing a per-type test:

- `test_no_supported_type_emits_a_non_finite_js_literal` — the value channel.
- `test_missing_or_non_finite_label_drops_the_row_in_every_type` — the label channel.
  The gauge family is *excluded* (keyed on `GAUGE_TYPES`): it would pass **vacuously**,
  reading as a pin on a policy the family deliberately does not have.
- `test_row_less_frame_draws_an_empty_chart_in_every_type`, with
  `test_count_marks_casts_every_mask_not_just_the_label_one` (which promotes warnings to
  errors — the only way the non-label casts are observable at all).

The app's **cache layer** is the part the ordinary AppTests barely reach, so it is pinned
from **two** directions: **statically**, by two `ast` tests that read `streamlit_app.py` as
source (every cached wrapper forwards each column/policy argument under its **own** name,
and all three call sites pass them by keyword); and **dynamically**, by
`test_app_static_png_mode_executes_the_cached_png_wrapper`, which selects Static PNG for
real with `build_chart_png` monkeypatched to a recorder, so no export server is contacted.
The set of arguments both layers check is **derived** from the three builders' signatures
(`_forwarded_arguments`), not hand-listed, so a new kwarg is covered the day it is added.
Why static, and why that test clears the caches on the way *out*:
[`docs/decisions.md`](docs/decisions.md#the-cache-layer-that-nothing-executed).

## Lint & format

Ruff does both; config is in `pyproject.toml`. (CI and the hooks run these same
gates — see Structure's `ci.yml` bullet and Hooks.)

```bash
uv run ruff check --fix . && uv run ruff format .   # fix + format
uv run ruff check . && uv run ruff format --check .  # verify (as CI does)
```

Note `ruff format` also formats ```python fences in Markdown, so `CLAUDE.md`, `README.md`,
`CHANGELOG.md` and `docs/*.md` are in scope for the format gate even though the hooks
(which route on `.py`) ignore them.

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
`highcharts-studio` version line; commit that with the bump. The `Edit(uv.lock)` deny rule
blocks *manual* edits to the lockfile, but uv's own re-sync is expected, not a stray
change.

## Hooks

`.claude/settings.json` wires two project hooks (committed; the per-developer
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
  `stop_hook_active` guard so it can't loop. Mirrors the test gate. Note it routes on
  `.py`, so a docs-only change does **not** trigger it — run `uv run pytest` yourself after
  editing `CLAUDE.md`, which the suite parses.

There is deliberately **no PreToolUse path guard**. `uv.lock`, `.streamlit/secrets.toml`
and `.git/` are protected by `permissions.deny` rules in the same `settings.json` instead,
which is strictly stronger: the permission engine runs **before** any hook and applies to
every path into the filesystem, not just the tools a `matcher` names — so it also catches
a Bash output redirection (`echo … > uv.lock`), which an `Edit|Write|MultiEdit` matcher
never sees. Why each of the three rules is spelled the way it is:
[`docs/decisions.md`](docs/decisions.md#permissions-why-each-deny-rule-is-spelled-the-way-it-is).

Adding or changing a hook triggers Claude Code's one-time hook-review prompt
before it runs.

## Conventions

Each rule below is stated with its mechanism. The per-type worked examples are in
[`docs/chart-types.md`](docs/chart-types.md) (see its Appendix for these same
conventions in their original, fully-enumerated form); the argument behind each is in
[`docs/decisions.md`](docs/decisions.md).

- **Astral tooling.** When working with Python, invoke the relevant Astral skill
  (`/astral:uv`, `/astral:ty`, `/astral:ruff`) for uv, ty, and ruff to ensure best
  practices are followed.
- **Streamlit-free builder.** Keep chart-building logic (DataFrame → Highcharts) in
  `highcharts_builder.py`, free of Streamlit imports, so it stays unit-testable.
- **Pure decision functions.** Keep each hook's decision logic in a pure, importable
  function in `.claude/hooks/` (as the builder is), so `tests/test_hooks.py` can cover it
  without subprocesses; the `main()` wrapper handles the stdin/exit-code plumbing and any
  impure subprocess orchestration (ruff/ty/pytest/git). `.github/scripts/release.py`
  follows the same split for CI, tested by `tests/test_release.py`; both load their script
  by file path via `tests/conftest.py`'s `load_script`.
- **Validate CI bash before pushing.** The `release` job in `ci.yml` carries real bash:
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
  regex is itself a tally that goes stale: each new type can push an ordinal past the end
  of the alternation, so extend it rather than assuming it still covers the top of the
  range.

  Bare **cardinals** are deliberately *not* swept — the signal rate is far too low to
  survive being run by hand
  ([why](docs/decisions.md#prose-drift-why-cardinals-are-not-swept)). Counts that scale
  with chart types are pinned mechanically instead, by the docs-count tests in
  `tests/test_smoke.py`: the supported-type count in both docs, the extra-column kwarg
  count, the kwarg table checked **by name** (so a rename cannot pass by keeping the total
  the same), and the `MARK_METRICS` table. Two consequences for prose: a count that scales
  needs no sweep but **must** appear in a form one of those tests reads, and new prose
  about a type-scaled set should prefer a **rule** ("one selector per extra column kwarg")
  to a **tally** — a rule cannot go stale.
- **Highcharts only.** Render every visualization with `highcharts-core`; do not use
  native Streamlit charts.
- **Null policy.** Use `EnforcedNull` (from `highcharts_core.constants`) for missing data
  points in dict configs fed to highcharts-core, **not** Python `None`. **There is exactly
  ONE exception, and it is exactly one slot wide: a bullet point's GOAL — the second
  element of its `[measure, goal]` array — must be Python `None`.** Do not "fix" it back;
  it raises one layer *below* `build_options`, so the options-dict suite stays green while
  the chart cannot be built at all
  ([mechanism](docs/decisions.md#the-bullet-goal-that-must-be-none)). Pinned by a test that
  drives `make_chart` rather than `build_options` — the only layer at which the failure is
  observable.
- **Row-less frames.** A frame with columns and no rows (a CSV with a header and no data)
  is a legitimate input and must draw an **empty chart, not raise**. Every
  `Series.map(...)` used as a mask must therefore be `.astype(bool)`-cast: `.map()` infers
  its result dtype from the values it produced, and with no rows there are none, so it
  returns an empty **non-boolean** Series. A DataFrame indexed by one is read as a list of
  **column names** — one shared line, so this killed *every* type at once, and a new type
  inherits the bug the day it is added unless the cast is there
  ([the other two failure modes](docs/decisions.md#row-less-frames-three-ways-a-non-boolean-mask-breaks)).
- **Non-finite is missing.** `pd.isna(inf)` is `False`, but an infinity can't be
  serialized: `to_js_literal` emits the bare token `inf`, which is not a JavaScript
  identifier (JS spells it `Infinity`), so the chart call dies with a `ReferenceError` and
  the iframe renders blank; the export server, sent the non-standard JSON literal
  `Infinity`, answers `400`. Each type applies its own missing-data policy to a non-finite
  **value** — keep-the-slot types via `_num`, drop-the-row types via `_plottable`, the
  aggregating types via `_finite_values` — and the same policy governs the **label** column
  via `_label_ok`. Reachable from a plain CSV: `inf`, `Infinity`, `-inf` and `1e400` (which
  silently overflows), and a blank cell (`nan`). One trap is pandas', not Highcharts': an
  **empty** column sums to `0.0`, the additive **identity** — a confident claim of "the
  total is zero" where the truth is "there is no data" — so `_gauge_value` tests for empty
  **above** the reducer. Only `sum` lies, which makes it worse rather than better.
- **Never rely on a Highcharts default.** `build_chart_html` pins the chart's
  `color-scheme` to `only light` (`_LIGHT_COLOR_SCHEME_CSS`, on the `.highcharts-root`
  `<svg>`, **not** `html` —
  [why the pin must sit that low](docs/decisions.md#color-scheme-why-the-pin-sits-on-the-svg)).
  Highcharts ≥ 13 expresses its own defaults as `light-dark()` CSS variables, so any color
  the project does *not* set would follow the **viewer's browser**. The export server
  already rasterizes with the light resolution, so this makes the two render modes agree
  and leaves `_themed` the single source of truth for the dark chrome. Anything a new chart
  type wants themed must go through `build_options`.
- **Chart colors.** Theme via `highcharts_builder.DEFAULT_COLORS` (applied by
  `build_options` to every chart, so the iframe and PNG paths are themed too). It **is**
  `.streamlit/config.toml`'s `chartCategoricalColors`, copied by hand because no theme CSS
  reaches an iframe or a server-side PNG; `_DARK_CHROME`'s `bg`/`text`/`muted`/`grid` are
  likewise its `backgroundColor`/`textColor`/`grayColor`/`borderColor`, and
  `_HEATMAP_GRADIENT`'s two endpoints come off its `chartSequentialColors`. All of it is
  guarded by `test_theme_colors_stay_in_sync_with_config`, so the copy fails the suite
  rather than drifting. Exactly **one** entry deviates from the upstream template — index 6
  is pink, not the template's gray, guarded by
  `test_no_series_colour_collides_with_the_chart_chrome`
  ([why](docs/decisions.md#palette-the-one-deviation-and-the-second-mode-smell)). The
  palette's **order** is load-bearing beyond its hues — `_WATERFALL_*` and
  `_BOXPLOT_OUTLIER_COLOR` index into it, so a reshuffle repaints "a rise" and "a loss".
  There is one mode, and a constant written at build time then overwritten by `_themed` is
  the smell that a second one is still hiding. Two marks sit outside the categorical
  palette: `heatmap` colors its cells by a sequential `colorAxis`, and `bullet`'s goal
  crossbar carries a **fill plus a border** — one value per surface, because it crosses
  both the bar and the background and no single colour can be legible on both. A mark whose
  legibility is a property of a PAIR needs its test written over the pair; a per-path hex
  assertion cannot see it, and did not. Invent no new colors: alias existing ones
  (`_NEEDLE_PIVOT_COLOR = _SUNBURST_ROOT_COLOR`) so paired values cannot drift.
