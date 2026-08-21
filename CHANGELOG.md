# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) — while
`0.x`, a minor bump is any new capability and a patch is a fix.

`0.7.0` is the first version cut as a release. Everything below it is
**reconstructed from git history**: the version in `pyproject.toml` was bumped by
hand, but nothing pinned it, tagged it, or wrote it down, so those entries are
read back off the commits rather than quoted from notes taken at the time.

Their `v0.1.0`–`v0.6.0` tags were **backfilled** on 2026-07-13 (the tag objects
say so, and their creation dates give them away). A tag here asserts only the one
checkable fact — that the commit it points at declares that version in
`pyproject.toml` — and not that a release was cut at the time, because none was.
They exist so the compare links below resolve to something structural rather than
to hand-typed SHAs.

Two consequences of the un-gated bumping are visible in the dates below, and are
worth stating rather than tidying away:

- **The bump often trailed the feature.** `0.2.0` was cut *for* areaspline and
  `0.3.0` *for* bubble, but by then both had already landed — so each range
  actually contains the *next* thing.
- **`0.6.0` ran long.** Five chart types (sankey, boxplot, waterfall, sunburst,
  xrange) plus the repo-wide missing-data hardening all shipped while the
  version sat still, because no gate asked it to move. Anyone who checked out at
  `xrange` got a tree calling itself `0.6.0`, so that is what this file says.
  `tests/test_packaging.py::test_changelog_documents_the_current_version` now
  pins `pyproject.toml`'s version to the top entry here, which is the gate that
  was missing.

Dates are the last commit at that version — the point it stopped being current.

## [0.18.0] - 2026-08-20

### Changed

- **The app ships ONE theme instead of a light/dark pair.** `.streamlit/config.toml` is now the
  **financial-dashboard** template bundled with Streamlit's own skill docs, written as a single
  `[theme]` (plus `[theme.sidebar]`). The shape is the decision rather than an omission: defining
  both `[theme.light]` and `[theme.dark]` is *precisely* what unlocks the light/dark toggle in
  Streamlit's settings menu, so a lone `[theme]` locks the app to one mode — here dark, via
  `base = "dark"`. `st.context.theme.type` therefore reads `"dark"` for every viewer, and
  `streamlit_app.py` hands the builder `dark=True` on every render. It is still **read** rather
  than hardcoded, so restoring the two subtables restores the old behaviour without touching
  Python. Pinned by `test_app_theme_is_a_single_mode_with_no_light_dark_toggle`, because re-adding
  a subtable is a change nothing else in the suite would object to.
- **`DEFAULT_COLORS` no longer *matches* the theme; it IS the theme's `chartCategoricalColors`.**
  Streamlit applies that key only to its own Vega/Plotly charts, of which this app has none — every
  chart is Highcharts, in an iframe or a server-side PNG that no theme CSS reaches — so the list has
  to be restated in `highcharts_builder` by hand. Same for `_DARK_CHROME`'s `bg`/`text`/`muted`/
  `grid`, which are the theme's `backgroundColor`/`textColor`/`grayColor`/`borderColor` under other
  names, and for `_HEATMAP_GRADIENT_DARK`, whose two endpoints now come off the theme's
  `chartSequentialColors` instead of being hand-picked slate. Only `_DARK_CHROME["axis"]` remains
  the builder's own — a Streamlit theme has no counterpart for tick lines.
