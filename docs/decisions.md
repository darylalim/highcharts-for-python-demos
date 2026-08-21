# Decisions

The arguments and incidents behind rules stated tersely elsewhere.

`CLAUDE.md` states the **rule** and the **command**; per-type design detail lives in
[`chart-types.md`](chart-types.md); this file carries the **argument** and the
**incident** — the reasoning that justifies a rule, and the bug that bought it. None of
it is needed resident in a context window to work on the project, but all of it is what
the next decision should be reasoned from. Nothing here is history for its own sake: each
entry exists because a rule elsewhere looks arbitrary without it.

## Contents

[Packaging: the fact with no second home](#packaging-the-fact-with-no-second-home) ·
[CI: one gates job rather than three](#ci-one-gates-job-rather-than-three) ·
[Release: two bumps in one push](#release-two-bumps-in-one-push) ·
[Release: the watermark that failed open](#release-the-watermark-that-failed-open) ·
[Permissions: why each deny rule is spelled the way it is](#permissions-why-each-deny-rule-is-spelled-the-way-it-is) ·
[Prose drift: why cardinals are not swept](#prose-drift-why-cardinals-are-not-swept) ·
[The cache layer that nothing executed](#the-cache-layer-that-nothing-executed) ·
[Light mode, and its removal](#light-mode-and-its-removal) ·
[The bullet goal that must be `None`](#the-bullet-goal-that-must-be-none) ·
[Row-less frames: three ways a non-boolean mask breaks](#row-less-frames-three-ways-a-non-boolean-mask-breaks) ·
[`color-scheme`: why the pin sits on the SVG](#color-scheme-why-the-pin-sits-on-the-svg) ·
[Palette: the one deviation, and the second-mode smell](#palette-the-one-deviation-and-the-second-mode-smell)

## Packaging: the fact with no second home

`tests/test_packaging.py` guards the licensing metadata, the README's badges and table of
contents, and `CHANGELOG.md`'s newest entry against `pyproject.toml`'s `version`. That
last guard closed the suite's own blind spot.

`version` was the single packaging fact with **no second home**. Every other fact in the
file was stated twice — the SPDX `license` field against the `LICENSE` text, the `NOTICE`
layers against the README's `## License` section — so any of them could be checked by
comparing the copies. `version` was stated once, so unlike every other it could neither
drift nor be checked. It duly went stale: **five chart types shipped under `0.6.0`**
because nothing asked the number to move.

The fix was to give it a second home rather than to write a smarter test — `CHANGELOG.md`'s
top `## [x.y.z]` heading — which is why a bump that ships without notes now fails the
suite. This is the same mechanical-sync idea as
`test_theme_colors_stay_in_sync_with_config`, and the generalization is the rule the docs
now follow everywhere: **a fact with one home decays silently.**

## CI: one gates job rather than three

The three gate jobs (Ruff, ty, pytest) were collapsed into a single `gates` job that
`uv sync --locked` **once**. The obvious cost of collapsing is that a job stops at its
first failing step, which would make one job strictly *less* informative than three — a
push whose lint failed would say nothing about types or tests.

What buys the informativeness back is the guard on each gate step:

```yaml
if: ${{ !cancelled() && steps.sync.outcome == 'success' }}
```

`!cancelled()` is what makes a step run even though an earlier step failed, so a single
push reports lint **and** type **and** test status rather than only the first to break —
while a failed step still fails the job. The `steps.sync.outcome` half keeps that from
degenerating: if the dependency sync itself failed there is nothing meaningful to run, and
three more red steps would be noise rather than signal.

Ordering is deliberate too: Ruff and ty run before pytest, so a lint or type error reports
in seconds rather than after the suite.

## Release: two bumps in one push

The `release` job cuts a tag and a GitHub release for *every* `CHANGELOG.md` version above
the latest released one, not merely for the current version. That is load-bearing, not
thoroughness.

`0.10.0` and `0.11.0` both reached `main` before either was released. A job that released
only the version currently in `pyproject.toml` would have tagged `0.11.0` and left
`0.10.0` un-released **forever** — the watermark moves past it, so no later push ever
reconsiders it. Releasing everything above the watermark makes the job self-healing
instead: a version missed for any reason ships on the next push.

Each version is tagged at the commit that *declares* it — HEAD for the current one, else
the bump commit located by a `git log -S` pickaxe over `pyproject.toml`, which is why the
checkout is `fetch-depth: 0`. Notes are sliced out of `CHANGELOG.md` verbatim, and only
the highest version gets `--latest`.

The top-level `concurrency` cancels superseded runs for **PRs only**. Main pushes
serialize instead, because a release job killed mid-run can strand a pushed tag with no
release attached to it — a state no later push repairs, since the tag already exists.

## Release: the watermark that failed open

`to-release LATEST_TAG` **raises** on a watermark that is present but is not a changelog
version. It used to fail *open* and return every version in the file, which would
resurrect the deliberately release-less `0.1.0`–`0.6.0` tags as six spurious releases.

The workflow feeds it a watermark only from a `gh` call whose failure is an **error**.
`gh release view` exits 1 both for "no releases yet" and for a transient 5xx, and
swallowing that status made a blip read as the former. The consequence was quiet and
permanent: the "no releases yet" branch releases only the current version, so a 5xx during
a two-bump push drops the intermediate version for good — and the job reports **green**
while doing it.

Both bugs share a shape worth recognizing: an error path that degrades to a *plausible*
answer rather than to a stop. Prefer raising.

## Permissions: why each deny rule is spelled the way it is

`uv.lock`, `.streamlit/secrets.toml` and `.git/` are protected by `permissions.deny` rules
rather than by a `PreToolUse` hook. The permission engine runs **before** any hook and
applies to every path into the filesystem, not just the tools a `matcher` names — so it
also catches a Bash output redirection (`echo … > uv.lock`), which an `Edit|Write|MultiEdit`
matcher never sees. That is strictly stronger than the `guard_paths.py` hook it replaced.

Three details make the three rules a faithful replacement:

- Claude Code consults **only** `Edit(...)` and `Read(...)` path rules, and warns at
  startup on a `Write(...)`/`MultiEdit(...)` path rule it will never check — so the one
  `Edit` rule covers all three edit tools, and writing `Write(uv.lock)` would silently
  protect nothing.
- A **bare filename** follows gitignore semantics: `Edit(uv.lock)` is `Edit(**/uv.lock)`,
  matching at any depth. That reproduces the retired hook's match-by-basename rather than
  pinning one location.
- `Read(...)` also blocks Edit and Write on the same path, so the secrets rule is a
  **`Read`** deny: it keeps the file out of the context window, which a `PreToolUse` hook
  on the edit tools could not do at all.

`.git` is additionally a built-in **protected path** (writes are never auto-approved
outside `bypassPermissions`), but that only *prompts*; the deny rule blocks outright in
every mode, which is why it is still written out rather than left to the default.

## Prose drift: why cardinals are not swept

Bare cardinals ("the four extra column selectors") are the same bug the `the one|only` and
ordinal sweeps exist for — a number in prose is a fact about the code with no second home
— and they have drifted twice: in `chart-types.md` and in `tests/test_smoke.py`'s AppTest
preamble, both saying "the four"/"the three" long after there were nine.

A sweep is nevertheless the wrong instrument for them. Widened to cardinals it turns up
**~59 hits** across the docs and the source against **~1** real one, because almost every
cardinal is structurally fixed — "the two ends of a bar", "the three builders". A signal
rate that low does not survive being run by hand on every added type; it gets skipped, and
a skipped sweep is worse than no sweep because it is still cited.

So the counts that **scale with chart types** are pinned mechanically instead, by the
docs-count tests in `tests/test_smoke.py`. The two consequences for prose are the rule
CLAUDE.md now states: a type-scaled count must appear in a form one of those tests reads,
and new prose about a type-scaled set should prefer a **rule** to a **tally**.

## The cache layer that nothing executed

`cached_chart_html` and `cached_chart_js` were covered only *indirectly*. `cached_chart_png`
was, for a long time, executed by **nothing** — the AppTests stay on the network-free
interactive path, so the Static PNG wrapper was never entered by any test at all.

It is now pinned from **two** directions, because the network and the wiring are separable
and only the network was ever worth avoiding:

- **Statically**, by two `ast` tests that read `streamlit_app.py` as source. Static
  because `import streamlit_app` **executes the whole Streamlit script** — and because it
  catches what the keyword form cannot: `goal_col=high_col` type-checks, caches, and
  renders the wrong column while every assertion about *names* passes.
- **Dynamically**, by `test_app_static_png_mode_executes_the_cached_png_wrapper`, which
  selects Static PNG for real with `highcharts_builder.build_chart_png` monkeypatched to a
  recorder, so forwarding is observed as **values** and no export server is contacted.

That dynamic test clears the `@st.cache_data` caches on the way **out** as well as in.
`monkeypatch` restores the function but not the cached *value*, so a stand-in PNG left
behind would be served to any later Static PNG render — which would then pass **without
calling the builder at all**, reintroducing the exact vacuity the test was written to end.

## Light mode, and its removal

`build_options`, `make_chart`, `build_chart_html` and `build_chart_png` used to take a
`dark=` flag, threaded from `st.context.theme.type` through the cached renderers. It is
gone, along with the light values it selected.

The argument for removing it: adopting the financial-dashboard theme as a single `[theme]`
locked the app to dark, so light mode became **a mode nothing could select**. Its palette
had been tuned against the other one, and the tests asserted its hexes rather than its
legibility — so it was a claim of support the suite could not actually check. Shipping an
unreachable, unverifiable mode is worse than shipping one mode.

What that trades away is **self-correction**: the chart no longer *follows* the shell, it
assumes it. `test_app_theme_is_a_single_mode_with_no_light_dark_toggle` is what makes the
assumption safe — re-adding a `[theme.light]`/`[theme.dark]` subtable is a change nothing
else in the project would object to, and it would silently un-true the assumption every
`_themed` call now makes.

The removal also renamed the constants that had carried a mode in their names
(`_HEATMAP_GRADIENT_DARK` became `_HEATMAP_GRADIENT`), which is worth knowing when reading
older commits or docs.

## The bullet goal that must be `None`

Missing data points in dict configs fed to highcharts-core use `EnforcedNull`. There is
exactly one exception, and it is exactly one slot wide: a bullet point's **goal** — the
second element of its `[measure, goal]` array — must be Python `None`.

The mechanism is why it must not be "fixed" back.
`options/series/data/bullet.py`'s `target` setter runs
`validators.numeric(value, allow_empty=True)`, which admits `None` and rejects
`EnforcedNullType` with `CannotCoerceError`. That is raised at `Chart.from_options` —
**one layer below `build_options`**. So the whole options-dict suite stays **green** while
the chart cannot be built at all, and the app's interactive path (which does not catch
builder errors) shows a bare traceback naming neither `target` nor `bullet`.

It is pinned by a test that drives `make_chart` rather than `build_options`, because that
is the only layer at which the failure is observable — a general lesson for any rule whose
violation surfaces below the function under test.

## Row-less frames: three ways a non-boolean mask breaks

A row-less frame (columns, no rows — a CSV with a header and no data) must draw an empty
chart, not raise. Every `Series.map(...)` used as a mask must therefore be
`.astype(bool)`-cast: `.map()` infers its result dtype from the values it produced, and
with no rows there are none, so it returns an empty **non-boolean** Series.

That breaks three ways, and only the first is obvious:

1. A DataFrame indexed by a non-boolean Series is read as a list of **column names**. This
   is one shared line, so it killed *every* type at once — and a new type inherits the bug
   the day it is added unless the cast is there.
2. `.sum()` of an empty string mask is `''`, so `int()` raises.
3. `&` between two of them raises out of the Arrow kernel, while `bool & str` merely
   *warns* today — deprecated, and it will raise in pandas 4.

The third is why `test_count_marks_casts_every_mask_not_just_the_label_one` promotes
warnings to errors: it is the only way the non-label casts are observable at all today.

## `color-scheme`: why the pin sits on the SVG

`build_chart_html` pins the chart's `color-scheme` to `only light` via
`_LIGHT_COLOR_SCHEME_CSS`, on the `.highcharts-root` `<svg>` — **not** on `html`.

Highcharts declares `color-scheme: light dark` on the `.highcharts-container` div between
them. Since the property inherits, that declaration shadows an `html` rule for the whole
SVG subtree, so a pin on `html` loses. The pin must sit **at or below the container** to
win.

It is needed because Highcharts ≥ 13 expresses its own defaults as `light-dark()` CSS
variables: any color the project does *not* set explicitly would follow the **viewer's
browser** rather than the project's theme. The export server already rasterizes with the
light resolution, so pinning it makes the two render modes agree and leaves `_themed` the
single source of truth for dark mode.

The general rule that falls out: anything a new chart type wants themed must go through
`build_options`, never through a Highcharts default.

## Palette: the one deviation, and the second-mode smell

`DEFAULT_COLORS` **is** `.streamlit/config.toml`'s `chartCategoricalColors`, copied by
hand because no theme CSS reaches an iframe or a server-side PNG.

Exactly **one** entry deviates from the upstream template: index 6 is pink, not the
template's gray. That gray is also the template's `grayColor`, and therefore
`_DARK_CHROME["muted"]` — so series 7 was being drawn in the axis-label colour at a
contrast ratio of **1.00:1**, i.e. invisible against the labels it sat among.
`test_no_series_colour_collides_with_the_chart_chrome` is the guard that keeps any future
theme from walking a chrome value back into the categorical scale.

**The second-mode smell.** A constant that is written at build time and then overwritten
by `_themed` is evidence that a second mode is still hiding in the code.
`_HEATMAP_GRADIENT`, `_HEATMAP_NULL` and `_BULLET_TARGET_COLOR` were each exactly that;
each now holds its final value at its single write. Finding another is a signal to delete
a mode, not to add a branch.

**The crossbar that needs a pair.** `bullet`'s goal crossbar necessarily crosses both the
bar and the background, so a single fixed colour cannot work *in principle* — provably:
the two 3:1 luminance ranges do not overlap. It therefore carries a **fill plus a border**,
one value per surface. The testing lesson is the durable part: a mark whose legibility is
a property of a **pair** needs its test written over the pair. A per-path hex assertion
cannot see the defect, and did not.
