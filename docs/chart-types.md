# Chart types

The per-type design record for `highcharts-studio`: why each of the 29 supported
types is built the way it is, what the library silently drops, and which decisions
were settled by rendering rather than by inference.

Split out of `CLAUDE.md` so the operational brief stays small. **The reasoning here
is load-bearing** — the cross-type arguments ("a link is a link, but a goal is not a
high") are what keep the type family coherent, and the uniqueness/ordinal claims are
checkable only while every type is co-resident. Read this file before adding a chart
type, and sweep it as `CLAUDE.md` > Conventions prescribes.

## Contents

[How a chart is built](#how-a-chart-is-built) ·
[The app's column controls](#the-apps-column-controls) ·
[The builder's helpers](#the-builders-helpers) ·
[The sample datasets](#the-sample-datasets) ·
[The test suite, type by type](#the-test-suite-type-by-type) ·
[Appendix: the cross-cutting conventions in full](#appendix-the-cross-cutting-conventions-in-full)

## How a chart is built

`highcharts_builder.py` exposes the public helpers the app uses:

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

All three helpers take an optional `dark=` flag (default `False`) that themes the
chart chrome (background/text/axes/gridlines/tooltip) for dark mode; the app
derives it from `st.context.theme.type` and threads it through the cached
renderers. Bubble charts also take a `size_col=` naming the numeric column that
drives each marker's area (required for `bubble`, raising `ValueError` if
omitted; ignored by the other types), threaded through the same renderers,
sankey charts a `target_col=` naming the destination-node column (required for
all four node-link types — `sankey`, `dependencywheel`, `networkgraph` and `organization`
(which reads it as each employee's manager), all sharing one
`target_col`, raising `ValueError` if omitted or equal to `x_col`; likewise
ignored by the other types), threaded the same way — and the two UNWEIGHTED node-link types
(`networkgraph` and `organization`) read *only* that
plus `x_col` (organization also an optional `title_col`), taking an **empty** `y_cols` (they are
unweighted), the only types that do, as the
gauge family is the only one taking a `None` `x_col`, sunburst charts a
`parent_col=` naming the parent-label column (required for `sunburst`, raising
`ValueError` if omitted or equal to `x_col` — and, unlike the other two, also raising
when the column it names does not describe a *tree*: see `explain_tree_error`), and
xrange charts an `end_col=` naming the column each bar ends at (required for `xrange`,
raising `ValueError` if omitted or equal to the *start* column — `y_cols[0]`, not
`x_col`, which is the one collision of the four that is not against `x_col` at all — and,
like sunburst, also raising when its columns cannot place a bar on one axis: see
`explain_xrange_error`), and the **magnitude-range family** (`columnrange` and its filled-band
mirror `arearange`, named by `MAGNITUDE_RANGE_TYPES`) charts a `high_col=` naming the column each
bar/band reaches up to (required for both, raising `ValueError` if omitted or equal to the
*low* column — `y_cols[0]`, xrange's start-is-end collision one type over). It is the fifth
column kwarg, and the one that is **not** a reuse *of xrange's `end_col`*: xrange's is a
**coordinate** (it may be a date, sniffed by `_coordinates`), while a high is a **magnitude** that
must be `_plottable`, so a shared kwarg would be a lie — but *within* the magnitude-range family it
is itself reused, since arearange's high is a magnitude too (a link is a link, a high is a high), so
no new kwarg and the cache layer is untouched. Neither type raises a *column*-level
contradiction — an inverted `high < low` is drawable (a bar spanning `[min, high]`; a band as an
honest crossover), so it is kept, not raised — so there is no `explain_columnrange_error` (nor an
arearange one). Their `x_col` **is** a real
category axis, so `x_col == low` is caught by the shared `X_IN_Y_GUARD_TYPES` rule (both join it via
`MAGNITUDE_RANGE_TYPES`), for a while the only
extra-column types whose x-collision that rule could express — `bullet`, `variwide` and `dumbbell`
have since joined them on
the identical sentence, and for the identical reason.

And `organization` — the fourth node-link type — charts a `title_col=` naming an optional per-node
job-title column, drawn inside each box under the name (read only by organization; a name-only
hierarchy without it). It is the one node-link type to add a **new** kwarg — a title is not a
weight, so unlike `dependencywheel`/`networkgraph` reusing `target_col` this one *does* touch the
cache layer — and the manager it reads through `target_col` is the far end of the reporting link,
so the `{from, to}` link is built `{from: manager, to: employee}` (a blank manager is a ROOT, via
sunburst's reused `_is_top_level`, since a manager is a parent — not `_label_ok`, because
`_label_ok("")` is True and would draw a phantom link from a nameless node).

And `bullet` charts a `goal_col=` naming the column each measure bar is read **against**, drawn as
a crossbar floating over it (required for `bullet`, raising `ValueError` if omitted or equal to the
*measure* column — `y_cols[0]`, xrange's and columnrange's start-is-end collision a third time).
It is the **seventh** column kwarg and the second that is **not** a reuse, and the argument is
`title_col`'s one family over rather than `high_col`'s: a goal is drawn from the same
`numeric_cols` a high is, it is a magnitude that must be `_plottable` exactly as a high is, and it
is the second number on a two-magnitude row exactly as a high is — and it is still not a high,
because a **high is the far END of the mark it shares a point with** while a **goal is the
REFERENCE that mark is read against**. "A link is a link, but a goal is not a high." So it is a
new kwarg and it **does** touch the cache layer (arearange's and networkgraph's untouched-cache
win is not available here, and buying it would have meant the lie). Bullet raises no *column*-level
contradiction at all — every combination its two columns can present has a right drawing, including
a measure far under its goal, which is the type's **ordinary reading** — so there is no
`explain_bullet_error`. Its `x_col` **is** a real category axis (the bars stand ON it, drawn
vertically), so it joins `X_IN_Y_GUARD_TYPES` for `x_col == measure`; the other collision,
`measure == goal`, that rule cannot express (`goal_col` is not in `y_cols`) and it gets the
dedicated guard above, with an app-side warning in **front** of it, since the interactive path does
not catch builder errors. That pair is worth stating as a rule, because it is the second time this
project has had to choose: **a cosmetic collision warns, a claim-fabricating one raises.**
Organization's optional Title colliding with Manager mislabels the boxes while the hierarchy stays
true — drawable-but-meaningless, and it has a "(no titles)" escape — so it is app-only. Bullet's
two are **required** columns of one relation, and the collision fabricates the chart's central
claim: every bar would land exactly on its own crossbar, so the chart would report that every
category hit target precisely, in the one register the type exists to answer.

And `dumbbell` charts an `after_col=` naming the LATER of its two readings, drawn as a second marker
joined to the first by a connector (required for `dumbbell`, raising `ValueError` if omitted or
equal to the *before* column — `y_cols[0]`, xrange's, columnrange's and bullet's start-is-end
collision a fourth time). It is the **ninth** column kwarg and the fourth that is **not** a reuse,
and the argument is `goal_col`'s and `width_col`'s one family further along: an after is drawn from
the same `numeric_cols`, is `_plottable` exactly as they are, and is the second number on a
two-magnitude row exactly as they are — and it is still none of them, because a **high is the far
END of the mark** and its pair is UNORDERED (swap a range's two values and the same bar is drawn),
a **goal is the REFERENCE** its measure is read against (one number is the world, the other an
intention), a **width is the mark's OTHER DIMENSION** on a second geometric channel, while a
**before and an after are the SAME QUANTITY AT TWO TIMES** — one channel, one unit, and ORDERED,
since swapping them turns every rise into a fall. "A link is a link, but a goal is not a high" a
third time. So it is a new kwarg and it **does** touch the cache layer, the third recent type to
pay that cost rather than escape it.

Its `x_col` **is** a real category axis (the paired markers stand ON it, drawn vertically), so it
joins `X_IN_Y_GUARD_TYPES` for `x_col == before`; the other collision, `before == after`, that rule
cannot express (`after_col` is not in `y_cols`) and it gets the dedicated guard, with an app-side
warning in **front** of it. That is the cosmetic-warns / claim-fabricating-raises rule a fourth
time — and this is the collision where it matters most, because its wrong chart is the only one of
the four that is **indistinguishable from a real result**: every category would draw its two markers
at one value, which Highcharts renders as a single dot with no connector, i.e. as "nothing changed
anywhere" — a reading this type exists to express. A bullet sitting on its own crossbar at least
looks suspiciously perfect; this just looks like a quiet quarter.

The **gauge family** (`solidgauge` and `gauge`) takes the fifth and sixth, and they are the only
two that are **not column names**: `agg=` names the reduction each mark applies to its column (one
of `GAUGE_AGGREGATIONS`; raising `ValueError` otherwise) and `dial=` an explicit `(min, max)`
scale, which — left `None` — is *derived from the readings* by `gauge_dial` (raising `ValueError`
when its maximum does not sit above its minimum: see `explain_gauge_error`). Both are read by both
types, and neither by any other. The family is also why `x_col` is `str | None` on all five
signatures: they are the types with no label channel, so every *other* type raises when `x_col` is
omitted. (`dial` is not called `scale=` because `build_chart_png` already has a `scale: int = 2` —
the image's pixel density, which means something completely different and got there first.)

Supported chart types: `line`, `spline`, `area`, `areaspline`, `column`, `bar`,
`pie`, `scatter`, `bubble` (scatter plus a `size_col` marker-size dimension),
`radar` (a polar spider/web line chart — shares the cartesian category-X data
shape, rendered as a `line` with `chart.polar` on polar axes), `heatmap` (a
category-X × category-Y value matrix — the wide-form category-X data
reinterpreted as `[x, y, value]` cells colored by a sequential `colorAxis`, with
`x_col`'s values as the X categories and each `y_cols` column *name* as a Y
category, pulling in the `modules/heatmap` module), `treemap` (nested rectangles
sized by value — the same single-value data shape as `pie`: `x_col` labels each
tile and the first `y_cols` column gives its `value`, but tiles are colored
categorically from the palette via `colorByPoint` and laid out by the
`squarified` algorithm, dropping missing values like pie; pulls in the
`modules/treemap` module), `funnel` and `pyramid` (part-of-whole **stages** — pie's
structural cousins, since `FunnelSeries` is literally `FunnelOptions(PieOptions)`: the
same single-value data shape (`x_col` names each stage, the first `y_cols` column sizes
it, a valueless row **dropped like a pie slice** via `_plottable`, the `{name, y}` leaf
keyed like pie — *not* treemap's `value`), drawn top-to-bottom in **row order** (not
re-sorted — columnrange's kept-as-given permissiveness). Each stage is palette-hued like
a pie slice (`colorByPoint` **inherited** from pie's JS default; highcharts-core cannot
express the key, so the builder sets nothing — the opposite of treemap, which sets it
explicitly), and the tooltip prints the value with its share of the stage total (pie's
`point.percentage`, labelled "of total" so it is not misread as a conversion rate).
`pyramid` is funnel's **inverted mirror** and its OWN highcharts-core series type
(`PyramidSeries(FunnelSeries)`, which draws inverted **by default**) — *not* a `funnel`
with `reversed=True`, which keeps this module's "every type serializes as its own
Highcharts name" rule intact (radar is the one exception) and needs no geometry knobs at all.
Neither type sets `FunnelOptions`' `neck_*`/`width`/`height` geometry: Highcharts' defaults
render correctly at every height the app offers (verified across the sample renders), so there
is nothing to steer — those setters assign cleanly, so it is a "the defaults are right" call,
not the pane-`size` silent-drop the gauge work hit. The two differ **only** in the `chart.type`
string, so they share one
build branch, one `count_marks` rule (`label_ok & value_ok`, so both opt INTO the
count-adaptive **"Stages"** KPI — unlike their twin pie, whose omission is an unjustified
gap), and one `_themed` hook (pie's **two** flips — the labels sit OUTSIDE the shape on
the chart background, so they take the light text color, and the segment borders dissolve
into the dark background — **measured by rendering**, not inferred from the pie kinship).
Both resolve `modules/funnel` from `chart.type` alone — **not** `highcharts-more` (the
plausible guess the round-trip corrects). The one rendering fact that IS Highcharts' and
not the builder's: a funnel draws row 0 at the **top** and narrows down, a pyramid draws
row 0 at the **base** and narrows up to an apex — so the same largest-first frame is a
funnel pointing down or a pyramid pointing up, which is the whole of the difference
(verified by rendering)), `sankey` (a node-link flow diagram — the only type
that reads the data as *edges of a graph* rather than as series or categories:
each row is one link, from the node named in `x_col` to the node named in
`target_col`, weighted by the first `y_cols` column, encoded as
`{from, to, weight}` dicts. Rows missing any of the three are dropped like pie's
slices; a node that is both a target and a source chains the flow into a second
hop; pulls in the `modules/sankey` module. Its nodes are named by Highcharts'
default node label and each link carries its weight as a *per-link* `dataLabels`
— gated on link count like heatmap's cell labels — because highcharts-core drops
`plotOptions.sankey.dataLabels.nodeFormat` and the `format` that survives there
would label the links with the node format and blank the node names),
`dependencywheel` (a circular sankey, and the one type that shares another's build branch
without being its *inverted* twin the way pyramid is funnel's — it is sankey drawn on a **ring**.
It reads the identical weighted node-link data (`x_col` source, `target_col`, `y_cols[0]` weight,
`{from, to, weight}` links) because in highcharts-core `SankeySeries` is literally a **subclass**
of `DependencyWheelSeries` — both carry `WeightedConnectionData` — so the link building, the
drop-a-row-missing-any-of-three policy, the node chaining and the node/link tooltips (the same
`plotOptions[type].tooltip.nodeFormat` that a top-level one is silently dropped in favour of) are
byte-identical to sankey's. The **one** thing NOT shared is sankey's per-link weight labels, and it
was found only by **rendering** (the waterfall-vs-column/bar lesson, one type family over): on a
sankey each label sits neatly on its link, but on a ring the links anchor on the arc and Highcharts
stacks their labels in a clipped, overlapping column off the LEFT of the wheel (both render modes),
so the wheel **omits** them and shows weight by ribbon width plus the hover/node tooltip — the
canonical dependency-wheel presentation — while keeping the node NAMES, which render cleanly on the
ring for both. So the two still share **one** build branch, keyed by `chart_type` (that per-link
label loop the lone `chart_type in SANKEY_TYPES` guard inside it) — the funnel/pyramid "differ only
in the type string" pattern, *not* the sankey/networkgraph split, since networkgraph genuinely
differs in several places (unweighted, no weight label, `contrast` node labels, no border hook)
while the wheel differs in the type string, its layout and that single label line. `WEIGHTED_NODE_LINK_TYPES = SANKEY_TYPES + DEPENDENCYWHEEL_TYPES` names the shared pair at
the three sites where they are identical modulo the type string — the build branch, the
`count_marks` rule (sankey's `label_ok & target_ok & value_ok`, so the KPI reads the shared
**"Flows"**) and the `_themed` `borderColor` dissolve — while the wider `NODE_LINK_TYPES` (now
three) binds the guards all node-link types share (target required, source ≠ target). It reuses
sankey's `target_col` — a link is a link, no new kwarg, so the cache layer is untouched
(networkgraph's win) — and resolves **both** `modules/dependency-wheel` **and** `modules/sankey`
from `chart.type` alone (the wheel builds on sankey's diagram infrastructure), *not*
`highcharts-more`, the plausible guess the round-trip corrects. Those two modules are the one place
this type touches the interactive path specially: `dependency-wheel.js` **extends** the sankey
series, so it must load AFTER `sankey.js`, but `get_script_tags` emits them REVERSED (it walks the
chart's `plotOptions` before its `series`, so the dependent is seen first). Loaded first it throws
and Highcharts reports the series missing (**error #17**), blanking the iframe while the export
server renders the PNG regardless — the `_LIGHT_COLOR_SCHEME_CSS` two-render-modes-must-agree rule,
found only by rendering in a browser. `build_chart_html` fixes it with `_order_script_tags`
(`_MODULE_LOAD_ORDER`), which reorders the tag lines so a prerequisite precedes its dependent;
pinned by asserting the ORDER in the emitted HTML, not just the presence. Best read beside the sankey energy
sample: that flow is a layered DAG whose source and target sets barely overlap, while a wheel is
for the symmetric, cyclic matrix where every node is both an origin and a destination),
`networkgraph` (a force-directed graph, sankey's cousin — rows are edges of a graph,
read as `{from, to}` dicts over the same two node columns (`x_col` and `target_col`,
reused from sankey — no new kwarg, so the cache layer is untouched), but **unweighted**,
and that is the *library's* decision, not a preference. A per-edge `weight`/`width` is
accepted by `Chart.from_options` and then silently dropped (the `{from, to, weight}` dict
serializes to a bare `[from, to]` array), so a numeric weight column would drive nothing —
and this project treats a control that does nothing as a lie, so the Y picker is **removed**,
not ignored. That makes networkgraph the **mirror of the gauge family**: gauge removes the
LABEL channel (`x_col is None`, marks are the selected columns), networkgraph the VALUE
channel (`y_cols == []`, marks are the edges) — the second subtractive-control type, and the
counterpart to gauge's absent X. Its `x_col` is the SOURCE node label, a real label channel
(unlike gauge), so it rides the shared `_label_ok` filter and checks its second label column
in its own branch, exactly as sankey does; a row missing either end is dropped, no
`EnforcedNull`. It needs a `count_marks` rule and a `MARK_METRICS` entry (**Links**, one per
drawable edge) because — unlike gauge — its one edge-series would misreport as a bare `1`.
Nodes are painted ONE brand hue: a networkgraph neither cycles the palette across nodes nor
lets a node carry its own color (`colorByPoint` and a `nodes` array are both silently dropped,
so `colorByPoint` is pinned to appear NOWHERE), which is honest rather than grudging — a
graph's nodes have no categorical identity to colour. Nodes are labelled by name (their only
identity — no axis, no legend), in Highcharts' `contrast` color, so networkgraph needs **no
`_themed` hook at all** (like boxplot): white labels on dark, black on light, palette nodes
and grey links legible on both, all verified by rendering. The one setting the whole type turns
on is `enableSimulation: false`, pinned on the emitted JS and load-bearing: with it *true* the
export server rasterizes the graph mid-simulation as an unreadable central knot while the iframe
animates it loose — the two render modes disagree, the class of bug `_LIGHT_COLOR_SCHEME_CSS`
exists to close — while *false* settles the layout synchronously so both draw the same picture.
It sets **no custom tooltip** — another render-derived conclusion. A networkgraph tooltip fires on
a NODE (the links are 1px lines that trigger none), and a node point has `name` but no
`fromNode`/`toNode`, so the obvious `{point.fromNode.name} → {point.toNode.name}` renders an **empty
box** on every node hover (verified by rendering). The node-specific `nodeFormat` that would fix it
is silently dropped (sankey's `nodeFormat` trap, one type over), so the node format cannot be set
explicitly at all — and Highcharts' OWN default is correct (it prints the node name), the one and
only way to get it. So the tooltip is left default (`_themed` still paints its box for dark mode).
Pulls in `modules/networkgraph` from `chart.type` alone, and — correcting the common lore —
*not* `highcharts-more`),
`organization` (a titled org chart — a reporting hierarchy, and the **fourth** node-link type. Its
input is one row per PERSON: an employee (`x_col`), their manager (`target_col`, reused from sankey —
a link is a link) and an optional job **title** (the one **new** kwarg, `title_col`, since a title is
not a weight — so this is the one node-link type whose cache layer is **not** untouched). The manager
is the far end of the reporting link, so the `{from, to}` link is built `{from: manager, to:
employee}` — the one node-link type whose two columns are **swapped** into from/to, because the
natural CSV names the child first and Highcharts draws `from` as the parent (the tree flows **down**).
A blank/whitespace/missing manager is a **root** (the CEO): it draws no incoming link, so — unlike
sankey, which *drops* a link missing an end — the row simply contributes no edge, its person still a
node via the nodes array and via being someone else's manager. `_is_top_level` decides "root" and is
reused **verbatim** from sunburst, because a manager IS a parent — and it is why the build and
`count_marks` both read `not _is_top_level(mgr)` and **not** `_label_ok(mgr)`: `_label_ok("")` is
True, so a bare label check would draw a phantom link from a nameless `""` node (the bug the render
caught). Both node columns go through sunburst's `_node_key`, so an integral-float employee id matches
itself across the two columns. It is **unweighted** like networkgraph — empty `y_cols`, no Y control —
the two named `UNWEIGHTED_NODE_LINK_TYPES` so the empty-`y_cols` guard, the app's numeric-columns
gate, its Y-control removal and its empty-selection warning read one constant; and it joins
`NODE_LINK_TYPES` for the shared target-required and source≠target guards and the Target control
(relabelled **Manager (to)**). What makes it a distinct **type** and not a networkgraph re-skin is
the one thing highcharts-core lets it *keep* that sankey/networkgraph silently drop — a modeled
`nodes` array — so each box carries a per-node **title** drawn under the name (deduped by node key,
first title wins; omitted entirely without a `title_col`, a plain name-box hierarchy). Its marks are
the reporting lines, so it needs a `count_marks` rule and a `MARK_METRICS` entry (**Reports** — one
per employee with a real manager; a root's box draws but its non-existent line does not, so the count
never exceeds the row count). Drawn top-down (`chart.inverted`); it **cycles** the palette across
nodes (each box a distinct identity like a pie slice — Highcharts' *default*, so the builder sets no
per-node color and no `colorByPoint`, an explicit series `color` being overridden), and — unlike
every weighted node-link type — needs **no `_themed` hook at all** (its boxes carry no white border
to dissolve; the name/title text rides Highcharts' `contrast` color), joining boxplot and networkgraph
in that. Pulls in `modules/organization` **plus** `modules/sankey` (both from `chart.type` alone;
*not* `highcharts-more`), and — organization.js **extending** the sankey series — hits the identical
reversed-emission bug dependencywheel does, so `_order_script_tags`/`_MODULE_LOAD_ORDER` was
**generalized** from a single hardcoded pair to a **list** (the "a second edge would generalize it"
the code's own comment predicted). All of the palette / no-hook / inverted / cycle facts were decided
by **rendering** in both themes),
`boxplot` (per-category Tukey distributions — the **first** type whose builder
*aggregates* (the gauge family is the second, and says so): every other maps rows 1:1 onto marks, but a box summarizes many rows.
The data is long/tidy — `x_col`'s values *repeat*, one row per observation — and each
distinct `x_col` value becomes one box over that group's raw `y_cols[0]` numbers,
encoded as a positional `[low, q1, median, q3, high]` 5-array matched to
`xAxis.categories` *by position*, since a `{name, low, …}` dict point collapses with
the name in the leading `x` slot. Whiskers follow `matplotlib.cbook.boxplot_stats`:
pandas' default linear quantiles, 1.5×IQR fences with *inclusive* membership (so a
zero-IQR group isn't read as all outliers), and `low`/`high` clamped to `q1`/`q3` at
both ends. Observations are cast to `float64` first (a text column raises `ValueError`,
as `float(v)` does in the pointwise branches) and reduced to the *finite* ones — an
infinity can't size a whisker and would turn the whole box to nulls, since
`iqr = inf - inf = nan`. Observations strictly beyond the fences become a second, linked
scatter series, emitted only when some exist. Groups keep first-appearance order
(`groupby(sort=False)`); a group whose observations are all missing keeps its axis
slot as an `EnforcedNull` box, while a row whose `x_col` is missing names no category
and forms no group. It shares bubble's and radar's `highcharts-more` module, and is
the **first** mark-styling type with *no* `_themed` hook (arearange, networkgraph, organization
and dumbbell have each since joined it, every one for its own measured reason):
`plotOptions.boxplot.fillColor`
and `stemColor` are accepted by `Chart.from_options` and then silently dropped (and
`ExportServer.global_options` is no side door — it is coerced through the same model),
so the box interior can't be set at all. It falls back to Highcharts' own
`var(--highcharts-background-color)`, which the `color-scheme` pin below resolves to
white in both themes, while `colorByPoint` gives each box a palette-hued
border/whisker/median legible against that white), and `waterfall` (a cumulative
"bridge" — the category-x data shape read as signed **deltas** rather than levels, so
each bar floats where the last one ended and the chart shows how a starting value
*becomes* an ending one. `x_col` names each step and the first `y_cols` column gives
its signed change; a missing/non-finite delta keeps its axis slot as an `EnforcedNull`
(the `_num` rule, not pie's drop-the-row), because a null delta reads as "no change" —
Highcharts draws no bar and carries the running total straight through, which is
exactly true. The builder then **appends** a closing `Total` bar (`{"isSum": True}`,
which makes Highcharts sum the preceding deltas itself so the bar reaches down to zero
as a *level* rather than stacking as one more delta) — it is what makes the chart a
bridge rather than a row of floating bars, and it made waterfall the **first** type whose
mark count exceeds its row count (`sunburst`'s appended root is the second, and says so);
it is appended only when there is at least one step
to sum. Bars are colored by **meaning**, not identity — green rise, red fall, brand-blue
total, read straight from `DEFAULT_COLORS` by index rather than from the *overridable*
`colors` list, the `_BOXPLOT_OUTLIER_COLOR` rule for both of its reasons (a short custom
palette can't `IndexError`, and red-means-loss is the chart's semantics, not a series'
arbitrary identity, so a custom palette must not repaint a fall green). The total's
`color` is carried **per point**, which takes the total *off the up/down scale entirely*.
Left alone, Highcharts colors a sum by its OWN sign, exactly as it colors a delta (a
positive total goes green, a negative one red — verified by rendering, not assumed); but
green does not mean the same thing on the two kinds of bar. On a delta it says "this step
added"; on the total it would say only "the end level is above zero", which a bridge that
fell 420 → 79 would earn just as cheerfully. Same hue, two claims. So the total is marked
as the different KIND of bar it is: a **level**, not a change. It labels each bar with
its delta — gated on step count like heatmap's cells and sankey's links — because unlike
column/bar (which carry no labels) a waterfall's bar floats at the running total and
encodes its value as a *length*, not a height above the axis, so no axis can be read
against it. It shares bubble's, radar's and boxplot's `highcharts-more` module, and it is
the **first** type to need **two** `_themed` hooks (`bullet` is the second, and the two pairs
have nothing in common: bullet's *is* the column/bar dissolve plus a hue flip on a MARK) — and
here *neither* is the column/bar case, since
waterfall's border and connectors both default to a fixed `#333333` (measured off the
rendered PNG) rather than the background variable that resolves to white for column/bar,
so its bars are never ringed white. `borderColor`: that crisp definition line on the white
shell becomes a muddy grey ring one shade off the dark background, and buys nothing (a
waterfall's bars never touch), so it is dissolved into the background as pie/treemap/sankey
dissolve their gaps. `lineColor`: the *connector* lines — the only line Highcharts draws
*between* marks, and what makes the chart read as a running total at all — survive on the
dark background only barely, so they are lifted to the axis color), and `sunburst` (a
hierarchy drawn as concentric rings — the only type that reads the frame as an **adjacency
list**: each row is one node, named by `x_col`, placed under the node named in `parent_col`
(a blank/missing/whitespace parent means a top-level branch — the one place in the module
where a missing label is a *statement* rather than an error), and, *if it is a leaf*, sized
by the first `y_cols` column. So it is also the only type whose marks are not in the data:
the tree has to be **assembled** before anything can be drawn, which is what `_sunburst_tree`
does — and, since a node's fate depends on its *ancestors* (a dangling parent, a cycle) and
on its *descendants* (a valueless internal node lives only if a leaf under it does), it is the
one type whose drops are not a per-row mask at all. `count_marks` therefore reuses not the
drop predicates but the *whole build*, which is a stronger form of the can't-drift rule than
any other type gets: the KPI is `len(series[0]["data"])` by construction.

Node ids are **synthesized** (`n0`, `n1`, …), never taken from the labels. A label is not a
key: two rows may legitimately share one — an `Other` bucket under both Sales and Marketing —
and label-as-id would hand Highcharts two points with the same `id`, which is not a silent
mismatch but **error #31, "Non-unique point or node id"**, printed in a red band across the
chart (verified by rendering). Synthesizing makes that unreachable: CSV text lands only in
`name`, so nothing in a hostile file can collide with anything, and the twins stay two honest
sectors rather than merging into one worth a sum nobody asked for. The label-keyed shape's one
real cost is then paid exactly once, and only where it is genuinely unpayable — a duplicate
label that is *used* as a parent names no single node, and the alternatives (merge them, or
pick one and graft a subtree onto the wrong branch) are both silent lies.

That is the type's organizing split, and it is `_sunburst_tree`'s whole design: everything
wrong with an adjacency list is either **missing data**, which has a right answer and is
*dropped* — a dangling parent (with its descendants, transitively: Highcharts does not leave an
unmatched parent alone, it silently *re-parents* the child to the root, promoting an orphaned
grandchild into ring 1 and lying about the data), or a leaf value that can't size an arc — or a
**contradiction**, which has no right drawing and *raises*: a cycle, an ambiguous parent. The
two are told apart by one iterative walk up the parent chain (iterative because a 50,000-deep
chain is valid input and a 50,000-long cycle is reachable input) that simultaneously grounds
each node, drops the unreachable, and raises on a loop. Order is moot, and provably so: no node
in a cycle can ever be dangling, so dropping a dangling row can never break one. The
contradiction comes back as a **returned message**, not a raised one — that is what keeps
`count_marks` *total*, and it matters, because the app's KPI row runs *above* its guards, so a
`count_marks` that raised on a cyclic CSV would blow the page up with a traceback before the
warning explaining it could render.

`_sizable` is `_plottable` widened by one comparison, and it is the type's own predicate for a
reason: Highcharts draws no sector for a **negative** leaf *and* excludes it from its parent's
sum (verified by rendering — a `-400` leaf beside a `500` one drew nothing and left its parent
sized 500, not 100), so keeping the row would make the KPI count a mark the chart never draws.
An arc has no negative length and a part-of-whole has no negative part, so the row is dropped —
pie's and treemap's rule. Zero is *kept*: a real measurement, a zero-width sector, and it
corrupts no sum.

An internal node carries **no value**, and this is not deference to Highcharts but the only
honest option: an explicit parent value *overrides* the children-sum, so emitting a CSV's
subtotal row draws a parent whose arc disagrees with the arcs inside it (verified by rendering —
two branches each declaring `value = 1` drew as equal halves while holding 900 and 100). It
would go wrong even when the subtotal is *right*, the moment one child row is dropped: the
parent would keep claiming the full total with a child missing beneath it. Omitting it makes a
parent's arc always equal what is actually drawn under it — the discipline `count_marks`
enforces on the KPI, applied to the geometry. Its corollary is not a special case but the rule
itself (`keep(n) = the value can size an arc, OR something under n survived`): a node whose only
child was dropped *becomes* a leaf, and then its own value is what sizes it.

A **root** sector is **appended** — waterfall's Total set the precedent for drawing a mark the
frame never held, and this is the second such type, so its count likewise exceeds its row count.
It carries no value (internal by construction, so the centre reads a total Highcharts computes
rather than one the builder asserts) and a color taken **off the categorical scale entirely** —
waterfall's Total argument, transposed and sharper: ring 1 *cycles* the palette, so no palette
entry is guaranteed not to be some branch's hue, and the only way to say "this is not a
category, it is the whole" is a neutral from outside it. (Left unset, Highcharts paints it one
of its own defaults — a cyan in no palette of ours.) It is appended only when at least one node
survives: a lone slate disc labelled `All` is not a chart.

Ring 1 is seeded with a per-**point** `color` from the *overridable* `colors` list — a branch's
hue is its arbitrary identity, like a pie slice's, the opposite of waterfall's semantic
red-means-loss — and every descendant then **inherits** its branch's hue for free, separated
from its siblings by a `levels[].colorVariation` whose sign *alternates* per ring (the variation
applies to the parent's already-varied color, so a fixed `-0.5` walks a deep tree to black). It
has to be seeded per point, because *both* obvious alternatives are traps: the canonical
Highcharts recipe, `levels[].colorByPoint`, is accepted by `Chart.from_options` and then
**silently dropped** (sankey's `nodeFormat` / boxplot's `fillColor` / treemap's `value`-not-`y`
again), while the `colorByPoint` that *does* survive is the series-wide one, which would hand
every point in the flat data array its own hue — deep descendants included — destroying the very
inheritance the scheme rests on. It labels each sector with its **name only** — the one type
that breaks the print-the-value-in-the-mark rule the other five keep — because a sector is a
thin *curved* arc with the text bent along it, so there is room for one short string, and the
name is the only thing identifying a sector (a sunburst has neither axis nor legend) while the
value is already the *angle*. `allowTraversingTree` makes a click re-root the chart on that
branch. It needs **one** `_themed` hook — `borderColor`, the white sector rings that pie,
treemap and sankey each dissolve — and pulls in `modules/sunburst`, and, unlike
bubble/radar/boxplot/waterfall, *not* `highcharts-more`), and `xrange` (a Gantt-style
timeline, and the only type whose mark has **extent** along the x axis rather than sitting at
a point on it. Each row is one bar, on the **lane** named by `x_col` — and here `x_col` is not
an x axis at all: the lanes are the categories of the **Y** axis, so its values *repeat*
(boxplot's long/tidy shape, but a lane holds 0..n bars rather than aggregating into one
mark), and `y` is a *position* into `yAxis.categories` rather than a value (boxplot's
positional trick again). The bar spans from the first `y_cols` column to `end_col`.

Those two are the type's real novelty: they are **coordinates**, not magnitudes. Every other
type's value column answers *how much*; these answer *when*. So the module gains a third
column role beside the LABEL (`_label_ok`, "this names a mark") and the VALUE (`_plottable`,
"this sizes a mark") — the COORDINATE (`_coordinates`, "this positions a mark"), which may be
a **date**. It is sniffed once per column, and the sniff is **dtype-first**, which is not
fastidiousness but the only safe order: `pd.to_datetime(12)` does not fail, it returns
`1970-01-01T00:00:00.000000012`, so a "try dates, fall back to numbers" sniff would silently
move a column of sprint numbers to an instant at the epoch. A numeric dtype is therefore never
shown to a date parser at all; a `datetime64` dtype is a date; and only an **object** column is
a genuine question — answered by counting how many cells each coercion recovers, with the date
parse **pinned to ISO-8601**. That pin is load-bearing too: pandas' default parser is wildly
permissive on free text, and `pd.to_datetime(["Jan","Feb","Mar"])` *succeeds*, returning **year
1 AD** — which is `_revenue_vs_cost`'s `month` column, the app's **landing dataset**, so a
permissive sniff would offer a date axis on the page you see when you open the app. (`utc=True`
for a third reason: `errors="coerce"` is not total without it — a DST-crossing column raises
"Mixed timezones detected" even under `coerce`, and this code runs *above* the app's guards.)
The dates then become epoch **milliseconds** via `_epoch_millis`, which normalizes the
resolution *before* taking the int64 view rather than dividing after it: `.astype("int64")`
reads a datetime column in its OWN resolution, and this project's pandas hands back
`datetime64[us]`, not the `[ns]` an obvious `// 1_000_000` would assume — that divisor renders
`2024-01-05` as `1970-01-20`, every bar in the correct *relative* order at catastrophically
wrong *absolute* dates, drawn confidently, with no error anywhere.

`_spannable` is the module's first **two-argument** predicate, because an interval's validity
is a fact about the **relation** and not about either end — `_sizable` widened to a *pair*
rather than by one comparison. Both ends must be `_plottable` before they are compared, and
the finiteness half is load-bearing: `end >= start` alone accepts `(-inf, 10)`, which would
put a bare `inf` in the emitted JS. Then the comparison decides two *asymmetric* fates. A
**milestone** (`end == start` — a launch date, a deadline, a same-day task, one of the
commonest Gantt rows) is **kept**, exactly as `_sizable` keeps its zero; Highcharts draws
nothing for it unaided (verified by rendering: an empty lane), so it is floored to a visible
sliver with `minPointLength`, which is what makes *counting* it honest rather than dropping it
being necessary. A **backwards** bar (`end < start`) is **dropped**: left in, Highcharts draws
a bar spanning the ENTIRE axis (verified by rendering) — not a visible error but a confident,
plausible lie that reads as the longest task in the project, the xrange counterpart of
sunburst's silent re-parenting. It drops rather than raises for `_sizable`'s reason: there IS
a right drawing (nothing), unlike a cycle, where every alternative is a lie.

The contradictions that *do* raise are **column**-level, decided once, with no per-row right
answer: a start/end column that is neither dates nor numbers, or two that disagree about which.
Returned as a message rather than raised (the `_SUNBURST_CYCLE` rule) so `count_marks` stays
total. Only *one* of the two is reachable from the app — the date-beside-a-number mismatch —
since `coordinate_columns` keeps a text column out of the pickers; the other is reachable only
through the pure builder API.

`_coordinates` therefore has a **fourth** answer, `_COORD_EMPTY`, and it is not a kind but the
absence of one — the fix for a bug the review caught. An unfilled column is missing **data**
(every row drops, the chart comes out empty), and it must not be allowed to masquerade as a
kind, because a kind is a claim about an *axis* and an empty column makes no such claim. The
dtype dispatch cannot tell the difference on its own: a blank CSV column arrives as all-`NaN`
`float64`, so `is_numeric_dtype` says "number" with total confidence — and that phantom number
then collides with a real date partner and raises, telling the user their empty End column
"reads as numbers", which is both false and unactionable. It is not a corner case (it is a
Gantt template whose end dates nobody has filled in yet, straight out of `read_csv`), and the
bug was *asymmetric*: an empty column beside a numeric partner agreed by coincidence and worked,
so only the **date** case — the type's headline use — was broken. Hence the empty test runs
*first*, above the dtype dispatch, and an empty column abstains from the start-vs-end vote
rather than vetoing it. A lane whose every row dropped never enters `yAxis.categories` at all — boxplot keeps
an all-missing group as an `EnforcedNull` box because there the group IS the mark, but a lane
holds 0..n bars, so there is nothing to null out: pie's drop-the-row family, no ghost lane.

Bars are colored **per lane**, seeded per **point** from the *overridable* `colors` — a lane's
hue is its arbitrary identity, like a pie slice's (the opposite of waterfall's semantic
red-means-loss), and every bar in a lane shares it, which is what makes a task's phases read as
one thing. Here the `colorByPoint` trap is the **mirror** of sunburst's: where sunburst's
`levels[].colorByPoint` is silently *dropped*, xrange's series-level one *survives perfectly* —
and is the wrong option, since it would hand every BAR its own hue. It is the **first** mark-bearing
type that prints **nothing** in the mark and needs no gate constant either — columnrange, arearange,
bullet and dumbbell have each since reached the same place from this very premise, and variwide from
its own (a variwide's width lands on no readable axis at all, so its silence needs a different
argument and its width goes in the tooltip instead). It is put as the CRITERION rather than as a tally of the types on
each side, because such a tally goes stale on every added type and nothing but a reader can check
it: a type prints a value in the mark exactly when the value can be read against no axis (an angle,
an area, a link's width, a bar floating above an invisible running total), but an xrange bar's two
ends BOTH land on a real, ticked x axis that renders in the Static PNG too — column/bar's case,
not waterfall's — and there is no second identity to print, since the lane name IS the y-axis
category. Its tooltip uses `{point.name}`, which is waterfall's *fix* and xrange's **bug** in
mirror image: `{point.category}` reads the X axis, and an xrange's categories are on the Y, so
it renders the raw x value (a tooltip reading `1767571200000` — verified by rendering). It
needs **one** `_themed` hook, and it joins **column/bar** rather than waterfall — the other
bar-shaped type, which needs the opposite treatment. That was *measured*, not inferred from the
shared bar base class: waterfall is the standing proof the inference is unsound, its border
being a fixed `#333333`, while xrange's default border is pure white (the background variable),
so every bar is ringed white on the dark background until it is dissolved. Pulls in
`modules/xrange`, and, like sunburst, *not* `highcharts-more`), and `columnrange` (floating
vertical bars, each spanning a **low** to a **high** per category — a min–max range, and
xrange's cousin along one axis and its **opposite** along the other. Both draw a bar from a low
to a high, but xrange's pair are **coordinates** (they position a bar, may be dates, answer
*when*) while columnrange's are **magnitudes** (they size a bar, must be finite numbers, answer
*how much*). So it reuses xrange's UI *shape* — a second value-column selector, low = `y_cols[0]`
and high = a dedicated **`high_col`** — but **not** xrange's `end_col` kwarg: a coordinate that
may be a date is a different column role than a magnitude that must be `_plottable`, sourced from
a different picker (`numeric_cols`, not `coordinate_columns`), so reusing it would be the "a link
is a link, but a coordinate is not a magnitude" lie. Its `x_col` is a genuine category X axis (the
bars stand **on** it, drawn vertically — column/bar's shape, not xrange's lanes-on-the-Y), so it
**joins** `X_IN_Y_GUARD_TYPES` where xrange could not, catching `x_col == low` as the classic
x-in-y collision; the *other* collision, `low == high`, gets a dedicated guard (xrange's start-is-
end rule, one type over), since `high_col` isn't in `y_cols` and that rule can't express it.

Each point is a `[low, high]` **2-array**, not a `{low, high}` dict, and that is the boxplot
lesson one type over: a numeric-first 2-array is read unambiguously as `[low, high]` and survives
`to_js_literal` intact (verified against the round-trip), whereas a dict whose null end
highcharts-core silently drops would draw a half-bar. `_range_point` decides the whole point once
— it is `_num` for a **pair**: the slot survives only when both ends are `_plottable`, else it
becomes a bare `EnforcedNull` (a kept category tick with no bar, the category-x keep-the-slot
family — column/bar/waterfall — never a half-drawn range). An **inverted** range (`high < low`) is
**KEPT**, drawn spanning `[min, high]`, and that is the mirror of xrange's backwards bar and the
sharpest thing about the type: a columnrange bar is *bounded by its two values*, so `8 → -3` draws
the same honest bar as `-3 → 8` (verified by rendering), whereas an xrange backwards bar spans the
*whole axis* — a confident lie, so xrange *drops* it. Same shape, opposite verdict, because one is
honest and one is not. Bars take a **single brand hue**: a columnrange is one measurement across
the axis, so `colorByPoint` stays off (its Highcharts default), the opposite call from
pie/treemap/xrange, whose slices/lanes *are* separate identities. It is a single low/high series,
so like xrange its one series would misreport the KPI as a bare `1`: it needs a `count_marks` rule
(waterfall's, *without* the appended total — one bar per drawable label, a missing/inverted range
kept as a null slot and still counted, so it never exceeds the row count) and a `MARK_METRICS`
entry (**Ranges**). It prints **nothing in the mark** and needs no gate constant — xrange's rule
reached from xrange's premise: both ends land on a real, ticked y axis that renders in the Static
PNG too (column/bar's case), and the only other identity, the category name, is already on the X
axis. Its tooltip uses `{point.category}` (waterfall's fix, not xrange's bug: a columnrange's
categories are on the X axis, so `{point.category}` reads the right one) plus `{point.low}` and
`{point.high}`. It needs **one** `_themed` hook — the `borderColor` dissolve it shares with
**column/bar/xrange**, and *not* waterfall, which was **measured** (its default border is pure
white, the background variable, exactly column/bar's case, not waterfall's fixed `#333333`) rather
than inferred from the shared bar base class. Pulls in `highcharts-more` from `chart.type` alone
— like bubble/boxplot/waterfall, and *not* a phantom `modules/columnrange`), and `arearange`
(columnrange's **filled-band mirror** — the same low/high magnitude data (`low` = `y_cols[0]`,
`high` = a **reused** `high_col`), drawn as **one continuous filled band** between a low line and a
high line instead of N discrete bars. The two are byte-identical in the options tree **modulo the
`chart.type` string**, so arearange **shares columnrange's build branch**, keyed by `chart_type` —
the **funnel/pyramid** "differ only in the type string" pattern, *not* the columnrange/xrange split
(a coordinate is not a magnitude, but a band **is** a bar's fill). The shared sites — the build
branch, the two `high_col` guards, the `count_marks` rule, `X_IN_Y_GUARD_TYPES` membership and the
app's High control — are bound by a new **`MAGNITUDE_RANGE_TYPES` = `COLUMNRANGE_TYPES` +
`AREARANGE_TYPES`** constant (the `WEIGHTED_NODE_LINK_TYPES` "name the family so the sites can't
drift" rule), and it reuses columnrange's `high_col` — a high is a high, **no new kwarg**, so the
cache layer is untouched (networkgraph's/dependencywheel's win). It reuses `_range_point` intact: a
missing/non-finite end is a bare `EnforcedNull` that **breaks the band** (verified by rendering: the
fill splits, honestly "no data here", rather than bridging the gap and implying data — a *keep-the-
slot* that reads differently on a continuous band than on independent bars), and an inverted range
(`high < low`) is **kept**, drawn as an honest crossover pinch (verified by rendering), the mirror of
xrange's *dropped* backwards bar exactly as columnrange keeps it. Single **brand hue**, `colorByPoint`
off (a band is one measurement); `{point.category}` tooltip (categories on the X axis). The **one**
thing NOT shared, and the reason a shared branch is still honest, is the `_themed` hook: columnrange
dissolves a white **bar border**, but an area **fill has none** (`area`/`areaspline` "paint no white
against the dark background"), so arearange is deliberately **out** of the border-dissolve group and
needs **no `_themed` hook at all** — **measured by rendering** in both themes (a dark-mode band with
no white ring), never inferred from the shared area base class (the waterfall lesson, in mirror: there
the inference from the *bar* base class was unsound, here the render *confirms* the analogy to the
*area* base class rather than trusting it). The divergence is orthogonal to the branch — `_themed` is
keyed on `chart.type` independently — which is what lets the branch stay shared. Its marks are the
band's `(low, high)` **points**, so like columnrange it needs a `count_marks` rule and a `MARK_METRICS`
entry — **"Points"**, a noun *distinct* from columnrange's "Ranges" on purpose: a band is one shape, so
the count names its vertices rather than implying N discrete ranges. Pulls in `highcharts-more` from
`chart.type` alone, *not* a phantom `modules/arearange`), and `bullet` (a KPI strip — columnrange's
**data shape read as a COMPARISON rather than as a range**, which is the whole of the type. Both
take a category X axis and two magnitude columns and draw one mark per category; but a
columnrange's two numbers are the two ends of **one** bar, while a bullet's are two **independent
channels** drawn as two shapes: a filled bar from zero to the **measure** (`y_cols[0]`) and a
crossbar floating over it at the **goal** (a new `goal_col`). That is why it does **not** join
`MAGNITUDE_RANGE_TYPES` and does **not** reuse `high_col` — a high is the far END of the mark it
shares a point with, a goal is the REFERENCE that mark is read against; the `title_col` "a title is
not a weight" precedent, here "a goal is not a high" — so it is one of the **three** recent types
that **do** touch the cache layer (`variwide`'s `width_col` and `dumbbell`'s `after_col` are the
others, each reaching the same conclusion from its own premise: a width is neither the far end of
the mark nor a reference it is read against but the mark's other DIMENSION, and a before/after pair
is the same quantity at two ORDERED moments).

The independence is the type's **policy**, not a nicety, and `_bullet_point` is `_range_point`'s
shape with the opposite verdict on the same input, which is why it is a second helper rather than a
widened one. A columnrange nulls the whole slot all-or-nothing (a range with one end is not a
range); a bullet nulls **each end alone**, because half a comparison is still worth drawing. All
four combinations were **verified by rendering**: measure-with-no-goal draws a bare bar with
nothing to compare it to, goal-with-no-measure draws a lone reference line over an empty slot,
neither keeps the category tick (the keep-the-slot family — column/bar/waterfall/columnrange), and
an inverted pair (a measure far under its goal) is the **ordinary reading** of a type that exists to
answer "did we hit it", not xrange's whole-axis lie. Nothing is dropped, nothing raises, hence no
`explain_bullet_error`.

The **goal slot is the module's one exception to the `EnforcedNull`-not-`None` convention**, and it
is exactly **one slot wide** — which is what keeps it small enough to be believed rather than
tidied away. The measure takes `_num` (`EnforcedNull`, this module's rule everywhere else); the
goal must be Python `None`, because `options/series/data/bullet.py`'s `target` setter runs
`validators.numeric(value, allow_empty=True)`, which admits `None` and rejects `EnforcedNullType`
with `CannotCoerceError` — raised at `Chart.from_options`, **one layer below `build_options`**. So
an options-dict assertion passes green while the chart cannot be built at all, and the app's
interactive path (which does not catch builder errors) shows a bare traceback naming neither
`target` nor `bullet`: the `_NEEDLE_DIAL` trap in a different validator. It is pinned by a test
that drives `make_chart`, the only layer at which it is observable, and written into `Conventions`
below so it is not "fixed" back.

The point is a `[measure, goal]` **2-array**, never a dict, and that is structural in two
directions a reader would not guess. First, the literal key `target` **never appears in the emitted
JS** — the value survives *positionally* — so `assert "target" in js` is **false on a correct
bullet chart**, inverting this module's dominant test idiom. Second, any key outside
`{x, y, target, name}` forces the point **dict** form, in which a `None` target *vanishes* entirely
rather than nulling while `EnforcedNull` there still raises: in dict form a goal-less row has **no
working spelling at all**. That is the second and stronger reason bullet takes a **single brand
hue** with `colorByPoint` pinned to appear **nowhere** — and unlike networkgraph's and sunburst's
pins, this one guards a real decision rather than restating a library limitation, since a bullet's
`colorByPoint` *survives* the round-trip at both the series and the `plotOptions` level (verified).
The decision itself is columnrange's: a bullet is one measurement read against one goal across the
axis, so a per-bar hue would assert a categorical identity the categories don't have — the opposite
call from pie/treemap/xrange.

The **crossbar trap** is the sharpest bug this type could ship, and it was found by **rendering**.
Left unset, the goal marker takes the *series* hue — the same blue as the bar it crosses — and
Highcharts draws it at **140% of the bar width**. So it does not vanish, which would at least be
obvious: the segment crossing the bar disappears into the fill while the two overhangs survive as
small stubs either side, reading as a deliberate tick rather than as a goal line. It strikes
**exactly when the measure exceeds the goal** — the "we beat plan" row, the one a reader most wants
to find — so the failure is invisible on the rows that look fine and silent on the rows that
matter. The tempting fix is the geometry, and it is both the wrong lever and a trap:
`targetOptions.width = 0` raises `EmptyValueError` out of a validator naming neither the key nor
the series, and every numeric key under `targetOptions` rejects a `numpy.int64` outright. The
problem is **contrast**, so the fix is the colour and Highcharts' 140% × 3px default is left
entirely alone (the pane-`size` "stop steering" rule, the funnel/pyramid "the defaults are right"
call). Setting no numeric key there, and deriving none from the frame, makes both traps unreachable
rather than remembered.

So it needs **two** `_themed` hooks. The first is the `borderColor` dissolve, where bullet is the
**fifth** member of the literal tuple (`column`, `bar`, `xrange`, `columnrange`, `bullet`,
`variwide`) — joined
on a **measurement**, not on an inference: its bars are a column subclass, but so are waterfall's,
and waterfall is the standing proof the base class settles nothing (its border is a fixed
`#333333`). Rendered in dark mode a bullet's bars come back crisply ringed white, the background
var, column/bar's case exactly. The tuple stays a **literal**, because arearange is deliberately
absent from it despite sharing columnrange's branch — extend it, do not swap it for a family
constant. The second is the crossbar's own hue, and it is the **only `_themed` hook in this module
that flips a MARK rather than chrome**. That is a principle, not a preference: at 140% width the
marker necessarily crosses **both** the bar (a constant palette blue in both themes) *and* the
background (white → slate), so a fixed colour cannot work **in principle** — a near-black reads on
the light shell and disappears on the dark one, a near-white does the exact reverse, and both were
rendered to confirm it.

That "in principle" is now **arithmetic** rather than a rendered impression, and the arithmetic
changed the fix. Against the theme's palette, clearing WCAG 3:1 on the slate background needs a
relative luminance ≥ 0.25 and on the palette blue needs ≤ 0.087: the two ranges do not overlap, so
no single value exists *at all*. The flip therefore carries **two** values in dark mode — a light
fill (16.3:1 on the background) plus `_BULLET_TARGET_BORDER_WIDTH` of `_DARK_CHROME["bg"]` border
(7.0:1 on the bar) — because a mark spanning two surfaces needs one value per surface. Light mode
keeps a single near-black fill, which does clear both (17.9:1 and 7.0:1); the border is a
dark-mode repair, not part of the mark.

This was found the hard way: adopting the theme's palette lightened the bar from `#2563eb` to
`#60a5fa` and dropped the fill's contrast against it from 4.19:1 to **2.32:1**, and *every* bullet
test stayed green — they each assert one hue at one path, and legibility here is a property of a
**pair**. The test now states the pair as a rule (each surface must have a ≥ 3:1 partner among
{fill, border}) rather than as a hex, so the next palette is checked too. Where every border
dissolve above matches a mark **to** the background,
this one matches it **against** the background; `_BULLET_TARGET_COLOR` is `_DARK_CHROME["bg"]` read
the other way round, so the pair the crossbar swings between is exactly the pair the app shell does
and neither can drift (`_NEEDLE_PIVOT_COLOR = _SUNBURST_ROOT_COLOR`'s aliasing rule). Highcharts'
`contrast` is no help: it computes against the fill a *label* sits on, and this is a shape.

It carries **no qualitative plot bands**, and that is a decision rather than an omission: the
poor/average/good bands every bullet demo draws are a **business judgement**, and a three-column CSV
states none — drawing them would be this module's standing offence, emitting a mark the data never
made. Same family as sunburst refusing to emit a CSV's own subtotal as a parent value, and
waterfall's Total being an `isSum` Highcharts computes rather than a number the builder asserts.

It is drawn **vertically**, and — unusually for this module — that was **not** decided by
rendering: both orientations render correctly in both modes and both themes, and the comment says
so rather than borrowing the authority of a render it did not need. It is a **consistency** call,
decided by the two sentences it would otherwise falsify: `X_IN_Y_GUARD_TYPES` admits bullet on "its
`x_col` is a genuine category X axis, the bars stand ON it, drawn vertically", and `_themed`'s
tuple admits it as the fifth bar-shaped type measured to ring white. Inverting would leave both
true in the options tree and false on the page — the exact divergence class this module catches by
rendering. (Inverting buys room for long category labels, which is a property of the *dataset*, not
of the type, and which the app already answers with the user's own column-vs-bar lever; a second,
type-baked answer to the same question is the steering the pane-`size` lesson says to stop doing.
The one inverted type here, organization, is inverted because its domain forces it — a hierarchy
flows down. A bullet's sideways convention is a convention.)

Its marks are the measure bars, so like columnrange its single series would misreport the KPI as a
bare `1`: it needs a `count_marks` rule and a `MARK_METRICS` entry (**Measures** — the bar being
only half of what a bullet draws, so the noun counts the pairing, not the rectangles). The rule is
one bar per drawable **label**, waterfall's without the appended total — the same number columnrange
returns, by a **different argument**, which is what earns it its own branch. It prints **nothing in
the mark** and needs no gate constant — *xrange's rule reached from xrange's premise*, exactly as
columnrange reached it: both numbers land on a real, ticked, gridlined y axis that renders in the
Static PNG too, the goal is *drawn* on that axis rather than printed, and the only other identity is
already on the X axis. A bullet's dataLabels default **off** (column/bar's behaviour, not a gauge's,
which default on and must be disabled explicitly), so the omitted key **is** the gate. Its tooltip
is `{point.category}` / `{point.y}` / `{point.target}`: the categories are on the X axis, so
`{point.category}` reads the right one (waterfall's fix, columnrange's reason) and `{point.name}` is
**blank** here anyway (positional arrays). `{point.target}` *resolves* despite the literal key never
reaching the JS — the same positional survival — and it is the only place the goal's **number** can
be read at all, the crossbar saying "here is the line" and the tooltip saying what it is. The two
column names are **labelled** rather than run together, and that is what makes a goal-less row
legible: on a null goal `{point.target}` renders as **nothing at all** (not the token `null`, not
`undefined` — verified by rendering), so the labelled form degrades to a clean "quota:" with no
value where a run-together "120 of {point.target}" would trail off mid-sentence. Pulls in
`modules/bullet` from `chart.type` alone and **not** `highcharts-more` — the plausible guess the
round-trip corrects, as for columnrange and funnel — and needs **no** `_MODULE_LOAD_ORDER` entry:
`bullet.js` declares `@requires highcharts` only, unlike dependency-wheel and organization (which
require `modules/sankey`) and solid-gauge (which requires `highcharts-more`)), and `variwide` (columns
whose **WIDTH** is a second magnitude — columnrange's data SHAPE read a **third** way, and the third
reading is the whole of the type. Line the three up, because every decision falls out of the
difference: a **columnrange**'s two numbers are the two **ends of one mark** (neither means anything
alone — the mark IS the span between them); a **bullet**'s are two **independent claims** about one
category on the **same** channel (what happened, what was meant to); a **variwide**'s are **one claim
spread over two geometric channels** — a height and a width, whose reading is their PRODUCT, the
bar's **AREA**. The width is not compared to the height and is not the far end of it: it **weights**
it.

So `width_col` is a **new** kwarg, the **eighth**, and the **third** that is not a reuse. Not
`high_col` (a high is the far END of the mark it shares a point with, a Y magnitude on the low's own
axis, while a width sizes the mark's X extent — "a coordinate is not a magnitude" transposed: *a
width is not a high*). Not `goal_col` (a goal is a REFERENCE ON THE SAME AXIS the measure is read
against, and bar-vs-crossbar is two lengths compared, while a width is not compared to the height at
all — it multiplies it). `title_col`'s and `goal_col`'s precedent a third time: the dtype and the
picker source match an existing kwarg exactly, and the **role** is what differs. The cost is worth
stating because it is the largest consequence of the call — variwide **touches the cache layer**
(three wrappers, three call sites, a `_FORWARDED` entry), which arearange and dependencywheel escaped
by reusing. Buying that back would have meant the lie. It joins `X_IN_Y_GUARD_TYPES` (its `x_col` is
a genuine category X axis — the bars stand ON it, drawn vertically) and **not**
`MAGNITUDE_RANGE_TYPES`, which binds five sites where columnrange and arearange are byte-identical
modulo `chart.type`; variwide shares **none** of them, so joining would be exactly the "consistency"
edit this file keeps warning about.

Its two value columns take **different predicates**, and it is the **first** type here that needs to.
The height is `_plottable`; the **width is `_sizable`** — sunburst's non-negative predicate, borrowed
with its argument intact, because a width is a **share of a total**. That is the type's organizing
hazard and it was **measured**: Highcharts sizes each column as its width's share of the width SUM,
so a bad width does not merely fail to draw its own bar — it drops out of the **denominator** and
silently makes every OTHER bar wider. Rendered, five clean rows drew the first bar 87px wide; nulling
the SECOND row's width redrew that same first bar at **134px**, pixel-identical to a control render
with the offending row **deleted**. A negative is worse still: a `-30` beside a `21` and a `44` drew
its own bar 1px wide and inflated the other two to 410px and 860px inside a **760px** chart — bars
overflowing the canvas, every width overstated, no error anywhere. Zero is **kept** (`_sizable`'s own
rule, verified the same way: a 1px sliver, its tick, and nothing added to the total).

Hence `_variwide_point`, the module's **third** pair helper, which reaches `_range_point`'s
ALL-OR-NOTHING answer from a **different premise** — and the premise is what the next edit will
reason from. `_range_point` nulls the whole slot because *a range with one end is not a range* (a
fact about the MARK); `_bullet_point` nulls each end alone because half a comparison is still worth
drawing; `_variwide_point` nulls the whole slot because **a half-row repaints its siblings** (a fact
about the OTHER ROWS). The slot is **kept**, never dropped: the points are positional against
`xAxis.categories`, so dropping would desynchronize the two *and* hide the category outright, which
is the one thing worse than a renormalized neighbour. **No `EnforcedNull` carve-out** — verified,
`z` coerces both tokens, so bullet's `None` must not be copied here.

The point is a `[value, width]` **2-array**, read as `[y, z]` because `xAxis.categories` supplies the
names, and it is load-bearing in bullet's two directions: the literal key **`z` never reaches the
emitted JS** (the width survives POSITIONALLY, so `assert "z" in js` is **false** on a correct chart
and this module's dominant test idiom is **inverted** again), and any key outside `{x, y, z, name}`
forces the point **dict** form, in which a null `z` **vanishes entirely** rather than nulling. So the
**single brand hue** (`colorByPoint` pinned to appear NOWHERE) is what keeps the null-width policy
expressible — and, like bullet's, that pin guards a real **decision**, since variwide's
`colorByPoint` *survives* the round-trip at both levels.

It **prints nothing in the mark** — but **not** by xrange's premise, which is **false** here: an
xrange's two ends both land on a ticked axis, whereas a variwide's **width lands on no readable axis
at all** (the x axis carries variable-width category slots, not a scale). It is the one number in
this module a **tooltip is the only home for**, carried as `{point.z}` beside `{point.category}` and
`{point.y}`. Printing it in the bar would fail exactly where it is most wanted: a bar narrow enough
to need its width read is too narrow to hold a label, and Highcharts hides a colliding label by
rendering it **invisible**. It sets **no `pointPadding`/`groupPadding`**: variwide overrides column's
0.1/0.2 defaults to **0/0** deliberately, so its bars **touch** — that adjacency IS the chart type,
and "restoring" column's values would silently un-make it.

It needs **one** `_themed` hook, and it is the **sixth** member of the border-dissolve tuple — the
one member whose border is **not a spurious ring**. Every other member's bars have gaps, so the white
outline is an artefact; a variwide's bars touch, so the border is the **only thing dividing two
neighbours**, and dissolving a load-bearing divider is exactly the edit to suspect. So it was
rendered as its own question, with adjacent bars of **equal height** — the case a silhouette cannot
disambiguate — and the dissolve survives it: the seam remains, drawn in the page colour, which is
precisely what the white border does on the light shell. It is the **absence** of the hook that would
break the symmetry, leaving a white seam on a navy page matching nothing on it. Same fix as
column/bar, opposite reason. Its marks are the bars, so it needs a `count_marks` rule and a
`MARK_METRICS` entry (**"Bars"**, xrange's noun rather than bullet's "Measures": a variwide draws
exactly one rectangle per category, the width being a property OF the bar rather than a mark beside
it) — counting by label, the same number columnrange and bullet return by a **third** argument, which
is what earns it its own branch. Two guards, both **raising**: width required, and `value != width`,
the second **claim-fabricating** rather than cosmetic (every bar's width proportional to its own
height, so each bar's AREA would be its value **squared** — a chart that draws perfectly while
stating something nobody asked). **No `explain_variwide_error`**: every data combination has a right
drawing, so the two guards are *column*-level collisions, not contradictions the data states. Pulls
in `modules/variwide` from `chart.type` alone and **not** `highcharts-more` — the plausible guess the
round-trip corrects, as for columnrange, funnel and bullet — and needs **no** `_MODULE_LOAD_ORDER`
entry (`variwide.js` requires only `highcharts`). Dropping the module is a **silent blank**: the
browser renders an SVG with zero series paths, no error band and no console error, while the export
server rasterizes the PNG perfectly — the solidgauge-pane trap, pinned on `get_script_tags`), and
`dumbbell` (two markers per category joined by a connector — columnrange's data SHAPE read a
**fourth** way, and, as with the third, the reading is the whole of the type. Line the four up,
because every decision falls out of the difference: a **columnrange**'s two numbers are the two
**ends of one mark**; a **bullet**'s are two **independent claims** about one category on the
**same** channel; a **variwide**'s are **one claim over two geometric channels**, read as their
product; a **dumbbell**'s are **one claim AT TWO TIMES** — the same measurement, of the same thing,
taken twice. So the reading is neither number but the **delta** between them, which is why the
connector is the mark and the two markers are merely its ends.

So `after_col` is a **new** kwarg, the **ninth**, and the **fourth** that is not a reuse. Not
`high_col`: a high is the far END of the mark it shares a point with, and that pair is
**UNORDERED** — a range is bounded by its two values, so swapping them draws the same bar — while a
before and an after are **ORDERED**, and swapping them turns every rise into a fall. Not `goal_col`:
a goal is a REFERENCE the measure is read against, so one number is the world and the other is an
intention, while a dumbbell's two are the same quantity at two moments, both equally real. Not
`width_col`: a width weights a height on a second geometric channel, while these two share one
channel and one unit. `title_col`'s, `goal_col`'s and `width_col`'s precedent a fourth time — the
dtype and the picker source match an existing kwarg exactly, and the **role** is what differs — and
so dumbbell is the **third** recent type to **touch the cache layer**, bullet's and variwide's cost
paid a third time rather than escaped as arearange and dependencywheel escaped it.

That the pair is ORDERED is a **rendered** fact, not a design preference, and it is what makes this
a fourth reading rather than a columnrange re-skin. Highcharts paints `lowColor` onto the marker at
the **FIRST array slot**, not onto the numerically smaller one: on a falling row (`55 → 31`) the
low-coloured marker drew at **55, the top**. So slot 0 is reliably the BEFORE whichever way the row
moved, the hues never swap, and a fall reads as a fall. Had it tracked the smaller value instead,
this type would have silently inverted its own colour coding on exactly the rows a reader most needs
to trust — and it would have done so while drawing a perfectly plausible chart. A dedicated test
pins the slot order for that reason, since a `sorted()` "tidy-up" is the obvious wrong edit.

It **joins** `X_IN_Y_GUARD_TYPES` (its `x_col` is a genuine category X axis — the paired markers
stand ON it, drawn vertically) and **not** `MAGNITUDE_RANGE_TYPES`, which binds five sites where
columnrange and arearange are byte-identical modulo `chart.type`; dumbbell shares **none** of them.
But it **does** reuse `_range_point` **verbatim**, and the two facts are not in tension — which is
worth stating, because it is the first time this module has had to separate them. A shared **helper**
is shared behaviour; a shared **family constant** is a claim that the types are interchangeable at
the sites it binds. `_is_top_level` (sunburst → organization) and `_sizable` (sunburst → variwide)
are the precedent for the first without the second.

Its null policy is `_range_point`'s, reached from a **third premise** and the only one of the four
that is **not a choice at all**: Highcharts draws **nothing** for a half-pair. Verified — `[42, null]`
serializes cleanly and renders no marker, no connector, just an empty category tick. So there is no
half-drawn state to prefer against, and bullet's per-end policy could not be expressed here even if
it were wanted. One trap rides along, and `_range_point`'s bare-`EnforcedNull` return is what keeps
it unreachable: an `EnforcedNull` **inside** a dumbbell's array raises `CannotCoerceError` at
`Chart.from_options`, one layer BELOW `build_options` — bullet's `target` trap in a third validator —
so `[EnforcedNull, EnforcedNull]` would pass every options-dict assertion while making the chart
unbuildable.

It prints **nothing in the mark** and needs no gate constant — *xrange's rule reached from xrange's
own premise*, unlike variwide where that premise is false: both of a dumbbell's numbers land on a
real, ticked, gridlined y axis that renders in the Static PNG too, and the only other identity, the
category name, is already on the X axis. Its dataLabels default **off** (column/bar's behaviour), so
the omitted key IS the gate. Its tooltip is `{point.category}` / `{point.low}` / `{point.high}`,
with both column names **labelled** rather than run together (bullet's rule: on a nulled slot each
value renders as nothing, so the labelled form degrades to a clean "q1: / q4:" where a run-together
`{low} → {high}` would collapse to a bare arrow).

It needs **no `_themed` hook at all**, and that is the surprising half — **measured**, never
inferred. Dumbbell is a `highcharts-more` bar cousin of columnrange, which IS in the border-dissolve
tuple, so kinship says it should join; it does not, because its markers carry
`stroke: var(--highcharts-background-color)` at **`stroke-width: 0`** — the white ring the tuple
exists to remove is declared and never painted, so a hook would dissolve a border that was never
drawn. The tuple therefore stays at **six**. What it sets instead is `_DUMBBELL_BEFORE_COLOR`, the
BEFORE marker's hue, aliased to `_SUNBURST_ROOT_COLOR` (no new colors invented) and deliberately OFF
the categorical palette — a prior reading is not one of the categories, so no palette entry can say
it and a custom `colors` must not repaint it into looking like a second series. It needs **no dark
flip**, and that is geometry rather than luck: a bullet's crossbar is drawn at 140% of the bar width
so it necessarily crosses **both** the bar and the background, which no fixed value can serve, while
a dumbbell's markers sit only on the background, so one mid-slate reads on both shells. Setting it at
all is load-bearing — Highcharts' own default is a near-black that all but vanishes on the dark
shell.

It sets two **geometry** constants (`_DUMBBELL_CONNECTOR_WIDTH = 3`, `_DUMBBELL_MARKER_RADIUS = 7`)
— it is in no way alone in that (`_XRANGE_POINT_WIDTH`, `_SUNBURST_ROOT_SIZE_PCT` and the gauge
family's whole `_GAUGE_*_PCT` band are the same kind of number) — and both survive the pane-`size`
"stop steering" rule only because the defaults were **rendered and measured** rather than eyeballed:
the connector is `stroke-width: 1` in the series hue and the markers are `radius: 4`. On a dumbbell the connector IS the mark, and at
1px against 8px markers the delta is the least prominent thing on the chart — the eye reads pairs of
dots, which is a scatter plot, not a set of movements. (One note for the next reader: at 1px the
default connector *photographs* as near-black, and reading the pixels would have "found" a grey to
fix. The DOM says the **series hue** — `DEFAULT_COLORS[0]`, ours already. On this type the
attribute is the evidence and the screenshot is not.)

Its marks are the before-to-after movements, so it needs a `count_marks` rule and a `MARK_METRICS`
entry (**"Changes"**) — counting by label, the same number columnrange, bullet and variwide return,
by a **fourth** argument, which is what earns it its own branch: neither value column can produce a
partial mark the count could disagree about, because a half-pair draws nothing at all. The noun is
"Changes" rather than "Pairs" or xrange's "Bars" because a dumbbell draws **three** shapes per
category and counts none of them; variwide could take "Bars" back precisely because it draws one
rectangle, and here there is no single shape to name, so the noun names the reading. Two guards,
both **raising**: after required, and `before != after`, the second **claim-fabricating** rather than
cosmetic — and the one such collision whose wrong chart is **indistinguishable from a real result**,
since every category would draw its two markers at one value, which renders as a single dot with no
connector, i.e. as "nothing changed anywhere", a reading this type exists to express.
**No `explain_dumbbell_error`**: every data combination has a right drawing. Pulls in
`modules/dumbbell` **plus** `highcharts-more`, both from `chart.type` alone — the guess the
round-trip **confirms** here, unlike columnrange/funnel/bullet/variwide where it corrects it — and
needs **no** `_MODULE_LOAD_ORDER` entry, verified in the walk order that reverses for
dependency-wheel and organization: highcharts-core emits the prerequisite first both with and
without a `plotOptions.dumbbell` key), and
`solidgauge` (concentric
rings on one shared dial — an "activity gauge", and the only type with **no label channel
at all**. Every other type names its marks from a column: a slice, an axis category, a
node, a box, a lane. A gauge's marks are the **selected columns themselves**, each
*reduced* to one number — so `x_col` names nothing, is `None`, and the column role that
seventeen types took for granted stops being universal. It is therefore also the first
type whose marks are neither in the frame (as every pointwise type's are) nor assembled
from it (as sunburst's tree is) but **reduced** from it: the second aggregating type after
boxplot, and the first whose row count has no bearing on its mark count at all.

That is the type's organizing fact, and the branch's placement is its first consequence: it
sits **above** the shared `_label_ok` filter, and the placement is load-bearing rather than
tidy. The exception is not merely vacuous — that is the sharper point. A row filter above an
*aggregating* branch does not drop a MARK, it silently changes a **NUMBER**: filter three
rows out of thirteen because their (unused) label cell happened to be blank, and the total
comes back smaller, drawn confidently, with nothing on the page saying so.

Each ring is its own **series**, and that is forced rather than chosen. The canonical
Highcharts activity gauge is ONE series whose N points each carry their own `radius` — and a
point-level `radius`/`innerRadius` is accepted by `Chart.from_options` and then silently
dropped from the emitted JS (the sankey-`nodeFormat` / boxplot-`fillColor` /
sunburst-`levels[].colorByPoint` family, and the first of them to dictate the SHAPE of a
whole branch rather than one of its options). The series-level ones survive. And that is what
makes `marks == series == len(y_cols)`, which is why gauge needs no `count_marks` rule and no
`MARK_METRICS` entry.

**The hue has to be written three times, to three different levels, and none of them
substitutes for another** — one `next()` off `itertools.cycle`, then said again and again,
because each is a different silent drop wearing a different hat. The **arc** reads the
*point*: Highcharts' solidgauge defaults `colorByPoint: true` and highcharts-core models no
`color_by_point` at all, so the default cannot be turned off, every series' single point is
index 0 of its own colorCounter, and a series-level `color` therefore serializes perfectly
and never reaches an arc — three hues in the JS, three identical blue arcs on screen, beside
pane tracks showing the three TRUE hues, so a reader matches a green track to a blue arc and
reads the wrong ring (verified by rendering). The **legend swatch** reads the *marker*: the
series `color` that the arc ignores is ignored here too, and Highcharts draws the bullet grey
for every ring — verified by rendering, and then verified again by *taking the series color
away*, which changed nothing at all, so it is not carried (an option that looks load-bearing
and isn't). A solid gauge draws no markers on an arc, so the marker is inert everywhere else.
The **hub label** reads its own `style.color`. It is the mirror of the radius, exactly: two
adjacent properties on opposite levels, each silently wrong on the other's.

The **pane** is load-bearing for a reason that has nothing to do with how it looks:
`get_script_tags` emits `highcharts-more` **only** when the options tree carries a `pane` key
— not for the series type, not for `plotOptions.solidgauge`, not for a series radius, not for
`yAxis.stops` (each tested in isolation) — and a solid gauge without `highcharts-more` draws
an **empty SVG** in the browser: zero series paths, no Highcharts error band, no Python-side
error. The export server rasterizes it regardless, so dropping the pane would make the two
render modes silently **disagree** — the class of bug `_LIGHT_COLOR_SCHEME_CSS` exists to
close. Pinned by a test on `get_script_tags`.

The **empty column is the type's headline trap**, and it is pandas' doing:
`pd.Series([], dtype="float64").sum()` is `0.0`, not NaN — and so is an all-NaN column's — so
pandas hands back the additive **identity**. Under `sum` an unfilled column would report "the
total is zero": a confident CLAIM where the truth is "there is no data", drawn as a real ring
sitting at the dial's floor to say so. mean/median/min/max/last all give NaN; **only `sum`
lies**, which makes it worse rather than better, because the bug would live in exactly one of
the six reductions and look like a rounding quirk in the other five. So the empty test runs
**above** the reducer (`_coordinates`' `_COORD_EMPTY` ordering, for the identical reason),
making it unrepresentable rather than a special case somebody has to remember. The ring is
then **kept** as an `EnforcedNull` — boxplot's all-missing-group rule, and here geometrically
forced: the radii are a function of the SELECTION, so a data-driven drop would resize and
recolour every ring below it. (A bare `EnforcedNull`, not `{"y": EnforcedNull, "color": …}`:
highcharts-core drops a null `y` out of a point dict entirely, leaving a point with no value
at all.) A null point draws no arc **and no label**, which is why gauge is the one type whose
**legend** is not redundant: it is the only thing that names an empty ring.

The **dial is derived from the READINGS, never from the raw columns**, and that is the type's
central invariant rather than a nicety. Under `sum` a reading *exceeds every observation in
its own column* (436 against a maximum cell of 63), so a max derived from the raw column would
pin every ring past the end of its own dial — "everyone smashed target", drawn confidently, on
data that says nothing of the sort. Reducing first, with the very reduction the rings draw,
makes a ring that overflows its own dial arithmetically unrepresentable. It is rounded outward
to a 1/2/2.5/5/10 × 10ᵏ step, because a dial ending exactly at the largest reading draws that
ring 100% full whatever it holds — "436 of 500" is the only reading a gauge ever gives, so the
500 has to come from somewhere. `gauge_dial` is **exported**, so the app can *seed* its Dial
min/max inputs from the builder rather than recompute them: `coordinate_columns`' can't-drift
rule, applied for the first time to a widget's **value** rather than to its options. It is
**total** by construction (`count_marks`' contract) — an empty selection, an all-missing column
and a row-less frame each give a drawable dial rather than raising, or, worse, a degenerate
`0..0` that Highcharts would divide by. An override with no span raises, via
`explain_gauge_error` — the third of that family, and the first that reads **no frame at all**:
this contradiction is a fact about two numbers the user typed.

`threshold: 0` is what makes an all-negative dial honest. A gauge is read **from zero** — an
arc's LENGTH is its magnitude — and left unset, Highcharts sweeps each arc from the axis
*minimum*, which **inverts** the reading: on a −200..0 dial a −40 would draw a *longer* arc
than a −155, so the smallest loss would look like the biggest (verified by rendering).

Its geometry is capped at **both** ends of the range, and each cap stops the band degenerating
in a different direction. The **gap** is capped for MANY rings (a fixed 3% gap exceeds the band
past ~21 of them, at which point `inner > outer` and Highcharts draws garbage — and a wide CSV
with 40 numeric columns is one click away); capping the ring COUNT instead would mean dropping
a column the user asked for, so the geometry degrades into thin rings rather than breaking. The
**thickness** is capped for FEW rings: with the whole radius to divide between them, one column
draws an arc 61% thick — a fat disc with a pinhole, which reads as a pie with a bite out of it
rather than as a gauge. It labels each ring in the hub with `name: value`, one line per ring in
that ring's own hue, **gated on ring count** like heatmap's cells, sankey's links, waterfall's
steps and sunburst's sectors — and the gate has a twist none of theirs has, plus a trap none of
theirs has. The twist: a gauge's dataLabels default to **ON**, so past the gate they must be
disabled *explicitly* — merely omitting the key (heatmap's style) would be a gate that did
nothing. The trap: Highcharts hides a *colliding* label by rendering the `<text>` and turning it
**invisible**, so the element stays in the DOM and every assertion about it still passes while a
ring's value is simply **absent from the chart** — hence `allowOverlap: True`, after which the
real limit is physical (the hub is a fixed fraction of a radius; the stack grows with the ring
count), and the number is **measured** at 300px, the smallest chart the app can draw. It carries
a **subtitle** naming the aggregation and the dial, because the scale is invisible on the chart
(a 360° gauge has nowhere to put an axis) and the Static PNG has no tooltip either, so without it
a downloaded gauge cannot be decoded at all. Its tooltip is `{series.name}` — a third answer for
a third reason: waterfall needs `{point.category}` (its points are positional), sunburst and
xrange need `{point.name}` (their categories are on the wrong axis), and a gauge ring holds
exactly ONE point, so the mark's identity is not on the point at all; it IS the series. It needs
**one** `_themed` hook, the pane's background **tracks** — the first hook to reach a **top-level**
key rather than `plotOptions[type]`, which is less an exception than a demonstration: a track is
*chrome* (the gauge's gridline, the colour of "no value here", so it takes `_HEATMAP_NULL` and
flips to the grid colour) that happens to belong to one type. It is also the only hook this type
*can* have: `borderColor` is impossible, since `SolidGaugeSeries` models no border at any level
and one would be silently dropped (boxplot's `fillColor` exactly). It is named **`solidgauge`**,
Highcharts' own name for it, and *not* the friendlier `gauge` — which radar's precedent (called
`radar`, serialized as a `line` with `chart.polar`) would have licensed, and which is what a
person actually shops for. The name was deliberately left free, because `gauge` in Highcharts is a
**different chart**: a needle on a dial, a distinct series type with its own
`DialOptions`/`PivotOptions`. Pulls in `modules/solid-gauge`, and `highcharts-more`, which only
the pane resolves), and `gauge` (**the needle**, which spends that name on exactly the type it was
being held for — so both gauges are called what Highcharts calls them, and radar stays the *one*
type whose `chart.type` is not its own name).

`gauge` is the **second member of the gauge family**, and the family is the point. `GAUGE_TYPES`
is now `SOLID_GAUGE_TYPES + NEEDLE_GAUGE_TYPES`, and splitting it that way *was* the whole of the
plumbing: the tuple was already consulted at exactly the five places where the two types are
**identical** — the `x_col is None` exemption, the `agg`/`dial` guard, `count_marks`' no-rule
raise, the label-drop sweep's exclusion, and the row-less sweep's null expectation — so every one
of them stayed correct for the needle with *no edit at all*. Everything above the mark is shared
and already pinned on the sibling (`_gauge_value`'s empty-column trap, `gauge_dial`'s
readings-derived scale, the six reductions, the non-finite policy); `_dial_from_readings` makes
that sharing **structural** rather than remembered, since a function that cannot see a DataFrame
cannot derive a dial from a raw column. The two branches share no options key worth sharing, so
they are two flat branches and there is no `if needle:` inside either tree.

What the needle does **not** inherit is the whole lesson, and each of the three would have been a
silent bug had the sibling's answer been copied on faith:

- **the MODULE.** A solid gauge resolves `highcharts-more` *only* from its `pane` — the scariest
  trap in the family, since dropping it draws an empty SVG in the browser while the export server
  renders perfectly. A needle resolves it from `chart.type` **alone** (verified against the pane,
  `plotOptions` and a bare series type, each in isolation). Its pane is geometry, and nothing hangs
  on it.
- **the HUE.** On a solid gauge a series-level `color` serializes perfectly and reaches *nothing*
  (the arc reads the point; the legend bullet draws grey and needs a `marker.fillColor`). On a
  needle `color` reaches **only the legend** — the needle itself is BLACK unless
  `dial.backgroundColor` says so (rendered: three coloured legend swatches above three black
  needles). Same property, opposite failure. The ring writes its hue to three places, the needle
  to two, and **not one of them is the same place**. (The needle also has to ask for the legend
  *twice*: a gauge series defaults to `showInLegend: false`, unlike almost every other type.)
- **the LABEL.** A solid gauge *must* print its readings in the hub — a 360° ring has nowhere to
  put an axis, so its value can be read against nothing, and it pays for that with a gate, a
  measured leading and a per-series offset. A needle points **at** an axis. So it prints **nothing
  in the mark** and needs no gate constant either — *xrange's rule, reached from xrange's premise*
  — and the sibling's label machinery is not re-tuned here, it is deleted. It was built the other
  way first and the renders killed it: the stack, the arc and the subtitle cannot all fit at 300px,
  and both levers that would have bought the room are closed **by the library** (see the pane
  below). Four constants and a gate, all to reprint a number already on the axis.

Its own novelties. The needles are **staggered in length**, longest first (`_needle_radii`), and
that is a correctness fix rather than a flourish: two columns with *equal* readings put two needles
at the same angle, and Highcharts draws the later series on top, so at one length the second needle
covers the first **completely** — three series, two visible needles, the legend and the tooltip
both still naming three. `marks == series`, the invariant the whole family rests on, was a lie *on
screen*, in the one place a reader would never think to check; staggering exposes each needle's tip
in its own hue (verified: a green needle with a blue tip). The **pivot** is one neutral colour set
once in `plotOptions` and never per series, because N needles pivot at the *same point* — N hued
pivots draw N discs on top of each other and the reader sees whichever series happened to be last;
it takes `_SUNBURST_ROOT_COLOR`, the module's existing off-palette "not a category" slate, which
reads on both backgrounds and needs no dark flip. The `yAxis` kills **both** grid widths, and the
**minor** one is the load-bearing half — exactly backwards from what you would guess: `_themed`
writes a `gridLineColor` onto every axis it finds, so the major width must be pinned, but *nothing*
themes the minor one, and Highcharts defaults it to 1px of `#f2f2f2` — invisible on the light face
and a **blazing white starburst** across the dark one (verified by rendering, on a chart whose every
unit test passed). The subtitle carries **only the `agg`**, not the dial: the dial is on the axis
now, and repeating it would be two homes for one number, free to disagree.

And **`overshoot`** is what keeps an *overridden* dial honest — the one way this type could still
draw a confident, plausible, wrong chart, and it is one keystroke away. `gauge_dial` guarantees
every reading sits inside the scale it *derives*, but the app's two Dial inputs accept any two
numbers: zoom the scale to `0..50` on a column that sums to 436 and, left to Highcharts, the needle
pegs **exactly on the final tick** — pixel-identical to a true reading of 50, with nothing anywhere
on the chart to contradict it and no tooltip in the Static PNG. It is also the **one place the two
gauges would disagree**: a ring in the same state fills its arc and *prints* `north: 436` in the
hub, so its reader is told; a needle prints nothing in the mark, so its reader is not — and a
family cannot be honest in one branch and mute in the other. Overshoot is the instrument's own
answer and needs no words: the needle swings **past** the last tick, which is what a real meter does
when it slams its end stop. It cannot say *how far* over the reading is — a dial that stops at 50
cannot draw a 436 — but it says, unmissably, that it **is** over, which is the whole of the
difference between an under-scaled chart and a lying one.

There is also **no `plotOptions.gauge.dial`**, and its *absence* is pinned by a test. It was carried
at first, with a comment swearing that `topWidth` is demanded at "both levels" — which is simply
false. Every needle carries its own complete dial (it must, for its hue and its length), so a
plotOptions dial defaults nothing and does no work; deleting it changes not one byte of the emitted
JS. It is an option that **looks load-bearing and isn't** — the exact defect this module tests other
libraries for — and one of ours would be worse than any of theirs, because ours came with a comment
insisting it was needed. (Found by the review, not by the build.)

And the **pane carries no geometry at all** — no `size` *and no `center`* — which is the one place
in this module where the right answer turned out to be to stop steering. `size` is a **silent
drop**: `options/pane.py`'s setter runs `validators.string(value)`, checks the result for `%`, and
then falls off the end **without ever assigning `self._size`** — only the numeric `except` branch
writes it. So the `size: "85%"` that every Highcharts gauge demo on the internet sets is accepted
and discarded, while `size: 200` (raw pixels, useless to a chart whose height the user drags)
survives. (`inner_size`, ten lines above it, assigns in *both* branches: one copy-paste slip, not a
policy.) And without `size`, `center` cannot be made safe — Highcharts reserves no room for the
tick labels outside the pane, and the pane's radius scales with the plot box — so every value
trades one chart height for another: at 58% the topmost label printed through the subtitle; at 65%
it was clean at 300px and 800px and **clipped clean off the canvas at 420**. A failure that is not
even monotonic in the height is the tell that it is not a number to be tuned. Highcharts' own
default is correct at every height the app offers, because it is the one placement that knows what
the labels need. The pane therefore says what the *chart* is and nothing about where to put it.

The one trap that **is** shared is the one CLAUDE.md predicted: `plot_options/gauge.py`'s
`top_width` validator lacks `allow_empty=True`, so **any** `dial` dict omitting `topWidth` raises
`EmptyValueError` — out of a validator naming neither the key, nor `dial`, nor the series, and at
`Chart.from_options`, one layer *below* `build_options`. So an options-dict test passes while the
chart cannot be built at all, and the app's interactive path (which does not catch builder errors)
shows a bare traceback. Hence `_NEEDLE_DIAL`: every dial dict the module emits is spread from it,
which makes the trap unreachable rather than remembered. (`yAxis.labels.distance` is a third
instance of the same `allow_empty` bug: it rejects `0` with `EmptyValueError` and refuses a
negative outright.)

Finally, `_gauge_reading_label` is the **family's** number format, and fixing the sibling with it is
the family working as intended rather than scope creep. A bare `{point.y}` prints the double, and
the double is what an aggregation hands you: the mean of nine integer percentages is
`66.44444444444444`, which ran off the side of the chart in a colour-matched 20-character smear.
`solidgauge` had the identical latent bug — its own sample merely happens to divide evenly
(436/8 = 54.5) — and it is the one flaw an options-dict assertion can **never** see, because the
number is not in the options at all, only the format string is. The reading is therefore formatted
in **Python** and baked into each series' own `dataLabels`/`tooltip` string (per series, because a
gauge point drops a `name` carrying the pre-formatted value — the `radius`/`colorByPoint` silent-drop
family again — so no shared format token survives). No fixed-decimal *Highcharts* format could do it:
`numberFormat` implements `f`/`e`/`s` and not `g`, and `.1f` trimmed the smear only by rounding a real
`0.008` reading to `0.0` — the family's own **confident zero**, the exact lie `_gauge_value` fusses to
keep an empty column from telling — while `.3f` would ring every integer total with `436.000`. So the
helper carries one decimal above 1 (the smear, trimmed), ~3 significant figures below it (a small
reading, preserved), a thousands separator, and stripped trailing zeros — falling back to scientific
outside `1e-4 .. 1e15`, since a `1e308` cell parses out of a plain CSV and a fixed-decimal format would
expand it to a 300-digit label. It is pinned in isolation, and — the whole point — so is its **output**,
not merely the format string that used to hide the absurd number.

## The app's column controls

- `streamlit_app.py` — the Streamlit UI: data source (sample datasets or CSV
  upload), chart-type/column controls (pills for the Y series, falling back to
  `st.multiselect` on wide CSVs, plus one type-specific extra column selector per extra
  column kwarg (stated as a rule rather than as a COUNT: this sentence read "the four"
  long after there were nine, and the enumeration below it had already outgrown the
  tally — so the number is left to the code, which the kwarg table in `CLAUDE.md` is
  pinned against)
  — Size (Z) for bubble, Target (to) for sankey (and **dependencywheel**,
  **networkgraph** and **organization**, all four of which reuse the very same control and
  `target_col`, since a link is a link — organization relabels it **Manager (to)** and adds a
  **Title** selector, the one extra control a node-link type has ever added, since a title is not a
  weight), Parent for sunburst, End
  for xrange, High (top) for **columnrange** and its filled-band mirror **arearange** (which reuse
  one High control and one `high_col`, keyed on `MAGNITUDE_RANGE_TYPES` — a link is a link, and a
  band's top is a bar's top; their shared Y control is renamed **Low (bottom)** — the two ends of a
  range, both magnitudes, drawn from `numeric_cols`, *not* xrange's `coordinate_columns`, since a
  high can never be a date; columnrange is the type that first introduced `high_col` as a new kwarg
  rather than a reuse — because a magnitude is not xrange's coordinate — and arearange then reuses
  it, so the cache layer is untouched, networkgraph's/dependencywheel's win), **Goal (target)** for
  **bullet** (which looks like a second High and is deliberately *not* one: it is drawn from the
  same `numeric_cols` for the same reason — a goal is a magnitude, never a date, never a label —
  but it feeds its own `goal_col`, because a high is the far END of the mark it shares a point with
  while a goal is the REFERENCE that mark is read against. "A link is a link, but a goal is not a
  high" — the `title_col` distinction one family over. It is called **Goal**, not Target, because
  **Target (to)** already names a destination *node* in this sidebar for all four node-link types,
  and one word cannot name both a label and a magnitude — the very collision that made it a new
  kwarg. It sits directly after the Y control so the sidebar reads as the pair it is
  (Category → Measure → Goal), and its `index` is a constant `min(1, …)`, landing on the *second*
  numeric column so it starts distinct from Measure and still clamps a one-column frame),
  **Width** for **variwide** (the *third* control drawn from `numeric_cols` and the third to feed a
  kwarg of its own — a width is neither the far END of the mark (`high_col`) nor a REFERENCE it is
  read against (`goal_col`) but the mark's OTHER DIMENSION, so `width_col`, and so the cache layer
  is touched. Called plain **Width**, *not* "Width (weight)", which is the more natural reading of
  the column: **Flow value (weight)** already names a link's magnitude in this sidebar for the
  weighted node-link types, and one word cannot name both a link's size and a bar's extent — the
  same collision that made bullet's control **Goal** rather than Target. It sits directly after the
  Y control, which is itself renamed **Height (bar)** so the two read as the two dimensions of one
  rectangle, and its `index` is the same constant `min(1, …)` Goal's and High's use),
  **After** for **dumbbell** (another control drawn from `numeric_cols`, and the *fourth* to feed
  a kwarg of its own after `title_col`/`goal_col`/`width_col` — that second tally is the checkable
  one, since bubble's **Size (Z)** is drawn from `numeric_cols` too and the "third/fourth from
  `numeric_cols`" counts above quietly mean the two-magnitude controls rather than all of them.
  An after is neither the far END of the mark (`high_col`), nor a REFERENCE it
  is read against (`goal_col`), nor the mark's OTHER DIMENSION (`width_col`), but THE SAME QUANTITY
  AT A LATER TIME, so `after_col`, and so the cache layer is touched a third time. Called plain
  **After**, *not* "To" — which was available, since the node-link types say **Target (to)** and
  **Manager (to)** — and rejected precisely because "To" reads as a DESTINATION, an xrange End or a
  sankey target, where this is a second reading of one quantity rather than somewhere the first one
  went. It sits directly after the Y control, which is itself renamed **Before** so the two read in
  the order they are drawn, and its `index` is the same constant `min(1, …)` Goal's, High's and
  Width's use. This is the **one** extra-column pair in the sidebar whose two halves are
  **ORDERED**: High/Low, Measure/Goal and Height/Width can each be read either way round without
  changing what the chart claims, while swapping Before/After turns every rise into a fall — which
  is why the two words have to carry the order and a bare "Value 1 / Value 2" could not) — and
  the **gauge family's** two, which are the only ones that name a **policy** and
  a **scale** rather than a column: an aggregation picker sourced from the builder's
  `GAUGE_AGGREGATIONS`, and a Dial min/max pair *seeded* from its `gauge_dial`. The gauge family is
  **not** the only thing that **removes** a control, though it was the first: neither gauge draws an
  X selectbox at all — a *subtractive* change, since a control that does nothing is a lie in
  the UI and passing a column the builder must ignore is a lie in the call site and
  in three cache keys — and the two **UNWEIGHTED node-link types** (**networkgraph** and
  **organization**, named `UNWEIGHTED_NODE_LINK_TYPES`) are the MIRROR of it, drawing no **Y**
  control at all (they are unweighted, so a value picker would drive nothing). Gauge removes the
  label channel and keeps the value; the unweighted pair remove the value channel and keep the
  label. Each is exempted
  from the empty-selection guard that the other's channel still enforces (`x_col is None` for
  gauge, `y_cols == []` for the unweighted pair — pinned both ways, by an exclusion and a positive test). Every one of those controls is keyed on `GAUGE_TYPES`, so `gauge` inherited
  the lot without a new branch — and the AppTests that pin them are *parametrized over the family*
  rather than written twice, which is what stops the two drifting. The single difference is a noun:
  the Y control says **Rings** for one and **Needles** for the other, because a reader picking
  columns should be told what each one will *become*),
  caching, a KPI metric row (its third metric adapts to the chart type — series
  plotted, or, for the one-series types, the mark count from the builder's
  `count_marks`: cells for a heatmap, tiles for a treemap, stages for a funnel or
  pyramid, flows for a sankey or dependencywheel,
  links for a networkgraph, reports for an organization,
  boxes for a boxplot, steps for a waterfall, sectors for a sunburst, bars for an
  xrange, ranges for a columnrange, points for an **arearange** (its band's vertices), measures for
  a **bullet**, bars for a **variwide**, changes for a **dumbbell** — sourced
  there
  rather than recomputed
  here so it can't drift from what the chart draws; waterfall's and sunburst's are the
  two that *exceed* their drawable mark count, by one, since each appends a mark the
  frame never held (a total bar, a root sector) — not necessarily their row count,
  since an undrawable label drops its row; xrange, columnrange and arearange append nothing, so
  their count is
  exactly their surviving rows (columnrange and arearange share **one** count rule, keyed on
  `MAGNITUDE_RANGE_TYPES`, counting by label like waterfall — a missing/inverted
  range kept as a null slot and still counted; their nouns differ, "Ranges" vs "Points", since a
  band is one shape whose vertices are counted, not N discrete ranges). Bullet reaches that same
  surviving-label number by its **own** branch and its own argument — columnrange never reads its
  value columns because a missing end nulls the *whole* slot, while bullet never reads *either*
  because **neither** channel can drop a row — and its noun is **"Measures"** rather than xrange's
  "Bars", because the bar is only half of what a bullet draws: the count is of the pairing, not of
  the rectangles. Variwide then reaches that same number by a **third** argument and takes xrange's
  noun **back**: neither of its channels can drop a row either, but for its own reason
  (`_variwide_point` nulls all-or-nothing and KEEPS the tick, so a bad cell costs a bar its ink and
  never its slot), and it draws exactly ONE rectangle per category — the width being a property OF
  the bar rather than a second mark beside it, which is precisely what bullet's noun exists to
  say and variwide's therefore must not. **Dumbbell** reaches that same number by a **fourth**
  argument — neither channel can drop a row because a half-pair draws *nothing at all*, so there is
  no partial mark a count could disagree about — and its noun, **"Changes"**, is the one in this set
  that names neither a shape nor a pairing of shapes: a dumbbell draws THREE things per category
  (two markers and the connector joining them) and counts none of them, only the one before-to-after
  movement they jointly describe. Variwide could take "Bars" back precisely because it draws a
  single rectangle; here there is no one shape left to name;
  membership of the `MARK_METRICS` dict is what makes a type count-adaptive, so the
  KPI stays one branch however many such types there are — and gauge is the first type
  whose *absence* from that dict is a decision worth stating: its marks ARE its series
  (one ring per y column, an empty column kept as a null ring rather than dropped), so
  "Series plotted" is already literally the ring count, and an entry would force a
  `count_marks` rule that did nothing but restate `len(y_cols)` — the can't-drift rule
  run backwards, a second computation of a fact that cannot differ from the first), the
  render-mode
  selector (interactive iframe / static PNG), reading the active light/dark theme
  (`st.context.theme.type`) so the charts render theme-aware, the chart embed,
  and a toggle that reveals the generated Highcharts config (JS).
  The **no-plottable-columns gate** runs *below* the chart-type selectbox and is
  type-aware, which xrange forced: every other type needs a NUMBER, but xrange's
  start/end are coordinates and may be dates — and a date column is object dtype, so
  the canonical Gantt CSV (`task,start,end`, all dates) has *no* numeric columns at
  all and the old `select_dtypes("number")` gate `st.stop()`ped it before the picker
  was even drawn. Xrange's Start/End pickers are likewise sourced from the builder's
  `coordinate_columns`, not from `numeric_cols` (which cannot see a date) nor from
  `df.columns` (which would offer a column of task names the builder can only reject).

## The builder's helpers

- `highcharts_builder.py` — pure, Streamlit-free helpers that turn a DataFrame
  into a Highcharts options `dict`, a `Chart`, and embeddable HTML or PNG bytes,
  plus `explain_export_failure()`, which turns a failed PNG export into a message
  naming the actual cause (it owns the export-server relationship, so it owns the
  diagnosis; duck-typed on `exc.response.status_code` rather than importing
  `requests`, which this project never declares), `explain_tree_error()`, its sunburst
  counterpart — the builder owns the hierarchy, so it owns the diagnosis — which returns
  the very message `build_options` raises for a malformed tree, so the app's warning and
  the exception it stands in for cannot drift apart (needed because the interactive path
  does *not* catch builder errors, and a cyclic CSV is the one such error a user can reach
  just by uploading a file), `explain_xrange_error()`, the same contract for a *column
  pair* rather than a tree. It reports two contradictions — a start/end column that can place a
  bar on no axis, and two that disagree about *which* axis — of which only the **second** is
  reachable from the app, since `coordinate_columns` keeps a column of task names out of the
  pickers entirely; the first is reachable only through the pure builder API. (So xrange adds
  exactly one app-reachable builder error, not two: a *date start beside a numeric end*.)
  Then `explain_gauge_error()`, the third of that family and the first that reads **no frame
  at all** — a dial whose maximum does not sit above its minimum is a contradiction about two
  numbers the user typed, not about a column or a tree, and it is reachable from the app because
  the two number inputs accept any two numbers. `bullet` adds **no fourth**, and its absence is
  worth stating rather than noticing: the family exists for contradictions that have *no right
  drawing*, and a bullet has none. A row missing its goal, one missing its measure, one missing
  both, and one whose measure falls far under its goal all have a correct picture (a bare bar, a
  lone crossbar, an empty category tick, a short bar under a high crossbar) — an inverted pair is
  the **ordinary reading** of a type that exists to answer "did we hit it", not xrange's
  whole-axis lie. So nothing is dropped, nothing raises, and there is no `explain_bullet_error` to
  write. Its one guard (`measure == goal`) is a *column*-level collision, not a contradiction the
  data states.
  Then `coordinate_columns()`, the
  builder's own answer to "which columns can place a bar on an axis" — exported so the
  app's Start/End pickers cannot offer a column the builder would refuse, which is the
  can't-drift rule applied to *which options appear in a widget* — and its gauge counterparts
  `GAUGE_AGGREGATIONS` (the same rule applied to a **policy**: the app can never offer a
  reduction the builder would reject) and `gauge_dial()` (the same rule applied, for the first
  time, to a widget's **value** rather than to its options: the Dial min/max inputs are *seeded*
  from the very call `build_options` makes when `dial is None`, so the number the app SHOWS
  cannot drift from the dial the chart DRAWS — and it must be, because a max recomputed in the
  app from the raw column would be smaller than every ring under `sum`, pinning them all at 100%
  with nothing on the page to say why). `gauge_dial` is now a thin shell over
  `_dial_from_readings()`, which takes **readings, not a frame** — the family's central invariant
  ("the dial comes from the READINGS, never from the raw columns") promoted from a rule two
  branches must remember into a **signature**, since a function that cannot see a DataFrame cannot
  derive a dial from a raw column. And `count_marks()`, which
  returns how many marks `build_options` will draw (a heatmap's cells, a treemap's
  tiles, a funnel's or pyramid's stages, a sankey's flows, a networkgraph's links, an
  organization's reporting lines, a boxplot's
  boxes, a waterfall's steps, a
  sunburst's sectors, an
  xrange's bars, a columnrange's ranges, an arearange band's points, a bullet's measures, a
  variwide's bars, a dumbbell's changes — funnel/pyramid counting
  `label_ok & value_ok` exactly
  like treemap, columnrange counting by label like waterfall minus the
  appended total, organization counting `label_ok & not _is_top_level(mgr)` — its own second
  mask, since a blank manager is a root that draws a box but no reporting line, so a bare
  `_label_ok` would overcount — and bullet, variwide and dumbbell each counting by label too, each in a
  **branch of its own** even though all four return the identical expression columnrange's does:
  each reaches that number by a *different argument* (columnrange never reads its value columns
  because a missing end nulls the whole slot; bullet never reads either because neither channel can
  drop a row; variwide never reads either because `_variwide_point` nulls all-or-nothing and keeps
  the tick; dumbbell never reads either because Highcharts draws nothing at all for a half-pair —
  the one of the four that is not a choice), and the premise
  is what the next edit will reason from. Folding them into a
  `MAGNITUDE_RANGE_TYPES + BULLET_TYPES` is precisely the "consistency" edit this file keeps
  warning about — that constant binds five sites and bullet belongs to exactly one of them, so a
  shared constant would be a claim about the TYPES where only the COUNTS agree, the
  funnel-beside-treemap pattern read backwards)
  for the app's KPI
  row — reusing the same `_label_ok`/`_plottable` drop predicates so the count can't
  drift from the chart (sunburst and xrange go further and reuse their *whole* build, for
  two different reasons: sunburst's drops are not a per-row mask at all, since a node's fate
  depends on its *ancestors* and its *descendants*; while xrange's drops *look* per-row but
  are read through a **column**-level fact — the axis kind — and `build_options` reaches its
  branch on the `_label_ok`-*filtered* frame while `count_marks` runs on the *raw* one, so a
  predicate-only reuse would sniff a different axis than the chart drew). Gauge has **no rule**
  in `count_marks` at all, and raises exactly as `line` does: its marks ARE its series, so
  `len(y_cols)` is an invariant, and a rule that only restated it would be the can't-drift rule
  run *backwards* — a second computation of a fact that cannot differ from the first.
  Independently importable and unit-testable.

## The sample datasets

- `sample_data.py` — pure (Streamlit-free) built-in sample datasets and the
  `SAMPLES` registry the app offers when no CSV is uploaded. The two gauge samples are siblings
  that exercise the dial from **opposite ends**: `Weekly bookings by region (solidgauge)` is read
  through `sum`, `Server utilization (gauge)` through `mean` (percentages, so the derived dial
  lands on the 0..100 a reader already has in mind — and `sum` on it is nonsense *on purpose*,
  reading past 600% and rounding the dial out to 1000, which is the fastest way to SEE what the
  aggregation picker is doing to your numbers). Both carry an entirely unreported column
  (`partner_deals`, `swap_pct`), which keeps the family's headline trap — pandas sums an all-NaN
  column to `0.0`, the additive identity — reachable from the page rather than only from a test.
  `Monthly temperature range (columnrange)` is the **mirror** of `Product release plan (xrange)`:
  both draw a bar from a low to a high, but the range sample's two value columns (`record_low`,
  `record_high`) are **magnitudes** of one quantity (°C), while the release plan's are
  **coordinates** (dates) — so reading the two side by side is the fastest way to see the axis the
  columnrange/xrange distinction turns on. Every low sits below its high (a clean range), because
  the type's headline is "a min–max per category" and the sample is meant to *show* it; the
  missing-slot and inverted-range edge cases are the tests' job, not a demo's.
  `Projected monthly active users (arearange)` is that temperature sample's own **mirror**, one
  axis over again: both read the same two magnitude columns (a low and a high per category), but a
  record-temperature range is a set of **independent** monthly facts (columnrange draws them as
  separate bars) while a forecast is a **continuous** estimate read for its **outline** — so the
  band **widens** month over month to show the uncertainty cone opening, the shape a row of bars
  cannot draw. It leads with a category (`month`) column and keeps every low below its high, like
  the temperature sample and for the same reason (the demo shows the clean band; the band-break and
  inverted edge cases are the tests' job).
  `Quarterly sales vs quota (bullet)` is that temperature sample's **other** mirror, and the one it
  looks most like while meaning least like: both lead with a category and carry two magnitude
  columns of one unit, but a record range's two numbers are the two **ends of one bar** (neither
  means anything alone — the bar *is* the span between them) while `actual` and `quota` are two
  **independent claims** about the same region: what happened, and what was meant to happen. So one
  draws N floating bars and the other N bars from zero, each crossed by a reference line — reading
  them side by side is the fastest way to see that "two magnitude columns" is a data **shape**, not
  a chart. Its regions deliberately **beat**, **miss** and exactly **match** their quotas, and the
  beats are the load-bearing part rather than the flattering one: the crossbar-contrast trap
  strikes *only* where the measure exceeds the goal, so a sample where every region missed would
  hide the one failure a reader could not diagnose (`North` matching exactly is the honest edge
  that a per-*row* equality is fine, unlike the per-*column* one the app guards). Every value is
  present — the missing-goal, missing-measure and missing-both cases are the tests' job, the
  `_temperature_range`/`_forecast_range` rule — and `deals_closed` is a throwaway numeric column
  (the `tenure_years`/`calls_per_min` rule) that earns a second keep here: the Goal picker defaults
  to the *second* numeric column, so it must sit below `quota` rather than compete with it.
  `Marketing conversion funnel (funnel)` and `Customer loyalty pyramid (pyramid)` are the same
  single-value **stage** shape drawn two ways: both lead with their **largest** stage and decrease,
  but the funnel puts it at the top and narrows downward (a shrinking purchase journey) while the
  pyramid draws row 0 at the **base** and narrows upward to an apex (a broad-based loyalty pyramid,
  the biggest group at the bottom) — so reading the two side by side shows the only difference is
  which way the shape points, not the data (the row-0-at-base direction was **verified by
  rendering**, since Highcharts draws a pyramid as the vertical flip of a funnel).
  `Product line margin by revenue (variwide)` extends that set of mirrors to a **three**: the
  temperature range, the sales-vs-quota strip and this one all lead with a category and carry two
  magnitude columns, and all three mean something different by them — two **ends of one bar**, two
  **independent claims** on one channel, and **one claim over two geometric channels** (a height and
  a width, whose reading is their AREA). `Market share shift by region (dumbbell)` closes it into a
  **four**, with the fourth reading: **one claim at two times** (the same measurement, of the same
  thing, taken twice, so what is read is the DELTA). So the four side by side are the fastest way to
  see that "two magnitude columns" is a data **shape**, not a chart. The dumbbell sample's rows move
  in deliberately **mixed** directions — two rise, two fall, one barely moves — and the falls are the
  load-bearing half rather than the pessimistic one: a frame that only rose would draw identically
  whether the before/after hues track the first array slot or the numerically smaller value, so it
  would hide the one way this type can silently lie. `UK & Ireland` moving 0.3 of a point is the
  honest edge, showing what "no material change" actually looks like — which is also why the
  before-equals-after guard matters, since that collision would draw *every* region that way. Its two columns deliberately
  **anti-correlate** — the best margin belongs to the smallest line — because a frame where margin
  simply rose with revenue would draw as a staircase, every bar's area ranked the way its height
  was, and a reader would never learn the width was carrying information. Revenues span ~3x so the
  width channel is unmistakable; every value is present and every width positive, the
  `_temperature_range`/`_forecast_range`/`_sales_vs_quota` rule (the missing-, zero- and
  **negative**-width cases are the tests' job, the negative one especially, since it does not merely
  fail to draw itself but shrinks the total every other bar's width is a share of). `sku_count` is
  the throwaway numeric column, and it earns its second keep by POSITION exactly as
  `deals_closed` does: the Width picker defaults to the *second* numeric column, so `revenue_musd`
  must sit directly below `margin_pct` and this one below both.
  `Company reporting lines (organization)` is the **edge-list cousin** of the sunburst
  `_org_headcount` sample: both describe a hierarchy, but that one sizes concentric rings by a
  headcount **value** while this one draws titled boxes and carries no magnitude at all (an org
  chart is unweighted). One person (Nadia, the CEO) has a **blank manager** — the root, which draws
  no reporting line but leads the chart — and several are both a manager and a report; the `title`
  column is the **third**, so the app's Title control defaults to it and the cards show without a
  click, and `tenure_years` is a throwaway numeric column (ignored by the chart, carried so the
  roster clears the no-numeric-columns gate — the `_service_dependencies`/`calls_per_min` rule).
  Every sample leads with a **category column**, and that is load-bearing rather than tidy: the app
  opens on `line` with the first column as X, so a numeric first column would trip the x-in-y guard
  the moment the dataset was selected.

## The test suite, type by type

- `tests/test_smoke.py` — builder unit tests (every chart type, the missing-data
  and scatter/bubble edge cases, radar's polar-line shape, heatmap's colorAxis
  value matrix, treemap's value-sized tiles, funnel's and pyramid's `{name, y}` stages
  (the pie-keyed leaf, the drop-the-row policy, the preserved row order, the two dark-mode
  flips, the `modules/funnel`-not-`highcharts-more` resolution, pyramid's own `chart.type`
  with no `reversed`, and the count-adaptive "Stages" KPI), sankey's node-link flows, boxplot's
  aggregated Tukey distributions, waterfall's appended total and semantic bar
  colors, sunburst's assembled hierarchy (synthesized ids, valueless internal nodes,
  the dropped dangling parent vs. the raised cycle, and the appended root), xrange's
  interval bars (the date-vs-number coordinate sniff and its two silent traps — a numeric
  column reaching a date parser, and an unnormalized epoch view — plus the kept milestone,
  the dropped backwards bar, and the per-lane hue), columnrange's range bars (the `[low, high]`
  2-array that must NOT collapse; the null slot for a missing/non-finite end; the **kept**
  inverted range that is xrange's dropped backwards bar in mirror; the single hue and the
  `colorByPoint` that must appear nowhere; the low-required and low≠high guards and the x-in-y
  one; the `highcharts-more` module resolved from `chart.type` alone; and the one border-dissolve
  `_themed` hook), arearange's filled band (the same coverage sharing columnrange's helpers, plus
  the two facts unique to the shared-branch mirror: `test_arearange_and_columnrange_differ_only_in_
  chart_type`, a byte-diff proving the branch stays shared, and `test_arearange_has_no_dark_mode_
  theme_hook`, which pins the *absence* of the border-dissolve hook — the mirror of columnrange's
  presence, and the render-verified divergence — plus the "Points" KPI distinct from "Ranges"),
  variwide's width-weighted bars (the `[value, width]` 2-array, read as `[y, z]` because
  `xAxis.categories` supplies the names — where the literal key `z`, like bullet's `target`, must
  appear **nowhere** in the emitted JS, so the inverted idiom again; the all-or-nothing null slot
  and its *render-derived* premise, that a bad width drops out of the width TOTAL and silently
  widens every OTHER bar; the negative width nulled where a negative HEIGHT survives, the one type
  whose two value columns take different predicates; the dict-point-form companion proving a null
  `z` VANISHES there, so the single hue is structural; `colorByPoint` asserted NOWHERE beside its
  survives-the-round-trip twin; the absent `pointPadding`/`groupPadding` that make the bars touch;
  the sixth seat in the border-dissolve tuple; the row-less `count_marks` cast that no sweep covers
  (bullet's gap, closed the same way); the `y_cols` DECOY, which must sit in the SELECTION rather
  than in the frame or it pins nothing; and `modules/variwide` from `chart.type` alone with no
  `highcharts-more`),
  dumbbell's before/after pairs (the `[before, after]` 2-array; and above all
  `test_dumbbell_keeps_the_before_in_slot_zero_even_when_the_value_falls`, which is the type's
  headline as a test — the FALLING rows are asserted in the frame's order, and stated as the
  invariant rather than only as two literals, because a `sorted()`/`min-max` "tidy-up" would still
  draw a plausible chart while swapping the before/after hues on exactly those rows; the
  all-or-nothing null slot swept over five unusable-reading combinations, its premise the only one
  of the four that is *not a choice* (a half-pair draws nothing); the bare-`EnforcedNull` companion
  that drives `Chart.from_options` to prove `[EnforcedNull, EnforcedNull]` RAISES one layer below
  `build_options` — bullet's `target` trap in a third validator, so an options-dict assertion could
  never see it; the off-palette before hue, pinned as both off-`DEFAULT_COLORS` and unmoved by a
  custom palette; `colorByPoint` asserted NOWHERE **beside its dropped-by-the-library companion** —
  the mirror of bullet's and variwide's, whose equivalents prove the key SURVIVES and so guards a
  real decision, where this one proves it cannot be made to work at all; the `{point.category}`
  tooltip with `{point.name}`/`{point.y}` asserted absent and the two names LABELLED; the
  `_tooltip_label` sanitization of a `{}`-carrying and a markup-carrying column name;
  `test_dumbbell_has_no_dark_mode_theme_hook`, which pins the *absence* of the border-dissolve hook
  at the PATH and not as a bare substring — the trap that caught this very test while it was being
  written, since `borderColor` is in every dark chart's JS as tooltip chrome; and
  `modules/dumbbell` **with** `highcharts-more`, asserted in ORDER and with `_order_script_tags`
  proven a no-op),
  bullet's measure-against-goal pairs (the `[measure, goal]` 2-array — where the literal key
  `target` must appear **nowhere** in the emitted JS, since the value survives *positionally*, so
  the module's dominant `assert "…" in js` idiom is **inverted** here and every JS-level pin
  asserts the array; the four independent-channel combinations, each end nulling ALONE; the goal's
  Python `None` — the module's one `EnforcedNull` carve-out — pinned by a test that drives
  `make_chart` rather than `build_options`, the only layer at which a `CannotCoerceError` one
  layer below `build_options` is observable at all; the `targetOptions.color` that closes the
  crossbar trap, and its dark-mode **flip**, the one `_themed` hook that moves a MARK; the fifth
  seat in the border-dissolve tuple; the single hue with `colorByPoint` asserted NOWHERE — the one
  such pin guarding a real decision, since bullet's *survives* the round-trip at both levels; the
  absent `yAxis.plotBands`; the measure-required and measure≠goal guards and the shared x-in-y one;
  `count_marks` agreeing with the built length; and `modules/bullet` resolved from `chart.type`
  alone, with no `highcharts-more`),
  the **gauge family's** reduced marks
  (`solidgauge`'s rings: the empty-column
  trap, swept over all six reductions because only `sum` lies; the dial derived from the
  *readings* rather than the raw column; `threshold: 0`; the three levels a ring's hue has to
  be written to; the pane that alone resolves `highcharts-more`; and the fact that the family is
  *excluded* from the label-drop sweep — where it would pass **vacuously**, reading as a pin on
  a policy it deliberately does not have. And `gauge`'s needles: the staggered lengths, without
  which two equal readings draw as ONE needle while the legend goes on naming two; the hue on the
  dial and the legend but never the point — a *different* two from the ring's three, with no
  overlap; `highcharts-more` resolved from `chart.type` alone, pinned by taking the pane away; the
  pane that carries **neither** `size` nor `center`, both pinned absent so nobody re-adds the one
  the library silently drops; the face that carries no grid, **not even the minor one**; the
  `topWidth` that must appear at every dial level or `Chart.from_options` cannot build the chart at
  all — so that test drives `make_chart`, not `build_options`; nothing printed in the mark, swept
  over the count so no gate can creep back; and
  `test_needle_and_ring_cannot_disagree_about_the_readings_or_the_dial`, which is the family
  invariant *as a test*: one frame, one selection, one reduction, two types, the same numbers), the
  brand
  palette, the validation
  guards including bubble's required size column, sankey's required and distinct
  target column (shared verbatim by networkgraph and organization, whose *empty* `y_cols` are pinned
  both ways — an exclusion from the empty-Y sweep (now keyed on `UNWEIGHTED_NODE_LINK_TYPES`) and a
  positive build — the mirror of gauge's `None` `x_col`; organization's own tests add the
  root-vs-phantom-link distinction, the `_node_key` int/float match, the deduped title `nodes`
  array, the `modules/sankey`-before-`modules/organization` load-order pin, the no-`_themed`-hook /
  palette-cycling render facts, and the `count_marks`-matches-the-built-links can't-drift check),
  sunburst's required and distinct parent column, xrange's required end
  column (distinct from the *start* column, not from `x_col`), the gauge family's known aggregation
  and its dial-with-a-span, and the
  heatmap/boxplot/waterfall/columnrange/arearange/bullet/variwide/dumbbell x-in-y rule, and
  an end-to-end pass driving every supported type through `Chart.from_options` /
  `to_js_literal`) and `sample_data` unit tests, plus headless `AppTest`
  interaction tests. The AppTests find widgets by **label**, not by position —
  `_pick_sample(app, chart_type)` is the shared body of the seven `_pick_*_sample` helpers, each
  of which keeps its own name and its own argument for why that type needs a dedicated sample
  rather than the landing dataset.

And what `tests/test_smoke.py` pins, in detail:

`tests/test_smoke.py` exercises the pure builder (`build_options`) —
parametrized across every supported chart type, covering missing data
(`EnforcedNull` for the category-x family — cartesian and radar — dropped
points/slices elsewhere) and non-finite data (each type applying that same policy
to an `inf`, swept over `SUPPORTED_TYPES` by asserting no type emits a bare `inf`
into the serialized JS), the numeric vs non-numeric scatter/bubble paths
(bubble adds the `(x, y, size)` triples whose series share one size column, plus
its dimension-naming tooltip), radar's polar-line shape (`chart.type` `line` +
`chart.polar`, sharing the `highcharts-more` module and themed by the same
`_themed` chrome), heatmap's colorAxis value matrix (`[x, y, value]` cells over
two category axes, empty cells kept as `EnforcedNull`, its colorAxis themed for
dark mode and resolving the `modules/heatmap` module), treemap's value-sized tiles
(`{name, value}` leaves colored categorically via `colorByPoint`, missing values
dropped like pie, its tile gaps themed for dark mode and resolving the
`modules/treemap` module), sankey's node-link flows (`{from, to, weight}` link
dicts over two node columns — the `keys`-plus-arrays form highcharts-core
rejects outright — rows missing any of the three dropped, its per-link weight
labels gated on link count, its node/link borders themed for dark mode while the
labels ride Highcharts' `contrast` default, and resolving the `modules/sankey`
module), dependencywheel's shared-branch reuse (the same `{from, to, weight}` links as sankey,
pinned to emit `chart.type` `dependencywheel` under its OWN `plotOptions` key — not left under
`sankey` — with the node tooltip surviving there as sankey's does; resolving **both**
`modules/dependency-wheel` and `modules/sankey` from `chart.type` alone and *not* `highcharts-more`;
sharing sankey's `count_marks` rule (proven in the count-vs-built sweep) and its dark border
dissolve; the two node-link guards; and the migration sample where every region is both origin and
destination), boxplot's aggregated Tukey distributions (raw observations grouped by a
repeating `x_col` into positional `[low, q1, median, q3, high]` 5-arrays in
first-appearance order; the outliers split into a linked scatter series that is
emitted only when they exist; the `iqr == 0` degeneracies — a one-observation group,
an all-identical group, and one with genuine tails — that the *inclusive* fence
decides; the matplotlib whisker clamp at *both* ends (a skewed group whose `q1` falls
below every in-fence point, and its mirror whose `q3` rises above every one); non-finite
observations dropped and a text column rejected with `ValueError`; an all-missing group
kept as an `EnforcedNull` box while a missing
`x_col` key forms no group; and the `fillColor`/`stemColor` silent drop pinned on the
emitted JS, which is why its box interior stays white and it needs no `_themed` hook),
waterfall's cumulative bridge (the appended `isSum` total — pinned on the emitted JS,
and *absent* when no step survives to sum, so a lone "Total: 0" bar is never drawn;
the semantic up/down/total colors, which a custom `colors` palette must NOT repaint,
and the total's *per-point* color, whose absence would silently paint it with the DOWN
color and read it as a loss whatever its sign; a missing delta keeping its axis slot as
an `EnforcedNull` rather than dropping its row; the in-bar value labels and their
step-count gate on both sides of the boundary; the `{point.category}` tooltip token,
since the positional points would render `{point.name}` blank; and the two dark-mode
hooks, bar borders *and* connector lines),
sunburst's assembled hierarchy (the synthesized ids — pinned by two leaves both named
`Other`, which must stay two sectors worth 100 and 40 rather than merging into one worth
140, the exact corruption label-as-id causes and which Highcharts rejects outright as
error #31; the invariant that every drawn leaf carries a `value` and every internal node
carries none, *even when the CSV states one*, since a stated parent value overrides the
sum; the appended root, its off-palette color that a custom `colors` must NOT repaint,
and its absence when no node survives; the dangling parent dropped *with its descendants*
rather than silently re-parented; the cycle, the self-parent one-node cycle, the
rootless forest that is necessarily a cycle, and the cycle a dangling row must not hide;
the 5,000-long cycle and 5,000-deep chain that pin the walk as iterative; the ambiguous
parent label that raises where an unreferenced duplicate does not; `_sizable` dropping a
negative leaf while keeping a zero; the `_node_key` int-vs-float trap, where a blank
parent cell widens that column to `float64` and a bare `str()` would dangle every row and
empty the chart *silently*; the per-point ring-1 seeding and the `colorByPoint` that must
appear NOWHERE in the emitted JS — dropped from `levels`, and wrong at series level; the
alternating `colorVariation`; the name-only sector labels and their gate; and the one
dark-mode hook),
xrange's interval bars (the **epoch pin** — `2026-01-05` must serialize to exactly
`1767571200000`, asserted across four column shapes (object ISO strings, `datetime64[us]`,
`datetime64[s]`, tz-aware), since the obvious `// 1_000_000` divisor is right for exactly one
of them and renders the rest in 1970; the **epoch trap mirrored** — an int column stays
numeric and gets *no* datetime axis, because `pd.to_datetime(12)` would silently make it the
epoch; the sniff table, including the month-name column that `format="ISO8601"` must reject
*because it is the landing sample's*, and the DST column that raises without `utc=True`; a
build under `warnings.simplefilter("error")`, the only way the ISO-8601 pin is observable; the
kept-and-floored milestone with `minPointLength` pinned on the emitted JS, and the dropped
backwards bar *with its lane gone from the axis*; `_spannable`'s four boundary pairs and the
`-inf`/`+inf` hole that `end >= start` alone would leave; the per-lane hue, a custom palette,
a short one that must cycle rather than `IndexError`, and the `colorByPoint` that must appear
NOWHERE — the mirror of sunburst's, since here the series-level one *survives* and is wrong;
the `{point.name}` tooltip, since `{point.category}` renders the raw epoch; the absent
dataLabels; the **no-drift pin**, a frame whose only garbage cell sits on a row dropped for its
label, which a raw-frame sniff would decide differently from the chart; and the one dark-mode
hook),
columnrange's range bars (the `[low, high]` **2-array** pinned on the emitted JS, since a
numeric-first 2-array must serialize as `[low, high]` rather than collapse the way a `{name, low}`
dict would — boxplot's lesson, one type over; the **null slot** kept as a bare `EnforcedNull` for
a missing OR non-finite end, with no `inf` reaching the JS; the **kept inverted range**
(`8 → -3`), which is xrange's *dropped* backwards bar in mirror — a columnrange bar is bounded by
its two values, so it is honest, not a whole-axis lie; the **single hue** with `colorByPoint`
asserted NOWHERE, the opposite of xrange's per-lane call; the low-required and low≠high guards and
— since its `x_col` is a real category axis — the shared x-in-y one; `count_marks` counting by
label like waterfall (a null slot still counted) and agreeing with the built length; the
`{point.category}` tooltip, waterfall's fix reached for the right reason; `highcharts-more`
resolved from `chart.type` **alone** and NOT a phantom `modules/columnrange`; and the one
border-dissolve dark hook it shares with column/bar/xrange, measured rather than inferred from the
shared bar base class),
arearange's filled band (columnrange's coverage in mirror, reusing its `_range_df`/`_ranges`
helpers: the same `[low, high]` 2-array, null-slot, kept-inverted, single-hue/no-`colorByPoint`,
`{point.category}` tooltip, three guards, `count_marks`-agrees-with-built and `highcharts-more`-
from-`chart.type`-alone checks — plus the two facts unique to the shared-branch mirror:
`test_arearange_and_columnrange_differ_only_in_chart_type`, a **byte-diff** proving the branch stays
shared once `chart.type` and the type-derived default title are set aside, and
`test_arearange_has_no_dark_mode_theme_hook`, which pins the *absence* of the border-dissolve hook —
the render-verified divergence, the mirror of columnrange's presence — and the "Points" KPI distinct
from "Ranges"),
bullet's measure-against-goal pairs (the `[measure, goal]` **2-array**, pinned on the emitted JS by
asserting the ARRAY and by asserting the literal key `target` is **absent** — the value survives
POSITIONALLY, so `assert "target" in js` is false on a correct chart and this module's dominant
test idiom is inverted here, which is stated in the test as the reason; the **four independent-
channel combinations**, each end nulling ALONE — measure-no-goal, goal-no-measure, neither (the
category tick kept), and the inverted pair KEPT as the ordinary reading, which is columnrange's
all-or-nothing slot in mirror; the goal's Python **`None`**, the module's one `EnforcedNull`
carve-out, pinned by a test that drives **`make_chart`** rather than `build_options` — the only
layer at which `CannotCoerceError` out of `target`'s `validators.numeric` is observable at all, the
`_NEEDLE_DIAL` lesson in a different validator — plus the mixed `[EnforcedNull, None]` array
serializing to `[null, null]`; `targetOptions.color`, the crossbar-contrast fix, and its dark-mode
**flip**, the one `_themed` hook that moves a MARK rather than chrome, asserted on both themes;
the border dissolve that makes bullet the fifth member of that literal tuple; the single hue with
`colorByPoint` asserted NOWHERE — the one such pin guarding a real *decision*, since bullet's
survives the round-trip at BOTH levels, so nothing but the choice keeps it off — and the *absent*
`yAxis.plotBands`, a pin on a mark the data never made; no numeric key under `targetOptions` at
all, so neither the `width = 0` `EmptyValueError` nor the `numpy.int64` rejection is reachable; the
measure-required and measure≠goal guards and the shared x-in-y one; `count_marks` counting by label
and agreeing with the built length; the `{point.category}`/`{point.y}`/`{point.target}` tooltip;
and `modules/bullet` resolved from `chart.type` alone with NO `highcharts-more`),
gauge's reduced rings (the **empty-column trap**, swept over all six reductions because only
`sum` lies — `pd.Series([nan, ...]).sum()` is `0.0`, an additive identity drawn as a real ring
at the dial's floor — with the assertion that pandas really does say `0.0` standing IN the test
as the reason; the ring KEPT as a bare `[EnforcedNull]` (`{"y": EnforcedNull, "color": …}` would
have its `y` dropped out of the dict entirely) and named in the legend, which is the only thing
that names it; the **dial derived from the readings**, pinned by a frame whose `sum` (436)
exceeds every observation in its column (63), so a raw-column dial would pin every ring — plus
the sweep asserting every reading falls inside its own dial under every reduction; the nice
ceiling and its overflow/underflow holes (`1.5e308` must not emit `inf`; `5e-324` must not
collapse the dial to nothing); `threshold: 0`, without which the −155 draws a *shorter* arc than
the −40; the overflow that makes a finite column non-finite (boxplot's lesson, second arithmetic
type); the **three levels a ring's hue is written to** — the point (the arc), the marker (the
legend swatch) and the label — with `colorByPoint` asserted to appear NOWHERE and a series-level
`color` asserted ABSENT, since it does no work here at all; the **pane** that alone resolves
`highcharts-more`, without which the iframe is silently blank while the PNG renders; ticks
silenced by *width* rather than by the pruned `tickPositions: []`; the label gate's explicit
`{"enabled": False}` (a gauge's labels default to ON, so an omitted key would be a gate that did
nothing); the geometry capped at BOTH ends (never inverted at 40 rings, never a disc at 1); and
`test_gauge_ignores_x_col_entirely`, which is where the label-drop policy gauge does NOT have is
pinned — a frame whose label column is entirely undrawable must still aggregate every row),
the brand palette, the
light/dark theming (dark-mode chrome — including the tooltip and the heatmap
colorAxis — vs. the shared palette), and the validation guards (including the
category-x x-in-y rule, widened to heatmap, boxplot, waterfall, the magnitude-range pair, bullet,
variwide and dumbbell, bubble's required
size column, sankey's required, distinct target column, sunburst's required,
distinct parent column, xrange's required end column, distinct from the *start*
column rather than from `x_col`, bullet's required goal column, distinct from the *measure* column
for the same reason, gauge's known `agg` and its dial-with-a-span, and — the
mirror of gauge's own exemption — the `x_col` that every OTHER type now requires) —
plus an end-to-end pass driving every supported type through the real
`Chart.from_options` → `to_js_literal` pipeline (so a newly added type is proven
to serialize — bubble, radar, boxplot, waterfall, columnrange, arearange and dumbbell all pulling in the
`highcharts-more` module (columnrange and arearange from `chart.type` alone, with no
`modules/columnrange` or `modules/arearange` — the
plausible guess the round-trip corrects),
heatmap the `modules/heatmap` module, treemap the `modules/treemap` module,
funnel and pyramid the `modules/funnel` module (shared, from `chart.type` alone — and *not*
`highcharts-more`, the plausible guess the round-trip corrects, as it does for columnrange),
sankey the `modules/sankey` module, sunburst the `modules/sunburst` module, xrange the
`modules/xrange` module, bullet the `modules/bullet` module (those three alone among the
extra-module types needing *not* `highcharts-more` — and bullet alone among *them* needing no
`_MODULE_LOAD_ORDER` entry either, since `bullet.js` requires only `highcharts`, unlike
dependency-wheel's and organization's `modules/sankey` and solid-gauge's `highcharts-more`),
and gauge `modules/solid-gauge` **plus** `highcharts-more` — which is the
one module resolution that is not merely proven but *load-bearing*, since it is pulled in by the
`pane` alone and without it the chart draws an empty SVG in the browser with no error anywhere,
while the export server renders it perfectly — rather than just
assumed; sankey's node
tooltip is pinned in that serialized JS too, since a top-level `nodeFormat` is
accepted by `Chart.from_options` and then silently dropped, as boxplot's `fillColor`
is and as sunburst's `levels[].colorByPoint` is, and waterfall's `isSum` is pinned
there for the same reason — it is a point key
that *does* survive, which only the emitted JS can show, as sunburst's `id`/`parent`
and `allowTraversingTree` are, and as xrange's `x2` and `minPointLength` are, and as gauge's
series-level `radius` is — the *surviving* half of a pair whose point-level half is dropped; bullet's
`target` is a **third** case again, and only the emitted JS can show it either: the key never
appears at all while its VALUE survives positionally, so the pin asserts the array and the *absence*
of the name) and
the sample
datasets, then drives the full app headless via Streamlit's `AppTest` (switching
controls — including the bubble Size (Z) control, radar, heatmap, treemap,
sankey's Target (to) control (and dependencywheel reusing it identically, its KPI reading
**Flows** like sankey's; and networkgraph reusing it while drawing *no Y control at all*,
its KPI reading **Links** over an empty selection), sunburst's Parent control, xrange's End
control, columnrange's **High (top)** control (over a renamed **Low (bottom)** single-select Y,
its High picker offering only numeric columns and surviving a Low change via its constant index,
its KPI reading **Ranges**) — and arearange **reusing that very control and `high_col`**, its KPI
reading **Points** instead (the shared-control mirror of dependencywheel reusing sankey's Target),
bullet's **Goal (target)** control — which looks like that same shared High and is a *separate*
widget feeding a separate `goal_col`, so the AppTest pins it as its own: numeric columns only, its
constant `min(1, …)` index landing on the second so it starts distinct from Measure, surviving a
Measure change (a Goal is still valid when the Measure moves, Target's/Parent's/End's/High's case,
not the Dial's), and its KPI reading **Measures**,
gauge's
aggregation picker and Dial min/max inputs — and gauge's *absent* X control and networkgraph's
*absent* Y control, the two mirror-image subtractive changes — and boxplot's
and waterfall's
single-select Y —
revealing the generated config behind its toggle,
the KPI metric row, the wide-CSV
`st.multiselect` fallback, the render-mode selector's two modes, and asserting
the guard messages — including a *cyclic uploaded CSV*, the one builder error a user
can reach just by uploading a file, which must warn and stop rather than render a
traceback, its xrange counterpart, a date start beside a numeric end, and its gauge
counterpart, a dial with no span; and bullet's **Measure == Goal**, which is a different
animal from those three — not a contradiction the *data* states but a collision of two required
columns, warned in front of the builder's own `ValueError` (columnrange's double) because the
interactive path does not catch, and worth a test because it fabricates the chart's central
claim rather than merely failing: every bar would sit exactly on its own crossbar and the chart
would report that every category hit target precisely; plus the
**type-aware column gate**, driven by an uploaded Gantt CSV with *no numeric columns
whatsoever*, which must plot as an xrange and must still be refused by `line`).

Gauge's two AppTest halves are worth naming, because together they *define* the keyless-widget
rule rather than merely obeying it. The Dial inputs carry **no `key=`**, and unlike every other
picker here that is the intended behaviour, not the bug the constant `index`es guard against.
The rule those comments were always applying, stated: *fold the default into the widget's
identity iff the selection depends on the state the default derives from.* Sankey's Target
derives from another **widget** and stays perfectly valid when Source changes, so re-minting it
would discard a real answer. A dial derives from the **data under a reduction**, and an override
of it is meaningless the moment either changes — a max of 500 typed against `sum` (436) would
leave every ring at ~1% under `mean` (54). A `key=` is precisely how you would *cause* that: with
a key, `value=` is honoured only on the FIRST render, so the stale number becomes permanent and
silent. One test pins that a typed dial **survives** an inert rerun (a title edit); its twin pins
that it is **re-derived** when the aggregation changes.

## Appendix: the cross-cutting conventions in full

- When working with Python, invoke the relevant Astral skill (`/astral:uv`,
  `/astral:ty`, `/astral:ruff`) for uv, ty, and ruff to ensure best practices
  are followed.
- Keep chart-building logic (DataFrame → Highcharts) in `highcharts_builder.py`,
  free of Streamlit imports, so it stays unit-testable.
- Keep each hook's decision logic in a pure, importable function in
  `.claude/hooks/` (as the builder is), so `tests/test_hooks.py` can cover it
  without subprocesses; the `main()` wrapper handles the stdin/exit-code plumbing
  and any impure subprocess orchestration (ruff/ty/pytest/git). `.github/scripts/
  release.py` follows the same split for CI (pure logic + thin `main()`, tested by
  `tests/test_release.py`); both load their script by file path via
  `tests/conftest.py`'s `load_script`.
- The `release` job in `ci.yml` carries real bash, so validate edits before
  pushing: `shellcheck -s bash` the extracted `run:` block and structure-check the
  file with `uv run --with pyyaml` (neither is a project dep). Exercise the script
  on the interpreter the job uses:
  `uv run --no-project --python 3.12 python .github/scripts/release.py to-release vX.Y.Z`.
- **Adding a chart type falsifies prose nobody edited.** This file is dense with uniqueness
  claims, and each is a claim about *every other type* — including ones that don't exist yet —
  so a new type can make a sentence false in a passage no diff touched, locally correct on both
  sides, with only the *pair* contradicting. Nothing mechanical can see it. Sweep
  ``grep -noE 'the (one|only) [a-zA-Z*`_.]+ [a-zA-Z*`_.]+' CLAUDE.md`` after adding a type and
  check each hit against the code. Two were stale when `bullet` landed: waterfall's "the one type
  needing **two** `_themed` hooks" (bullet is the second), and its "the one type whose mark count
  exceeds its row count" — which `sunburst`'s appended root had falsified long before, while
  sunburst's own passage already said "this is the second such type".
  Three more were stale when `variwide` landed, and the third is the instructive one: bullet's
  "the one recent type that **does** touch the cache layer" (variwide's `width_col` is a second),
  bullet's "the **fifth** member of the literal tuple" (variwide is the sixth), and — surfaced by
  the sweep rather than caused by it — boxplot's "the **only** type whose builder *aggregates*",
  which the gauge family had already falsified while gauge's own passage said "the second
  aggregating type". So the sweep catches PRE-EXISTING drift too, not only what you just added;
  fix what it finds rather than only what your diff caused. Note also that the prescribed grep
  does **not** catch ORDINAL claims ("the fifth member", "the seventh column kwarg") — sweep
  ``grep -noE 'the (first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)' CLAUDE.md`` as
  well — and note that this regex is itself a tally that goes stale, since each new type can push an
  ordinal past the end of it. `dumbbell` made `ninth` reachable; extend the alternation rather than
  assuming the sweep still covers the top of the range.
- Render every visualization with Highcharts (`highcharts-core`); do not use
  native Streamlit charts.
- Use `EnforcedNull` (from `highcharts_core.constants`) for missing data points
  in dict configs fed to highcharts-core (`Chart.from_options`), not Python
  `None`. **There is exactly ONE exception, and it is exactly one slot wide: a bullet point's
  GOAL — the second element of its `[measure, goal]` array — must be Python `None`.** Do not
  "fix" it back. `options/series/data/bullet.py`'s `target` setter runs
  `validators.numeric(value, allow_empty=True)`, which admits `None` and rejects `EnforcedNullType`
  with `CannotCoerceError` — and it raises at `Chart.from_options`, **one layer below
  `build_options`**. So the whole options-dict test suite stays **green** while the chart cannot be
  built at all, and the app's interactive path (which does not catch builder errors) shows a bare
  traceback naming neither `target` nor `bullet`: the `_NEEDLE_DIAL` trap in a different validator.
  The same point's **measure** slot takes `EnforcedNull` normally, so the array is deliberately
  mixed (`[EnforcedNull, None]` serializes to `[null, null]`, verified). Pinned by a test that
  drives `make_chart` rather than `build_options` — the only layer at which the failure is
  observable — and stated here because that is the only thing standing between the carve-out and a
  tidy-up that silently breaks the type. (The related trap: any per-point key outside
  `{x, y, target, name}` forces the point DICT form, where a `None` target *vanishes* from the
  emitted JS instead of nulling while `EnforcedNull` still raises — no working spelling at all,
  which is why the branch emits a bare array and takes a single hue.)
- A **row-less** frame (columns, no rows — a CSV with a header and no data) is a legitimate
  input and must draw an **empty chart, not raise**. Every `Series.map(...)` used as a mask
  must therefore be `.astype(bool)`-cast: `.map()` infers its result dtype from the values it
  produced, and with no rows there are none, so it returns an empty **non-boolean** Series
  (object, or `str` for an Arrow-backed column). That then breaks three different ways —
  a DataFrame indexed by a non-boolean Series is not masked at all but read as a list of
  **column names** (this is what made `build_options` die with a bare `KeyError` in *every*
  type — one shared line, so the count is however many types there are, and a new one
  inherits the bug the day it is added unless the cast is there); `.sum()` of an empty string
  mask is `''`, so `int()` raises `ValueError`; and
  `&` between two of them raises out of the Arrow kernel, while `bool & str` merely *warns*
  today but is deprecated and will raise in pandas 4. The casts live at
  `build_options`' `_label_ok` filter, on all three of `count_marks`' masks, and on
  `_xrange_bars`' own `keep` mask. Sunburst is
  the one type that needs no cast of its own: `_sunburst_tree` reads the frame with a plain
  `zip` rather than a mask, so a row-less frame is simply an empty loop, and its `count_marks`
  branch returns *above* the three masks. It still rides the shared `_label_ok` filter, so it
  is covered by that cast like everything else. Xrange's `count_marks` branch likewise returns
  above the three masks, but `_xrange_bars` re-applies `_label_ok` *itself* — a mask, and so
  a cast — because it must produce byte-identical output from the raw frame `count_marks`
  hands it and the filtered one `build_options` does. A row-less coordinate column is also the
  one case `_coordinates` must NOT call a contradiction: nothing parses, but nothing is
  *present* either, so it is missing data (an empty chart), not a column of the wrong kind.
  Gauge needs no cast either, and for a third reason: it reads no mask at all (it reduces whole
  columns), and its branch returns above the shared filter. But it is the one type whose empty
  chart is **not zero marks** — its marks are the selected COLUMNS, not the rows, so a
  header-only CSV still selects one, and the ring is kept as a **null**. That is not a special
  case for the row-less frame: it is the ordinary no-data reading, arrived at with no rows rather
  than with blank ones. Two sweeps
  pin it (`test_row_less_frame_draws_an_empty_chart_in_every_type` over `SUPPORTED_TYPES`,
  and `test_count_marks_casts_every_mask_not_just_the_label_one`, which promotes warnings to
  errors — the only way the non-label casts are observable at all).
- Treat a **non-finite** number as a missing one. `pd.isna(inf)` is `False`, but an
  infinity can't be serialized: `to_js_literal` emits the bare token `inf`, which is not
  a JavaScript identifier (JS spells it `Infinity`), so the chart call dies with a
  `ReferenceError` and the iframe renders blank; the export server, sent the
  non-standard JSON literal `Infinity`, answers `400`. So each type applies the same
  missing-data policy to a non-finite **value**: the keep-the-slot types go through `_num`
  (gap = `EnforcedNull`), the drop-the-row types through the shared `_plottable` predicate
  (pie, treemap, scatter, bubble, and sankey's *weight*), boxplot and gauge — the two
  AGGREGATING types, which share `_finite_values` for exactly this reason — drop non-finite
  observations before reducing, and, because they are the two types that do *arithmetic*
  on the values, then null the whole mark (an `EnforcedNull`) if that arithmetic overflows
  a finite column into a non-finite quantile/fence (boxplot) or reading (gauge:
  `1e308 + 1e308` is `inf`, and a `1e308` cell parses out of a plain CSV) — and xrange drops
  the row via
  `_spannable`, whose `_plottable`-on-both-ends half exists precisely for this: `end >= start`
  alone accepts `(-inf, 10)`, so the comparison is *not* enough on its own and the finiteness
  check is what keeps a bare `inf` out of the emitted JS. **Bullet is the one type whose two value
  columns apply the policy INDEPENDENTLY**, and that is a policy rather than an oversight: a
  columnrange's pair are two ends of one mark, so `_range_point` nulls the whole slot
  all-or-nothing (a range with one end is not a range), while a bullet's are two **independent
  channels**, so `_bullet_point` nulls each end **alone** — a missing or non-finite measure leaves
  the goal's crossbar drawn over an empty slot, a missing or non-finite goal leaves the bar drawn
  with nothing to compare it to, and a row missing both still keeps its category tick
  (keep-the-slot, never a drop, never a raise). The two ends null with *different tokens* for the
  library reason in the `EnforcedNull` bullet above: `_num` for the measure, `None` for the goal.
  **Variwide is the third reading of that same two-magnitude shape and is deliberately NOT
  independent**, which is why bullet's claim above stays true rather than being quietly broken: a
  variwide's pair are ONE claim over two geometric channels, so `_variwide_point` nulls the **whole
  slot**. Not columnrange's reason ("a range with one end is not a range" — a fact about the MARK)
  but its own, and the sharper one, because it is a fact about the **other rows**: a variwide's
  widths are **shares of a total**, so a bad width drops out of the denominator and silently makes
  every *other* bar wider (measured — nulling one row's width redrew a sibling from 87px to 134px,
  pixel-identical to deleting the row outright). That is also why it is the **one type whose two
  value columns take different predicates**: `_plottable` for the height, `_sizable` for the width,
  since a negative width does not merely fail to draw itself but corrupts the denominator every
  sibling is measured against (rendered: a `-30` inflated its two neighbours past the canvas edge).
  It needs **no** `EnforcedNull` carve-out — `z` coerces both tokens, so bullet's `None` must not be
  copied across.
  **Dumbbell is the fourth reading and likewise NOT independent**, so bullet's claim survives a
  second challenge — but it reaches that answer from a premise neither of the others could supply,
  and the premise is the point: it is **not a policy choice at all**. Highcharts DRAWS NOTHING for a
  half-pair (verified — `[42, null]` serializes cleanly and renders no marker, no connector, just an
  empty tick), so there is no half-drawn state a per-end rule could prefer, and bullet's policy is
  *unavailable* here rather than rejected. That is why dumbbell reuses `_range_point` **verbatim**
  instead of gaining a fourth pair helper: `_variwide_point` exists because its predicates differ,
  not merely because its premise does. It needs no `EnforcedNull` carve-out either — but for the
  **opposite** reason to variwide's, and the difference is a live trap: an `EnforcedNull` *inside* a
  dumbbell's array does **not** coerce, it raises `CannotCoerceError` at `Chart.from_options`, one
  layer BELOW `build_options`. `_range_point`'s **bare** token is what keeps that unreachable, so
  the day someone widens that helper to emit a pair of tokens, dumbbell breaks in the one place the
  options-dict suite cannot see.
  Gauge adds one twist the others have
  no analogue for, and it is pandas', not Highcharts': an **empty** column is not merely a
  no-op for `sum`, it is a `0.0` — the additive **identity**, a confident claim of "the total is
  zero" where the truth is "there is no data" — so `_gauge_value` tests for empty **above** the
  reducer rather than trusting it (`_coordinates`' `_COORD_EMPTY` ordering; and note that only
  `sum` lies, which makes it worse rather than better, since the bug would live in exactly one
  of six reductions). The same policy governs the **label**
  column (the one that NAMES a mark — a slice/category/node/box): a missing or non-finite
  label names nothing drawable, so its row is dropped uniformly via `_label_ok`, filtered
  once at the top of `build_options` (except scatter/bubble with a numeric x, where x is a
  coordinate `_plottable` already guards; sankey's second label column, `target_col`, is
  checked in its own branch; and the **gauge family** (`solidgauge` and `gauge`), which has no
  label channel at all — both branches return *above* the filter, because a row filter over an
  AGGREGATE does not drop a mark, it
  silently changes a NUMBER). This replaced an earlier split where most types kept a
  `"nan"`/`"inf"` label and only sankey/boxplot dropped it. Two sweeps pin it:
  `test_no_supported_type_emits_a_non_finite_js_literal` for the value channel and
  `test_missing_or_non_finite_label_drops_the_row_in_every_type` for the label channel, so
  a new type is covered on both the day it is added. The gauge family is *excluded*
  from the second sweep (keyed on `GAUGE_TYPES`, so `gauge` inherited the exclusion with no edit),
  and the reason generalizes: it would pass **vacuously** (with a clean
  value column the assertion holds whatever the type does with its labels), so it would read as
  a pin on a policy the family deliberately does not have. A vacuous pass is worse than no test.
  Reachable from a plain CSV: `inf`,
  `Infinity`, `-inf` and `1e400` (which silently overflows), and a blank cell (`nan`).
- `build_chart_html` pins the chart's `color-scheme` to `only light`
  (`_LIGHT_COLOR_SCHEME_CSS`, on the `.highcharts-root` `<svg>`, not `html`: Highcharts
  declares `color-scheme: light dark` on the `.highcharts-container` div between them, and
  since the property inherits, that shadows an `html` rule for the SVG subtree — so the pin
  must sit at or below the container to win). Highcharts ≥ 13 expresses
  its own defaults as `light-dark()` CSS variables, so any color we *don't* set would
  follow the **viewer's browser**, not the `dark` flag: a light-mode chart rendered dark
  on a dark-OS browser, and `boxplot`'s unsettable box fill differed between the iframe
  and the PNG. The export server already rasterizes with the light resolution, so this
  makes the two render modes agree and leaves `_themed` the single source of truth for
  dark mode. Anything a new chart type wants themed must go through `build_options`,
  never through a Highcharts default.
- Theme charts via `highcharts_builder.DEFAULT_COLORS` (applied by
  `build_options` to every chart, so the iframe and PNG paths are themed too). It **is**
  `.streamlit/config.toml`'s `chartCategoricalColors` — the bundled financial-dashboard
  theme's categorical scale — copied by hand, because no theme CSS reaches an iframe or a
  server-side PNG and Streamlit applies that key only to its own Vega/Plotly charts, of
  which this app has none. `_DARK_CHROME`'s `bg`/`text`/`muted`/`grid` are the same theme's
  `backgroundColor`/`textColor`/`grayColor`/`borderColor`; only its `axis` is the builder's
  own, a Streamlit theme having no counterpart for tick lines. Every one of those copies is
  guarded by `test_theme_colors_stay_in_sync_with_config`.
  The palette's **order** carries meaning the hues alone do not: `_WATERFALL_UP_COLOR`,
  `_WATERFALL_DOWN_COLOR`, `_WATERFALL_SUM_COLOR` and `_BOXPLOT_OUTLIER_COLOR` index into
  it, so reordering the config list repaints "a rise", "a loss" and "the total" while every
  hue stays present. And the palette **constrains** `_SUNBURST_ROOT_COLOR`: that constant's
  whole definition is "outside the palette", so pointing `DEFAULT_COLORS` at a theme
  containing its hue breaks it — which is exactly what happened when this theme landed
  (slate-400 was index 6 of the new scale) and what
  `test_sunburst_root_color_is_off_the_categorical_scale` caught.
  The palette is shared across light/dark; only the
  chart chrome (background/text/axes/gridlines/tooltip) flips, via
  `build_options(..., dark=...)` / `_DARK_CHROME`. `streamlit_app.py` reads `dark` from
  `st.context.theme.type` and threads it through the cached renderers (so it's
  part of their cache key) — and since the config is a single `[theme]` with no
  `[theme.light]`/`[theme.dark]`, that resolves to dark for every viewer; `dark=False`
  remains a supported builder input, exercised by the AppTests and the light-mode
  per-type tests. The one exception is `heatmap`, which colors its cells
  by a sequential `colorAxis` (`_HEATMAP_GRADIENT`, anchored on
  `DEFAULT_COLORS[0]`; a dark ramp `_HEATMAP_GRADIENT_DARK`, its two endpoints drawn off the
  theme's own `chartSequentialColors`, flipped in by
  `_themed`) rather than the categorical palette — it still carries `colors` for
  cross-type consistency (the palette tests). The second, and the only place a **mark** flips
  rather than chrome, is `bullet`'s goal crossbar: Highcharts draws it at 140% of the bar width,
  so it necessarily crosses **both** the bar (a constant palette blue in both themes) *and* the
  chart background (white → slate), and a fixed colour therefore cannot work **in principle** —
  a near-black reads on the light shell and disappears on the dark one, a near-white does the
  exact reverse (both rendered) — and against the current palette the two 3:1 ranges provably do
  not overlap, so in dark mode the mark carries a **fill and a border**, one per surface. Where
  every `borderColor` dissolve matches a mark **to** the
  background, this hook matches one **against** it, and its light-mode value
  (`_BULLET_TARGET_COLOR`) is `_DARK_CHROME["bg"]` read the other way round, so the pair the
  crossbar swings between cannot drift from the pair the app shell uses
  (`_NEEDLE_PIVOT_COLOR = _SUNBURST_ROOT_COLOR`'s aliasing rule — no new colors invented).