- **`test_theme_colors_stay_in_sync_with_config` grew from three assertions to eight**, which is the
  point of adopting the theme wholesale rather than piecemeal: every value copied across the
  Streamlit-free boundary now has its second home. It pins the palette **as an ordered list**, not
  as a set — `_WATERFALL_UP_COLOR`, `_WATERFALL_DOWN_COLOR`, `_WATERFALL_SUM_COLOR` and
  `_BOXPLOT_OUTLIER_COLOR` index into it, so a reshuffle that kept all eight hues would repaint "a
  rise" and "a loss" while every other assertion still passed. The dark heatmap ramp is pinned by
  its **rule** (both endpoints lie on the theme's sequential scale, low before high) rather than by
  its indices, which would only restate the constant.

### Fixed

- **The app's "not a category" grey had quietly become a category.** `_SUNBURST_ROOT_COLOR` — also
  the dumbbell *before* marker and the gauge needle pivot, which alias it — exists to say "this
  sector is the WHOLE, not one of the branches", and ring 1 *cycles* the palette, so its entire
  definition is a hue from **outside** it. The financial-dashboard categorical scale contains
  slate-400 at index 6, so repointing `DEFAULT_COLORS` at the theme made the constant a palette
  entry and a seventh series would have been painted in it. Moved to slate-500. Caught by
  `test_sunburst_root_color_is_off_the_categorical_scale` on the first full run, not by reading —
  and because `DEFAULT_COLORS` is now itself pinned to `config.toml`, that test has become a guard
  on the **theme**: a future palette containing the root hue fails there rather than on screen.
- **Two prose anecdotes quoted a palette hex that has since moved.** Both recorded a rendering
  session — the dumbbell connector's default colour read off the DOM, in `highcharts_builder.py`
  and again in `docs/chart-types.md` — and both made their point by naming the old brand blue. The
  point was never the hex; it was that the value **equals the series hue**. Restated as that rule,
  which cannot go stale, in the same spirit as replacing a tally with its criterion.

### Removed

- **The one-rerun theme lag is no longer reachable.** A *manual* mid-session light/dark switch was
  applied frontend-side with no Python rerun, so the chart kept the previous mode's chrome until the
  next interaction — pre-existing Streamlit behaviour rather than a bug here, and never fixable from
  this side. Removing the toggle removes the only way to trigger it.

## [0.17.0] - 2026-07-19

### Added

- **`dumbbell` chart type** — two markers per category joined by a connector: a **before** and an
  **after** ("where each region started and where it ended up"). It is columnrange's data shape read
  a **fourth** way, and — as with the three before it — the reading settles every decision. A
  columnrange's two numbers are the two **ends of one mark**; a bullet's are two **independent
  claims** on one channel; a variwide's are **one claim over two geometric channels**; a dumbbell's
  are **one claim at two times**, so the reading is neither number but the *delta*, and the
  connector is the mark. It therefore does not join `MAGNITUDE_RANGE_TYPES` and reuses neither
  `high_col`, `goal_col` nor `width_col` — the new **`after_col`** kwarg is the ninth, the fourth
  that is not a reuse, and the third recent type to touch the cache layer. Joins
  `X_IN_Y_GUARD_TYPES`, adds a dedicated `before == after` guard for the collision that rule cannot
  express, and reads the **"Changes"** KPI.
- **The pair is not normalized, and that is the type.** Highcharts paints `lowColor` onto the marker
  at the **first array slot**, not onto the numerically smaller value — verified by rendering a
  falling row, where the low-coloured marker drew at the **top**. So slot 0 is reliably the *before*
  whichever direction the row moved, and a fall reads as a fall. Had it tracked the smaller value,
  the type would have silently inverted its own colour coding on exactly the rows a reader most
  needs to trust; a dedicated test pins the order so a `sorted()` "tidy-up" cannot land.
- **`_range_point` reused across a family boundary**, without joining the family constant — a shared
  *helper* is shared behaviour, a shared *family constant* is a claim the types are interchangeable
  at the five sites it binds (`_is_top_level` and `_sizable` are the precedent). Dumbbell reaches
  that helper's all-or-nothing policy from a **third premise**, and the only one of the four that is
  not a choice at all: Highcharts draws **nothing** for a half-pair — verified, `[42, null]`
  serializes cleanly and renders no marker, no connector, just an empty tick — so there is no
  half-drawn state a per-end policy could prefer.
- **No `_themed` hook**, which is the surprising half and was **measured** rather than inferred.
  Dumbbell is a `highcharts-more` bar cousin of columnrange, which *is* in the border-dissolve
  tuple, but its markers carry `stroke: var(--highcharts-background-color)` at **`stroke-width: 0`**
  — the white ring the tuple exists to remove is declared and never painted. The tuple stays at six.
  Its **before** hue is instead a fixed off-palette slate (`_DUMBBELL_BEFORE_COLOR`, aliased to
  `_SUNBURST_ROOT_COLOR`), which needs no dark flip because a dumbbell's markers sit only on the
  background — unlike bullet's crossbar, drawn at 140% of the bar width, which necessarily crosses
  both the bar and the background and so cannot take a fixed value. Setting it at all is
  load-bearing: Highcharts' own default is a near-black that all but vanishes on the dark shell.
- Sample dataset **"Market share shift by region (dumbbell)"**, whose rows deliberately move in
  **mixed** directions. A frame that only rose would draw identically whether the before/after hues
  track the first slot or the smaller value, so the falls are what make the sample demonstrate the
  type rather than merely exercise it.

- **Runtime cover for the PNG cache wrapper.** `cached_chart_png` was executed by **nothing**: the
  AppTests stay on the network-free interactive path, so a bad forward in that wrapper shipped
  silently and surfaced only as a wrong Static PNG in production. It is now driven for real with
  `highcharts_builder.build_chart_png` monkeypatched to a recorder, so the forwarding is observed
  as **values** rather than as AST names and no export server is contacted. The fixture empties the
  `@st.cache_data` caches on **both** sides: `monkeypatch` restores the function but not the cached
  *value*, so a stand-in PNG left behind would be served to the next Static PNG render, which would
  then pass without calling the builder at all.
- **`_FORWARDED` is now derived from the three builders' signatures** rather than hand-listed. A
  hand-listed tuple was the one fact in those tests with no second home — the property that let
  `version` go stale for five chart types — so a tenth kwarg added to the builders and the wrappers
  but omitted there would have left that column unchecked while both tests kept passing. Its floor
  test uses `>=`, not `==`: growth is the expected direction and needs no assertion, only shrinkage
  is the bug.
- **The docs' type-scaled counts are pinned mechanically**, the supported-type count in both homes
  and the extra-column kwarg table checked **by name** — so a rename cannot pass by keeping the
  total the same. "The four type-specific extra column selectors" had sat in `docs/chart-types.md`
  while there were nine, and neither `grep` sweep in `CLAUDE.md` could catch it: a bare cardinal is
  not an ordinal and not a uniqueness claim.

### Fixed

- **`build_options`' own docstring was a per-type inventory that had gone stale**, and unlike
  `CLAUDE.md` nothing sweeps it. `bullet` and `variwide` had **no entry at all**, its `Raises`
  paragraph never mentioned their guards, and it still described the x-in-y rule as covering "the
  category-axis types — cartesian, radar, heatmap, boxplot, and waterfall", four families out of
  date. `count_marks`' mark list was likewise missing xrange's bars, bullet's measures and
  variwide's bars. Both are now current, and the `Raises` paragraph states the
  cosmetic-collision-warns / claim-fabricating-collision-raises rule once rather than leaving it
  implicit across four guards.
- **Stale tallies corrected across both prose homes**, most of them pre-existing rather than caused
  by this change: the cache-layer tally (two recent types → three), the `_pick_*_sample` family (six
  → seven), `_FORWARDED`'s forwarded parameters (ten → eleven) and the extra-column-kwarg count (six
  → **nine**, having missed the `variwide` bump too), the `highcharts-more` and x-in-y enumerations
  (both, in **two** homes each), boxplot's "the one mark-styling type with no `_themed` hook" (four
  types now), and the `count_marks` note claiming *two* branches return the identical expression
  where **four** do.
- **One tally replaced by its criterion instead of being re-counted.** xrange's "the one mark-bearing
  type that prints nothing in the mark… the five that do" was stale on *both* halves, in both its
  homes, and would have gone stale again on the next type. It now states the rule that decides the
  question — a type prints a value in the mark exactly when that value can be read against no axis —
  which cannot drift, and says why it is put that way. A count of types on each side of a rule is
  prose only a reader can check; the rule itself is checkable against any type at all.

- **The `ty` gate was being OOM-killed, not failing a check.** From this version's own commit
  onward, `Type check (ty)` failed on every push while emitting **no diagnostics at all** — SIGKILL
  after ~5 minutes. On `ty` 0.0.49 the checker's memory grows super-linearly in the branch count of
  `streamlit_app.py`'s chart-type label chain, and `dumbbell`'s branch — the **14th of 18** —
  crossed the cliff: removing that one `elif` takes the same tree from OOM back to a 15s pass, and
  removing any *other* single branch does the same, so it is the count and not the branch. Fixed
  upstream; the pin moves 0.0.49 → **0.0.61**, which checks the same tree in ~1s. Two
  plausible-looking fixes were tested and **rejected by measurement** first — disabling the four
  `@st.cache_data` decorators, and declaring the chain's tuple types ahead of it — either of which
  would have shipped as a convincing no-op.

### Changed

- `CLAUDE.md`'s ordinal grep gained `ninth`, and now says outright that the regex is **itself a
  tally that goes stale** — each new type can push an ordinal past the end of the alternation, so
  the sweep silently stops covering the top of its own range. `dumbbell` made `ninth` reachable.

- **The per-type design record moved out of `CLAUDE.md`** into `docs/chart-types.md` — why each
  type is built the way it is, what the library silently drops, and which calls were settled by
  rendering. `CLAUDE.md` keeps the commands, the file map, and the rules that apply to every type
  at once, and points at the record rather than restating it.

## [0.16.0] - 2026-07-18

### Added

- **`variwide` chart type** — columns whose **width** is a second magnitude, so each bar's *area*
  is height x width ("margin, weighted by the revenue it earns"). It is columnrange's data shape
  read a **third** way, and the reading settles every decision: a columnrange's two numbers are the
  two **ends of one mark**, a bullet's are two **independent claims** on one channel, and a
  variwide's are **one claim spread over two geometric channels**. So it neither joins
  `MAGNITUDE_RANGE_TYPES` nor reuses `high_col`/`goal_col` — a high is the far *end* of its mark, a
  goal is a *reference* the mark is read against, a width is the mark's *other dimension*. The new
  **`width_col`** kwarg therefore does touch the cache layer. Joins `X_IN_Y_GUARD_TYPES`, adds a
  dedicated `value == width` guard for the collision that rule cannot express, and reads the
  **"Bars"** KPI.
- **A bad width nulls the whole slot** (`_variwide_point`, the third pair helper), and the reason is
  a fact about the *other rows* rather than about the mark: Highcharts sizes each column as its
  width's share of the width **total**, so a missing width drops out of the denominator and silently
  makes every other bar wider. Measured — nulling one row's width in a five-row frame redrew a
  sibling from 87px to **134px**, pixel-identical to a control render with the offending row deleted.
  The slot is kept, never dropped, so the category tick survives and a reader can see it exists.
- **The width channel takes `_sizable`, the height `_plottable`** — the first type here whose two
  value columns take different predicates. A negative width does not merely fail to draw itself: it
  shrinks the denominator, and rendered, a `-30` beside a `21` and a `44` inflated those two to 410px
  and 860px inside a **760px** chart, overflowing the canvas with no error anywhere. Zero is kept.
- **Sixth member of the dark-mode border-dissolve tuple**, joined on a measurement and on an argument
  the other five do not share: their bars have gaps, so the white outline is a spurious ring, while a
  variwide's bars *touch* by construction — the border is the only thing dividing two neighbours. So
  the dissolve was rendered as its own question, with adjacent bars of **equal height**, and it
  survives: the seam remains, drawn in the page colour, exactly as the white border is on the light
  shell.
- Sample dataset **"Product line margin by revenue (variwide)"**, whose two magnitude columns
  deliberately *anti*-correlate (the best margin belongs to the smallest line), so the chart shows
  that area — not height — is the reading. Read beside the columnrange and bullet samples, the three
  demonstrate that "a category plus two magnitude columns" is a data **shape**, not a chart.

### Changed

- Stale counts corrected where `width_col` and `_pick_variwide_sample` pushed a tally past its
  prose: `_FORWARDED` grew from nine forwarded parameters to ten (named in three comments and one
  docstring), the `_pick_*_sample` family from five helpers to six (named in both the helper's own
  docstring and `CLAUDE.md`), and the extra-column-kwarg tally from six to eight. None was reachable
  by any gate — they are prose about counts, which nothing but a reader can check.
- `CLAUDE.md`'s uniqueness-claim sweep gained an **ordinal** grep, after three claims went stale on
  this change and the prescribed regex caught none of them: two that `variwide` falsified (bullet's
  "the one recent type that does touch the cache layer" and "the fifth member of the literal tuple")
  and one **pre-existing** — boxplot's "the only type whose builder aggregates", which the gauge
  family had falsified while gauge's own passage already called itself the second.

## [0.15.0] - 2026-07-18

### Added

- **`bullet` chart type** — a KPI strip: one row per category, a **Measure** column drawn as a bar
  from zero and a **Goal** column drawn as a crossbar floating over it ("actual against target").
  It is columnrange's data shape read as a **comparison** rather than as a range, and that
  distinction settles the type: a columnrange's two numbers are the two ends of **one** bar, while
  a bullet's are two **independent channels** drawn as two shapes. So it does not join
  `MAGNITUDE_RANGE_TYPES` and does not reuse `high_col` — a high is the far *end* of the mark it
  shares a point with, a goal is a *reference* the mark is read against, the `title_col`
  "a title is not a weight" precedent one family over. The new **`goal_col`** kwarg therefore does
  touch the cache layer. Joins `X_IN_Y_GUARD_TYPES` (its `x_col` is a genuine category axis, bars
  standing on it), adds a dedicated `measure == goal` guard for the collision that rule cannot
  express, and reads the **"Measures"** KPI.
- **Each channel nulls alone** (`_bullet_point`, sitting directly below `_range_point` and stating
  the opposite verdict on the same input shape): a row with a measure and no goal draws its bar
  with no crossbar, one with a goal and no measure draws a lone reference line, and one with
  neither keeps its category tick. Nothing is dropped and nothing raises — a measure *below* its
  goal is the ordinary reading, not xrange's whole-axis lie, so there is no `explain_bullet_error`.
  All four combinations verified by rendering.
- **One documented exception to the `EnforcedNull`-not-`None` convention, exactly one slot wide.**
  A bullet point's **goal** must be Python `None`: `options/series/data/bullet.py` validates it with
  `validators.numeric(value, allow_empty=True)`, which admits `None` and rejects `EnforcedNullType`
  with `CannotCoerceError` — raised at `Chart.from_options`, one layer *below* `build_options`, so
  an options-dict test passes green while the chart cannot be built at all. The same point's
  **measure** slot takes `EnforcedNull` like every other keep-the-slot type. Pinned by a test that
  drives `make_chart`, the only layer at which it is observable.
- **The crossbar is coloured explicitly, and theme-flipped** — two `_themed` hooks, both measured
  rather than inferred. Left unset the goal marker takes the *series* hue at 140% of the bar width,
  so it collapses into the fill and survives as two meaningless stubs exactly when the measure
  *exceeds* the goal — the "we beat plan" row a reader most wants to find. And because it spans
  both the bar (a constant blue) and the background (white → slate), no fixed colour can work in
  principle, which makes this the one `_themed` hook in the module that flips a **mark** rather
  than chrome. Bullet also joins the bar-border dissolve tuple as its fifth member (rendered: its
  bars ring white in dark mode), while `arearange` stays deliberately out of it.
- **Single brand hue, `colorByPoint` pinned nowhere** — and here that pin guards a real decision
  rather than restating a library limitation, since bullet's `colorByPoint` survives the round trip
  at both levels. It is also load-bearing: any per-point key forces the point *dict* form, in which
  a `None` goal vanishes entirely, so a per-bar hue would leave a goal-less row with no working
  spelling at all.
- **No qualitative plot bands**, deliberately. The poor/average/good bands every bullet demo draws
  are a business judgement and a three-column CSV states none — sunburst refusing to emit a CSV's
  own subtotal as a parent value, and waterfall's `isSum` Total, applied once more.
- Adds the **"Quarterly sales vs quota (bullet)"** sample, whose regions deliberately beat, miss and
  exactly match their quotas — the beats being the load-bearing part, since that is where the
  crossbar-contrast trap strikes. Pulls in `modules/bullet` and *not* `highcharts-more` (the
  plausible guess the round trip corrects), and needs no `_MODULE_LOAD_ORDER` entry.

## [0.14.0] - 2026-07-17

### Added

- **`organization` chart type** — a titled reporting hierarchy, and the **fourth node-link type**
  (with `sankey`, `dependencywheel` and `networkgraph`). Its input is one row per person — an
  employee (`x_col`), their manager (`target_col`) and a job title (the new `title_col`) — which the
  builder turns into Highcharts' sankey-style `{from, to}` links, **swapped** to `{from: manager,
  to: employee}` so the tree flows down from a manager (Highcharts draws `from` as the parent). A
  blank/whitespace/missing manager is a **root** (the CEO): no incoming link rather than a dropped
  row, reusing sunburst's `_is_top_level` verbatim (a manager is a parent). It is **unweighted**
  like `networkgraph` (empty `y_cols`, no Y control) — the two are named `UNWEIGHTED_NODE_LINK_TYPES`
  so the empty-`y_cols` guard, the app's numeric-columns gate and its Y-control removal read one
  constant — and joins `NODE_LINK_TYPES` for the shared target-required and source≠target guards and
  the Target control (relabelled **"Manager (to)"**). The KPI reads **"Reports"** (reporting lines,
  counted by `not _is_top_level`, so a root's box draws but its non-existent line does not).
- **Per-node title cards** are the type's reason to exist and the one thing highcharts-core lets an
  organization keep that `sankey`/`networkgraph` silently drop: a modeled `nodes` array (`{id, name,
  title}`, deduped by node key, keyed with `_node_key` so an integral-float employee id matches
  itself across the two columns). It is the **one** node-link type to add a kwarg — `title_col`,
  since a title is not a weight — so this one does touch the cache layer. The Title control is
  optional via a leading **"(no titles)"** option (a name-only hierarchy — `title_col=None`), which
  is also the escape a 2-column roster (`employee, manager`) needs: with no third column to be a
  title, the control defaults to "(no titles)" rather than clamping onto — and mislabelling every
  box with — the Manager column. A **deliberate** Title == Employee/Manager collision is caught by
  an app-level guard (a warning + stop) — app-only, not a builder `ValueError`, since the choice is
  drawable (like scatter's x-in-y), just meaningless.
- **`_order_script_tags` generalized** from a single hardcoded `sankey → dependency-wheel` pair to a
  `_MODULE_LOAD_ORDER` **list**, because `modules/organization.js` extends the sankey series and hits
  the identical reversed-emission bug (a blank iframe beside a working PNG, **error #17**) — the
  "second edge would generalize it" the code's own comment predicted. Organization pulls in
  `modules/organization` **plus** `modules/sankey` (both from `chart.type` alone), and **not**
  `highcharts-more`.
- Rendering decisions, all **verified in a browser in both themes**: drawn top-down
  (`chart.inverted`); nodes **cycle the palette** (each box a distinct identity like a pie slice —
  Highcharts' default, so the builder sets no per-node color and no `colorByPoint`); and — unlike
  every weighted node-link type — it needs **no `_themed` hook at all** (its boxes carry no white
  border to dissolve; the name/title text rides Highcharts' `contrast` color), joining `boxplot` and
  `networkgraph` in that.
- **`Company reporting lines (organization)` sample** — the edge-list cousin of the sunburst
  `_org_headcount` sample: one row per person with a blank-manager root, a `title` column feeding the
  cards, and a throwaway numeric `tenure_years` (ignored by the chart, carried so the roster clears
  the no-numeric-columns gate).

## [0.13.0] - 2026-07-17

### Added

- **`arearange` chart type** — columnrange's filled-band mirror. It reads the **same** low/high
  magnitude data as `columnrange` (a category `x_col`, a low `y_cols[0]`, and a high `high_col`,
  encoded as a `[low, high]` 2-array per category) and draws it as one continuous **filled band**
  between a low line and a high line instead of N discrete bars. The two are byte-identical in the
  options tree **modulo the `chart.type` string**, so they share **one** build branch keyed by
  `chart_type` (the funnel/pyramid "differ only in the type string" pattern), plus the
  `high_col` guards, the `_range_point` missing-slot/kept-inverted policy, the `count_marks` rule,
  the `X_IN_Y_GUARD_TYPES` membership and the app's High control — all via the new
  `MAGNITUDE_RANGE_TYPES` constant, so columnrange and arearange can't drift. It reuses
  columnrange's `high_col` (no new kwarg, so the cache layer is untouched) and resolves
  `highcharts-more` from `chart.type` alone (**not** a phantom `modules/arearange`). The **one**
  thing NOT shared — decided by **rendering** in both themes — is the dark-mode hook: columnrange
  dissolves a white *bar border*, but an area *fill* has none (like `area`/`areaspline`), so
  arearange is deliberately **out** of the border-dissolve group and needs no `_themed` hook at
  all. A row missing either end keeps its category slot and **breaks** the band there (honestly "no
  data here", not a bridge across the gap); an inverted range is kept and drawn as an honest
  crossover, exactly as columnrange keeps it. Its marks are the band's `(low, high)` points, so it
  is count-adaptive with its own **"Points"** KPI (distinct from columnrange's "Ranges": a band is
  one shape, so the noun counts its vertices rather than implying N discrete ranges).
- **`Projected monthly active users (arearange)` sample** — a low/high forecast band over twelve
  months, and the deliberate **mirror** of the columnrange temperature-range sample: both read the
  same two magnitude columns, but a record-temperature range is a set of independent monthly facts
  (discrete bars) while a forecast is a continuous estimate read for its **outline** — so the band
  **widens** month over month to show the uncertainty cone opening, the shape a row of bars can't
  draw. It leads with a category (`month`) column so the app opens cleanly on `line`.

## [0.12.0] - 2026-07-16

### Added

- **`dependencywheel` chart type** — a circular sankey. It reads the **same** weighted
  node-link data as `sankey` (a source `x_col`, a `target_col`, and a weight `y_cols[0]`,
  encoded as `{from, to, weight}` links) and draws it as nodes on a ring joined by curved
  ribbons instead of a left-to-right flow. In highcharts-core `SankeySeries` is literally a
  **subclass** of `DependencyWheelSeries` (both carry `WeightedConnectionData`), so the link
  building, the drop-a-row-missing-any-of-three policy, the node chaining and the node/link
  tooltips are all **identical** to sankey's — so the two share **one** build branch, keyed by
  `chart_type` (the funnel/pyramid "differ only in the type string" pattern), plus one
  `count_marks` rule and one dark-mode border hook, via the new `WEIGHTED_NODE_LINK_TYPES`
  constant. The one thing NOT shared — found by **rendering** — is sankey's per-link weight
  labels: on a ring they stack in a clipped column off the left, so the wheel omits them and
  shows weight by ribbon width plus the tooltip (its canonical presentation), keeping only the
  node names on the arc. It reuses sankey's `target_col` (a link is a link — no new
  kwarg, so the cache layer is untouched) and joins `NODE_LINK_TYPES`, so the Target control, the
  required-target guard and the source≠target guard all bind it for free. It resolves **both**
  `modules/dependency-wheel` **and** `modules/sankey` from `chart.type` alone (the wheel builds on
  sankey's diagram infrastructure) — **not** `highcharts-more` (the plausible guess the round-trip
  corrects). Its marks are the same links, so it shares sankey's count-adaptive **"Flows"** KPI.
  The interactive path reorders those two module `<script>` tags (`_order_script_tags`) so
  `modules/sankey.js` loads **before** `modules/dependency-wheel.js` — the latter extends the
  sankey series, and `get_script_tags` emits them reversed, which blanks the iframe with
  Highcharts error #17 while the export-server PNG renders regardless (the two-render-modes-must-
  agree rule; found by rendering in a browser).
- **`Regional migration flows (dependencywheel)` sample** — population moving between five
  regions, and the deliberate **mirror** of the sankey energy sample: both read the same
  `{from, to, weight}` shape, but where the energy flow is a layered DAG (its source and target
  sets barely overlap), here **every** region is both an origin and a destination — the
  symmetric, cyclic matrix a wheel is built for, and a straight sankey would draw as a tangle of
  back-crossing links. It leads with a category (`origin`) column so the app opens cleanly on
  `line`.

## [0.11.0] - 2026-07-16

### Added

- **`funnel` and `pyramid` chart types** — part-of-whole *stages*, and pie's structural
  cousins: `FunnelSeries` is literally `FunnelOptions(PieOptions)`, so a funnel reads the same
  single-value shape pie does (one `{name, y}` leaf per row — `x_col` names each stage, the
  first `y_cols` column sizes it, a valueless row dropped like a pie slice). They are drawn
  **top-to-bottom in row order** (not re-sorted, so the sequence is the user's — columnrange's
  kept-as-given permissiveness). `pyramid` is funnel's inverted mirror and its **own**
  highcharts-core series type (`PyramidSeries`, which draws inverted by default) — **not** a
  `funnel` with `reversed=True` — so both serialize under their own Highcharts name (radar stays
  the one exception) and neither touches `FunnelOptions`' `neck_*` setters. The two differ only
  in the `chart.type` string, so they share one build branch and one `count_marks` rule, and both
  resolve `modules/funnel` from `chart.type` alone — **not** `highcharts-more` (verified on the
  round-trip). Each stage is palette-hued like a pie slice (`colorByPoint` inherited from pie's
  default; highcharts-core cannot express the key, so the builder sets nothing), and the tooltip
  prints the value with its share of the stage total. Both opt **into** the count-adaptive KPI
  (**"Stages"**), unlike their twin pie — one drawable stage per surviving row.
- **`Marketing conversion funnel (funnel)` and `Customer loyalty pyramid (pyramid)` samples** —
  the same single-value stage shape drawn two ways. Both lead with their *largest* stage and
  decrease, but a funnel puts it at the top and narrows downward (a shrinking purchase journey)
  while a pyramid draws the first row at the *base* and narrows upward to an apex (a broad-based
  loyalty pyramid) — so reading the two side by side shows the only difference is which way the
  shape points, not the data. Each leads with a category (stage/tier) column so the app opens
  cleanly on `line`.

## [0.10.0] - 2026-07-15

### Added

- **`columnrange` chart type** — floating vertical bars, each spanning a **low** to a
  **high** per category (a min–max range). It is xrange's cousin along one axis and its
  opposite along the other: both draw a bar from a low to a high, but xrange's pair are
  *coordinates* (they position a bar, may be dates, answer "when") while columnrange's are
  *magnitudes* (they size a bar, must be finite numbers, answer "how much"). So it reuses
  xrange's **UI shape** — a second value-column selector, low = `y_cols[0]` and high = a
  dedicated **`high_col`** — but **not** xrange's `end_col` kwarg: a coordinate that may be a
  date is a different column role than a magnitude, sourced from a different picker
  (`numeric_cols`, not `coordinate_columns`), so reusing it would be a lie. Its `x_col` is a
  genuine category X axis (the bars stand on it), so it joins `X_IN_Y_GUARD_TYPES` where
  xrange — whose x names a *lane* on the Y axis — could not. Its marks are the bars, one per
  surviving category (a single series with paired low/high points), so it needs a
  `count_marks` rule and a `MARK_METRICS` entry (**"Ranges"**) because its one series would
  otherwise misreport as a bare `1`.
- **`Monthly temperature range (columnrange)` sample** — a city's monthly record low/high in
  °C, the canonical columnrange demo. It is the mirror of `_release_plan`: its two value
  columns are a *low* and a *high* of the same quantity (magnitudes), not xrange's
  coordinates, so reading the two samples side by side is the fastest way to see the
  difference. Every low sits below its high (a clean range), because the type's headline is
  "a min–max per category" and the sample is meant to show it; the edge cases are the tests'.

### Notes

Each of these was measured on the round-trip or by rendering, never assumed:

- **A missing low or high keeps its category slot as a null bar** (the category-x
  keep-the-slot family — column/bar/waterfall), never a half-drawn range. The point is a
  bare `EnforcedNull`, not `{"low": …, "high": EnforcedNull}`: highcharts-core drops a null
  out of a point dict, so a partial dict would draw an arbitrary bar.
- **An inverted range (`high < low`) is kept, spanning both values.** Unlike xrange's
  backwards bar — which Highcharts draws across the *whole axis*, a confident lie, so xrange
  *drops* it — a columnrange bar is bounded by its two values, so `8 → -3` draws the same
  honest bar as `-3 → 8` (rendered). It is kept, order preserved, not dropped and not
  silently normalized.
- **The `[low, high]` point is a 2-array, not a dict.** A numeric-first 2-array is read
  unambiguously as `[low, high]` and survives `to_js_literal` intact; a `{name, low}` dict
  would collapse with the name in the leading `x` slot (boxplot's lesson, one type over).
- **Bars take one hue, not `colorByPoint`.** A columnrange is one measurement across the
  axis, so a per-bar hue would assert a categorical identity the categories don't have (the
  opposite call from pie/treemap/xrange, whose slices/lanes *are* separate identities).
- **The module is `highcharts-more`, from `chart.type` alone** (like bubble/boxplot/
  waterfall), **not** a phantom `modules/columnrange.js`. It needs one dark-mode `_themed`
  hook — the border dissolve it shares with column/bar/xrange (measured at pure white, the
  background variable), and *not* waterfall's fixed `#333333`.

## [0.9.0] - 2026-07-15

### Added

- **`networkgraph` chart type** — a force-directed graph, and sankey's cousin: each
  row is one edge between two node columns. It is the **mirror of the gauge family**.
  Gauge removes the *label* channel (`x_col is None`, its marks are the selected
  columns); networkgraph removes the *value* channel (`y_cols == []`, its marks are
  the edges), so the app draws it with **no Y control at all** — the second
  subtractive-control type, and the counterpart to gauge's absent X. It reuses
  sankey's `target_col` (a link is a link, so there is no new kwarg and the cache
  layer is untouched), rides the shared `_label_ok` filter on its source column, and
  needs a `count_marks` rule and a `MARK_METRICS` entry ("Links") because — unlike
  gauge — its one edge-series would otherwise misreport as a bare `1`.
- **`Service dependencies (networkgraph)` sample** — a microservice call graph whose
  source labels *repeat* and whose nodes are many of them both a source and a target
  (an `API Gateway` hub, a shared `Auth`), so it reads as a connected network rather
  than a star. It carries a `Catalog ⇄ Search` **cycle**, the one graph shape the
  sunburst sample's tree could never hold. Its `calls_per_min` column is a genuine
  numeric column carried for the reason `_release_plan`'s `headcount` is — so the
  dataset stays plottable by the value types and clears the no-numeric-columns gate —
  which networkgraph *ignores*, the honest place for a magnitude a graph can't draw.

### Notes

The type is **unweighted**, and that is the library's decision, not a preference —
each of these was measured on the round-trip or by rendering, never assumed:

- **A per-edge weight is silently dropped.** A `{from, to, weight}` link collapses
  to a `[from, to]` array in the emitted JS, so a numeric weight column (sankey's
  entire reason for being) would drive *nothing*. This repo treats a control that
  does nothing as a lie, so there is no weight column — the Y picker is removed, not
  ignored.
- **A node carries no individual color.** A series `nodes` array and a
  `colorByPoint` are both dropped the same way, so every node is the one brand hue;
  `colorByPoint` is asserted to appear nowhere. A graph's nodes have no categorical
  identity to colour, so this is honest rather than a limitation grudgingly accepted.
- **`enableSimulation` must be `false`.** With it `true` the export server rasterizes
  the graph mid-simulation as an unreadable central knot while the iframe animates it
  loose — the two render modes disagree, the class of bug `_LIGHT_COLOR_SCHEME_CSS`
  exists to close. With it `false` Highcharts settles the layout synchronously and
  both modes draw the same picture. Pinned on the emitted JS.
- **It needs no dark-mode `_themed` hook** (like boxplot, for a kindred reason): its
  node labels ride Highcharts' `contrast` color (white on dark, black on light), its
  nodes carry palette hues, and its links use a grey legible on both backgrounds —
  all verified by rendering a dark PNG. And it resolves `modules/networkgraph.js`
  from `chart.type` alone, and — correcting the common lore — **not**
  `highcharts-more`.

## [0.8.0] - 2026-07-13

### Added

- **`gauge` chart type** — the needle on a dial, and the second member of the
  **gauge family**. It spends the name `0.7.0` was deliberately holding for it:
  `solidgauge` was never given the friendlier `gauge` (which radar's precedent
  would have licensed) because `gauge` in Highcharts is a genuinely different
  series type, with its own `DialOptions`/`PivotOptions`. Both are now called
  what Highcharts calls them, and radar stays the *one* type whose `chart.type`
  is not its own name.
- **`GAUGE_TYPES` is now a family**, `SOLID_GAUGE_TYPES + NEEDLE_GAUGE_TYPES`.
  The tuple was already consulted at exactly the five places where the two types
  are *identical* — the `x_col is None` exemption, the `agg`/`dial` guard,
  `count_marks`' no-rule raise, the label-drop sweep's exclusion, and the
  row-less sweep's null expectation — so splitting it in two while keeping their
  sum under the old name was the whole of the family plumbing. Every one of those
  five sites stayed correct for the needle with **no edit at all**.
- `_dial_from_readings()` — the half of `gauge_dial` that **cannot see a
  DataFrame**. The family's central invariant ("the dial comes from the readings,
  never from the raw columns") stops being a rule two branches must remember and
  becomes a *signature*: a function that cannot see a raw column cannot derive a
  dial from one.
- **`Server utilization (gauge)` sample** — percentages across nine hosts, whose
  `mean` lands the derived dial almost exactly on `0..100`. Carries an entirely
  unreported `swap_pct` column, putting the family's headline trap on a page you
  can reach in two clicks.

### Fixed

- The needle gauge's **staggered needle lengths**. Two columns with *equal*
  readings put two needles at the same angle, and Highcharts draws the later
  series on top — so at one length the second needle covered the first
  completely: three series, two visible needles, with the legend still naming
  three. `marks == series` — the invariant the whole family rests on — was a lie
  *on screen*, in the one place a reader would never think to check. Staggering
  exposes each needle's tip in its own hue.
- **`overshoot`**, which keeps an *overridden* dial honest. `gauge_dial` guarantees
  every reading sits inside the scale it derives, but the app's two Dial inputs
  accept any two numbers — so zoom the scale to `0..50` on a column that sums to
  436 and the needle pegs **exactly on the final tick**, pixel-identical to a true
  reading of 50, with nothing on the chart to contradict it and no tooltip in the
  Static PNG. It was also the one place the two gauges would have *disagreed*: a
  ring in the same state fills its arc and prints `north: 436` in the hub, so its
  reader is told; a needle prints nothing in the mark. Now the needle swings *past*
  the last tick — what a real meter does when it slams its end stop.
- **`_GAUGE_VALUE_FORMAT`**, the family's number format, applied to **both** types.
  A bare `{point.y}` prints the raw double, and the double is what an aggregation
  hands you: the mean of nine integer percentages is `66.44444444444444`, which ran
  off the side of the chart in a 20-character smear. `solidgauge` had the identical
  latent bug — its own sample merely happens to divide evenly (436/8 = 54.5) — and
  it is the one flaw an options-dict assertion can never see, since the number is
  not in the options at all, only the format string is.
- The stale comment in `build_chart_html` claiming a gauge resolves
  `highcharts-more` from its `pane`. True of `solidgauge` (drop the pane there
  and the browser draws an empty SVG while the export server renders perfectly);
  **false** of `gauge`, which resolves the module from `chart.type` alone. The
  comment now names the type it is about, because the wrong half of it is a
  silently blank iframe.

### Notes

Three things the needle does *not* inherit from its sibling, each measured on the
round-trip or by rendering rather than assumed — and each of which would have been
a silent bug had solidgauge's answer been copied on faith:

- **The hue.** On a solid gauge a series-level `color` serializes perfectly and
  reaches *nothing* (the arc reads the point; the legend bullet draws grey and
  needs a `marker.fillColor`). On a needle, `color` reaches *only* the legend —
  the needle itself is **black** unless `dial.backgroundColor` says otherwise.
  Same property, opposite failure. The ring writes its hue to three places, the
  needle to two, and **not one of them is the same place**.
- **The module.** As above: `pane` for one, `chart.type` for the other.
- **The label.** A ring *must* print its readings in the hub — a 360° arc has
  nowhere to put an axis, so its value can be read against nothing, and it pays for
  that with a gate, a measured leading and a per-series offset. A needle points
  **at** an axis, so it prints **nothing in the mark** and needs no gate constant
  either: `xrange`'s rule, reached from `xrange`'s premise. The sibling's label
  machinery is not re-tuned here, it is *deleted*. (It was built the other way
  first, and the renders killed it: the stack, the arc and the subtitle cannot all
  fit at 300px, and both levers that would have bought the room are closed by the
  library — see below.)

Three silent drops found and pinned along the way. `Pane.size` discards a
percentage string (its setter validates `"85%"`, checks it for `%`, then falls off
the end without ever assigning `self._size` — only the numeric branch writes it),
which is what every gauge demo on the internet sets. `yAxis.labels.distance`
rejects `0` with `EmptyValueError` and refuses a negative outright — the same
`allow_empty` bug as `top_width`. And a `yAxis.plotBands` entry keeps
`from`/`to`/`color` but drops `thickness`, `innerRadius` and `outerRadius`; the type
carries no plot bands anyway, since `solidgauge`'s argument against `yAxis.stops`
holds unchanged — a coloured zone is a *judgment*, and the data never said low was
bad.

Between them, those first two are why the needle's **pane carries no geometry at
all** — no `size` *and no `center`*. Without `size`, a hand-placed centre cannot be
made safe: Highcharts reserves no room for the tick labels outside the pane, so
every value trades one chart height for another (at 65% it was clean at 300px and
800px and clipped clean off the canvas at 420). A failure that is not even monotonic
in the height is the tell that it is not a number to be tuned. Highcharts' own
default is correct at every height the app offers, because it is the one placement
that knows what the labels need.

## [0.7.0] - 2026-07-13

### Added

- **`solidgauge` chart type** — concentric activity-gauge rings on one shared
  dial. The first type with **no label channel at all**: its marks are the
  *selected columns themselves*, each reduced to a single number, so `x_col`
  names nothing and is `None` (widening it to `str | None` across the public
  signatures, and making every *other* type raise when it is omitted). The
  second aggregating type after `boxplot`, and the first whose row count has no
  bearing on its mark count.
- `agg=` — the reduction each ring applies to its column, one of the exported
  `GAUGE_AGGREGATIONS` (`sum`, `mean`, `median`, `min`, `max`, `last`), surfaced
  in the app as an aggregation picker sourced from that same tuple.
- `gauge_dial()` and `dial=` — the ring scale, **derived from the readings, not
  from the raw columns**. Under `sum` a reading can exceed every observation in
  its own column, so a dial derived from the column would pin every ring past
  its own end. The app *seeds* its Dial min/max inputs from this same call, which
  is the can't-drift rule applied for the first time to a widget's **value**
  rather than to its options.
- `explain_gauge_error()` — the third of the `explain_*` family, and the first
  that reads no DataFrame at all: a dial whose maximum does not sit above its
  minimum is a contradiction about two numbers the user typed.

### Fixed

- An **empty column no longer reports a total of zero**. `pd.Series([], dtype="float64").sum()`
  is `0.0` — the additive *identity* — so under `sum` an unfilled column would
  have drawn a confident ring at the dial's floor claiming "the total is zero"
  where the truth is "there is no data". Only `sum` lies (the other five
  reductions give `NaN`), which would have made it look like a rounding quirk.
  The empty test now runs *above* the reducer, and the ring is kept as a null and
  named in the legend — the one type whose legend is not redundant, because it is
  the only thing that names an empty ring.
- `threshold: 0`, without which Highcharts sweeps each arc from the axis
  *minimum* and **inverts an all-negative dial** — a −40 drawing a longer arc
  than a −155.

### Changed

- The app **removes** the X selectbox for gauge — the first *subtractive* control
  change, since a control that does nothing is a lie in the UI.
- Named `solidgauge` (Highcharts' own name), not the friendlier `gauge`, which
  is a *different* Highcharts chart (a needle on a dial) whose name is left free.

## [0.6.0] - 2026-07-12

The long one: the bump ships `treemap`, and then five more chart types land
behind it without the version moving.

### Added

- **`treemap`** — nested rectangles sized by value, laid out `squarified` and
  colored categorically, with the value printed in each tile so the static PNG
  shows numbers and not just relative areas.
- **`sankey`** — node-link flows sized by weight, the first type to read the
  frame as a **graph** rather than a table: each row is one link, from `x_col`'s
  node to a new `target_col`'s node.
- **`boxplot`** — per-category Tukey distributions, and the first builder that
  **aggregates** (every other type maps rows 1:1 onto marks). Whiskers follow
  `matplotlib.cbook.boxplot_stats`, with *inclusive* 1.5×IQR fences so a
  zero-IQR group isn't read as all outliers.
- **`waterfall`** — a cumulative bridge, the category-x shape read as signed
  *deltas*, with the builder **appending** the closing Total bar itself. The
  first type whose mark count exceeds its row count. Bars are colored by
  *meaning* (green rise, red fall, brand-blue total), so a custom palette cannot
  repaint a loss green.
- **`sunburst`** — a hierarchy as concentric rings, the first type to read the
  frame as an **adjacency list** and the first whose marks must be *assembled*
  rather than read. Node ids are synthesized rather than taken from labels (a
  duplicate label is Highcharts error #31); an internal node carries no value (a
  stated parent value would override the children-sum); a dangling parent is
  dropped *with its descendants* rather than silently re-parented; a cycle
  raises.
- **`xrange`** — a Gantt-style timeline, the first type whose marks have
  **extent** along an axis. Its start/end columns are **coordinates, not
  magnitudes**, so they may be dates — sniffed dtype-first, because
  `pd.to_datetime(12)` silently returns an instant at the epoch.
- `count_marks()` — returns exactly how many marks `build_options` will draw, so
  the app's KPI row can source its counts from the builder rather than
  recomputing them and drifting.
- `explain_export_failure()` — a failed static-PNG render now names its actual
  cause: a build error before any request, an unreachable server, or an HTTP
  answer (a 4xx especially, since the server is plainly reachable).
- `explain_tree_error()` and `explain_xrange_error()` — the same contract for a
  malformed hierarchy and for a contradictory column pair.

### Fixed

- **A non-finite value is now treated as missing in every chart type.**
  `pd.isna(inf)` is `False`, so an infinity slipped through both missing-data
  policies: `to_js_literal` renders it as the bare token `inf`, which is not a
  JavaScript identifier, so the interactive iframe died with a `ReferenceError`
  and rendered blank — while the export server, handed the non-standard literal
  `Infinity`, answered `400`, which the app then misreported as an unreachable
  server. Reachable from a plain CSV (`inf`, `Infinity`, `-inf`, `1e400`).
- **The missing-data policy now governs label columns too.** It had covered only
  value columns, so most types rendered a mark literally named `nan` — reachable
  from one blank cell in a text column.
- **A row-less frame draws an empty chart instead of raising.** A header-only CSV
  parses to columns-with-no-rows, and `Series.map()` infers its dtype from the
  values it produced — with no rows there are none, so it returns an empty
  *non-boolean* Series, and the DataFrame was then read as a *list of column
  names* rather than masked. `build_options` died with a bare `KeyError` in every
  single type.
- **A boxplot group whose statistics overflow** to a non-finite quantile is
  nulled: with a spread near the double range, `iqr = q3 - q1` overflows to `inf`
  from *finite* CSV input.
- **Both render modes now agree on color.** Highcharts ≥ 13 expresses its
  defaults as `light-dark()` CSS variables, so every color not set explicitly
  resolved against the **viewer's browser** rather than the `dark` flag — a
  light-mode chart of any type painted itself dark on a dark-OS browser.
  `build_chart_html` now pins `color-scheme: only light`, leaving `_themed` the
  single source of truth for dark mode.
- Column/bar borders and the heatmap colorAxis legend are themed for dark mode;
  they had fallen through to a light-background default that ringed every bar
  white.

## [0.5.0] - 2026-07-05

### Added

- **`heatmap` chart type** — a category × category value matrix, and the first
  type colored by **value** (a sequential `colorAxis`) rather than by the
  categorical palette. `x_col`'s values are the X categories and each selected
  column *name* is a Y category; empty cells stay `EnforcedNull` so the grid
  keeps its alignment.
- A tooltip naming both category axes, in-cell value labels for grids of ≤ 50
  cells, a vertical colorAxis legend, and a **Cells** KPI replacing "Series
  plotted", which had misreported the single-series grid.

### Changed

- `X_IN_Y_GUARD_TYPES` names the guard set shared by the builder and the UI (it
  had been a duplicated expression in two files), and `_category_labels` folds
  the thrice-repeated x-category stringify.

## [0.4.0] - 2026-07-05

### Added

- **`radar` chart type** — a polar spider/web line chart, reusing the cartesian
  category-X data shape on polar axes (a `line` series with `chart.polar`).

### Fixed

- Dropped radar's `pane: {size: "85%"}`. highcharts-core silently discards
  *percentage* pane sizes, so it never serialized — a latent silent-drop trap,
  and 85% is already the default.

## [0.3.0] - 2026-07-05

### Fixed

- **The default-Y reset regression.** The dynamic default (skip the X column) fed
  the *identity* of the keyless Y widget, so changing X re-minted the widget and
  silently discarded a multi-series selection.
- The bubble tooltip is hardened: column names are brace-stripped (so Highcharts
  won't parse `weight {kg}` as a token) and HTML-escaped (tooltips render HTML).

## [0.2.0] - 2026-07-05

### Added

- **`bubble` chart type** — scatter plus a marker-size dimension, via a required
  `size_col`. A size-aware tooltip names all three dimensions rather than
  emitting a bare x/y/z.

### Changed

- The end-to-end serialization pass widened from the cartesian types to **every**
  supported type, closing a real gap: the pie and scatter branches hardcode their
  `chart.type` literal and had never been driven through the real serializer.

## [0.1.0] - 2026-07-04

The initial app. The repository is repurposed from a collection of Highcharts
demo notebooks (archived at the `notebooks-archive` tag) into a Streamlit studio.

### Added

- **The app** — `streamlit_app.py` (UI, controls, caching) over a pure,
  Streamlit-free `highcharts_builder.py` (DataFrame → Highcharts options dict →
  `Chart` → embeddable HTML or PNG bytes), with built-in samples in
  `sample_data.py`. Every chart is produced by `highcharts-core`; no native
  Streamlit charts.
- **Eight chart types**: `line`, `spline`, `area`, `areaspline`, `column`, `bar`,
  `pie`, `scatter`.
- **Two render modes** — an interactive iframe (Highcharts from the CDN) and a
  static PNG (rendered server-side by the export server).
- **Light/dark theming** — split `[theme.light]`/`[theme.dark]` themes unlock
  Streamlit's in-app toggle, and a `dark` flag read from `st.context.theme.type`
  threads through the builder and into the cached renderers' keys. Only the chart
  chrome flips; the palette is shared, so a series keeps its color across a
  toggle.
- **A KPI metric row**, a chart-type help tooltip, and the generated Highcharts
  config behind a toggle.
- An `st.multiselect` fallback for wide CSV uploads, since `st.pills` is bounded
  at about five options.
- **The toolchain**: GitHub Actions CI (pytest, Ruff, ty), and Claude Code hooks
  under `.claude/hooks/` that mirror those same gates locally.
- **MIT licensing** with a separate `NOTICE` for the two proprietary layers
  (Highcharts JS / the export server, and the `highcharts-core` wrapper), so
  `LICENSE` stays pristine and GitHub detects the repo as MIT.

### Changed

- The interactive click-events render mode (a Streamlit Custom Component v2) was
  added and then **removed** again within this range; the render selector settled
  at two modes.
- The project was renamed twice on its way to `highcharts-studio`.

[0.9.0]: https://github.com/darylalim/highcharts-studio/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/darylalim/highcharts-studio/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/darylalim/highcharts-studio/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/darylalim/highcharts-studio/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/darylalim/highcharts-studio/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/darylalim/highcharts-studio/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/darylalim/highcharts-studio/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/darylalim/highcharts-studio/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/darylalim/highcharts-studio/releases/tag/v0.1.0
