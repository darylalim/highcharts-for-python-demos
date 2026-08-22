"""Smoke and behavior tests for the Highcharts builder and the Streamlit app.

Run with: ``uv run pytest``

Layers:

- ``build_options`` unit tests covering every supported chart type, the
  missing-data and scatter/bubble edge cases (NaN -> ``EnforcedNull`` for
  cartesian and radar series, dropped points/slices elsewhere, numeric vs
  non-numeric x, and bubble's (x, y, size) triples whose series share one size
  column, its ``highcharts-more`` module resolution, and its dimension-naming
  tooltip), non-finite data (an ``inf`` is not missing but can't be serialized —
  ``to_js_literal`` emits the bare token ``inf``, a JS ReferenceError, and the
  export server 400s — so every type applies its own missing-data policy to it,
  swept over ``SUPPORTED_TYPES``), radar's polar-line shape (chart.type "line" + ``chart.polar``,
  sharing the ``highcharts-more`` module), heatmap's category × category value
  matrix (``[x, y, value]`` cells colored by a ``colorAxis``, empty cells kept as
  ``EnforcedNull``, resolving its own ``modules/heatmap.js``), treemap's
  value-sized tiles (``{name, value}`` leaves colored categorically via
  ``colorByPoint``, missing values dropped like pie, resolving its own
  ``modules/treemap.js``), sankey's node-link flows (``{from, to, weight}`` links
  over two node columns, rows missing any of the three dropped like pie's slices,
  its node tooltip and its per-link weight labels each pinned to the one place
  highcharts-core doesn't silently drop them, those labels gated on link count,
  resolving its own ``modules/sankey.js``), boxplot's per-category Tukey
  distributions (the one AGGREGATING builder: raw observations grouped by a
  repeating ``x_col`` into positional ``[low, q1, median, q3, high]`` 5-arrays,
  outliers split off into a linked scatter series emitted only when they exist,
  the ``iqr == 0`` degeneracies that the inclusive fence saves, the matplotlib
  whisker clamp, an all-missing group kept as an ``EnforcedNull`` box, and the
  ``fillColor``/``stemColor`` silent drop that leaves its box interior unsettable —
  sharing bubble's and radar's ``highcharts-more``), waterfall's cumulative bridge
  (signed deltas floating at a running total, closed by an APPENDED ``isSum`` bar —
  so it is the one type drawing more marks than the frame has rows, and the one
  whose ``count_marks`` exceeds its drawable row count; the bar colors are semantic
  rather than identity-based, read from ``DEFAULT_COLORS`` by index so a custom
  ``colors`` palette cannot repaint a fall green, and the total carries its own
  per-point color, which takes it OFF that up/down scale — Highcharts would otherwise
  color the sum by its own sign, and "the end level is above zero" is not the claim
  "this step added"; a missing delta keeps its axis slot as an ``EnforcedNull``; the
  in-bar value labels are gated on step count; and it needs TWO dark-mode hooks — the
  bar borders and the connector lines between bars, neither of which is column/bar's
  white-ring case — while sharing that same ``highcharts-more``), sunburst's hierarchy
  of rings (the only type reading the frame as an ADJACENCY LIST — one row per node,
  naming its parent by LABEL — so its marks must be ASSEMBLED before anything can be
  drawn. Node ids are SYNTHESIZED, never the labels: two teams may legitimately both be
  called "Other", and label-as-id would hand Highcharts a duplicate id, which is not a
  silent mismatch but error #31 printed in a red band across the chart — so the twins stay
  two honest sectors, and the label-keyed shape's one real cost is paid only where it is
  genuinely unpayable, on a duplicate label that is USED as a parent. The tree's two kinds
  of fault are kept apart: MISSING DATA is dropped (a dangling parent, with its descendants
  — Highcharts would otherwise silently re-parent an orphan to the root; an unsizable leaf
  value, ``_sizable`` widening ``_plottable`` by one comparison because a NEGATIVE leaf is
  not merely undrawn but excluded from its parent's sum), while a CONTRADICTION RAISES (a
  cycle, an ambiguous parent) — through a message ``_sunburst_tree`` RETURNS rather than
  throws, which is what keeps ``count_marks`` total and the app's KPI row, which runs above
  its guards, from blowing the page up with a traceback. Internal nodes carry NO value, so
  Highcharts' sum is authoritative and a parent's arc always equals what is drawn under it;
  a root sector is APPENDED, making sunburst the second type whose mark count exceeds its row
  count; ring 1 is seeded per POINT from the palette, routing around ``levels[].colorByPoint``,
  which highcharts-core silently drops, and around the series-level ``colorByPoint``, which
  survives but would destroy the hue inheritance; and it needs ONE dark-mode hook, the white
  sector rings that pie, treemap and sankey each dissolve — resolving its own
  ``modules/sunburst.js`` and, unlike bubble/radar/boxplot/waterfall, no ``highcharts-more``),
  the brand-palette
  (``DEFAULT_COLORS`` / ``colors`` override), and the validation guards
  (unsupported type, empty ``y_cols``, the category-x x-in-y rule widened to
  heatmap, boxplot and waterfall, the bubble size-column requirement, sankey's
  required, distinct target column, and sunburst's required, distinct parent column).
- light/dark theming: dark mode paints the chart background (light leaves it
  unset), the chart chrome (axes/text/gridlines, pie labels, and the tooltip)
  flips while the ``DEFAULT_COLORS`` palette stays shared across modes,
  ``build_chart_html`` gives the iframe body a background that tracks the mode,
  and it pins the chart's ``color-scheme`` so Highcharts' own ``light-dark()``
  defaults resolve to the export server's values rather than the viewer's browser.
- a row-less frame (columns, no rows — a header-only CSV) draws an EMPTY chart
  rather than raising, swept over ``SUPPORTED_TYPES`` because the bug was one
  shared line: an empty ``.map()`` mask comes back non-boolean, and a DataFrame
  indexed by one is read as a list of COLUMN NAMES, so every type died with a bare
  ``KeyError``. ``count_marks`` had the same bug in each of its three masks, where
  it surfaces instead as ``int('')`` and as an Arrow ``&`` kernel error — and, for
  the non-label masks, only as a pandas deprecation, so that test promotes warnings
  to errors to see it at all.
- ``sample_data`` unit tests: every built-in dataset is plottable (fresh,
  non-empty, with a numeric column).
- Headless ``AppTest`` interaction tests that drive the full Streamlit app's
  control flow — switching chart type (including bubble, which reveals a
  Size (Z) control, radar, heatmap, treemap, sankey, which reveals a
  Target (to) control, sunburst, which reveals a Parent one, and boxplot and waterfall,
  which reveal a single-select Y
  and no extra control at all — waterfall also asserting that its Steps KPI counts
  the appended total, and sunburst that its Sectors KPI counts the appended root, and
  that a CYCLIC uploaded CSV — the one builder error a user can reach by uploading a
  file, since the interactive path does not catch — warns and stops rather than
  rendering a traceback), title, and series, revealing
  the generated Highcharts config
  behind its toggle, the KPI metric row, the wide-CSV multiselect fallback, and
  the render-mode selector's two modes (interactive iframe / static PNG), plus
  tripping the x-in-y warning and the no-CSV-uploaded info guard — asserting on
  the generated config (incl. the brand palette) and the guard messages.
"""

import ast
import inspect
import math
import re
import sys
import warnings
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from highcharts_core.constants import EnforcedNull

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from highcharts_builder import (  # noqa: E402
    BULLET_TYPES,
    CARTESIAN_TYPES,
    CATEGORY_X_TYPES,
    DEFAULT_COLORS,
    DUMBBELL_TYPES,
    GAUGE_AGGREGATIONS,
    GAUGE_TYPES,
    MAGNITUDE_RANGE_TYPES,
    NODE_LINK_TYPES,
    SUPPORTED_TYPES,
    UNWEIGHTED_NODE_LINK_TYPES,
    VARIWIDE_TYPES,
    _gauge_reading_label,
    _needle_radii,
    _pct,
    build_chart_html,
    build_chart_png,
    build_options,
    count_marks,
    explain_gauge_error,
    explain_xrange_error,
    gauge_dial,
    make_chart,
)


@pytest.fixture
def labeled_frame() -> pd.DataFrame:
    """A label column plus a numeric column — valid input for every chart type.

    The second label column ("target") is there for sankey alone, whose links need a
    node column at each end, and the third ("parent") for sunburst alone, whose rows are
    an adjacency list. Every other type names the columns it reads, so the extras are
    inert (neither is numeric, so neither can perturb a y-column sweep).

    "parent" is a real 2-level tree — "a" is a top-level branch (its blank parent says so)
    and "b"/"c" hang off it — so the sweeps exercise sunburst's internal-node path as well
    as its leaves. Note the consequence for the value sweeps: "a" has children, so its
    value is never read at all (an internal node's arc is the sum of its children's).

    The fourth column ("end") is for xrange alone, whose bars need a coordinate at each end.
    It is the one extra that IS numeric, so — unlike "target"/"parent" — it is not inert:
    it is a second numeric column, and "value" is no longer the only one. Every sweep names
    the columns it reads, so nothing is perturbed, but a new test that reaches for "the
    numeric column" must now say which. Its values sit strictly above "value"'s, so for
    xrange every row is spannable (``value`` is the START and ``end`` the END).
    """
    return pd.DataFrame(
        {
            "label": ["a", "b", "c"],
            "target": ["x", "y", "z"],
            "parent": [None, "a", "a"],
            "value": [1.0, 2.0, 3.0],
            "end": [2.0, 4.0, 6.0],
        }
    )


def _size_for(chart_type: str) -> str | None:
    """The size column the SUPPORTED_TYPES-parametrized tests pass for the bubble
    case: bubble requires one (its marker-size dimension); other types ignore it,
    so it's None. The shared ``labeled_frame``'s "value" doubles as the size (it is not
    the only numeric column any more — "end" is one too — but it is the one every sweep
    plots)."""
    return "value" if chart_type == "bubble" else None


def _target_for(chart_type: str) -> str | None:
    """The target column those same sweeps pass for the node-link cases: sankey,
    dependencywheel, networkgraph and organization all require one (the far end of every
    edge/reporting link, reusing one ``target_col``); other
    types ignore it, so it's None. The
    ``_size_for`` idea, for the other types with a required companion column — the
    sweeps assert invariants that must hold for *every* type (it builds, it carries
    the palette, dark mode paints the background), so a type that needs an extra
    column adapts its input rather than dropping out. Networkgraph and organization are built by the
    sweeps with the shared ``y_cols=["value"]``, which both simply IGNORE (neither has a value
    channel); their own empty-``y_cols`` behaviour is pinned separately
    (``test_networkgraph_builds_with_empty_y_cols`` / ``test_organization_builds_with_empty_y_cols``)."""
    return "target" if chart_type in NODE_LINK_TYPES else None


def _parent_for(chart_type: str) -> str | None:
    """The parent column those same sweeps pass for the sunburst case: sunburst requires
    one (each node's place in the hierarchy); other types ignore it, so it's None. The
    third of the ``_size_for``/``_target_for`` family — see ``_target_for`` for why a type
    with a required companion column adapts its input rather than dropping out of the
    sweeps."""
    return "parent" if chart_type == "sunburst" else None


def _end_for(chart_type: str) -> str | None:
    """The end column those same sweeps pass for the xrange case: xrange requires one (the
    far end of every bar); other types ignore it, so it's None. The fourth of the
    ``_size_for``/``_target_for``/``_parent_for`` family — see ``_target_for``.

    Note what xrange does with the sweeps' ``y_cols=["value"]``: it reads it as the bar's
    START, not as a magnitude. So the pair is ("value", "end"), and the fixtures keep "end"
    strictly above "value" so the bars are drawable."""
    return "end" if chart_type == "xrange" else None


def _high_for(chart_type: str) -> str | None:
    """The high column those same sweeps pass for the MAGNITUDE_RANGE case: columnrange and its
    filled-band mirror arearange each require one (each bar's / band's top); other types ignore it,
    so it's None. The fifth of the ``_size_for``/``_target_for``/``_parent_for``/``_end_for``
    family — see ``_target_for``. Keyed on the family constant so arearange rides every
    ``SUPPORTED_TYPES`` sweep the day it is added, exactly as columnrange does.

    It reuses the fixtures' ``"end"`` column, the one extra that is NUMERIC, exactly as
    ``_end_for`` does — but reading it as a MAGNITUDE (the bar's/band's high), not a coordinate. The
    pair is ("value", "end") as it is for xrange, and for the same reason the fixtures keep
    "end" strictly above "value": here that makes every range a clean ``low < high`` rather than
    an inverted one, so the sweeps exercise the ordinary drawable case."""
    return "end" if chart_type in MAGNITUDE_RANGE_TYPES else None


def _goal_for(chart_type: str) -> str | None:
    """The goal column those same sweeps pass for the bullet case: bullet requires one (each
    bar's target crossbar); other types ignore it, so it's None. The SIXTH of the
    ``_size_for``/``_target_for``/``_parent_for``/``_end_for``/``_high_for`` family — see
    ``_target_for`` for why a type with a required companion column adapts its input rather
    than dropping out of the sweeps.

    It reuses the fixtures' ``"end"`` column, the one extra that is NUMERIC, exactly as
    ``_high_for`` does — but reading it as a GOAL, not as a high. The pair is ("value", "end"),
    and since the fixtures keep "end" strictly above "value", every sweep row is the ordinary
    UNDER-target case (a bar below its crossbar). The beat-plan case, where the crossbar-contrast
    trap actually strikes, is pinned by the dedicated tests and by the sample rather than here."""
    return "end" if chart_type in BULLET_TYPES else None


def _width_for(chart_type: str) -> str | None:
    """The width column those same sweeps pass for the variwide case: variwide requires one (each
    bar's X extent); other types ignore it, so it's None. The SEVENTH of the
    ``_size_for``/``_target_for``/``_parent_for``/``_end_for``/``_high_for``/``_goal_for`` family —
    see ``_target_for`` for why a type with a required companion column adapts its input rather
    than dropping out of the sweeps.

    It reuses the fixtures' ``"end"`` column, the one extra that is NUMERIC, exactly as
    ``_high_for`` and ``_goal_for`` do — but reading it as a WIDTH, which is neither of those
    things (not the far end of the mark, not a reference the mark is read against, but the mark's
    other dimension). The fixtures keep "end" strictly above "value" and, more to the point here,
    POSITIVE: a width is a share of a total, so ``_variwide_point`` requires it to be non-negative
    (``_sizable``, not merely ``_plottable``), and a negative one in a shared fixture would null
    every sweep's slot and quietly make several of them vacuous."""
    return "end" if chart_type in VARIWIDE_TYPES else None


def _after_for(chart_type: str) -> str | None:
    """The after column those same sweeps pass for the dumbbell case: dumbbell requires one (the
    LATER of its two readings); other types ignore it, so it's None. The EIGHTH of the
    ``_size_for``/``_target_for``/``_parent_for``/``_end_for``/``_high_for``/``_goal_for``/
    ``_width_for`` family — see ``_target_for`` for why a type with a required companion column
    adapts its input rather than dropping out of the sweeps.

    It reuses the fixtures' ``"end"`` column, the one extra that is NUMERIC, exactly as
    ``_high_for``, ``_goal_for`` and ``_width_for`` do — but reading it as an AFTER, which is none
    of those three (not the far end of one mark, not a reference the mark is read against, not the
    mark's other dimension, but the same quantity at a later time). The fixtures keep "end"
    strictly above "value", so every sweep row is a clean RISE — the ordinary drawable case. The
    fall, where the before/after hues could have swapped had Highcharts painted ``lowColor`` onto
    the smaller value rather than the first slot, is pinned by the dedicated tests and by the
    sample rather than here."""
    return "end" if chart_type in DUMBBELL_TYPES else None


# Radar remains the ONE "meta" type: Highcharts has no radar series, so it renders as a polar
# *line* chart and its chart.type serializes as "line". Every other supported type's chart.type
# equals its own name — and the gauge FAMILY is why that stayed true. `solidgauge` was never
# given the friendlier name `gauge` that radar's precedent would have licensed, because `gauge`
# in Highcharts is a DIFFERENT chart, a needle on a dial. That name is now SPENT, on exactly the
# type it was being held for, so both gauges are called what Highcharts calls them and this map
# still has one entry.
_HC_TYPE = {"radar": "line"}


def _hc_type(chart_type: str) -> str:
    """The Highcharts ``chart.type`` a supported type renders as: identity for all but
    radar, which is a polar line."""
    return _HC_TYPE.get(chart_type, chart_type)


# --------------------------------------------------------------------------- #
# Every supported type builds
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_supported_type_builds(labeled_frame, chart_type):
    opts = build_options(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    assert opts["chart"]["type"] == _hc_type(chart_type)
    assert opts["series"]  # at least one series/data set was produced


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_supported_type_builds_a_working_highcharts_core_chart(
    labeled_frame, chart_type
):
    # build_options's SUPPORTED_TYPES check only guards against a Python-level
    # typo — it can't catch a chart_type string highcharts-core itself would
    # reject. Drive every type through the real pipeline (make_chart ->
    # Chart.from_options -> to_js_literal), not just the options dict. This is the
    # only test that proves the pie, scatter, and radar branches serialize: they
    # hardcode their chart.type literal (scatter also its zooming block, radar its
    # `line` + polar) rather than using the chart_type variable, so nothing else
    # validates those literals end to end. Radar renders as a polar line, so its
    # serialized type is "line" (see _hc_type), not "radar".
    from highcharts_builder import make_chart

    js = make_chart(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    ).to_js_literal()
    assert js and f"type: '{_hc_type(chart_type)}'" in js


@pytest.fixture
def non_finite_frame() -> pd.DataFrame:
    """``labeled_frame``'s shape, but the numeric column carries an infinity at each end
    and one drawable value. Every type reads x from "label" and y from "value", so the
    one frame exercises all of them (bubble takes "value" as its size too, sankey as its
    weight — see ``_size_for``/``_target_for``/``_parent_for``).

    For sunburst the tree is "a" over "b"/"c", so the frame reaches its branch three ways at
    once: "a" is INTERNAL, so its ``inf`` is never even read (a parent's arc is the sum of its
    children's); "b"'s ``-inf`` fails ``_sizable`` and drops that leaf; and "c" survives. No
    infinity can reach the JS by any of the three routes.

    For xrange "value" is each bar's START, so the two infinities fail ``_spannable`` and drop
    their rows while "c" (9 -> 10) survives and draws. "end" is kept FINITE here on purpose:
    it is the one channel this fixture cannot reach, since an infinite end would drop the only
    surviving row and leave an empty chart that passes the sweep trivially. It is covered
    directly instead — see ``test_xrange_drops_a_non_finite_start_or_end``."""
    return pd.DataFrame(
        {
            "label": ["a", "b", "c"],
            "target": ["x", "y", "z"],
            "parent": [None, "a", "a"],
            "value": [float("inf"), float("-inf"), 9.0],
            "end": [2.0, 4.0, 10.0],
        }
    )


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_no_supported_type_emits_a_non_finite_js_literal(non_finite_frame, chart_type):
    # An infinity is not missing — pd.isna(inf) is False — but it cannot be serialized:
    # to_js_literal renders it as the bare token `inf`, which is not a JavaScript
    # identifier (JS spells it `Infinity`), so the whole Highcharts.chart(...) call dies
    # with a ReferenceError and the iframe renders blank. The static path fares no better:
    # the export server is handed the non-standard JSON literal `Infinity` and answers
    # 400, which the app then misreports as an unreachable server. Both were live bugs in
    # every type before `_plottable`. Only the emitted JS can prove the fix, and this
    # sweeps SUPPORTED_TYPES so a newly added type is covered the day it is added — but only
    # for its VALUE channel (this fixture carries the infinities in the y/weight/size
    # column, always with a safe string x). The LABEL channel has its own sweep
    # (test_missing_or_non_finite_label_drops_the_row_in_every_type), and boxplot's
    # aggregation-overflow path — the one type that can manufacture a non-finite from
    # finite inputs — has its own test, since neither is reachable through this frame.
    from highcharts_builder import make_chart

    js = make_chart(
        non_finite_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    ).to_js_literal()
    assert js
    # `Infinity` is capitalized, so a lowercase "inf" can only be the broken token. None
    # of the column names, titles or type names above contains "inf"/"nan" either.
    for token in ("inf", "nan", "NaN"):
        assert token not in js, f"{chart_type} emitted a non-finite literal: {token}"


# Gauge is EXCLUDED, and vacuously passing here is exactly why it has to be. It has no label
# channel — `x_col` names nothing — so there is no policy for this sweep to test, and with a
# clean value column the assertion below ("no nan/inf token in the JS") would hold whatever
# gauge did with the labels. Worse than untested: it would READ as a pin on a policy gauge
# deliberately does not have, since a row filter over an AGGREGATE does not drop a mark, it
# silently changes a NUMBER. What gauge actually promises is the opposite, and it is pinned
# where it belongs: test_gauge_ignores_x_col_entirely.
@pytest.mark.parametrize(
    "chart_type", [t for t in SUPPORTED_TYPES if t not in GAUGE_TYPES]
)
def test_missing_or_non_finite_label_drops_the_row_in_every_type(chart_type):
    # The counterpart to the value-column sweep above, for the LABEL column (the one that
    # NAMES a mark: a pie slice, an axis category, a sankey node, a boxplot group). A
    # missing or non-finite label names nothing drawable, so its row is dropped in EVERY
    # type — not rendered as a slice/category/node/box labelled the literal "nan"/"inf".
    # This is the value-column missing-data policy extended to the label column, and it is
    # uniform now: before, most types kept the "nan" mark and only sankey and boxplot
    # dropped it. Proven on the emitted JS (a kept NaN/inf label stringifies to the quoted
    # category 'nan'/'inf', which contains the token; the good rows never do).
    from highcharts_builder import make_chart

    # A NaN in a STRING label column (object dtype, so scatter/bubble take the
    # non-numeric-x path) and an inf in a NUMERIC label column (so they take the numeric-x
    # path `_plottable` guards) — both label channels, so no type slips through on either.
    nan_df = pd.DataFrame(
        {
            "label": ["a", float("nan"), "c"],
            "to": ["x", "y", "z"],
            # sunburst's second label column: "a" is a top-level branch and "c" hangs off it,
            # so the undrawable middle row is the only one dropped.
            "parent": [None, "a", "a"],
            "value": [1.0, 2.0, 3.0],
            # xrange's second coordinate column, above "value" so every row is spannable —
            # leaving the LABEL the only reason a row can drop, which is what this sweep tests.
            "end": [2.0, 4.0, 6.0],
        }
    )
    inf_df = pd.DataFrame(
        {
            "label": [1.0, float("inf"), 3.0],
            "to": [9.0, 8.0, 7.0],
            # A NUMERIC parent column, matched against a numeric label column — so this row
            # also exercises `_node_key`: a bare str() would stringify the label 1.0 to "1"
            # (int64-backed) but the parent 1.0 to "1.0", dangle every row, and quietly empty
            # the chart. Here they must meet.
            "parent": [float("nan"), 1.0, 1.0],
            "value": [1.0, 2.0, 3.0],
            "end": [2.0, 4.0, 6.0],
        }
    )
    for df, token in ((nan_df, "nan"), (inf_df, "inf")):
        js = make_chart(
            df,
            chart_type,
            "label",
            ["value"],
            size_col=_size_for(chart_type),
            target_col="to" if chart_type in NODE_LINK_TYPES else None,
            parent_col="parent" if chart_type == "sunburst" else None,
            end_col=_end_for(chart_type),
            high_col=_high_for(chart_type),
            goal_col=_goal_for(chart_type),
            width_col=_width_for(chart_type),
            after_col=_after_for(chart_type),
        ).to_js_literal()
        assert js and token not in js.lower(), f"{chart_type} kept a '{token}' label"


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_row_less_frame_draws_an_empty_chart_in_every_type(chart_type):
    # A frame with columns but NO ROWS is a legitimate input — a CSV with a header and no
    # data rows parses to exactly this — and it should draw an EMPTY chart, not raise.
    #
    # It used to raise, in all of them, from a single line: the shared `_label_ok` filter
    # `df[df[x_col].map(_label_ok)]`. `.map()` infers its result dtype from the values it
    # produced, and with no rows there are none, so it returns an empty *object* Series
    # instead of an empty *boolean* one — and a DataFrame indexed by a non-boolean Series is
    # not masked at all, it is read as a list of COLUMN NAMES. So the frame lost every
    # column and the next line to touch df[x_col] died with a bare `KeyError: 'label'`. The
    # `.astype(bool)` in that filter is what pins the dtype.
    #
    # Swept over SUPPORTED_TYPES because the filter is shared by all of them: one line, one
    # bug, EVERY type — the count is however many there are, which is exactly why this is a
    # sweep and not a list, so a newly added type is covered the day it is added. Both
    # scatter/bubble paths are reached: the object-dtype x below takes the label path (the
    # filtered one), and the numeric-x frame at the end takes the branch that skips it.
    from highcharts_builder import make_chart

    # "target"/"parent" (not "to") — the names `_target_for`/`_parent_for` hand the sankey and
    # sunburst cases, as in `labeled_frame`.
    empty = pd.DataFrame(
        {
            "label": pd.Series([], dtype=object),
            "target": pd.Series([], dtype=object),
            "parent": pd.Series([], dtype=object),
            "value": pd.Series([], dtype=float),
            # xrange's end column. A row-less coordinate column is the one case `_coordinates`
            # must NOT call a contradiction: nothing parses, but nothing is PRESENT either, so
            # it is missing data (an empty chart), not a column of the wrong kind (a raise).
            "end": pd.Series([], dtype=float),
        }
    )
    opts = build_options(
        empty,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    # An empty chart, not a raise. Gauge is the one type whose empty chart is not zero marks:
    # its marks are the selected COLUMNS, not the rows, so a header-only CSV still selects one
    # — and the ring is KEPT, as a null, exactly as an all-missing column is in a populated
    # frame. (Dropping it would renumber and recolour every other ring, and make the KPI count a
    # ring the chart never drew.) So the row-less case is not a special case for gauge at all:
    # it is the ordinary no-data reading, arrived at with no rows rather than with blank ones.
    expected = [EnforcedNull] if chart_type in GAUGE_TYPES else []
    assert opts["series"][0]["data"] == expected
    # And it must still SERIALIZE — an empty series is only useful if Highcharts gets it.
    js = make_chart(
        empty,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    ).to_js_literal()
    assert js and f"type: '{_hc_type(chart_type)}'" in js


@pytest.mark.parametrize(
    "chart_type",
    ["treemap", "sankey", "dependencywheel", "networkgraph", "organization"],
)
def test_count_marks_casts_every_mask_not_just_the_label_one(chart_type):
    # The types that AND their masks together (`label_ok & value_ok`, plus sankey's/
    # networkgraph's/organization's `target_ok` — the two unweighted node-link types AND
    # `label_ok & target_ok` with no value mask, since they carry no weight; organization's
    # second mask reads `not _is_top_level` rather than `_label_ok`, but is cast the same way).
    # On a row-less frame each `.map()` returns a non-boolean Series, and once
    # the label mask alone is cast, `bool & str` still evaluates — so a missing cast on the
    # OTHER masks is invisible to an ordinary assertion. It is not harmless: pandas emits a
    # deprecation saying the operation will RAISE in pandas 4 and that the operand must be
    # cast explicitly. So promote warnings to errors — that is the only thing that can see it.
    #
    # The value/target columns are given a STRING dtype on purpose. A y column is numeric in
    # the app (the picker draws from select_dtypes("number")), and `bool & float64` neither
    # warns nor raises; only a non-numeric one — reachable through the pure builder API this
    # module is — puts the string mask on the right-hand side where the deprecation bites.
    from highcharts_builder import count_marks

    empty = pd.DataFrame(
        {
            "cat": pd.Series([], dtype="str"),
            "to": pd.Series([], dtype="str"),
            "v": pd.Series([], dtype="str"),
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any pandas deprecation here fails the test
        assert count_marks(empty, chart_type, "cat", ["v"], target_col="to") == 0


def test_row_less_frame_with_a_numeric_x_also_draws_an_empty_chart():
    # The other side of the `x_is_label` branch: scatter/bubble with a NUMERIC x skip the
    # label filter entirely (x is a coordinate `_plottable` guards per point), so they reach
    # the row-less frame by a different route and must survive it too.
    numeric = pd.DataFrame(
        {"label": pd.Series([], dtype=float), "value": pd.Series([], dtype=float)}
    )
    for chart_type in ("scatter", "bubble"):
        opts = build_options(
            numeric,
            chart_type,
            "label",
            ["value"],
            size_col="value" if chart_type == "bubble" else None,
        )
        assert opts["series"][0]["data"] == []


@pytest.mark.parametrize(
    "chart_type",
    [
        "heatmap",
        "treemap",
        "funnel",
        "pyramid",
        "sankey",
        "dependencywheel",
        "boxplot",
        "waterfall",
        "sunburst",
        "xrange",
    ],
)
def test_count_marks_matches_the_built_series(chart_type):
    # The app's KPI (heatmap Cells / treemap Tiles / funnel|pyramid Stages / sankey Flows /
    # boxplot Boxes / waterfall Steps / sunburst Sectors) comes
    # from count_marks, which must equal the marks build_options actually draws — the whole
    # reason it lives in the builder, beside the drop rules. Cross-check the two on a frame
    # that exercises every drop: a NaN label (dropped in all six), a NaN value (drops a
    # tile/flow, kept as an EnforcedNull cell/box/bar), an inf value (same), and a NaN target
    # (drops a sankey link). If they ever diverge, the KPI is lying about the chart.
    # Waterfall and sunburst are the two types whose count EXCEEDS their surviving rows — each
    # appends a mark the frame never held (a Total bar, a root sector).
    #
    # Sunburst reads the same frame as a HIERARCHY, and the one column of parents makes it
    # exercise five drops at once: the NaN label drops row 2; "b"'s NaN value drops that LEAF;
    # "a" is thereby left childless, BECOMES a leaf, and is sized by its own 1.0; "d"'s `inf`
    # is harmlessly never read, because "e" keeps it INTERNAL (a parent's arc is the sum of its
    # children's); and the root is appended. 3 nodes + root = 4.
    from highcharts_builder import build_options, count_marks

    # Xrange reads the same frame as INTERVALS, "v" being each bar's START rather than a
    # magnitude, and it exercises three drops at once: the NaN label drops row 3, "b"'s NaN
    # start drops row 2, and "d"'s `inf` start drops row 4 — leaving "a" (1 -> 2) and "e"
    # (5 -> 6). Unlike waterfall and sunburst it appends nothing, so its count is exactly its
    # surviving rows: 2.
    nan, inf = float("nan"), float("inf")
    df = pd.DataFrame(
        {
            "cat": ["a", "b", nan, "d", "e"],
            "to": ["p", "q", "r", "s", nan],
            "parent": [nan, "a", nan, nan, "d"],
            "v": [1.0, nan, 3.0, inf, 5.0],
            "end": [2.0, 4.0, 6.0, 8.0, 6.0],
        }
    )
    built = build_options(
        df,
        chart_type,
        "cat",
        ["v"],
        target_col="to",
        parent_col="parent",
        end_col="end",
    )
    drawn = len(built["series"][0]["data"])  # the cells/tiles/links/boxes/bars/sectors
    assert (
        count_marks(
            df,
            chart_type,
            "cat",
            ["v"],
            target_col="to",
            parent_col="parent",
            end_col="end",
        )
        == drawn
    )
    # The two must also agree on a ROW-LESS frame (a header-only CSV), where the chart is
    # empty — so the KPI reads 0 rather than counting marks nobody drew. This is the case
    # that used to make build_options raise outright (see the row-less sweep above), so the
    # KPI half was never even reachable to be wrong.
    empty = df.iloc[:0]
    assert (
        build_options(
            empty,
            chart_type,
            "cat",
            ["v"],
            target_col="to",
            parent_col="parent",
            end_col="end",
        )["series"][0]["data"]
        == []
    )
    assert (
        count_marks(
            empty,
            chart_type,
            "cat",
            ["v"],
            target_col="to",
            parent_col="parent",
            end_col="end",
        )
        == 0
    )
    # And the expected value, spelled out, so the cross-check can't pass on a shared bug:
    assert (
        drawn
        == {
            "heatmap": 4,
            "treemap": 2,
            # Funnel/pyramid drop the NaN label (row 3) and the NaN/inf value (rows 2, 4)
            # like treemap, leaving "a" (1.0) and "e" (5.0): 2 stages, no appended mark.
            "funnel": 2,
            "pyramid": 2,
            "sankey": 1,
            # Dependencywheel shares sankey's rule and build exactly — same 4 rows dropped
            # (the NaN weight, NaN source, inf weight and NaN target), leaving one link.
            "dependencywheel": 1,
            "boxplot": 4,
            "waterfall": 5,
            "sunburst": 4,
            "xrange": 2,
        }[chart_type]
    )


def test_num_maps_missing_and_non_finite_to_enforced_null():
    from highcharts_builder import _num, _plottable

    assert _num(1.5) == 1.5
    assert _num(float("nan")) is EnforcedNull
    assert _num(float("inf")) is EnforcedNull  # not missing, but not drawable
    assert _num(float("-inf")) is EnforcedNull
    # The drop-path predicate agrees with the keep-the-slot one on what is drawable.
    assert _plottable(1.5)
    assert not _plottable(float("nan"))
    assert not _plottable(float("inf"))
    assert not _plottable(float("-inf"))


@pytest.mark.parametrize("chart_type", CATEGORY_X_TYPES)
def test_category_x_non_finite_becomes_enforced_null(chart_type):
    # The keep-the-slot family treats an infinity exactly as it treats a NaN: a gap in the
    # line, not a dropped point — so the categories stay aligned with the data.
    df = pd.DataFrame({"x": ["a", "b", "c"], "y": [1.0, float("inf"), 3.0]})
    data = build_options(df, chart_type, "x", ["y"])["series"][0]["data"]
    assert data == [1.0, EnforcedNull, 3.0]


def test_heatmap_non_finite_cell_becomes_enforced_null():
    df = pd.DataFrame({"day": ["Mon", "Tue"], "AM": [1.0, float("-inf")]})
    data = build_options(df, "heatmap", "day", ["AM"])["series"][0]["data"]
    assert len(data) == 2  # the grid never collapses
    assert data[1][2] is EnforcedNull


@pytest.mark.parametrize("chart_type", ["pie", "treemap", "funnel", "pyramid"])
def test_single_value_types_drop_a_non_finite_row(chart_type):
    # The drop-the-row family drops an infinity exactly as it drops a NaN: a slice, tile or
    # funnel stage can no more be sized by infinity than by nothing.
    df = pd.DataFrame({"n": ["a", "b", "c"], "v": [1.0, float("inf"), 3.0]})
    data = build_options(df, chart_type, "n", ["v"])["series"][0]["data"]
    assert [point["name"] for point in data] == ["a", "c"]


def test_scatter_and_bubble_drop_non_finite_points():
    inf = float("inf")
    xy = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [10.0, inf, 30.0]})
    assert build_options(xy, "scatter", "x", ["y"])["series"][0]["data"] == [
        [1.0, 10.0],
        [3.0, 30.0],
    ]
    # An infinite x drops the point too, not just an infinite y.
    xinf = pd.DataFrame({"x": [1.0, inf, 3.0], "y": [10.0, 20.0, 30.0]})
    assert build_options(xinf, "scatter", "x", ["y"])["series"][0]["data"] == [
        [1.0, 10.0],
        [3.0, 30.0],
    ]
    # And so does an infinite SIZE, which would otherwise ask for a bubble of infinite area.
    zinf = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0], "s": [5.0, -inf]})
    assert build_options(zinf, "bubble", "x", ["y"], size_col="s")["series"][0][
        "data"
    ] == [[1.0, 3.0, 5.0]]


def test_sankey_drops_a_non_finite_weight_and_a_non_finite_node_label():
    inf = float("inf")
    df = pd.DataFrame({"s": ["a", "b"], "t": ["c", "d"], "w": [inf, 5.0]})
    assert _links(build_options(df, "sankey", "s", ["w"], target_col="t")) == [
        {"from": "b", "to": "d", "weight": 5.0}
    ]
    # A node column is a LABEL, and a non-finite label names nothing drawable: it would
    # stringify to a node literally named "inf". Under the uniform label policy (`_label_ok`)
    # that row is dropped in EITHER end — the source (filtered up front) or the target
    # (checked in the sankey branch) — exactly as every other type now drops a "nan"/"inf"
    # label, rather than the old sankey-only exception that kept the "inf" node.
    src_inf = pd.DataFrame({"s": [inf, "a"], "t": ["d", "e"], "w": [5.0, 6.0]})
    assert _links(build_options(src_inf, "sankey", "s", ["w"], target_col="t")) == [
        {"from": "a", "to": "e", "weight": 6.0}
    ]
    dst_inf = pd.DataFrame({"s": ["a", "b"], "t": [inf, "e"], "w": [5.0, 6.0]})
    assert _links(build_options(dst_inf, "sankey", "s", ["w"], target_col="t")) == [
        {"from": "b", "to": "e", "weight": 6.0}
    ]


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_default_title_per_type(labeled_frame, chart_type):
    opts = build_options(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    assert opts["title"]["text"] == f"{chart_type.title()} chart"


def test_explicit_title_overrides_default(labeled_frame):
    opts = build_options(labeled_frame, "line", "label", ["value"], title="Custom")
    assert opts["title"]["text"] == "Custom"


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_default_palette_applied_per_type(labeled_frame, chart_type):
    # Every chart type carries the brand palette so all render modes share a look.
    opts = build_options(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    assert opts["colors"] == list(DEFAULT_COLORS)


def test_colors_override(labeled_frame):
    opts = build_options(
        labeled_frame, "line", "label", ["value"], colors=["#000000", "#ffffff"]
    )
    assert opts["colors"] == ["#000000", "#ffffff"]


# --------------------------------------------------------------------------- #
# Dark theme: only the chart "chrome" flips; the series palette is shared across
# modes, and light mode is a byte-for-byte no-op. The shell now locks to dark (a lone
# [theme] in config.toml), so these two modes are no longer a viewer-facing toggle —
# but `dark` is still a builder INPUT, both values are still built, and the light path
# is what the AppTests exercise, so the pairing below is live in every direction.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_dark_mode_sets_chart_background(labeled_frame, chart_type):
    # Dark mode paints the chart background so it matches the dark app shell
    # (kept in sync with .streamlit/config.toml's backgroundColor by
    # test_theme_colors_stay_in_sync_with_config).
    opts = build_options(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    assert opts["chart"]["backgroundColor"] == "#0f172a"


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_dark_mode_keeps_the_shared_palette(labeled_frame, chart_type):
    opts = build_options(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    assert opts["colors"] == list(DEFAULT_COLORS)


def test_dark_mode_themes_cartesian_axes_text_and_legend():
    # Two series so the legend is enabled and its recoloring is meaningful.
    df = pd.DataFrame({"x": ["a", "b"], "y": [1, 2], "z": [3, 4]})
    opts = build_options(df, "line", "x", ["y", "z"])
    assert opts["title"]["style"]["color"] == "#f1f5f9"
    # Axis labels + title, and the line/tick/gridline colors, all flip.
    assert opts["xAxis"]["labels"]["style"]["color"] == "#94a3b8"
    assert opts["xAxis"]["title"]["style"]["color"] == "#94a3b8"
    assert opts["xAxis"]["lineColor"] == "#475569"
    assert opts["xAxis"]["tickColor"] == "#475569"
    assert opts["yAxis"]["gridLineColor"] == "#334155"
    # Legend text recolors too (dark-on-dark would be unreadable otherwise).
    assert opts["legend"]["itemStyle"]["color"] == "#f1f5f9"
    assert opts["legend"]["itemHoverStyle"]["color"] == "#94a3b8"


@pytest.mark.parametrize("chart_type", ["column", "bar"])
def test_dark_mode_matches_column_bar_borders_to_the_background(chart_type):
    # column/bar draw a 1px border per bar that defaults to the light background
    # variable; the color-scheme pin keeps it white even in dark mode, ringing every
    # bar. Match it to the dark background so the separators vanish as they do in light
    # mode — the pie/treemap/sankey slice-gap rule, which these two were missing. The
    # cartesian branch emits no plotOptions, so the hook must create it.
    df = pd.DataFrame({"x": ["a", "b"], "y": [1, 2]})
    opts = build_options(df, chart_type, "x", ["y"])
    assert opts["plotOptions"][chart_type]["borderColor"] == "#0f172a"
    # The line family draws no such border, so it stays untouched (no dead plotOptions).
    # This is the assertion that keeps the hook TARGETED now that there is no light mode to
    # contrast it against: it fires only for the types that draw a border, not for every type.
    assert "plotOptions" not in build_options(df, "line", "x", ["y"])


def test_dark_mode_themes_pie_labels_and_skips_axes():
    df = pd.DataFrame({"name": ["A", "B"], "v": [1.0, 2.0]})
    opts = build_options(df, "pie", "name", ["v"])
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["plotOptions"]["pie"]["dataLabels"]["color"] == "#f1f5f9"
    # Pie has no axes, so the axis-theming loop must simply skip it (not crash).
    assert "xAxis" not in opts


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_dark_mode_themes_the_tooltip(labeled_frame, chart_type):
    # The tooltip is lazily rendered by Highcharts and defaults to a light box, so
    # dark mode must theme it explicitly or it floats light-on-dark on hover.
    opts = build_options(
        labeled_frame,
        chart_type,
        "label",
        ["value"],
        size_col=_size_for(chart_type),
        target_col=_target_for(chart_type),
        parent_col=_parent_for(chart_type),
        end_col=_end_for(chart_type),
        high_col=_high_for(chart_type),
        goal_col=_goal_for(chart_type),
        width_col=_width_for(chart_type),
        after_col=_after_for(chart_type),
    )
    assert opts["tooltip"]["backgroundColor"] == "#0f172a"
    assert opts["tooltip"]["borderColor"] == "#475569"
    assert opts["tooltip"]["style"]["color"] == "#f1f5f9"


def test_dark_mode_tooltip_merge_preserves_pie_point_format():
    # Theming MERGES rather than clobbers: the pie path's custom pointFormat lives.
    opts = build_options(
        pd.DataFrame({"name": ["A", "B"], "v": [1.0, 2.0]}),
        "pie",
        "name",
        ["v"],
    )
    assert opts["tooltip"]["backgroundColor"] == "#0f172a"
    assert "point.percentage" in opts["tooltip"]["pointFormat"]


def test_build_chart_html_body_background_matches_the_chart():
    # The iframe body is painted to match the chart background, so no white flash shows at
    # the edges or during load. One value now, not two: the builder has no light mode, so
    # the assertion is that the body tracks _DARK_CHROME["bg"] rather than that it tracks a
    # flag. The white it used to paint would now be a seam around every chart.
    from highcharts_builder import _DARK_CHROME

    df = pd.DataFrame({"x": ["a", "b"], "y": [1, 2]})
    html = build_chart_html(df, "line", "x", ["y"])
    assert f"background:{_DARK_CHROME['bg']}" in html
    assert "background:#ffffff" not in html


@pytest.mark.parametrize("chart_type", ["line", "boxplot"])
def test_build_chart_html_pins_the_chart_color_scheme(chart_type):
    # Highcharts >= 13 defines its defaults as `light-dark()` CSS variables, so every
    # color we don't set explicitly would resolve against the VIEWER'S BROWSER rather
    # than our `dark` flag. Two real failures followed: a light-mode chart painted itself
    # dark (#141414 background, pale text) on a dark-OS browser, and a boxplot's box fill
    # — the one mark color highcharts-core cannot express — differed between the iframe
    # and the export-server PNG. Pinning the chart root to `only light` makes the iframe
    # resolve those defaults exactly as the export server does, in BOTH modes, leaving
    # `_themed` the single source of truth for dark mode.
    #
    # The selector must be `.highcharts-root` (the <svg>), not `html`: Highcharts declares
    # `color-scheme: light dark` on `.highcharts-container` (between `html` and the <svg>),
    # and since `color-scheme` inherits, that shadows an `html` rule for the SVG subtree —
    # so the pin has to sit at or below the container to win.
    df = pd.DataFrame({"g": ["a", "a", "b", "b"], "v": [1.0, 2.0, 3.0, 4.0]})
    html = build_chart_html(df, chart_type, "g", ["v"])
    assert ".highcharts-root{color-scheme:only light}" in html
    # `only light` even though the chart IS dark, and that is not a contradiction: this pins
    # how Highcharts' own `light-dark()` DEFAULTS resolve, so that the iframe resolves them
    # exactly as the export server does. Our dark chrome is expressed in the options, never
    # here — which is why removing light mode did not make this pin removable.
    assert "color-scheme:only dark" not in html


def _relative_luminance(hex_color):
    """WCAG 2.x relative luminance of a #rrggbb string."""
    raw = hex_color.lstrip("#")
    channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(a, b):
    """WCAG contrast ratio between two #rrggbb strings, 1.0 (identical) to 21.0."""
    la, lb = _relative_luminance(a), _relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_no_series_colour_collides_with_the_chart_chrome():
    """No palette entry may BE a chrome colour, whoever chose the palette.

    The guard that was missing. `_SUNBURST_ROOT_COLOR` had one — its whole definition is
    "outside the palette" — but the chrome had none, and pointing DEFAULT_COLORS at a theme
    is exactly the edit that can walk a chrome value into the categorical scale without any
    single assertion noticing. It did: the upstream financial-dashboard template sets
    `grayColor` and `chartCategoricalColors[6]` to the same #94a3b8, and `_DARK_CHROME`
    copies `grayColor` for axis labels, legend hover and axis titles — so a 7-series dark
    chart drew its 7th series in precisely the axis-label colour, at 1.00:1.

    Stated as identity rather than as a contrast floor on purpose. A series and a gridline
    MAY legitimately sit close (both are chosen from one restrained palette, and a low ratio
    between a mark and a hairline is a design call); being the SAME string is never a design
    call, it is two roles that have stopped being distinguishable. A ratio floor here would
    either be so low it caught nothing or would start failing on defensible themes.
    """
    from highcharts_builder import _DARK_CHROME

    for role, colour in _DARK_CHROME.items():
        assert colour not in DEFAULT_COLORS, (
            f"_DARK_CHROME[{role!r}] == {colour} is also a series hue "
            f"(index {list(DEFAULT_COLORS).index(colour) if colour in DEFAULT_COLORS else '?'})"
        )
    # The off-palette marks are covered by their own tests; assert here only that they are
    # likewise not chrome, which no other test says.
    from highcharts_builder import _SUNBURST_ROOT_COLOR

    assert _SUNBURST_ROOT_COLOR not in _DARK_CHROME.values()


def _config_theme():
    """The `[theme]` table of .streamlit/config.toml, hex values case-normalized.

    Read rather than imported: the builder is Streamlit-free by design, so it cannot
    resolve the theme at runtime and has to restate it. Normalizing case means a
    re-pasted upstream template (which ships uppercase hex) still compares equal.
    """
    import tomllib

    def norm(value):
        # Hex strings anywhere in the tree, including inside [theme.sidebar] — recursing into
        # dicts as well as lists is what makes the docstring's promise true for the WHOLE
        # table rather than only its top level. Ints (headingFontWeights), font URLs and
        # everything else pass through untouched.
        if isinstance(value, dict):
            return {k: norm(v) for k, v in value.items()}
        if isinstance(value, list):
            return [norm(v) for v in value]
        if isinstance(value, str) and value.startswith("#"):
            return value.lower()
        return value

    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())["theme"]
    return {k: norm(v) for k, v in theme.items()}


def test_app_theme_is_a_single_mode_with_no_light_dark_toggle():
    # A [theme] carrying BOTH a [theme.light] and a [theme.dark] is what unlocks the
    # light/dark toggle in Streamlit's settings menu; a lone [theme] locks the app to one
    # mode. This app is deliberately locked to DARK, and that decision has to have a second
    # home or it can be undone by re-adding a subtable that nothing objects to.
    #
    # It is not cosmetic, and the reason INVERTED when the `dark=` flag was removed. The
    # app no longer reads the theme at all: `_themed` paints slate unconditionally because
    # a lone [theme] guarantees the dark shell. The chart therefore does not FOLLOW the
    # shell, it ASSUMES it — so re-adding a subtable would put a dark chart on a light one
    # with nothing at runtime objecting. This assertion is the only thing that would.
    theme = _config_theme()
    assert theme["base"] == "dark"
    assert "light" not in theme and "dark" not in theme, (
        "re-adding [theme.light]/[theme.dark] restores the toggle this app opted out of"
    )


def test_theme_colors_stay_in_sync_with_config():
    # The chart palette and chrome DUPLICATE config.toml theme values, and must: the charts
    # render in an iframe / server-side PNG that no theme CSS reaches, and Streamlit applies
    # its own chartCategoricalColors only to its own Vega/Plotly charts — of which this app
    # has none. So the theme is restated in highcharts_builder and guarded mechanically
    # here, rather than by cross-referencing comments on both sides.
    from highcharts_builder import _DARK_CHROME, _HEATMAP_GRADIENT

    theme = _config_theme()
    # Fail with the reason, not a KeyError. Moving these colours down into [theme.light] /
    # [theme.dark] is the single most likely future edit here — it is literally what this
    # file held before the theme change — and every assertion below would then die on a bare
    # `KeyError: 'backgroundColor'`, which describes neither the cause nor the fix.
    required = (
        "backgroundColor",
        "textColor",
        "grayColor",
        "borderColor",
        "primaryColor",
        "chartCategoricalColors",
        "chartSequentialColors",
    )
    missing = [k for k in required if k not in theme]
    assert not missing, (
        f"[theme] is missing {missing}. If these moved into [theme.light]/[theme.dark], the "
        f"app is no longer single-mode — see "
        f"test_app_theme_is_a_single_mode_with_no_light_dark_toggle — and both this test and "
        f"streamlit_app.py's `dark` derivation need revisiting together."
    )

    # The series palette IS the theme's categorical scale — the whole list, in order.
    # Order, not just membership: _WATERFALL_UP_COLOR, _WATERFALL_DOWN_COLOR,
    # _WATERFALL_SUM_COLOR and _BOXPLOT_OUTLIER_COLOR index into it, so a reshuffle that
    # kept the same eight hues would repaint "a rise" and "a loss" while staying green.
    assert list(DEFAULT_COLORS) == theme["chartCategoricalColors"]
    # A separate claim from the line above, and it survives a reordering of that list:
    # the brand primary leads the palette, which is what makes DEFAULT_COLORS[0] the
    # right anchor for the heatmap's light ramp and for a waterfall's closing total.
    assert DEFAULT_COLORS[0] == theme["primaryColor"]

    # Four of the five chrome slots are theme values under different names. ("axis" is
    # the builder's own — a Streamlit theme has no counterpart for tick lines.)
    assert _DARK_CHROME["bg"] == theme["backgroundColor"]
    assert _DARK_CHROME["text"] == theme["textColor"]
    assert _DARK_CHROME["muted"] == theme["grayColor"]
    assert _DARK_CHROME["grid"] == theme["borderColor"]

    # The dark heatmap ramp is drawn from the theme's SEQUENTIAL scale. Which two stops is
    # a legibility judgment settled by rendering, so pin the rule (both are on that scale)
    # rather than the indices, which would only restate the constant.
    sequential = theme["chartSequentialColors"]
    # The two NAMED keys, not .values(): the builder's own note says _themed swaps that dict
    # "as one unit ... so the two can't drift if a key is ever added", so a `stops` list or a
    # `dataClasses` entry is planned for — and would make a .values() subset check fail
    # reporting a colour-scale problem that does not exist.
    endpoints = {_HEATMAP_GRADIENT["minColor"], _HEATMAP_GRADIENT["maxColor"]}
    assert endpoints <= set(sequential)
    # ...and that it IS a ramp: low end nearer the background than the high end. Reversed,
    # every heatmap would read inverted while every assertion above still passed.
    assert sequential.index(_HEATMAP_GRADIENT["minColor"]) < sequential.index(
        _HEATMAP_GRADIENT["maxColor"]
    )


# --------------------------------------------------------------------------- #
# Cartesian: line / spline / area / areaspline / column / bar
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chart_type", CARTESIAN_TYPES)
def test_cartesian_categories_and_series(chart_type):
    df = pd.DataFrame({"x": ["a", "b", "c"], "y": [1, 2, 3]})
    opts = build_options(df, chart_type, "x", ["y"])
    assert opts["chart"]["type"] == chart_type
    assert opts["xAxis"]["categories"] == ["a", "b", "c"]
    assert opts["xAxis"]["title"]["text"] == "x"
    assert opts["series"][0]["name"] == "y"
    assert opts["series"][0]["data"] == [1.0, 2.0, 3.0]


@pytest.mark.parametrize("chart_type", CATEGORY_X_TYPES)
def test_category_x_missing_value_becomes_enforced_null(chart_type):
    # The category-x family (cartesian + radar) shares one series build, so a NaN
    # is an EnforcedNull gap (a break in the line/polygon), not a dropped point —
    # unlike pie/scatter/bubble, which drop missing rows entirely.
    df = pd.DataFrame({"x": ["a", "b", "c"], "y": [1.0, float("nan"), 3.0]})
    data = build_options(df, chart_type, "x", ["y"])["series"][0]["data"]
    assert data[0] == 1.0
    assert data[1] is EnforcedNull  # missing point, not Python None
    assert data[2] == 3.0


@pytest.mark.parametrize("chart_type", CATEGORY_X_TYPES)
def test_category_x_numeric_x_becomes_string_categories(chart_type):
    # A numeric x column is coerced to string category *labels* (Highcharts
    # categories are labels, not values) — shared by cartesian and radar, so a
    # numeric CSV x-column plots as discrete categories, not along a value axis.
    # Pins the str() coercion in the category-x branch (a no-op on the string-x
    # data every other categories assertion here feeds).
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    opts = build_options(df, chart_type, "x", ["y"])
    assert opts["xAxis"]["categories"] == ["1", "2", "3"]


@pytest.mark.parametrize(
    ("y_cols", "legend_enabled"),
    [(["y"], False), (["y", "z"], True)],
)
def test_legend_enabled_only_with_multiple_series(y_cols, legend_enabled):
    df = pd.DataFrame({"x": ["a", "b"], "y": [1, 2], "z": [3, 4]})
    opts = build_options(df, "line", "x", y_cols)
    assert opts["legend"]["enabled"] is legend_enabled
    assert len(opts["series"]) == len(y_cols)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_rejects_unsupported_type():
    df = pd.DataFrame({"x": [1], "y": [1]})
    with pytest.raises(ValueError):
        build_options(df, "bogus", "x", ["y"])


@pytest.mark.parametrize(
    "chart_type", [t for t in SUPPORTED_TYPES if t not in UNWEIGHTED_NODE_LINK_TYPES]
)
def test_rejects_empty_y_cols(chart_type):
    # Every type needs at least one y column — EXCEPT the two UNWEIGHTED node-link types
    # (networkgraph and organization), whose marks are edges/reporting lines sized by nothing. They
    # are excluded here and pinned the other way by `test_networkgraph_builds_with_empty_y_cols` /
    # `test_organization_builds_with_empty_y_cols`: the exclusion is the mirror of the gauge
    # family's exclusion from the label sweep — a positive assertion of the missing channel, not an
    # oversight. (Excluding them here also matters because organization would otherwise pass this
    # test for the WRONG reason — the missing target_col raises before empty y_cols is even reached.)
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    with pytest.raises(ValueError):
        build_options(df, chart_type, "x", [])


@pytest.mark.parametrize("chart_type", CATEGORY_X_TYPES)
def test_category_x_rejects_x_in_y(chart_type):
    # The category-x family (cartesian + radar, i.e. CATEGORY_X_TYPES) treats
    # x_col as the category/angular axis, so it can't double as a y value series.
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    with pytest.raises(ValueError):
        build_options(df, chart_type, "y", ["y"])


def test_scatter_allows_x_in_y():
    # The x-in-y guard is category-x-only (cartesian + radar); scatter happily
    # pairs a column with itself (a diagonal of points).
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    opts = build_options(df, "scatter", "a", ["a"])
    assert opts["chart"]["type"] == "scatter"
    assert opts["series"][0]["data"] == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]


# --------------------------------------------------------------------------- #
# Pie
# --------------------------------------------------------------------------- #
def test_pie_builds_slices_and_skips_missing():
    df = pd.DataFrame({"name": ["A", "B", "C"], "v": [10.0, float("nan"), 30.0]})
    opts = build_options(df, "pie", "name", ["v"])
    assert opts["chart"]["type"] == "pie"
    assert opts["series"][0]["name"] == "v"
    # The NaN-valued slice (B) is dropped, not rendered as a null point.
    assert opts["series"][0]["data"] == [
        {"name": "A", "y": 10.0},
        {"name": "C", "y": 30.0},
    ]


def test_pie_uses_only_first_y_col():
    df = pd.DataFrame({"name": ["A", "B"], "v": [1.0, 2.0], "v2": [9.0, 9.0]})
    opts = build_options(df, "pie", "name", ["v", "v2"])
    assert opts["series"][0]["name"] == "v"
    assert [pt["y"] for pt in opts["series"][0]["data"]] == [1.0, 2.0]


# --------------------------------------------------------------------------- #
# Scatter
# --------------------------------------------------------------------------- #
def test_scatter_numeric_x_makes_xy_pairs_and_drops_missing():
    df = pd.DataFrame({"h": [1.0, 2.0, 3.0], "w": [10.0, float("nan"), 30.0]})
    opts = build_options(df, "scatter", "h", ["w"])
    assert opts["chart"]["type"] == "scatter"
    # Numeric x: points are [x, y] pairs; the row with a NaN y is dropped.
    assert opts["series"][0]["data"] == [[1.0, 10.0], [3.0, 30.0]]
    # No category axis for a numeric x.
    assert "categories" not in opts["xAxis"]


def test_scatter_non_numeric_x_uses_positions_and_categories():
    df = pd.DataFrame({"label": ["p", "q", "r"], "w": [10.0, float("nan"), 30.0]})
    opts = build_options(df, "scatter", "label", ["w"])
    # Non-numeric x: points use row position as x; the dropped point (q) leaves
    # a gap in positions (0, 2) rather than renumbering the rest.
    assert opts["series"][0]["data"] == [[0, 10.0], [2, 30.0]]
    # Every x value still labels the axis — including q, whose point was dropped.
    assert opts["xAxis"]["categories"] == ["p", "q", "r"]


def test_scatter_multiple_y_cols_make_one_series_each_with_legend():
    # The app reaches scatter with a multiselect, so verify the multi-y shape:
    # one [x, y]-pair series per y column, and the legend on once there's >1.
    df = pd.DataFrame(
        {"h": [1.0, 2.0, 3.0], "w": [10.0, 20.0, 30.0], "z": [100.0, 200.0, 300.0]}
    )
    opts = build_options(df, "scatter", "h", ["w", "z"])
    assert [s["name"] for s in opts["series"]] == ["w", "z"]
    assert opts["series"][0]["data"] == [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]]
    assert opts["series"][1]["data"] == [[1.0, 100.0], [2.0, 200.0], [3.0, 300.0]]
    assert opts["legend"]["enabled"] is True


# --------------------------------------------------------------------------- #
# Bubble (scatter + a size dimension)
# --------------------------------------------------------------------------- #
def test_bubble_numeric_x_makes_xyz_triples_and_drops_missing():
    df = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0],
            "y": [10.0, 20.0, 30.0],
            "size": [5.0, float("nan"), 15.0],
        }
    )
    opts = build_options(df, "bubble", "x", ["y"], size_col="size")
    assert opts["chart"]["type"] == "bubble"
    # Numeric x: points are [x, y, z] triples; the row with a NaN size is dropped.
    assert opts["series"][0]["data"] == [[1.0, 10.0, 5.0], [3.0, 30.0, 15.0]]
    # No category axis for a numeric x (same rule as scatter).
    assert "categories" not in opts["xAxis"]


def test_bubble_non_numeric_x_uses_positions_and_categories():
    df = pd.DataFrame(
        {
            "label": ["p", "q", "r"],
            "y": [10.0, 20.0, 30.0],
            "size": [5.0, float("nan"), 15.0],
        }
    )
    opts = build_options(df, "bubble", "label", ["y"], size_col="size")
    # Non-numeric x: points use row position as x; the NaN-size row (q) is dropped,
    # leaving a gap in positions (0, 2) rather than renumbering the rest.
    assert opts["series"][0]["data"] == [[0, 10.0, 5.0], [2, 30.0, 15.0]]
    # Every x value still labels the axis — including q, whose point was dropped.
    assert opts["xAxis"]["categories"] == ["p", "q", "r"]


def test_bubble_multiple_y_cols_share_the_size_column():
    # Like scatter, each y column is its own series; every series carries the one
    # size column as its z, and the legend turns on once there's more than one.
    df = pd.DataFrame(
        {"x": [1.0, 2.0], "a": [10.0, 20.0], "b": [100.0, 200.0], "size": [3.0, 4.0]}
    )
    opts = build_options(df, "bubble", "x", ["a", "b"], size_col="size")
    assert [s["name"] for s in opts["series"]] == ["a", "b"]
    assert opts["series"][0]["data"] == [[1.0, 10.0, 3.0], [2.0, 20.0, 4.0]]
    assert opts["series"][1]["data"] == [[1.0, 100.0, 3.0], [2.0, 200.0, 4.0]]
    assert opts["legend"]["enabled"] is True


def test_bubble_requires_a_size_column():
    # Bubble minus its size dimension is just a scatter, so the size column is
    # mandatory — omitting it is a ValueError, not a silent 2-D fallback.
    df = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    with pytest.raises(ValueError):
        build_options(df, "bubble", "x", ["y"])  # no size_col


def test_bubble_serializes_and_pulls_in_the_more_module():
    # End to end: the [x, y, z] shape must serialize AND resolve highcharts-more,
    # the module bubble lives in — a plain scatter/core template renders blank
    # because the browser never loads that module.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0], "size": [5.0, 6.0]})
    chart = make_chart(df, "bubble", "x", ["y"], size_col="size")
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'bubble'" in js
    assert "highcharts-more" in chart.get_script_tags(as_str=True)


def test_bubble_tooltip_names_the_size_column_and_survives_dark_merge():
    # The bubble tooltip names all three dimensions (the default shows a bare
    # x/y/z); the size column in particular is labelled by name.
    df = pd.DataFrame({"gdp": [1.0, 2.0], "life": [3.0, 4.0], "population": [5.0, 6.0]})
    light = build_options(df, "bubble", "gdp", ["life"], size_col="population")
    fmt = light["tooltip"]["pointFormat"]
    assert "population" in fmt and "{point.z}" in fmt  # size named + wired
    assert "gdp" in fmt and "{point.x}" in fmt  # numeric x -> point.x
    # Dark mode merges chrome onto the tooltip without dropping the pointFormat
    # (the same merge the pie path relies on).
    dark = build_options(df, "bubble", "gdp", ["life"], size_col="population")
    assert dark["tooltip"]["backgroundColor"] == "#0f172a"
    assert "population" in dark["tooltip"]["pointFormat"]


def test_bubble_tooltip_uses_category_for_non_numeric_x():
    # With a non-numeric x the point's x is a row index, so the tooltip references
    # the category label instead of the bare position.
    df = pd.DataFrame({"country": ["A", "B"], "life": [3.0, 4.0], "pop": [5.0, 6.0]})
    opts = build_options(df, "bubble", "country", ["life"], size_col="pop")
    fmt = opts["tooltip"]["pointFormat"]
    assert "{point.category}" in fmt and "{point.x}" not in fmt


def test_bubble_tooltip_sanitizes_user_column_names():
    # Column names are user/CSV-controlled and land in a Highcharts format string:
    # braces would be parsed as (empty) value tokens and HTML would inject, so the
    # interpolated x/size names are brace-stripped and HTML-escaped.
    df = pd.DataFrame({"w {kg}": [1.0], "y": [2.0], "<b>pop</b>": [3.0]})
    fmt = build_options(df, "bubble", "w {kg}", ["y"], size_col="<b>pop</b>")[
        "tooltip"
    ]["pointFormat"]
    # Braces stripped from the label, so Highcharts won't tokenize `{kg}` away.
    assert "{kg}" not in fmt
    assert "w kg: " in fmt
    # HTML in the size column name is escaped, not emitted as live markup.
    assert "<b>pop</b>" not in fmt
    assert "&lt;b&gt;pop&lt;/b&gt;" in fmt
    # The genuine Highcharts tokens are untouched.
    assert "{point.z}" in fmt


# --------------------------------------------------------------------------- #
# Radar (a polar line chart over the categories)
# --------------------------------------------------------------------------- #
def test_radar_builds_polar_line_over_categories():
    # Radar shares the cartesian category-x shape but renders on polar axes: the
    # chart.type is "line" (Highcharts has no radar type) with chart.polar set,
    # the x values become the angular categories, and each y column is a series.
    df = pd.DataFrame({"attr": ["a", "b", "c"], "p": [1, 2, 3], "q": [3, 2, 1]})
    opts = build_options(df, "radar", "attr", ["p", "q"])
    assert opts["chart"]["type"] == "line"
    assert opts["chart"]["polar"] is True
    assert opts["xAxis"]["categories"] == ["a", "b", "c"]
    assert [s["name"] for s in opts["series"]] == ["p", "q"]
    assert opts["series"][0]["data"] == [1.0, 2.0, 3.0]
    # Two series -> legend on; the value axis is left to auto-scale (no forced
    # min), like the cartesian one, and draws polygon gridlines for the web look.
    assert opts["legend"]["enabled"] is True
    assert "min" not in opts["yAxis"]
    assert opts["yAxis"]["gridLineInterpolation"] == "polygon"


def test_radar_dark_mode_themes_the_polar_axes():
    # The polygon rings (yAxis gridlines) and the category labels must recolor in
    # dark mode, or the web is invisible against the dark background.
    df = pd.DataFrame({"attr": ["a", "b"], "p": [1, 2]})
    opts = build_options(df, "radar", "attr", ["p"])
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["yAxis"]["gridLineColor"] == "#334155"
    assert opts["xAxis"]["labels"]["style"]["color"] == "#94a3b8"


def test_radar_serializes_and_pulls_in_the_more_module():
    # End to end: the polar chart must serialize AND resolve highcharts-more, the
    # module chart.polar lives in (like bubble) — without it the browser draws a
    # plain, non-polar line instead of the radar.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"attr": ["a", "b", "c"], "p": [1.0, 2.0, 3.0]})
    chart = make_chart(df, "radar", "attr", ["p"])
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'line'" in js and "polar: true" in js
    assert "highcharts-more" in chart.get_script_tags(as_str=True)


# --------------------------------------------------------------------------- #
# Heatmap (an x-category × y-category value matrix, colored by a colorAxis)
# --------------------------------------------------------------------------- #
def test_heatmap_builds_matrix_over_category_axes():
    # Wide-form: x_col's values are the X categories, each y column *name* is a Y
    # category, and every cell is [x_index, y_index, value] — the category-x shape
    # reinterpreted as a grid. Cells are colored by a sequential colorAxis, not the
    # categorical DEFAULT_COLORS palette (still carried, unused, for consistency).
    df = pd.DataFrame({"day": ["Mon", "Tue"], "AM": [1.0, 2.0], "PM": [3.0, 4.0]})
    opts = build_options(df, "heatmap", "day", ["AM", "PM"])
    assert opts["chart"]["type"] == "heatmap"
    assert opts["xAxis"]["categories"] == ["Mon", "Tue"]
    assert opts["yAxis"]["categories"] == ["AM", "PM"]
    # One [x_index, y_index, value] cell per (row, column): 2 rows × 2 columns = 4.
    assert opts["series"][0]["data"] == [
        [0, 0, 1.0],
        [1, 0, 2.0],
        [0, 1, 3.0],
        [1, 1, 4.0],
    ]
    from highcharts_builder import _HEATMAP_GRADIENT

    assert opts["colorAxis"]["maxColor"] == _HEATMAP_GRADIENT["maxColor"]
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert opts["legend"]["enabled"] is True
    # The Y categories are self-labelling, so Highcharts' default "Values" y-axis
    # title is suppressed with an empty string (None would be dropped and leak the
    # default back in).
    assert opts["yAxis"]["title"]["text"] == ""
    # The color scale sits vertically to the right (the heatmap convention).
    assert opts["legend"]["layout"] == "vertical"
    # The tooltip names both category axes so a hovered cell says which (row,
    # column) it is — not just the bare value.
    fmt = opts["tooltip"]["pointFormat"]
    assert "xAxis.categories" in fmt and "yAxis.categories" in fmt
    assert "{point.value}" in fmt
    # A small grid (4 cells) prints each cell's value inside it.
    assert opts["plotOptions"]["heatmap"]["dataLabels"]["enabled"] is True


def test_heatmap_missing_cell_becomes_enforced_null_and_keeps_the_grid():
    # Unlike pie/scatter/bubble (which drop missing rows), a heatmap KEEPS the slot
    # for a missing cell — as EnforcedNull (an empty nullColor cell) — so the grid
    # stays aligned rather than shifting the remaining cells.
    df = pd.DataFrame({"day": ["Mon", "Tue"], "AM": [1.0, float("nan")]})
    data = build_options(df, "heatmap", "day", ["AM"])["series"][0]["data"]
    assert len(data) == 2  # both slots kept, none dropped
    assert data[0] == [0, 0, 1.0]
    assert data[1][:2] == [1, 0]
    assert data[1][2] is EnforcedNull  # missing cell, not Python None or dropped


def test_heatmap_rejects_x_in_y():
    # The X column is a category axis (its values label the columns), so it can't
    # also be one of the Y value columns — the category-x rule, widened to heatmap.
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    with pytest.raises(ValueError):
        build_options(df, "heatmap", "a", ["a"])


def test_heatmap_dark_mode_themes_the_color_axis():
    # The colorAxis gradient legend + its labels aren't reached by the generic
    # xAxis/yAxis theming loop, so dark mode must flip them explicitly (a dark ramp
    # + muted labels) and recolor the empty-cell nullColor — or the color legend
    # renders light-on-dark.
    df = pd.DataFrame({"day": ["Mon", "Tue"], "AM": [1.0, 2.0]})
    opts = build_options(df, "heatmap", "day", ["AM"])
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["colorAxis"]["minColor"] == "#0c4a6e"
    assert opts["colorAxis"]["maxColor"] == "#7dd3fc"
    assert opts["colorAxis"]["labels"]["style"]["color"] == "#94a3b8"
    # The gradient legend's tick lines (full-width gridlines + the shorter edge ticks)
    # default to white and cross the bar as bright dashes; both are muted to the axis
    # colors, or the gridlines stay white while only the ticks flip.
    assert opts["colorAxis"]["gridLineColor"] == "#334155"
    assert opts["colorAxis"]["tickColor"] == "#475569"
    assert opts["plotOptions"]["heatmap"]["nullColor"] == "#334155"
    # The category axes still recolor via the shared loop.
    assert opts["xAxis"]["labels"]["style"]["color"] == "#94a3b8"


def test_heatmap_serializes_and_pulls_in_the_heatmap_module():
    # End to end: the [x, y, value] + colorAxis shape must serialize AND resolve
    # the heatmap module (modules/heatmap.js) — a DIFFERENT module from bubble/
    # radar's highcharts-more; without it the browser renders the chart blank.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"day": ["Mon", "Tue"], "AM": [1.0, 2.0], "PM": [3.0, 4.0]})
    chart = make_chart(df, "heatmap", "day", ["AM", "PM"])
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'heatmap'" in js and "colorAxis" in js
    tags = chart.get_script_tags(as_str=True)
    assert "modules/heatmap.js" in tags
    assert "highcharts-more" not in tags  # heatmap's own module, not bubble/radar's


def test_heatmap_numeric_x_becomes_string_categories():
    # Heatmap has its OWN str() coercion (via _category_labels), separate from the
    # cartesian/radar branch and deliberately excluded from the CATEGORY_X_TYPES
    # parametrization — so a numeric x column must still become string category
    # labels here, or highcharts-core raises CannotCoerceError on render for any
    # user who picks a numeric X.
    df = pd.DataFrame({"week": [1, 2, 3], "AM": [4.0, 5.0, 6.0]})
    opts = build_options(df, "heatmap", "week", ["AM"])
    assert opts["xAxis"]["categories"] == ["1", "2", "3"]


def test_heatmap_light_mode_shape():
    # The dark test pins the dark counterparts; pin the light-mode chrome + tooltip
    # here so the pair reads symmetrically. reversed=True is load-bearing (flips the
    # Y-row order, changing how the whole grid reads); the category-naming tooltip
    # and the light nullColor/minColor are deliberate and otherwise unguarded.
    df = pd.DataFrame({"day": ["Mon", "Tue"], "AM": [1.0, 2.0]})
    opts = build_options(df, "heatmap", "day", ["AM"])
    assert opts["yAxis"]["reversed"] is True
    assert opts["series"][0]["name"] == "value"
    assert opts["tooltip"]["headerFormat"] == ""
    assert "{point.value}" in opts["tooltip"]["pointFormat"]


def test_heatmap_large_grid_omits_data_labels():
    # Per-cell value labels help on a small grid but overprint into noise on a big
    # one, so they're gated on the cell count: past the threshold, none are drawn.
    from highcharts_builder import _HEATMAP_DATALABEL_MAX_CELLS

    rows = _HEATMAP_DATALABEL_MAX_CELLS + 1  # one column, so cells == rows
    df = pd.DataFrame({"x": [str(i) for i in range(rows)], "v": list(range(rows))})
    opts = build_options(df, "heatmap", "x", ["v"])
    assert len(opts["series"][0]["data"]) == rows
    assert "dataLabels" not in opts["plotOptions"]["heatmap"]


def test_heatmap_all_nan_column_serializes_null_cells():
    # A fully-missing Y column must keep ALL its cells (as EnforcedNull) — the grid
    # can't collapse — and those nulls must survive to_js_literal (Python None would
    # be silently dropped; the other serialize test uses all-valid data, so nothing
    # else proves an EnforcedNull cell reaches the JS).
    from highcharts_builder import make_chart

    df = pd.DataFrame(
        {"day": ["Mon", "Tue"], "AM": [1.0, 2.0], "PM": [float("nan"), float("nan")]}
    )
    opts = build_options(df, "heatmap", "day", ["AM", "PM"])
    assert len(opts["series"][0]["data"]) == 2 * 2  # full grid, nothing dropped
    pm_cells = [cell for cell in opts["series"][0]["data"] if cell[1] == 1]  # PM col
    assert pm_cells and all(cell[2] is EnforcedNull for cell in pm_cells)
    js = make_chart(df, "heatmap", "day", ["AM", "PM"]).to_js_literal()
    # A null closing a cell array — distinct from the unconditional nullColor key
    # (whose substring makes a bare "null" check vacuous) — so this proves the
    # EnforcedNull cell actually reached the data array.
    assert js and "null]" in js


# --------------------------------------------------------------------------- #
# Treemap (nested rectangles sized by value, colored categorically like pie)
# --------------------------------------------------------------------------- #
def test_treemap_builds_leaves_and_skips_missing():
    # Treemap shares pie's single-value shape (a label column + one value column)
    # but is its own branch: leaves are keyed "value" (NOT pie's "y" — highcharts-
    # core's treemap point model reads "value" and ignores a stray "y"), colored
    # categorically via colorByPoint, and laid out by the squarified algorithm.
    # Like pie, a NaN-valued row is dropped (a tile can't be sized without a value).
    df = pd.DataFrame({"name": ["A", "B", "C"], "v": [10.0, float("nan"), 30.0]})
    opts = build_options(df, "treemap", "name", ["v"])
    assert opts["chart"]["type"] == "treemap"
    assert opts["series"][0]["name"] == "v"
    # The NaN-valued tile (B) is dropped; leaves use "value", not "y".
    assert opts["series"][0]["data"] == [
        {"name": "A", "value": 10.0},
        {"name": "C", "value": 30.0},
    ]
    tm = opts["plotOptions"]["treemap"]
    assert tm["colorByPoint"] is True
    assert tm["layoutAlgorithm"] == "squarified"
    # Colored categorically from the shared palette (like pie), NOT a colorAxis —
    # so this is not a value-colored type (unlike heatmap).
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert "colorAxis" not in opts


def test_treemap_uses_only_first_y_col():
    # Single-value like pie: only the first selected column sizes the tiles.
    df = pd.DataFrame({"name": ["A", "B"], "v": [1.0, 2.0], "v2": [9.0, 9.0]})
    opts = build_options(df, "treemap", "name", ["v", "v2"])
    assert opts["series"][0]["name"] == "v"
    assert [pt["value"] for pt in opts["series"][0]["data"]] == [1.0, 2.0]


def test_treemap_dark_mode_themes_tiles_and_skips_axes():
    # Dark mode paints the background and matches the tile gaps (borderColor) to it
    # so they don't read as white grid-lines — as pie does for its slice gaps. The
    # data-label color stays "contrast" (NOT flipped to light like pie's): treemap
    # labels sit on the palette-colored tile, not the chart background, so the same
    # value stays legible in both themes.
    df = pd.DataFrame({"name": ["A", "B"], "v": [1.0, 2.0]})
    opts = build_options(df, "treemap", "name", ["v"])
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["plotOptions"]["treemap"]["borderColor"] == "#0f172a"
    assert opts["plotOptions"]["treemap"]["dataLabels"]["color"] == "contrast"
    # Treemap has no axes, so the axis-theming loop must simply skip it (not crash).
    assert "xAxis" not in opts


def test_treemap_serializes_and_pulls_in_the_treemap_module():
    # End to end: the {name, value} leaf shape must serialize AND resolve
    # modules/treemap.js — treemap's own module, distinct from bubble/radar's
    # highcharts-more; without it the browser renders the chart blank.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"name": ["A", "B", "C"], "v": [1.0, 2.0, 3.0]})
    chart = make_chart(df, "treemap", "name", ["v"])
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'treemap'" in js
    tags = chart.get_script_tags(as_str=True)
    assert "modules/treemap.js" in tags
    assert "highcharts-more" not in tags  # treemap's own module, not bubble/radar's


def test_treemap_light_mode_shape():
    # The dark test pins the dark counterparts; pin the light-mode chrome here so
    # the pair reads symmetrically (mirrors test_heatmap_light_mode_shape). These
    # treemap-specific choices are otherwise unguarded: the {name, value} tooltip
    # (headerFormat blanked so a hovered tile isn't a bare value), the disabled
    # legend (the in-tile labels carry identity, so a legend would just repeat
    # them), and the two-line name+value "contrast" tile labels (printed in the
    # mark so the Static-PNG mode, which has no hover, still shows the numbers —
    # like pie and heatmap).
    df = pd.DataFrame({"name": ["A", "B"], "v": [1.0, 2.0]})
    opts = build_options(df, "treemap", "name", ["v"])
    assert opts["legend"]["enabled"] is False
    assert opts["tooltip"]["headerFormat"] == ""
    assert opts["tooltip"]["pointFormat"] == "{point.name}: <b>{point.value}</b>"
    labels = opts["plotOptions"]["treemap"]["dataLabels"]
    assert labels["enabled"] is True
    assert labels["format"] == "{point.name}<br>{point.value}"
    assert labels["color"] == "contrast"


# --------------------------------------------------------------------------- #
# Funnel / pyramid (part-of-whole stages — pie's single-value cousins)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_funnel_family_builds_leaves_and_skips_missing(chart_type):
    # Funnel/pyramid share pie's single-value shape (a label column + one value column)
    # AND pie's leaf key: FunnelSeries is FunnelOptions(PieOptions), so leaves are keyed
    # "y" (NOT treemap's "value"). Like pie, a NaN- or inf-valued row is DROPPED (a stage
    # can't be sized without a value) — not the category-x keep-a-slot EnforcedNull family.
    df = pd.DataFrame({"stage": ["A", "B", "C"], "v": [10.0, float("nan"), 30.0]})
    opts = build_options(df, chart_type, "stage", ["v"])
    # chart.type is the CONCRETE type name for both — pyramid is its own series type, not a
    # funnel with reversed=True, so nothing here says "funnel" for a pyramid.
    assert opts["chart"]["type"] == chart_type
    assert opts["series"][0]["name"] == "v"
    assert opts["series"][0]["data"] == [
        {"name": "A", "y": 10.0},
        {"name": "C", "y": 30.0},
    ]
    # Palette-hued per stage from the shared colors, NOT a colorAxis (like pie, unlike heatmap).
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert "colorAxis" not in opts


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_funnel_family_uses_only_first_y_col(chart_type):
    # Single-value like pie: only the first selected column sizes the stages.
    df = pd.DataFrame({"stage": ["A", "B"], "v": [1.0, 2.0], "v2": [9.0, 9.0]})
    opts = build_options(df, chart_type, "stage", ["v", "v2"])
    assert opts["series"][0]["name"] == "v"
    assert [pt["y"] for pt in opts["series"][0]["data"]] == [1.0, 2.0]


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_funnel_family_draws_stages_in_row_order(chart_type):
    # A stage's row order IS load-bearing (unlike pie's cosmetic slice order), and Highcharts does
    # NOT auto-sort. The builder is deliberately permissive — it emits stages in the order the rows
    # arrive, re-sorting nothing — so an out-of-order input is kept as given (columnrange's
    # kept-inverted-range permissiveness, one family over). This pins that no sort creeps into the
    # emitted DATA ARRAY; which end of the shape row 0 lands on is Highcharts' call and differs by
    # type (a funnel draws row 0 at the top, a pyramid at the base), so it is not asserted here.
    df = pd.DataFrame(
        {"stage": ["A", "B", "C"], "v": [10.0, 90.0, 40.0]}
    )  # non-monotonic
    data = build_options(df, chart_type, "stage", ["v"])["series"][0]["data"]
    assert [pt["name"] for pt in data] == ["A", "B", "C"]
    assert [pt["y"] for pt in data] == [10.0, 90.0, 40.0]


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_funnel_family_dark_mode_themes_labels_and_border(chart_type):
    # Pie's TWO dark-mode flips, not treemap's one — because a funnel's data labels sit OUTSIDE
    # the shape on the chart background (its default placement), so they take the light TEXT
    # color; and the segment borders default to the white background var, so they are dissolved
    # into the dark background (borderColor). Keyed by the concrete chart.type, so pyramid themes
    # through its own plotOptions key.
    df = pd.DataFrame({"stage": ["A", "B"], "v": [1.0, 2.0]})
    opts = build_options(df, chart_type, "stage", ["v"])
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    po = opts["plotOptions"][chart_type]
    assert (
        po["dataLabels"]["color"] == "#f1f5f9"
    )  # light text, unlike treemap's "contrast"
    assert po["borderColor"] == "#0f172a"  # segment gaps match the dark background
    # No axes, so the axis-theming loop must simply skip it (not crash).
    assert "xAxis" not in opts


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_funnel_family_serializes_and_pulls_in_the_funnel_module(chart_type):
    # End to end: the {name, y} leaf shape must serialize (values reach the JS) AND resolve
    # modules/funnel.js — shared by funnel and pyramid, and NOT highcharts-more (the plausible
    # guess the round-trip corrects, as it does for bubble/boxplot vs treemap/sunburst/xrange).
    from highcharts_builder import make_chart

    df = pd.DataFrame({"stage": ["A", "B", "C"], "v": [10.0, 20.0, 30.0]})
    chart = make_chart(df, chart_type, "stage", ["v"])
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and f"type: '{chart_type}'" in js
    # The leaf VALUE must survive the Chart.from_options round-trip into the JS — the treemap
    # `value`-vs-`y` silent-drop trap, one type over. highcharts-core collapses each {name, y}
    # leaf into a `[name, value]` 2-array, so pin the name-to-value PAIR (a dropped value would
    # leave `['A']` with no number) rather than a bare "10", which could match elsewhere.
    flat = "".join(js.split())  # the pairs span newlines: ['A',\n10.0] -> ['A',10.0]
    assert "['A',10.0]" in flat
    assert "['B',20.0]" in flat
    assert "['C',30.0]" in flat
    tags = chart.get_script_tags(as_str=True)
    assert "modules/funnel.js" in tags
    assert "highcharts-more" not in tags  # funnel's own module, not bubble/radar's


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_funnel_family_light_mode_shape(chart_type):
    # Pin the otherwise-unguarded funnel/pyramid choices — parametrized over BOTH, since they
    # share one branch and these strings must be byte-identical between them: the value+share
    # tooltip (headerFormat blanked; the percentage is a funnel point's share of the STAGE TOTAL —
    # pie semantics, inherited — labelled "of total" so it isn't misread as a conversion rate),
    # the outside-the-shape name+value data labels, and the ABSENCE of an explicit colorByPoint
    # key (funnel inherits colorByPoint: true from pie's JS default, and highcharts-core cannot
    # express the key at all — so the builder must set nothing, unlike treemap which sets it).
    df = pd.DataFrame({"stage": ["A", "B"], "v": [3.0, 1.0]})
    opts = build_options(df, chart_type, "stage", ["v"])
    assert opts["tooltip"]["headerFormat"] == ""
    assert opts["tooltip"]["pointFormat"] == (
        "{point.name}: <b>{point.y}</b> ({point.percentage:.1f}% of total)"
    )
    plot = opts["plotOptions"][chart_type]
    assert plot["dataLabels"]["enabled"] is True
    assert plot["dataLabels"]["format"] == "{point.name}: {point.y}"
    assert "colorByPoint" not in plot  # inherited from pie's default, never set here


def test_pyramid_is_its_own_series_type_not_a_reversed_funnel():
    # Pyramid is modeled as the real PyramidSeries (chart.type "pyramid"), which draws inverted
    # by default — NOT a funnel with reversed=True + a zeroed neck. So the emitted options carry
    # NO `reversed` key and the type is literally "pyramid", keeping this module's "every type
    # serializes as its own Highcharts name" rule intact (radar is the sole exception).
    df = pd.DataFrame({"tier": ["A", "B", "C"], "v": [1.0, 2.0, 3.0]})
    opts = build_options(df, "pyramid", "tier", ["v"])
    assert opts["chart"]["type"] == "pyramid"
    assert "reversed" not in opts["plotOptions"]["pyramid"]
    assert "neckWidth" not in opts["plotOptions"]["pyramid"]


@pytest.mark.parametrize("chart_type", ["pie", "treemap", "funnel", "pyramid"])
def test_single_value_numeric_labels_coerce_to_strings(chart_type):
    # The single-value point-name types (pie, treemap, funnel, pyramid) build leaves as
    # {"name": str(label), ...}. That str() is load-bearing: highcharts-core's
    # point model rejects a non-string name (CannotCoerceError on render), so a
    # user who picks a numeric label column (years, IDs) would otherwise get a
    # blank/erroring chart. This is the point-name analog of the category-axis
    # coercion tests (test_category_x_numeric_x_becomes_string_categories,
    # test_heatmap_numeric_x_becomes_string_categories); the shared labeled_frame
    # sweeps only use string labels, so nothing else pins it for these two.
    df = pd.DataFrame({"yr": [2001, 2002], "v": [1.0, 2.0]})
    data = build_options(df, chart_type, "yr", ["v"])["series"][0]["data"]
    assert [pt["name"] for pt in data] == ["2001", "2002"]  # strings, not ints


# --------------------------------------------------------------------------- #
# Sankey (node-link flows: source -> target links sized by weight)
# --------------------------------------------------------------------------- #
def _links(opts) -> list[dict]:
    """The sankey links with their per-link ``dataLabels`` stripped, so the shape
    tests read as the plain edge list. Those labels are pinned separately by
    test_sankey_labels_its_nodes_and_links, and their absence on a large diagram by
    test_sankey_many_links_omit_the_weight_labels."""
    return [
        {key: value for key, value in link.items() if key != "dataLabels"}
        for link in opts["series"][0]["data"]
    ]


def test_sankey_builds_links_and_skips_missing():
    # Sankey is the one type whose data is a *graph*, not a table: every row is a
    # link, keyed {from, to, weight}. Not the [x, y, value] arrays heatmap builds
    # (highcharts-core rejects the equivalent array-form sankey series outright),
    # and not pie's "y". A row with a missing weight can't size a link — and
    # serializes silently, as an invisible zero-width one — so it's dropped, as a
    # valueless pie slice is. No EnforcedNull: unlike the heatmap grid, there's no
    # cell here to keep aligned.
    df = pd.DataFrame(
        {
            "src": ["Coal", "Gas", "Wind"],
            "dst": ["Power", "Power", "Power"],
            "w": [42.0, float("nan"), 26.0],
        }
    )
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    assert opts["chart"]["type"] == "sankey"
    assert opts["series"][0]["name"] == "w"
    # The NaN-weighted link (Gas) is dropped; links use from/to/weight.
    assert _links(opts) == [
        {"from": "Coal", "to": "Power", "weight": 42.0},
        {"from": "Wind", "to": "Power", "weight": 26.0},
    ]
    # Nodes are colored categorically from the shared palette (like pie/treemap),
    # NOT by a colorAxis — so this is not a value-colored type (unlike heatmap).
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert "colorAxis" not in opts
    # A flow diagram has no axes at all.
    assert "xAxis" not in opts and "yAxis" not in opts


def test_sankey_drops_rows_missing_either_node():
    # Not only a missing weight: a link with no source, or no target, isn't an edge
    # either — all three columns are required per row.
    df = pd.DataFrame(
        {"src": ["A", None, "C"], "dst": ["X", "Y", None], "w": [1.0, 2.0, 3.0]}
    )
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    assert _links(opts) == [{"from": "A", "to": "X", "weight": 1.0}]


def test_sankey_uses_only_first_y_col():
    # Single-value like pie/treemap: only the first selected column weights the
    # links (the app gives sankey a single-select Y for exactly this reason).
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0], "w2": [9.0]})
    opts = build_options(df, "sankey", "src", ["w", "w2"], target_col="dst")
    assert opts["series"][0]["name"] == "w"
    assert [link["weight"] for link in opts["series"][0]["data"]] == [1.0]


def test_sankey_requires_a_target_column():
    # A sankey without its target column has only one end per link, so the target is
    # mandatory — a ValueError, not a silent fallback (as bubble's size_col is).
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    with pytest.raises(ValueError):
        build_options(df, "sankey", "src", ["w"])  # no target_col


def test_sankey_rejects_source_as_target():
    # One column can't name both ends of a link: every row would be a self-loop.
    # This is sankey's OWN guard, not the category-x x-in-y rule — target_col is
    # never among y_cols, so X_IN_Y_GUARD_TYPES structurally can't express it, which
    # is why sankey is absent from that constant.
    df = pd.DataFrame({"src": ["A"], "w": [1.0]})
    with pytest.raises(ValueError):
        build_options(df, "sankey", "src", ["w"], target_col="src")


def test_sankey_allows_the_weight_to_repeat_a_node_column():
    # The guard is source-vs-target ONLY. Weighting a link by the same column that
    # names one of its nodes is odd but well-defined, so it builds — the same
    # deliberate restraint as test_scatter_allows_x_in_y. Also pins that a numeric
    # node column is stringified into a node name.
    df = pd.DataFrame({"src": ["A", "B"], "w": [1.0, 2.0]})
    opts = build_options(df, "sankey", "src", ["w"], target_col="w")
    assert _links(opts) == [
        {"from": "A", "to": "1.0", "weight": 1.0},
        {"from": "B", "to": "2.0", "weight": 2.0},
    ]


def test_sankey_node_tooltip_lives_in_plot_options_not_the_tooltip():
    # The node-hover format MUST sit under plotOptions.sankey.tooltip: highcharts-
    # core's Tooltip model has no nodeFormat, so a top-level one is accepted by
    # Chart.from_options and then SILENTLY DROPPED from the emitted JS — the same
    # class of trap as treemap's "value" vs "y" leaf key. Only the serialized JS
    # proves it arrived, so assert on that too, not just the options dict.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    assert "nodeFormat" not in opts["tooltip"]  # would vanish if it were here
    assert (
        opts["plotOptions"]["sankey"]["tooltip"]["nodeFormat"]
        == "{point.name}: <b>{point.sum}</b>"
    )
    js = make_chart(df, "sankey", "src", ["w"], target_col="dst").to_js_literal()
    assert js and "nodeFormat" in js and "point.sum" in js


def test_sankey_serializes_and_pulls_in_the_sankey_module():
    # End to end: the {from, to, weight} link shape must serialize AND resolve
    # modules/sankey.js — sankey's own module, distinct from bubble/radar's
    # highcharts-more; without it the browser renders the chart blank. The link keys
    # in particular must reach the JS: highcharts-core builds a typed point model
    # and silently discards any key it doesn't recognize.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"src": ["A", "B"], "dst": ["C", "C"], "w": [1.0, 2.0]})
    chart = make_chart(df, "sankey", "src", ["w"], target_col="dst")
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'sankey'" in js
    assert "from: 'A'" in js and "to: 'C'" in js and "weight: 1.0" in js
    # The per-link weight label must reach the JS too — a series-level dataLabels
    # format is the one thing that WOULD survive serialization while rendering the
    # wrong chart (it labels the links with the node format and blanks the names),
    # so the options-dict assertions alone can't prove this arrived intact.
    assert "format: '{point.weight}'" in js
    tags = chart.get_script_tags(as_str=True)
    assert "modules/sankey.js" in tags
    assert "highcharts-more" not in tags  # sankey's own module, not bubble/radar's


def test_sankey_labels_its_nodes_and_links():
    # Nodes are named and links carry their weight — the value printed IN the mark,
    # as pie/heatmap/treemap print theirs, so the Static-PNG mode (no hover) still
    # shows the numbers. Getting BOTH takes two separate places, and the reason is a
    # silent drop: highcharts-core discards plotOptions.sankey.dataLabels.nodeFormat,
    # and the `format` that does survive there applies to nodes AND links, so setting
    # it series-wide would label every link with the node format and blank the node
    # names. Hence: an empty series-level dataLabels (Highcharts' own default
    # nodeFormat names the nodes) plus a per-link label carrying the weight. No color
    # is set anywhere — Highcharts' `contrast` default handles both themes.
    df = pd.DataFrame({"src": ["A", "B"], "dst": ["C", "C"], "w": [1.0, 2.0]})
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    series_labels = opts["plotOptions"]["sankey"]["dataLabels"]
    assert series_labels == {"enabled": True}  # no `format`: it would blank the names
    for link in opts["series"][0]["data"]:
        assert link["dataLabels"] == {"enabled": True, "format": "{point.weight}"}
    # Each link's label dict is its own object, so nothing can mutate the module
    # constant through one of them (the _HEATMAP_GRADIENT copy rule).
    first, second = (link["dataLabels"] for link in opts["series"][0]["data"])
    assert first is not second


def test_sankey_many_links_omit_the_weight_labels():
    # Per-link weight labels help on a small diagram but overprint into noise on a
    # big one, so they're gated on the link count: past the threshold, none are
    # attached. The sankey counterpart of test_heatmap_large_grid_omits_data_labels.
    from highcharts_builder import _SANKEY_DATALABEL_MAX_LINKS

    rows = _SANKEY_DATALABEL_MAX_LINKS + 1
    df = pd.DataFrame(
        {
            "src": [f"s{i}" for i in range(rows)],
            "dst": ["hub"] * rows,
            "w": [float(i + 1) for i in range(rows)],
        }
    )
    links = build_options(df, "sankey", "src", ["w"], target_col="dst")["series"][0][
        "data"
    ]
    assert len(links) == rows
    assert all("dataLabels" not in link for link in links)
    # The node names still render — those come from the series-level dataLabels.
    assert build_options(df, "sankey", "src", ["w"], target_col="dst")["plotOptions"][
        "sankey"
    ]["dataLabels"] == {"enabled": True}


def test_sankey_light_mode_shape():
    # Mirrors test_treemap_light_mode_shape: pin the light-mode choices that nothing
    # else guards — the link tooltip naming both ends (headerFormat blanked so a
    # hovered link isn't a bare number) and the disabled legend (each node is
    # labelled on the chart, so a legend would only repeat them).
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    assert opts["legend"]["enabled"] is False
    assert opts["tooltip"]["headerFormat"] == ""
    assert opts["tooltip"]["pointFormat"] == "src → dst: <b>{point.weight}</b>"


def test_sankey_dark_mode_themes_borders_and_skips_axes():
    # Only the borders flip: they default to light and would read as white outlines
    # against the dark background, exactly as pie's slice gaps do. The node and link
    # LABELS are deliberately left alone — Highcharts draws them in its `contrast`
    # color, computed against whatever each sits on, so they stay legible in both
    # themes without a flip (the treemap reasoning, not pie's).
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["plotOptions"]["sankey"]["borderColor"] == "#0f172a"
    assert "color" not in opts["plotOptions"]["sankey"]["dataLabels"]
    assert all("color" not in link["dataLabels"] for link in opts["series"][0]["data"])
    # The dark tooltip merge keeps the link pointFormat (as the pie path relies on).
    assert opts["tooltip"]["backgroundColor"] == "#0f172a"
    assert "{point.weight}" in opts["tooltip"]["pointFormat"]
    # Sankey has no axes, so the axis-theming loop must simply skip it (not crash).
    assert "xAxis" not in opts


def test_sankey_tooltip_sanitizes_user_column_names():
    # Both node column names land in a Highcharts format string as literal text, so
    # — like bubble's x/size names — they're brace-stripped (Highcharts would parse
    # `{...}` as a value token) and HTML-escaped (tooltips render as HTML).
    df = pd.DataFrame({"from {a}": ["A"], "<b>to</b>": ["B"], "w": [1.0]})
    fmt = build_options(df, "sankey", "from {a}", ["w"], target_col="<b>to</b>")[
        "tooltip"
    ]["pointFormat"]
    # Braces stripped, so Highcharts won't tokenize `{a}` away.
    assert "{a}" not in fmt
    assert "from a" in fmt
    # HTML in the target column name is escaped, not emitted as live markup.
    assert "<b>to</b>" not in fmt
    assert "&lt;b&gt;to&lt;/b&gt;" in fmt
    # The genuine Highcharts token is untouched.
    assert "{point.weight}" in fmt


def test_sankey_numeric_node_labels_coerce_to_strings():
    # Both node columns are stringified: highcharts-core's point model rejects a
    # non-string node name, so a user picking numeric ids would otherwise get a
    # blank/erroring chart. The pie/treemap coercion test
    # (test_single_value_numeric_labels_coerce_to_strings) for the one type with
    # *two* label columns — the shared labeled_frame sweeps use string nodes only.
    df = pd.DataFrame({"src": [1, 2], "dst": [10, 20], "w": [1.0, 2.0]})
    opts = build_options(df, "sankey", "src", ["w"], target_col="dst")
    assert _links(opts) == [
        {"from": "1", "to": "10", "weight": 1.0},
        {"from": "2", "to": "20", "weight": 2.0},
    ]


# --------------------------------------------------------------------------- #
# Dependencywheel (a circular sankey: weighted links around a ring) — SHARES
# sankey's build branch, keyed by chart_type. So the {from, to, weight} links, the
# drop policy, the per-link weight labels and the node/link tooltips are the ones the
# sankey block above already pins; these tests pin only what is DISTINCT: the
# chart.type / plotOptions key the branch parametrizes, and the TWO modules the wheel
# resolves (modules/dependency-wheel PLUS modules/sankey) where sankey pulls one. In
# highcharts-core, DependencyWheelSeries is literally SankeySeries' parent class.
# --------------------------------------------------------------------------- #
def test_dependencywheel_builds_weighted_links_like_sankey():
    # The shared branch must emit chart.type 'dependencywheel' (not 'sankey') while
    # producing the identical {from, to, weight} links — a row missing any of the three is
    # dropped exactly as sankey's is (an invisible zero-width link otherwise). No colorAxis
    # and no axes: a wheel colors its ribbons categorically from the palette (like pie /
    # treemap / sankey) and, being a diagram, has no axes to draw.
    df = pd.DataFrame(
        {
            "src": ["Coal", "Gas", "Wind"],
            "dst": ["Power", "Power", "Power"],
            "w": [42.0, float("nan"), 26.0],
        }
    )
    opts = build_options(df, "dependencywheel", "src", ["w"], target_col="dst")
    assert opts["chart"]["type"] == "dependencywheel"
    assert opts["series"][0]["name"] == "w"
    assert _links(opts) == [
        {"from": "Coal", "to": "Power", "weight": 42.0},
        {"from": "Wind", "to": "Power", "weight": 26.0},
    ]
    # A wheel prints NO per-link weight label — the ONE place it diverges from sankey beyond the
    # type string, found by rendering: on the ring Highcharts stacks link labels in a clipped
    # column off the left. The node NAMES still render, via the series-level dataLabels.
    assert all("dataLabels" not in link for link in opts["series"][0]["data"])
    assert opts["plotOptions"]["dependencywheel"]["dataLabels"] == {"enabled": True}
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert "colorAxis" not in opts
    assert "xAxis" not in opts and "yAxis" not in opts


def test_dependencywheel_plot_options_land_under_its_own_key():
    # The one place the shared branch diverges from sankey: `chart.type` and the
    # `plotOptions` key must key on 'dependencywheel', not 'sankey' — a copy-paste leaving
    # them under 'sankey' would emit a block Highcharts ignores. The node tooltip (throughput
    # of a hovered node) rides plotOptions[type].tooltip.nodeFormat, and — as with sankey — a
    # TOP-LEVEL tooltip.nodeFormat is silently dropped, so it must live here; only the emitted
    # JS proves it survived (verified on the round-trip that the wheel's nodeFormat does).
    from highcharts_builder import make_chart

    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    opts = build_options(df, "dependencywheel", "src", ["w"], target_col="dst")
    assert "sankey" not in opts["plotOptions"]  # not left under the wrong key
    assert "nodeFormat" not in opts["tooltip"]  # would vanish if it were here
    assert (
        opts["plotOptions"]["dependencywheel"]["tooltip"]["nodeFormat"]
        == "{point.name}: <b>{point.sum}</b>"
    )
    js = make_chart(
        df, "dependencywheel", "src", ["w"], target_col="dst"
    ).to_js_literal()
    assert js and "nodeFormat" in js and "point.sum" in js


def test_dependencywheel_serializes_and_pulls_in_both_modules():
    # End to end, and the type's headline serialization fact: a dependencywheel resolves
    # modules/dependency-wheel.js AND modules/sankey.js — BOTH, from chart.type alone (the
    # wheel builds on sankey's diagram infrastructure) — and NOT highcharts-more (the
    # plausible guess the round-trip corrects, as it does for columnrange/funnel). The link
    # keys and the per-link weight label must reach the JS too, since highcharts-core silently
    # discards any key its typed point model doesn't recognize.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"src": ["A", "B"], "dst": ["C", "C"], "w": [1.0, 2.0]})
    chart = make_chart(df, "dependencywheel", "src", ["w"], target_col="dst")
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'dependencywheel'" in js
    assert "from: 'A'" in js and "to: 'C'" in js and "weight: 1.0" in js
    # No per-link weight label on a wheel (they misplace on the ring), unlike sankey's JS.
    assert "format: '{point.weight}'" not in js
    tags = chart.get_script_tags(as_str=True)
    assert "modules/dependency-wheel.js" in tags
    assert "modules/sankey.js" in tags  # the wheel builds on sankey's module
    assert "highcharts-more" not in tags  # the round-trip corrects the plausible guess


def test_dependencywheel_html_loads_sankey_before_dependency_wheel():
    # THE interactive-mode regression pin. modules/dependency-wheel.js EXTENDS the sankey series,
    # so it must load AFTER modules/sankey.js — but highcharts-core's get_script_tags emits them
    # REVERSED (it walks the chart's plotOptions before its series, so the dependent module is
    # seen first). Loaded first, dependency-wheel.js throws "Cannot read properties of undefined
    # (reading 'prototype')" and Highcharts reports the series missing (error #17), leaving a BLANK
    # iframe while the export-server PNG renders fine — the two-render-modes-must-agree bug that
    # build_chart_html fixes via _order_script_tags. So pin the ORDER in the emitted HTML, not just
    # the presence the test above covers: sankey's tag must precede the wheel's. Verified by
    # rendering in a real browser (the console showed error #17 before the fix, nothing after).
    from highcharts_builder import build_chart_html

    df = pd.DataFrame({"src": ["A", "B"], "dst": ["C", "C"], "w": [1.0, 2.0]})
    html = build_chart_html(df, "dependencywheel", "src", ["w"], target_col="dst")
    assert "modules/sankey.js" in html and "modules/dependency-wheel.js" in html
    assert html.index("modules/sankey.js") < html.index("modules/dependency-wheel.js")


def test_order_script_tags_puts_a_prerequisite_before_its_dependent():
    # The pure reorder behind the fix above. Given the dependent's tag AHEAD of its prerequisite's
    # (get_script_tags' actual output for a dependencywheel), it moves the prerequisite in front;
    # it is a no-op when the pair is absent or already ordered, so it can't disturb a plain sankey
    # (no dependency-wheel tag) or any other type, and it is idempotent.
    from highcharts_builder import _order_script_tags

    reversed_tags = (
        '<script src="x/highcharts.js"></script>\n'
        '<script src="x/modules/dependency-wheel.js"></script>\n'
        '<script src="x/modules/sankey.js"></script>'
    )
    out = _order_script_tags(reversed_tags).split("\n")
    assert out[0].endswith('highcharts.js"></script>')  # untouched
    assert "modules/sankey.js" in out[1]  # prerequisite moved ahead of the dependent
    assert "modules/dependency-wheel.js" in out[2]

    # Idempotent on already-ordered input, and a no-op on a lone sankey tag (no dependent present).
    assert _order_script_tags("\n".join(out)) == "\n".join(out)
    lone_sankey = '<script src="x/modules/sankey.js"></script>'
    assert _order_script_tags(lone_sankey) == lone_sankey


def test_order_script_tags_raises_when_a_dependent_lacks_its_prerequisite():
    # A dependent module present WITHOUT its prerequisite can't be saved by reordering — the chart
    # pulled a module that extends one it did not, so the interactive iframe would blank. Raise
    # loudly instead of silently no-opping (which is how a renamed module or a drifted tag format
    # would otherwise re-introduce the very blank-iframe bug this helper exists to prevent).
    from highcharts_builder import _order_script_tags

    orphaned = (
        '<script src="x/highcharts.js"></script>\n'
        '<script src="x/modules/dependency-wheel.js"></script>'  # no modules/sankey.js
    )
    with pytest.raises(ValueError, match="prerequisite"):
        _order_script_tags(orphaned)


def test_dependencywheel_requires_a_target_column():
    # A wheel without its target column has only one end per link — mandatory, a ValueError,
    # exactly as sankey's is (both bind the shared NODE_LINK_TYPES guard).
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    with pytest.raises(ValueError):
        build_options(df, "dependencywheel", "src", ["w"])  # no target_col


def test_dependencywheel_rejects_source_as_target():
    # One column can't name both ends of a link — every row a self-loop. The shared
    # node-link guard, not the category-x x-in-y rule (target_col is never among y_cols).
    df = pd.DataFrame({"src": ["A"], "w": [1.0]})
    with pytest.raises(ValueError):
        build_options(df, "dependencywheel", "src", ["w"], target_col="src")


def test_dependencywheel_light_mode_shape():
    # Pin the light-mode choices nothing else guards: the link tooltip naming both ends and
    # the disabled legend (each node is labelled on the ring, so a legend would only repeat
    # them). Light mode injects no dark chrome, and the border hook must NOT fire (dark-only).
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    opts = build_options(df, "dependencywheel", "src", ["w"], target_col="dst")
    assert opts["legend"]["enabled"] is False
    assert opts["tooltip"]["headerFormat"] == ""
    assert opts["tooltip"]["pointFormat"] == "src → dst: <b>{point.weight}</b>"
    # Key-correctness — that the border block lands under 'dependencywheel', not a stale
    # 'sankey' — is pinned by test_dependencywheel_plot_options_land_under_its_own_key.


def test_dependencywheel_dark_mode_dissolves_borders_under_its_own_key():
    # The border hook is keyed on the type, so in dark mode it must dissolve the border under
    # plotOptions.dependencywheel (not a stale 'sankey' key), exactly as sankey's does under
    # its own. The node/link labels ride Highcharts' `contrast` default (no color set), and
    # the tooltip box is themed for dark mode.
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "w": [1.0]})
    opts = build_options(df, "dependencywheel", "src", ["w"], target_col="dst")
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["plotOptions"]["dependencywheel"]["borderColor"] == "#0f172a"
    assert "sankey" not in opts["plotOptions"]
    assert "color" not in opts["plotOptions"]["dependencywheel"]["dataLabels"]
    assert opts["tooltip"]["backgroundColor"] == "#0f172a"


# --------------------------------------------------------------------------- #
# Networkgraph (a force-directed graph: rows are UNWEIGHTED edges) — sankey's
# cousin, and the MIRROR of the gauge family: it removes the VALUE channel
# (empty y_cols) as gauge removes the LABEL channel (None x_col).
# --------------------------------------------------------------------------- #
def test_networkgraph_builds_edges_and_skips_missing():
    # Like sankey, each row is one edge keyed {from, to} — but UNWEIGHTED: there is no
    # third value key, because a per-link weight is silently dropped from the emitted JS
    # anyway. A row missing EITHER node isn't an edge, so it's dropped (no EnforcedNull:
    # there's no aligned slot, exactly as sankey drops a link).
    df = pd.DataFrame({"src": ["Web", None, "API"], "dst": ["API", "Auth", None]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert opts["chart"]["type"] == "networkgraph"
    # One edge-series; its name is the source→target relation (no y column to name it).
    assert opts["series"][0]["name"] == "src → dst"
    assert opts["series"][0]["data"] == [{"from": "Web", "to": "API"}]
    # Nodes are palette-colored (like sankey/pie), not by a colorAxis, and there are no axes.
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert "colorAxis" not in opts
    assert "xAxis" not in opts and "yAxis" not in opts


def test_networkgraph_builds_with_empty_y_cols():
    # The positive half of test_rejects_empty_y_cols' networkgraph EXCLUSION: an empty y_cols
    # is networkgraph's normal state (it has no value channel), so it must BUILD rather than
    # raise — the mirror of a gauge building with a None x_col.
    df = pd.DataFrame({"src": ["A", "B"], "dst": ["B", "C"]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert opts["series"][0]["data"] == [
        {"from": "A", "to": "B"},
        {"from": "B", "to": "C"},
    ]


def test_networkgraph_ignores_any_y_cols_it_is_given():
    # It has no value channel, so a y column passed through the pure API (the sweeps do this)
    # changes nothing — the edges are identical with y_cols=["v"] and with []. Proven by
    # equality, so the day networkgraph starts reading y_cols this test fails.
    df = pd.DataFrame({"src": ["A"], "dst": ["B"], "v": [99.0]})
    with_y = build_options(df, "networkgraph", "src", ["v"], target_col="dst")
    without_y = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert with_y["series"][0]["data"] == without_y["series"][0]["data"]


def test_networkgraph_requires_a_target_column():
    # An edge needs two ends, so the target is mandatory (a ValueError, not a silent
    # fallback) — sankey's rule, and the message names the type.
    df = pd.DataFrame({"src": ["A"], "dst": ["B"]})
    with pytest.raises(ValueError, match="networkgraph"):
        build_options(df, "networkgraph", "src", [])  # no target_col


def test_networkgraph_rejects_source_as_target():
    # One column can't name both ends — every edge would be a self-loop. Networkgraph's OWN
    # guard, shared with sankey (a fact about the two node columns), not the x-in-y rule.
    df = pd.DataFrame({"src": ["A", "B"]})
    with pytest.raises(ValueError):
        build_options(df, "networkgraph", "src", [], target_col="src")


def test_networkgraph_serializes_and_pulls_in_only_the_networkgraph_module():
    # End to end: the edge shape must serialize AND resolve modules/networkgraph.js — and,
    # unlike bubble/radar/boxplot, NOT highcharts-more (verified against the round-trip, the
    # correction to the common lore that a networkgraph needs it). colorByPoint must appear
    # NOWHERE: it is silently dropped for a networkgraph (so setting it is a lie), and the
    # nodes carry no per-point color at all.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"src": ["A", "B"], "dst": ["B", "C"]})
    chart = make_chart(df, "networkgraph", "src", [], target_col="dst")
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'networkgraph'" in js
    # highcharts-core serializes each {from, to} dict as a [from, to] ARRAY (Highcharts' default
    # link shape) — so the node names reach the JS as array elements, not `from:`/`to:` keys.
    assert "'A'" in js and "'B'" in js and "'C'" in js
    assert "colorByPoint" not in js
    tags = chart.get_script_tags(as_str=True)
    assert "modules/networkgraph.js" in tags
    assert "highcharts-more" not in tags  # a networkgraph does NOT need highcharts-more


def test_networkgraph_disables_the_simulation_so_both_render_modes_agree():
    # enableSimulation MUST be False, and pinned on the EMITTED JS (this repo's silent-drop
    # discipline). It is the one setting the whole type turns on: with it True the export
    # server rasterizes the graph as an unreadable central knot while the iframe animates it
    # loose, so the two render modes disagree — the class of bug _LIGHT_COLOR_SCHEME_CSS
    # exists to close. With it False Highcharts settles the layout synchronously and both
    # modes draw the same picture.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"src": ["A"], "dst": ["B"]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    layout = opts["plotOptions"]["networkgraph"]["layoutAlgorithm"]
    assert layout["enableSimulation"] is False
    # keys maps each serialized [from, to] array onto the edge's two ends.
    assert opts["plotOptions"]["networkgraph"]["keys"] == ["from", "to"]
    js = make_chart(df, "networkgraph", "src", [], target_col="dst").to_js_literal()
    assert js and "enableSimulation: false" in js


def test_networkgraph_labels_its_nodes_and_prints_nothing_per_edge():
    # Nodes are labelled by name (their only identity — no axis, no legend). Unlike sankey
    # there is NO per-edge label, because the type is unweighted: there is no value to print
    # in the mark. So the edges are bare {from, to} dicts with no dataLabels of their own.
    df = pd.DataFrame({"src": ["A", "B"], "dst": ["B", "C"]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert opts["plotOptions"]["networkgraph"]["dataLabels"] == {"enabled": True}
    assert all("dataLabels" not in edge for edge in opts["series"][0]["data"])
    # Each label dict is copied off the module constant, so nothing can mutate it downstream.
    assert (
        opts["plotOptions"]["networkgraph"]["dataLabels"]
        is not build_options(df, "networkgraph", "src", [], target_col="dst")[
            "plotOptions"
        ]["networkgraph"]["dataLabels"]
    )


def test_networkgraph_light_mode_shape():
    # The light-mode choices nothing else guards: the disabled legend (nodes are labelled on the
    # chart), and — deliberately — NO custom tooltip at all. A networkgraph tooltip fires on a
    # NODE, whose point has no fromNode/toNode, so a "name the edge" pointFormat would render an
    # empty box on every node hover; and the node-specific nodeFormat that would fix it is silently
    # dropped (sankey's trap). Highcharts' own default prints the node name and is the only way to
    # get it, so the branch sets no tooltip — and in light mode (where _themed is a no-op) the
    # options carry none at all.
    df = pd.DataFrame({"src": ["A"], "dst": ["B"]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert opts["legend"]["enabled"] is False
    # No CUSTOM tooltip — which was always the claim; the key exists now only because
    # `_themed` writes chrome into it for every chart, so the absence to assert is the
    # FORMAT, not the key.
    assert "pointFormat" not in opts["tooltip"]
    assert "headerFormat" not in opts["tooltip"]
    # Light mode injects no dark chrome anywhere.
    assert "borderColor" not in opts["plotOptions"]["networkgraph"]


def test_networkgraph_dark_mode_themes_only_the_shared_chrome():
    # Networkgraph needs NO type-specific _themed hook (like boxplot, and for a kindred
    # reason): its node labels ride Highcharts' `contrast` color (white on dark, black on
    # light — verified by rendering), its nodes carry palette hues, and its links use a grey
    # legible on both backgrounds. So dark mode sets the shared chrome (background, tooltip)
    # and touches plotOptions.networkgraph not at all.
    df = pd.DataFrame({"src": ["A"], "dst": ["B"]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["tooltip"]["backgroundColor"] == "#0f172a"
    # No border/color flip and no dataLabels color — the plotOptions block is untouched by dark.
    assert "borderColor" not in opts["plotOptions"]["networkgraph"]
    assert "color" not in opts["plotOptions"]["networkgraph"]["dataLabels"]
    # No axes to theme; the axis loop must skip it, not crash.
    assert "xAxis" not in opts and "yAxis" not in opts


def test_networkgraph_numeric_node_labels_coerce_to_strings():
    # Both node columns are stringified — highcharts-core's point model rejects a non-string
    # node name — exactly as sankey's are. A user picking numeric ids gets named nodes, not a
    # blank chart.
    df = pd.DataFrame({"src": [1, 2], "dst": [10, 20]})
    opts = build_options(df, "networkgraph", "src", [], target_col="dst")
    assert opts["series"][0]["data"] == [
        {"from": "1", "to": "10"},
        {"from": "2", "to": "20"},
    ]


def test_networkgraph_count_marks_counts_drawable_edges():
    # Its marks are the edges: one per row with BOTH ends present, no value consulted (the
    # type is unweighted). The KPI's "Links" reads this. A row missing either node drops.
    df = pd.DataFrame({"src": ["A", None, "C", "D"], "dst": ["B", "Y", None, "E"]})
    assert count_marks(df, "networkgraph", "src", [], target_col="dst") == 2


# --------------------------------------------------------------------------- #
# Organization (a titled reporting hierarchy — the fourth node-link type). Its
# data is one row per PERSON (employee, manager, title); the manager is the far
# end of the reporting link, so the link is {from: manager, to: employee}, a
# blank manager is a ROOT, and the title rides a modeled `nodes` array. Unweighted
# like networkgraph (empty y_cols); the one node-link type with a `title_col`.
# --------------------------------------------------------------------------- #
def test_organization_builds_links_and_nodes():
    # The core shape: one row per PERSON becomes a {from: manager, to: employee} link (SWAPPED —
    # the tree flows down from a manager, which Highcharts draws as `from`), plus a `nodes` array
    # carrying each person's job title. Drawn top-down (chart.inverted). Ada has a blank manager, so
    # she is the ROOT: no incoming link, but a titled node that Bo and Cy hang off.
    df = pd.DataFrame(
        {
            "emp": ["Ada", "Bo", "Cy"],
            "mgr": ["", "Ada", "Ada"],
            "title": ["CEO", "VP", "VP"],
        }
    )
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["chart"]["type"] == "organization"
    assert opts["chart"]["inverted"] is True  # top-down, the conventional org chart
    assert opts["series"][0]["data"] == [
        {"from": "Ada", "to": "Bo"},
        {"from": "Ada", "to": "Cy"},
    ]
    assert opts["series"][0]["nodes"] == [
        {"id": "Ada", "name": "Ada", "title": "CEO"},
        {"id": "Bo", "name": "Bo", "title": "VP"},
        {"id": "Cy", "name": "Cy", "title": "VP"},
    ]
    assert "xAxis" not in opts and "yAxis" not in opts  # a node diagram, no axes
    assert "colorAxis" not in opts


def test_organization_builds_with_empty_y_cols():
    # The positive half of test_rejects_empty_y_cols' organization EXCLUSION: an org chart is
    # unweighted, so an empty y_cols is its normal state and must BUILD, not raise (networkgraph's
    # mirror, and gauge's with a None x_col).
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "title": ["CEO", "CTO"]})
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["series"][0]["data"] == [{"from": "A", "to": "B"}]


def test_organization_ignores_any_y_cols_it_is_given():
    # Unweighted: a y column passed through the pure API (the sweeps do this) changes nothing — the
    # links are identical with y_cols=["v"] and with []. The day organization reads y_cols, this
    # fails.
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "v": [9.0, 9.0]})
    with_y = build_options(df, "organization", "emp", ["v"], target_col="mgr")
    without_y = build_options(df, "organization", "emp", [], target_col="mgr")
    assert with_y["series"][0]["data"] == without_y["series"][0]["data"]


def test_organization_root_has_no_link_but_is_still_a_node():
    # A manager that is blank, whitespace or missing means a ROOT — `_is_top_level`, reused from
    # sunburst (a manager IS a parent). Such a row draws NO reporting link (unlike sankey, which
    # would drop it), but the person is still a node. This is why the build uses `not _is_top_level`
    # and NOT `_label_ok`: `_label_ok("")` is True, so a bare label check would draw a phantom link
    # from a nameless "" source node (the exact bug the render caught).
    df = pd.DataFrame(
        {
            "emp": ["CEO", "VP", "IC", "Solo"],
            "mgr": ["", "CEO", "VP", "   "],  # CEO blank + Solo whitespace = roots
            "title": ["Chief", "VP Eng", "Engineer", "Founder"],
        }
    )
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    links = opts["series"][0]["data"]
    assert links == [{"from": "CEO", "to": "VP"}, {"from": "VP", "to": "IC"}]
    assert all(
        link["from"].strip() for link in links
    )  # no blank/whitespace source node
    # Every titled person is still a node, roots included (CEO leads; Solo is an island).
    assert {n["id"] for n in opts["series"][0]["nodes"]} == {"CEO", "VP", "IC", "Solo"}


def test_organization_titles_ride_a_nodes_array_deduped():
    # Titles are the type's differentiator and the one thing highcharts-core lets an organization
    # keep (sankey/networkgraph drop a `nodes` array). One entry per titled person, deduped by node
    # key — a person named in several rows keeps the FIRST title. Without a title_col the series
    # carries no `nodes` at all (a plain name-box hierarchy, the render-verified path).
    df = pd.DataFrame(
        {
            "emp": ["Ann", "Bo", "Ann"],  # Ann appears twice
            "mgr": ["", "Ann", "Bo"],
            "title": ["CEO", "CTO", "Chair"],  # Ann's second title (Chair) is ignored
        }
    )
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["series"][0]["nodes"] == [
        {"id": "Ann", "name": "Ann", "title": "CEO"},  # first title wins
        {"id": "Bo", "name": "Bo", "title": "CTO"},
    ]
    plain = build_options(df, "organization", "emp", [], target_col="mgr")
    assert "nodes" not in plain["series"][0]  # no title column -> no nodes array


def test_organization_node_key_matches_integral_float_ids():
    # The sunburst int/float trap, one type over: a blank manager cell widens the manager column to
    # float64, so an integer employee id (int64) and its appearance as a manager (float64) must
    # still MATCH. `_node_key` renders an integral float as its integer, so `2` (an employee) and
    # `2.0` (a manager reference) are the SAME node — a bare str() would make "2" and "2.0" two
    # people and break the tree.
    df = pd.DataFrame({"emp": [1, 2, 3], "mgr": [None, 1, 2], "title": ["A", "B", "C"]})
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["series"][0]["data"] == [
        {"from": "1", "to": "2"},
        {"from": "2", "to": "3"},
    ]
    assert {n["id"] for n in opts["series"][0]["nodes"]} == {"1", "2", "3"}


def test_organization_requires_a_manager_column():
    # Every reporting link needs a manager end, so target_col is mandatory (a ValueError naming the
    # type) — the shared node-link guard.
    df = pd.DataFrame({"emp": ["A"], "mgr": ["B"]})
    with pytest.raises(ValueError, match="organization"):
        build_options(df, "organization", "emp", [])  # no target_col


def test_organization_rejects_employee_as_manager():
    # One column can't name both the employee and their manager — every person would report to
    # themselves. The shared node-link source-vs-target guard (a fact about the two node columns).
    df = pd.DataFrame({"emp": ["A", "B"]})
    with pytest.raises(ValueError):
        build_options(df, "organization", "emp", [], target_col="emp")


def test_organization_numeric_node_labels_coerce_to_strings():
    # Both node columns stringify via _node_key (highcharts-core rejects a non-string node name), so
    # numeric employee/manager ids get named boxes rather than a blank chart.
    df = pd.DataFrame({"emp": [10, 20], "mgr": [None, 10]})
    opts = build_options(df, "organization", "emp", [], target_col="mgr")
    assert opts["series"][0]["data"] == [{"from": "10", "to": "20"}]


def test_organization_serializes_and_pulls_in_sankey_and_organization_modules():
    # End to end, the type's headline serialization facts: an organization resolves
    # modules/organization.js AND modules/sankey.js — BOTH, from chart.type alone (organization
    # builds on sankey's diagram infrastructure, like the wheel) — and NOT highcharts-more (the
    # plausible guess the round-trip corrects). The node TITLE must reach the JS (highcharts-core
    # drops any key its point model doesn't model, and — unlike sankey/networkgraph — it DOES model
    # a node `title`). colorByPoint must appear NOWHERE: the palette cycles by Highcharts' own
    # default, and the builder sets no per-point color.
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "title": ["CEO", "CTO"]})
    chart = make_chart(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'organization'" in js
    assert "inverted: true" in js  # drawn top-down
    assert (
        "title: 'CTO'" in js
    )  # the node title survives serialization (org's differentiator)
    assert "colorByPoint" not in js
    tags = chart.get_script_tags(as_str=True)
    assert "modules/organization.js" in tags
    assert "modules/sankey.js" in tags  # organization builds on sankey's module
    assert "highcharts-more" not in tags  # the round-trip corrects the plausible guess


def test_organization_html_loads_sankey_before_organization():
    # THE interactive-mode regression pin, the dependency-wheel bug recurring: modules/
    # organization.js EXTENDS the sankey series, so it must load AFTER modules/sankey.js — but
    # get_script_tags emits them REVERSED (it walks plotOptions before series, so the dependent is
    # seen first). Loaded first, organization.js throws and Highcharts reports the series missing
    # (error #17), blanking the iframe while the export-server PNG renders fine. build_chart_html
    # fixes it via _order_script_tags (now a LIST of prerequisite/dependent pairs). Verified by
    # rendering in a real browser. Pin the ORDER in the emitted HTML, not just the presence.
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "title": ["CEO", "CTO"]})
    html = build_chart_html(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert "modules/sankey.js" in html and "modules/organization.js" in html
    assert html.index("modules/sankey.js") < html.index("modules/organization.js")


def test_order_script_tags_orders_organization_after_sankey():
    # The pure reorder for the SECOND dependent pair — the generalization of _order_script_tags from
    # one hardcoded pair to _MODULE_LOAD_ORDER. Given organization's tag ahead of sankey's
    # (get_script_tags' actual output), it moves the prerequisite in front, idempotently; and it
    # RAISES when the prerequisite is absent, exactly as it does for the wheel.
    from highcharts_builder import _order_script_tags

    reversed_tags = (
        '<script src="x/highcharts.js"></script>\n'
        '<script src="x/modules/organization.js"></script>\n'
        '<script src="x/modules/sankey.js"></script>'
    )
    out = _order_script_tags(reversed_tags).split("\n")
    assert "modules/sankey.js" in out[1]  # prerequisite moved ahead of the dependent
    assert "modules/organization.js" in out[2]
    assert _order_script_tags("\n".join(out)) == "\n".join(out)  # idempotent

    orphaned = (
        '<script src="x/highcharts.js"></script>\n'
        '<script src="x/modules/organization.js"></script>'  # no modules/sankey.js
    )
    with pytest.raises(ValueError, match="prerequisite"):
        _order_script_tags(orphaned)


def test_organization_light_mode_shape():
    # Light-mode choices nothing else guards: the legend is OFF (each node is labelled in its own
    # box), and the node tooltip lives under plotOptions[type].tooltip.nodeFormat (a top-level one
    # is silently dropped, sankey's trap). No `color` is set on the plotOptions — the palette cycles
    # by Highcharts' default (an explicit series color is OVERRIDDEN, verified by rendering) — and
    # in light mode _themed injects no dark chrome.
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "title": ["CEO", "CTO"]})
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["legend"]["enabled"] is False
    assert (
        opts["plotOptions"]["organization"]["tooltip"]["nodeFormat"] == "{point.name}"
    )
    assert "nodeFormat" not in opts.get(
        "tooltip", {}
    )  # not top-level, where it would vanish
    assert (
        "color" not in opts["plotOptions"]["organization"]
    )  # palette cycles by default
    assert "borderColor" not in opts["plotOptions"]["organization"]


def test_organization_dark_mode_needs_no_type_hook():
    # Organization needs NO type-specific _themed hook (like boxplot/networkgraph, and VERIFIED BY
    # RENDERING in both themes): its boxes carry no white border to dissolve, the name/title text
    # rides Highcharts' `contrast` color, and the palette hues and grey links read on either
    # background. So dark mode themes only the shared chrome (background/tooltip) and touches
    # plotOptions.organization not at all.
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "title": ["CEO", "CTO"]})
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["tooltip"]["backgroundColor"] == "#0f172a"
    assert "borderColor" not in opts["plotOptions"]["organization"]
    assert "color" not in opts["plotOptions"]["organization"]
    assert "xAxis" not in opts and "yAxis" not in opts


def test_organization_cycles_the_palette_across_nodes():
    # Unlike networkgraph's one-brand-hue mesh, an organization CYCLES the palette across nodes
    # (each box a distinct identity like a pie slice — Highcharts' default, verified by rendering).
    # So `colors` is carried and LOAD-BEARING, colorByPoint appears nowhere (the default does the
    # cycling), and no per-node `color` is set on the node entries.
    df = pd.DataFrame({"emp": ["A", "B"], "mgr": ["", "A"], "title": ["CEO", "CTO"]})
    opts = build_options(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    )
    assert opts["colors"] == list(DEFAULT_COLORS)
    js = make_chart(
        df, "organization", "emp", [], target_col="mgr", title_col="title"
    ).to_js_literal()
    assert js and "colorByPoint" not in js
    assert all("color" not in n for n in opts["series"][0]["nodes"])


def test_organization_count_marks_counts_reporting_lines():
    # Its marks (for the KPI) are the REPORTING LINES: one per employee with a real manager. A root
    # (blank/whitespace/missing manager) draws a box but no line, so it does NOT count — the count
    # uses `not _is_top_level`, matching the build, not `_label_ok` (which would overcount a blank
    # manager). "Reports" reads this.
    df = pd.DataFrame(
        {
            "emp": ["CEO", "A", "B", "C"],
            "mgr": [
                "",
                "CEO",
                "CEO",
                None,
            ],  # CEO blank root; C's manager missing = also a root
        }
    )
    assert count_marks(df, "organization", "emp", [], target_col="mgr") == 2


def test_organization_count_marks_matches_the_built_links():
    # The can't-drift invariant AS a test: count_marks and the build must agree on the SAME frame,
    # so a future edit to one and not the other is caught (count_marks runs on the RAW frame, the
    # build on the _label_ok-FILTERED one — they must still land on the same number). One frame with
    # every drop kind: a root (blank manager), a nameless employee, a missing manager, and two real
    # reports.
    df = pd.DataFrame(
        {
            "emp": ["CEO", "A", None, "B", "C"],
            "mgr": [
                "",
                "CEO",
                "CEO",
                None,
                "CEO",
            ],  # CEO=root; None-emp & None-mgr drop; A/C report
        }
    )
    links = build_options(df, "organization", "emp", [], target_col="mgr")["series"][0][
        "data"
    ]
    assert links == [{"from": "CEO", "to": "A"}, {"from": "CEO", "to": "C"}]
    assert count_marks(df, "organization", "emp", [], target_col="mgr") == len(links)


# --------------------------------------------------------------------------- #
# Boxplot (per-category Tukey distributions, aggregated from raw observations)
# --------------------------------------------------------------------------- #
def _boxes(opts) -> list:
    """The box series' data: one positional ``[low, q1, median, q3, high]`` 5-array (or
    ``EnforcedNull``) per category."""
    return opts["series"][0]["data"]


def test_boxplot_builds_boxes_over_categories():
    # Boxplot is the one type whose builder AGGREGATES: the frame is long/tidy (x_col
    # REPEATS, one row per observation) and each distinct x_col value becomes ONE box
    # over that group's raw y_cols[0] numbers. Points are positional 5-arrays matched to
    # xAxis.categories BY POSITION — not the {name, low, ...} dict form, which
    # highcharts-core collapses with the name in the leading x slot.
    df = pd.DataFrame(
        {"svc": ["a", "a", "a", "b", "b", "b"], "ms": [1.0, 2.0, 3.0, 5.0, 6.0, 7.0]}
    )
    opts = build_options(df, "boxplot", "svc", ["ms"])
    assert opts["chart"]["type"] == "boxplot"
    assert opts["xAxis"]["categories"] == ["a", "b"]
    assert opts["xAxis"]["title"]["text"] == "svc"
    assert opts["yAxis"]["title"]["text"] == "ms"
    assert opts["series"][0]["name"] == "ms"
    # [low, q1, median, q3, high] — pandas' default linear quantiles.
    assert _boxes(opts) == [
        [1.0, 1.5, 2.0, 2.5, 3.0],
        [5.0, 5.5, 6.0, 6.5, 7.0],
    ]
    # Boxes are colored categorically from the shared palette (like pie/treemap/sankey),
    # NOT by a colorAxis — so this is not a value-colored type (unlike heatmap).
    assert opts["plotOptions"]["boxplot"]["colorByPoint"] is True
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert "colorAxis" not in opts


def test_boxplot_tukey_outliers_become_a_linked_scatter_series():
    # Observations strictly beyond the 1.5 x IQR fences are drawn individually, as a
    # SECOND series linked to the boxes. The whiskers stop at the most extreme point
    # still inside the fence (13.0), never at the fence value itself.
    df = pd.DataFrame({"g": ["a"] * 5, "v": [10.0, 11.0, 12.0, 13.0, 100.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert _boxes(opts) == [
        [10.0, 11.0, 12.0, 13.0, 13.0]
    ]  # high is the whisker, not 100
    outliers = opts["series"][1]
    assert outliers["type"] == "scatter"
    assert outliers["linkedTo"] == ":previous"
    assert outliers["data"] == [[0, 100.0]]  # [category_index, value]
    # A fixed brand hue, read from DEFAULT_COLORS rather than the overridable `colors`
    # list (a short custom palette would IndexError), and never dark-flipped.
    assert outliers["marker"]["fillColor"] == DEFAULT_COLORS[3]


def test_boxplot_without_outliers_emits_a_single_series():
    # The linked scatter is emitted ONLY when there are outliers — an empty one would be
    # dead config (the restraint heatmap/sankey show in gating their labels on count).
    df = pd.DataFrame({"g": ["a"] * 4, "v": [10.0, 11.0, 12.0, 13.0]})
    assert len(build_options(df, "boxplot", "g", ["v"])["series"]) == 1


def test_boxplot_single_observation_group_is_a_flat_box():
    # n == 1: every quantile is that value, so iqr == 0 and the box is a flat line. This
    # is not a corner case to tolerate but the one the SUPPORTED_TYPES sweeps hit —
    # `labeled_frame` gives boxplot three groups of exactly one observation.
    df = pd.DataFrame({"g": ["a", "b"], "v": [7.0, 9.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert _boxes(opts) == [[7.0] * 5, [9.0] * 5]
    assert len(opts["series"]) == 1  # a flat box is not an outlier


def test_boxplot_two_observation_group_has_no_false_outliers():
    df = pd.DataFrame({"g": ["a", "a"], "v": [3.0, 9.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert _boxes(opts) == [[3.0, 4.5, 6.0, 7.5, 9.0]]
    assert len(opts["series"]) == 1


def test_boxplot_identical_observations_have_zero_iqr_and_no_outliers():
    # THE degenerate case. All values equal -> q1 == q3 -> iqr == 0 -> both fences
    # collapse onto that value. Because fence membership is INCLUSIVE (>=/<=), every
    # observation sits ON the fence and none is flagged. A strict (>/<) test would
    # classify the entire group as outliers — and would fail the sweeps above, which
    # feed boxplot single-observation groups.
    df = pd.DataFrame({"g": ["a"] * 4, "v": [5.0, 5.0, 5.0, 5.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert _boxes(opts) == [[5.0] * 5]
    assert len(opts["series"]) == 1


def test_boxplot_zero_iqr_with_genuine_tails_still_flags_them():
    # The other half of the iqr == 0 story: over half the mass on one value collapses the
    # fences, but the real tails ARE strictly beyond them, so they are correctly flagged.
    # The inclusive fence spares the 5s; it does not spare the 1 and the 9.
    df = pd.DataFrame({"g": ["a"] * 10, "v": [1.0] + [5.0] * 8 + [9.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert _boxes(opts) == [[5.0] * 5]
    assert opts["series"][1]["data"] == [[0, 1.0], [0, 9.0]]


def test_boxplot_whisker_includes_a_value_exactly_on_the_fence():
    # q1 == 4, q3 == 8, iqr == 4, so the lower fence lands exactly on -2. Inclusive
    # membership keeps it as the whisker end rather than exiling it as an outlier.
    df = pd.DataFrame({"g": ["a"] * 5, "v": [-2.0, 4.0, 6.0, 8.0, 10.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert _boxes(opts) == [[-2.0, 4.0, 6.0, 8.0, 10.0]]
    assert len(opts["series"]) == 1


def test_boxplot_whiskers_are_clamped_to_the_quartiles():
    # On a small, sharply skewed group the interpolated q1 can fall BELOW every
    # non-outlier observation: here q1 == 75 while the lowest in-fence point is 100. Left
    # alone, `low` would be 100 and the box's lower edge (75) would sit beneath its own
    # whisker. matplotlib clamps (`if np.min(wisklo) > q1: whislo = q1`) and so do we, so
    # low <= q1 <= median <= q3 <= high holds for every input. The 0 is still an outlier.
    df = pd.DataFrame({"g": ["a"] * 4, "v": [0.0, 100.0, 101.0, 102.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    low, q1, median, q3, high = _boxes(opts)[0]
    assert low == q1 == 75.0  # clamped, not 100.0
    assert [median, q3, high] == [100.5, 101.25, 102.0]
    assert low <= q1 <= median <= q3 <= high
    assert opts["series"][1]["data"] == [[0, 0.0]]


def test_boxplot_high_whisker_is_clamped_to_the_upper_quartile():
    # The mirror of the test above, and the reason the clamp is two-sided. Skew the group
    # the OTHER way and the interpolated q3 (27.0) rises above every non-outlier
    # observation (the largest is 2.0), so `high` must be clamped UP to q3 or the box's
    # upper edge would sit above its own whisker. Without this test the `max(..., q3)`
    # term is unexercised — the whole boxplot suite passes with it deleted.
    df = pd.DataFrame({"g": ["a"] * 4, "v": [0.0, 1.0, 2.0, 102.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    low, q1, median, q3, high = _boxes(opts)[0]
    assert high == q3 == 27.0  # clamped up, not the in-fence maximum of 2.0
    assert [low, q1, median] == [0.0, 0.75, 1.5]
    assert low <= q1 <= median <= q3 <= high
    assert opts["series"][1]["data"] == [[0, 102.0]]


def test_boxplot_non_finite_observations_are_dropped():
    # An infinity can't size a whisker, and left in it poisons the WHOLE box: the
    # quantiles go infinite, so iqr = inf - inf = nan, both fences are nan, every fence
    # comparison is false, and the five numbers all come back nan. Aggregation is what
    # makes this bite — a lone inf only spoils its own point in the pointwise branches.
    # So the non-finite values are dropped up front, exactly as NaN is.
    inf = float("inf")
    df = pd.DataFrame({"g": ["a"] * 4, "v": [1.0, 2.0, 3.0, inf]})
    assert _boxes(build_options(df, "boxplot", "g", ["v"]))[0] == [
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
    ]
    # Dropped, not flagged as an outlier — it can't be drawn at any coordinate.
    assert len(build_options(df, "boxplot", "g", ["v"])["series"]) == 1
    # Nothing finite left is just an empty group: keep the slot, like an all-NaN one.
    both = pd.DataFrame({"g": ["a", "a", "b", "b"], "v": [-inf, inf, 5.0, 7.0]})
    boxes = _boxes(build_options(both, "boxplot", "g", ["v"]))
    assert boxes[0] is EnforcedNull
    assert boxes[1] == [5.0, 5.5, 6.0, 6.5, 7.0]


def test_boxplot_finite_but_overflowing_group_becomes_enforced_null():
    # Dropping non-finite INPUTS is not enough for the one type that does arithmetic on
    # the values: a group of finite-but-huge numbers overflows during aggregation. With a
    # spread near the double range, iqr = q3 - q1 (and numpy's quantile interpolation,
    # a + (b - a) * frac) exceeds it and returns +/-inf, so a fence or the median itself
    # goes non-finite while the rest stay finite — smuggling the bare token `inf` past the
    # input guard and into the emitted JS (a blank iframe, a 400 from the export server).
    # The whole group is treated as unplottable, the same EnforcedNull box an all-missing
    # group gets. Reachable from a plain CSV: read_csv parses -9e307/9e307 as finite floats.
    big = 9e307  # finite (max double ~1.8e308), but 9e307 - (-9e307) overflows to inf
    df = pd.DataFrame({"g": ["a"] * 4, "v": [-big, -big, big, big]})
    boxes = _boxes(build_options(df, "boxplot", "g", ["v"]))
    assert boxes[0] is EnforcedNull
    # And it must not have leaked into the serialized JS (the sweep's non_finite_frame
    # only carries infinities in a value column that gets DROPPED, never this arithmetic
    # path, so it can't catch this — hence the direct assertion here).
    from highcharts_builder import make_chart

    js = make_chart(df, "boxplot", "g", ["v"]).to_js_literal()
    assert js and "inf" not in js


def test_boxplot_rejects_a_non_numeric_value_column():
    # The observations are cast to float64 before aggregating, so a text column raises
    # ValueError — the same contract the pointwise branches get for free from `float(v)`
    # (column/pie/scatter/treemap all raise it). Without the cast, `.quantile()` surfaces
    # an opaque dtype error from pandas' engine instead.
    df = pd.DataFrame({"g": ["a", "a"], "v": ["x", "y"]})
    with pytest.raises(ValueError):
        build_options(df, "boxplot", "g", ["v"])
    # A bool column still works, and means 1.0/0.0 — as `float(True)` does elsewhere.
    flags = pd.DataFrame({"g": ["a", "a"], "v": [True, False]})
    assert _boxes(build_options(flags, "boxplot", "g", ["v"]))[0] == [
        0.0,
        0.25,
        0.5,
        0.75,
        1.0,
    ]


def test_boxplot_all_missing_group_keeps_its_slot_as_enforced_null():
    # A group with no observations can't be summarized, but its category still exists, so
    # the slot is KEPT as EnforcedNull (heatmap's keep-the-axis-aligned rule, not pie's
    # drop-the-row one) — dropping it would slide every later box one place left. The
    # whole POINT is EnforcedNull; highcharts-core expands it to five nulls in the JS.
    from highcharts_builder import make_chart

    df = pd.DataFrame({"g": ["a", "a", "b", "b"], "v": [1.0, 2.0, float("nan"), None]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert opts["xAxis"]["categories"] == ["a", "b"]  # both slots kept
    boxes = _boxes(opts)
    assert boxes[0] == [1.0, 1.25, 1.5, 1.75, 2.0]
    assert boxes[1] is EnforcedNull  # missing box, not Python None or dropped
    js = make_chart(df, "boxplot", "g", ["v"]).to_js_literal()
    # A null closing the point array proves the EnforcedNull reached the data (Python
    # None would have been silently dropped) — as the heatmap null-cell test does.
    assert js and "null]" in js


def test_boxplot_missing_category_key_forms_no_group():
    # The other missing-data axis: a row whose x_col is NaN names no category at all, so
    # pandas' groupby(dropna=True) drops it. There is no slot to keep — unlike the
    # all-missing-observations group above, whose category the other rows still name.
    df = pd.DataFrame({"g": ["a", None, "b"], "v": [1.0, 2.0, 3.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert opts["xAxis"]["categories"] == ["a", "b"]
    assert len(_boxes(opts)) == 2


def test_boxplot_group_order_is_first_appearance():
    # groupby(sort=False): the boxes keep the frame's row order, the same fidelity every
    # other category-x type has (_category_labels never sorts). Sorted order would silently
    # reorder a user's meaningful sequence (Mon..Sun, or a funnel's stages).
    df = pd.DataFrame({"g": ["c", "a", "b", "a"], "v": [1.0, 2.0, 3.0, 4.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert opts["xAxis"]["categories"] == ["c", "a", "b"]


def test_boxplot_numeric_category_labels_coerce_to_strings():
    # The category-axis coercion, for the one type whose categories come from groupby keys
    # rather than _category_labels: highcharts-core rejects a non-string category
    # (CannotCoerceError on render), so a numeric grouping column must be stringified.
    df = pd.DataFrame({"yr": [2001, 2001, 2002], "v": [1.0, 2.0, 3.0]})
    assert build_options(df, "boxplot", "yr", ["v"])["xAxis"]["categories"] == [
        "2001",
        "2002",
    ]


def test_boxplot_uses_only_first_y_col():
    # Single-value like pie/treemap/sankey: only the first selected column is the
    # observations column (the app gives boxplot a single-select Y for exactly this).
    df = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 3.0], "v2": [9.0, 9.0]})
    opts = build_options(df, "boxplot", "g", ["v", "v2"])
    assert opts["series"][0]["name"] == "v"
    assert _boxes(opts) == [[1.0, 1.5, 2.0, 2.5, 3.0]]


def test_boxplot_rejects_x_in_y():
    # The X column groups the observations, so it can't also BE them: every box would hold
    # one observation equal to its own label. The category-x rule, widened to boxplot.
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    with pytest.raises(ValueError):
        build_options(df, "boxplot", "a", ["a"])


def test_boxplot_fill_color_is_accepted_then_silently_dropped():
    # THE boxplot trap, and the reason its box interior can't be themed at all. Both
    # `fillColor` and `stemColor` are read by BoxPlotOptions._get_kwargs_from_dict and
    # then never emitted by _to_untrimmed_dict, because the model has no such property —
    # so Chart.from_options ACCEPTS them and the JS silently lacks them. The same class of
    # trap as sankey's top-level tooltip.nodeFormat and treemap's "y"-instead-of-"value".
    # Only the serialized JS can prove it, so assert there. The fill therefore falls back
    # to Highcharts' `var(--highcharts-background-color)`, pinned to white by
    # _LIGHT_COLOR_SCHEME_CSS (see test_build_chart_html_pins_the_chart_color_scheme).
    # If a future highcharts-core starts honoring fillColor, this fails — and _themed
    # should then grow a boxplot hook that paints the interior with the theme.
    from highcharts_core.chart import Chart

    df = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    # We don't set it — precisely because it wouldn't work.
    assert "fillColor" not in opts["plotOptions"]["boxplot"]
    assert "stemColor" not in opts["plotOptions"]["boxplot"]
    opts["plotOptions"]["boxplot"]["fillColor"] = "#123456"
    opts["plotOptions"]["boxplot"]["stemColor"] = "#654321"
    js = Chart.from_options(opts).to_js_literal()
    assert js and "type: 'boxplot'" in js  # it built and serialized...
    assert "123456" not in js  # ...and swallowed both colors whole
    assert "654321" not in js


def test_boxplot_serializes_and_pulls_in_the_more_module():
    # End to end: the 5-array box shape and its linked outlier scatter must serialize AND
    # resolve highcharts-more — the module boxplot shares with bubble and radar, not a
    # modules/*.js of its own. Assert on the compacted JS: the box must reach the data as
    # a positional array, which is the whole reason we don't build {name, low, ...} dicts
    # (highcharts-core collapses those with the name in the leading x slot).
    from highcharts_builder import make_chart

    df = pd.DataFrame({"g": ["a"] * 5, "v": [10.0, 11.0, 12.0, 13.0, 100.0]})
    chart = make_chart(df, "boxplot", "g", ["v"])
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'boxplot'" in js
    compact = "".join(js.split())
    assert "[10.0,11.0,12.0,13.0,13.0]" in compact  # the 5-array, not a dict point
    assert "linkedTo:':previous'" in compact  # the outlier series survived
    assert "type:'scatter'" in compact
    tags = chart.get_script_tags(as_str=True)
    assert "highcharts-more" in tags  # bubble/radar's module, shared
    assert "modules/" not in tags  # boxplot has no module of its own


def test_boxplot_light_mode_shape():
    # Mirrors the treemap/sankey light-mode tests: pin the choices nothing else guards.
    # The tooltip lives under plotOptions.boxplot (scoping it to the boxes, so the linked
    # outlier scatter keeps Highcharts' own point tooltip) and RENAMES the caps —
    # Highcharts calls point.low/point.high "Minimum"/"Maximum", a lie once an outlier is
    # drawn as its own point. The legend is off: it would only repeat the y-axis title.
    df = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert opts["legend"]["enabled"] is False
    # No CUSTOM tooltip — which was always the claim; the key exists now only because
    # `_themed` writes chrome into it for every chart, so the absence to assert is the
    # FORMAT, not the key.
    assert "pointFormat" not in opts["tooltip"]
    assert "headerFormat" not in opts["tooltip"]
    box_opts = opts["plotOptions"]["boxplot"]
    assert set(box_opts) == {"colorByPoint", "tooltip"}
    fmt = box_opts["tooltip"]["pointFormat"]
    assert "Upper whisker" in fmt and "Lower whisker" in fmt  # not Maximum/Minimum
    assert "{point.q1}" in fmt and "{point.median}" in fmt and "{point.q3}" in fmt
    assert box_opts["tooltip"]["headerFormat"] == "<b>{point.key}</b><br/>"


def test_boxplot_dark_mode_needs_no_box_hook():
    # Boxplot is the one mark-styling type with NO branch in _themed. Its box interior is
    # unsettable (see the fillColor trap) and so stays white in both themes, while
    # colorByPoint draws the border, whisker, stem and median in a palette hue legible
    # against that white — so there is nothing left to flip. Only the generic chrome moves.
    df = pd.DataFrame({"g": ["a", "a"], "v": [1.0, 2.0]})
    opts = build_options(df, "boxplot", "g", ["v"])
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    assert opts["xAxis"]["labels"]["style"]["color"] == "#94a3b8"
    assert opts["yAxis"]["gridLineColor"] == "#334155"
    assert (
        opts["tooltip"]["backgroundColor"] == "#0f172a"
    )  # chrome _themed auto-creates
    # Untouched: no borderColor/fillColor/medianColor injected, unlike pie/treemap/sankey.
    assert set(opts["plotOptions"]["boxplot"]) == {"colorByPoint", "tooltip"}


# --------------------------------------------------------------------------- #
# waterfall (signed deltas floating at a running total)
# --------------------------------------------------------------------------- #
def _bridge() -> pd.DataFrame:
    """Four signed deltas — the mixed signs are the point of the type."""
    return pd.DataFrame(
        {
            "step": ["Revenue", "COGS", "Opex", "Tax"],
            "delta": [120.0, -45.0, -18.0, -7.0],
        }
    )


def test_waterfall_builds_steps_and_appends_a_total():
    # The frame carries only the DELTAS; the closing bar is the builder's, not the data's.
    # So the axis gains a category and the series a point that no row produced — waterfall
    # is the one type whose mark count exceeds its row count.
    opts = build_options(_bridge(), "waterfall", "step", ["delta"])
    assert opts["chart"]["type"] == "waterfall"
    assert opts["xAxis"]["categories"] == ["Revenue", "COGS", "Opex", "Tax", "Total"]
    data = opts["series"][0]["data"]
    assert data[:4] == [120.0, -45.0, -18.0, -7.0]  # positional, matched to categories
    # isSum makes Highcharts total the preceding deltas itself, so the bar reaches down to
    # zero as a LEVEL rather than stacking as one more delta. That IS the bridge.
    assert data[4]["isSum"] is True
    assert opts["series"][0]["name"] == "delta"
    assert opts["xAxis"]["title"]["text"] == "step"  # every category-x type pins this
    assert opts["yAxis"]["title"]["text"] == "delta"
    assert opts["legend"]["enabled"] is False


def test_waterfall_colors_rises_falls_and_the_total_by_meaning():
    # The bars are colored by MEANING, not identity: green up, red down, brand-blue total.
    opts = build_options(_bridge(), "waterfall", "step", ["delta"])
    wf = opts["plotOptions"]["waterfall"]
    assert wf["upColor"] == DEFAULT_COLORS[1]  # green: a rise
    assert wf["color"] == DEFAULT_COLORS[3]  # red: a fall
    assert opts["series"][0]["data"][4]["color"] == DEFAULT_COLORS[0]  # blue: the total


def test_waterfall_total_is_taken_off_the_up_down_color_scale():
    # Left alone, Highcharts colors the sum by ITS OWN SIGN, exactly as it colors a delta: a
    # positive total takes upColor (green), a negative one takes color (red). Verified by
    # rendering it. But green does not mean the same thing on the two kinds of bar — on a
    # delta it says "this step ADDED", while on the total it would say only "the end level is
    # above zero", which a bridge that fell 420 -> 79 would also earn. So the total is taken
    # off the up/down scale and marked as the different KIND of bar it is: a LEVEL, not a
    # change. Pin the per-point color on the emitted JS — unlike boxplot's fillColor
    # (accepted, then silently dropped), a point color does survive.
    from highcharts_builder import make_chart

    js = make_chart(_bridge(), "waterfall", "step", ["delta"]).to_js_literal()
    assert js  # stubbed str | None
    compact = "".join(js.split())
    assert f"isSum:true,color:'{DEFAULT_COLORS[0]}'" in compact
    # The total's hue must be neither of the two the deltas use, or it rejoins the very scale
    # this takes it off. (_bridge() sums to +50, so without the override it would be green.)
    assert DEFAULT_COLORS[0] not in (DEFAULT_COLORS[1], DEFAULT_COLORS[3])


def test_waterfall_semantic_colors_ignore_a_custom_palette():
    # `colors` overrides the series palette, but must NOT repaint the bars: red-means-loss
    # is the chart's semantics, not a series' arbitrary identity, so a custom palette can't
    # turn a fall green. The _BOXPLOT_OUTLIER_COLOR rule — and it also means a caller's
    # SHORT palette (two entries here, where the hues index up to 3) can't IndexError.
    opts = build_options(
        _bridge(), "waterfall", "step", ["delta"], colors=["#000000", "#ffffff"]
    )
    assert opts["colors"] == ["#000000", "#ffffff"]  # carried, as heatmap carries it
    wf = opts["plotOptions"]["waterfall"]
    assert wf["upColor"] == DEFAULT_COLORS[1] and wf["color"] == DEFAULT_COLORS[3]
    assert opts["series"][0]["data"][-1]["color"] == DEFAULT_COLORS[0]


def test_waterfall_missing_delta_keeps_its_slot_as_enforced_null():
    # A missing/non-finite delta KEEPS its slot (the `_num` cartesian rule), rather than
    # dropping its row as pie and treemap do. Semantics, not just shape: a null delta means
    # "no change", so Highcharts draws no bar and carries the running total straight through
    # — true. Dropping the row would delete a step from the bridge without saying so.
    df = pd.DataFrame(
        {
            "step": ["a", "b", "c", "d"],
            "delta": [1.0, float("nan"), float("inf"), 4.0],
        }
    )
    opts = build_options(df, "waterfall", "step", ["delta"])
    data = opts["series"][0]["data"]
    assert data[1] is EnforcedNull and data[2] is EnforcedNull  # inf is missing too
    assert opts["xAxis"]["categories"] == [
        "a",
        "b",
        "c",
        "d",
        "Total",
    ]  # nothing shifted
    # And the null must REACH the JS — a Python None would be dropped and misalign the bars.
    from highcharts_builder import make_chart

    js = make_chart(df, "waterfall", "step", ["delta"]).to_js_literal()
    # not a bare "null", which other keys could satisfy
    assert js and "null]" in js  # stubbed str | None


def test_waterfall_with_no_drawable_steps_appends_no_total():
    # A lone "Total: 0" bar is not a chart — the restraint boxplot shows in omitting an
    # empty outlier series, and sankey/heatmap in gating their labels on count.
    from highcharts_builder import count_marks

    df = pd.DataFrame({"step": [float("nan")], "delta": [1.0]})
    opts = build_options(df, "waterfall", "step", ["delta"])
    assert opts["series"][0]["data"] == []
    assert opts["xAxis"]["categories"] == []
    # And the KPI must agree with the empty chart. This is the ONLY test that reaches
    # count_marks' zero-step branch: without it, `return steps + 1` (dropping the `if steps`
    # guard entirely) passes the whole suite while the app reports "Steps: 1" over a chart
    # with no bars at all.
    assert count_marks(df, "waterfall", "step", ["delta"]) == 0


def test_waterfall_labels_each_bar_with_its_delta():
    # The value is printed IN the bar, as pie/heatmap/treemap/sankey print theirs, so the
    # Static-PNG mode (which has no hover tooltip) still shows the numbers. This is where
    # waterfall parts from column/bar, which carry no labels: their bars stand ON the axis,
    # so a height is a value — while a waterfall's bar floats at the running total and
    # encodes its value as a LENGTH, which no axis can be read against.
    opts = build_options(_bridge(), "waterfall", "step", ["delta"])
    labels = opts["plotOptions"]["waterfall"]["dataLabels"]
    assert labels["enabled"] is True
    assert labels["format"] == "{point.y}"
    assert (
        labels["inside"] is True
    )  # on the bar, where "contrast" is computed vs the fill
    assert labels["color"] == "contrast"
    # The outline is what keeps "contrast" legible where a label straddles a bar's edge. It
    # comes from the shared _in_mark_labels helper (with heatmap's cells and treemap's
    # tiles), so pin it here too — otherwise dropping it from that helper breaks three types
    # and no waterfall test notices.
    assert labels["style"]["textOutline"] == "1px contrast"
    assert labels["color"] == "contrast"


def test_waterfall_many_steps_omit_the_value_labels():
    # Above the gate the labels overprint into noise (the heatmap/sankey rule). The count
    # includes the appended total, which is drawn and labelled like any other bar.
    from highcharts_builder import _WATERFALL_DATALABEL_MAX_STEPS

    n = _WATERFALL_DATALABEL_MAX_STEPS  # n steps + 1 total = one over the gate
    df = pd.DataFrame({"step": [str(i) for i in range(n)], "delta": [1.0] * n})
    opts = build_options(df, "waterfall", "step", ["delta"])
    assert len(opts["series"][0]["data"]) == n + 1
    assert "dataLabels" not in opts["plotOptions"]["waterfall"]
    # One fewer step and they come back, so the boundary is pinned, not just the far side.
    smaller = df.iloc[:-1]
    assert (
        "dataLabels"
        in build_options(smaller, "waterfall", "step", ["delta"])["plotOptions"][
            "waterfall"
        ]
    )


def test_waterfall_tooltip_names_the_category_not_the_point():
    # {point.name} would render BLANK: the points are positional, their names living in
    # xAxis.categories. {point.category} is what reads them back — bubble's non-numeric-x
    # tooltip resolves the same way, for the same reason.
    opts = build_options(_bridge(), "waterfall", "step", ["delta"])
    fmt = opts["tooltip"]["pointFormat"]
    assert "{point.category}" in fmt
    assert "{point.name}" not in fmt
    assert "{point.y}" in fmt  # on the appended bar this is the summed total
    # The empty header suppresses Highcharts' default header row, which would repeat the
    # category the pointFormat already names (treemap and sankey suppress theirs the same
    # way). Pinned, or dropping it silently restores the duplicate.
    assert opts["tooltip"]["headerFormat"] == ""


def test_waterfall_uses_only_first_y_col():
    df = _bridge()
    df["other"] = [9.0, 9.0, 9.0, 9.0]
    opts = build_options(df, "waterfall", "step", ["delta", "other"])
    assert len(opts["series"]) == 1
    assert opts["series"][0]["name"] == "delta"


def test_waterfall_rejects_x_in_y():
    # Its x_col is a category axis, so it joins X_IN_Y_GUARD_TYPES (with heatmap/boxplot).
    with pytest.raises(ValueError, match="cannot also be a y series"):
        build_options(_bridge(), "waterfall", "step", ["step"])


def test_waterfall_numeric_step_labels_coerce_to_strings():
    df = pd.DataFrame({"step": [1, 2], "delta": [1.0, -1.0]})
    opts = build_options(df, "waterfall", "step", ["delta"])
    assert opts["xAxis"]["categories"] == ["1", "2", "Total"]


def test_waterfall_serializes_and_pulls_in_the_more_module():
    # End to end: isSum must survive the point model (highcharts-core accepts plenty it then
    # silently drops — boxplot's fillColor, sankey's nodeFormat), and the module must resolve
    # to highcharts-more, which waterfall shares with bubble, radar and boxplot rather than
    # having a modules/*.js of its own.
    from highcharts_builder import make_chart

    chart = make_chart(_bridge(), "waterfall", "step", ["delta"])
    js = chart.to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "type: 'waterfall'" in js
    compact = "".join(js.split())
    assert "isSum:true" in compact  # the sum point survived
    assert f"upColor:'{DEFAULT_COLORS[1]}'" in compact  # so did the semantic hues
    assert "inside:true" in compact  # and the in-bar labels
    tags = chart.get_script_tags(as_str=True)
    assert "highcharts-more" in tags  # bubble/radar/boxplot's module, shared
    assert "modules/" not in tags  # waterfall has no module of its own


def test_waterfall_light_mode_shape():
    # Mirrors the treemap/sankey/boxplot light-mode tests: pin the choices nothing else
    # guards, and prove the dark-only keys are absent (so the dark test below is meaningful).
    opts = build_options(_bridge(), "waterfall", "step", ["delta"])
    assert opts["legend"]["enabled"] is False
    wf = opts["plotOptions"]["waterfall"]
    # Both of the theme's waterfall writes are here: the dissolved bar border AND the
    # connector lineColor, which is the pair test_waterfall_dark_mode_themes_the_bars_and_
    # the_connectors reads by value.
    assert set(wf) == {"upColor", "color", "dataLabels", "borderColor", "lineColor"}


def test_waterfall_dark_mode_themes_the_bars_and_the_connectors():
    # TWO flips, and neither is column/bar's. Waterfall's bar border and its connector lines
    # BOTH default to a fixed #333333 (measured off the rendered PNG on either background),
    # not to the background variable that resolves to white for column/bar — so the bars are
    # never ringed white, and these flips are not that bug. The border, a crisp definition
    # line on the white shell, becomes a muddy grey ring one shade off the dark background,
    # and buys nothing (waterfall's bars never touch), so it is dissolved into the background
    # as pie/treemap/sankey dissolve their gaps. The CONNECTOR lines — what make a waterfall
    # read as a running total rather than a row of floating bars — survive on the dark
    # background only barely, so they are lifted to the axis color. That half is waterfall's
    # alone: it is the only line Highcharts draws BETWEEN marks.
    opts = build_options(_bridge(), "waterfall", "step", ["delta"])
    wf = opts["plotOptions"]["waterfall"]
    assert wf["borderColor"] == "#0f172a"  # == _DARK_CHROME["bg"]
    assert wf["lineColor"] == "#475569"  # == _DARK_CHROME["axis"]
    # The bar hues are NOT flipped: like the shared series palette, they read on both
    # backgrounds, and their meaning is fixed.
    assert wf["upColor"] == DEFAULT_COLORS[1] and wf["color"] == DEFAULT_COLORS[3]
    assert opts["chart"]["backgroundColor"] == "#0f172a"


# --------------------------------------------------------------------------- #
# Sunburst — a hierarchy read from an adjacency list
# --------------------------------------------------------------------------- #
def _tree() -> pd.DataFrame:
    """Two branches over four leaves, three levels deep counting the synthesized root.

    "Other" appears TWICE, under two different parents — the case a label-keyed node
    identity would silently merge (and which Highcharts rejects outright, as error #31).
    Nothing NAMES "Other" as a parent, so it is not ambiguous, just repeated.
    """
    return pd.DataFrame(
        {
            "node": ["EMEA", "APAC", "UK", "Other", "Japan", "Other"],
            "parent": [None, None, "EMEA", "EMEA", "APAC", "APAC"],
            "value": [None, None, 500.0, 100.0, 380.0, 40.0],
        }
    )


def _sun(df=None, **kw):
    return build_options(
        df if df is not None else _tree(),
        "sunburst",
        "node",
        ["value"],
        parent_col="parent",
        **kw,
    )


def _points(opts) -> list[dict]:
    return opts["series"][0]["data"]


def test_sunburst_builds_nodes_and_appends_a_root():
    points = _points(_sun())
    assert len(points) == 7  # 6 rows + the appended root
    root = points[-1]  # APPENDED, so the real nodes keep their row positions
    assert root["id"] == "__root__" and root["name"] == "All"
    # The root carries NO value: it is internal by construction, so Highcharts sums the whole
    # tree into it and the centre reads a total the builder never computed.
    assert "value" not in root
    assert [p["name"] for p in points[:-1]] == [
        "EMEA",
        "APAC",
        "UK",
        "Other",
        "Japan",
        "Other",
    ]


def test_sunburst_ids_are_synthesized_never_the_labels():
    # THE identity decision. Highcharts links parent -> child by `id`, and a duplicate id is
    # not a silent mismatch but error #31 ("Non-unique point or node id"), printed in a red
    # band across the chart. Synthesizing ids from the row position makes that unreachable: a
    # CSV label lands only in `name`, so nothing in a hostile file can collide with anything.
    points = _points(_sun())
    ids = [p["id"] for p in points]
    assert len(ids) == len(set(ids))  # the invariant error #31 exists to enforce
    assert ids == ["n0", "n1", "n2", "n3", "n4", "n5", "__root__"]
    assert not any(p["id"] == p["name"] for p in points[:-1])


def test_sunburst_duplicate_labels_under_different_parents_stay_distinct_sectors():
    # The pay-off of synthesized ids, and the reason label-as-id was rejected. Two teams named
    # "Other" are two honest sectors worth 100 and 40 — NOT one merged sector worth 140 hanging
    # under whichever parent won. Identity is the ROW, exactly as it is for treemap.
    others = [p for p in _points(_sun()) if p["name"] == "Other"]
    assert len(others) == 2
    assert {p["id"] for p in others} == {"n3", "n5"}
    assert sorted(p["value"] for p in others) == [40.0, 100.0]  # not merged into 140
    assert {p["parent"] for p in others} == {"n0", "n1"}  # under EMEA and APAC


def test_sunburst_a_duplicate_label_used_as_a_parent_raises():
    # A duplicate label is only a CONTRADICTION once something points at it: `parent = "dup"`
    # then names no single node. The alternatives are both silent lies — merge the twins, or
    # pick one and graft a subtree onto the wrong branch — so it raises, sankey's rule.
    df = pd.DataFrame(
        {
            "node": ["dup", "dup", "child"],
            "parent": [None, None, "dup"],
            "value": [None, 1.0, 2.0],
        }
    )
    with pytest.raises(ValueError, match="must name exactly one"):
        _sun(df)


def test_sunburst_internal_nodes_carry_no_value_and_leaves_always_do():
    # The invariant. Highcharts resolves a node's size as its own value IF GIVEN, else the sum
    # of its children — so an explicit parent value OVERRIDES the sum, and a subtotal row would
    # draw a parent whose arc disagrees with the arcs inside it (verified by rendering: two
    # branches declaring value=1 drew as equal halves while holding 900 and 100). Omitting it
    # makes a parent's arc always equal what is actually drawn under it.
    for point in _points(_sun()):
        is_leaf = point["name"] in ("UK", "Other", "Japan")
        assert ("value" in point) is is_leaf, point


def test_sunburst_an_internal_nodes_stated_value_is_ignored():
    # ...and it is ignored even when the CSV states one, which is the case that matters: a
    # subtotal row is an extremely common export. The number is discarded, not honored.
    df = _tree()
    df.loc[0, "value"] = 999.0  # EMEA claims 999; its children hold 600
    emea = next(p for p in _points(_sun(df)) if p["name"] == "EMEA")
    assert "value" not in emea


def test_sunburst_ring_one_is_seeded_from_the_palette_and_descendants_inherit():
    # The canonical Highcharts recipe — levels[].colorByPoint — is accepted by
    # Chart.from_options and then SILENTLY DROPPED (the treemap "value not y" trap), and the
    # colorByPoint that does survive is the series-wide one, which would hand every point its
    # own hue and destroy the inheritance. So ring 1 is seeded per POINT and everything below
    # it carries no color at all, inheriting its branch's (verified by rendering).
    points = _points(_sun())
    seeded = {p["name"]: p["color"] for p in points if "color" in p}
    assert seeded["EMEA"] == DEFAULT_COLORS[0]
    assert seeded["APAC"] == DEFAULT_COLORS[1]
    for point in points:
        if point["name"] not in ("EMEA", "APAC", "All"):
            assert "color" not in point, (
                f"{point['name']} must inherit, not carry, a hue"
            )


def test_sunburst_ring_one_takes_a_custom_palette_and_a_short_one_cycles():
    # Unlike waterfall's semantic red-means-loss, a branch's hue is its arbitrary IDENTITY —
    # like a pie slice's — so a caller MAY repaint it. A one-color palette must cycle rather
    # than IndexError (the _BOXPLOT_OUTLIER_COLOR concern).
    points = _points(_sun(colors=["#111111"]))
    seeded = [p["color"] for p in points if p["name"] in ("EMEA", "APAC")]
    assert seeded == ["#111111", "#111111"]


def test_sunburst_root_color_is_off_the_categorical_scale():
    # Waterfall's Total argument, transposed. There the scale was up/down and blue sat off it;
    # here the scale is the WHOLE palette, which ring 1 CYCLES — so no palette entry is
    # guaranteed not to be some branch's hue, and the only way to say "this is not a category,
    # it is the whole" is a color from outside the palette. Read straight from the constant, so
    # a custom palette cannot repaint the root as one more branch.
    #
    # This is the test that FIRED when DEFAULT_COLORS was repointed at the config theme's
    # chartCategoricalColors: the old slate-400 root was index 6 of the new palette, so the
    # "not a category" grey had quietly become a category. The constant moved to slate-500.
    # Since DEFAULT_COLORS is now itself pinned to config.toml, this assertion reaches the
    # THEME — a future palette containing the root hue fails here rather than on screen.
    root = _points(_sun())[-1]
    assert root["color"] == "#64748b"
    assert root["color"] not in DEFAULT_COLORS
    # ...and a custom palette does NOT reach it, though it does reach ring 1 above.
    assert _points(_sun(colors=["#111111", "#222222"]))[-1]["color"] == "#64748b"


def test_sunburst_levels_add_an_alternating_color_variation_below_ring_one():
    # Ring 1 (level 2) gets no entry — it is seeded per point. Every ring below needs a
    # colorVariation or a branch's descendants, which inherit its hue, would be
    # indistinguishable. The SIGN alternates because the variation applies to the parent's
    # already-varied color: a fixed -0.5 walks a deep tree to black.
    levels = _sun()["plotOptions"]["sunburst"]["levels"]
    assert levels[0] == {"level": 1, "levelSize": {"unit": "percentage", "value": 15}}
    assert levels[1] == {
        "level": 3,
        "colorVariation": {"key": "brightness", "to": -0.5},
    }
    assert not any(entry["level"] == 2 for entry in levels)
    # A deeper tree keeps going, and flips the sign at each ring.
    deep = pd.DataFrame(
        {
            "node": ["a", "b", "c", "d"],
            "parent": [None, "a", "b", "c"],
            "value": [None, None, None, 1.0],
        }
    )
    deep_levels = _sun(deep)["plotOptions"]["sunburst"]["levels"]
    assert [entry["level"] for entry in deep_levels] == [1, 3, 4, 5]
    assert [entry["colorVariation"]["to"] for entry in deep_levels[1:]] == [
        -0.5,
        0.5,
        -0.5,
    ]


def test_sunburst_a_two_ring_tree_needs_no_color_variation():
    # Root + one ring: nothing to vary, so only the levelSize entry is emitted (the
    # dead-config restraint the heatmap/sankey label gates show).
    flat = pd.DataFrame(
        {"node": ["a", "b"], "parent": [None, None], "value": [1.0, 2.0]}
    )
    levels = _sun(flat)["plotOptions"]["sunburst"]["levels"]
    assert levels == [{"level": 1, "levelSize": {"unit": "percentage", "value": 15}}]


def test_sunburst_dangling_parent_drops_the_row_and_its_descendants():
    # A parent naming no node is MISSING DATA, so its row is dropped — treemap's rule. And the
    # drop must be TRANSITIVE: Highcharts does not leave an unmatched parent alone, it silently
    # RE-PARENTS the child to the root, which would promote an orphaned grandchild into ring 1
    # and lie about the data. Here "b" dangles and "c" hangs off "b", so both go — and "a",
    # left with no children and no value of its own, goes too.
    df = pd.DataFrame(
        {
            "node": ["a", "b", "c", "keep"],
            "parent": [None, "ATLANTIS", "b", None],
            "value": [None, 1.0, 2.0, 7.0],
        }
    )
    assert [p["name"] for p in _points(_sun(df))] == ["keep", "All"]


def test_sunburst_a_cycle_raises():
    # A cycle is not missing data, it is a CONTRADICTION — there is no right drawing of it —
    # so it raises rather than dropping, mirroring sankey's x_col == target_col guard. The
    # message names the loop so the user can find it.
    two = pd.DataFrame({"node": ["a", "b"], "parent": ["b", "a"], "value": [1.0, 2.0]})
    with pytest.raises(ValueError, match=r"'a' → 'b' → 'a' is a cycle"):
        _sun(two)
    # The degenerate one-node cycle: a node that is its own parent. Same guard, same message.
    self_parent = pd.DataFrame({"node": ["a"], "parent": ["a"], "value": [1.0]})
    with pytest.raises(ValueError, match=r"'a' → 'a' is a cycle"):
        _sun(self_parent)


def test_sunburst_a_forest_with_no_top_level_node_is_a_cycle():
    # Each node has exactly one parent, so the parent map is a FUNCTION: if no node is
    # top-level and every parent resolves, following parents from anywhere must revisit a node
    # within N steps. "No roots" therefore *implies* a cycle — it is not a separate case.
    df = pd.DataFrame(
        {"node": ["a", "b", "c"], "parent": ["c", "a", "b"], "value": [1.0, 2.0, 3.0]}
    )
    with pytest.raises(ValueError, match="is a cycle"):
        _sun(df)


def test_sunburst_a_dangling_row_does_not_hide_a_cycle():
    # Order-independence, stated as a test. No node in a cycle can ever be dangling (every
    # cycle node's parent is the next cycle node, which exists), so dropping a dangling row can
    # never break one — the walk raises regardless of which it meets first.
    df = pd.DataFrame(
        {
            "node": ["orphan", "a", "b"],
            "parent": ["ATLANTIS", "b", "a"],
            "value": [1.0, 2.0, 3.0],
        }
    )
    with pytest.raises(ValueError, match="is a cycle"):
        _sun(df)


def test_sunburst_a_long_cycle_and_a_deep_chain_survive_without_recursion():
    # Both are reachable from a plain CSV and both would blow a recursive walk's stack, so the
    # walk is iterative. The cycle raises; the chain builds.
    n = 5000
    cycle = pd.DataFrame(
        {
            "node": [str(i) for i in range(n)],
            "parent": [str((i - 1) % n) for i in range(n)],
            "value": [1.0] * n,
        }
    )
    with pytest.raises(ValueError, match="is a cycle"):
        _sun(cycle)
    chain = pd.DataFrame(
        {
            "node": [str(i) for i in range(n)],
            "parent": [None, *(str(i - 1) for i in range(1, n))],
            "value": [None] * (n - 1) + [1.0],  # only the deepest node is a leaf
        }
    )
    assert len(_points(_sun(chain))) == n + 1  # every node, plus the root


def test_sunburst_a_long_cycle_message_is_truncated():
    # A 10,000-node cycle must not print a 10,000-node message — but the loop must still
    # visibly CLOSE, so the final label is always kept.
    n = 50
    df = pd.DataFrame(
        {
            "node": [str(i) for i in range(n)],
            "parent": [str((i - 1) % n) for i in range(n)],
            "value": [1.0] * n,
        }
    )
    with pytest.raises(ValueError) as excinfo:
        _sun(df)
    message = str(excinfo.value)
    assert "..." in message and message.count("→") <= 8


def test_sunburst_a_missing_non_finite_or_negative_leaf_value_drops_the_row():
    # A leaf's value must be able to SIZE AN ARC. A negative one cannot: Highcharts draws no
    # sector for it AND excludes it from its parent's sum (verified by rendering — a -400 leaf
    # beside a 500 one drew nothing and left its parent sized 500, not 100), so keeping the row
    # would make count_marks report a mark the chart never draws. Zero is KEPT: it is a real
    # measurement, it draws a zero-width sector, and it corrupts no sum — pie's and treemap's
    # rule for their own zeros.
    df = pd.DataFrame(
        {
            "node": ["root", "gone_nan", "gone_inf", "gone_neg", "kept_zero", "kept"],
            "parent": [None, "root", "root", "root", "root", "root"],
            "value": [None, float("nan"), float("inf"), -400.0, 0.0, 500.0],
        }
    )
    names = [p["name"] for p in _points(_sun(df))]
    assert names == ["root", "kept_zero", "kept", "All"]


def test_sunburst_a_parent_left_childless_becomes_a_leaf():
    # Not a special case — the rule itself: keep(n) = its value can size an arc, OR something
    # under it survived. So a node whose only child was dropped BECOMES a leaf, and then its
    # own value is what sizes it. (And when it has none, it is dropped in turn.)
    df = pd.DataFrame(
        {
            "node": ["has_own", "doomed_child", "has_none", "doomed_child2"],
            "parent": [None, "has_own", None, "has_none"],
            "value": [42.0, float("nan"), None, float("nan")],
        }
    )
    points = _points(_sun(df))
    assert [p["name"] for p in points] == ["has_own", "All"]
    assert points[0]["value"] == 42.0  # promoted to a leaf, sized by its own value


def test_sunburst_a_blank_missing_or_whitespace_parent_is_a_top_level_branch():
    # The ONE place in the module where a missing label is a STATEMENT, not an error:
    # everywhere else `_label_ok` False means "drop the row", here it means "hang off the
    # root". A whitespace-only string is folded in — read as a label it would match no node,
    # dangle, and drop the row: the silently wrong answer where "top-level" is the right one.
    df = pd.DataFrame(
        {
            "node": ["a", "b", "c", "d"],
            "parent": [None, "", "   ", float("nan")],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )
    points = _points(_sun(df))
    assert len(points) == 5  # all four, plus the root
    assert all(p["parent"] == "__root__" for p in points[:-1])
    # ...and all four are ring-1 branches, so all four are seeded from the palette.
    assert [p["color"] for p in points[:-1]] == list(DEFAULT_COLORS[:4])


def test_sunburst_a_numeric_node_column_matches_a_float_parent_column():
    # The `_node_key` trap, and the most canonical adjacency CSV there is. A blank parent cell
    # WIDENS that column to float64, so `node` comes in as int64 and `parent` as float64 —
    # and a bare str() would stringify the same node to "1" on one side and "1.0" on the
    # other. Every parent would dangle, every row would drop, and the chart would come out
    # SILENTLY EMPTY.
    df = pd.DataFrame(
        {"node": [1, 2, 3], "parent": [None, 1, 1], "value": [None, 10.0, 20.0]}
    )
    assert str(df["node"].dtype) == "int64" and str(df["parent"].dtype) == "float64"
    points = _points(_sun(df))
    assert [p["name"] for p in points] == ["1", "2", "3", "All"]
    assert points[1]["parent"] == points[0]["id"]  # "2" really did attach to "1"


def test_sunburst_a_node_labelled_like_the_root_does_not_collide():
    # Ids are synthesized, so CSV text never becomes one and a node literally named "__root__"
    # is just a node. A node named "All" is a cosmetic name clash on screen — exactly as a
    # waterfall step named "Total" is — not a broken tree.
    df = pd.DataFrame(
        {
            "node": ["__root__", "All"],
            "parent": [None, None],
            "value": [1.0, 2.0],
        }
    )
    points = _points(_sun(df))
    assert [p["id"] for p in points] == ["n0", "n1", "__root__"]
    assert points[0]["name"] == "__root__" and points[0]["id"] != "__root__"


def test_sunburst_with_no_drawable_nodes_appends_no_root():
    # A lone slate disc labelled "All" is not a chart — waterfall's no-lone-Total restraint,
    # and boxplot's in omitting an empty outlier series. Pins the `if points` guard.
    df = pd.DataFrame({"node": ["a"], "parent": [None], "value": [float("nan")]})
    assert _points(_sun(df)) == []
    from highcharts_builder import count_marks

    assert count_marks(df, "sunburst", "node", ["value"], parent_col="parent") == 0


def test_sunburst_labels_each_sector_with_its_name_only():
    # The one type that does NOT print its value in the mark, and the geometry is why: a sector
    # is a thin CURVED arc with the text bent along it, so there is room for one short string —
    # and the name is the only thing identifying a sector (a sunburst has neither axis nor
    # legend), while the value is already encoded as the ANGLE.
    labels = _sun()["plotOptions"]["sunburst"]["dataLabels"]
    assert labels["enabled"] is True
    assert labels["format"] == "{point.name}"
    assert labels["rotationMode"] == "circular"
    assert (
        labels["color"] == "contrast"
    )  # computed against the sector fill (treemap's rule)


def test_sunburst_many_sectors_omit_the_labels():
    # The heatmap-cell / sankey-link / waterfall-step gate. Unlike those, a sunburst's
    # dataLabels default to ON, so past the gate they must be turned off EXPLICITLY —
    # omitting the key would be a gate that did nothing.
    n = 70
    df = pd.DataFrame(
        {
            "node": [str(i) for i in range(n)],
            "parent": [None] * n,
            "value": [1.0] * n,
        }
    )
    assert _sun(df)["plotOptions"]["sunburst"]["dataLabels"] == {"enabled": False}
    # ...and just under the gate they are drawn (both sides of the boundary).
    n = 59  # 59 nodes + the root == 60, the limit
    under = pd.DataFrame(
        {
            "node": [str(i) for i in range(n)],
            "parent": [None] * n,
            "value": [1.0] * n,
        }
    )
    assert _sun(under)["plotOptions"]["sunburst"]["dataLabels"]["enabled"] is True


def test_sunburst_tooltip_names_the_point_not_the_category():
    # {point.name}, not waterfall's {point.category}: sunburst's points are NAMED dicts rather
    # than positional ones. On the appended root {point.value} is the grand total Highcharts
    # summed, which is exactly what it should read.
    tooltip = _sun()["tooltip"]
    assert tooltip["headerFormat"] == ""
    assert tooltip["pointFormat"] == "{point.name}: <b>{point.value}</b>"


def test_sunburst_uses_only_first_y_col():
    df = _tree()
    df["ignored"] = [9.0] * 6
    assert _sun(df)["series"][0]["name"] == "value"


def test_sunburst_requires_a_parent_column():
    with pytest.raises(ValueError, match="requires a parent column"):
        build_options(_tree(), "sunburst", "node", ["value"])


def test_sunburst_rejects_x_col_as_the_parent_column():
    # Every row would name itself as its own parent. The tree walk WOULD catch it, but with a
    # mystifying "'EMEA' → 'EMEA' is a cycle" when the real fault is that one column was picked
    # twice — sankey's source-is-target argument.
    with pytest.raises(ValueError, match="cannot also be the parent column"):
        build_options(_tree(), "sunburst", "node", ["value"], parent_col="node")


def test_sunburst_allows_x_in_y():
    # Deliberately NOT in X_IN_Y_GUARD_TYPES: its x_col is a node LABEL, not a category axis,
    # and its own collision is node-vs-parent (which parent_col guards). x-in-y merely names
    # every node by its own value — odd, well-defined, drawable. The scatter/sankey tolerance,
    # third instance.
    df = pd.DataFrame({"node": [1.0, 2.0], "parent": [None, 1.0]})
    points = _points(
        build_options(df, "sunburst", "node", ["node"], parent_col="parent")
    )
    assert [p["name"] for p in points] == ["1", "2", "All"]
    assert (
        points[1]["value"] == 2.0
    )  # the leaf is sized by the very column that names it


def test_sunburst_explain_tree_error_returns_the_message_build_options_raises():
    # The app renders this instead of letting the builder raise (the interactive path does not
    # catch), so the two MUST be the same string — the X_IN_Y_GUARD_TYPES named-once rule.
    from highcharts_builder import explain_tree_error

    cyclic = pd.DataFrame(
        {"node": ["a", "b"], "parent": ["b", "a"], "value": [1.0, 2.0]}
    )
    problem = explain_tree_error(cyclic, "node", "parent", "value")
    assert problem is not None
    with pytest.raises(ValueError) as excinfo:
        _sun(cyclic)
    assert str(excinfo.value) == problem
    # ...and None for a tree that is fine, which is what lets the app fall through.
    assert explain_tree_error(_tree(), "node", "parent", "value") is None


def test_sunburst_rejects_a_non_numeric_value_column():
    # `_sizable` is evaluated for EVERY node, internal ones included, so a text column raises
    # uniformly rather than raising or not depending on the tree's shape — boxplot's contract.
    df = pd.DataFrame({"node": ["a", "b"], "parent": [None, "a"], "value": ["x", "y"]})
    with pytest.raises(ValueError):
        _sun(df)


def test_sunburst_serializes_and_resolves_the_sunburst_module():
    # The only test that can see the traps: highcharts-core accepts several of these keys and
    # then silently drops them, so only the emitted JS proves they survived.
    from highcharts_builder import make_chart

    chart = make_chart(_tree(), "sunburst", "node", ["value"], parent_col="parent")
    js = chart.to_js_literal()
    assert js
    for token in ("type: 'sunburst'", "allowTraversingTree", "colorVariation", "id:"):
        assert token in js, f"{token} did not survive serialization"
    # colorByPoint must appear NOWHERE. In `levels` it is silently DROPPED (the canonical
    # Highcharts recipe, and useless to us); at series level it SURVIVES but is the wrong
    # option — it would hand every point its own hue and destroy the inheritance. Pinned like
    # sankey's nodeFormat and boxplot's fillColor. `allowDrillToNode` is the dropped alias.
    assert "colorByPoint" not in js and "allowDrillToNode" not in js
    # The module is resolved by highcharts-core itself, from the options shape — nothing in
    # this repo registers it, so only this can prove it. And sunburst needs no highcharts-more.
    tags = chart.get_script_tags(as_str=True)
    assert "modules/sunburst.js" in tags
    assert "highcharts-more" not in tags


def test_sunburst_light_mode_shape():
    # Pin the choices nothing else guards, and prove the dark-only key is absent (so the dark
    # test below is meaningful).
    opts = _sun()
    assert opts["legend"]["enabled"] is False
    sb = opts["plotOptions"]["sunburst"]
    assert set(sb) == {
        "allowTraversingTree",
        "cursor",
        "levels",
        "dataLabels",
        "borderColor",
    }


def test_sunburst_dark_mode_dissolves_the_sector_borders():
    # Sector borders default to the background variable, which the color-scheme pin holds at
    # WHITE in both themes — so in dark mode every sector is ringed white (verified by
    # rendering). Dissolve them into the dark background, as pie, treemap and sankey dissolve
    # their gaps. Nothing else flips: the labels ride `contrast` and the hues read on both.
    opts = _sun()
    sb = opts["plotOptions"]["sunburst"]
    assert sb["borderColor"] == "#0f172a"  # == _DARK_CHROME["bg"]
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    points = _points(opts)
    assert points[0]["color"] == DEFAULT_COLORS[0]  # ring-1 hues unchanged
    assert points[-1]["color"] == "#64748b"  # ...and the root's


# --------------------------------------------------------------------------- #
# Xrange — a Gantt timeline: bars with EXTENT along x, on lanes down the y axis
# --------------------------------------------------------------------------- #
def _plan() -> pd.DataFrame:
    """Two lanes, one of them holding TWO bars (so the per-lane hue has something to prove),
    plus a milestone. Dates as ISO-8601 STRINGS — an object column, which is what read_csv
    hands back and what `_coordinates` must sniff."""
    return pd.DataFrame(
        {
            "lane": ["Design", "Build", "Build", "Launch"],
            "start": ["2026-01-05", "2026-02-01", "2026-04-01", "2026-06-01"],
            "end": ["2026-02-10", "2026-03-20", "2026-04-20", "2026-06-01"],
        }
    )


def _xr(df: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_options(
        df if df is not None else _plan(),
        "xrange",
        "lane",
        ["start"],
        end_col="end",
        **kwargs,
    )


def _bars(opts: dict) -> list[dict]:
    return opts["series"][0]["data"]


def test_xrange_builds_one_bar_per_row_on_lanes_down_the_y_axis():
    opts = _xr()
    assert opts["chart"]["type"] == "xrange"
    # Lanes are the categories of the Y axis (x_col is NOT an x axis here), in
    # first-appearance order, deduplicated — "Build" holds two bars but is one lane.
    assert opts["yAxis"]["categories"] == ["Design", "Build", "Launch"]
    # A Gantt reads DOWN the page in plan order; Highcharts' own default runs bottom-up.
    assert opts["yAxis"]["reversed"] is True
    # Highcharts titles a category y-axis "Values" unless explicitly CLEARED (None does not
    # do it — verified by rendering); a lane is a name, not a value.
    assert opts["yAxis"]["title"]["text"] == ""
    bars = _bars(opts)
    assert len(bars) == 4
    # `y` is a POSITION into `categories`, not a value — boxplot's positional trick.
    assert [b["y"] for b in bars] == [0, 1, 1, 2]
    assert [b["name"] for b in bars] == ["Design", "Build", "Build", "Launch"]


def test_xrange_iso_date_strings_become_a_datetime_axis_in_epoch_millis():
    # THE EPOCH PIN, and it guards a regression that is silent and catastrophic. Pandas 3
    # returns `datetime64[us]` from to_datetime (NOT the `[ns]` that the obvious
    # `.astype("int64") // 1_000_000` assumes), so that divisor renders 2026-01-05 as
    # 1970-01-16: every bar in the correct RELATIVE order at hopelessly wrong ABSOLUTE dates,
    # drawn confidently, with no error anywhere. `_epoch_millis` normalizes the unit BEFORE
    # taking the int64 view, which is why this number is exact.
    opts = _xr()
    assert opts["xAxis"]["type"] == "datetime"
    bars = _bars(opts)
    assert bars[0]["x"] == 1767571200000.0  # 2026-01-05T00:00:00Z, to the millisecond
    assert bars[0]["x2"] == 1770681600000.0  # 2026-02-10
    assert pd.to_datetime(bars[0]["x"], unit="ms").date() == date(2026, 1, 5)


@pytest.mark.parametrize(
    "make",
    [
        pytest.param(lambda s: pd.Series(s, dtype=object), id="iso_strings"),
        pytest.param(lambda s: pd.to_datetime(pd.Series(s)), id="datetime64_us"),
        pytest.param(
            lambda s: pd.to_datetime(pd.Series(s)).astype("datetime64[s]"), id="dt64_s"
        ),
        pytest.param(
            lambda s: pd.to_datetime(pd.Series(s)).dt.tz_localize("America/New_York"),
            id="tz_aware",
        ),
    ],
)
def test_xrange_epoch_millis_are_resolution_independent(make):
    # The same instant must serialize to the same millis whatever RESOLUTION or timezone the
    # column arrives in — object strings, datetime64[us] (to_datetime's answer), datetime64[s]
    # (read_csv's), or a tz-aware column (an ISO CSV carrying an offset, which would raise
    # outright without the UTC conversion). A hardcoded divisor is right for exactly one of
    # these and wrong by 1e3 or 1e6 for the others.
    df = pd.DataFrame(
        {
            "lane": ["a"],
            "start": make(["2026-01-05"]),
            "end": make(["2026-02-10"]),
        }
    )
    bars = _bars(_xr(df))
    # tz-aware New York is UTC-5 in January, so its midnight is 05:00Z — the same INSTANT,
    # correctly shifted to UTC, not the same wall clock reinterpreted.
    tz_aware = isinstance(df["start"].dtype, pd.DatetimeTZDtype)
    offset = 5 * 3600 * 1000 if tz_aware else 0
    assert bars[0]["x"] == 1767571200000.0 + offset


def test_xrange_numbers_stay_numbers_and_get_no_datetime_axis():
    # THE EPOCH TRAP, mirrored — and the reason `_coordinates` is dtype-FIRST. Bare
    # `pd.to_datetime(12)` does not fail; it returns 1970-01-01T00:00:00.000000012. So a
    # "try dates, fall back to numbers" sniff would silently move a column of sprint numbers
    # to an instant at the epoch. A numeric dtype is never shown to a date parser at all.
    df = pd.DataFrame({"lane": ["a", "b"], "start": [12, 20], "end": [18, 24]})
    opts = _xr(df)
    assert "type" not in opts["xAxis"]  # a linear axis, not a datetime one
    bars = _bars(opts)
    assert [(b["x"], b["x2"]) for b in bars] == [(12.0, 18.0), (20.0, 24.0)]


@pytest.mark.parametrize(
    ("values", "kind"),
    [
        # Numeral STRINGS are numbers, not dates: ISO-8601 rejects "12", so no bespoke regex
        # is needed to keep them out of the date branch.
        (["12", "18"], "number"),
        (["2026-01-05", "2026-02-10"], "date"),
        # A DST-crossing column: `errors="coerce"` alone RAISES "Mixed timezones detected" on
        # this (verified), which would be a traceback in count_marks — hence `utc=True`.
        (["2026-03-06T12:00:00-05:00", "2026-03-10T12:00:00-04:00"], "date"),
    ],
)
def test_coordinates_sniffs_a_column_kind(values, kind):
    from highcharts_builder import _coordinates

    assert _coordinates(pd.Series(values))[1] == kind


@pytest.mark.parametrize(
    "values",
    [
        # THE LANDING-SAMPLE TRAP. Bare `pd.to_datetime(["Jan","Feb"])` SUCCEEDS, returning
        # YEAR 1 AD (verified) — and this is `_revenue_vs_cost`'s `month` column, the first
        # entry in SAMPLES and so the app's landing dataset. A permissive sniff would offer it
        # as a date axis on the page you see when you open the app. `format="ISO8601"` is what
        # rejects it.
        ["Jan", "Feb", "Mar"],
        [
            "00:00",
            "01:00",
        ],  # ...and these parse to TODAY'S DATE under the default parser
        ["Engineering", "Design"],
        ["13/01/2026", "14/01/2026"],  # a real date, but not ISO-8601
    ],
)
def test_coordinates_rejects_a_column_that_is_neither_dates_nor_numbers(values):
    from highcharts_builder import _COORD_NEITHER, _coordinates

    assert _coordinates(pd.Series(values))[1] == _COORD_NEITHER


@pytest.mark.parametrize(
    ("values", "kind"),
    [
        # A MIXED object column is decided by MAJORITY — a column is one kind or the other,
        # and a few stray cells of the other kind are typos, not a second axis. The losers
        # coerce to NaN and drop their rows as missing data.
        (["2026-01-05", "2026-02-01", "12"], "date"),  # 2 dates beat 1 number
        (["2026-01-05", "12", "13"], "number"),  # 2 numbers beat 1 date
        # A TIE goes to NUMBER (a strict `>`), and that is the safe way to break it: a date
        # read as a number leaves a visibly missing bar, while a number read as a date would
        # silently place it at the epoch — the failure this function's whole ordering exists
        # to prevent.
        (["2026-01-05", "12"], "number"),
    ],
)
def test_coordinates_breaks_a_mixed_column_by_majority_and_a_tie_toward_number(
    values, kind
):
    from highcharts_builder import _coordinates

    assert _coordinates(pd.Series(values))[1] == kind


@pytest.mark.parametrize(
    ("values", "kind"),
    [
        # Dtypes a real CSV or a hand-built frame can arrive as, none of which may raise or
        # mis-sniff. An all-missing column is "empty" — NOT the kind its dtype suggests, which
        # is the trap: an all-NaT column is still datetime64 and an all-NaN one is still
        # float64, so a dtype-only answer would have them claiming an axis they know nothing
        # about (see the empty-column test below).
        (pd.Series([12, 18], dtype="Int64"), "number"),  # pandas nullable
        (pd.Series(["2026-01-05"], dtype="string[pyarrow]"), "date"),  # arrow-backed
        (pd.Series([pd.NaT, pd.NaT], dtype="datetime64[ns]"), "empty"),
        (pd.Series([None, None], dtype=object), "empty"),
        (pd.Series([], dtype=float), "empty"),  # a row-less frame's column
    ],
)
def test_coordinates_survives_the_dtypes_a_real_frame_arrives_as(values, kind):
    from highcharts_builder import _coordinates

    assert _coordinates(values)[1] == kind


@pytest.mark.parametrize(
    "blank",
    [
        pytest.param(lambda n: [None] * n, id="all_none"),
        pytest.param(lambda n: [float("nan")] * n, id="all_nan_float64"),
        pytest.param(
            lambda n: pd.Series([pd.NaT] * n, dtype="datetime64[ns]"), id="all_nat"
        ),
    ],
)
def test_xrange_an_empty_coordinate_column_is_missing_data_not_a_contradiction(blank):
    # An unfilled column is MISSING DATA — every row drops, the chart comes out empty — and it
    # must not be mistaken for a KIND. The tempting shortcut folds "nothing present" into
    # `_COORD_NUMBER`, and it is tempting precisely because it looks true: a blank CSV column
    # arrives as all-NaN float64, so `is_numeric_dtype` says "number" with total confidence.
    # That phantom number then collides with a real DATE partner and raises the axis-mismatch
    # message — telling the user their empty End column "reads as numbers", which is both FALSE
    # and unactionable.
    #
    # And it is not a corner case: this is a Gantt template whose end dates nobody has filled in
    # yet, straight out of read_csv. The bug was also ASYMMETRIC — an empty column beside a
    # NUMERIC partner agreed by coincidence and worked — so only the date case, the type's
    # headline use, was broken.
    for start, end in (
        (["2026-01-05", "2026-02-01"], blank(2)),  # blank END beside a date start
        (blank(2), ["2026-01-05", "2026-02-01"]),  # ...and the mirror
        (blank(2), blank(2)),  # both
    ):
        df = pd.DataFrame({"lane": ["a", "b"], "start": start, "end": end})
        opts = _xr(df)
        assert _bars(opts) == []  # every row dropped, as missing data
        assert count_marks(df, "xrange", "lane", ["start"], end_col="end") == 0
        assert (
            explain_xrange_error(df, "lane", "start", "end") is None
        )  # NOT a contradiction


def test_xrange_an_empty_column_does_not_hide_a_real_axis_mismatch():
    # The other side of the fix: an empty column abstains from the vote, it does not veto it.
    # Two columns that genuinely disagree must still raise.
    df = pd.DataFrame({"lane": ["a"], "start": ["2026-01-05"], "end": [7]})
    with pytest.raises(ValueError, match="must be the same kind"):
        build_options(df, "xrange", "lane", ["start"], end_col="end")


def test_xrange_epoch_millis_span_dates_outside_the_nanosecond_range():
    # `datetime64[ns]` overflows outside 1677..2262, which is why `_epoch_millis` pins the
    # unit to [ms] rather than leaning on to_datetime's default: a medieval start date and a
    # far-future end date must both survive, not raise.
    df = pd.DataFrame({"lane": ["a"], "start": ["1400-01-01"], "end": ["2300-01-01"]})
    bars = _bars(_xr(df))
    assert len(bars) == 1
    assert bars[0]["x"] < 0 < bars[0]["x2"]  # before and after the epoch


def test_xrange_builds_under_warnings_as_errors():
    # Pins `format="ISO8601"` from the other side: the bare `pd.to_datetime` this replaced
    # emits a format-inference UserWarning on every object column, which under `-W error`
    # (or a stricter CI) would fail. The only way this assertion is observable.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert len(_bars(_xr())) == 4
        assert count_marks(_plan(), "xrange", "lane", ["start"], end_col="end") == 4


def test_xrange_keeps_a_zero_length_bar_as_a_milestone_and_floors_it():
    # A launch date / deadline / same-day task — one of the commonest Gantt rows. Highcharts
    # draws NOTHING for it unaided (verified by rendering: x == x2 left an empty lane), so
    # without a floor it would be a mark the KPI counts and the chart never draws. `_sizable`
    # keeps its zero for the same kind of reason; here the floor is what makes keeping it
    # honest, and it must survive serialization (this repo has been bitten three times by
    # options that validate and then silently vanish).
    opts = _xr()
    launch = _bars(opts)[-1]
    assert launch["name"] == "Launch" and launch["x"] == launch["x2"]
    assert opts["plotOptions"]["xrange"]["minPointLength"] == 3
    js = make_chart(_plan(), "xrange", "lane", ["start"], end_col="end").to_js_literal()
    assert js and "minPointLength" in js


def test_xrange_drops_a_backwards_bar():
    # An interval that ends before it begins. Left in, Highcharts draws a bar spanning the
    # ENTIRE axis (verified by rendering) — not a visible error but a confident, plausible lie
    # that reads as the longest task in the project. It is the xrange counterpart of
    # sunburst's silent re-parenting, and it DROPS rather than raises for `_sizable`'s reason:
    # there is a right drawing (nothing), unlike a cycle, where every alternative is a lie.
    df = pd.DataFrame(
        {
            "lane": ["ok", "backwards"],
            "start": ["2026-02-01", "2026-05-01"],
            "end": ["2026-03-01", "2026-01-01"],
        }
    )
    opts = _xr(df)
    assert [b["name"] for b in _bars(opts)] == ["ok"]
    # ...and the lane it would have occupied is gone from the axis entirely. A lane holds
    # 0..n bars, so unlike a boxplot group (which IS its mark, and survives as an
    # EnforcedNull box) there is nothing to null out: an empty labelled axis row is exactly
    # the phantom this drop exists to prevent.
    assert opts["yAxis"]["categories"] == ["ok"]
    assert count_marks(df, "xrange", "lane", ["start"], end_col="end") == 1


def test_xrange_drops_a_non_finite_start_or_end():
    # `end >= start` ALONE is not enough, and this is the hole it leaves: `10 > -inf` is True,
    # so a -inf start (reachable from a plain CSV via `1e400`) would sail through and put the
    # bare token `inf` in the emitted JS — the ReferenceError / HTTP-400 the whole non-finite
    # doctrine exists to prevent. Both ends must be `_plottable` BEFORE they are compared.
    # The END channel is the one `non_finite_frame` cannot reach (an infinite end would drop
    # its only surviving row), so it is covered here.
    inf = float("inf")
    df = pd.DataFrame(
        {
            "lane": ["neg_inf_start", "pos_inf_end", "nan_start", "ok"],
            "start": [-inf, 1.0, float("nan"), 5.0],
            "end": [10.0, inf, 4.0, 9.0],
        }
    )
    opts = _xr(df)
    assert [b["name"] for b in _bars(opts)] == ["ok"]
    js = make_chart(df, "xrange", "lane", ["start"], end_col="end").to_js_literal()
    assert js and "inf" not in js.lower()


def test_xrange_drops_an_unparseable_date_cell_but_keeps_the_column():
    # One typo must not condemn the column. An unparseable cell coerces to NaT -> NaN, which
    # is missing DATA and drops its row — while a column where NOTHING parses is a column of
    # the wrong KIND and is a contradiction (see the raise tests below). That is
    # `_sunburst_tree`'s split, applied to a coordinate column.
    df = pd.DataFrame(
        {
            "lane": ["ok", "typo"],
            "start": ["2026-01-05", "2026-13-45"],
            "end": ["2026-02-10", "2026-03-01"],
        }
    )
    opts = _xr(df)
    assert opts["xAxis"]["type"] == "datetime"  # still a date column
    assert [b["name"] for b in _bars(opts)] == ["ok"]


def test_spannable_decides_the_four_boundary_pairs():
    from highcharts_builder import _spannable

    assert _spannable(1.0, 2.0)  # a real bar
    assert _spannable(2.0, 2.0)  # a milestone: KEPT (floored to a sliver)
    assert not _spannable(2.0, 1.0)  # backwards: dropped
    assert not _spannable(float("-inf"), 10.0)  # the finiteness hole
    assert not _spannable(10.0, float("inf"))
    assert not _spannable(float("nan"), 1.0)


def test_xrange_colors_every_bar_in_a_lane_alike_and_never_uses_color_by_point():
    # A lane's hue is its arbitrary IDENTITY, like a pie slice's — the opposite of waterfall's
    # semantic red-means-loss — so it reads from the OVERRIDABLE palette. It must be seeded
    # per POINT, and here the trap is the mirror of sunburst's: where sunburst's
    # `levels[].colorByPoint` is silently DROPPED, xrange's series-level one SURVIVES — and is
    # the wrong option. It would hand every BAR its own hue, so Build's two phases would come
    # out two colors and the lane would stop reading as one thing.
    bars = _bars(_xr())
    design, build_a, build_b, launch = bars
    assert build_a["color"] == build_b["color"]  # one lane, one hue
    assert design["color"] == DEFAULT_COLORS[0]
    assert build_a["color"] == DEFAULT_COLORS[1]
    assert launch["color"] == DEFAULT_COLORS[2]
    js = make_chart(_plan(), "xrange", "lane", ["start"], end_col="end").to_js_literal()
    assert js and "colorByPoint" not in js


def test_xrange_takes_a_custom_palette_and_a_short_one_cycles():
    # A short custom palette must not IndexError (the `_BOXPLOT_OUTLIER_COLOR` concern) — three
    # lanes over a two-color palette wrap back to the first.
    bars = _bars(_xr(colors=["#111111", "#222222"]))
    assert [b["color"] for b in bars] == ["#111111", "#222222", "#222222", "#111111"]


def test_xrange_tooltip_names_the_point_and_formats_the_dates():
    # {point.name}, NOT waterfall's {point.category}. This is not a stylistic echo: it is
    # waterfall's FIX and xrange's BUG. {point.category} reads the X axis, and an xrange's
    # categories are on the Y, so it renders the raw x value — a tooltip reading
    # "1767571200000" (verified by rendering). And a datetime axis must FORMAT its endpoints,
    # or they print as raw epoch millis too.
    tip = _xr()["tooltip"]["pointFormat"]
    assert "{point.name}" in tip and "{point.category}" not in tip
    assert "{point.x:%Y-%m-%d}" in tip and "{point.x2:%Y-%m-%d}" in tip
    # A numeric axis has no dates to format, so it prints the bare coordinates.
    numeric = pd.DataFrame({"lane": ["a"], "start": [12], "end": [18]})
    assert (
        _xr(numeric)["tooltip"]["pointFormat"]
        == "<b>{point.name}</b><br/>{point.x} → {point.x2}"
    )


def test_xrange_carries_no_data_labels():
    # The one mark-bearing type that prints nothing in the mark, and needs no gate constant
    # either. The five that DO print a value in the mark do it because the value can be read
    # against no axis (an angle, an area, a link's width, a bar floating above an invisible
    # running total). An xrange bar's two ends BOTH land on a real, ticked x axis that renders
    # in the Static PNG too — column/bar's case. And there is no second identity to print: the
    # lane name IS the y-axis category (labelling the bar just repeats it — verified by
    # rendering).
    assert "dataLabels" not in _xr()["plotOptions"]["xrange"]


def test_xrange_requires_an_end_column():
    with pytest.raises(ValueError, match="requires an end column"):
        build_options(_plan(), "xrange", "lane", ["start"])


def test_xrange_rejects_the_start_column_as_the_end_column():
    # A bar's two ends, like sankey's source/target and sunburst's node/parent. It must be a
    # guard rather than a tolerated oddity because it fails SILENTLY: every bar would be
    # zero-length, so the chart would come back as a column of milestone slivers.
    with pytest.raises(ValueError, match="cannot also be the end column"):
        build_options(_plan(), "xrange", "lane", ["start"], end_col="start")


def test_xrange_allows_x_in_y():
    # x_col IS free to repeat a coordinate column: the lanes are then named by their own start
    # number — odd, well-defined, drawable. Scatter's x-in-y tolerance, and the reason xrange
    # stays OUT of X_IN_Y_GUARD_TYPES (its x_col names a lane on the Y axis, and end_col isn't
    # in y_cols at all, so that rule cannot even express xrange's real collision).
    df = pd.DataFrame({"start": [1.0, 2.0], "end": [5.0, 6.0]})
    opts = build_options(df, "xrange", "start", ["start"], end_col="end")
    assert opts["yAxis"]["categories"] == ["1", "2"]  # _node_key: "1", not "1.0"


@pytest.mark.parametrize(
    ("start", "end", "match"),
    [
        ("lane", "end", "neither dates nor numbers"),  # a column of task names
        ("start", "lane", "neither dates nor numbers"),
    ],
)
def test_xrange_a_non_coordinate_column_raises(start, end, match):
    with pytest.raises(ValueError, match=match):
        build_options(_plan(), "xrange", "lane", [start], end_col=end)


def test_xrange_a_date_start_beside_a_numeric_end_raises():
    # Both ends of a bar sit on ONE axis, so they must be the same kind. A contradiction with
    # no right drawing — a returned message, raised here.
    df = _plan().assign(sprint=[1, 2, 3, 4])
    with pytest.raises(ValueError, match="must be the same kind"):
        build_options(df, "xrange", "lane", ["start"], end_col="sprint")


@pytest.mark.parametrize("end", ["lane", "sprint"])
def test_xrange_explain_returns_the_message_build_options_raises(end):
    # The `explain_tree_error` contract: the builder owns the coordinate relationship, so it
    # owns the diagnosis, and the app's warning cannot drift from the exception it stands in
    # for. Needed because the interactive path does NOT catch builder errors — and picking a
    # text column for Start, or a date Start beside a numeric End, is reachable through the
    # app's own pickers.
    from highcharts_builder import explain_xrange_error

    df = _plan().assign(sprint=[1, 2, 3, 4])
    problem = explain_xrange_error(df, "lane", "start", end)
    assert problem
    with pytest.raises(ValueError) as excinfo:
        build_options(df, "xrange", "lane", ["start"], end_col=end)
    assert str(excinfo.value) == problem
    # count_marks must stay TOTAL over the same contradiction: it runs ABOVE the app's guards,
    # so a raise here would blow the page up with a traceback before the warning that explains
    # it could render.
    assert count_marks(df, "xrange", "lane", ["start"], end_col=end) == 0


def test_xrange_explain_is_none_when_the_columns_are_fine():
    from highcharts_builder import explain_xrange_error

    assert explain_xrange_error(_plan(), "lane", "start", "end") is None


def test_a_non_coordinate_column_is_unreachable_from_the_app_pickers():
    # Pins the scoping claim the builder's docstrings and CLAUDE.md now make: of the TWO
    # contradictions `explain_xrange_error` reports, only the date-vs-number mismatch is
    # reachable through the app. The other — a column that is neither dates nor numbers — is
    # kept out of the Start/End pickers by `coordinate_columns`, so it is reachable only
    # through the pure builder API.
    #
    # This is a documentation invariant with teeth: if `coordinate_columns` ever started
    # admitting a text column, the app would grow a traceback path AND three prose claims would
    # silently become false at once. Nothing else in the suite would notice.
    import itertools

    from highcharts_builder import coordinate_columns, explain_xrange_error

    offerable = coordinate_columns(_plan())
    assert "lane" not in offerable  # the text column the builder would refuse
    for start, end in itertools.product(offerable, repeat=2):
        if start == end:
            continue  # the Start == End collision, guarded separately
        problem = explain_xrange_error(_plan(), "lane", start, end)
        # Whatever the pickers CAN produce is either drawable or a same-kind mismatch —
        # never the "neither dates nor numbers" message.
        assert problem is None or "must be the same kind" in problem


def test_xrange_count_marks_agrees_with_the_chart_on_the_raw_frame():
    # THE NO-DRIFT PIN, and the subtlest bug in the type. A row's survival LOOKS per-row, so
    # xrange looks like it belongs on count_marks' shared-predicate mask path with
    # treemap/sankey. It does not. The AXIS KIND is a COLUMN-level fact that every row's
    # start/end is read THROUGH — and the two callers do not hold the same column:
    # build_options reaches its branch on the `_label_ok`-FILTERED frame, while count_marks
    # and explain_xrange_error run on the RAW one.
    #
    # This frame is built to expose exactly that. The ONLY garbage cell ("oops") sits on the
    # row whose LANE is missing — so it is dropped for its label before the sniff ever sees
    # it. On the filtered frame the start column is 2 clean dates; on the raw frame it is 2
    # dates and one piece of junk. A raw-frame sniff still calls it a date column (2 date hits
    # beats 0 numeric hits), so the counts happen to agree — but `explain_xrange_error` would
    # be deciding on different evidence than the chart. `_xrange_bars` re-applies `_label_ok`
    # itself and sniffs the SURVIVORS only, which is what makes the two frames byte-identical.
    df = pd.DataFrame(
        {
            "lane": ["a", "b", None],
            "start": ["2026-01-01", "2026-02-01", "oops"],
            "end": ["2026-01-15", "2026-02-15", "2026-03-01"],
        }
    )
    built = _bars(_xr(df))
    assert len(built) == 2
    assert count_marks(df, "xrange", "lane", ["start"], end_col="end") == len(built)
    # And the guard must PASS on this frame, not report a contradiction the builder won't raise.
    from highcharts_builder import explain_xrange_error

    assert explain_xrange_error(df, "lane", "start", "end") is None


def test_xrange_uses_only_first_y_col():
    opts = build_options(_plan(), "xrange", "lane", ["start", "end"], end_col="end")
    assert len(_bars(opts)) == 4


def test_coordinate_columns_offers_numbers_and_dates_but_not_text():
    # Sourced from `_coordinates` itself, so the app's Start/End pickers cannot offer a column
    # the builder would refuse — the can't-drift rule applied to which options appear in a
    # widget. It is what lets the app widen those controls past select_dtypes("number")
    # (invisible to a date column, which is object dtype) without reintroducing the hazard
    # that filter exists to prevent.
    from highcharts_builder import coordinate_columns

    df = pd.DataFrame(
        {
            "lane": ["a", "b"],  # text: not a coordinate
            "month": ["Jan", "Feb"],  # the landing-sample trap: NOT a date
            "start": ["2026-01-05", "2026-02-10"],  # ISO strings: a date
            "parsed": pd.to_datetime(
                ["2026-01-05", "2026-02-10"]
            ),  # datetime64: a date
            "sprint": [12, 18],  # a number
        }
    )
    assert coordinate_columns(df) == ["start", "parsed", "sprint"]
    # A superset of the numeric columns, which is the whole point.
    assert set(df.select_dtypes("number")) <= set(coordinate_columns(df))


def test_xrange_serializes_and_resolves_the_xrange_module():
    chart = make_chart(_plan(), "xrange", "lane", ["start"], end_col="end")
    js = chart.to_js_literal()
    assert js
    # x2 is the whole type — a mark with EXTENT — and unlike sankey's nodeFormat, boxplot's
    # fillColor and sunburst's levels[].colorByPoint, it DOES survive. Only the emitted JS can
    # show that, which is why it is pinned here rather than on the options dict.
    for token in ("type: 'xrange'", "x2:", "reversed", "minPointLength", "pointWidth"):
        assert token in js, f"{token} did not survive serialization"
    assert "type: 'datetime'" in js
    # The module is resolved by highcharts-core itself, from the options shape — nothing in
    # this repo registers it. And xrange needs no highcharts-more (unlike bubble, radar,
    # boxplot and waterfall).
    tags = chart.get_script_tags(as_str=True)
    assert "modules/xrange.js" in tags
    assert "highcharts-more" not in tags


def test_xrange_light_mode_shape():
    # Pin the choices nothing else guards, and prove the dark-only key is absent (so the dark
    # test below is meaningful).
    opts = _xr()
    assert opts["legend"]["enabled"] is False
    xr = opts["plotOptions"]["xrange"]
    assert set(xr) == {"pointWidth", "minPointLength", "borderColor"}


def test_xrange_dark_mode_dissolves_the_bar_borders():
    # Xrange joins column/bar here and NOT waterfall — the other bar-shaped type, which needs
    # the opposite treatment. That was MEASURED, not inferred from the shared bar base class:
    # waterfall is the standing proof the inference is unsound, its border being a fixed
    # #333333. Pixel-scanning a dark-mode xrange PNG off the export server puts its default
    # border at pure #ffffff — the background variable, exactly column/bar's case — so every
    # bar is ringed white until it is dissolved into the dark background.
    opts = _xr()
    assert (
        opts["plotOptions"]["xrange"]["borderColor"] == "#0f172a"
    )  # _DARK_CHROME["bg"]
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    # The lane hues are unchanged: like the shared palette, they read on both backgrounds.
    assert _bars(opts)[0]["color"] == DEFAULT_COLORS[0]


def test_release_plan_sample_builds_an_xrange_chart():
    from sample_data import _release_plan

    df = _release_plan()
    opts = build_options(df, "xrange", "workstream", ["start"], end_col="end")
    assert opts["xAxis"]["type"] == "datetime"
    # Backend and Frontend each run twice, with a gap — so the sample proves the per-lane hue.
    assert opts["yAxis"]["categories"] == [
        "Discovery",
        "Design",
        "Backend",
        "Frontend",
        "QA",
        "Launch",
    ]
    bars = _bars(opts)
    assert len(bars) == 8  # every row draws, the milestone included
    backend = [b["color"] for b in bars if b["name"] == "Backend"]
    assert len(backend) == 2 and len(set(backend)) == 1
    assert count_marks(df, "xrange", "workstream", ["start"], end_col="end") == 8


# --------------------------------------------------------------------------- #
# Columnrange — floating bars spanning [low, high] per category
# --------------------------------------------------------------------------- #
def _range_df() -> pd.DataFrame:
    """Four categories, each a low/high pair. Apr is INVERTED (high < low) so the keep-and-span
    policy has something to prove; the rest are ordinary low < high ranges."""
    return pd.DataFrame(
        {
            "month": ["Jan", "Feb", "Mar", "Apr"],
            "low": [-2.0, 1.0, 4.0, 8.0],
            "high": [
                8.0,
                12.0,
                18.0,
                -3.0,
            ],  # Apr: high < low — kept, spans [min, high]
        }
    )


def _cr(df: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_options(
        df if df is not None else _range_df(),
        "columnrange",
        "month",
        ["low"],
        high_col="high",
        **kwargs,
    )


def _ranges(opts: dict) -> list:
    return opts["series"][0]["data"]


def test_columnrange_builds_one_bar_per_category_as_low_high_pairs():
    opts = _cr()
    assert opts["chart"]["type"] == "columnrange"
    # x_col is a genuine category X axis (the bars stand ON it, drawn vertically) — column/bar's
    # shape, NOT xrange's, whose lanes are on the Y axis.
    assert opts["xAxis"]["categories"] == ["Jan", "Feb", "Mar", "Apr"]
    # Each point is a `[low, high]` 2-ARRAY matched to categories BY POSITION — the boxplot
    # positional trick, one type over. A numeric-first 2-array is read unambiguously as
    # [low, high] (verified against the round-trip in the serialization test below), so it does
    # NOT collapse the way a `{name, low}` dict would.
    assert _ranges(opts) == [[-2.0, 8.0], [1.0, 12.0], [4.0, 18.0], [8.0, -3.0]]
    # One series, and its legend is off: a single-hue series legends as one useless bullet, and
    # the categories are on the X axis already (xrange's, treemap's, boxplot's reasoning).
    assert len(opts["series"]) == 1
    assert opts["legend"]["enabled"] is False


def test_columnrange_keeps_a_missing_or_non_finite_end_as_a_null_slot():
    # The category-x keep-the-slot family (column/bar/waterfall), applied to a PAIR: a bar needs
    # BOTH ends, so if either is missing (NaN) or non-finite (inf) the whole slot becomes a bare
    # EnforcedNull — a kept category tick with no bar — never a half-drawn range. A bare null, not
    # `{"low": ..., "high": EnforcedNull}`: highcharts-core drops a null out of a point dict, so a
    # partial dict would draw an arbitrary bar. And no bare `inf` reaches the JS (the `_plottable`
    # rule the whole module shares).
    df = pd.DataFrame(
        {
            "month": ["Jan", "Feb", "Mar", "Apr"],
            "low": [-2.0, float("nan"), 4.0, float("inf")],
            "high": [8.0, 12.0, float("nan"), 20.0],
        }
    )
    opts = _cr(df)
    assert _ranges(opts) == [[-2.0, 8.0], EnforcedNull, EnforcedNull, EnforcedNull]
    # The category slots are all KEPT — a null bar still holds its tick (unlike a dropped row).
    assert opts["xAxis"]["categories"] == ["Jan", "Feb", "Mar", "Apr"]
    js = make_chart(
        df, "columnrange", "month", ["low"], high_col="high"
    ).to_js_literal()
    assert js
    for token in ("inf", "nan", "NaN"):
        assert token not in js, f"columnrange emitted a non-finite literal: {token}"


def test_columnrange_keeps_an_inverted_range_spanning_both_values():
    # The vote the user made, and the mirror of xrange's backwards bar. xrange DROPS a bar that
    # ends before it starts, because Highcharts draws it spanning the WHOLE axis — a confident,
    # plausible lie. A columnrange bar is bounded by its two values, so an inverted low/high
    # (Apr's 8 → -3) draws the SAME honest bar as -3 → 8 (verified by rendering), spanning
    # [min, max]. So it is KEPT, order preserved, not dropped and not silently normalized.
    apr = _ranges(_cr())[3]
    assert apr == [8.0, -3.0]  # kept as-is, not swapped, not dropped
    # count_marks counts it, exactly as the chart draws it — all four categories survive.
    assert count_marks(_range_df(), "columnrange", "month", ["low"]) == 4


def test_columnrange_colors_every_bar_one_hue_and_never_uses_color_by_point():
    # A columnrange is ONE measurement across the axis, so every bar takes the single series hue
    # (colors[0]); `colorByPoint` stays OFF (its Highcharts default) — a per-bar hue would assert
    # a categorical identity the categories don't have (the opposite call from pie/treemap/xrange,
    # whose slices/lanes ARE separate identities). So the data carry NO per-point color, and
    # `colorByPoint` appears NOWHERE in the emitted JS.
    opts = _cr()
    assert all(not isinstance(pt, dict) or "color" not in pt for pt in _ranges(opts))
    # The palette is carried and OVERRIDABLE, so a custom palette repaints the bars.
    assert opts["colors"] == list(DEFAULT_COLORS)
    assert _cr(colors=["#abcabc"])["colors"] == ["#abcabc"]
    js = make_chart(
        _range_df(), "columnrange", "month", ["low"], high_col="high"
    ).to_js_literal()
    assert js and "colorByPoint" not in js


def test_columnrange_tooltip_names_the_category_and_the_range():
    # {point.category}, NOT xrange's {point.name}: a columnrange's categories are on the X axis
    # (its bars stand ON it), so {point.category} reads the RIGHT axis — waterfall's fix, not
    # xrange's bug. {point.low}/{point.high} are the two ends; a bare {point.y} would print null.
    tip = _cr()["tooltip"]["pointFormat"]
    assert "{point.category}" in tip
    assert "{point.low}" in tip and "{point.high}" in tip
    assert "{point.name}" not in tip and "{point.y}" not in tip


def test_columnrange_requires_a_high_column():
    with pytest.raises(ValueError, match="requires a high column"):
        build_options(_range_df(), "columnrange", "month", ["low"])


def test_columnrange_rejects_the_low_column_as_the_high_column():
    # A bar's two ends, like xrange's start/end. It must be a guard rather than a tolerated
    # oddity because it fails SILENTLY: every bar would span zero height, a row of hairlines.
    with pytest.raises(ValueError, match="cannot also be the high column"):
        build_options(_range_df(), "columnrange", "month", ["low"], high_col="low")


def test_columnrange_rejects_x_as_a_y_series():
    # columnrange IS in X_IN_Y_GUARD_TYPES (unlike xrange): its x_col is a real category X axis,
    # so x_col == low is the classic x-in-y collision the rule was written for. (x_col == high is
    # not expressible there — high_col isn't in y_cols — but it is a magnitude picked from
    # numeric_cols beside a category x, a scatter-style tolerance, so it needs no guard.)
    with pytest.raises(ValueError, match="cannot also be a y series"):
        build_options(_range_df(), "columnrange", "low", ["low"], high_col="high")


def test_columnrange_uses_only_first_y_col():
    # low = y_cols[0]; any further y columns are ignored (high comes from high_col, not y_cols[1]).
    opts = build_options(
        _range_df(), "columnrange", "month", ["low", "high"], high_col="high"
    )
    assert len(_ranges(opts)) == 4


def test_columnrange_count_marks_counts_drawable_categories():
    # Waterfall's rule without the appended total: one bar per drawable LABEL, the value columns
    # NOT consulted (a missing/inverted range keeps its slot as a null bar and still counts). A
    # row whose LABEL is missing names no category and drops; a row whose VALUE is missing keeps
    # its slot. So the KPI's "Ranges" counts by label, and equals the built data length.
    df = pd.DataFrame(
        {
            "month": ["Jan", None, "Mar"],
            "low": [
                1.0,
                2.0,
                float("nan"),
            ],  # Mar's low is missing -> null slot, still counted
            "high": [5.0, 6.0, 7.0],
        }
    )
    built = _ranges(_cr(df))
    assert built == [
        [1.0, 5.0],
        EnforcedNull,
    ]  # None-label row dropped; Mar kept as a null slot
    assert count_marks(df, "columnrange", "month", ["low"]) == 2 == len(built)


def test_columnrange_serializes_and_resolves_highcharts_more():
    # End to end: the [low, high] pairs must survive `to_js_literal` (NOT collapse like a boxplot
    # dict would) AND resolve `highcharts-more` — from `chart.type` ALONE, like bubble/boxplot/
    # waterfall, and (correcting the plausible guess) NOT a phantom `modules/columnrange.js`. Only
    # the round-trip can show which module a type pulls in; this repo registers none of them.
    chart = make_chart(_range_df(), "columnrange", "month", ["low"], high_col="high")
    js = chart.to_js_literal()
    assert js and "type: 'columnrange'" in js
    # The low/high values reach the JS as array elements (the pair did not collapse to [x, y]).
    for token in ("-2", "8", "12", "18"):
        assert token in js
    tags = chart.get_script_tags(as_str=True)
    assert "highcharts-more" in tags
    assert (
        "modules/columnrange" not in tags
    )  # no such module — it lives in highcharts-more


def test_columnrange_light_mode_shape():
    # Pin the choices nothing else guards, and prove the dark-only key is absent (so the dark
    # test below is meaningful). columnrange emits NO plotOptions at all in light mode — which is
    # also how it "carries no data labels": there is no plotOptions.columnrange to hold any.
    opts = _cr()
    assert opts["legend"]["enabled"] is False
    # The ONLY plotOptions entry is the dissolved border the theme writes — in particular
    # there are still no dataLabels, which is what this line has always been about.
    assert set(opts["plotOptions"]["columnrange"]) == {"borderColor"}


def test_columnrange_dark_mode_dissolves_the_bar_borders():
    # columnrange joins column/bar/xrange here and NOT waterfall — MEASURED, not inferred from
    # the shared bar base class (waterfall is the standing proof that inference is unsound, its
    # border being a fixed #333333). A columnrange bar's default border is the background
    # variable, pure white, which the color-scheme pin keeps white in dark mode, ringing every
    # bar until it is dissolved into the dark background.
    opts = _cr()
    assert (
        opts["plotOptions"]["columnrange"]["borderColor"] == "#0f172a"
    )  # _DARK_CHROME bg
    assert opts["chart"]["backgroundColor"] == "#0f172a"
    # The single hue is unchanged: like the shared palette, it reads on both backgrounds.
    assert _ranges(opts)[0] == [-2.0, 8.0]


def test_temperature_range_sample_builds_a_columnrange_chart():
    from sample_data import _temperature_range

    df = _temperature_range()
    opts = build_options(
        df, "columnrange", "month", ["record_low"], high_col="record_high"
    )
    assert opts["chart"]["type"] == "columnrange"
    ranges = _ranges(opts)
    assert len(ranges) == 12  # one bar per month
    # Every low sits below its high — a clean demo range, no inverted or missing slots.
    assert all(low < high for low, high in ranges)
    assert count_marks(df, "columnrange", "month", ["record_low"]) == 12


# --------------------------------------------------------------------------- #
# Arearange — columnrange's filled-band mirror (one band spanning [low, high])
# --------------------------------------------------------------------------- #
# Reuses the columnrange block's `_range_df` (four categories, Apr inverted) and `_ranges`
# helpers above — arearange reads the identical low/high shape, which is the whole point.
def _ar(df: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_options(
        df if df is not None else _range_df(),
        "arearange",
        "month",
        ["low"],
        high_col="high",
        **kwargs,
    )


def test_arearange_builds_one_band_of_low_high_pairs():
    opts = _ar()
    # Its OWN chart.type (not columnrange's) — a real highcharts-core series, so it serializes as
    # its own name, the module's "every type is its own Highcharts name" rule (radar excepted).
    assert opts["chart"]["type"] == "arearange"
    # x_col is a genuine category X axis (the band runs ALONG it) — column/bar's shape.
    assert opts["xAxis"]["categories"] == ["Jan", "Feb", "Mar", "Apr"]
    # The SAME `[low, high]` 2-array points columnrange builds (verified against the round-trip in
    # the serialization test below), Apr's inverted pair kept as-is.
    assert _ranges(opts) == [[-2.0, 8.0], [1.0, 12.0], [4.0, 18.0], [8.0, -3.0]]
    # One series (one band), legend off: a single-hue band legends as one useless bullet, and the
    # categories are on the X axis already (columnrange's/xrange's/treemap's reasoning).
    assert len(opts["series"]) == 1
    assert opts["legend"]["enabled"] is False


def test_arearange_and_columnrange_differ_only_in_chart_type():
    # The funnel/pyramid "one branch, differ only in the type string" invariant, as a test: the two
    # share ONE build branch, so their options must be byte-identical once chart.type is set aside.
    # This is what lets the shared branch stay shared — if a future edit diverges them, this fails.
    # A shared explicit title is passed so the chart_type-DERIVED default title ("Arearange chart"
    # vs "Columnrange chart") — a separate behavior pinned by test_default_title_per_type, not a
    # branch divergence — doesn't masquerade as one.
    ar, cr = _ar(title="t"), _cr(title="t")
    assert ar["chart"]["type"] == "arearange" and cr["chart"]["type"] == "columnrange"
    ar["chart"]["type"] = cr["chart"]["type"] = "_"
    # ONE divergence, and it is not the shared BUILD branch — it is `_themed`, which is keyed
    # on chart type by design: columnrange has a white bar border to dissolve and an area FILL
    # has no stroke to dissolve (test_arearange_has_no_dark_mode_theme_hook states the argument).
    # Lift that off and the branch output is byte-identical, which is the invariant here.
    from highcharts_builder import _DARK_CHROME

    assert cr.pop("plotOptions") == {"columnrange": {"borderColor": _DARK_CHROME["bg"]}}
    assert "plotOptions" not in ar
    assert ar == cr


def test_arearange_keeps_a_missing_or_non_finite_end_as_a_null_slot():
    # `_range_point` for a PAIR, shared verbatim with columnrange: a band vertex needs BOTH ends, so
    # if either is missing (NaN) or non-finite (inf) the whole slot becomes a bare EnforcedNull —
    # which BREAKS the band there (verified by rendering: the band splits, honestly "no data here",
    # rather than bridging the gap and implying data). A bare null, not `{"low": ..., "high": null}`.
    # And no bare `inf` reaches the JS (the `_plottable` rule the module shares).
    df = pd.DataFrame(
        {
            "month": ["Jan", "Feb", "Mar", "Apr"],
            "low": [-2.0, float("nan"), 4.0, float("inf")],
            "high": [8.0, 12.0, float("nan"), 20.0],
        }
    )
    opts = _ar(df)
    assert _ranges(opts) == [[-2.0, 8.0], EnforcedNull, EnforcedNull, EnforcedNull]
    assert opts["xAxis"]["categories"] == ["Jan", "Feb", "Mar", "Apr"]  # slots KEPT
    js = make_chart(df, "arearange", "month", ["low"], high_col="high").to_js_literal()
    assert js
    for token in ("inf", "nan", "NaN"):
        assert token not in js, f"arearange emitted a non-finite literal: {token}"


def test_arearange_keeps_an_inverted_range_spanning_both_values():
    # The mirror of xrange's DROPPED backwards bar, kept exactly as columnrange keeps it: a band is
    # bounded by its two values, so an inverted low/high (Apr's 8 -> -3) draws an honest crossover
    # (verified by rendering), not the whole-axis lie xrange's backwards bar would be. Kept, order
    # preserved, counted.
    assert _ranges(_ar())[3] == [8.0, -3.0]
    assert count_marks(_range_df(), "arearange", "month", ["low"]) == 4


def test_arearange_colors_the_band_one_hue_and_never_uses_color_by_point():
    # A band is ONE continuous measurement, so it takes the single series hue (colors[0]) and
    # `colorByPoint` stays OFF (its Highcharts default) — the opposite call from pie/treemap/xrange,
    # exactly as columnrange makes it. So the data carry NO per-point color and `colorByPoint`
    # appears NOWHERE in the emitted JS.
    opts = _ar()
    assert all(not isinstance(pt, dict) or "color" not in pt for pt in _ranges(opts))
    assert opts["colors"] == list(DEFAULT_COLORS)  # carried and OVERRIDABLE
    assert _ar(colors=["#abcabc"])["colors"] == ["#abcabc"]
    js = make_chart(
        _range_df(), "arearange", "month", ["low"], high_col="high"
    ).to_js_literal()
    assert js and "colorByPoint" not in js


def test_arearange_tooltip_names_the_category_and_the_range():
    # {point.category} (categories are on the X axis, the band stands ON it) plus the two ends —
    # columnrange's tooltip verbatim, waterfall's fix rather than xrange's {point.name} bug.
    tip = _ar()["tooltip"]["pointFormat"]
    assert "{point.category}" in tip
    assert "{point.low}" in tip and "{point.high}" in tip
    assert "{point.name}" not in tip and "{point.y}" not in tip


def test_arearange_requires_a_high_column():
    with pytest.raises(ValueError, match="requires a high column"):
        build_options(_range_df(), "arearange", "month", ["low"])


def test_arearange_rejects_the_low_column_as_the_high_column():
    # The magnitude-range family's low==high guard, shared with columnrange: a band would collapse
    # to a line. It must be a guard rather than a tolerated oddity because it fails SILENTLY.
    with pytest.raises(ValueError, match="cannot also be the high column"):
        build_options(_range_df(), "arearange", "month", ["low"], high_col="low")


def test_arearange_rejects_x_as_a_y_series():
    # arearange joins X_IN_Y_GUARD_TYPES via MAGNITUDE_RANGE_TYPES (its x_col is a real category X
    # axis, exactly columnrange's), so x_col == low is the classic x-in-y collision.
    with pytest.raises(ValueError, match="cannot also be a y series"):
        build_options(_range_df(), "arearange", "low", ["low"], high_col="high")


def test_arearange_uses_only_first_y_col():
    # low = y_cols[0]; further y columns are ignored (high comes from high_col, not y_cols[1]).
    opts = build_options(
        _range_df(), "arearange", "month", ["low", "high"], high_col="high"
    )
    assert len(_ranges(opts)) == 4


def test_arearange_count_marks_counts_drawable_categories():
    # The shared MAGNITUDE_RANGE rule: one mark per drawable LABEL (the band's vertices), value
    # columns NOT consulted (a missing/inverted range keeps its slot). A None-label row drops.
    df = pd.DataFrame(
        {
            "month": ["Jan", None, "Mar"],
            "low": [
                1.0,
                2.0,
                float("nan"),
            ],  # Mar low missing -> null slot, still counted
            "high": [5.0, 6.0, 7.0],
        }
    )
    built = _ranges(_ar(df))
    assert built == [
        [1.0, 5.0],
        EnforcedNull,
    ]  # None-label dropped; Mar kept as a null slot
    assert count_marks(df, "arearange", "month", ["low"]) == 2 == len(built)


def test_arearange_serializes_and_resolves_highcharts_more():
    # End to end: the [low, high] pairs must survive `to_js_literal` (NOT collapse) AND resolve
    # `highcharts-more` — from `chart.type` ALONE, like bubble/boxplot/waterfall/columnrange, and
    # NOT a phantom `modules/arearange.js`. Only the round-trip can show which module a type pulls.
    chart = make_chart(_range_df(), "arearange", "month", ["low"], high_col="high")
    js = chart.to_js_literal()
    assert js and "type: 'arearange'" in js
    for token in ("-2", "8", "12", "18"):
        assert (
            token in js
        )  # low/high reached the JS as array elements, not a collapsed [x, y]
    tags = chart.get_script_tags(as_str=True)
    assert "highcharts-more" in tags
    assert (
        "modules/arearange" not in tags
    )  # no such module — it lives in highcharts-more


def test_arearange_light_mode_shape():
    # As columnrange: NO plotOptions in light mode (which is also how it carries no data labels —
    # there is no plotOptions.arearange to hold any).
    opts = _ar()
    assert opts["legend"]["enabled"] is False
    assert "plotOptions" not in opts


def test_arearange_has_no_dark_mode_theme_hook():
    # THE distinguishing test, and the one the render verified: arearange is columnrange's mirror in
    # the DATA but NOT in `_themed`. columnrange dissolves a white BAR BORDER; an area FILL has none
    # (area/areaspline "paint no white against the dark background"), so arearange is deliberately
    # OUT of the border-dissolve group and adds NO plotOptions even in dark mode. Pins the decision
    # against a future edit that "helpfully" adds arearange to the dissolve set on the false analogy
    # to columnrange — the waterfall lesson (inference from a shared base class is unsound).
    opts = _ar()
    assert "plotOptions" not in opts  # no border hook, unlike columnrange
    assert (
        opts["chart"]["backgroundColor"] == "#0f172a"
    )  # generic dark chrome still applied
    assert _ranges(opts)[0] == [
        -2.0,
        8.0,
    ]  # the single hue is unchanged (reads on both backgrounds)


def test_forecast_range_sample_builds_an_arearange_chart():
    from sample_data import _forecast_range

    df = _forecast_range()
    opts = build_options(
        df, "arearange", "month", ["forecast_low"], high_col="forecast_high"
    )
    assert opts["chart"]["type"] == "arearange"
    ranges = _ranges(opts)
    assert len(ranges) == 12  # one band vertex per month
    # Every low sits below its high — a clean forecast cone, no inverted or missing slots.
    assert all(low < high for low, high in ranges)
    # And the band WIDENS: the sample is built to SHOW the cone opening over the year.
    spans = [high - low for low, high in ranges]
    assert spans[-1] > spans[0]
    assert count_marks(df, "arearange", "month", ["forecast_low"]) == 12


# --------------------------------------------------------------------------- #
# Bullet — a measure bar read against a goal crossbar, per category
# --------------------------------------------------------------------------- #
# Columnrange's DATA SHAPE (a category axis + two magnitude columns, one mark per
# category) read as a COMPARISON rather than as a range: the point is `[measure, goal]`
# where columnrange's is `[low, high]`, and the NULL POLICY is the exact opposite —
# `_range_point` nulls the whole slot all-or-nothing (a range with one end is not a
# range), while `_bullet_point` nulls each end ALONE (half a comparison is still worth
# drawing). Every JS-level pin here asserts the emitted ARRAY rather than a `target` key,
# which inverts this file's dominant idiom; the reason is stated once, in
# `test_bullet_never_emits_the_literal_target_key_for_a_point`.
#
# Bullet rides `SUPPORTED_TYPES` and is threaded through the sweeps by `_goal_for`, so
# the palette, the dark background, the light no-op, the non-finite-literal ban, the
# end-to-end serialization, the label-drop policy and the row-less frame are ALREADY
# covered there and are not restated below. What is here is what only bullet can say.
def _bullet_df() -> pd.DataFrame:
    """Four regions, each an actual against a quota. South and West BEAT theirs, East MISSES and
    North matches exactly — the beats are the load-bearing rows, since the crossbar trap strikes
    precisely when the measure exceeds the goal and a frame of near-misses would hide it."""
    return pd.DataFrame(
        {
            "region": ["North", "South", "East", "West"],
            "actual": [420.0, 512.0, 331.0, 604.0],
            "quota": [420.0, 450.0, 400.0, 550.0],
        }
    )


def _bullet_opts(df: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_options(
        df if df is not None else _bullet_df(),
        "bullet",
        "region",
        ["actual"],
        goal_col="quota",
        **kwargs,
    )


def _bullet_points(opts: dict) -> list:
    return opts["series"][0]["data"]


def _bullet_chart(df: pd.DataFrame | None = None, **kwargs):
    return make_chart(
        df if df is not None else _bullet_df(),
        "bullet",
        "region",
        ["actual"],
        goal_col="quota",
        **kwargs,
    )


def _bullet_js(df: pd.DataFrame | None = None, **kwargs) -> str:
    """The emitted JS, whitespace-stripped where a test needs to match a serialized literal."""
    js = _bullet_chart(df, **kwargs).to_js_literal()
    assert js
    return js


# --- the data shape -------------------------------------------------------- #


def test_bullet_builds_one_positional_measure_goal_pair_per_category():
    opts = _bullet_opts()
    assert opts["chart"]["type"] == "bullet"
    # x_col is a genuine category X axis — the measure bars stand ON it, drawn vertically
    # (column/bar's shape, and the sentence X_IN_Y_GUARD_TYPES admits bullet on). NOT xrange's
    # lanes-on-the-Y, and NOT `chart.inverted`, whatever the textbook horizontal bullet does.
    assert opts["xAxis"]["categories"] == ["North", "South", "East", "West"]
    assert "inverted" not in opts["chart"]
    # The category axis carries its column NAME too, and it is asserted here because nothing else
    # would notice its loss: the categories above survive without it, so the axis would simply go
    # unlabelled — a chart that still draws, still reads as correct, and no longer says what its
    # bars are grouped BY. (The yAxis title has its own test, for a sharper reason: a `None` there
    # drops the whole axis.)
    assert opts["xAxis"]["title"]["text"] == "region"
    # Each point is a `[measure, goal]` 2-ARRAY matched to those categories BY POSITION —
    # columnrange's positional shape, the boxplot trick two types over. The goal is the SECOND
    # slot and reaches Highcharts' `target` through that position alone.
    assert _bullet_points(opts) == [
        [420.0, 420.0],
        [512.0, 450.0],
        [331.0, 400.0],
        [604.0, 550.0],
    ]
    # ONE series, named for the MEASURE alone — the goal is an annotation on the bar, not a
    # co-equal end of one mark, so this is xrange's `start_col` precedent and NOT columnrange's
    # paired `f"{low}–{high}"`, which is right THERE precisely because a columnrange's two
    # numbers are the two ends of one bar and neither names the series alone. And the legend is
    # off: a single-hue series legends as one useless grey bullet (Highcharts draws that marker
    # in its own grey regardless) and the categories are already on the X axis — columnrange's,
    # xrange's, treemap's reasoning. There is no second series for a legend to tell apart.
    assert len(opts["series"]) == 1
    assert opts["series"][0]["name"] == "actual"
    assert "quota" not in opts["series"][0]["name"]
    assert opts["legend"]["enabled"] is False
    assert _bullet_opts()["legend"]["enabled"] is False


def test_bullet_never_emits_the_literal_target_key_for_a_point():
    """The one fact that inverts this file's dominant idiom, so it gets a test of its own.

    Everywhere else a surviving point key is pinned by grepping the emitted JS for it — sankey's
    `nodeFormat`, waterfall's `isSum`, sunburst's `id`/`parent`, xrange's `x2`. Do that here and
    the test FAILS on a perfectly correct chart: the goal survives by its INDEX in a positional
    array, so the literal key `target` never reaches the JS at all.

    The trap is that a naive grep for "target" DOES hit twice, and neither hit is a data point —
    `targetOptions` carries it as a substring and the tooltip's `{point.target}` token carries it
    verbatim — so a lazily written pin passes for the wrong reason and goes on passing if the data
    shape silently became a dict. Hence both spellings: the two legitimate occurrences enumerated
    and removed, and, independently, no `target:` OBJECT KEY anywhere, which is the only form a
    dict point could take.
    """
    js = _bullet_js()
    assert "targetOptions" in js
    assert "{point.target}" in js
    # With both taken out, the bare word is nowhere: the goal reaches Highcharts by POSITION.
    assert "target" not in js.replace("targetOptions", "").replace("{point.target}", "")
    # Said again the way a dict point would betray itself — as a serialized object key.
    assert "target:" not in js
    # And the positive half, without which the two absences above pass on an empty chart: what IS
    # there is the second array element, in position, per category.
    assert "[420.0,420.0]" in "".join(js.split())


# --- the null policy: two channels, each nulling alone ---------------------- #


def test_bullet_keeps_the_bar_when_the_goal_is_missing():
    # The type's POLICY, and the whole reason `_bullet_point` exists beside `_range_point` rather
    # than being a widened version of it. A columnrange with one end is not a range, so its slot
    # nulls all-or-nothing; a bullet's two numbers are INDEPENDENT CHANNELS, so a bar with no goal
    # is a perfectly good bar with nothing to compare it to (verified by rendering: the bar draws,
    # with no crossbar over it). The measure survives untouched. Python `None`, NOT `EnforcedNull`
    # — the module's ONE exception to that convention, forced by the library rather than chosen,
    # and observable only one layer down (see the make_chart test below).
    df = _bullet_df()
    df.loc[1, "quota"] = float("nan")
    assert _bullet_points(_bullet_opts(df))[1] == [512.0, None]


def test_bullet_keeps_the_crossbar_when_the_measure_is_missing():
    # The mirror, and the half a `_range_point`-style all-or-nothing rule would silently throw
    # away: a goal whose bar is missing is a perfectly good reference line over an empty category
    # slot (verified by rendering — a lone crossbar). The measure end takes `_num`, so it becomes
    # `EnforcedNull`, this module's rule everywhere else; the goal end is untouched beside it.
    df = _bullet_df()
    df.loc[2, "actual"] = float("nan")
    assert _bullet_points(_bullet_opts(df))[2] == [EnforcedNull, 400.0]


def test_bullet_keeps_the_category_slot_when_both_ends_are_missing():
    # The keep-the-slot family (column/bar/waterfall/columnrange) reached by a THIRD route: both
    # channels null independently and neither drags the row out of the frame, so a row with
    # nothing to draw still holds its axis tick.
    df = _bullet_df()
    df.loc[0, "actual"] = float("nan")
    df.loc[0, "quota"] = float("nan")
    opts = _bullet_opts(df)
    assert _bullet_points(opts)[0] == [EnforcedNull, None]  # the mixed pair
    assert opts["xAxis"]["categories"] == ["North", "South", "East", "West"]
    assert count_marks(df, "bullet", "region", ["actual"]) == 4
    # And the mixed array really does come out as two nulls, which is the only thing that makes
    # the asymmetry above invisible to a reader of the chart.
    assert "[null,null]" in "".join(_bullet_js(df).split())


def test_bullet_missing_goal_builds_a_real_chart_not_just_an_options_dict():
    """The `EnforcedNull`-vs-`None` trap, pinned at the only layer that can see it.

    `options/series/data/bullet.py`'s `target` setter runs `validators.numeric(value,
    allow_empty=True)`: it admits `None` and rejects `EnforcedNullType` with `CannotCoerceError`
    — raised at `Chart.from_options`, ONE LAYER BELOW `build_options`. So an options-dict
    assertion on a goal-less row passes green while the chart cannot be built at all, and the
    app's interactive path (which does not catch builder errors) shows a bare traceback naming
    neither `target` nor `bullet`. That is the `_NEEDLE_DIAL` trap in a different validator, and
    the reason this test drives `make_chart`.

    It also asserts the converse, so the module's ONE `None`-not-`EnforcedNull` slot is PINNED
    rather than merely commented: this project's own options tree, with nothing changed but the
    goal's spelling, must fail to build. Only `TypeError` is asserted — a stdlib base the
    library's class happens to derive from — because the point is that building fails, not which
    validator says so.
    """
    from highcharts_core.chart import Chart

    df = _bullet_df()
    df.loc[1, "quota"] = float("nan")
    assert "type: 'bullet'" in _bullet_js(df)

    hostile = _bullet_opts(df)
    assert hostile["series"][0]["data"][1] == [512.0, None]
    hostile["series"][0]["data"][1] = [512.0, EnforcedNull]
    with pytest.raises(TypeError):
        Chart.from_options(hostile)


def test_bullet_routes_a_non_finite_through_each_channel_own_null():
    # `test_no_supported_type_emits_a_non_finite_js_literal` already proves no `inf` token
    # escapes into the JS for any type, so that is NOT restated here. What is bullet's alone is
    # WHICH null each channel produces: the measure to `EnforcedNull` via `_num`, the goal to
    # `None` via `_plottable` — two spellings of "missing" in one array, which no sweep can see.
    # Reachable from a plain CSV (`inf`, `-inf`, `1e400`, which silently overflows).
    df = pd.DataFrame(
        {
            "region": ["North", "South", "East"],
            "actual": [420.0, float("inf"), 331.0],
            "quota": [400.0, 450.0, float("-inf")],
        }
    )
    assert _bullet_points(_bullet_opts(df)) == [
        [420.0, 400.0],
        [EnforcedNull, 450.0],
        [331.0, None],
    ]


def test_bullet_count_marks_matches_the_built_data_across_every_null_combination():
    # The can't-drift check, over a frame carrying all four combinations at once: both present,
    # goal missing, measure missing, both missing. Bullet reaches columnrange's NUMBER by a
    # DIFFERENT ARGUMENT — columnrange never reads its value columns because a missing END nulls
    # the whole slot, bullet never reads EITHER because NEITHER channel can drop a row — so the
    # rule is pinned against the built length rather than against the sibling's constant.
    # (Bullet is in neither `test_count_marks_matches_the_built_series`' list nor
    # `test_count_marks_casts_every_mask_not_just_the_label_one`'s, so this is its only home.)
    df = pd.DataFrame(
        {
            "region": ["North", "South", "East", "West"],
            "actual": [420.0, 512.0, float("nan"), float("nan")],
            "quota": [400.0, float("nan"), 380.0, float("nan")],
        }
    )
    built = _bullet_points(_bullet_opts(df))
    assert built == [
        [420.0, 400.0],
        [512.0, None],
        [EnforcedNull, 380.0],
        [EnforcedNull, None],
    ]
    assert count_marks(df, "bullet", "region", ["actual"]) == 4 == len(built)
    # And every one of those four spellings must survive the layer below build_options.
    _bullet_js(df)  # builds: the helper asserts the JS is non-empty


def test_bullet_count_marks_casts_its_mask_on_a_row_less_frame():
    """Bullet's `count_marks` branch is covered by NO sweep, and this is the rule it must obey.

    `test_row_less_frame_draws_an_empty_chart_in_every_type` sweeps `build_options` over
    `SUPPORTED_TYPES`, so bullet's BUILD is covered the day it was added — but
    `test_count_marks_casts_every_mask_not_just_the_label_one` is an explicit LIST and
    `test_count_marks_matches_the_built_series` is another, and bullet is in neither. So the
    `.astype(bool)` rule — a `.map()` over a row-less column returns an empty NON-boolean Series,
    which pandas reads as a list of COLUMN NAMES rather than as a mask — is unpinned on the one
    function of bullet's that reads a mask at all.

    Warnings are promoted to errors because that is the only way the failure is observable before
    pandas 4: today an object-dtype mask merely warns where it will later raise.
    """
    empty = _bullet_df().iloc[:0]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert count_marks(empty, "bullet", "region", ["actual"]) == 0
        assert _bullet_points(_bullet_opts(empty)) == []
    # The KPI and the chart must agree here too — the app's metric row runs above its guards, so
    # a count that disagreed with an empty chart would report marks nobody drew.
    assert count_marks(empty, "bullet", "region", ["actual"]) == len(
        _bullet_points(_bullet_opts(empty))
    )


# --- the inputs nothing else reaches --------------------------------------- #


def test_bullet_keeps_an_inverted_pair_where_the_measure_falls_far_under_its_goal():
    # Not an edge case — the ORDINARY reading of this type, and the register it exists to answer.
    # xrange DROPS a backwards bar because Highcharts draws it spanning the whole axis (a
    # confident lie) and columnrange KEEPS its inverted range because a range bar is bounded by
    # its two values; a bullet's two numbers are not two ends at all, so "measure far under goal"
    # is simply a short bar under a high crossbar. Nothing is dropped, nothing raises, nothing is
    # normalized — which is also why bullet has no `explain_*` counterpart.
    df = pd.DataFrame(
        {
            "region": ["North", "South"],
            "actual": [12.0, 88.0],  # both far under their goals
            "quota": [900.0, 550.0],
        }
    )
    opts = _bullet_opts(df)
    assert _bullet_points(opts) == [[12.0, 900.0], [88.0, 550.0]]
    assert count_marks(df, "bullet", "region", ["actual"]) == 2


def test_bullet_draws_negative_measures_and_negative_goals():
    """The one sign the family treats differently everywhere else, and never probed here.

    Sunburst's `_sizable` DROPS a negative leaf (an arc has no negative length); waterfall reads a
    negative as its semantic DOWN colour; gauge's `threshold: 0` exists precisely because an
    all-negative dial reads backwards without it. A bullet does none of that — it is a bar from
    zero, so a negative measure draws downward and a negative goal is a crossbar below the axis.

    The half that would fail SILENTLY is the predicate: `_sizable` is `_plottable` plus a `> 0`,
    one type over, and a reader consolidating the two would drop or null every row below — with
    every other bullet test staying green, because every other frame in this block is positive.
    """
    df = pd.DataFrame(
        {
            "region": ["Loss", "Mixed", "Zero"],
            "actual": [-40.0, 10.0, 0.0],
            "quota": [-20.0, -5.0, 0.0],
        }
    )
    opts = _bullet_opts(df)
    assert _bullet_points(opts) == [[-40.0, -20.0], [10.0, -5.0], [0.0, 0.0]]
    # Nothing dropped and nothing nulled: zero is a real reading (sunburst's rule for its
    # zero-width sector) and a negative is an ordinary one.
    assert opts["xAxis"]["categories"] == ["Loss", "Mixed", "Zero"]
    assert count_marks(df, "bullet", "region", ["actual"]) == 3
    assert "[-40.0,-20.0]" in "".join(_bullet_js(df).split())


def test_bullet_raises_a_value_error_on_a_text_column_but_still_nulls_a_blank_cell():
    """The last unpinned input class for the new kwarg, and the one asymmetry inside it.

    Every other way a goal column can be wrong is covered — missing, non-finite, equal to the
    measure, absent — but not "it is a column of words", the only one that RAISES out of `float()`
    rather than nulling. It is the module's documented convention (boxplot pins the same
    `ValueError` for a text observation column) and it is unreachable from the app, both bullet
    pickers being sourced from `numeric_cols` — but `goal_col` is a public kwarg, so an unpinned
    raise is free to become a silent `None` goal on some future edit to `_bullet_point`: every bar
    would then draw with no crossbar and no error, in the one register the type answers.

    The asymmetry is the reachable half: a text column with a BLANK cell must still null that cell
    rather than raise, because `pd.isna` is tested before `float()`. A `_bullet_point` rewritten to
    coerce the column first would turn a partly-filled goal column into a hard failure.
    """
    with pytest.raises(ValueError):
        _bullet_opts(
            pd.DataFrame(
                {"region": ["N", "S"], "actual": [1.0, 2.0], "quota": ["high", "low"]}
            )
        )
    # The mirror, so the convention is pinned on BOTH channels rather than only the new one.
    with pytest.raises(ValueError):
        _bullet_opts(
            pd.DataFrame(
                {"region": ["N", "S"], "actual": ["a", "b"], "quota": [1.0, 2.0]}
            )
        )
    # But a MISSING cell in that same object-dtype column nulls, as everywhere else.
    blanks = pd.DataFrame(
        {"region": ["N", "S"], "actual": [1.0, 2.0], "quota": [None, None]}
    )
    assert _bullet_points(_bullet_opts(blanks)) == [[1.0, None], [2.0, None]]


def test_bullet_keeps_duplicate_category_labels_as_separate_marks():
    """A real CSV shape no other bullet test contains, and sunburst's error #31 in mirror.

    Sunburst SYNTHESIZES its node ids precisely because two rows may legitimately share a label
    and handing Highcharts two points with one id is a red error band across the chart. Bullet
    reaches the opposite answer by a different route — its points are positional and its
    categories are a plain list — so two "North" rows must stay two bars against two crossbars.
    Nothing asserts it, and "one mark per category" appears in the branch comment, the
    `count_marks` comment AND the KPI's own noun, so a future edit that grouped by label to make
    that phrase literally true would be an easy one to make: it would silently halve the chart,
    and — because `count_marks` counts LABELS and would halve with it — the KPI would agree with
    the corrupted chart rather than expose it.
    """
    df = pd.DataFrame(
        {
            "region": ["North", "North", "South"],
            "actual": [420.0, 380.0, 512.0],
            "quota": [400.0, 400.0, 550.0],
        }
    )
    opts = _bullet_opts(df)
    assert opts["xAxis"]["categories"] == ["North", "North", "South"]
    assert _bullet_points(opts) == [[420.0, 400.0], [380.0, 400.0], [512.0, 550.0]]
    assert (
        count_marks(df, "bullet", "region", ["actual"])
        == 3
        == len(_bullet_points(opts))
    )
    _bullet_js(df)  # builds: two identical categories are not an id collision here


def test_bullet_drops_a_row_whose_label_is_undrawable_and_the_count_follows():
    # `test_missing_or_non_finite_label_drops_the_row_in_every_type` already proves no "nan"
    # label reaches the JS, so the drop itself is not restated. What is bullet's alone is that
    # the category list, the data array and `count_marks` shorten TOGETHER — the whole of its
    # count rule, since an undrawable label is the ONE way a bullet row can leave the frame
    # (neither VALUE channel can drop one).
    df = pd.DataFrame(
        {
            "region": ["North", None, "East"],
            "actual": [
                420.0,
                512.0,
                float("nan"),
            ],  # East's measure nulls, keeps its slot
            "quota": [400.0, 450.0, 380.0],
        }
    )
    opts = _bullet_opts(df)
    assert opts["xAxis"]["categories"] == ["North", "East"]
    assert _bullet_points(opts) == [[420.0, 400.0], [EnforcedNull, 380.0]]
    assert count_marks(df, "bullet", "region", ["actual"]) == 2


def test_bullet_builds_a_real_chart_from_an_integer_dtype_frame():
    """`_bullet_point`'s `float()` cast, at the only layer it is observable — and the SHIPPED
    SAMPLE is the frame that reaches it.

    The cast does one job beyond `_range_point`'s: numpy scalars are rejected outright by the
    numeric keys this type reaches in highcharts-core (a `numpy.int64` raises where a
    `numpy.float64` does not, which is what would make that bug look random). Every hand-written
    frame in this block uses float literals, so every one produces `numpy.float64` and takes the
    branch that survives the cast's removal. `_sales_vs_quota` does not: its two magnitude columns
    are bare Python ints, so pandas gives them `int64` and the goal channel hands a `numpy.int64`
    straight at the `target` setter — at `Chart.from_options`, where the sample tests below stop
    short. So the cast could be deleted and the DEMO DATASET would be the thing that broke, in the
    app's interactive path, which does not catch builder errors.
    """
    from sample_data import _sales_vs_quota

    df = _sales_vs_quota()
    assert df["actual"].dtype == "int64" and df["quota"].dtype == "int64", (
        "this test is only meaningful while the sample's two magnitude columns are integers — "
        "written as float literals it would exercise the branch that survives without the cast"
    )
    assert "type: 'bullet'" in _bullet_js(df)
    # The cast really happened: floats in the emitted array, not a repr of a numpy scalar.
    assert all(
        isinstance(m, float) and isinstance(g, float)
        for m, g in _bullet_points(_bullet_opts(df))
    )
    # And a mixed int/float frame with a missing goal — the combination the app can reach on any
    # upload, where the surviving cells stay integral while the column widens to float64.
    mixed = df.copy()
    mixed["quota"] = mixed["quota"].astype(float)
    mixed.loc[0, "quota"] = float("nan")
    _bullet_js(mixed)  # builds: the helper asserts the JS is non-empty


# --- the guards ------------------------------------------------------------ #


def test_bullet_requires_a_goal_column():
    # A bullet without a goal is a column chart wearing a different name — the crossbar IS the
    # comparison the type exists to draw, so it is required rather than optional (unlike
    # organization's `title_col`, which is cosmetic and has a "(no titles)" escape).
    with pytest.raises(ValueError, match="requires a goal column"):
        build_options(_bullet_df(), "bullet", "region", ["actual"])


def test_bullet_rejects_the_measure_column_as_the_goal_column():
    # sankey's source-is-target, sunburst's node-is-parent, xrange's start-is-end and
    # columnrange's low-is-high, a fifth time — and the worst of the five. The other four produce
    # a VISIBLY broken chart (a row of hairlines, a collapsed band); this one produces a PERFECT
    # chart making a FALSE CLAIM: every bar landing exactly on its own crossbar, so the chart
    # reports that every category hit its target precisely, with no tooltip at all in the Static
    # PNG to contradict it.
    with pytest.raises(ValueError, match="cannot also be the goal column"):
        build_options(_bullet_df(), "bullet", "region", ["actual"], goal_col="actual")


def test_bullet_rejects_x_as_a_y_series():
    # Bullet IS in X_IN_Y_GUARD_TYPES (unlike xrange, whose x_col names a lane on the Y axis):
    # its x_col is a real category X axis, so x_col == measure is the classic collision the rule
    # was written for. The OTHER collision, measure == goal, is not expressible there (goal_col
    # isn't in y_cols) and gets the dedicated guard above — exactly columnrange's split.
    with pytest.raises(ValueError, match="cannot also be a y series"):
        build_options(_bullet_df(), "bullet", "actual", ["actual"], goal_col="quota")


def test_bullet_uses_only_first_y_col():
    # The goal comes from `goal_col`, NEVER from `y_cols[1]` — which is what keeps both guards
    # above independent of how many columns the selection happens to carry.
    #
    # The THIRD column is what makes that testable rather than merely stated. Passing
    # `y_cols=["actual", "quota"]` beside `goal_col="quota"` — the obvious spelling — makes
    # `y_cols[1]` and the goal the SAME column, so a branch that wrongly read `y_cols[1]` would
    # produce byte-identical output and the assertion would pin nothing while the comment above
    # it claimed otherwise. `stretch` exists only to be the decoy: it sits in `y_cols[1]`, its
    # values appear NOWHERE below, and the goals that do appear are `quota`'s.
    df = _bullet_df()
    df["stretch"] = [900.0, 900.0, 900.0, 900.0]
    opts = build_options(
        df, "bullet", "region", ["actual", "stretch"], goal_col="quota"
    )
    assert len(opts["series"]) == 1
    assert opts["series"][0]["name"] == "actual"
    assert _bullet_points(opts) == [
        [420.0, 420.0],
        [512.0, 450.0],
        [331.0, 400.0],
        [604.0, 550.0],
    ]
    assert not any(900.0 in point for point in _bullet_points(opts))


# --- colour, and the two absences that had to be earned -------------------- #


def test_bullet_paints_every_bar_from_the_palette_and_never_by_point():
    # A bullet is ONE measurement read against ONE goal across the axis, so every bar takes the
    # single series hue — `colors[0]` — rather than a per-bar identity (columnrange's call, the
    # opposite of pie/treemap/xrange, whose slices/lanes ARE separate identities). The palette
    # itself is swept by `test_default_palette_applied_per_type`, so what is asserted here is what
    # is bullet's: no explicit series `color` (a hardcoded one would serialize perfectly and
    # silently ignore every custom palette), so a caller's `colors` is what repaints the bars.
    opts = _bullet_opts()
    assert "color" not in opts["series"][0]
    assert _bullet_opts(colors=["#abcabc", "#defdef"])["colors"] == [
        "#abcabc",
        "#defdef",
    ]
    # `colorByPoint` appears NOWHERE, and here that pin guards a real DECISION rather than
    # restating a library drop the way networkgraph's and sunburst's do — a claim that is only
    # true because `test_bullet_color_by_point_really_survives_the_round_trip` proves the key
    # survives. Without that companion this assertion would be indistinguishable from theirs.
    assert "colorByPoint" not in str(opts)
    assert "colorByPoint" not in _bullet_js()
    # And the shape the decision protects: array points, never dicts. See
    # `test_bullet_dict_point_form_really_breaks_the_missing_goal_policy` for why.
    assert all(isinstance(pt, list) for pt in _bullet_points(opts))


def test_bullet_color_by_point_really_survives_the_round_trip():
    """Without this, every `colorByPoint` pin in the bullet block is a vacuous pass.

    The block asserts `"colorByPoint" not in js` and justifies it in prose as guarding a DECISION
    rather than restating a library limitation — the distinction drawn against networkgraph's and
    sunburst's pins, where highcharts-core silently drops the key so its absence could not have
    been otherwise. But an absence assertion passes identically whether the branch chose to omit
    the key or the library would have thrown it away, so the whole justification rests on an
    untested claim in a comment. If highcharts-core ever starts dropping it, the pin stays green
    while its stated reason silently becomes false, and the next reader "consolidates" bullet's
    with networkgraph's as one more restatement of a limitation.
    """
    from highcharts_core.chart import Chart

    opts = _bullet_opts()
    opts["plotOptions"]["bullet"]["colorByPoint"] = True
    opts["series"][0]["colorByPoint"] = True
    js = Chart.from_options(opts).to_js_literal()
    assert js
    assert js.count("colorByPoint") == 2, (
        "bullet's colorByPoint is supposed to SURVIVE at both the series and the plotOptions "
        "level — that survival is the entire reason its absence is a decision worth pinning"
    )


def test_bullet_dict_point_form_really_breaks_the_missing_goal_policy():
    """Without this, "the array form is load-bearing" is prose, not a pinned fact.

    The branch comment and the single-hue decision both rest on it: a per-point key forces the
    OBJECT point form, in which a `None` goal VANISHES rather than nulling while an `EnforcedNull`
    raises — so a per-bar hue would leave a goal-less row with no working spelling. The block's own
    assertions (`not isinstance(pt, dict)`, `"colorByPoint" not in js`) pin the CONSEQUENCE and not
    the premise, so a library change that made the dict form safe would leave the argument standing
    on nothing while every test stayed green — and someone would then be told, by a comment, that
    they must not add a per-point colour.

    Both halves of the trap run on the module's own tree with nothing changed but the point's
    SPELLING, which is the only comparison that can show the array form is doing work.
    """
    from highcharts_core.chart import Chart

    df = _bullet_df()
    df.loc[1, "quota"] = float("nan")
    assert _bullet_points(_bullet_opts(df))[1] == [512.0, None]  # the shipped spelling

    # Half one: in dict form a `None` target does not null — it disappears entirely, so a
    # goal-less bar would claim to have no goal channel at all rather than an empty one.
    dict_form = _bullet_opts(df)
    dict_form["series"][0]["data"] = [
        {"y": 420.0, "target": 400.0, "color": DEFAULT_COLORS[0]},
        {"y": 512.0, "target": None, "color": DEFAULT_COLORS[0]},
    ]
    js = Chart.from_options(dict_form).to_js_literal()
    assert js
    flat = "".join(js.split())
    assert "target:400.0" in flat  # the present goal survives
    assert "target:null" not in flat, (
        "the whole premise of the array form is that a None target VANISHES in dict form rather "
        "than nulling — if it nulls cleanly now, the single-hue decision has lost its second and "
        "stronger reason and the comments saying otherwise are wrong"
    )

    # Half two: the module's usual EnforcedNull is not the escape hatch either — in dict form it
    # raises, so there is genuinely NO working spelling for a missing goal once a point is a dict.
    hostile = _bullet_opts(df)
    hostile["series"][0]["data"] = [
        {"y": 420.0, "target": 400.0, "color": DEFAULT_COLORS[0]},
        {"y": 512.0, "target": EnforcedNull, "color": DEFAULT_COLORS[0]},
    ]
    with pytest.raises(TypeError):
        Chart.from_options(hostile)


def test_bullet_draws_no_qualitative_plot_bands():
    # The poor/average/good background bands every bullet demo on the internet draws are a
    # BUSINESS JUDGEMENT, and a three-column CSV of a category, a measure and a goal states none
    # of it. Drawing them would be this module's standing offence — emitting a mark the data never
    # made — the one sunburst refuses when it declines to draw a CSV's own subtotal as a parent
    # value, and the one waterfall sidesteps by making its Total an `isSum` Highcharts computes.
    # There is no library excuse behind this absence: `yAxis.plotBands` is a modelled, surviving
    # option. So it is refused, not forgotten.
    #
    # The yAxis assertions are the PRESENCE ANCHOR, without which every line below passes on a
    # chart that dropped the whole axis — which is not hypothetical here but the exact
    # `{"text": None}` failure `test_bullet_y_axis_title_names_both_columns_and_is_never_none`
    # exists for, and which would take the bands' own home with it.
    opts = _bullet_opts()
    assert opts["yAxis"]["title"]["text"]  # the axis is there to have carried bands
    assert "plotBands" not in str(opts)
    js = _bullet_js()
    assert "yAxis" in js  # the anchor again, at the layer the drop happens
    assert "plotBands" not in js
    # Nor invented for dark mode, where a band would be the easiest thing to slip in as "chrome"
    # — every band on a bullet is data, whatever colour it is drawn in.
    dark = _bullet_opts()
    assert dark["yAxis"]["title"]["text"]
    assert "plotBands" not in str(dark)


def test_bullet_sets_a_crossbar_colour_off_the_categorical_palette():
    # THE CROSSBAR TRAP, stated once, here — the other tests that touch this hook refer back
    # rather than restating it. Left unset, the goal marker takes the SERIES hue (the same blue as
    # the bar it crosses) and Highcharts draws it at 140% of the bar width. So it does not vanish,
    # which would at least be obvious: the segment crossing the bar disappears into the fill while
    # the two overhangs survive as small stubs either side, reading as a deliberate tick rather
    # than as a goal line. It strikes exactly when the measure EXCEEDS the goal — the "we beat
    # plan" case, the row a reader most wants to find — so the failure is invisible on the rows
    # that look fine and silent on the rows that matter.
    #
    # The hue is asserted as a LITERAL, not against the constant the branch writes: importing
    # `_BULLET_TARGET_COLOR` and asserting the branch equals it would stay green if its value were
    # renamed to `#ff00ff`. The independent facts are the three below it — off the categorical
    # palette (`_WATERFALL_SUM_COLOR`/`_SUNBURST_ROOT_COLOR`'s argument: a goal is not one of the
    # categories, it is the line they are read AGAINST) and unrepaintable by a custom palette.
    # That it also READS against both surfaces it crosses is the separate claim next door.
    opts = _bullet_opts()
    target = opts["plotOptions"]["bullet"]["targetOptions"]
    assert target["color"] == "#f1f5f9"
    assert target["color"] not in list(DEFAULT_COLORS)
    custom = ["#111111", "#222222"]
    assert (
        _bullet_opts(colors=custom)["plotOptions"]["bullet"]["targetOptions"]["color"]
        == "#f1f5f9"
    )
    assert "#f1f5f9" not in custom
    # No geometry DERIVED FROM DATA beside it, which is the trap that matters. `targetOptions
    # .width = 0` raises EmptyValueError out of a validator naming neither the key nor the series,
    # and every numeric key under `targetOptions` rejects a numpy.int64 outright — so Highcharts'
    # 140% x 3px default is left entirely alone (the pane-`size` "stop steering" rule) and the one
    # numeric key set, `borderWidth`, is a module constant that no frame can reach. Width and
    # height stay absent, so neither trap is reachable rather than merely remembered.
    # The keys that ARE set, exhaustively — so `width`/`height` cannot creep in later. Stated as
    # the full set rather than as two `not in`s: that is what makes it a pin on the geometry trap
    # rather than a pin on two names someone thought of today.
    assert set(target) == {"color", "borderColor", "borderWidth"}


def test_bullet_themes_both_hooks_and_the_crossbar_reads_on_both_its_surfaces():
    """Bullet's two `_themed` hooks, of DIFFERENT KINDS, pinned together because a fix to either
    that broke the other would otherwise pass half the suite.

    `borderColor` is the ordinary dissolve, shared with column/bar/xrange/columnrange and NOT
    waterfall — joined on a MEASUREMENT rather than an inference, since waterfall is the standing
    proof the shared bar base class settles nothing (its border is a fixed #333333, while bullet's
    bars come back crisply ringed white). `targetOptions` is the only hook in this module that
    styles a MARK rather than chrome: the crossbar is drawn at 140% of the bar width, so it
    necessarily spans TWO surfaces at once — the bar and the chart background — and a single
    colour therefore cannot work in PRINCIPLE, not merely in practice. Which is why it is the one
    mark carrying a fill AND a border: one value per surface.

    The hue is asserted at its PATH in the option tree and in the serialized JS at the level it
    was written to, never as a bare `"#f1f5f9" in js`: that string is `_DARK_CHROME["text"]`,
    which `_themed` also writes to the title, both axis label styles and the tooltip on EVERY
    chart, so the substring test would pass with this hook deleted outright — the one thing it
    exists to catch.
    """
    opts = _bullet_opts()

    target = opts["plotOptions"]["bullet"]["targetOptions"]
    crossbar = target["color"]
    # Read with a FALLBACK rather than by subscript, and deliberately: with no border, the fill
    # is all the mark has, which is the state to be judged — not a KeyError. Delete the border
    # half of the hook and this test must fail on the CONTRAST assertion below, the one it
    # exists for; subscripting here would kill it two lines earlier and leave that assertion
    # permanently unverified (the mutation rule: read the failure, not the exit code — a mutant
    # caught by KeyError is still a hole).
    edge = target.get("borderColor", crossbar)
    width = target.get("borderWidth", 0)
    border = opts["plotOptions"]["bullet"]["borderColor"]
    background = opts["chart"]["backgroundColor"]
    bar = DEFAULT_COLORS[0]

    # THE PAIRING, and the assertion whose absence let a real regression ship green. Every other
    # check here reads ONE value at ONE path; the crossbar's whole problem is that it spans two
    # surfaces at once, so its legibility is a property of a PAIR and no single-value assertion
    # can see it. Repointing DEFAULT_COLORS at the config theme lightened the bar from #2563eb to
    # #60a5fa and dropped the fill's contrast against it from 4.19:1 to 2.32:1 — every assertion
    # in this test still passed, and the crossbar visibly washed out on exactly the rows where
    # the measure beats the goal.
    #
    # Run the numbers and no single value CAN work: clearing 3:1 on the slate background needs a
    # luminance >= 0.25, on the palette blue <= 0.087. So the requirement is stated over the pair
    # — each surface must have a >= 3:1 partner among {fill, border} — which is a rule about the
    # mark rather than a literal about today's theme, and survives the next palette the way a
    # hardcoded hex would not.
    assert (
        max(_contrast_ratio(crossbar, background), _contrast_ratio(edge, background))
        >= 3.0
    )
    assert max(_contrast_ratio(crossbar, bar), _contrast_ratio(edge, bar)) >= 3.0
    assert width >= 1

    # Hook one: the bar border dissolves INTO the background.
    assert border == background
    # Hook two: the crossbar is readable against both surfaces rather than dissolving into
    # either. `_DARK_CHROME["bg"]` serves as the crossbar's BORDER and as the bar's dissolved
    # border, so the fill must differ from it or the mark disappears where it matters most.
    assert crossbar != border
    assert crossbar != background
    assert edge == background  # the border half IS the background colour, on purpose
    # And the hue reaches the JS at the level it was written to — not merely somewhere in the
    # chrome, which is what `"#f1f5f9" in js` would have settled for. (highcharts-core emits the
    # keys alphabetically, so borderColor/borderWidth lead.)
    flat = "".join(_bullet_js().split())
    assert (
        f"targetOptions:{{borderColor:'{edge}',borderWidth:{width},color:'{crossbar}'}}"
        in flat
    )
    assert opts["colors"] == list(DEFAULT_COLORS)


# --- modules, tooltip, axis, and the mark that prints nothing -------------- #


def test_bullet_resolves_its_own_module_and_needs_no_load_reordering():
    # This test MUST drive the BUILT chart: highcharts-core resolves modules from a chart's
    # contents, and a bare `chart.type` in an options dict resolves NOTHING for ANY type — so a
    # module assertion written against `build_options` output is not weak, it is vacuous.
    # `highcharts-more` is the plausible guess (it is where columnrange's and boxplot's
    # floating-bar machinery lives) and the round-trip corrects it, as it does for columnrange and
    # funnel: bullet has its OWN module.
    #
    # The reordering claim lives HERE rather than in a test of its own, because standalone it is
    # `_order_script_tags`' identity — true verbatim for `line`, `pie`, `column` and twenty others,
    # and still true if bullet's tags stopped being emitted at all. Asserted one line below the
    # proof that `modules/bullet` IS among these tags, it says something only about bullet:
    # bullet.js declares `@requires highcharts` only, extending nothing, unlike dependency-wheel
    # and organization, whose reversed emission blanks the iframe with Highcharts error #17.
    from highcharts_builder import _order_script_tags

    chart = _bullet_chart()
    assert "type: 'bullet'" in _bullet_js()
    tags = chart.get_script_tags(as_str=True)
    assert "modules/bullet" in tags
    assert "highcharts-more" not in tags
    assert _order_script_tags(tags) == tags


def test_bullet_tooltip_reads_the_right_axis_and_labels_both_columns():
    # `{point.category}`, NOT xrange's `{point.name}`: a bullet's categories are on the X axis (its
    # bars stand ON it), so this reads the right one — waterfall's fix, columnrange's reason — and
    # `{point.name}` is blank here anyway, the points being positional arrays. `{point.target}`
    # RESOLVES despite the literal key never appearing in the emitted JS (the same positional
    # survival the data array shows), and the tooltip is the ONLY place the goal's NUMBER can be
    # read at all. Both names are LABELLED rather than run together, because `{point.target}` on a
    # null goal renders as NOTHING — not `null`, not `undefined` — so the labelled form degrades to
    # a clean "quota:" where "420 of {point.target}" would trail off mid-sentence.
    tooltip = _bullet_opts()["tooltip"]
    assert tooltip["headerFormat"] == ""
    fmt = tooltip["pointFormat"]
    assert "{point.category}" in fmt
    assert "{point.y}" in fmt and "{point.target}" in fmt
    assert "{point.name}" not in fmt
    assert "actual:" in fmt and "quota:" in fmt


def test_bullet_tooltip_sanitizes_both_user_column_names():
    # Bubble's and sankey's rule, and bullet is the type with the MOST exposure to it: it
    # interpolates TWO user-supplied column names into one format string, beside two genuine
    # Highcharts tokens. Both names are brace-stripped (Highcharts would parse `{...}` as a value
    # token and swallow it) and HTML-escaped (a tooltip renders as HTML). Reachable from any
    # uploaded CSV, since a header cell is arbitrary text.
    #
    # It is asserted for bullet rather than left to the bubble/sankey tests because `_tooltip_label`
    # is applied per CALL SITE — nothing forces this branch to use it, so deleting either call here
    # would leave both of those tests green while this chart injected live markup.
    df = pd.DataFrame({"region": ["A"], "act {x}": [1.0], "<b>quota</b>": [2.0]})
    fmt = build_options(df, "bullet", "region", ["act {x}"], goal_col="<b>quota</b>")[
        "tooltip"
    ]["pointFormat"]
    # Braces stripped, so Highcharts won't tokenize `{x}` away.
    assert "{x}" not in fmt
    assert "act x" in fmt
    # HTML in the goal column name is escaped, not emitted as live markup.
    assert "<b>quota</b>" not in fmt
    assert "&lt;b&gt;quota&lt;/b&gt;" in fmt
    # The genuine Highcharts tokens are untouched — including the goal's, which survives
    # positionally even though the literal key `target` never reaches the data array.
    assert "{point.y}" in fmt and "{point.target}" in fmt


def test_bullet_prints_nothing_in_the_mark_and_the_omitted_key_is_the_gate():
    # xrange's rule reached from xrange's premise, exactly as columnrange reached it: a bullet's
    # bar stands on a real, ticked, gridlined y axis that renders in the Static PNG too
    # (column/bar's case, not waterfall's bar floating above an invisible running total); its goal
    # is DRAWN on that same axis rather than printed; and the only other identity, the category
    # name, is already on the X axis. So there is nothing to print and no gate constant to tune.
    #
    # The omitted key IS the gate, and that is a fact about bullet rather than a convenience. A
    # bullet's dataLabels default OFF — column/bar's behaviour — so saying nothing says "off". A
    # GAUGE's default ON, which is why that family disables them EXPLICITLY and why merely
    # omitting the key there would be a gate that did nothing. Same silence, opposite meaning.
    assert "dataLabels" not in str(_bullet_opts())
    assert "dataLabels" not in str(_bullet_opts())


def test_bullet_y_axis_title_names_both_columns_and_is_never_none():
    # Both channels are read against this ONE axis, so it names both — "vs", not columnrange's en
    # dash, because these are two quantities COMPARED and not the two ends of one span.
    #
    # The `is not None` half is the load-bearing half, and it is not defensive typing: a
    # `{"text": None}` title silently drops the ENTIRE yAxis out of the emitted options (verified
    # on the round-trip), taking its dark-mode chrome with it — so the axis a reader needs to
    # decode both channels would simply cease to exist, with nothing raised anywhere. If it ever
    # needs blanking, blank it with `""`.
    title = _bullet_opts()["yAxis"]["title"]["text"]
    assert title is not None
    assert title == "actual vs quota"
    js = _bullet_js()
    assert "yAxis" in js and "actual vs quota" in js


# --------------------------------------------------------------------------- #
# The bullet sample
# --------------------------------------------------------------------------- #


def test_sales_vs_quota_sample_builds_a_bullet_chart():
    # The three-way beat/miss/match assertion is the argumentative half. A quota sample where every
    # region MISSED would look tidier and would hide the one failure a reader could not diagnose —
    # the crossbar trap, which is only reachable from the page on a BEATING row (see
    # `test_bullet_sets_a_crossbar_colour_off_the_categorical_palette`). So the beats
    # are load-bearing, not flattering. The exact MATCH (North) is the honest-looking edge that a
    # per-ROW equality is fine, unlike the per-COLUMN one the app guards against.
    from sample_data import _sales_vs_quota

    df = _sales_vs_quota()
    # The category column LEADS, like every sample here and for the same load-bearing reason: the
    # app opens on `line` with the first column as X, so a numeric first column would trip the
    # x-in-y guard the instant the dataset was selected.
    assert list(df.columns) == ["region", "actual", "quota", "deals_closed"]
    assert not pd.api.types.is_numeric_dtype(df["region"])

    pairs = list(zip(df["actual"], df["quota"], strict=True))
    assert any(a > q for a, q in pairs)  # BEAT — the crossbar-contrast case
    assert any(a < q for a, q in pairs)  # MISS
    assert any(a == q for a, q in pairs)  # exact MATCH

    # Every value is present. The missing-goal, missing-measure and missing-both cases are the
    # tests' job, not a demo's — the _temperature_range/_forecast_range rule: a sample shows the
    # clean reading, and the null slots are pinned where they can be read.
    assert not df.isna().to_numpy().any()

    # The throwaway numeric column, carried for _reporting_lines' `tenure_years` reason and one of
    # its own: it sits BELOW `quota` so the Goal picker's constant second-numeric index defaults to
    # the quota rather than competing with it.
    assert list(df.select_dtypes("number").columns) == [
        "actual",
        "quota",
        "deals_closed",
    ]

    opts = build_options(df, "bullet", "region", ["actual"], goal_col="quota")
    assert opts["chart"]["type"] == "bullet"
    (series,) = opts["series"]
    assert series["data"] == [[a, q] for a, q in pairs]  # positional [measure, goal]
    assert count_marks(df, "bullet", "region", ["actual"]) == len(df) == 6


# ---------------------------------------------------------------------------
# Variwide: columns whose WIDTH is a second magnitude
#
# Variwide rides SUPPORTED_TYPES and is threaded through the sweeps by `_width_for`, so the
# palette, the dark background, the light no-op, the non-finite-literal ban, the end-to-end
# serialization, the label-drop policy and the row-less frame are ALREADY covered there and are
# not restated below. What is here is what only variwide can say.
#
# Two facts shape almost every test in this block, and both were established by RENDERING:
#
#   1. The width survives POSITIONALLY. The literal key `z` never reaches the emitted JS, so this
#      module's dominant `assert "..." in js` idiom is INVERTED here, exactly as it is for bullet.
#   2. A width is a SHARE OF A TOTAL. So a bad width does not merely fail to draw its own bar —
#      it drops out of the denominator and silently makes every OTHER bar wider. That is why the
#      null policy is all-or-nothing and why the width takes `_sizable` rather than `_plottable`.
# ---------------------------------------------------------------------------


def _variwide_df() -> pd.DataFrame:
    """Four product lines, each a margin (the bar's HEIGHT) and a revenue (its WIDTH).

    Margin deliberately ANTI-correlates with revenue — the best margin belongs to the smallest
    line — so a test that confused the two channels reads differently rather than plausibly.
    """
    return pd.DataFrame(
        {
            "line": ["Analytics", "Platform", "Services", "Hardware"],
            "margin_pct": [62.0, 41.0, 22.0, 34.0],
            "revenue": [21.0, 58.0, 76.0, 30.0],
        }
    )


def _variwide_opts(df: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_options(
        df if df is not None else _variwide_df(),
        "variwide",
        "line",
        ["margin_pct"],
        width_col="revenue",
        **kwargs,
    )


def _variwide_points(opts: dict) -> list:
    return opts["series"][0]["data"]


def _variwide_chart(df: pd.DataFrame | None = None, **kwargs):
    return make_chart(
        df if df is not None else _variwide_df(),
        "variwide",
        "line",
        ["margin_pct"],
        width_col="revenue",
        **kwargs,
    )


def _variwide_js(df: pd.DataFrame | None = None, **kwargs) -> str:
    js = _variwide_chart(df, **kwargs).to_js_literal()
    assert js
    return js


def test_variwide_builds_value_width_pairs_per_category():
    """Each point is a positional `[value, width]` 2-array, matched to xAxis.categories by
    POSITION — columnrange's and bullet's data shape, and NOT a `{name, y, z}` dict (see the
    dict-form test below for what that would cost)."""
    opts = _variwide_opts()
    assert opts["chart"]["type"] == "variwide"
    assert opts["xAxis"]["categories"] == [
        "Analytics",
        "Platform",
        "Services",
        "Hardware",
    ]
    assert _variwide_points(opts) == [
        [62.0, 21.0],
        [41.0, 58.0],
        [22.0, 76.0],
        [34.0, 30.0],
    ]
    # The series is named for the HEIGHT column alone: the width is the bar's other dimension,
    # not a co-equal end of it, so there is no columnrange-style paired name.
    assert opts["series"][0]["name"] == "margin_pct"
    assert opts["yAxis"]["title"]["text"] == "margin_pct"
    assert opts["legend"]["enabled"] is False


def test_variwide_never_emits_the_literal_z_key_for_a_point():
    """The fact that inverts this file's dominant idiom, so it gets a test of its own.

    A variwide's width reaches Highcharts as the SECOND element of a positional array, never as a
    `z: ...` object key — so `assert "z" in js` is meaningless here and `assert "z:" in js` is
    FALSE on a perfectly correct chart. Bullet's `target` has the identical property; this is that
    test one type over, and it is written the same three ways for the same reason.
    """
    js = _variwide_js()
    # The bare key, in the spelling a serialized object point would betray itself by.
    assert "z:" not in js
    # The ONE legitimate occurrence of the letter, asserted PRESENT first — without this the
    # subtraction below would quietly go vacuous if the tooltip token were ever removed.
    assert "{point.z}" in js
    # And now the whole word, with that one occurrence stripped: nothing else in the emitted JS
    # spells it, because the width reaches Highcharts by POSITION.
    assert "z" not in js.replace("{point.z}", "")
    # The positive half, without which the two absences above pass vacuously on an empty chart:
    # what IS there is the second array element, in position, per category.
    assert "[62.0,21.0]" in "".join(js.split())


def test_variwide_dict_point_form_really_eats_a_null_width():
    """The companion that turns the array-form decision from a comment into a measurement.

    An absence-only assertion cannot distinguish "the branch chose the array form" from "the
    library would have thrown the dict form away anyway". So drive the dict form deliberately and
    show what it costs: a `None` width VANISHES from the emitted JS entirely rather than nulling,
    leaving Highcharts to read the width as undefined. That is why a per-point key — a `color`,
    say — is not a style choice here but would silently break the missing-width policy.
    """
    from highcharts_core.chart import Chart

    chart = Chart.from_options(
        {
            "chart": {"type": "variwide"},
            "series": [
                {
                    "type": "variwide",
                    "data": [{"name": "A", "y": 62.0, "z": None, "color": "#ff0000"}],
                }
            ],
        }
    )
    js = chart.to_js_literal()
    assert js
    # The per-point color forced the dict form, and the null width is simply GONE — not `null`.
    # (No format token here to strip: this chart carries no tooltip.)
    assert "color" in js
    assert "z" not in js


def test_variwide_missing_or_non_finite_end_nulls_the_whole_slot():
    """All-or-nothing, and KEEPING the slot — `_range_point`'s answer reached from variwide's own
    premise (a half-row repaints its SIBLINGS' widths), not columnrange's (a range with one end is
    not a range). Contrast bullet, whose two channels null INDEPENDENTLY.

    The tick survives in every case: the points are positional against xAxis.categories, so a
    dropped row would desynchronize the two, and a reader would never learn the category existed.
    """
    df = _variwide_df()
    df.loc[1, "revenue"] = None  # width missing -> whole slot nulls, height discarded
    df.loc[2, "margin_pct"] = float("inf")  # non-finite height -> likewise
    opts = _variwide_opts(df)
    points = _variwide_points(opts)
    assert points[0] == [62.0, 21.0]
    assert points[1] is EnforcedNull
    assert points[2] is EnforcedNull
    assert points[3] == [34.0, 30.0]
    # All four categories keep their tick — the keep-the-slot family.
    assert len(opts["xAxis"]["categories"]) == 4
    assert "inf" not in _variwide_js(df).lower()


def test_variwide_negative_width_nulls_its_slot_because_a_width_is_a_share():
    """The one place variwide's two columns take DIFFERENT predicates, and the reason is measured.

    A negative HEIGHT is fine — it is a length on a real axis and draws honestly downward. A
    negative WIDTH is not, because a width is a share of a total: rendered, a `-30` beside a `21`
    and a `44` drew its own bar 1px wide and inflated the other two to 410px and 860px inside a
    760px chart, overflowing the canvas with every width overstated and no error anywhere. So the
    width takes `_sizable` (sunburst's non-negative predicate) while the height takes `_plottable`.

    ZERO is KEPT, for `_sizable`'s own reason and verified the same way: it draws a 1px sliver,
    keeps its tick, and contributes nothing to the total, which is exactly true.
    """
    df = _variwide_df()
    df.loc[1, "revenue"] = -30.0
    df.loc[2, "revenue"] = 0.0
    df.loc[3, "margin_pct"] = -12.0  # a negative HEIGHT is ordinary and must survive
    points = _variwide_points(_variwide_opts(df))
    assert points[1] is EnforcedNull, "a negative width must not reach the denominator"
    assert points[2] == [22.0, 0.0], "a zero width is a real measurement"
    assert points[3] == [-12.0, 30.0], "a negative HEIGHT is not the same question"


def test_variwide_takes_a_single_hue_and_never_color_by_point():
    """`colorByPoint` must appear NOWHERE, and — like bullet's, unlike networkgraph's and
    sunburst's — this pin guards a real DECISION rather than restating a library limitation: a
    variwide's `colorByPoint` survives the round trip at both levels (the companion test below),
    so nothing but the choice keeps it off. A variwide is one measurement read across the axis,
    and the varying WIDTH already distinguishes the categories."""
    assert "colorByPoint" not in _variwide_js()
    # No per-point key anywhere — the fact the policy actually rests on, so it is asserted against
    # a frame that HAS a null slot rather than against clean data (where it would reduce to "the
    # points are lists", already pinned two tests up).
    df = _variwide_df()
    df.loc[1, "revenue"] = None
    assert all(
        p is EnforcedNull or isinstance(p, list)
        for p in _variwide_points(_variwide_opts(df))
    )


def test_variwide_color_by_point_really_survives_the_round_trip():
    """The companion to the pin above. Force `colorByPoint` on and show the library keeps it, at
    BOTH levels — so its absence in our output is ours, not highcharts-core's."""
    from highcharts_core.chart import Chart

    variants: dict[str, dict] = {
        "series": {
            "chart": {"type": "variwide"},
            "series": [
                {
                    "type": "variwide",
                    "data": [["A", 1.0, 2.0]],
                    "colorByPoint": True,
                }
            ],
        },
        "plotOptions": {
            "chart": {"type": "variwide"},
            "plotOptions": {"variwide": {"colorByPoint": True}},
            "series": [{"type": "variwide", "data": [["A", 1.0, 2.0]]}],
        },
    }
    for where, opts in variants.items():
        js = Chart.from_options(opts).to_js_literal()
        assert js and "colorByPoint" in js, f"{where}-level colorByPoint was dropped"


def test_variwide_tooltip_reads_the_category_and_both_channels():
    """`{point.category}`, not xrange's `{point.name}`: a variwide's categories are on the X axis,
    so this reads the right one (waterfall's fix, columnrange's and bullet's reason), and
    `{point.name}` is blank here anyway (positional arrays).

    `{point.z}` is the one number in this module a tooltip is the ONLY home for. Everywhere else
    "prints nothing in the mark" rests on xrange's premise — the value lands on a ticked axis —
    and that premise is FALSE for a width: the x axis carries variable-width category slots, not a
    scale. It resolves despite the literal key never appearing in the JS (the same positional
    survival `{point.target}` relies on).
    """
    fmt = _variwide_opts()["tooltip"]["pointFormat"]
    assert "{point.category}" in fmt
    assert "{point.name}" not in fmt
    assert "{point.y}" in fmt and "{point.z}" in fmt
    assert "margin_pct" in fmt and "revenue" in fmt


def test_variwide_prints_nothing_in_the_mark():
    """No dataLabels, and no gate constant either. A variwide's dataLabels default OFF (column's
    behaviour, not a gauge's, which default ON and must be disabled explicitly), so the omitted
    key IS the gate — and printing the width in the bar would fail exactly where it is most
    wanted: a bar narrow enough to need its width read is too narrow to hold a label, and
    Highcharts hides a colliding label by rendering it INVISIBLE, so every assertion would keep
    passing while the number was absent."""
    assert "dataLabels" not in _variwide_js()


def test_variwide_sets_no_padding_so_its_bars_touch():
    """Variwide OVERRIDES column's 0.1/0.2 padding defaults to 0/0 on purpose — the adjacency IS
    the chart type (a band of the axis divided up, where a bar's share of the width is readable
    only because no gaps eat it). Setting either key would silently un-make the type, so both are
    pinned absent."""
    js = _variwide_js()
    assert "pointPadding" not in js
    assert "groupPadding" not in js


def test_variwide_requires_a_width_column():
    with pytest.raises(ValueError, match="requires a width column"):
        build_options(_variwide_df(), "variwide", "line", ["margin_pct"])


def test_variwide_rejects_the_value_column_as_the_width_column():
    """Claim-fabricating, not cosmetic, so it raises: every bar's width would be proportional to
    its own height, making each bar's AREA its value SQUARED — a chart that draws perfectly while
    stating something nobody asked."""
    with pytest.raises(ValueError, match="cannot also be the width column"):
        build_options(
            _variwide_df(), "variwide", "line", ["margin_pct"], width_col="margin_pct"
        )


def test_variwide_rejects_x_as_a_y_series():
    """The shared X_IN_Y_GUARD_TYPES rule: a variwide's x_col is a genuine category X axis (its
    bars stand ON it, drawn vertically), so x_col == the height column is the same category-x
    collision the rule was written for."""
    with pytest.raises(ValueError, match="cannot also be"):
        build_options(_variwide_df(), "variwide", "line", ["line"], width_col="revenue")


def test_variwide_uses_only_the_first_y_column():
    # The width comes from `width_col`, NEVER from `y_cols[1]` — which is what keeps both guards
    # above independent of how many columns the selection happens to carry.
    #
    # The DECOY is what makes that testable rather than merely stated, and it has to sit IN
    # `y_cols` to be one: an unused extra frame COLUMN pins nothing, because with a one-element
    # `y_cols` the expressions `y_cols[0]`, `y_cols[1]` and `y_cols[-1]` are all the same value and
    # no index-reading mutant is distinguishable. (This test was written that way first and caught
    # nothing — a `y_cols[-1]` mutant left the whole suite green.) So `stretch` goes in the
    # selection, its values appear NOWHERE below, and the heights that do appear are
    # `margin_pct`'s. Bullet's `test_bullet_uses_only_first_y_col` is the same decoy one type over.
    df = pd.DataFrame(
        {
            "line": ["A", "B"],
            "margin_pct": [10.0, 20.0],
            "stretch": [99.0, 99.0],
            "revenue": [5.0, 6.0],
        }
    )
    opts = build_options(
        df, "variwide", "line", ["margin_pct", "stretch"], width_col="revenue"
    )
    assert len(opts["series"]) == 1
    assert opts["series"][0]["name"] == "margin_pct"
    assert _variwide_points(opts) == [[10.0, 5.0], [20.0, 6.0]]


def test_variwide_count_marks_counts_drawable_categories():
    """One bar per surviving LABEL — the same number columnrange and bullet return, by a third
    argument: neither channel can drop a row here because `_variwide_point` nulls all-or-nothing
    and KEEPS the slot. A null slot is still a counted bar, so the count never exceeds the row
    count and never falls below the number of ticks drawn."""
    df = _variwide_df()
    df.loc[1, "revenue"] = None  # a bad WIDTH nulls its slot, keeps its tick
    df.loc[2, "revenue"] = -5.0  # likewise
    # A bad HEIGHT too, and this row is the load-bearing one: without it the test passes just as
    # happily against a `count_marks` that ANDs a value mask onto the label one (verified by
    # mutation — that mutant SURVIVED until this row was added). The two channels have to be shown
    # separately, because the rule being pinned is that NEITHER of them can drop a row.
    df.loc[3, "margin_pct"] = None
    assert (
        count_marks(df, "variwide", "line", ["margin_pct"])
        == 4
        == len(_variwide_points(_variwide_opts(df)))
    )
    # An undrawable LABEL does drop its row, and the count follows the chart down.
    df.loc[0, "line"] = None
    assert (
        count_marks(df, "variwide", "line", ["margin_pct"])
        == 3
        == len(_variwide_points(_variwide_opts(df)))
    )


def test_variwide_count_marks_casts_its_mask_on_a_row_less_frame():
    """Variwide's `count_marks` branch is covered by NO sweep, exactly as bullet's is not.

    `test_row_less_frame_draws_an_empty_chart_in_every_type` sweeps `build_options` over
    `SUPPORTED_TYPES`, so variwide's BUILD is covered the day it joins — but it never calls
    `count_marks` at all, while `test_count_marks_casts_every_mask_not_just_the_label_one` and
    `test_count_marks_matches_the_built_series` are both explicit LISTS that variwide is in
    neither of. So the `.astype(bool)` rule — a `.map()` over a row-less column returns an empty
    NON-boolean Series, which pandas reads as a list of COLUMN NAMES rather than as a mask — is
    otherwise unpinned on the one function of variwide's that reads a mask at all.

    Warnings are promoted to errors because that is the only way the failure is observable before
    pandas 4: today an object-dtype mask merely warns where it will later raise.
    """
    empty = _variwide_df().iloc[:0]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert count_marks(empty, "variwide", "line", ["margin_pct"]) == 0
        assert _variwide_points(_variwide_opts(empty)) == []
    # The KPI and the chart must agree here too — the app's metric row runs above its guards, so
    # a count that disagreed with an empty chart would report marks nobody drew.
    assert count_marks(empty, "variwide", "line", ["margin_pct"]) == len(
        _variwide_points(_variwide_opts(empty))
    )


def test_variwide_resolves_its_own_module_and_not_highcharts_more():
    """`modules/variwide` from `chart.type` alone, and NOT `highcharts-more` — the plausible guess
    the round trip corrects, as it does for columnrange, funnel and bullet. Dropping the module is
    a SILENT blank: verified by stripping the tag, the browser renders an SVG with zero series
    paths, no Highcharts error band and no console error, while the export server rasterizes the
    PNG perfectly — the solidgauge-pane trap, and the class of bug the two-render-modes rule
    exists to close.

    Note the chart must carry a SERIES: resolution is by the series' effective type, and an
    options tree with `chart.type` and no series emits only `highcharts.js`, so a test omitting it
    would pin nothing.
    """
    from highcharts_builder import _order_script_tags

    tags = _variwide_chart().get_script_tags(as_str=True)
    assert "modules/variwide" in tags
    assert "highcharts-more" not in tags
    # And no reordering is needed: variwide.js declares `@requires highcharts` only, unlike
    # dependency-wheel's and organization's modules/sankey and solid-gauge's highcharts-more.
    assert _order_script_tags(tags) == tags


def test_variwide_dark_mode_dissolves_its_bar_borders():
    """Variwide is the SIXTH member of the border-dissolve tuple, joined on a MEASUREMENT (its
    default border came back as pure white, the background var — column/bar's case, not
    waterfall's fixed #333333) and on an argument the other five do not share.

    Their bars have GAPS, so the white outline is a spurious ring. A variwide's bars TOUCH, so the
    border is the only thing DIVIDING two neighbours — which is why dissolving it was rendered as
    its own question, with adjacent bars of EQUAL height, the case a silhouette cannot
    disambiguate. The seam survives, drawn in the page colour, exactly as the white border is on
    the light shell; it is the ABSENCE of the hook that would break the symmetry, leaving a white
    seam on a navy page. Same fix as column/bar, opposite reason.
    """
    assert _variwide_opts()["plotOptions"]["variwide"]["borderColor"] == "#0f172a"


def test_variwide_sample_builds():
    from sample_data import SAMPLES

    df = SAMPLES["Product line margin by revenue (variwide)"]()
    opts = build_options(
        df, "variwide", "product_line", ["margin_pct"], width_col="revenue_musd"
    )
    assert len(_variwide_points(opts)) == len(df)
    # The sample's whole point: margin ANTI-correlates with revenue, so the tallest bar is the
    # narrowest. A staircase would hide that AREA is the reading.
    tallest = max(_variwide_points(opts), key=lambda p: p[0])
    assert tallest[1] == min(p[1] for p in _variwide_points(opts))


# --------------------------------------------------------------------------- #
# Dumbbell — a before and an after per category, joined by a connector
#
# The SUPPORTED_TYPES sweeps already cover, via `_after_for`: that it builds, serializes through
# the real Chart.from_options -> to_js_literal pipeline, carries DEFAULT_COLORS, takes the dark
# background, emits no bare `inf`, drops a row whose LABEL is missing or non-finite, and survives a
# row-less frame. What follows is only what is dumbbell's own.
# --------------------------------------------------------------------------- #
def _dumbbell_df() -> pd.DataFrame:
    """Four regions, each with a BEFORE and an AFTER reading of one quantity.

    Directions are deliberately MIXED — two rise, two fall — because the type's sharpest failure
    mode is only reachable on a FALLING row (see the slot-order test below). A frame that only
    rose would draw identically whether the before/after hues track the first slot or the smaller
    value, so several assertions here would go quietly vacuous.
    """
    return pd.DataFrame(
        {
            "region": ["Nordics", "DACH", "Iberia", "Benelux"],
            "q1": [12.0, 28.0, 9.0, 17.0],  # two below their after, two above
            "q4": [19.0, 21.0, 15.0, 13.0],
        }
    )


def _dumbbell_opts(df: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_options(
        df if df is not None else _dumbbell_df(),
        "dumbbell",
        "region",
        ["q1"],
        after_col="q4",
        **kwargs,
    )


def _dumbbell_points(opts: dict) -> list:
    return opts["series"][0]["data"]


def _dumbbell_chart(df: pd.DataFrame | None = None, **kwargs):
    return make_chart(
        df if df is not None else _dumbbell_df(),
        "dumbbell",
        "region",
        ["q1"],
        after_col="q4",
        **kwargs,
    )


def _dumbbell_js(df: pd.DataFrame | None = None, **kwargs) -> str:
    js = _dumbbell_chart(df, **kwargs).to_js_literal()
    assert js
    return js


def test_dumbbell_builds_before_after_pairs_per_category():
    """Each point is a positional `[before, after]` 2-array matched to xAxis.categories by
    POSITION — columnrange's, bullet's and variwide's data shape."""
    opts = _dumbbell_opts()
    assert opts["chart"]["type"] == "dumbbell"
    assert opts["xAxis"]["categories"] == ["Nordics", "DACH", "Iberia", "Benelux"]
    assert _dumbbell_points(opts) == [
        [12.0, 19.0],
        [28.0, 21.0],
        [9.0, 15.0],
        [17.0, 13.0],
    ]
    # BOTH column names, in order, on the axis and the series: the two ends share one axis and
    # one unit, so neither name alone describes what is being measured. (Variwide names only its
    # height column, because there the second number is on no axis at all.)
    assert opts["yAxis"]["title"]["text"] == "q1 \u2192 q4"
    assert opts["series"][0]["name"] == "q1\u2192q4"
    assert opts["legend"]["enabled"] is False


def test_dumbbell_keeps_the_before_in_slot_zero_even_when_the_value_falls():
    """The type's headline fact, and the one a reader would most reasonably assume away.

    Highcharts paints `lowColor` onto the marker at the FIRST array slot, NOT onto the
    numerically smaller value (verified by rendering a falling row: the low-coloured marker drew
    at the TOP). So the builder must not normalize the pair — and this test is what stops a future
    `sorted(...)` or `min/max` "tidy-up" from landing, because such an edit would still draw a
    plausible chart while silently swapping the before/after hues on exactly the falling rows.

    DACH and Benelux both FELL. If the pair were normalized their slots would read [21, 28] and
    [13, 17]; asserted here in the order the frame states them.
    """
    points = _dumbbell_points(_dumbbell_opts())
    assert points[1] == [28.0, 21.0], "a falling row must keep its BEFORE in slot 0"
    assert points[3] == [17.0, 13.0], "a falling row must keep its BEFORE in slot 0"
    # Stated as the invariant rather than only as two literals, so a frame change cannot make the
    # assertion above accidentally true: slot 0 is always the q1 cell, whatever the direction.
    df = _dumbbell_df()
    assert [p[0] for p in points] == list(df["q1"])
    assert [p[1] for p in points] == list(df["q4"])


@pytest.mark.parametrize(
    ("before", "after", "why"),
    [
        (float("nan"), 19.0, "a missing BEFORE"),
        (12.0, float("nan"), "a missing AFTER"),
        (float("nan"), float("nan"), "both missing"),
        (float("inf"), 19.0, "a non-finite BEFORE"),
        (12.0, float("-inf"), "a non-finite AFTER"),
    ],
)
def test_dumbbell_nulls_the_whole_slot_when_either_reading_is_unusable(
    before, after, why
):
    """All-or-nothing, and — unlike columnrange's, whose policy is a CHOICE about what a range
    means — this one is not a choice at all: Highcharts draws NOTHING for a half-pair (verified by
    rendering `[42, null]` — no marker, no connector, just an empty tick). So there is no
    half-drawn state a per-end policy could prefer, which is why bullet's independent-ends rule is
    unavailable here rather than merely rejected.

    The slot is KEPT, never dropped: the points are positional against xAxis.categories, so the
    tick must survive or the two desynchronize.
    """
    df = _dumbbell_df()
    df.loc[1, "q1"] = before
    df.loc[1, "q4"] = after
    opts = _dumbbell_opts(df)
    points = _dumbbell_points(opts)
    assert points[1] is EnforcedNull, why
    # the category tick survives, and the other rows are untouched
    assert opts["xAxis"]["categories"] == ["Nordics", "DACH", "Iberia", "Benelux"]
    assert points[0] == [12.0, 19.0]
    js = _dumbbell_js(df)
    assert "inf" not in js.lower()


def test_dumbbell_null_slot_must_be_a_bare_token_not_a_pair_of_them():
    """Why `_range_point`'s BARE `EnforcedNull` return is load-bearing for dumbbell specifically.

    `EnforcedNull` INSIDE a dumbbell's array raises `CannotCoerceError` — and it raises at
    `Chart.from_options`, one layer BELOW `build_options`, which is bullet's `target` trap in a
    third validator. So `[EnforcedNull, EnforcedNull]` would pass every options-dict assertion in
    this file while making the chart unbuildable, and the app's interactive path (which does not
    catch builder errors) would show a bare traceback naming neither the column nor the type.

    This test therefore drives `make_chart`, the only layer at which the failure is observable at
    all, and pins BOTH halves: the spelling the builder uses works, and the spelling a reasonable
    "tidy-up" would reach for does not.
    """
    # what the builder actually emits, through the layer that would reject a bad spelling
    df = _dumbbell_df()
    df.loc[1, "q4"] = float("nan")
    js = _dumbbell_js(df)
    assert "null" in js

    # and the alternative, proven to raise rather than merely being unused
    from highcharts_core.chart import Chart

    with pytest.raises(Exception) as excinfo:
        Chart.from_options(
            {
                "chart": {"type": "dumbbell"},
                "xAxis": {"categories": ["A"]},
                "series": [
                    {
                        "type": "dumbbell",
                        "name": "s",
                        "data": [[EnforcedNull, EnforcedNull]],
                    }
                ],
            }
        )
    assert (
        "EnforcedNull" in str(excinfo.value) or "coerce" in str(excinfo.value).lower()
    )


def test_dumbbell_paints_the_before_marker_off_the_categorical_palette():
    """The BEFORE marker takes a fixed slate, NOT an entry from `colors`.

    Two separate claims, both deliberate. It is off-palette because a prior reading is not one of
    the categories (the `_WATERFALL_SUM_COLOR` / `_SUNBURST_ROOT_COLOR` / `_BULLET_TARGET_COLOR`
    argument), so a caller's custom palette must not repaint it into looking like a second series.
    And it is set AT ALL because Highcharts' own default here is a near-black that all but
    vanishes on the dark shell — verified by rendering both ways, which is what makes this
    load-bearing rather than decorative.
    """
    opts = _dumbbell_opts()
    low = opts["plotOptions"]["dumbbell"]["lowColor"]
    assert low not in DEFAULT_COLORS
    # A custom palette repaints the AFTER marker and the connector (they are the series hue) and
    # must leave the BEFORE marker alone.
    custom = ["#111111", "#222222"]
    assert _dumbbell_opts(colors=custom)["plotOptions"]["dumbbell"]["lowColor"] == low


def test_dumbbell_takes_a_single_hue_and_never_color_by_point():
    """`colorByPoint` must appear NOWHERE — but unlike bullet's and variwide's identical-looking
    pins, this one restates a LIBRARY limitation rather than guarding a decision, and saying so is
    the point of the test.

    highcharts-core DROPS `colorByPoint` for this type at both the series and the plotOptions
    level (pinned by its companion below), so there is no choice here to protect: networkgraph's
    and sunburst's case, not bullet's. The pin still earns its place — it stops someone "fixing"
    a per-point hue in and believing it works.
    """
    js = _dumbbell_js()
    assert "colorByPoint" not in js
    assert "colorByPoint" not in str(_dumbbell_opts())


def test_dumbbell_color_by_point_really_is_dropped_by_the_library():
    """The companion that turns the claim above from an assertion into a measurement.

    Without this, `colorByPoint not in js` would be indistinguishable from "the builder happens
    not to set it" — and the reason for the absence would be undocumented and free to be wrong.
    Bullet's and variwide's equivalents prove the OPPOSITE (theirs survive, so their absence is a
    decision); this one proves the key cannot be made to work at all.
    """
    from highcharts_core.chart import Chart

    chart = Chart.from_options(
        {
            "chart": {"type": "dumbbell"},
            "xAxis": {"categories": ["A"]},
            "plotOptions": {"dumbbell": {"colorByPoint": True}},
            "series": [
                {
                    "type": "dumbbell",
                    "name": "s",
                    "data": [[1.0, 2.0]],
                    "colorByPoint": True,
                }
            ],
        }
    )
    chart.container = "c"
    js = chart.to_js_literal()
    assert js and "colorByPoint" not in js


def test_dumbbell_tooltip_reads_the_category_and_both_readings():
    """`{point.category}`, not xrange's `{point.name}`: a dumbbell's categories are on the X axis
    (its markers stand ON it), so this reads the RIGHT axis — waterfall's fix, reached for
    columnrange's/bullet's/variwide's reason. `{point.name}` is blank here anyway (positional
    arrays), and a bare `{point.y}` would print null, since a range-shaped point carries low/high.

    Both column names are LABELLED rather than run together (bullet's rule): on a nulled slot each
    value renders as nothing at all, so the labelled form degrades to a clean "q1: / q4:" where a
    run-together "{low} -> {high}" would collapse to a bare arrow.
    """
    fmt = _dumbbell_opts()["tooltip"]["pointFormat"]
    assert "{point.category}" in fmt
    assert "{point.name}" not in fmt
    assert "{point.y}" not in fmt
    assert "{point.low}" in fmt and "{point.high}" in fmt
    assert "q1:" in fmt and "q4:" in fmt


def test_dumbbell_tooltip_sanitizes_user_column_names():
    """Column names come from an uploaded CSV, so they reach the tooltip through `_tooltip_label`:
    Highcharts parses `{...}` as value tokens and renders tooltips as HTML."""
    df = _dumbbell_df().rename(columns={"q1": "share {pct}", "q4": "<b>q4</b>"})
    fmt = build_options(
        df, "dumbbell", "region", ["share {pct}"], after_col="<b>q4</b>"
    )["tooltip"]["pointFormat"]
    assert "share pct" in fmt  # the braces are stripped, the unit survives
    assert "&lt;b&gt;q4&lt;/b&gt;" in fmt  # markup escaped, not rendered


def test_dumbbell_prints_nothing_in_the_mark():
    """xrange's rule reached from xrange's OWN premise, unlike variwide where that premise is
    false: BOTH of a dumbbell's numbers land on a real, ticked, gridlined y axis that renders in
    the Static PNG too, and the only other identity — the category name — is already on the X
    axis. A dumbbell's dataLabels default OFF (column/bar's behaviour, not a gauge's), so the
    OMITTED key is the gate.
    """
    opts = _dumbbell_opts()
    assert "dataLabels" not in opts["plotOptions"]["dumbbell"]
    assert "dataLabels" not in opts["series"][0]


def test_dumbbell_requires_an_after_column():
    with pytest.raises(ValueError, match="requires an after column"):
        build_options(_dumbbell_df(), "dumbbell", "region", ["q1"])


def test_dumbbell_rejects_the_before_column_as_the_after_column():
    """The start-is-end collision a seventh time, and CLAIM-FABRICATING rather than cosmetic, so
    it raises: every category would draw its two markers at one value, which renders as a single
    dot with no connector — a chart reporting that nothing changed anywhere."""
    with pytest.raises(ValueError, match="cannot also be the after column"):
        build_options(_dumbbell_df(), "dumbbell", "region", ["q1"], after_col="q1")


def test_dumbbell_rejects_x_as_a_y_series():
    """Its x_col is a genuine category X axis (the markers stand ON it), so it joins
    X_IN_Y_GUARD_TYPES — the collision the dedicated guard above cannot express."""
    df = _dumbbell_df()
    with pytest.raises(ValueError, match="cannot also be a y series"):
        build_options(df, "dumbbell", "q1", ["q1"], after_col="q4")


def test_dumbbell_uses_only_the_first_y_column():
    """A second Y is ignored — the app offers a single-select, but the pure API does not enforce
    it. The DECOY sits in the SELECTION, not merely in the frame: written the other way a
    `y_cols[-1]` mutant would leave this green.
    """
    df = _dumbbell_df()
    df["decoy"] = [99.0, 98.0, 97.0, 96.0]
    opts = _dumbbell_opts(df, **{})
    assert _dumbbell_points(opts) == _dumbbell_points(
        build_options(df, "dumbbell", "region", ["q1", "decoy"], after_col="q4")
    )
    assert 99.0 not in [p[0] for p in _dumbbell_points(opts) if p is not EnforcedNull]


def test_dumbbell_count_marks_counts_drawable_categories():
    """One change per drawable LABEL, agreeing with the built series length by construction."""
    df = _dumbbell_df()
    df.loc[2, "q4"] = float("nan")  # a null slot still COUNTS: its tick survives
    assert count_marks(df, "dumbbell", "region", ["q1"]) == len(df)
    assert len(_dumbbell_points(_dumbbell_opts(df))) == count_marks(
        df, "dumbbell", "region", ["q1"]
    )
    # a row whose LABEL is undrawable loses its tick, so it is not counted
    df.loc[0, "region"] = None
    assert count_marks(df, "dumbbell", "region", ["q1"]) == len(df) - 1


def test_dumbbell_count_marks_casts_its_mask_on_a_row_less_frame():
    """A header-only CSV is legitimate input and must draw an empty chart, not raise. Uncast, the
    `.map()` mask comes back non-boolean and `int(...sum())` blows up."""
    empty = pd.DataFrame({"region": [], "q1": [], "q4": []})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert count_marks(empty, "dumbbell", "region", ["q1"]) == 0
        assert _dumbbell_points(_dumbbell_opts(empty)) == []


def test_dumbbell_resolves_its_module_and_highcharts_more():
    """Unlike columnrange/funnel/bullet/variwide — where `highcharts-more` is the plausible guess
    the round-trip CORRECTS — a dumbbell genuinely needs both, and `modules/dumbbell.js` requires
    `highcharts-more.js`, so the ORDER matters too.

    Driven off the BUILT chart: an assertion against a `build_options` dict would be vacuous, and
    an options tree with a chart.type and no series emits only `highcharts.js`.
    """
    from highcharts_builder import _order_script_tags

    tags = _dumbbell_chart().get_script_tags(as_str=True)
    assert "modules/dumbbell.js" in tags
    assert "highcharts-more.js" in tags
    assert tags.index("highcharts-more.js") < tags.index("modules/dumbbell.js")
    # and it needs no _MODULE_LOAD_ORDER entry: highcharts-core already emits them in that order,
    # unlike dependency-wheel's and organization's, which come out reversed.
    assert _order_script_tags(tags) == tags


def test_dumbbell_has_no_dark_mode_theme_hook():
    """Pins an ABSENCE, arearange's precedent — and here the absence is the surprising half.

    Dumbbell is a `highcharts-more` bar cousin of columnrange, which IS in the border-dissolve
    tuple, so the inference from kinship says it should be too. It is not, and that was MEASURED
    rather than assumed: its markers carry `stroke: var(--highcharts-background-color)` at
    `stroke-width: 0`, so the white ring the tuple exists to remove is declared but never painted.
    Adding a hook here would dissolve a border that was never drawn.
    """
    assert (
        "plotOptions" in _dumbbell_opts()
    )  # it HAS plotOptions, for lowColor/connector
    light = _dumbbell_opts()["plotOptions"]["dumbbell"]
    dark = _dumbbell_opts()["plotOptions"]["dumbbell"]
    assert light == dark, "dumbbell's plotOptions must not differ between themes"
    # Asserted at the PATH, never as a bare substring: `borderColor` appears in EVERY dark chart's
    # emitted JS as part of the tooltip chrome `_themed` writes, so `"borderColor" not in js`
    # fails on a correct chart — and, written the other way round, a `"borderColor" in js` pin
    # would pass with the hook it existed for deleted outright. That is this file's standing
    # dark-mode trap, and it caught this very test while it was being written.
    assert "borderColor" not in _dumbbell_opts()["plotOptions"]["dumbbell"]
    # The theme still reaches the CHROME, so the absence above is specific rather than a dead flag.
    assert _dumbbell_opts()["chart"]["backgroundColor"] == "#0f172a"


def test_dumbbell_sample_builds():
    from sample_data import SAMPLES

    df = SAMPLES["Market share shift by region (dumbbell)"]()
    opts = build_options(
        df, "dumbbell", "region", ["q1_share_pct"], after_col="q4_share_pct"
    )
    assert len(_dumbbell_points(opts)) == len(df)
    assert not df.isna().any().any()
    # The sample's load-bearing property: directions are MIXED. A frame that only rose would draw
    # identically whether the before/after hues track the first slot or the smaller value, so the
    # falls are what make the sample demonstrate the type rather than merely exercise it.
    rose = [p for p in _dumbbell_points(opts) if p[1] > p[0]]
    fell = [p for p in _dumbbell_points(opts) if p[1] < p[0]]
    assert rose and fell, "the sample must contain both a rise and a fall"
    # numeric column ORDER is load-bearing: the app's After picker defaults to the SECOND numeric
    # column, so before/after must be the first two.
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    assert numeric[:2] == ["q1_share_pct", "q4_share_pct"]


# --------------------------------------------------------------------------- #
# Gauge — concentric rings, each one COLUMN reduced to one number
# --------------------------------------------------------------------------- #
@pytest.fixture
def bookings_frame() -> pd.DataFrame:
    """Four regions, eight weeks — the shape a gauge reads: comparable measures on one scale.

    ``emea`` has a reporting gap (the drop happens INSIDE the aggregate) and ``partner_deals``
    is entirely unreported, which is the type's headline trap: pandas sums it to ``0.0``.
    """
    blank = float("nan")
    return pd.DataFrame(
        {
            "week": ["W01", "W02", "W03", "W04", "W05", "W06", "W07", "W08"],
            "north": [42, 51, 47, 58, 61, 55, 63, 59],  # sum 436, mean 54.5, max 63
            "south": [38, 35, 44, 41, 39, 46, 43, 48],  # sum 334
            "emea": [22, 27, 25, blank, blank, 31, 34, 36],  # sum 175, over SIX weeks
            "partner_deals": [blank] * 8,  # nothing reported
        }
    )


def _gauge(df, y_cols, **kwargs) -> dict:
    return build_options(df, "solidgauge", None, list(y_cols), **kwargs)


def _rings(opts: dict) -> list[dict]:
    return opts["series"]


def _reading(ring: dict):
    """The one number a ring draws — or EnforcedNull when its column held no data."""
    (point,) = ring["data"]
    return point if point is EnforcedNull else point["y"]


def test_gauge_draws_one_ring_per_column_reduced_to_one_number(bookings_frame):
    opts = _gauge(bookings_frame, ["north", "south", "emea"], agg="sum")
    rings = _rings(opts)
    assert [r["name"] for r in rings] == ["north", "south", "emea"]
    assert [_reading(r) for r in rings] == [436.0, 334.0, 175.0]
    # emea's 175 is over SIX weeks, not eight: the gap drops INSIDE the aggregate.
    assert opts["chart"]["type"] == "solidgauge"


@pytest.mark.parametrize(
    ("agg", "expected"),
    [
        ("sum", 436.0),
        ("mean", 54.5),
        ("median", 56.5),
        ("min", 42.0),
        ("max", 63.0),
        ("last", 59.0),
    ],
)
def test_gauge_every_aggregation_reduces_its_column(bookings_frame, agg, expected):
    # All six, so a new reducer cannot be added without a reading to prove it.
    assert GAUGE_AGGREGATIONS == ("sum", "mean", "median", "min", "max", "last")
    (ring,) = _rings(_gauge(bookings_frame, ["north"], agg=agg))
    assert _reading(ring) == expected


@pytest.mark.parametrize("agg", GAUGE_AGGREGATIONS)
def test_gauge_an_empty_column_is_no_data_not_a_zero_total(bookings_frame, agg):
    # THE TYPE'S HEADLINE TRAP, swept over every reduction because only ONE of them lies —
    # which makes it worse, not better: the bug would live in `sum` alone and look like a
    # rounding quirk in the other five.
    assert (
        bookings_frame["partner_deals"].sum() == 0.0
    )  # <- pandas' answer: the IDENTITY
    assert pd.Series([], dtype="float64").sum() == 0.0  # <- and for an empty column too
    # A gauge that believed pandas would draw an emphatic, entirely fictional ZERO ring at the
    # dial's floor — a confident CLAIM ("we booked nothing") where the truth is "nobody
    # reported". The empty test runs ABOVE the reducer, so it is unrepresentable, not
    # special-cased.
    (ring,) = _rings(_gauge(bookings_frame, ["partner_deals"], agg=agg))
    assert _reading(ring) is EnforcedNull


def test_gauge_an_empty_ring_is_kept_not_dropped(bookings_frame):
    # boxplot's all-missing-group rule — and here it is geometrically FORCED. The radii are a
    # function of the SELECTION, so dropping a ring would resize and recolour every ring below
    # it, and the KPI ("Series plotted") would count a ring the chart never drew. Keeping it is
    # what makes marks == series == len(y_cols) an invariant, which is why gauge needs no
    # MARK_METRICS entry and no count_marks rule.
    cols = ["north", "south", "emea", "partner_deals"]
    rings = _rings(_gauge(bookings_frame, cols, agg="sum"))
    assert len(rings) == len(cols)
    assert [r["name"] for r in rings] == cols
    assert _reading(rings[3]) is EnforcedNull
    # The null ring is a BARE EnforcedNull, not {"y": EnforcedNull, ...}: highcharts-core drops
    # a null `y` out of a point dict entirely, leaving a point with no value at all.
    assert rings[3]["data"] == [EnforcedNull]
    js = make_chart(bookings_frame, "solidgauge", None, cols).to_js_literal()
    assert js and "data:[[null]]" in "".join(js.split())


def test_gauge_the_empty_ring_is_still_named_in_the_legend(bookings_frame):
    # A null point draws no arc AND no data label, so the legend is the ONLY thing that names
    # it. That is why gauge is the one type whose legend is not redundant.
    opts = _gauge(bookings_frame, ["north", "partner_deals"])
    assert opts["legend"]["enabled"] is True
    assert all(r["showInLegend"] is True for r in _rings(opts))


def test_gauge_drops_non_finite_observations_before_reducing():
    # An inf cannot be summed with anything (it poisons the total), and it cannot be
    # SERIALIZED: `to_js_literal` emits the bare token `inf`, which is not valid JS.
    df = pd.DataFrame({"v": [10.0, float("inf"), 20.0, float("nan")]})
    (ring,) = _rings(_gauge(df, ["v"], agg="sum"))
    assert _reading(ring) == 30.0  # the two finite ones


def test_gauge_a_reduction_that_overflows_becomes_a_null_ring():
    # Gauge is the SECOND type (after boxplot) that does ARITHMETIC on the values, so it can
    # manufacture a non-finite reading out of finite inputs — boxplot's overflow lesson, one
    # type over. 1e308 parses out of a plain CSV.
    df = pd.DataFrame({"v": [1e308, 1e308]})
    with (
        warnings.catch_warnings()
    ):  # numpy warns on the overflow; that IS the point here
        warnings.simplefilter("ignore", RuntimeWarning)
        assert df["v"].sum() == float("inf")  # finite inputs, non-finite output
    (ring,) = _rings(_gauge(df, ["v"], agg="sum"))
    assert _reading(ring) is EnforcedNull
    js = make_chart(df, "solidgauge", None, ["v"], agg="sum").to_js_literal()
    assert js and "inf" not in js.lower()


def test_gauge_last_reads_the_last_KNOWN_reading():
    # `_finite_values` runs first, so `last` is the last reading that EXISTS, not the last cell
    # (which may be blank — and `float(nan)` would null the whole ring).
    df = pd.DataFrame({"v": [5.0, 7.0, float("nan")]})
    (ring,) = _rings(_gauge(df, ["v"], agg="last"))
    assert _reading(ring) == 7.0


def test_gauge_rejects_a_non_numeric_column_and_an_unknown_aggregation():
    df = pd.DataFrame({"v": ["x", "y"]})
    with pytest.raises(ValueError):
        _gauge(df, ["v"])  # `_finite_values` casts first, as float() does elsewhere
    with pytest.raises(ValueError, match="aggregation"):
        _gauge(pd.DataFrame({"v": [1.0]}), ["v"], agg="mode")


# --- the dial ------------------------------------------------------------------------ #
def test_gauge_dial_is_derived_from_the_readings_not_the_raw_column(bookings_frame):
    # THE OTHER HEADLINE. Under `sum` a reading EXCEEDS every observation in its own column
    # (436 vs a max cell of 63), so a dial derived from the raw column would end at 100 and pin
    # every ring past the end of its own scale — "everyone smashed target", drawn confidently.
    # Reducing FIRST, with the very reduction the rings draw, makes that unrepresentable.
    cols = ["north", "south", "emea"]
    assert bookings_frame[cols].max().max() == 63  # the raw column's ceiling
    opts = _gauge(bookings_frame, cols, agg="sum")
    assert (opts["yAxis"]["min"], opts["yAxis"]["max"]) == (0.0, 500.0)  # 436 -> 500
    # And every reading fits inside its own dial, under EVERY reduction.
    for agg in GAUGE_AGGREGATIONS:
        low, high = gauge_dial(bookings_frame, cols, agg)
        readings = [
            _reading(r)
            for r in _rings(_gauge(bookings_frame, cols, agg=agg))
            if _reading(r) is not EnforcedNull
        ]
        assert all(low <= v <= high for v in readings), agg


@pytest.mark.parametrize(
    ("value", "ceiling"),
    [(436.0, 500.0), (79.0, 100.0), (9.0, 10.0), (0.83, 1.0), (100.0, 100.0)],
)
def test_gauge_dial_rounds_the_ceiling_outward(value, ceiling):
    # A dial ending exactly at the largest reading draws that ring 100% full whatever it holds.
    # "436 of 500" is the only reading a gauge gives, so the 500 has to come from somewhere.
    _low, high = gauge_dial(pd.DataFrame({"v": [value]}), ["v"], "sum")
    assert high == ceiling


def test_gauge_dial_survives_overflow_and_underflow():
    # The two ways the nice-ceiling arithmetic breaks on real input. `2.0 * 1e308` is `inf`,
    # which would put the bare token `inf` in the emitted JS; `10.0 ** -324` is `0.0`, which
    # would leave the dial with no extent at all. In both cases the reading is finite and
    # positive, so it is its own ceiling.
    _low, high = gauge_dial(pd.DataFrame({"v": [1.5e308]}), ["v"], "sum")
    assert math.isfinite(high)
    js = make_chart(
        pd.DataFrame({"v": [1.5e308]}), "solidgauge", None, ["v"]
    ).to_js_literal()
    assert js and "inf" not in js.lower()
    _low, tiny = gauge_dial(pd.DataFrame({"v": [5e-324]}), ["v"], "sum")
    assert tiny > 0


def test_gauge_dial_floors_at_zero_and_an_all_negative_one_sweeps_from_zero():
    # A gauge is read FROM ZERO: an arc's LENGTH is its magnitude. Left unset, Highcharts sweeps
    # each arc from the axis MINIMUM, which INVERTS an all-negative dial — on a -200..0 dial the
    # -40 would draw a LONGER arc than the -155, so the SMALLEST loss would look like the
    # biggest. `threshold` is what stops that.
    df = pd.DataFrame({"a": [-155.0], "b": [-40.0]})
    opts = _gauge(df, ["a", "b"], agg="sum")
    assert (opts["yAxis"]["min"], opts["yAxis"]["max"]) == (-200.0, 0.0)
    assert all(r["threshold"] == 0.0 for r in _rings(opts))
    # A positive frame's dial floors at zero rather than at its smallest reading.
    up = _gauge(pd.DataFrame({"v": [40.0]}), ["v"])
    assert up["yAxis"]["min"] == 0.0


def test_gauge_dial_of_an_empty_or_all_missing_selection_is_still_drawable():
    # gauge_dial is TOTAL — it runs above the app's empty-Y guard, like count_marks — and it
    # must never return a degenerate 0..0, which Highcharts would divide by.
    df = pd.DataFrame({"v": [float("nan")]})
    assert gauge_dial(df, [], "sum") == (0.0, 100.0)
    assert gauge_dial(df, ["v"], "sum") == (0.0, 100.0)
    assert gauge_dial(pd.DataFrame({"v": [0.0]}), ["v"], "sum") == (0.0, 100.0)


def test_gauge_dial_override_replaces_the_derived_one(bookings_frame):
    opts = _gauge(bookings_frame, ["north"], agg="sum", dial=(0.0, 1000.0))
    assert (opts["yAxis"]["min"], opts["yAxis"]["max"]) == (0.0, 1000.0)


@pytest.mark.parametrize("bad", [(5.0, 5.0), (100.0, 50.0), (0.0, float("inf"))])
def test_gauge_rejects_a_dial_with_no_span(bookings_frame, bad):
    with pytest.raises(ValueError) as excinfo:
        _gauge(bookings_frame, ["north"], dial=bad)
    # The app's warning IS the exception's message — they cannot drift apart.
    assert explain_gauge_error(bad) == str(excinfo.value)
    assert explain_gauge_error(None) is None  # "derive it" is not an error
    assert explain_gauge_error((0.0, 10.0)) is None


# --- the two silent-drop traps, pinned on the EMITTED JS ------------------------------ #
def test_gauge_arc_colour_rides_the_point_and_the_radius_rides_the_series(
    bookings_frame,
):
    # THE NASTIEST THING ABOUT THIS TYPE: two adjacent properties on OPPOSITE levels, each
    # silently wrong on the other's.
    cols = ["north", "south", "emea"]
    opts = _gauge(bookings_frame, cols)
    rings = _rings(opts)
    # The RADIUS must be on the SERIES. A point-level one is accepted by Chart.from_options and
    # then silently dropped — and it is the canonical Highcharts activity-gauge recipe.
    assert all("radius" in r and "innerRadius" in r for r in rings)
    js = make_chart(bookings_frame, "solidgauge", None, cols).to_js_literal()
    assert js
    flat = "".join(js.split())
    assert "radius:'100.0%'" in flat  # survived to the JS
    # The COLOUR must be on the POINT. Highcharts' solidgauge defaults `colorByPoint: true` and
    # highcharts-core models no `color_by_point` at all, so the default CANNOT be turned off:
    # every series' single point is index 0 of its own colorCounter, so a series-level `color`
    # serializes perfectly and every ring still resolves to colors[0] — three hues in the JS,
    # three identical blue arcs on screen, beside pane tracks showing the three TRUE hues.
    for ring, hue in zip(rings, DEFAULT_COLORS, strict=False):
        assert ring["data"][0]["color"] == hue  # the ARC
        # And the same hue AGAIN, on the marker, for the LEGEND swatch — the same drop wearing a
        # third hat. A series-level `color` serializes perfectly and Highcharts renders the
        # legend bullet grey anyway (verified by rendering; removing the series `color` changed
        # nothing at all, so it does no work here). The legend is the only thing that names an
        # EMPTY ring, and a grey bullet cannot be matched back to a band. A solid gauge draws no
        # markers on an arc, so this is inert everywhere else.
        assert ring["marker"] == {"fillColor": hue, "symbol": "circle"}
        assert (
            "color" not in ring
        )  # it would be an option that looks load-bearing and isn't
    for hue in DEFAULT_COLORS[:3]:
        assert f"color:'{hue}'" in flat
    # And `colorByPoint` must appear NOWHERE: it cannot be emitted, and the one that would
    # survive is the wrong one anyway.
    assert "colorByPoint" not in js


def test_gauge_takes_a_custom_palette_and_a_short_one_cycles(bookings_frame):
    # A ring's hue is its arbitrary IDENTITY (a pie slice's rule, not waterfall's semantic
    # red-means-loss), so it reads from the OVERRIDABLE palette — and a short one must WRAP
    # rather than IndexError.
    rings = _rings(
        _gauge(
            bookings_frame, ["north", "south", "emea"], colors=["#111111", "#222222"]
        )
    )
    assert [r["data"][0]["color"] for r in rings] == ["#111111", "#222222", "#111111"]


def test_gauge_pane_pulls_in_highcharts_more_without_which_the_chart_is_blank(
    bookings_frame,
):
    # The pane is LOAD-BEARING, not decoration. `get_script_tags` emits highcharts-more ONLY
    # when the options tree carries a `pane` key — not for the series type, not for
    # plotOptions.solidgauge, not for a series radius — and a solid gauge WITHOUT
    # highcharts-more draws an EMPTY SVG in the browser: zero series paths, no error band, no
    # Python-side error. The export server rasterizes it regardless, so dropping the pane would
    # make the two render modes silently DISAGREE.
    chart = make_chart(bookings_frame, "solidgauge", None, ["north"])
    tags = " ".join(chart.get_script_tags())
    assert "highcharts-more.js" in tags
    assert "modules/solid-gauge.js" in tags
    js = chart.to_js_literal()
    assert js and "pane" in js


def test_gauge_pane_tracks_mirror_the_ring_radii(bookings_frame):
    cols = ["north", "south", "emea"]
    opts = _gauge(bookings_frame, cols)
    tracks = opts["pane"]["background"]
    rings = _rings(opts)
    assert len(tracks) == len(rings)
    for track, ring in zip(tracks, rings, strict=True):
        assert track["outerRadius"] == ring["radius"]
        assert track["innerRadius"] == ring["innerRadius"]


@pytest.mark.parametrize("count", [1, 2, 5, 12, 40])
def test_gauge_ring_radii_nest_without_ever_inverting(count):
    # Two caps, each stopping the band degenerating at one END of the range.
    # MANY rings: a fixed 3% gap exceeds the band past ~21 of them, at which point inner > outer
    # and Highcharts draws garbage — and a wide CSV with 40 numeric columns is one click away.
    # The geometry DEGRADES (thin rings) rather than breaking; capping the RINGS instead would
    # mean dropping a column the user asked for.
    df = pd.DataFrame({f"c{i}": [float(i + 1)] for i in range(count)})
    rings = _rings(_gauge(df, list(df.columns)))
    assert len(rings) == count
    radii = [(float(r["radius"][:-1]), float(r["innerRadius"][:-1])) for r in rings]
    for outer, inner in radii:
        assert outer > inner  # never inverted
        # FEW rings: with the whole radius to divide, ONE column would draw an arc 61% thick — a
        # fat disc with a pinhole, which reads as a pie with a bite out of it, not a gauge.
        # A ring has to look like a ring.
        assert outer - inner <= 30.0
    for (_o1, inner), (outer, _i2) in zip(radii, radii[1:], strict=False):
        assert inner >= outer  # each ring sits strictly inside the one before it


def test_gauge_ticks_are_silenced_by_width_not_by_tick_positions(bookings_frame):
    # The obvious `tickPositions: []` is PRUNED before it is emitted (an empty list), and the
    # tick dashes then stay visible ON the tracks even with the labels switched off.
    axis = _gauge(bookings_frame, ["north"])["yAxis"]
    assert axis["tickWidth"] == 0 and axis["minorTickWidth"] == 0
    assert "tickPositions" not in axis
    assert axis["labels"]["enabled"] is False


def test_gauge_labels_stack_in_the_hub_in_each_rings_own_hue(bookings_frame):
    cols = ["north", "south", "emea"]
    opts = _gauge(bookings_frame, cols)
    labels = [r["dataLabels"] for r in _rings(opts)]
    # One line per ring, centred about the middle one.
    assert [lbl["y"] for lbl in labels] == [-17, 0, 17]
    assert [lbl["style"]["color"] for lbl in labels] == list(DEFAULT_COLORS[:3])
    shared = opts["plotOptions"]["solidgauge"]["dataLabels"]
    assert shared["enabled"] is True
    # `allowOverlap` is load-bearing: Highcharts otherwise HIDES a colliding label by rendering
    # the <text> and turning it INVISIBLE — the element stays in the DOM, so every assertion
    # about it still passes while a ring's value is simply absent from the chart.
    assert shared["allowOverlap"] is True
    # `useHTML` is pinned False: the export server silently drops HTML labels, so the iframe and
    # the PNG would disagree.
    assert shared["useHTML"] is False


def test_gauge_many_rings_disable_the_labels_EXPLICITLY():
    # Gated on ring count, like heatmap's cells and waterfall's steps — but with a twist none of
    # them has: a gauge's dataLabels default to ON, so merely OMITTING the key (heatmap's style)
    # would be a gate that did nothing at all, and twenty labels would pile up at one offset.
    df = pd.DataFrame({f"c{i}": [float(i + 1)] for i in range(6)})
    opts = _gauge(df, list(df.columns))
    assert opts["plotOptions"]["solidgauge"]["dataLabels"] == {"enabled": False}
    assert all("dataLabels" not in r for r in _rings(opts))
    js = make_chart(df, "solidgauge", None, list(df.columns)).to_js_literal()
    assert js and "enabled:false" in "".join(js.split())


def test_gauge_tooltip_names_the_series_not_the_point_or_the_category(bookings_frame):
    # A third answer for a third reason: waterfall needs {point.category} (its points are
    # positional), sunburst and xrange need {point.name} (their categories are on the wrong
    # axis) — and a gauge ring holds exactly ONE point, so the mark's identity is not on the
    # point at all. It IS the series. The tooltip is PER RING now (the reading is baked in
    # Python and differs per ring), so it lives on the series, not chart-wide.
    (ring,) = _rings(_gauge(bookings_frame, ["north"]))
    assert "{series.name}" in ring["tooltip"]["pointFormat"]


def test_gauge_subtitle_states_the_aggregation_and_the_dial(bookings_frame):
    # The scale is INVISIBLE on the chart (a 360° gauge has nowhere to put an axis) and the
    # Static PNG has no tooltip, so without this a downloaded gauge cannot be decoded at all:
    # "436" means nothing until you know it is a sum of eight weeks against a 500 target.
    opts = _gauge(bookings_frame, ["north"], agg="sum")
    assert opts["subtitle"]["text"] == "sum · dial 0 – 500"


# --- no label channel ----------------------------------------------------------------- #
def test_gauge_ignores_x_col_entirely(bookings_frame):
    # Gauge is the first type with NO LABEL CHANNEL, and this is the pin that makes the
    # `_label_ok` exception more than a formality. Naming a column changes NOTHING...
    without = make_chart(bookings_frame, "solidgauge", None, ["north"]).to_js_literal()
    with_x = make_chart(bookings_frame, "solidgauge", "week", ["north"]).to_js_literal()
    assert without == with_x
    # ...and — the load-bearing half — a frame whose label column is ENTIRELY undrawable still
    # aggregates every row. If the shared `_label_ok` filter reached this branch it would drop
    # all eight rows and the ring would come back null; if it dropped only some, the total would
    # come back SMALLER, drawn confidently, with nothing on the page saying so. A row filter over
    # an AGGREGATE does not drop a mark — it silently changes a NUMBER.
    unlabelled = bookings_frame.assign(week=[float("nan")] * 8)
    (ring,) = _rings(_gauge(unlabelled, ["north"], agg="sum"))
    assert _reading(ring) == 436.0  # every row still counted


def test_every_other_type_requires_an_x_col(bookings_frame):
    # The column role stops being universal, so the signature has to admit it — and a pure-API
    # caller who omits x_col for a pie deserves a message, not a KeyError out of pandas.
    with pytest.raises(ValueError, match="x column"):
        build_options(bookings_frame, "line", None, ["north"])


def test_count_marks_has_no_rule_for_gauge(bookings_frame):
    # Its marks ARE its series, so `len(y_cols)` is an invariant and "Series plotted" is already
    # literally the ring count. A rule here would be the can't-drift rule run backwards: a second
    # computation of a fact that cannot differ from the first.
    with pytest.raises(ValueError, match="no rule"):
        count_marks(bookings_frame, "solidgauge", None, ["north"])


def test_gauge_light_mode_shape_and_dark_mode_themes_the_tracks(bookings_frame):
    cols = ["north", "south"]
    light = _gauge(bookings_frame, cols)
    # There is no `borderColor` anywhere, and there CANNOT be: SolidGaugeSeries models no border
    # at any level, so one would be silently dropped (boxplot's fillColor, exactly).
    assert "borderColor" not in light["plotOptions"]["solidgauge"]
    assert set(light["plotOptions"]["solidgauge"]) == {
        "rounded",
        "linecap",
        "stickyTracking",
        "dataLabels",
    }
    assert all(t["backgroundColor"] == "#334155" for t in light["pane"]["background"])

    dark = _gauge(bookings_frame, cols)
    # The ONE hook this type can have, and the first to reach a TOP-LEVEL key rather than
    # plotOptions: the tracks. Left unset they take a Highcharts default that
    # _LIGHT_COLOR_SCHEME_CSS pins to its LIGHT resolution in BOTH themes, so every dial would
    # sit on a pale rail against the dark shell.
    assert all(t["backgroundColor"] == "#334155" for t in dark["pane"]["background"])
    # The ring hues are untouched (the palette is theme-shared), and so are the hub labels,
    # which carry them.
    assert [r["data"][0]["color"] for r in _rings(dark)] == list(DEFAULT_COLORS[:2])
    assert dark["subtitle"]["style"]["color"]  # the subtitle follows the chrome


def test_weekly_bookings_sample_builds_a_gauge():
    from sample_data import SAMPLES

    df = SAMPLES["Weekly bookings by region (solidgauge)"]()
    cols = ["north", "south", "emea", "partner_deals"]
    opts = _gauge(df, cols, agg="sum")
    rings = _rings(opts)
    assert len(rings) == 4
    assert _reading(rings[0]) == 436.0
    assert _reading(rings[3]) is EnforcedNull  # the trap, reachable from the app
    assert opts["yAxis"]["max"] == 500.0


# --------------------------------------------------------------------------- #
# Needle gauge — the family's second half: the same readings, pointed at a DRAWN scale
#
# Everything ABOVE the mark (the reduction, the empty-column trap, the readings-derived dial,
# the six aggregations, the non-finite policy) is shared with solidgauge and is already pinned
# there — `_dial_from_readings` and `_gauge_value` are the same functions. These tests pin only
# what is genuinely the needle's, and almost every one of them is a MEASUREMENT: the properties
# below fail DIFFERENTLY here than they do on the ring, and copying the sibling's answers on
# faith would have shipped four separate silent bugs.
# --------------------------------------------------------------------------- #
def _needle(df, y_cols, **kwargs) -> dict:
    return build_options(df, "gauge", None, list(y_cols), **kwargs)


def _needles(opts: dict) -> list[dict]:
    return opts["series"]


def _needle_reading(needle: dict):
    """The one number a needle points at — or EnforcedNull when its column held no data."""
    (point,) = needle["data"]
    return point


def test_needle_draws_one_needle_per_column_reduced_to_one_number(bookings_frame):
    opts = _needle(bookings_frame, ["north", "south", "emea"], agg="sum")
    needles = _needles(opts)
    assert [n["name"] for n in needles] == ["north", "south", "emea"]
    assert [_needle_reading(n) for n in needles] == [436.0, 334.0, 175.0]
    # marks == series == len(y_cols): the invariant the whole family rests on, and the reason
    # neither gauge needs a `count_marks` rule or a MARK_METRICS entry.
    assert opts["chart"]["type"] == "gauge"


def test_needle_the_empty_column_is_a_null_not_a_confident_zero(bookings_frame):
    # The family's headline trap, and it bites HARDER on a needle than on a ring: pandas sums an
    # all-NaN column to 0.0 (the additive identity), and a needle swung to the floor of the dial
    # is INDISTINGUISHABLE from a real reading of zero — an arc at least draws nothing.
    assert pd.Series([float("nan")] * 8).sum() == 0.0  # the reason this test exists
    (needle,) = _needles(_needle(bookings_frame, ["partner_deals"], agg="sum"))
    assert _needle_reading(needle) is EnforcedNull
    # ...and it is KEPT, not dropped, so the needle count still equals the column count. The
    # legend is then the ONLY thing naming it: a null point draws no needle AND no label.
    assert needle["showInLegend"] is True
    assert needle["name"] == "partner_deals"


def test_needle_a_null_point_needs_no_ternary_unlike_the_ring(bookings_frame):
    # The ring must branch on emptiness because a LIVE ring carries `color` on the POINT (its arc
    # reads the point, not the series) while a null point must not — highcharts-core drops a null
    # `y` out of a point dict entirely, leaving a point with no value at all. A needle's colour is
    # on its DIAL, so the point is just the number and both cases are the same expression.
    live, empty = _needles(
        _needle(bookings_frame, ["north", "partner_deals"], agg="sum")
    )
    assert live["data"] == [436.0]  # a bare number, NOT {"y": ..., "color": ...}
    assert empty["data"] == [EnforcedNull]
    js = make_chart(
        bookings_frame, "gauge", None, ["north", "partner_deals"]
    ).to_js_literal()  # stubbed str | None; `js and` guards the None case
    assert js and "data:[[null]]" in "".join(js.split())  # a real null point survives


@pytest.mark.parametrize("count", [1, 2, 3, 5, 12, 40])
def test_needle_lengths_stagger_and_never_reach_the_pivot(count):
    # The fix for a corruption, not a decoration. Two columns with EQUAL readings put two needles
    # at the SAME angle, and Highcharts draws the later series ON TOP — at one length the second
    # needle covers the first COMPLETELY, so N series draw fewer than N needles while the legend
    # and the labels both go on naming N. `marks == series` becomes a lie ON SCREEN, in the one
    # place a reader would never think to check. Staggering exposes each needle's TIP.
    lengths = _needle_radii(count)
    assert len(lengths) == count
    assert lengths == sorted(
        lengths, reverse=True
    )  # y_cols[0] is the headline: longest
    assert (
        len(set(lengths)) == count
    )  # every needle a DIFFERENT length, or the fix is not one
    # Degrades rather than breaks, exactly like `_gauge_rings`: at 40 columns the needles bunch
    # up, but all 40 are there and none has walked back into the pivot (or past it, to a negative
    # radius Highcharts draws as garbage). Capping the COUNT instead would drop a column the user
    # asked for.
    assert all(0 < length <= 100 for length in lengths)


def test_needle_the_staggered_lengths_actually_REACH_the_emitted_needles(
    bookings_frame,
):
    # The gap a mutation test found: `_needle_radii` was pinned in ISOLATION, and the only
    # options-level radius assertion was the count==1 case — where the stagger is vacuous by
    # construction. So replacing `_pct(length)` with `_pct(_NEEDLE_LONGEST_PCT)` in the branch —
    # which restores the exact bug the helper exists to prevent, every needle the same length,
    # two equal readings drawing as one — left the whole suite GREEN.
    #
    # A helper is not a behaviour until something calls it. This asserts the call.
    cols = ["north", "south", "emea"]
    opts = _needle(bookings_frame, cols)
    radii = [n["dial"]["radius"] for n in _needles(opts)]
    assert radii == [_pct(length) for length in _needle_radii(len(cols))]
    assert len(set(radii)) == len(cols)  # DISTINCT: the point of the whole exercise
    # And on the emitted JS, since a dial's geometry is exactly the sort of thing this library
    # accepts and then drops (the `pane.size` family).
    js = make_chart(bookings_frame, "gauge", None, cols).to_js_literal()
    flat = "".join(js.split()) if js else ""
    assert js and all(f"radius:'{r}'" in flat.replace('"', "'") for r in radii)


def test_needle_one_column_takes_the_full_length(bookings_frame):
    # The n=1 boundary: there is nothing to stagger against, and a lone needle stunted to the
    # shortest length would look like a bug.
    (needle,) = _needles(_needle(bookings_frame, ["north"]))
    assert needle["dial"]["radius"] == "88.0%"


def test_needle_every_dial_carries_topwidth_or_the_chart_cannot_be_built(
    bookings_frame,
):
    # THE family's one shared trap, and the nastiest thing about this type. `plot_options/gauge.py`
    # and the series' own DialOptions both validate `top_width` WITHOUT `allow_empty=True`, so any
    # dial dict omitting `topWidth` raises EmptyValueError — out of a validator that names neither
    # the key, nor `dial`, nor the series. And it fires at `Chart.from_options`, one layer BELOW
    # `build_options`: an options-dict assertion would pass while the chart cannot be built at all,
    # and the app's interactive path (which does not catch builder errors) would show a bare
    # traceback. Hence: this test drives `make_chart`, not `build_options`.
    opts = _needle(bookings_frame, ["north", "south"])
    assert all(n["dial"]["topWidth"] == 1 for n in _needles(opts))
    # There is NO `plotOptions.gauge.dial`, and that absence is pinned rather than merely true.
    # It was carried at first, on the reasoning that `topWidth` is demanded at "both levels" —
    # which is false: every needle carries its own complete dial (it must, for its hue and its
    # length), so a plotOptions dial defaults nothing and does no work. Deleting it changes not one
    # byte of the emitted JS. An option that LOOKS load-bearing and isn't is the exact defect this
    # module tests other libraries for, and one of ours would be worse — it came with a comment
    # swearing it was needed.
    assert "dial" not in opts["plotOptions"]["gauge"]
    js = make_chart(
        bookings_frame, "gauge", None, ["north", "south"]
    ).to_js_literal()  # stubbed str | None; `js and` guards the None case
    # One per needle, and only per needle — the trap is guarded where it actually bites.
    assert js and "".join(js.split()).count("topWidth:1") == 2


def test_needle_hue_rides_the_dial_and_the_legend_but_never_the_point(bookings_frame):
    # TWO levels, and NOT two of the ring's three — there is no overlap at all. On a solid gauge a
    # series-level `color` serializes perfectly and reaches NOTHING (the arc reads the POINT,
    # because `colorByPoint: true` is a default highcharts-core cannot express turning off; the
    # legend bullet draws grey and needs a `marker.fillColor`). On a needle, `color` reaches ONLY
    # the legend — the needle itself is BLACK unless `dial.backgroundColor` says otherwise.
    # Verified by rendering `color` alone: three perfectly coloured legend swatches above three
    # black needles. Same property, opposite failure.
    cols = ["north", "south", "emea"]
    opts = _needle(bookings_frame, cols)
    hues = list(DEFAULT_COLORS[:3])
    assert [n["dial"]["backgroundColor"] for n in _needles(opts)] == hues  # the NEEDLE
    assert [n["color"] for n in _needles(opts)] == hues  # the LEGEND swatch
    # The point carries the number and nothing else — no `color` to be read (the ring's level),
    # and no `marker`, which is the ring's legend hack and does no work at all here.
    assert all(not isinstance(n["data"][0], dict) for n in _needles(opts))
    assert all("marker" not in n for n in _needles(opts))
    js = make_chart(bookings_frame, "gauge", None, cols).to_js_literal()
    assert js and (
        "colorByPoint" not in js
    )  # solidgauge's un-turn-off-able default is not this type's


def test_needle_asks_for_the_legend_explicitly_because_a_gauge_series_defaults_to_hiding_it(
    bookings_frame,
):
    # A gauge series defaults to `showInLegend: false`, unlike almost every other type — so
    # `legend.enabled` alone renders NO legend at all (verified by rendering: it was simply
    # absent). It has to be asked for twice. And it matters more here than anywhere: a needle
    # carries no name on the chart, so past the label gate — and for an empty column, whose null
    # point draws neither needle nor label — the legend is the ONLY thing that says which is which.
    opts = _needle(bookings_frame, ["north", "south"])
    assert opts["legend"]["enabled"] is True
    assert all(n["showInLegend"] is True for n in _needles(opts))


def test_needle_pivot_is_one_neutral_colour_not_one_per_series(bookings_frame):
    # N needles pivot at the SAME POINT, so N hued pivots draw N discs on top of each other and
    # the reader sees whichever series happened to be drawn last — a hub wearing one arbitrary
    # column's identity. It is not a mark and has no identity, so it takes the module's existing
    # off-palette slate (sunburst's root colour), which reads on both backgrounds and needs no
    # dark flip. Left unset it defaults to BLACK, invisible on the dark shell.
    opts = _needle(bookings_frame, ["north", "south", "emea"])
    assert opts["plotOptions"]["gauge"]["pivot"]["backgroundColor"] == "#64748b"
    assert all("pivot" not in n for n in _needles(opts))  # never per series


def test_needle_resolves_highcharts_more_from_the_chart_type_alone(bookings_frame):
    # The family's sharpest INVERSION, and the reason solidgauge's pane comment must not be
    # copied here. A solid gauge resolves highcharts-more ONLY from its `pane` — drop that key and
    # the browser draws an empty SVG while the export server renders perfectly. A needle resolves
    # it from `chart.type`, so its pane is geometry and nothing hangs on it.
    chart = make_chart(bookings_frame, "gauge", None, ["north"])
    assert "highcharts-more" in chart.get_required_modules()
    # ...and it does so with the pane taken away entirely — which is what "from the type alone"
    # means, and the only way to show it.
    from highcharts_core.chart import Chart

    paneless = build_options(bookings_frame, "gauge", None, ["north"])
    paneless.pop("pane")
    assert "highcharts-more" in Chart.from_options(paneless).get_required_modules()


def test_needle_pane_is_an_arc_not_a_disc(bookings_frame):
    # A pane background defaults to a CIRCLE, so an arc gauge left to itself draws a full disc
    # behind its semicircle — and `_themed` would then flip a whole dark disc in. `shape` has to
    # be said out loud. (`size` is NOT set, and must not be: highcharts-core's Pane.size setter
    # validates a percentage string and then never assigns it — see the next test.)
    opts = _needle(bookings_frame, ["north"])
    (face,) = opts["pane"]["background"]
    assert face["shape"] == "arc"
    assert (opts["pane"]["startAngle"], opts["pane"]["endAngle"]) == (-90, 90)


def test_needle_pane_says_what_the_dial_is_and_nothing_about_where_to_put_it(
    bookings_frame,
):
    # NEITHER key, and that is a conclusion rather than an omission — which is why it is pinned.
    #
    # `size` is a SILENT DROP, found by reading the library: `options/pane.py`'s setter runs
    # `validators.string(value)`, checks the result for '%', and then falls off the end WITHOUT
    # EVER ASSIGNING `self._size` — only the numeric `except` branch writes it. So the `size: "85%"`
    # every Highcharts gauge demo sets is accepted and discarded. (`inner_size`, ten lines above
    # it, assigns in both branches: one copy-paste slip, not a policy.)
    #
    # And without `size`, `center` cannot be made safe: Highcharts reserves no room for the tick
    # labels outside the pane, and the pane's radius scales with the plot box. At 58% the topmost
    # label printed through the subtitle; at 65% it was clean at 300px and 800px and CLIPPED CLEAN
    # OFF THE CANVAS at 420 — a failure that is not even monotonic in the height, which is the tell
    # that it is not a number to be tuned. Highcharts' own default is correct at every height the
    # app offers, because it is the one placement that knows what the labels need.
    #
    # This test exists so nobody "helpfully" re-adds either one.
    opts = _needle(bookings_frame, ["north"])
    assert "size" not in opts["pane"]
    assert "center" not in opts["pane"]
    assert set(opts["pane"]) == {"startAngle", "endAngle", "background"}
    js = make_chart(bookings_frame, "gauge", None, ["north"]).to_js_literal()
    flat = "".join(js.split()) if js else ""
    assert js and "size:" not in flat and "center:" not in flat


def test_needle_draws_the_axis_it_points_at(bookings_frame):
    # The type's whole reason to exist, and the one thing a solid gauge cannot have: a 360° ring
    # has nowhere to put an axis, so it prints its dial in a subtitle. A needle's reading IS an
    # angle against a drawn scale, so the ticks are the chart.
    opts = _needle(bookings_frame, ["north"], agg="sum")
    assert (opts["yAxis"]["min"], opts["yAxis"]["max"]) == (
        0.0,
        500.0,
    )  # 436 -> a 0..500 dial
    assert (
        opts["yAxis"]["tickWidth"] == 2
    )  # DRAWN — the solid gauge silences its ticks to 0
    # `gridLineWidth` is pinned to 0 rather than left to Highcharts, because `_themed` writes a
    # gridLineColor onto every axis it finds — so a nonzero default would draw concentric
    # gridlines across the face that ONLY dark-mode readers would ever see.
    assert opts["yAxis"]["gridLineWidth"] == 0
    assert opts["yAxis"]["title"]["text"] == ""  # or Highcharts titles it "Values"


def test_needle_subtitle_states_only_the_aggregation(bookings_frame):
    # The solid gauge's subtitle carries `agg` AND the dial, because neither is on the chart. The
    # needle draws its dial, so repeating it here would be the one thing worse than not saying it:
    # two homes for one number, free to disagree. The `agg` stays, because no axis will ever say
    # that 436 is a sum of eight weeks rather than one week's reading.
    opts = _needle(bookings_frame, ["north"], agg="mean")
    assert opts["subtitle"]["text"] == "mean"
    assert "dial" not in opts["subtitle"]["text"]


@pytest.mark.parametrize("count", [1, 3, 8])
def test_needle_prints_nothing_in_the_mark_and_says_so_EXPLICITLY(count):
    # The sibling MUST print its readings in the hub — a 360° ring has nowhere to put an axis, so
    # the value can be read against nothing, and it pays for that with a gate, a measured leading
    # and a per-series offset. A needle points AT an axis that renders in the Static PNG too, and
    # its identity is in the legend it carries anyway. So it prints NOTHING in the mark and needs
    # no gate constant either: xrange's rule, reached from xrange's premise.
    #
    # DISABLED EXPLICITLY, which is the whole reason the key is here: a gauge's dataLabels default
    # to ON (unlike heatmap's and column's), so merely omitting it would print Highcharts' own
    # boxed label — N of them stacked at ONE anchor, since Highcharts renders every gauge series'
    # label at the same point. Swept over the count so no gate can creep back in unnoticed.
    wide = pd.DataFrame({f"c{i}": [float(i + 1)] for i in range(count)})
    opts = _needle(wide, list(wide.columns))
    assert opts["plotOptions"]["gauge"]["dataLabels"] == {"enabled": False}
    assert all("dataLabels" not in n for n in _needles(opts))
    assert (
        len(_needles(opts)) == count
    )  # ...and every column the user asked for is still drawn


def test_needle_off_the_dial_swings_past_the_scale_instead_of_lying_on_it(
    bookings_frame,
):
    # The one way this type could still draw a confident, plausible, WRONG chart, and it is
    # reachable in one keystroke: `gauge_dial` guarantees every reading sits inside the scale it
    # DERIVES, but the app's two Dial inputs accept any two numbers. Zoom the scale to 0..50 on a
    # column that sums to 436 and — left to Highcharts — the needle pegs EXACTLY ON the final tick,
    # pixel-identical to a true reading of 50 (verified by rendering). Nothing on the chart
    # contradicts it, and the Static PNG has no tooltip.
    #
    # It is also the ONE place the two gauges would disagree: a solid gauge in the same state fills
    # its arc and PRINTS "north: 436" in the hub, so its reader is told. A needle prints nothing in
    # the mark. The family must not be honest in one branch and mute in the other.
    opts = _needle(bookings_frame, ["north"], agg="sum", dial=(0.0, 50.0))
    assert (
        _needle_reading(_needles(opts)[0]) == 436.0
    )  # the TRUE value still reaches the chart
    assert opts["yAxis"]["max"] == 50.0  # ...on a dial that cannot show it
    assert (
        opts["plotOptions"]["gauge"]["overshoot"] == 5
    )  # ...so the needle swings PAST the end
    js = make_chart(
        bookings_frame, "gauge", None, ["north"], agg="sum", dial=(0.0, 50.0)
    ).to_js_literal()
    assert js and "overshoot:5" in "".join(js.split())  # and it survives the round-trip


def test_needle_face_carries_no_grid_not_even_the_minor_one(bookings_frame):
    # The MINOR gridline is the load-bearing half, which is exactly backwards from what you would
    # guess. `_themed` writes a `gridLineColor` onto every axis it finds, so the MAJOR width must
    # be pinned or dark-mode readers get concentric gridlines nobody asked for. But NOTHING themes
    # the minor one, and Highcharts defaults it to 1px of `#f2f2f2` — invisible on the light dial
    # face, and a BLAZING WHITE STARBURST across the dark one. Verified by rendering, on a chart
    # whose every unit test passed: the options were right and the picture was not.
    opts = _needle(bookings_frame, ["north"])
    assert opts["yAxis"]["gridLineWidth"] == 0
    assert opts["yAxis"]["minorGridLineWidth"] == 0
    assert opts["yAxis"]["minorTickWidth"] == 0


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_gauge_family_formats_a_reading_honestly_at_every_magnitude(chart_type):
    # The reading is the ONE flaw an options-dict assertion used to be unable to see: a bare
    # `{point.y}` prints the raw double, so a `mean` renders `66.44444444444444` off the side of
    # the chart. `.1f` trimmed that but rounded a real 0.008 reading to "0.0" — the family's own
    # confident zero, the exact lie `_gauge_value` fusses to keep an empty column from telling.
    # No FIXED-decimal Highcharts format is honest at both ends (Highcharts has no `g`), so the
    # reading is now formatted in PYTHON (`_gauge_reading_label`) and BAKED into each series' own
    # format string — which is what finally puts the NUMBER, not just the format string, under
    # test. Swept over the FAMILY because both types share `_gauge_value` and one reduction: they
    # must format one number one way, or a reader comparing them gets whichever branch they opened.
    smear = pd.DataFrame({"m": [1.0] * 8 + [2.0]})  # mean 1.111..., a repeating decimal
    (series,) = build_options(smear, chart_type, None, ["m"], agg="mean")["series"]
    assert (
        series["tooltip"]["pointFormat"] == "{series.name}: <b>1.1</b>"
    )  # smear trimmed
    assert "{point.y}" not in series["tooltip"]["pointFormat"]  # the raw double is gone

    tiny = pd.DataFrame(
        {"t": [0.008, 0.008]}
    )  # a real reading `.1f` would flatten to "0.0"
    (series,) = build_options(tiny, chart_type, None, ["t"], agg="mean")["series"]
    assert (
        series["tooltip"]["pointFormat"] == "{series.name}: <b>0.008</b>"
    )  # preserved

    # ...and the IN-MARK hub label, which is where the solidgauge smear was actually SEEN (the
    # needle prints nothing in the mark). The same baked reading, so the two cannot disagree.
    if chart_type == "solidgauge":
        (ring,) = build_options(smear, chart_type, None, ["m"], agg="mean")["series"]
        assert ring["dataLabels"]["format"] == "{series.name}: 1.1"

    # And on the emitted JS, because a format string is only a string until Highcharts reads it:
    # the baked reading must survive the round-trip and no `{point.y}` token may reappear.
    js = make_chart(tiny, chart_type, None, ["t"], agg="mean").to_js_literal()
    flat = "".join(js.split()) if js else ""
    assert js and "0.008" in flat and "{point.y}" not in flat


def test_gauge_reading_label_is_honest_and_length_bounded_at_every_magnitude():
    # The helper tested in isolation (like `_needle_radii`), because it is the one thing an
    # options-dict assertion structurally cannot see the OUTPUT of: only the format string.
    # Big numbers keep one decimal and a separator; small ones keep ~3 significant figures rather
    # than rounding to a confident zero; a null reading prints nothing.
    assert _gauge_reading_label(436.0) == "436"  # no trailing zero on an integer total
    assert _gauge_reading_label(66.44444444444444) == "66.4"  # the mean smear, trimmed
    assert _gauge_reading_label(1234567.0) == "1,234,567"  # separators, not scientific
    assert _gauge_reading_label(0.008) == "0.008"  # NOT "0.0" — the whole fix
    assert _gauge_reading_label(0.0) == "0"
    assert _gauge_reading_label(-155.0) == "-155"
    # A non-finite float has no reading to print — guarded so it can't leak "nan"/"inf" into a
    # label (belt-and-suspenders: `_gauge_value` already returns EnforcedNull for these).
    assert _gauge_reading_label(float("nan")) == ""
    assert _gauge_reading_label(float("inf")) == ""
    assert (
        _gauge_reading_label("absent") == ""
    )  # EnforcedNull stands in for a non-float

    # The label must stay SHORT even for a magnitude a dial cannot show — a 1e308 cell parses out
    # of a plain CSV (the module guards it elsewhere), and a fixed-decimal format would expand it
    # to a 300-digit string dumped into the emitted JS. Scientific keeps it legible and bounded.
    assert _gauge_reading_label(1e308) == "1e+308"
    for value in (1e308, 5e-324, 9e-5, 1.5e15, 1e-4, 9.99e14):
        assert len(_gauge_reading_label(value)) < 20


def test_needle_tooltip_names_the_series_not_the_point(bookings_frame):
    # A gauge series holds exactly ONE point, so the mark's identity is not on the point at all.
    # It IS the series. (`{point.name}` renders blank; `{point.category}` reads an axis that has
    # no categories.) The tooltip is PER NEEDLE (the reading is baked in Python) and is the only
    # place the exact reading survives, now that nothing is printed in the mark — the one thing
    # interactive mode has that the Static PNG does not, a real cost of axis-instead-of-labels.
    (needle,) = _needles(_needle(bookings_frame, ["north"], agg="sum"))
    assert needle["tooltip"]["pointFormat"] == "{series.name}: <b>436</b>"
    # ...and there is no chart-wide tooltip pointFormat left to drift from the per-series one.
    assert "pointFormat" not in _needle(bookings_frame, ["north"]).get("tooltip", {})


def test_needle_takes_a_custom_palette_and_a_short_one_cycles(bookings_frame):
    short = ["#111111", "#222222"]
    opts = _needle(bookings_frame, ["north", "south", "emea"], colors=short)
    # WRAPS rather than IndexErrors — a needle's hue is its arbitrary IDENTITY, so it rides the
    # overridable palette (waterfall's semantic red-means-loss is the opposite case).
    assert [n["dial"]["backgroundColor"] for n in _needles(opts)] == [*short, "#111111"]


def test_needle_no_plot_bands_because_the_data_never_said_low_was_bad(bookings_frame):
    # The red/amber/green zones a speedometer is popularly drawn with are a JUDGMENT, and the user
    # declared no target — they picked columns and a reduction. Solidgauge's argument against
    # `yAxis.stops`, unchanged. (It would also be a poor band: `thickness`, `innerRadius` and
    # `outerRadius` are all accepted by Chart.from_options and silently dropped.)
    opts = _needle(bookings_frame, ["north"])
    assert "plotBands" not in opts["yAxis"]
    assert "stops" not in opts["yAxis"]


def test_needle_ignores_x_col_entirely(bookings_frame):
    # The gauge family's defining pin, and the load-bearing half is the second one: this branch
    # sits ABOVE the shared `_label_ok` filter, and a row filter over an AGGREGATE does not drop a
    # mark — it silently changes a NUMBER.
    without = make_chart(bookings_frame, "gauge", None, ["north"]).to_js_literal()
    with_x = make_chart(bookings_frame, "gauge", "week", ["north"]).to_js_literal()
    assert without == with_x
    unlabelled = bookings_frame.assign(week=[float("nan")] * 8)
    (needle,) = _needles(_needle(unlabelled, ["north"], agg="sum"))
    assert _needle_reading(needle) == 436.0  # every row still counted


def test_needle_light_mode_shape_and_dark_mode_themes_the_dial_face(bookings_frame):
    light = _needle(bookings_frame, ["north", "south"])
    assert all(f["backgroundColor"] == "#334155" for f in light["pane"]["background"])

    dark = _needle(bookings_frame, ["north", "south"])
    # The family's ONE hook, widened from solidgauge's: the dial FACE. Left unset it takes a
    # Highcharts default that _LIGHT_COLOR_SCHEME_CSS pins to its LIGHT resolution in BOTH themes,
    # so the dial would sit on a glaring white rail against the dark shell (verified by rendering:
    # a white arc, unmissable). It is the only hook this type NEEDS — its axis is a real yAxis
    # dict, so `_themed`'s generic axis loop has already coloured the labels, ticks and line.
    assert all(f["backgroundColor"] == "#334155" for f in dark["pane"]["background"])
    assert dark["yAxis"]["labels"]["style"][
        "color"
    ]  # ...themed for free, unlike the ring's
    assert dark["yAxis"]["tickColor"]
    # The needle hues are untouched (the palette is theme-shared), and so is the slate pivot.
    assert [n["dial"]["backgroundColor"] for n in _needles(dark)] == list(
        DEFAULT_COLORS[:2]
    )
    assert dark["plotOptions"]["gauge"]["pivot"]["backgroundColor"] == "#64748b"


def test_needle_and_ring_cannot_disagree_about_the_readings_or_the_dial(bookings_frame):
    # The family invariant, stated as a test: the two types share `_gauge_value` and `gauge_dial`,
    # so given one frame, one selection and one reduction they MUST reduce to the same numbers and
    # scale them against the same dial. Only the mark differs. This is what `_dial_from_readings`
    # makes structural (a function that cannot see a raw column cannot derive a dial from one) —
    # and this test is what would catch the two branches drifting apart if anyone ever inlined it.
    cols = ["north", "south", "emea", "partner_deals"]
    for agg in GAUGE_AGGREGATIONS:
        ring = _gauge(bookings_frame, cols, agg=agg)
        needle = _needle(bookings_frame, cols, agg=agg)
        assert [_reading(r) for r in _rings(ring)] == [
            _needle_reading(n) for n in _needles(needle)
        ]
        assert (ring["yAxis"]["min"], ring["yAxis"]["max"]) == (
            needle["yAxis"]["min"],
            needle["yAxis"]["max"],
        )


def test_server_utilization_sample_builds_a_needle_gauge():
    from sample_data import SAMPLES

    df = SAMPLES["Server utilization (gauge)"]()
    cols = ["cpu_pct", "memory_pct", "disk_pct", "swap_pct"]
    opts = _needle(df, cols, agg="mean")
    needles = _needles(opts)
    assert len(needles) == 4
    # A mean of percentages lands the derived dial on the scale the reader already has in mind.
    assert opts["yAxis"]["max"] == 100.0
    assert (
        _needle_reading(needles[3]) is EnforcedNull
    )  # the trap, reachable from the app
    # ...and the three live readings SPREAD, which is what a needle gauge is for.
    live = [_needle_reading(n) for n in needles[:3]]
    assert max(live) - min(live) > 15


# --------------------------------------------------------------------------- #
# Static-PNG failure messages (the export server's three different answers)
# --------------------------------------------------------------------------- #
class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeRequestError(OSError):
    """Stands in for a ``requests`` exception: they all subclass ``OSError`` and carry a
    ``response`` (``None`` when no HTTP answer ever arrived). Faked rather than imported,
    for the same reason the helper doesn't import requests — and so these tests need no
    network."""

    def __init__(self, status_code: int | None = None):
        super().__init__("boom")
        self.response = _FakeResponse(status_code) if status_code else None


def test_export_failure_explains_a_build_error_without_blaming_the_network():
    # `except Exception` also catches a ValueError raised by build_options before any
    # request is made. Telling that user to check their network sends them somewhere the
    # bug isn't. Non-OSError == it never left the process.
    from highcharts_builder import explain_export_failure

    message = explain_export_failure(ValueError("At least one y column is required."))
    assert "could not be built" in message
    assert "not with your network" in message
    assert "export server" in message  # names what it did NOT reach


def test_export_failure_explains_an_unreachable_server():
    from highcharts_builder import explain_export_failure

    message = explain_export_failure(_FakeRequestError())  # no HTTP response at all
    assert "could not be reached" in message
    assert "Check your network" in message


@pytest.mark.parametrize("status", [400, 413, 422])
def test_export_failure_explains_a_rejected_chart(status):
    # The case that most needs saying out loud: the server answered, so it is plainly
    # reachable, and the fault is in the payload we sent it.
    from highcharts_builder import explain_export_failure

    message = explain_export_failure(_FakeRequestError(status))
    assert f"HTTP {status}" in message
    assert "rejected this chart" in message
    assert "not at your network" in message
    assert "check your network" not in message.lower()  # the old, wrong advice


@pytest.mark.parametrize("status", [500, 502, 503])
def test_export_failure_explains_a_server_side_error(status):
    from highcharts_builder import explain_export_failure

    message = explain_export_failure(_FakeRequestError(status))
    assert f"HTTP {status}" in message
    assert "internal error" in message
    assert "rejected" not in message


def test_app_static_png_error_uses_the_export_failure_explainer():
    # The helper is only worth having if the app calls it, and the AppTest suite stays on
    # the network-free interactive path, so it can never reach that except block. Pin the
    # call site by reading the source — the same mechanical-sync idea as
    # test_theme_colors_stay_in_sync_with_config.
    source = (ROOT / "streamlit_app.py").read_text()
    assert "explain_export_failure" in source
    assert "explain_export_failure(exc)" in source
    # And the old advice, which asserted a cause it could not know, is gone for good.
    assert (
        "This usually means the Highcharts export server is unreachable" not in source
    )


# --------------------------------------------------------------------------- #
# Sample datasets
# --------------------------------------------------------------------------- #
def test_sample_datasets_are_plottable_and_fresh():
    from sample_data import SAMPLES

    assert SAMPLES  # the app offers these when no CSV is uploaded
    for label, factory in SAMPLES.items():
        df = factory()
        assert not df.empty, label
        # The app stops with an error unless a dataset has a numeric column.
        assert df.select_dtypes("number").shape[1] >= 1, label

    # Each call returns a fresh frame, so per-session mutation can't leak.
    factory = next(iter(SAMPLES.values()))
    assert factory() is not factory()


def test_daily_temperature_sample_builds_an_areaspline_chart():
    # The areaspline sample is wired to its intended type: plot the real sample
    # as an areaspline and pin the shape it produces (24 hourly categories, one
    # full series) — ties the new dataset to the new chart type end to end.
    from sample_data import _daily_temperature

    df = _daily_temperature()
    opts = build_options(df, "areaspline", "hour", ["temp_c"])
    assert opts["chart"]["type"] == "areaspline"
    assert opts["series"][0]["name"] == "temp_c"
    assert opts["xAxis"]["categories"][0] == "00:00"
    assert len(opts["xAxis"]["categories"]) == len(opts["series"][0]["data"]) == 24


def test_country_economics_sample_builds_a_bubble_chart():
    # Ties the new bubble sample to its intended type end to end: a numeric GDP (X)
    # and life-expectancy (Y) pair with a population size column produces one
    # [x, y, z] triple per country row.
    from sample_data import _country_economics

    df = _country_economics()
    opts = build_options(
        df, "bubble", "gdp_per_capita_k", ["life_expectancy"], size_col="population_m"
    )
    assert opts["chart"]["type"] == "bubble"
    assert opts["series"][0]["name"] == "life_expectancy"
    assert len(opts["series"][0]["data"]) == len(df)
    assert len(opts["series"][0]["data"][0]) == 3  # [x, y, z]


def test_product_ratings_sample_builds_a_radar_chart():
    # Ties the new radar sample to its intended type end to end: a category axis
    # (attribute) with two numeric product-score series produces a polar line
    # chart, one series per product, each covering every attribute row.
    from sample_data import _product_ratings

    df = _product_ratings()
    opts = build_options(df, "radar", "attribute", ["Aurora", "Zephyr"])
    assert opts["chart"]["type"] == "line" and opts["chart"]["polar"] is True
    assert [s["name"] for s in opts["series"]] == ["Aurora", "Zephyr"]
    assert opts["xAxis"]["categories"][0] == "Design"
    assert len(opts["series"][0]["data"]) == len(df)
    assert opts["legend"]["enabled"] is True


def test_website_activity_sample_builds_a_heatmap_chart():
    # Ties the new heatmap sample to its intended type end to end: a weekday
    # category (X) plus four numeric time-block columns (Y) produce a full grid of
    # [x, y, value] cells — one per (weekday, block), none dropped.
    from sample_data import _weekly_activity

    df = _weekly_activity()
    y_cols = ["Night", "Morning", "Afternoon", "Evening"]
    opts = build_options(df, "heatmap", "weekday", y_cols)
    assert opts["chart"]["type"] == "heatmap"
    assert opts["yAxis"]["categories"] == y_cols
    assert opts["xAxis"]["categories"][0] == "Mon"
    assert len(opts["series"][0]["data"]) == len(df) * len(y_cols)


def test_company_market_cap_sample_builds_a_treemap_chart():
    # Ties the new treemap sample to its intended type end to end: a company label
    # (X) plus one market-cap value column (Y) produce one sized tile per company
    # row, each a {name, value} leaf.
    from sample_data import _company_market_cap

    df = _company_market_cap()
    opts = build_options(df, "treemap", "company", ["market_cap_b"])
    assert opts["chart"]["type"] == "treemap"
    assert opts["series"][0]["name"] == "market_cap_b"
    assert len(opts["series"][0]["data"]) == len(df)
    assert opts["series"][0]["data"][0]["name"] == "Apple"
    assert "value" in opts["series"][0]["data"][0]


def test_conversion_funnel_sample_builds_a_funnel_chart():
    # Ties the new funnel sample to its intended type end to end: a stage label (X) plus one
    # visitor-count value column (Y) produce one {name, y} band per stage, in row order, and the
    # sample's values strictly DECREASE — the narrowing a funnel is meant to show.
    from sample_data import _conversion_funnel

    df = _conversion_funnel()
    opts = build_options(df, "funnel", "stage", ["visitors"])
    assert opts["chart"]["type"] == "funnel"
    assert opts["series"][0]["name"] == "visitors"
    data = opts["series"][0]["data"]
    assert len(data) == len(df)
    assert data[0]["name"] == "Visitors"
    assert "y" in data[0]  # pie's key, not treemap's "value"
    values = [pt["y"] for pt in data]
    assert values == sorted(values, reverse=True)  # a clean narrowing funnel


def test_loyalty_pyramid_sample_builds_a_pyramid_chart():
    # The mirror of the funnel sample: a tier label (X) plus one people-count column (Y). Like the
    # funnel it leads with its LARGEST stage and DECREASES, but a pyramid draws the first row at
    # the base (verified by rendering), so the broad Audience base is row 0 and it narrows up to
    # the Advocates apex. Same data SHAPE as the funnel sample, drawn as pyramid's own series type.
    from sample_data import _loyalty_pyramid

    df = _loyalty_pyramid()
    opts = build_options(df, "pyramid", "tier", ["people"])
    assert opts["chart"]["type"] == "pyramid"
    assert opts["series"][0]["name"] == "people"
    data = opts["series"][0]["data"]
    assert len(data) == len(df)
    assert data[0]["name"] == "Audience"  # the broad base, drawn at the bottom
    values = [pt["y"] for pt in data]
    assert values == sorted(
        values, reverse=True
    )  # largest-first, narrowing to the apex


def test_energy_flow_sample_builds_a_sankey_chart():
    # Ties the new sankey sample to its intended type end to end: two node columns
    # plus a numeric weight produce one link per row. Unlike every other sample, its
    # source values REPEAT, and "Electricity" is both a link target and a link
    # source — that is what makes the second hop appear rather than a bipartite fan.
    from sample_data import _energy_flow

    df = _energy_flow()
    opts = build_options(
        df, "sankey", "source", ["terawatt_hours"], target_col="target"
    )
    assert opts["chart"]["type"] == "sankey"
    assert opts["series"][0]["name"] == "terawatt_hours"
    links = _links(opts)
    assert len(links) == len(df)
    assert links[0] == {"from": "Coal", "to": "Electricity", "weight": 42.0}
    sources = {link["from"] for link in links}
    targets = {link["to"] for link in links}
    assert "Electricity" in sources & targets  # the two-hop node
    # The flow balances: everything generated is consumed.
    generated = sum(link["weight"] for link in links if link["to"] == "Electricity")
    consumed = sum(link["weight"] for link in links if link["from"] == "Electricity")
    assert generated == consumed == 150.0


def test_regional_migration_sample_builds_a_dependencywheel_chart():
    # Ties the new dependencywheel sample to its type end to end: two node columns plus a
    # numeric weight produce one link per row. It is the MIRROR of the sankey energy sample —
    # where that is a layered flow (its source and target sets barely overlap), here EVERY
    # region is BOTH an origin and a destination: the symmetric, cyclic matrix a wheel is
    # built for, and a straight sankey would draw as a tangle of back-crossing links.
    from sample_data import _regional_migration

    df = _regional_migration()
    opts = build_options(
        df, "dependencywheel", "origin", ["people"], target_col="destination"
    )
    assert opts["chart"]["type"] == "dependencywheel"
    assert opts["series"][0]["name"] == "people"
    links = _links(opts)
    assert len(links) == len(df)  # every row is a drawable link
    assert links[0] == {"from": "North", "to": "South", "weight": 1200.0}
    origins = {link["from"] for link in links}
    destinations = {link["to"] for link in links}
    # The wheel's defining shape: every region is BOTH an origin and a destination.
    assert origins == destinations == {"North", "South", "East", "West", "Central"}


def test_service_dependencies_sample_builds_a_networkgraph_chart():
    # Ties the new networkgraph sample to its intended type end to end: two node columns and
    # NO value column produce one unweighted edge per row. Like the sankey sample (and unlike
    # the value-per-row types) its source values REPEAT and several nodes are BOTH a source
    # and a target — that connectivity is what makes it a graph rather than a star. It also
    # carries a CYCLE (Catalog ⇄ Search) that a sunburst's tree could never hold.
    from sample_data import _service_dependencies

    df = _service_dependencies()
    opts = build_options(df, "networkgraph", "service", [], target_col="depends_on")
    assert opts["chart"]["type"] == "networkgraph"
    edges = opts["series"][0]["data"]
    assert len(edges) == len(df)  # one edge per row, none dropped
    assert edges[0] == {"from": "Web", "to": "API Gateway"}
    sources = {e["from"] for e in edges}
    targets = {e["to"] for e in edges}
    # Shared nodes make it a connected network (an API Gateway hub, an Auth reached by several).
    assert {"API Gateway", "Orders", "Auth", "Catalog"} <= sources & targets
    # The Catalog ⇄ Search cycle: each names the other as a target.
    assert {"from": "Catalog", "to": "Search"} in edges
    assert {"from": "Search", "to": "Catalog"} in edges
    # The sample carries a numeric column (so it stays plottable by other types and clears the
    # app's no-numeric-columns gate — the _release_plan/headcount precedent), but networkgraph
    # IGNORES it: the edges name only the two label columns, no weight in sight.
    from pandas.api.types import is_numeric_dtype

    assert is_numeric_dtype(df["calls_per_min"])
    assert all(set(e) == {"from", "to"} for e in edges)


def test_reporting_lines_sample_builds_an_organization_chart():
    # Ties the org sample to its type end to end: one row per person, drawn as titled boxes. Its
    # first person (Nadia) has a BLANK manager — the root — so she draws no reporting line but leads
    # the chart; everyone else names a real manager, and several are BOTH a manager and a report,
    # which gives the tree depth. The `title` column feeds the node cards; the numeric
    # `tenure_years` is IGNORED (an org chart is unweighted) but carried so the roster clears the
    # app's no-numeric-columns gate.
    from sample_data import _reporting_lines

    df = _reporting_lines()
    opts = build_options(
        df, "organization", "employee", [], target_col="manager", title_col="title"
    )
    assert opts["chart"]["type"] == "organization"
    links = opts["series"][0]["data"]
    assert (
        len(links) == len(df) - 1
    )  # everyone but the one root (Nadia) is a reporting line
    assert {"from": "Nadia", "to": "Priya"} in links  # a VP reports to the CEO
    assert {
        "from": "Priya",
        "to": "Sana",
    } in links  # ...and a manager reports to that VP
    assert all(link["to"] != "Nadia" for link in links)  # the root has no incoming link
    nodes = {n["id"]: n["title"] for n in opts["series"][0]["nodes"]}
    assert (
        nodes["Nadia"] == "Chief Executive Officer"
    )  # the root still carries its title card
    # A genuine numeric column (clears the gate), which the org chart never reads.
    from pandas.api.types import is_numeric_dtype

    assert is_numeric_dtype(df["tenure_years"])
    assert all(set(link) == {"from", "to"} for link in links)  # no weight


def test_response_times_sample_builds_a_boxplot_chart():
    # Ties the new boxplot sample to its intended type end to end. Like the sankey sample
    # (and unlike every other, which has one row per unique x value) its x values REPEAT
    # — that is the long/tidy shape boxplot aggregates. 60 rows collapse to 4 boxes, and
    # the lone 890 ms spike in `search` (category index 1) is the frame's only Tukey
    # outlier, so the linked scatter has exactly one point to draw.
    from sample_data import _response_times

    df = _response_times()
    opts = build_options(df, "boxplot", "service", ["response_ms"])
    assert opts["chart"]["type"] == "boxplot"
    assert opts["series"][0]["name"] == "response_ms"
    assert opts["xAxis"]["categories"] == ["auth", "search", "checkout", "profile"]
    assert len(_boxes(opts)) == df["service"].nunique() == 4
    assert len(df) == 60  # ~15 raw observations per service, not one row per box
    # search's box stops at its 120 ms whisker; the 890 ms spike is the sole outlier.
    assert _boxes(opts)[1] == [85.0, 94.0, 101.0, 109.0, 120.0]
    assert opts["series"][1]["data"] == [[1, 890.0]]
    # Every box is well formed: low <= q1 <= median <= q3 <= high.
    for box in _boxes(opts):
        assert list(box) == sorted(box)


def test_profit_bridge_sample_builds_a_waterfall_chart():
    # Ties the new waterfall sample to its intended type end to end. It is the only sample
    # whose numeric column holds signed DELTAS rather than levels — they mean nothing
    # individually, only cumulatively — so it is also the only one where the built chart has
    # MORE marks than the frame has rows: the builder appends the closing total.
    from sample_data import _profit_bridge

    df = _profit_bridge()
    opts = build_options(df, "waterfall", "step", ["delta"])
    assert opts["chart"]["type"] == "waterfall"
    assert opts["series"][0]["name"] == "delta"
    data = opts["series"][0]["data"]
    assert len(data) == len(df) + 1 == 7  # 6 deltas + the appended total
    assert data[:6] == [420.0, -155.0, -120.0, -64.0, 38.0, -40.0]
    assert data[6]["isSum"] is True
    assert opts["xAxis"]["categories"][-1] == "Total"
    # Mixed signs are the point of the type: a same-signed column would just be a column
    # chart drawn oddly. "Other income" is the one mid-sequence RISE, which is what proves
    # the up/down coloring keys off each value's sign rather than off its position.
    assert min(df["delta"]) < 0 < max(df["delta"])
    assert df.loc[df["step"] == "Other income", "delta"].item() == 38.0
    # The deltas bridge gross revenue to net profit — the total Highcharts will compute.
    assert df["delta"].sum() == 79.0


def test_org_headcount_sample_builds_a_sunburst_chart():
    # Ties the sunburst sample to its intended type end to end. It is the only sample whose
    # rows are a HIERARCHY (sankey's _energy_flow is the near miss — its rows are edges of a
    # GRAPH, and Electricity is both a source and a target, which no tree can be), and the only
    # one whose value column is deliberately BLANK on some rows: there a blank means "ask my
    # children", not "missing".
    from sample_data import _org_headcount

    df = _org_headcount()
    opts = build_options(df, "sunburst", "team", ["headcount"], parent_col="reports_to")
    assert opts["chart"]["type"] == "sunburst"
    data = opts["series"][0]["data"]
    assert len(data) == len(df) + 1 == 16  # 15 nodes + the appended root
    assert data[-1]["name"] == "All"

    # The five internal nodes state no headcount and carry none: Engineering's 80 is nowhere in
    # this frame — it is 80 BECAUSE its teams are, and the chart is what does that addition.
    internal = {"Engineering", "Sales", "Marketing", "Platform", "Product"}
    for point in data[:-1]:
        assert ("value" in point) is (point["name"] not in internal), point
    assert df["headcount"].isna().sum() == 5

    # The two "Other" teams: the exact case a label-keyed node identity would silently merge
    # into one 9-person sector. They stay two honest leaves under two different divisions.
    others = [p for p in data if p["name"] == "Other"]
    assert len(others) == 2
    assert sorted(p["value"] for p in others) == [4.0, 5.0]
    assert others[0]["parent"] != others[1]["parent"]

    # Three CSV levels + the synthesized root = four rings, which is what makes the colour
    # inheritance and the ALTERNATING sign of the colorVariation visible at all.
    levels = opts["plotOptions"]["sunburst"]["levels"]
    assert [entry["level"] for entry in levels] == [1, 3, 4]
    # The branch sums Highcharts will compute (the numbers the chart shows but the frame never
    # states), and the grand total the centre reads.
    assert df["headcount"].sum() == 143.0


# --------------------------------------------------------------------------- #
# Full app, headless (Streamlit AppTest)
#
# These drive the UI control flow, not chart correctness (the builder tests
# above own that). The rendered chart lives in an opaque st.iframe that AppTest
# can't see into, but the "generated config" toggle reveals the Highcharts JS
# literal via st.code — so, after switching that toggle on, we assert the
# controls actually reach the builder. (It's a toggle rather than an expander
# because a collapsed expander body still runs on every rerun; the toggle skips
# building the JS until asked, and unlike an expander AppTest can switch it on.)
# Sidebar widgets are addressed by position: selectbox [0] Dataset, [1] Chart
# type, [2] X axis; segmented_control [0] Source, [1] Render mode; pills [0] the
# Y series (a wide CSV upload swaps these pills for a multiselect); toggle [0] the
# generated-config reveal. Those indices hold for every type, because EVERY
# type-specific extra control is created *after* the X selectbox — one per extra column
# kwarg ("Size (Z)", "Target (to)"/"Manager (to)", "Parent", "End", "High (top)",
# "Title", "Goal (target)", "Width", "After"), plus the gauge family's two non-column
# controls. Stated as "every" rather than as a COUNT deliberately: this comment read
# "the three" of them long after there were nine, naming the three types that happened
# to exist when it was written. A tally invites that drift and a rule does not — and
# neither `grep` sweep in CLAUDE.md would have caught it, since a bare cardinal is not
# an ordinal and "the three" is not a uniqueness claim. All of them are addressed by
# LABEL rather than index, since each shifts the widgets that follow it. The Upload CSV
# path shifts them again — it has no Dataset selectbox — so a test on that path addresses
# "Chart type" by label too. Everything in THIS section stays on the network-free
# interactive path; the one test that selects Static PNG lives in the cache-layer section
# at the end of the file and swaps the builder out, so it contacts no export server
# either.
# --------------------------------------------------------------------------- #
@pytest.fixture
def app():
    """A freshly loaded, run-once AppTest for the Streamlit app."""
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()


def _reveal_config(app):
    """Flip the generated-config toggle on (revealing the st.code panel)."""
    app.toggle[0].set_value(True).run()


def _metrics(app) -> dict[str, str]:
    """The KPI metric row as a ``{label: value}`` dict."""
    return {m.label: m.value for m in app.metric}


def test_app_config_hidden_by_default_then_revealed_by_toggle(app):
    # The point of the toggle (vs an always-rendering expander): on a default run
    # the config JS is NOT built or shown; it appears only once the toggle is on.
    assert not app.code  # nothing rendered while the toggle is off
    _reveal_config(app)
    assert not app.exception
    assert app.code and "Highcharts" in app.code[0].value  # config now rendered


def test_app_switch_to_pie_regenerates_config(app):
    app.selectbox[1].set_value("pie")  # Chart type -> pie
    _reveal_config(app)
    assert not app.exception
    assert "type: 'pie'" in app.code[0].value


def test_app_switch_to_bubble_shows_size_control_and_regenerates_config(app):
    # Bubble adds a "Size (Z)" selectbox that no other type shows, and drives the
    # config through the size_col plumbing. Stays on the network-free config path.
    assert not any(sb.label == "Size (Z)" for sb in app.selectbox)  # absent by default
    app.selectbox[1].set_value("bubble").run()  # Chart type -> bubble
    assert not app.exception
    assert any(sb.label == "Size (Z)" for sb in app.selectbox)  # now present
    _reveal_config(app)
    assert not app.exception
    assert "type: 'bubble'" in app.code[0].value


def test_app_switch_to_radar_regenerates_config(app):
    # Radar renders as a polar line chart; switching to it drives the config
    # through the shared category-x path. `polar: true` (absent from a plain line)
    # proves the radar branch — not the cartesian one — produced it. Network-free.
    app.selectbox[1].set_value("radar").run()  # Chart type -> radar
    assert not app.exception
    _reveal_config(app)
    assert not app.exception
    assert "polar: true" in app.code[0].value


def test_app_switch_to_heatmap_regenerates_config(app):
    # Heatmap reinterprets the category-x data as a value matrix colored by a
    # colorAxis; switching to it drives the config through the heatmap branch.
    # `type: 'heatmap'` + the colorAxis prove it — heatmap adds no extra sidebar
    # control, so the positional widget indices are unchanged. Network-free.
    app.selectbox[1].set_value("heatmap").run()  # Chart type -> heatmap
    assert not app.exception
    _reveal_config(app)
    assert not app.exception
    assert "type: 'heatmap'" in app.code[0].value
    assert "colorAxis" in app.code[0].value


def test_app_switch_to_treemap_regenerates_config(app):
    # Treemap is single-value like pie, so switching to it swaps the Y pills for a
    # single-select Y (an extra selectbox, exactly as pie does) and drives the
    # config through the treemap branch. `type: 'treemap'` proves that branch
    # produced it. Modeled on the pie test (widgets addressed by index [1]) — NOT
    # heatmap, whose multi=True pills leave the widget indices unchanged. Network-free.
    app.selectbox[1].set_value("treemap").run()  # Chart type -> treemap
    assert not app.exception
    _reveal_config(app)
    assert not app.exception
    assert "type: 'treemap'" in app.code[0].value


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_app_switch_to_funnel_family_regenerates_config(app, chart_type):
    # Funnel/pyramid are single-value like pie/treemap, so switching swaps the Y pills for a
    # single-select Y (an extra selectbox, exactly as pie does) and drives the config through the
    # funnel branch, adding NO extra control before Chart type (so the index-[1] addressing other
    # app tests rely on still holds). `type: '<chart_type>'` proves that branch produced it — and
    # that a pyramid emits its OWN type name, not a funnel. Network-free.
    app.selectbox[1].set_value(chart_type).run()  # Chart type -> funnel / pyramid
    assert not app.exception
    _reveal_config(app)
    assert not app.exception
    assert f"type: '{chart_type}'" in app.code[0].value


def test_app_switch_to_sankey_shows_target_control_and_regenerates_config(app):
    # Sankey is the second type with a required extra column (after bubble): it
    # reveals a "Target (to)" selectbox that no other type shows, and drives the
    # config through the target_col plumbing. Addressed by LABEL, not index — unlike
    # bubble's Size (Z), the Target control sits between the X and the single-select
    # Y widgets, so the positional indices past [2] shift. Stays network-free.
    assert not any(sb.label == "Target (to)" for sb in app.selectbox)  # absent
    app.selectbox[1].set_value("sankey").run()  # Chart type -> sankey
    assert not app.exception
    assert any(sb.label == "Target (to)" for sb in app.selectbox)  # now present
    # Single-select Y (the weight), like pie/treemap — not the multi-select pills.
    assert any(sb.label == "Flow value (weight)" for sb in app.selectbox)
    assert not app.pills
    _reveal_config(app)
    assert not app.exception
    assert "type: 'sankey'" in app.code[0].value


def test_app_sankey_target_survives_a_source_change(app):
    # The keyless-widget trap the Target selectbox's `index` guards against. These
    # widgets carry no key, so Streamlit folds `index` into their identity: a default
    # derived from x_col (the tempting "the column after Source") would re-mint the
    # widget whenever Source changed, silently discarding the user's Target. Pick a
    # Target, change Source, and assert the Target survives. A dynamic index makes
    # this fail — nothing else in the suite would notice.
    app.selectbox[1].set_value("sankey").run()  # Chart type -> sankey
    target = next(sb for sb in app.selectbox if sb.label == "Target (to)")
    target.set_value("cost").run()  # the third column, not the default
    assert not app.exception
    app.selectbox[2].set_value("revenue").run()  # Source (from): month -> revenue
    assert not app.exception
    target = next(sb for sb in app.selectbox if sb.label == "Target (to)")
    assert target.value == "cost"  # not reset to the default


def test_app_sankey_source_equals_target_shows_guard_warning(app):
    # Sankey's own guard, NOT the category-x x-in-y rule (which the Target column
    # can't trip — it's never among the Y series): naming one column as both ends of
    # a link would make every link a self-loop. The default Source is the first
    # column, so pointing Target at it collides.
    app.selectbox[1].set_value("sankey").run()  # Chart type -> sankey
    target = next(sb for sb in app.selectbox if sb.label == "Target (to)")
    target.set_value("month").run()  # == the default Source column
    assert not app.exception
    assert app.warning
    assert "Source and Target must be different" in app.warning[0].value


def test_app_sankey_kpi_shows_flows(app):
    # Sankey is one series of links, so the KPI swaps "Series plotted" (which would
    # read a bare 1) for "Flows" = the rows that become links — mirroring heatmap's
    # "Cells" and treemap's "Tiles". The default dataset has no missing values, so
    # every row is a flow.
    from sample_data import SAMPLES

    app.selectbox[1].set_value("sankey").run()  # Chart type -> sankey
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    assert metrics["Flows"] == f"{len(default_df):,}"


def test_app_switch_to_dependencywheel_shows_target_control_and_regenerates_config(app):
    # Dependencywheel is sankey's circular twin, so switching to it reveals the SAME
    # "Target (to)" selectbox and single-select "Flow value (weight)" Y (the node-link controls,
    # keyed on NODE_LINK_TYPES) and drives the config through the shared target_col plumbing —
    # but the emitted `type: 'dependencywheel'` proves the WHEEL branch, not sankey's, produced
    # it. The source==target guard and the keyless Target's survival are shared code paths,
    # already pinned on sankey. Network-free.
    assert not any(
        sb.label == "Target (to)" for sb in app.selectbox
    )  # absent by default
    app.selectbox[1].set_value("dependencywheel").run()  # Chart type -> dependencywheel
    assert not app.exception
    assert any(sb.label == "Target (to)" for sb in app.selectbox)  # now present
    assert any(sb.label == "Flow value (weight)" for sb in app.selectbox)
    assert not app.pills  # single-select Y (the weight), not the multi-select pills
    _reveal_config(app)
    assert not app.exception
    assert "type: 'dependencywheel'" in app.code[0].value


def test_app_dependencywheel_kpi_shows_flows(app):
    # A dependencywheel is one series of links like sankey, so the KPI swaps "Series plotted"
    # (which would read a bare 1) for "Flows" — sharing sankey's label because it counts the
    # same {from, to, weight} links. The default dataset has no missing values, so every row
    # becomes a flow.
    from sample_data import SAMPLES

    app.selectbox[1].set_value("dependencywheel").run()  # Chart type -> dependencywheel
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    assert metrics["Flows"] == f"{len(default_df):,}"


def test_app_switch_to_networkgraph_shows_target_hides_y_and_regenerates_config(app):
    # Networkgraph is the SUBTRACTIVE mirror of gauge: gauge removes the X selectbox, and
    # networkgraph removes the Y control entirely (it has no value channel). So after switching
    # it shows a "Target (to)" selectbox (reused from sankey) and NO Y widget at all — neither
    # the multi-select pills nor a single-select Y selectbox. The only selectboxes left are
    # Dataset, Chart type, Source (from) and Target (to). The config still generates without a Y,
    # which is the whole point: an empty y_cols is valid input here. Network-free.
    assert app.pills  # the default `line` type shows multi-select Y pills...
    app.selectbox[1].set_value("networkgraph").run()  # Chart type -> networkgraph
    assert not app.exception
    assert not app.pills  # ...which are gone, and NOT replaced by a Y selectbox
    labels = {sb.label for sb in app.selectbox}
    assert labels == {"Dataset", "Chart type", "Source (from)", "Target (to)"}
    _reveal_config(app)
    assert not app.exception
    assert "type: 'networkgraph'" in app.code[0].value


def test_app_networkgraph_source_equals_target_shows_guard_warning(app):
    # Networkgraph shares sankey's source-vs-target guard: one column can't be both ends of an
    # edge. The default Source is the first column, so pointing Target at it collides.
    app.selectbox[1].set_value("networkgraph").run()  # Chart type -> networkgraph
    target = next(sb for sb in app.selectbox if sb.label == "Target (to)")
    target.set_value("month").run()  # == the default Source column
    assert not app.exception
    assert app.warning
    assert "Source and Target must be different" in app.warning[0].value


_EDGE_LIST_CSV = (
    b"source,target\nWeb,API Gateway\nAPI Gateway,Auth\nAPI Gateway,Orders\n"
)


def test_app_networkgraph_plots_a_csv_with_no_numeric_columns_at_all(app):
    # THE GATE, networkgraph's half of it — the xrange test's mirror. The canonical networkgraph
    # input is a pure edge list: two TEXT columns and not one number. `select_dtypes("number")`
    # finds nothing, so the no-numeric-columns gate would refuse the single most natural input for
    # this type — exactly as it once refused the Gantt CSV for xrange. networkgraph is now exempt
    # (it reads its two columns as node labels), so the file plots.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(("edges.csv", _EDGE_LIST_CSV, "text/csv")).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("networkgraph").run()
    assert not app.exception
    assert not app.error  # NOT "this dataset has no numeric columns to plot"
    metrics = _metrics(app)
    assert metrics["Numeric columns"] == "0"  # ...and yet
    assert metrics["Links"] == "3"  # ...it plots every edge

    # The gate stays honest in the other direction: the same file on a type that really does need
    # a number must still be refused.
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("line").run()
    assert app.error
    assert "no numeric columns" in app.error[0].value


def test_app_networkgraph_kpi_shows_links(app):
    # Networkgraph is one series of edges, so — like sankey — the KPI swaps "Series plotted"
    # (which would read a bare 1) for "Links" = the rows that become edges. The default dataset
    # has no missing node cells, so every row is an edge. This also proves the empty-Y guard
    # exempts networkgraph: the KPI (and the chart) render with no Y selected.
    from sample_data import SAMPLES

    app.selectbox[1].set_value("networkgraph").run()  # Chart type -> networkgraph
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    assert metrics["Links"] == f"{len(default_df):,}"


def test_app_switch_to_organization_shows_manager_title_hides_y(app):
    # Organization is unweighted like networkgraph (no Y control), but ADDS a Title control — so
    # after switching it shows Employee/Manager/Title selectboxes and NO Y widget (neither pills nor
    # a Y selectbox). The Target control is relabelled "Manager (to)". The config still generates
    # without a Y, an empty y_cols being valid here. Network-free.
    assert app.pills  # the default `line` type shows multi-select Y pills...
    app.selectbox[1].set_value("organization").run()  # Chart type -> organization
    assert not app.exception
    assert not app.pills  # ...gone, and NOT replaced by a Y selectbox
    labels = {sb.label for sb in app.selectbox}
    assert labels == {
        "Dataset",
        "Chart type",
        "Employee (node)",
        "Manager (to)",
        "Title",
    }
    _reveal_config(app)
    assert not app.exception
    assert "type: 'organization'" in app.code[0].value


def test_app_organization_kpi_shows_reports(app):
    # One org series, so — like sankey/networkgraph — the KPI swaps "Series plotted" (a bare 1) for
    # "Reports" = the rows with a real manager. The default dataset's manager column (its 2nd
    # column) has no blanks, so every row is a reporting line. Also proves the empty-Y guard exempts
    # organization: the KPI and chart render with no Y selected.
    from sample_data import SAMPLES

    app.selectbox[1].set_value("organization").run()  # Chart type -> organization
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    assert metrics["Reports"] == f"{len(default_df):,}"


def test_app_organization_source_equals_manager_shows_guard_warning(app):
    # Organization shares the node-link source-vs-target guard: an employee can't be their own
    # manager. The default Employee is the first column, so pointing Manager at it collides.
    app.selectbox[1].set_value("organization").run()  # Chart type -> organization
    manager = next(sb for sb in app.selectbox if sb.label == "Manager (to)")
    manager.set_value("month").run()  # == the default Employee column
    assert not app.exception
    assert app.warning
    assert "Source and Target must be different" in app.warning[0].value


_ROSTER_CSV = b"employee,manager,title\nAda,,CEO\nBo,Ada,CTO\nCy,Ada,CFO\n"


def test_app_organization_plots_a_csv_with_no_numeric_columns(app):
    # THE GATE, organization's half of it — networkgraph's mirror. A plain roster is three TEXT
    # columns and not one number, so the no-numeric-columns gate would refuse the type's most
    # natural input. Organization is now exempt (it reads its columns as node/title labels), so the
    # file plots; a root (Ada's blank manager) draws no line, so 3 people with 1 root give 2
    # Reports. The Title control defaults to the third column ("title"), so the cards show at once.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(("roster.csv", _ROSTER_CSV, "text/csv")).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("organization").run()
    assert not app.exception
    assert not app.error  # NOT "this dataset has no numeric columns to plot"
    metrics = _metrics(app)
    assert metrics["Numeric columns"] == "0"  # ...and yet
    assert (
        metrics["Reports"] == "2"
    )  # Bo and Cy report to Ada; Ada (blank manager) is the root

    # The gate stays honest in the other direction: the same file on a type that really does need a
    # number must still be refused.
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("line").run()
    assert app.error
    assert "no numeric columns" in app.error[0].value


_ROSTER_2COL_CSV = b"employee,manager\nAda,\nBo,Ada\nCy,Ada\n"


def test_app_organization_two_column_csv_draws_name_only(app):
    # The 2-column-collision guard, primary half: a roster with only Employee and Manager (no title
    # column) must draw a plain NAME-ONLY hierarchy, NOT clamp the Title control onto the Manager
    # column and mislabel every box with its manager's name. The Title control defaults to
    # "(no titles)" (title_col=None) when there is no third column, so no `nodes` array is emitted
    # and no collision warning fires.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(("roster2.csv", _ROSTER_2COL_CSV, "text/csv")).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("organization").run()
    assert not app.exception
    assert not app.error  # gate exempt (no numeric columns needed)
    assert not app.warning  # no collision: Title defaulted to "(no titles)"
    metrics = _metrics(app)
    assert (
        metrics["Reports"] == "2"
    )  # Bo and Cy report to Ada; Ada (blank manager) is the root
    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'organization'" in js
    assert "nodes" not in js  # name-only: no title cards, so no nodes array


def test_app_organization_title_equals_manager_shows_guard_warning(app):
    # The 2-column-collision guard, deliberate half: even with a title column available, manually
    # pointing Title at the Employee or Manager column is a plausible-looking lie (every box titled
    # with its own or its manager's name), so the app warns and stops. Unlike the source-vs-target
    # guard it is app-only (the pure build tolerates it, being drawable). The default sample's
    # Manager is its second column ("revenue"); setting Title to it collides.
    app.selectbox[1].set_value("organization").run()  # Chart type -> organization
    title = next(sb for sb in app.selectbox if sb.label == "Title")
    title.set_value("revenue").run()  # == the default Manager column
    assert not app.exception
    assert app.warning
    assert "Title must be a different column" in app.warning[0].value


def test_app_switch_to_boxplot_shows_single_select_y_and_regenerates_config(app):
    # Boxplot reads its Y as one column of raw observations, so — like pie/treemap/sankey
    # — it swaps the multi-select Y pills for a single selectbox. It needs no EXTRA
    # column selector (unlike bubble's Size and sankey's Target), so it adds exactly one
    # widget. Modeled on the pie/treemap tests, not heatmap's (whose multi=True pills
    # leave the widget indices unchanged). Network-free.
    app.selectbox[1].set_value("boxplot").run()  # Chart type -> boxplot
    assert not app.exception
    assert not app.pills  # single-select Y, so the pills are gone
    assert any(sb.label == "Observations (Y)" for sb in app.selectbox)
    assert not any(sb.label == "Size (Z)" for sb in app.selectbox)  # no extra selector
    assert not any(sb.label == "Target (to)" for sb in app.selectbox)
    assert not any(sb.label.startswith("Parent") for sb in app.selectbox)
    _reveal_config(app)
    assert not app.exception
    assert "type: 'boxplot'" in app.code[0].value


def test_app_boxplot_kpi_shows_boxes(app):
    # Boxplot is one series of boxes, so the KPI swaps "Series plotted" (which would read
    # a bare 1) for "Boxes" = the distinct categories — mirroring heatmap's "Cells",
    # treemap's "Tiles" and sankey's "Flows". The default dataset has one row per month,
    # so each month is a (degenerate, single-observation) box.
    from sample_data import SAMPLES

    app.selectbox[1].set_value("boxplot").run()  # Chart type -> boxplot
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    # The app's default X is the first column, as the X selectbox's default index shows.
    expected = default_df[default_df.columns[0]].nunique()
    assert metrics["Boxes"] == f"{expected:,}"


def test_app_switch_to_waterfall_shows_single_select_y_and_regenerates_config(app):
    # Waterfall reads its Y as one column of signed deltas, so — like pie/treemap/sankey/
    # boxplot — it swaps the multi-select Y pills for a single selectbox. It needs no EXTRA
    # column selector (unlike bubble's Size and sankey's Target), so the widget indices are
    # unchanged. Network-free.
    app.selectbox[1].set_value("waterfall").run()  # Chart type -> waterfall
    assert not app.exception
    assert not app.pills  # single-select Y, so the pills are gone
    assert any(sb.label == "Step values (signed delta)" for sb in app.selectbox)
    assert not any(sb.label == "Size (Z)" for sb in app.selectbox)  # no extra selector
    assert not any(sb.label == "Target (to)" for sb in app.selectbox)
    assert not any(sb.label.startswith("Parent") for sb in app.selectbox)
    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'waterfall'" in js
    assert "isSum: true" in js  # the appended total reached the chart


def test_app_waterfall_kpi_shows_steps_including_the_appended_total(app):
    # Waterfall is one series of bars, so the KPI swaps "Series plotted" (which would read a
    # bare 1) for "Steps" — mirroring heatmap's "Cells", treemap's "Tiles", sankey's "Flows"
    # and boxplot's "Boxes". It is the one KPI that EXCEEDS the row count, because the
    # appended total is a bar the chart really draws; sourcing it from count_marks is what
    # keeps that true rather than merely asserted here.
    from highcharts_builder import count_marks
    from sample_data import SAMPLES

    app.selectbox[1].set_value("waterfall").run()  # Chart type -> waterfall
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    x_col = default_df.columns[0]  # the app's default X is the first column
    y_col = default_df.select_dtypes("number").columns[0]  # and Y the first numeric one
    expected = count_marks(default_df, "waterfall", x_col, [y_col])
    assert metrics["Steps"] == f"{expected:,}"
    assert expected == len(default_df) + 1  # every row a step, plus the total


def _pick_sample(app, chart_type: str):
    """Select the sample dataset built FOR ``chart_type``, and that type, in the sidebar.

    The shared body of the seven ``_pick_*_sample`` helpers below, each of which keeps its own
    name and its own argument for why that type needs a dedicated sample rather than the
    landing dataset. Only the mechanics live here.

    Widgets are found by LABEL, not by position. ``app.selectbox[0]``/``[1]`` were five copies
    of the same two indices, so one new selectbox added above Dataset would have broken all
    five identically and each would have needed the same edit — and a positional index says
    nothing about WHICH widget it means, so a wrong one silently drives the wrong control.
    Label lookup is already this file's majority idiom.
    """
    from sample_data import SAMPLES

    label = next(key for key in SAMPLES if f"({chart_type})" in key)
    next(sb for sb in app.selectbox if sb.label == "Dataset").set_value(label).run()
    next(sb for sb in app.selectbox if sb.label == "Chart type").set_value(
        chart_type
    ).run()
    return SAMPLES[label]()


def _pick_sunburst_sample(app):
    """Select the sunburst sample dataset and switch the chart type to sunburst.

    The DEFAULT dataset (monthly revenue vs cost) is not a hierarchy — its Parent column
    would default to `revenue`, whose numbers name no node — so every row dangles and the
    chart is legitimately empty. The KPI test needs a real tree to count.
    """
    return _pick_sample(app, "sunburst")


def test_app_switch_to_sunburst_shows_parent_control_and_regenerates_config(app):
    # Sunburst is the third type with a required extra column (after bubble's Size and
    # sankey's Target): it reveals a "Parent" selectbox no other type shows, and drives the
    # config through the parent_col plumbing. Addressed by LABEL, not index — like sankey's
    # Target it sits between the X and the single-select Y widgets, so the positional indices
    # past [2] shift. Network-free.
    assert not any(sb.label.startswith("Parent") for sb in app.selectbox)  # absent
    _pick_sunburst_sample(app)
    assert not app.exception
    parent = [sb for sb in app.selectbox if sb.label.startswith("Parent")]
    assert len(parent) == 1  # now present
    # Single-select Y (the leaf values), like pie/treemap/sankey/boxplot/waterfall.
    assert any(sb.label == "Leaf values" for sb in app.selectbox)
    assert not app.pills
    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'sunburst'" in js
    assert "allowTraversingTree: true" in js  # the drill-in survived to the chart


def test_app_sunburst_parent_survives_a_node_change(app):
    # The keyless-widget trap the Parent selectbox's constant `index` guards against, exactly
    # as sankey's Target does. These widgets carry no key, so Streamlit folds `index` into
    # their identity: a default derived from x_col (the tempting "the column after Node")
    # would re-mint the widget whenever Node changed, silently discarding the user's Parent.
    # A dynamic index makes this fail — nothing else in the suite would notice.
    _pick_sunburst_sample(app)  # columns: team, reports_to, headcount
    parent = next(sb for sb in app.selectbox if sb.label.startswith("Parent"))
    parent.set_value("headcount").run()  # the third column, not the default
    assert not app.exception
    app.selectbox[2].set_value("reports_to").run()  # Node: team -> reports_to
    assert not app.exception
    parent = next(sb for sb in app.selectbox if sb.label.startswith("Parent"))
    assert parent.value == "headcount"  # not reset to the default


def test_app_sunburst_node_equals_parent_shows_guard_warning(app):
    # Sunburst's own collision, sankey's one relation over: a node and its parent. Not the
    # x-in-y rule (the Parent column is never among the Y series). Every node would be its own
    # parent — a self-cycle in every row.
    _pick_sunburst_sample(app)
    parent = next(sb for sb in app.selectbox if sb.label.startswith("Parent"))
    parent.set_value("team").run()  # == the default Node column
    assert not app.exception  # the guard fires; it does NOT blow up the page
    assert app.warning
    assert "Node and Parent must be different" in app.warning[0].value
    # The KPI row runs ABOVE that guard, so it still renders — and it must render the SAME way
    # a cyclic CSV does (below), because they are the same contradiction. This is the assertion
    # that keeps the KPI from growing a special case: count_marks is total, so it reports the
    # true count of the chart about to be replaced by the warning. A `chart_type == "sunburst"
    # and x_col == parent_col` escape hatch here would read "Series plotted 1" instead, making
    # two identical situations display differently and breaking MARK_METRICS' one-branch
    # property. Nothing else in the suite would notice.
    metrics = _metrics(app)
    assert metrics["Sectors"] == "0"
    assert "Series plotted" not in metrics


def test_app_sunburst_a_contradictory_tree_reads_zero_sectors(app):
    # The other half of the pair above, on the other contradiction: a cyclic CSV reaches the
    # same guard block and must reach the same KPI. Pins the two together, so neither can grow
    # a special case the other doesn't.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        ("cycle.csv", b"node,parent,value\na,b,1\nb,a,2\n", "text/csv")
    ).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("sunburst").run()
    assert not app.exception
    assert _metrics(app)["Sectors"] == "0"


def test_app_sunburst_a_cyclic_csv_warns_instead_of_crashing(app):
    # The one BUILDER error a user can reach just by uploading a file. The interactive path
    # doesn't catch, so the app has to stop on it first — and the KPI row runs ABOVE that
    # guard, which is why count_marks returns 0 on a contradictory tree rather than raising.
    # If it raised, this page would be a traceback instead of an explanation.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        ("cycle.csv", b"node,parent,value\na,b,1\nb,a,2\n", "text/csv")
    ).run()
    # By LABEL, not index: the Upload CSV path has no Dataset selectbox, so every positional
    # index shifts by one against the sample-dataset path the other app tests use.
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("sunburst").run()
    assert not app.exception  # NOT a traceback
    assert app.warning
    assert "is a cycle" in app.warning[0].value
    # The message is the builder's own — explain_tree_error returns the very string
    # build_options raises — so the warning can't drift from the exception it stands in for.
    assert "must describe a tree" in app.warning[0].value


def test_app_sunburst_kpi_shows_sectors_including_the_appended_root(app):
    # Sunburst is one series of sectors, so the KPI swaps "Series plotted" (which would read a
    # bare 1) for "Sectors" — mirroring heatmap's "Cells", treemap's "Tiles", sankey's "Flows",
    # boxplot's "Boxes" and waterfall's "Steps". It is the SECOND KPI that exceeds its row
    # count, because the appended root is a sector the chart really draws; sourcing it from
    # count_marks is what keeps that true rather than merely asserted here.
    from highcharts_builder import count_marks

    df = _pick_sunburst_sample(app)
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    expected = count_marks(
        df, "sunburst", "team", ["headcount"], parent_col="reports_to"
    )
    assert metrics["Sectors"] == f"{expected:,}"
    assert expected == len(df) + 1 == 16  # every node a sector, plus the root


# A real Gantt CSV: a lane column and two DATE columns, and so NOT ONE numeric column. This
# is the file the app used to refuse at the door — `select_dtypes("number")` is empty, and
# the no-numeric-columns gate ran ABOVE the chart-type picker and st.stop()ped the page.
_GANTT_CSV = (
    b"task,start,end\n"
    b"Design,2026-01-05,2026-02-10\n"
    b"Build,2026-02-01,2026-04-20\n"
    b"QA,2026-04-10,2026-05-15\n"
)


def _pick_xrange_sample(app):
    """Select the xrange sample dataset and switch the chart type to xrange.

    The DEFAULT dataset (monthly revenue vs cost) has no coordinate pair to span — and its
    `month` column is the very one that must NOT sniff as a date (see `_coordinates`) — so
    the KPI test needs the release plan to have bars to count.
    """
    return _pick_sample(app, "xrange")


def test_app_switch_to_xrange_shows_end_control_and_regenerates_config(app):
    # Xrange is the fourth type with a required extra column (after bubble's Size, sankey's
    # Target and sunburst's Parent): it reveals an "End" selectbox no other type shows, and
    # drives the config through the end_col plumbing. Network-free.
    assert not any(sb.label == "End" for sb in app.selectbox)  # absent
    _pick_xrange_sample(app)
    assert not app.exception
    assert len([sb for sb in app.selectbox if sb.label == "End"]) == 1  # now present
    # Single-select Y — and it is labelled as a COORDINATE ("Start"), not a value, because it
    # says WHEN rather than HOW MUCH.
    assert any(sb.label == "Start" for sb in app.selectbox)
    assert not app.pills
    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'xrange'" in js
    assert "x2:" in js  # the extent survived to the chart
    assert "type: 'datetime'" in js  # ...and the ISO date strings became a time axis


def test_app_xrange_start_and_end_pickers_offer_only_coordinate_columns(app):
    # Both are sourced from the builder's `coordinate_columns`, so a picker cannot offer a
    # column the builder would only turn around and reject. `workstream` is text — it names a
    # lane, it cannot place a bar on an axis — so it must not appear in either.
    _pick_xrange_sample(app)
    start = next(sb for sb in app.selectbox if sb.label == "Start")
    end = next(sb for sb in app.selectbox if sb.label == "End")
    for picker in (start, end):
        assert "workstream" not in picker.options
        assert set(picker.options) == {"start", "end", "headcount"}


def test_app_xrange_end_survives_a_lane_change(app):
    # The keyless-widget trap the End selectbox's constant `index` guards against, exactly as
    # sankey's Target and sunburst's Parent do. A default derived from the Start column (the
    # tempting "the column after Start") would re-mint the widget whenever Start changed,
    # silently discarding the user's End. A dynamic index makes this fail — nothing else in
    # the suite would notice.
    _pick_xrange_sample(app)  # columns: workstream, start, end, headcount
    end = next(sb for sb in app.selectbox if sb.label == "End")
    end.set_value("headcount").run()  # not the default
    assert not app.exception
    app.selectbox[2].set_value("start").run()  # Lane: workstream -> start
    assert not app.exception
    end = next(sb for sb in app.selectbox if sb.label == "End")
    assert end.value == "headcount"  # not reset to the default


def test_app_xrange_start_equals_end_shows_guard_warning(app):
    # Xrange's own collision, the third of these: a bar's two ends. Not the x-in-y rule (the
    # End column is never among the Y series). It must be GUARDED rather than tolerated
    # because it fails silently — every bar would be zero-length, so the chart would come back
    # as a column of milestone slivers rather than as anything anyone asked for.
    _pick_xrange_sample(app)
    end = next(sb for sb in app.selectbox if sb.label == "End")
    end.set_value("start").run()  # == the Start column
    assert not app.exception  # the guard fires; it does NOT blow up the page
    assert app.warning
    assert "Start and End must be different" in app.warning[0].value


def test_app_xrange_a_date_start_beside_a_numeric_end_warns_instead_of_crashing(app):
    # The SECOND builder error a user can reach without writing any code (sunburst's cyclic CSV
    # was the first). The interactive path doesn't catch, so the app has to stop on it — and
    # the KPI row runs ABOVE that guard, which is why count_marks returns 0 on a contradictory
    # column pair rather than raising. If it raised, this page would be a traceback.
    #
    # A TEXT start is the other contradiction, but it is unreachable from the app by
    # construction: `coordinate_columns` keeps a column of task names out of both pickers (see
    # the test above), which is the point of sourcing them from the builder. The date-beside-a-
    # number mismatch is the one a user CAN still select, so that is the one to drive here.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        (
            "mixed.csv",
            b"task,start,end,sprint\nDesign,2026-01-05,2026-02-10,3\n",
            "text/csv",
        )
    ).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("xrange").run()
    end = next(sb for sb in app.selectbox if sb.label == "End")
    end.set_value("sprint").run()  # a NUMBER beside a DATE start
    assert not app.exception  # NOT a traceback
    assert app.warning
    # The message is the builder's own — explain_xrange_error returns the very string
    # build_options raises — so the warning can't drift from the exception it stands in for.
    assert "must be the same kind" in app.warning[0].value
    # ...and the KPI reports the true count of the chart about to be replaced by that warning.
    assert _metrics(app)["Bars"] == "0"


def test_app_xrange_plots_a_csv_with_no_numeric_columns_at_all(app):
    # THE GATE. A real Gantt CSV is a lane column and two DATE columns — and a date column is
    # object dtype, so `select_dtypes("number")` finds NOTHING in it. The no-numeric-columns
    # gate used to run above the chart-type picker and st.stop() the page, so this file — the
    # single most natural input for this chart type — was refused before xrange could even be
    # chosen. The gate now runs BELOW the picker and asks the question the type actually has.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(("gantt.csv", _GANTT_CSV, "text/csv")).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("xrange").run()
    assert not app.exception
    assert not app.error  # NOT "this dataset has no numeric columns to plot"
    metrics = _metrics(app)
    assert metrics["Numeric columns"] == "0"  # ...and yet
    assert metrics["Bars"] == "3"  # ...it plots

    # The gate stays honest in the other direction: the same file on a type that really does
    # need a number must still be refused.
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("line").run()
    assert app.error
    assert "no numeric columns" in app.error[0].value


def test_app_xrange_kpi_shows_bars(app):
    # Xrange is one series of bars, so the KPI swaps "Series plotted" (which would read a bare
    # 1) for "Bars" — mirroring heatmap's "Cells", treemap's "Tiles", sankey's "Flows",
    # boxplot's "Boxes", waterfall's "Steps" and sunburst's "Sectors". Unlike the last two it
    # appends nothing, so its count is exactly its surviving rows — the milestone included,
    # because the builder floors that bar to a visible sliver rather than dropping it.
    df = _pick_xrange_sample(app)
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    expected = count_marks(df, "xrange", "workstream", ["start"], end_col="end")
    assert metrics["Bars"] == f"{expected:,}"
    assert (
        expected == len(df) == 8
    )  # every row a bar; nothing appended, nothing dropped


def _pick_columnrange_sample(app):
    """Select the columnrange sample dataset and switch the chart type to columnrange.

    The DEFAULT dataset (monthly revenue vs cost) would build a columnrange too, but the
    temperature sample is the one whose two numeric columns ARE a low and a high, so the KPI
    and picker tests read the numbers the type is meant to draw."""
    return _pick_sample(app, "columnrange")


def test_app_switch_to_columnrange_shows_high_control_and_regenerates_config(app):
    # Columnrange is the fifth type with a required extra column (after bubble's Size, sankey's
    # Target, sunburst's Parent and xrange's End): it reveals a "High (top)" selectbox no other
    # type shows, and drives the config through the high_col plumbing. Network-free.
    assert not any(sb.label == "High (top)" for sb in app.selectbox)  # absent
    _pick_columnrange_sample(app)
    assert not app.exception
    assert (
        len([sb for sb in app.selectbox if sb.label == "High (top)"]) == 1
    )  # now present
    # Single-select Y, labelled as a MAGNITUDE ("Low (bottom)") — one end of the range, not a
    # coordinate like xrange's "Start". No pills.
    assert any(sb.label == "Low (bottom)" for sb in app.selectbox)
    assert not app.pills
    _reveal_config(app)
    assert not app.exception
    assert "type: 'columnrange'" in app.code[0].value


def test_app_columnrange_low_and_high_pickers_offer_only_numeric_columns(app):
    # High is a MAGNITUDE, sourced from numeric_cols — NOT coordinate_columns like xrange's End,
    # because a high can never be a date. `month` is a category, so it must appear in NEITHER
    # value picker (the mirror of xrange excluding its text lane column from its coordinate ones).
    _pick_columnrange_sample(app)  # columns: month, record_low, record_high
    low = next(sb for sb in app.selectbox if sb.label == "Low (bottom)")
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    for picker in (low, high):
        assert "month" not in picker.options
        assert set(picker.options) == {"record_low", "record_high"}


def test_app_columnrange_high_survives_a_low_change(app):
    # The keyless-widget trap High's constant `index` guards against, exactly as xrange's End,
    # sankey's Target and sunburst's Parent do. A default derived from the current Low would
    # re-mint High whenever Low changed, silently discarding the user's pick. A 3-numeric CSV
    # gives room to change Low without colliding with High.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        ("ranges.csv", b"category,a,b,c\nX,1,5,9\nY,2,6,10\n", "text/csv")
    ).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("columnrange").run()
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    high.set_value("c").run()  # not the default (which is the 2nd numeric, "b")
    assert not app.exception
    low = next(sb for sb in app.selectbox if sb.label == "Low (bottom)")
    low.set_value("b").run()  # change Low a -> b
    assert not app.exception
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    assert high.value == "c"  # not reset to the default


def test_app_columnrange_low_equals_high_shows_guard_warning(app):
    # Columnrange's own collision, xrange's one type over: a bar's low and high. Not the x-in-y
    # rule (High is the high_col selector, never among the Y series). It must be GUARDED rather
    # than tolerated because it fails silently — every bar would span zero height.
    _pick_columnrange_sample(app)  # Low defaults record_low, High defaults record_high
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    high.set_value("record_low").run()  # == the Low column
    assert not app.exception  # the guard fires; it does NOT blow up the page
    assert app.warning
    assert "Low and High must be different" in app.warning[0].value


def test_app_columnrange_kpi_shows_ranges(app):
    # Columnrange is one series of low/high bars, so the KPI swaps "Series plotted" (which would
    # read a bare 1) for "Ranges" — mirroring heatmap's "Cells", xrange's "Bars" and the rest.
    # One bar per category, nothing appended or dropped, so its count is exactly its rows.
    df = _pick_columnrange_sample(app)
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    expected = count_marks(df, "columnrange", "month", ["record_low"])
    assert metrics["Ranges"] == f"{expected:,}"
    assert expected == len(df) == 12


def _pick_arearange_sample(app):
    """Select the arearange sample dataset and switch the chart type to arearange.

    The forecast sample is the one whose two numeric columns ARE a low and a high (a projected
    band), so the KPI and picker tests read the numbers the type is meant to draw."""
    return _pick_sample(app, "arearange")


def test_app_switch_to_arearange_shows_high_control_and_regenerates_config(app):
    # Arearange reuses columnrange's "High (top)" control (the shared MAGNITUDE_RANGE High selector)
    # and its "Low (bottom)" Y label, driving the config through the same high_col plumbing — no new
    # cache kwarg. It reveals the High selectbox no plain type shows, and serializes as its OWN
    # chart.type. Network-free.
    assert not any(
        sb.label == "High (top)" for sb in app.selectbox
    )  # absent by default
    _pick_arearange_sample(app)
    assert not app.exception
    assert (
        len([sb for sb in app.selectbox if sb.label == "High (top)"]) == 1
    )  # now present
    assert any(
        sb.label == "Low (bottom)" for sb in app.selectbox
    )  # single-select magnitude
    assert not app.pills
    _reveal_config(app)
    assert not app.exception
    assert "type: 'arearange'" in app.code[0].value


def test_app_arearange_low_and_high_pickers_offer_only_numeric_columns(app):
    # Like columnrange: High is a MAGNITUDE from numeric_cols (never a date), and the `month`
    # category must appear in NEITHER value picker.
    _pick_arearange_sample(app)  # columns: month, forecast_low, forecast_high
    low = next(sb for sb in app.selectbox if sb.label == "Low (bottom)")
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    for picker in (low, high):
        assert "month" not in picker.options
        assert set(picker.options) == {"forecast_low", "forecast_high"}


def test_app_arearange_high_survives_a_low_change(app):
    # The keyless-widget trap High's constant `index` guards against — the shared control, so the
    # same guarantee columnrange has. A 3-numeric CSV gives room to change Low without colliding.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        ("bands.csv", b"category,a,b,c\nX,1,5,9\nY,2,6,10\n", "text/csv")
    ).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("arearange").run()
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    high.set_value("c").run()  # not the default (the 2nd numeric, "b")
    assert not app.exception
    low = next(sb for sb in app.selectbox if sb.label == "Low (bottom)")
    low.set_value("b").run()  # change Low a -> b
    assert not app.exception
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    assert high.value == "c"  # not reset to the default


def test_app_arearange_low_equals_high_shows_guard_warning(app):
    # The shared MAGNITUDE_RANGE low==high guard, so arearange gets it for free: a band would
    # collapse to a line. It fires a warning and stops rather than blowing up the page.
    _pick_arearange_sample(
        app
    )  # Low defaults forecast_low, High defaults forecast_high
    high = next(sb for sb in app.selectbox if sb.label == "High (top)")
    high.set_value("forecast_low").run()  # == the Low column
    assert not app.exception
    assert app.warning
    assert "Low and High must be different" in app.warning[0].value


def test_app_arearange_kpi_shows_points(app):
    # Arearange is one continuous band, so the KPI swaps "Series plotted" (a bare 1) for "Points" —
    # its own noun, distinct from columnrange's "Ranges", counting the band's (low, high) vertices.
    df = _pick_arearange_sample(app)
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    expected = count_marks(df, "arearange", "month", ["forecast_low"])
    assert metrics["Points"] == f"{expected:,}"
    assert expected == len(df) == 12


def test_app_heatmap_kpi_shows_cells_from_count_marks(app):
    # Heatmap swaps "Series plotted" for "Cells", sourced from the builder's count_marks so
    # the KPI can't drift from the grid the chart draws. Assert the app's number equals
    # count_marks on the default selection (X = first column, Y = first numeric column).
    from highcharts_builder import count_marks
    from sample_data import SAMPLES

    app.selectbox[1].set_value("heatmap").run()  # Chart type -> heatmap
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    x = default_df.columns[0]
    y = [default_df.select_dtypes("number").columns[0]]
    assert metrics["Cells"] == f"{count_marks(default_df, 'heatmap', x, y):,}"


def test_app_treemap_kpi_shows_tiles_from_count_marks(app):
    # Treemap swaps "Series plotted" for "Tiles", likewise from count_marks (rows with a
    # drawable label AND a plottable value), so the KPI matches the tiles actually laid out.
    from highcharts_builder import count_marks
    from sample_data import SAMPLES

    app.selectbox[1].set_value("treemap").run()  # Chart type -> treemap
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    x = default_df.columns[0]
    y = [default_df.select_dtypes("number").columns[0]]
    assert metrics["Tiles"] == f"{count_marks(default_df, 'treemap', x, y):,}"


@pytest.mark.parametrize("chart_type", ["funnel", "pyramid"])
def test_app_funnel_family_kpi_shows_stages_from_count_marks(app, chart_type):
    # Funnel/pyramid swap "Series plotted" for "Stages", from count_marks (rows with a drawable
    # label AND a plottable value) — unlike their twin pie, which opts out and shows a bare 1. So
    # the KPI matches the stages actually drawn.
    from highcharts_builder import count_marks
    from sample_data import SAMPLES

    app.selectbox[1].set_value(chart_type).run()  # Chart type -> funnel / pyramid
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    default_df = next(iter(SAMPLES.values()))()
    x = default_df.columns[0]
    y = [default_df.select_dtypes("number").columns[0]]
    assert metrics["Stages"] == f"{count_marks(default_df, chart_type, x, y):,}"


def test_app_chart_type_selector_offers_every_supported_type(app):
    # Contract test mirroring test_app_render_mode_selector_offers_the_two_modes:
    # the chart-type selectbox offers exactly SUPPORTED_TYPES (so a new builder
    # type shows up in the UI, and a removed/renamed one fails here) and defaults
    # to the first. Also pins the positional index [1] other app tests rely on.
    selector = app.selectbox[1]
    assert selector.label == "Chart type"
    assert list(selector.options) == list(SUPPORTED_TYPES)
    assert selector.value == SUPPORTED_TYPES[0]


def test_app_custom_title_flows_into_config(app):
    app.text_input(key="chart_title").set_value("My Title")
    _reveal_config(app)
    assert not app.exception
    assert "My Title" in app.code[0].value


def test_app_multiple_series_selected(app):
    # The revenue-vs-cost sample has two numeric columns; select both via pills.
    app.pills[0].set_value(["revenue", "cost"])
    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "revenue" in js and "cost" in js


def _chart_type_selectbox(app):
    """The Chart type selectbox, by LABEL — see `_pick_sample` on why not by position."""
    return next(sb for sb in app.selectbox if sb.label == "Chart type")


def test_app_y_selection_survives_a_label_only_chart_type_switch(app):
    # solidgauge -> gauge changes exactly ONE thing about the Y widget: the noun in its
    # label ("Rings (Y)" -> "Needles (Y)", a deliberate distinction). The option list is
    # `numeric_cols` for both, so the user's answer is still valid across the switch and
    # must survive it.
    #
    # It only survives because the widget is KEYED. `compute_and_register_element_id`
    # folds every command kwarg into a KEYLESS widget's identity — the LABEL included, not
    # just the `index`/`default` the sidebar's other comments name — so without `key=` this
    # switch re-mints the pills and silently resets the selection. Deleting `key=y_key`
    # fails this test; that is the whole point of it.
    _chart_type_selectbox(app).set_value("solidgauge").run()
    assert not app.exception
    rings = next(p for p in app.pills if p.label.startswith("Rings"))
    rings.set_value(["revenue", "cost"]).run()
    assert not app.exception

    _chart_type_selectbox(app).set_value("gauge").run()
    assert not app.exception
    needles = next(p for p in app.pills if p.label.startswith("Needles"))
    assert list(needles.value) == ["revenue", "cost"], (
        "the Y selection was reset by a chart-type switch that changed only the label — "
        "the pills lost their key"
    )


def test_app_x_selection_survives_a_label_only_chart_type_switch(app):
    # The X selectbox's half of the same claim: line -> scatter relabels it
    # "Category (X) axis" -> "X axis" while the choices stay `df.columns`, so a keyless
    # widget would re-mint and drop a still-valid answer. "cost" rather than the default
    # "month" so a carried-over value is distinguishable from a reset one.
    x_axis = next(sb for sb in app.selectbox if sb.label == "Category (X) axis")
    x_axis.set_value("cost").run()
    assert not app.exception

    _chart_type_selectbox(app).set_value("scatter").run()
    assert not app.exception
    assert next(sb for sb in app.selectbox if sb.label == "X axis").value == "cost", (
        "the X selection was reset by a chart-type switch that changed only the label — "
        "the selectbox lost its key"
    )


def test_app_dataset_switch_reconciles_a_stale_y_selection(app):
    # The other half of keying the Y pills. A key makes `default=` first-render-only, and
    # Streamlit's multiselect/pills FILTER a stored selection against the current options
    # rather than resetting it (selectbox is the one that resets, which is why X needs no
    # guard) — so a Dataset switch leaves Y EMPTY and drops the page onto the "Pick at least
    # one numeric column" guard, where the keyless version showed a chart. That is a degraded
    # landing, not a crash, and it is what the reconciliation in front of the widget exists to
    # undo. Narrowing it to `if stored is None:` (seed-only) fails this test with `Y is []`.
    from sample_data import SAMPLES

    app.pills[0].set_value(["revenue", "cost"]).run()
    assert not app.exception

    other = next(key for key in SAMPLES if "(pie/bar/column)" in key)
    next(sb for sb in app.selectbox if sb.label == "Dataset").set_value(other).run()
    assert not app.exception, (
        f"a stale Y selection survived into {other!r} and reached the builder"
    )
    selected = list(app.pills[0].value)
    available = list(SAMPLES[other]().select_dtypes("number").columns)
    assert selected and set(selected) <= set(available), (
        f"Y is {selected}, which is not a non-empty subset of {available}"
    )


def test_app_x_equals_y_shows_guard_warning(app):
    # Force the category-x "X can't also be a Y series" guard (CATEGORY_X_TYPES)
    # from the UI, exercised here via the default line/cartesian type: set the X
    # axis to a numeric column and pick that same column as the Y series.
    app.selectbox[2].set_value("revenue").run()  # Category (X) axis
    app.pills[0].set_value(["revenue"]).run()  # Series (Y)
    assert not app.exception
    assert app.warning
    assert "can't also be a Y series" in app.warning[0].value


def test_app_upload_csv_with_no_file_shows_info_guard(app):
    # The second data source: switching to "Upload CSV" with no file uploaded
    # hits the st.info + st.stop guard. Network-free (no CSV read, no render).
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    assert not app.exception
    assert app.info
    assert "Upload a CSV" in app.info[0].value


def test_app_render_mode_selector_offers_the_two_modes(app):
    # After removing the click-events mode, the Render selector offers exactly
    # two modes and defaults to the interactive one. This pins the two-mode
    # contract (a re-added or renamed mode fails here) and guards the positional
    # index [1] the other app tests rely on.
    mode = app.segmented_control[1]
    assert mode.label == "Mode"
    assert list(mode.options) == ["Interactive", "Static PNG"]
    assert mode.value == "Interactive"


def test_app_default_interactive_mode_shows_iframe_caption(app):
    # The default (Interactive) render shows the iframe (CDN) caption; the
    # negative check that no click-events caption appears is a light backstop —
    # the selector-options test above owns the two-mode contract.
    assert not app.exception
    assert any(
        "Highcharts JS is loaded from the CDN" in cap.value for cap in app.caption
    )
    assert not any("Custom Component" in cap.value for cap in app.caption)


def test_app_generated_config_includes_brand_palette(app):
    # The brand palette reaches the iframe/PNG paths through build_options; the
    # generated-config toggle is the visible proof once switched on.
    _reveal_config(app)
    assert not app.exception
    assert DEFAULT_COLORS[0] in app.code[0].value


def _csv_bytes(num_numeric: int) -> bytes:
    """A CSV: one label column + ``num_numeric`` numeric columns, three rows."""
    header = ",".join(["label"] + [f"m{i}" for i in range(num_numeric)])
    rows = "\n".join(
        f"r{r}," + ",".join(str(r + i) for i in range(num_numeric)) for r in range(3)
    )
    return (header + "\n" + rows).encode()


def test_app_wide_csv_upload_swaps_pills_for_multiselect(app):
    # The Y-series picker uses compact pills for narrow data (<=5 numeric columns,
    # like every sample) but falls back to st.multiselect for a wide uploaded CSV
    # so it doesn't wrap the narrow sidebar. Seven numeric columns trips it.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(("wide.csv", _csv_bytes(7), "text/csv")).run()
    assert not app.exception
    assert not app.pills  # the pills widget is gone
    assert len(app.multiselect) == 1
    assert list(app.multiselect[0].options) == [f"m{i}" for i in range(7)]


def test_app_narrow_csv_upload_keeps_pills(app):
    # A narrow upload (<=5 numeric columns) stays on pills, like the samples — so
    # the pills-based tests above keep exercising the common path.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(("narrow.csv", _csv_bytes(2), "text/csv")).run()
    assert not app.exception
    assert len(app.pills) == 1
    assert not app.multiselect


@pytest.mark.parametrize(("num_numeric", "widget"), [(5, "pills"), (6, "multiselect")])
def test_app_pills_multiselect_boundary(app, num_numeric, widget):
    # Pin the MAX_PILL_OPTIONS (5) threshold at its edge: exactly 5 numeric columns
    # keeps pills, 6 switches to multiselect. The wide/narrow tests use 7 and 2,
    # far from the decision point, so an off-by-one would slip past them.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        (f"n{num_numeric}.csv", _csv_bytes(num_numeric), "text/csv")
    ).run()
    assert not app.exception
    if widget == "pills":
        assert len(app.pills) == 1 and not app.multiselect
    else:
        assert len(app.multiselect) == 1 and not app.pills


def test_app_chart_type_selector_has_help(app):
    # The chart-type selector silently reshapes the X/Y controls, so it carries a
    # markdown help tooltip naming each type's data shape (mirrors the Mode help).
    help_text = app.selectbox[1].help  # selectbox [1] is Chart type
    assert help_text
    assert "pie" in help_text and "scatter" in help_text and "bubble" in help_text
    assert "radar" in help_text
    assert "heatmap" in help_text
    assert "treemap" in help_text
    assert "sankey" in help_text
    assert "boxplot" in help_text
    # Every cartesian type is named in the prose; loop so a future addition to
    # CARTESIAN_TYPES that's forgotten in the help text actually fails here.
    for chart_type in CARTESIAN_TYPES:
        assert chart_type in help_text


def test_app_kpi_row_summarizes_active_data(app):
    # The KPI row surfaces the active data at a glance. Derive the expected values
    # from the same sources the app uses, rather than hardcoding sample internals.
    from sample_data import SAMPLES

    default_df = next(iter(SAMPLES.values()))()  # the first dataset is the default
    numeric = default_df.select_dtypes("number").columns
    assert _metrics(app) == {
        "Rows": f"{len(default_df):,}",
        "Numeric columns": str(len(numeric)),
        "Series plotted": "1",  # the default selects numeric_cols[:1]
    }


def test_app_kpi_series_count_tracks_selection_and_empty_state(app):
    # "Series plotted" follows the Y selection and reads 0 — a useful empty state,
    # not a blank — once cleared, since the KPI row sits above the empty-y guard.
    app.pills[0].set_value(["revenue", "cost"]).run()
    assert not app.exception
    assert _metrics(app)["Series plotted"] == "2"
    app.pills[0].set_value([]).run()
    assert not app.exception
    assert _metrics(app)["Series plotted"] == "0"


def test_app_heatmap_kpi_shows_cells_not_series(app):
    # Heatmap is a single series, so the KPI swaps "Series plotted" (which would
    # misreport len(y_cols)) for "Cells" = rows × columns.
    from sample_data import SAMPLES

    app.selectbox[1].set_value("heatmap").run()  # Chart type -> heatmap
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    # Default dataset (6 rows); the default Y selection is one column -> 6 cells.
    default_df = next(iter(SAMPLES.values()))()
    assert metrics["Cells"] == f"{len(default_df) * 1:,}"


def test_app_treemap_kpi_shows_tiles(app):
    # Treemap is one series of tiles (like pie), so the KPI swaps "Series plotted"
    # (which would read a bare 1) for "Tiles" = the non-null values that become
    # rectangles — mirroring heatmap's "Cells".
    from sample_data import SAMPLES

    app.selectbox[1].set_value("treemap").run()  # Chart type -> treemap
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    # Default dataset; treemap's single-value control selects one column, so every
    # (non-null) row is one tile.
    default_df = next(iter(SAMPLES.values()))()
    assert metrics["Tiles"] == f"{len(default_df):,}"


def test_app_chart_type_badge_reflects_selection(app):
    # Chart type is a categorical badge by the chart (not a metric), and updates
    # when the selection changes. AppTest renders st.badge as markdown.
    def badge_texts(a):
        return [m.value for m in a.markdown if "-badge[" in m.value]

    assert any("Line chart" in b for b in badge_texts(app))
    app.selectbox[1].set_value("pie").run()  # Chart type -> pie
    assert not app.exception
    assert any("Pie chart" in b for b in badge_texts(app))


# The gauge family's app tests are PARAMETRIZED over GAUGE_TYPES rather than written twice, and
# that is the point rather than a saving. Every behaviour below — the absent X control, the
# builder-sourced aggregation picker, the builder-seeded keyless dial and both halves of its
# re-mint rule, the no-span warning, the KPI — belongs to the FAMILY: it follows from having no
# label channel and from reducing whole columns against one dial, which is exactly what
# `GAUGE_TYPES` means. A second copy would let the two drift, and the drift would be invisible.
# Only the emitted `chart.type` is per-type, and it is threaded through as a literal.
def _gauge_app(app, chart_type: str):
    """Switch the app to one of the gauge types and return it. The default dataset works: its
    numerics are revenue/cost, which either gauge happily reduces."""
    app.selectbox[1].set_value(chart_type).run()  # Chart type
    assert not app.exception
    return app


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_switch_to_gauge_hides_the_x_control_and_shows_the_dial_controls(
    app, chart_type
):
    # The ONLY SUBTRACTIVE control change in this app: every other type's extra widget is
    # additive (bubble's Size, sankey's Target, sunburst's Parent, xrange's End), but the gauge
    # family REMOVES the X selectbox — no label channel, so a control there would do nothing,
    # and a control that does nothing is a lie in the UI.
    assert any(sb.label == "Category (X) axis" for sb in app.selectbox)
    _gauge_app(app, chart_type)
    assert not any(sb.label == "Category (X) axis" for sb in app.selectbox)
    assert any(sb.label == "Reduce each column by" for sb in app.selectbox)
    assert [n.label for n in app.number_input] == ["Dial min", "Dial max"]
    # Multi-select Y: each column is one mark (a ring, or a needle).
    assert app.pills
    _reveal_config(app)
    assert not app.exception
    assert f"type: '{chart_type}'" in app.code[0].value
    # The solid gauge's pane is what resolves highcharts-more — without it the iframe is silently
    # blank while the PNG renders perfectly. The needle's pane is only geometry (it resolves the
    # module from chart.type alone), but both emit one, so the assertion holds for the family.
    assert "pane" in app.code[0].value


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_gauge_aggregation_picker_offers_exactly_the_builders_reductions(
    app, chart_type
):
    # Sourced from the builder, so the app can never offer a reduction the builder rejects —
    # `coordinate_columns`' can't-drift rule, applied to a POLICY rather than to a column.
    _gauge_app(app, chart_type)
    picker = next(sb for sb in app.selectbox if sb.label == "Reduce each column by")
    assert list(picker.options) == list(GAUGE_AGGREGATIONS)


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_gauge_dial_defaults_come_from_the_builder(app, chart_type):
    # The can't-drift rule applied to a widget's VALUE rather than to its options: the number the
    # app SHOWS is the very dial the chart DRAWS. The app must not recompute it — a max derived
    # here from the raw column would be smaller than every reading under `sum`, pinning every mark
    # at 100% with nothing on the page to say why.
    from sample_data import SAMPLES

    _gauge_app(app, chart_type)
    df = next(iter(SAMPLES.values()))()
    y_cols = [p for p in app.pills[0].value]
    low, high = gauge_dial(df, y_cols, "sum")
    assert [n.value for n in app.number_input] == [low, high]


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_gauge_dial_override_reaches_the_chart_and_survives_an_inert_rerun(
    app, chart_type
):
    # HALF ONE of the keyless-widget decision. A typed dial is scoped to its derivation, not to
    # every rerun: it survives a change that cannot affect it (the title).
    _gauge_app(app, chart_type)
    app.number_input[1].set_value(1000.0).run()
    assert not app.exception
    _reveal_config(app)
    assert "max:1000" in "".join(app.code[0].value.split())  # it reached the chart
    app.text_input[0].set_value("A different title").run()  # inert w.r.t. the dial
    assert not app.exception
    assert app.number_input[1].value == 1000.0  # the override stands


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_gauge_dial_re_mints_when_the_aggregation_changes(app, chart_type):
    # HALF TWO, and the reason there is NO `key=` on these inputs. A dial derives from the DATA
    # under a REDUCTION, so an override of it is meaningless the moment either changes: a max of
    # 500 typed against `sum` would leave every mark at ~1% under `mean`. A `key=` is how you
    # would CAUSE that — with a key, `value=` is honoured only on the FIRST render, so the stale
    # number would become permanent and silent. Re-minting is the INTENDED behaviour here, and
    # it is visible: the box shows the newly derived number.
    _gauge_app(app, chart_type)
    app.number_input[1].set_value(9999.0).run()
    assert app.number_input[1].value == 9999.0
    picker = next(sb for sb in app.selectbox if sb.label == "Reduce each column by")
    picker.set_value("mean").run()  # the derivation changed
    assert not app.exception
    assert app.number_input[1].value != 9999.0  # re-derived, not carried over


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_gauge_a_dial_with_no_span_warns_instead_of_crashing(app, chart_type):
    # The third builder error reachable from this page (after sunburst's cycle and xrange's
    # axis mismatch), and the first that is not about a COLUMN at all: two number inputs accept
    # any two numbers, so a max at or below the min is one keystroke away. The interactive path
    # does not catch builder errors, so this must warn and stop rather than throw a traceback.
    _gauge_app(app, chart_type)
    app.number_input[1].set_value(-10.0).run()  # max below min
    assert not app.exception
    assert app.warning
    assert "must be a finite number above its minimum" in app.warning[0].value


@pytest.mark.parametrize("chart_type", GAUGE_TYPES)
def test_app_gauge_kpi_counts_the_marks_as_series(app, chart_type):
    # The family is deliberately absent from MARK_METRICS: its marks ARE its series, so the
    # default "Series plotted" is already literally the ring/needle count. An entry would force a
    # count_marks rule that only restated len(y_cols) — the can't-drift rule run backwards.
    _gauge_app(app, chart_type)
    metrics = _metrics(app)
    assert metrics["Series plotted"] == str(len(app.pills[0].value))


def test_app_needle_gauge_y_control_names_the_mark_it_draws(app):
    # The one place the two types' controls DIFFER, and the reason it is worth differing: a
    # reader picking columns should be told what each one will BECOME. Same widget, same
    # cardinality, different noun.
    _gauge_app(app, "solidgauge")
    assert "Rings" in app.pills[0].label
    _gauge_app(app, "gauge")
    assert "Needles" in app.pills[0].label


# --------------------------------------------------------------------------- #
# Bullet — the app layer
# --------------------------------------------------------------------------- #
# These are the columnrange/arearange AppTests one type over, and the resemblance is the
# point: bullet reuses their control SHAPE (a category X, a single-select magnitude Y, a
# second magnitude selectbox drawn from numeric_cols, a dedicated equality guard the
# x-in-y rule cannot express) while meaning something else entirely — so every test here
# pins the ONE thing that differs: the label, the kwarg, the noun, the warning text. A
# control shape copied wholesale is exactly what silently ends up wired to the wrong
# kwarg, and only the emitted config can tell.
def _pick_bullet_sample(app):
    """Select the bullet sample dataset and switch the chart type to bullet.

    The quota sample is the one whose two leading numeric columns ARE a measure and a goal, so the
    picker, KPI and guard tests read the numbers the type is meant to draw rather than borrowing
    the landing dataset's revenue/cost pair and hoping it means the same thing."""
    return _pick_sample(app, "bullet")


def test_app_switch_to_bullet_shows_goal_control_and_regenerates_config(app):
    # Bullet is the sixth type with a required extra column (after bubble's Size, sankey's Target,
    # sunburst's Parent, xrange's End and the magnitude-range family's High): it reveals a "Goal
    # (target)" selectbox no other type shows and drives the config through the goal_col plumbing.
    # The LABEL matters as much as the presence — "Goal", never "Target", because "Target (to)"
    # already names a destination NODE in this same sidebar for all four node-link types, and one
    # word cannot mean both a label and a magnitude. That collision is the whole reason goal_col is
    # its own kwarg rather than a reuse, so a test asserting only "some second selectbox appeared"
    # would pin nothing about it.
    #
    # The Y control is a SINGLE-select labelled "Measure (bar)" — not the multi-select pills, and
    # not columnrange's "Low (bottom)": bullet's two numbers are not the two ends of one bar but
    # two independent channels, and the label is the only place in the UI that says so.
    assert not any(sb.label == "Goal (target)" for sb in app.selectbox)  # absent
    df = _pick_bullet_sample(app)
    assert not app.exception
    assert not app.error  # the no-numeric-columns gate has nothing to say here
    assert len([sb for sb in app.selectbox if sb.label == "Goal (target)"]) == 1
    assert any(sb.label == "Measure (bar)" for sb in app.selectbox)
    assert not app.pills
    assert not app.multiselect
    # The defaults land on DISTINCT columns, so no warning fires on a freshly picked sample —
    # `deals_closed` is carried third precisely so the Goal picker's constant second-numeric index
    # lands on `quota` rather than on the throwaway column.
    measure = next(sb for sb in app.selectbox if sb.label == "Measure (bar)")
    goal = next(sb for sb in app.selectbox if sb.label == "Goal (target)")
    assert (measure.value, goal.value) == ("actual", "quota")
    assert not app.warning
    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'bullet'" in js
    # The sample's own numbers reached the chart, which is what proves the config was regenerated
    # through the bullet branch rather than left over from the previous type.
    for actual in df["actual"]:
        assert str(actual) in js


def test_app_bullet_measure_and_goal_pickers_offer_only_numeric_columns(app):
    # A goal is a MAGNITUDE, so both pickers are sourced from numeric_cols — NOT from df.columns
    # (sankey's Target / sunburst's Parent / organization's Title are drawn from every column
    # because THOSE are labels) and NOT from coordinate_columns (xrange's End, because a start and
    # an end may be dates and a goal never can). Offering `region` here would hand the builder a
    # column it can only turn around and reject, which is the invariant these picker-source tests
    # keep: the app never offers a column the builder would refuse.
    df = _pick_bullet_sample(app)
    measure = next(sb for sb in app.selectbox if sb.label == "Measure (bar)")
    goal = next(sb for sb in app.selectbox if sb.label == "Goal (target)")
    numeric = set(df.select_dtypes("number").columns)
    for picker in (measure, goal):
        assert "region" not in picker.options
        assert set(picker.options) == numeric == {"actual", "quota", "deals_closed"}


def test_app_bullet_goal_survives_a_measure_change(app):
    # THE KEYLESS-WIDGET RULE, stated: fold the default into the widget's identity IFF the
    # SELECTION depends on the state the default DERIVES from. The Goal selectbox carries no
    # `key=`, so Streamlit folds its `index` into the widget's identity — which is why that index
    # is a CONSTANT (`min(1, …)`, the second numeric column) rather than the tempting "the column
    # after Measure". A default derived from the current Measure would re-mint the widget the
    # instant Measure changed, silently discarding a Goal the user had deliberately picked.
    #
    # And a `key=` here would be the BUG, not the fix — the inverse of the gauge Dial's case. A
    # goal derives from the numeric-column LIST (the dataset), never from the Measure selection,
    # and a chosen Goal stays perfectly VALID when Measure changes, so there is nothing to
    # re-derive. Add a key and `index=` is honoured only on the FIRST render, so the widget would
    # freeze on whatever the dataset happened to offer then and survive a dataset swap that made it
    # meaningless. Target's / Parent's / End's / High's case exactly.
    #
    # A three-numeric CSV gives room to move Measure without colliding with Goal — which matters,
    # since a collision would fire the equality guard and st.stop() the page before this could be
    # observed at all, and the test would pass vacuously on a two-column frame.
    app.segmented_control[0].set_value("Upload CSV").run()  # Source
    app.file_uploader[0].set_value(
        ("kpi.csv", b"team,a,b,c\nX,1,5,9\nY,2,6,10\n", "text/csv")
    ).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("bullet").run()
    goal = next(sb for sb in app.selectbox if sb.label == "Goal (target)")
    assert goal.value == "b"  # the constant index: the SECOND numeric column
    goal.set_value("c").run()  # a deliberate pick, away from the default
    assert not app.exception
    measure = next(sb for sb in app.selectbox if sb.label == "Measure (bar)")
    measure.set_value("b").run()  # change Measure a -> b
    assert not app.exception
    goal = next(sb for sb in app.selectbox if sb.label == "Goal (target)")
    assert goal.value == "c"  # NOT reset to the default


def test_app_bullet_single_numeric_column_clamps_goal_onto_measure_and_warns(app):
    """The `min(1, len - 1)` clamp — a guard that fires BY ACCIDENT rather than by design.

    Every other bullet app test runs on a three-numeric-column frame, where the constant index
    lands on a genuinely distinct second column. On a ONE-numeric-column CSV — a perfectly ordinary
    upload — the clamp has nowhere else to go and pins Goal onto Measure, so the equality guard
    fires on a selection the USER never made. That is the intended reading (a bullet needs two
    numbers), but it is intended by a comment, not by a test: an index written `1` without the
    clamp would `IndexError` the page instead, and one written as "the next column after Measure"
    would wrap around to it silently.

    What must hold is what the guard promises everywhere else: a WARNING, not an exception. The
    builder raises `ValueError` on this same pair and the interactive path does not catch builder
    errors, so if the app-side mirror did not fire first the user would get a bare traceback for
    uploading a two-column file.
    """
    app.segmented_control[0].set_value("Upload CSV").run()
    app.file_uploader[0].set_value(
        ("one.csv", b"region,actual\nNorth,420\nSouth,512\n", "text/csv")
    ).run()
    chart_type = next(sb for sb in app.selectbox if sb.label == "Chart type")
    chart_type.set_value("bullet").run()

    measure = next(sb for sb in app.selectbox if sb.label == "Measure (bar)")
    goal = next(sb for sb in app.selectbox if sb.label == "Goal (target)")
    assert (
        measure.value == goal.value == "actual"
    )  # the clamp, with nowhere else to land
    assert not app.exception  # a warning, NOT the builder's traceback
    assert app.warning
    assert "Measure and Goal must be different" in app.warning[0].value


def test_app_bullet_measure_equals_goal_shows_guard_warning(app):
    # Bullet's own collision, the fifth of these and NOT the x-in-y rule (the Goal column is the
    # goal_col selector, never among the Y series). It fails in this type's own idiom and it fails
    # SILENTLY: every bar would land exactly on its own crossbar, so the chart would report that
    # every category hit its target precisely — a confident, plausible, entirely fabricated claim,
    # drawn with no error anywhere.
    #
    # `not app.exception` is the whole point of this test rather than boilerplate. The builder ALSO
    # raises ValueError on this pair and the interactive path does NOT catch builder errors — so
    # without the app-side mirror firing FIRST, a user who pointed Goal at Measure would get a bare
    # traceback across the page instead of a sentence telling them what they did. The warning must
    # arrive in FRONT of the raise, not instead of it (columnrange's double).
    _pick_bullet_sample(app)  # Measure defaults `actual`, Goal defaults `quota`
    goal = next(sb for sb in app.selectbox if sb.label == "Goal (target)")
    goal.set_value("actual").run()  # == the Measure column
    assert not app.exception  # the guard fires; it does NOT blow up the page
    assert app.warning
    assert "Measure and Goal must be different" in app.warning[0].value


def test_app_bullet_kpi_shows_measures(app):
    # Bullet is a single measure/goal series, so its default "Series plotted" would read a bare 1,
    # exactly as columnrange's and arearange's would. It swaps in "Measures".
    #
    # The noun is the assertion. "Measures", not xrange's "Bars", because the bar is only HALF of
    # what a bullet draws — every mark is a bar AND its crossbar, and the number counts the
    # pairing. The value is asserted against the sample's LITERAL row count rather than against a
    # `count_marks` call: the app computes the KPI by calling `count_marks`, so asserting one call
    # against another is circular and would agree happily on a number wrong for both.
    df = _pick_bullet_sample(app)
    assert not app.exception
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    assert metrics["Measures"] == "6"
    assert (
        len(df) == 6
    )  # and neither value column can drop a mark, so it IS the row count


def test_app_leaving_bullet_retires_the_goal_control_and_the_measures_kpi(app):
    """The subtractive half, which every other app test here asserts only in the additive
    direction.

    A control that lingers is how a stale `goal_col` gets threaded into a type that must ignore it
    — and bullet's kwarg DOES touch the cache layer, so a stale value is a stale cache KEY, not
    merely a stale widget. The KPI is the same claim one row down: "Measures" is a `MARK_METRICS`
    entry keyed on the type, so leaving bullet must restore "Series plotted" rather than go on
    counting something the chart no longer draws.
    """
    _pick_bullet_sample(app)
    assert any(sb.label == "Goal (target)" for sb in app.selectbox)
    assert "Measures" in {m.label for m in app.metric}

    app.selectbox[1].set_value("column").run()
    assert not app.exception
    assert not any(sb.label == "Goal (target)" for sb in app.selectbox)
    assert not any(sb.label == "Measure (bar)" for sb in app.selectbox)
    labels = {m.label for m in app.metric}
    assert "Measures" not in labels
    assert "Series plotted" in labels


# --------------------------------------------------------------------------- #
# Variwide's Width control
# --------------------------------------------------------------------------- #
# The bullet AppTests one type over, and worth writing out rather than trusting to the sweep for
# the same reason bullet's were: variwide reuses that control SHAPE wholesale (a category X, a
# single-select magnitude Y, a second magnitude selectbox drawn from numeric_cols with the same
# constant index, a dedicated equality guard the x-in-y rule cannot express) while meaning
# something else entirely — the width is not a goal, and it feeds `width_col`, not `goal_col`. A
# control shape copied wholesale is exactly what silently ends up wired to the wrong kwarg, and
# nothing but the emitted config can tell.
def _pick_variwide_sample(app):
    """Select the variwide sample dataset and switch the chart type to variwide.

    The product-line sample is the one whose two leading numeric columns ARE a height and a width,
    and — unlike any other sample here — whose two columns deliberately ANTI-correlate, so a test
    that read them in the wrong order would produce visibly different numbers rather than
    plausible ones."""
    return _pick_sample(app, "variwide")


def test_app_switch_to_variwide_shows_width_control_and_regenerates_config(app):
    # The seventh type with a required extra column (after bubble's Size, sankey's Target,
    # sunburst's Parent, xrange's End, the magnitude-range family's High and bullet's Goal).
    assert not any(sb.label == "Width" for sb in app.selectbox)
    _pick_variwide_sample(app)
    assert not app.exception
    assert not app.error  # the no-numeric-columns gate stays silent
    assert len([sb for sb in app.selectbox if sb.label == "Width"]) == 1
    # The Y control is a single-select named for the GEOMETRIC CHANNEL, so it pairs with "Width"
    # and the two read as the two dimensions of one rectangle.
    assert any(sb.label == "Height (bar)" for sb in app.selectbox)
    assert not app.pills
    assert not app.multiselect

    height = next(sb for sb in app.selectbox if sb.label == "Height (bar)")
    width = next(sb for sb in app.selectbox if sb.label == "Width")
    # The defaults land on DISTINCT columns, so the sample demonstrates the type on landing and
    # the equality guard does not fire.
    assert (height.value, width.value) == ("margin_pct", "revenue_musd")
    assert not app.warning

    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'variwide'" in js
    # Both channels reached the config, in the right slots — the check that a copied control
    # shape wired to `goal_col` would fail while every other assertion here still passed.
    assert "[62.0,21.0]" in "".join(js.split())


def test_app_variwide_height_and_width_pickers_offer_only_numeric_columns(app):
    """Both are magnitudes, so both are sourced from numeric_cols — not from all columns (unlike
    Target/Parent/Title, which name LABELS) and not from coordinate_columns (unlike xrange's End,
    which names a coordinate that may be a date). A width can never be a date and never a label."""
    df = _pick_variwide_sample(app)
    numeric = list(df.select_dtypes("number").columns)
    height = next(sb for sb in app.selectbox if sb.label == "Height (bar)")
    width = next(sb for sb in app.selectbox if sb.label == "Width")
    assert list(height.options) == numeric
    assert list(width.options) == numeric
    assert "product_line" not in width.options


def test_app_variwide_width_survives_a_height_change(app):
    """The keyless-widget rule, stated in full at bullet's equivalent: fold the default into the
    widget's identity IFF the SELECTION depends on the state the default DERIVES from. A width
    default derives from the numeric-column LIST, never from the Height selection — and a chosen
    Width stays perfectly VALID when Height moves, so re-minting it would discard a real answer.
    That is Target's/Parent's/End's/High's/Goal's case, not the gauge Dial's."""
    _pick_variwide_sample(app)
    width = next(sb for sb in app.selectbox if sb.label == "Width")
    # The constant index landed on the SECOND numeric column.
    assert width.value == "revenue_musd"
    width.set_value("sku_count").run()
    assert not app.exception
    next(sb for sb in app.selectbox if sb.label == "Height (bar)").set_value(
        "revenue_musd"
    ).run()
    assert not app.exception
    # Unchanged: a Width is still a valid width when the Height moves.
    assert next(sb for sb in app.selectbox if sb.label == "Width").value == "sku_count"


def test_app_variwide_height_equals_width_shows_guard_warning(app):
    """Claim-fabricating rather than cosmetic, so the app warns and stops IN FRONT of the
    builder's ValueError (the interactive path does not catch): every bar's area would be its
    height squared."""
    _pick_variwide_sample(app)
    next(sb for sb in app.selectbox if sb.label == "Width").set_value(
        "margin_pct"
    ).run()
    assert not app.exception
    assert app.warning
    assert "different columns" in app.warning[0].value


def test_app_variwide_kpi_shows_bars(app):
    """ "Bars", xrange's noun rather than bullet's "Measures": a variwide draws exactly one
    rectangle per category, the width being a property OF the bar rather than a second mark
    beside it. Checked against the sample's literal row count rather than against count_marks,
    which would be circular."""
    df = _pick_variwide_sample(app)
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    assert metrics["Bars"] == str(len(df))


def test_app_leaving_variwide_retires_the_width_control_and_the_bars_kpi(app):
    """The subtractive direction, which is where a control that is added but never removed shows
    up: the Width picker and the "Bars" KPI must both disappear when the type changes."""
    _pick_variwide_sample(app)
    assert any(sb.label == "Width" for sb in app.selectbox)
    assert "Bars" in {m.label for m in app.metric}

    app.selectbox[1].set_value("column").run()
    assert not app.exception
    assert not any(sb.label == "Width" for sb in app.selectbox)
    assert not any(sb.label == "Height (bar)" for sb in app.selectbox)
    labels = {m.label for m in app.metric}
    assert "Bars" not in labels
    assert "Series plotted" in labels


def _pick_dumbbell_sample(app):
    """Select the dumbbell sample dataset and switch the chart type to dumbbell.

    The market-share sample is the one whose two leading numeric columns are the SAME quantity at
    two times, and — uniquely here — whose rows move in MIXED directions. That mix is what these
    tests need: on a frame that only rose, a before/after mix-up would produce a chart that looked
    entirely reasonable, so several assertions below would pass while pinning nothing."""
    return _pick_sample(app, "dumbbell")


def test_app_switch_to_dumbbell_shows_after_control_and_regenerates_config(app):
    # The eighth type with a required extra column (after bubble's Size, sankey's Target,
    # sunburst's Parent, xrange's End, the magnitude-range family's High, bullet's Goal and
    # variwide's Width).
    assert not any(sb.label == "After" for sb in app.selectbox)
    _pick_dumbbell_sample(app)
    assert not app.exception
    assert not app.error  # the no-numeric-columns gate stays silent
    assert len([sb for sb in app.selectbox if sb.label == "After"]) == 1
    # The Y control is a single-select named "Before", so the two read in the order they are
    # drawn. This is the one extra-column pair in the sidebar whose halves are ORDERED.
    assert any(sb.label == "Before" for sb in app.selectbox)
    assert not app.pills
    assert not app.multiselect

    before = next(sb for sb in app.selectbox if sb.label == "Before")
    after = next(sb for sb in app.selectbox if sb.label == "After")
    # The defaults land on DISTINCT columns, so the sample demonstrates the type on landing and
    # the equality guard does not fire.
    assert (before.value, after.value) == ("q1_share_pct", "q4_share_pct")
    assert not app.warning

    _reveal_config(app)
    assert not app.exception
    js = app.code[0].value
    assert "type: 'dumbbell'" in js
    # Both readings reached the config in the right slots, and — the point of choosing a FALLING
    # row for this assertion — in the frame's order rather than sorted. DACH went 28.1 -> 21.5, so
    # a builder that normalized the pair would emit [21.5,28.1] here and every other assertion in
    # this test would still pass.
    assert "[28.1,21.5]" in "".join(js.split())


def test_app_dumbbell_before_and_after_pickers_offer_only_numeric_columns(app):
    """Both are magnitudes in one unit, so both are sourced from numeric_cols — not from all
    columns (unlike Target/Parent/Title, which name LABELS) and not from coordinate_columns
    (unlike xrange's End, which names a coordinate that may be a date). A reading can never be a
    date and never a label."""
    df = _pick_dumbbell_sample(app)
    numeric = list(df.select_dtypes("number").columns)
    before = next(sb for sb in app.selectbox if sb.label == "Before")
    after = next(sb for sb in app.selectbox if sb.label == "After")
    assert list(before.options) == numeric
    assert list(after.options) == numeric
    assert "region" not in after.options


def test_app_dumbbell_after_survives_a_before_change(app):
    """The keyless-widget rule, stated in full at bullet's equivalent: fold the default into the
    widget's identity IFF the SELECTION depends on the state the default DERIVES from. An after
    default derives from the numeric-column LIST, never from the Before selection — and a chosen
    After stays perfectly VALID when Before moves, so re-minting it would discard a real answer.
    That is Target's/Parent's/End's/High's/Goal's/Width's case, not the gauge Dial's."""
    _pick_dumbbell_sample(app)
    after = next(sb for sb in app.selectbox if sb.label == "After")
    # The constant index landed on the SECOND numeric column.
    assert after.value == "q4_share_pct"
    after.set_value("accounts").run()
    assert not app.exception
    next(sb for sb in app.selectbox if sb.label == "Before").set_value(
        "q4_share_pct"
    ).run()
    assert not app.exception
    # Unchanged: an After is still a valid after when the Before moves.
    assert next(sb for sb in app.selectbox if sb.label == "After").value == "accounts"


def test_app_dumbbell_before_equals_after_shows_guard_warning(app):
    """Claim-fabricating rather than cosmetic, so the app warns and stops IN FRONT of the
    builder's ValueError (the interactive path does not catch). This is the one such collision
    whose wrong chart is indistinguishable from a real result: every category would draw its two
    markers at one value, i.e. as "nothing changed anywhere", which is a reading this type exists
    to express."""
    _pick_dumbbell_sample(app)
    next(sb for sb in app.selectbox if sb.label == "After").set_value(
        "q1_share_pct"
    ).run()
    assert not app.exception
    assert app.warning
    assert "two different readings" in app.warning[0].value


def test_app_dumbbell_kpi_shows_changes(app):
    """ "Changes" rather than "Pairs" or xrange's "Bars": a dumbbell draws three shapes per
    category (two markers and the connector joining them) and counts none of them — what it counts
    is the one before-to-after movement they jointly describe. Checked against the sample's literal
    row count rather than against count_marks, which would be circular."""
    df = _pick_dumbbell_sample(app)
    metrics = _metrics(app)
    assert "Series plotted" not in metrics
    assert metrics["Changes"] == str(len(df))


def test_app_leaving_dumbbell_retires_the_after_control_and_the_changes_kpi(app):
    """The subtractive direction, which is where a control that is added but never removed shows
    up: the After picker and the "Changes" KPI must both disappear when the type changes."""
    _pick_dumbbell_sample(app)
    assert any(sb.label == "After" for sb in app.selectbox)
    assert "Changes" in {m.label for m in app.metric}

    app.selectbox[1].set_value("column").run()
    assert not app.exception
    assert not any(sb.label == "After" for sb in app.selectbox)
    assert not any(sb.label == "Before" for sb in app.selectbox)
    labels = {m.label for m in app.metric}
    assert "Changes" not in labels
    assert "Series plotted" in labels


# --------------------------------------------------------------------------- #
# The app's CACHE LAYER — the wiring, checked without the network
# --------------------------------------------------------------------------- #
# The three `@st.cache_data` renderers are the one part of the app the ordinary AppTests
# barely reach. `cached_chart_html` and `cached_chart_js` are covered INDIRECTLY — every
# AppTest runs the app, which calls them, so a bad forward there surfaces as a wrong
# chart — but `cached_chart_png` used to be executed by NOTHING: the AppTests stay on the
# network-free interactive path, and `test_app_render_mode_selector_offers_the_two_modes`
# pins that Static PNG is OFFERED without ever selecting it. A slip in that wrapper
# shipped silently and surfaced only as a wrong Static PNG in production.
#
# The gap was never "the export server is untested" — that is a deliberate and correct
# choice. It is that avoiding the network also un-tested the WIRING, and the two are
# separable. Both halves are now covered, from opposite directions:
#
#   - STATICALLY, by the two `ast` tests below, which read the SOURCE rather than
#     importing the module (importing `streamlit_app` executes the whole Streamlit
#     script) — `test_packaging.py`'s and `test_theme_colors_stay_in_sync_with_config`'s
#     mechanical-sync idea applied to argument passing.
#   - DYNAMICALLY, by `test_app_static_png_mode_executes_the_cached_png_wrapper`, which
#     selects Static PNG for real with the BUILDER swapped for a recorder. That executes
#     the wrapper, builds its cache key, and observes the forwarding as VALUES instead of
#     as AST names — while still contacting no export server.
#
# What they catch is precisely what the keyword form does NOT prevent: `goal_col=high_col`
# type-checks, caches and renders, and just draws the wrong column. Ten of these
# parameters are `str | None`, so nothing else in the toolchain can tell them apart.
_CACHE_LAYER = {  # cached wrapper -> the builder it must forward to
    "cached_chart_html": "build_chart_html",
    "cached_chart_png": "build_chart_png",
    "cached_chart_js": "make_chart",
}


def _keyword_only(fn) -> set[str]:
    """The names of ``fn``'s keyword-only parameters."""
    return {
        name
        for name, param in inspect.signature(fn).parameters.items()
        if param.kind is param.KEYWORD_ONLY
    }


def _forwarded_arguments() -> tuple[str, ...]:
    """The column/policy kwargs every cached wrapper must forward, read off the BUILDERS.

    DERIVED rather than hand-listed, because a hand-listed tuple is a fact with no second
    home — the one property that let `version` go stale for five chart types. A tenth
    extra-column kwarg added to the builders and to the wrappers but omitted here would
    leave that column unchecked while both tests below kept passing: a test that grows
    blind spots as the code grows is worse than one that fails. Deriving it means adding
    a kwarg to the three builders extends the check for free, on the day it is added.

    The intersection drops each render mode's OWN parameters, which are not
    interchangeable with anything (`container_id`, `height`, `scale`, `width`,
    `timeout`). `title` and `dark` survive it and are excluded by name: they are
    forwarded verbatim inside the wrappers, but the call SITES pass them positionally, so
    including them would fail the call-site test for a transposition that cannot happen —
    a `str` title and a `bool` dark are not silently interchangeable with a column name.
    """
    shared = (
        _keyword_only(build_chart_html)
        & _keyword_only(build_chart_png)
        & _keyword_only(make_chart)
    )
    return tuple(sorted(shared - {"title", "dark"}))


# Same-typed, positionally interchangeable, and the whole reason these tests exist. The
# leading arguments (df/chart_type/x_col/y_cols/height/title/dark) are transformed in
# flight (`list(y_cols)`) or differ per wrapper, so they are not pinned by name here.
_FORWARDED = _forwarded_arguments()

# The subset that names a COLUMN. `agg` (a reduction) and `dial` (a scale) are forwarded
# identically but are not columns, and the docs count only the columns — which is why
# CLAUDE.md's two numbers differ. Hoisted rather than re-filtered per test so the one
# place that encodes "these two are not columns" cannot drift between its readers.
_EXTRA_COLUMN_KWARGS = tuple(n for n in _FORWARDED if n not in ("agg", "dial"))


def _app_functions() -> dict[str, ast.FunctionDef]:
    tree = ast.parse((ROOT / "streamlit_app.py").read_text())
    return {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }


@pytest.mark.parametrize(("wrapper", "builder"), sorted(_CACHE_LAYER.items()))
def test_app_cached_renderer_forwards_every_column_kwarg_under_its_own_name(
    wrapper, builder
):
    """Each cached wrapper must pass `foo=foo`, never `foo=bar`.

    A transposition here is invisible to every other gate: it type-checks (ten of the
    parameters are `str | None`), it caches (the key is the bound arguments, which are
    still distinct), and it renders — it just draws the wrong column. For
    `cached_chart_png` nothing else in the suite would notice at all.
    """
    fn = _app_functions()[wrapper]
    call = next(
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == builder
    )
    passed = {kw.arg: kw.value for kw in call.keywords}
    for name in _FORWARDED:
        assert name in passed, f"{wrapper} does not forward {name} to {builder}"
        value = passed[name]
        assert isinstance(value, ast.Name) and value.id == name, (
            f"{wrapper} forwards {name}={ast.unparse(value)} to {builder} — a column "
            f"argument must be forwarded under its OWN name, or the chart silently "
            f"reads the wrong column"
        )


def test_app_calls_its_cached_renderers_with_named_column_arguments():
    """The call SITES pass the same eleven by keyword, so ordering is not a failure mode.

    The wrapper test above pins the inside of each wrapper; this pins the outside. Passing
    these positionally is what made a `high_col`/`title_col`/`goal_col` transposition a
    silent wrong-column bug rather than a `TypeError` — and the project has paid that risk
    NINE times now, once per extra column kwarg (`size_col` through `after_col`; `agg` and
    `dial` are the two entries in `_FORWARDED` that name a policy and a scale rather than a
    column, which is why the two counts differ).
    """
    tree = ast.parse((ROOT / "streamlit_app.py").read_text())
    # The renderer's name is captured HERE rather than read back off `call.func` in the
    # loop: the `isinstance(node.func, ast.Name)` narrowing does not survive out of the
    # comprehension, so `call.func.id` below would be an unresolved attribute on `expr`.
    calls = [
        (node.func.id, node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _CACHE_LAYER
    ]
    assert len(calls) == len(_CACHE_LAYER), (
        "expected exactly one call site per renderer"
    )
    for name, call in calls:
        named = {kw.arg for kw in call.keywords}
        missing = [arg for arg in _FORWARDED if arg not in named]
        assert not missing, (
            f"{name} is called with {missing} passed POSITIONALLY — same-typed "
            f"arguments in a list this long transpose silently"
        )


def test_forwarded_arguments_derivation_is_not_vacuous():
    """The derivation must not silently collapse — an empty tuple passes both tests below.

    `_FORWARDED` is computed from three signatures, so a refactor that made the column
    kwargs positional, or renamed one in only two of the three builders, would shrink the
    intersection instead of raising. Both tests below loop over it, so a shrunk tuple
    checks less and stays GREEN — the vacuous pass this project treats as worse than no
    test at all.

    A FLOOR (`>=`), not an equality, and the distinction is the point: an equality here
    would be a tally on a type-scaled set, so adding a tenth column kwarg would fail this
    test even though the derivation had worked perfectly — contradicting the promise in
    `_forwarded_arguments` that a new kwarg extends the check for free, and teaching the
    next person to bump a number rather than read the failure. Growth is the expected
    direction and needs no assertion; only SHRINKAGE is the bug, and `>=` catches exactly
    that. The named members below carry the rest: they cannot be satisfied by an
    unrelated tuple that merely happens to be long enough.
    """
    assert len(_FORWARDED) >= 11, (
        f"the derivation SHRANK — it found {len(_FORWARDED)} shared keyword-only "
        f"arguments where at least 11 (9 extra-column kwargs + agg + dial) exist, so a "
        f"kwarg is positional or renamed in one builder only: {_FORWARDED}"
    )
    # The two that are NOT column names, and the extremes of the column set.
    for name in ("size_col", "after_col", "agg", "dial"):
        assert name in _FORWARDED


# A real 1x1 PNG: `st.image` decodes its bytes through PIL, so a `b"not-a-png"` stand-in
# fails the render rather than the assertion, blaming the test for the app's behaviour.
_ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def cleared_chart_caches():
    """Clear the `@st.cache_data` caches around a test that installs a STAND-IN builder.

    SYMMETRIC on purpose, and the asymmetry was a real bug: clearing only on the way IN
    protects this test from a cached real render, but leaves its fake behind for everyone
    else. `monkeypatch` restores the patched FUNCTION at teardown; it knows nothing about
    the cached VALUE that function produced, which stays keyed by the real arguments for
    the rest of the session. A later test rendering Static PNG with those same arguments
    would be handed the 1x1 stand-in, call no builder, contact no network, and PASS —
    vacuously, and in the one section of this file whose whole subject is coverage that
    silently isn't there.

    Applies to the `load_csv` cache too, since `st.cache_data.clear()` is global; that is
    harmless here (it only re-reads a sample frame) and is the reason this is a fixture
    rather than a bare call — the teardown runs even when the test fails mid-way.
    """
    import streamlit as st

    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.mark.usefixtures("cleared_chart_caches")
def test_app_static_png_mode_executes_the_cached_png_wrapper(app, monkeypatch):
    """Run the Static PNG path for real, with the builder swapped for a recorder.

    The `ast` tests above read the source; this one EXECUTES `cached_chart_png` — the
    wrapper nothing else in the suite runs — so its forwarding is observed as values
    rather than as AST names, and a wrapper that raised or failed to hash its arguments
    would fail here rather than in production.

    The patch targets `highcharts_builder.build_chart_png` (the module attribute), not the
    app's own binding: `streamlit_app` does `from highcharts_builder import ...`, and
    AppTest re-executes the whole script on every `run()`, so the from-import re-reads the
    patched attribute each time. Patching by string keeps the module out of this file's
    imports. No export server is contacted, so the suite stays network-free.

    Takes the shared `app` fixture like every other control-switching test here rather
    than building its own AppTest. The fixture's initial `.run()` renders the INTERACTIVE
    mode, which never calls `build_chart_png` — so patching in the body, before the
    `.run()` that switches to Static PNG, still covers every call the builder receives.

    The `cleared_chart_caches` fixture empties the renderer caches on BOTH sides: a hit on
    the way in would skip the recorder and read as "the app never called the builder", and
    an entry left on the way out would hand this test's stand-in PNG to the next one.
    """
    seen: dict[str, object] = {}

    # The four leading arguments are passed POSITIONALLY by the wrapper, so they are
    # accepted and ignored here; only the keyword tail is what this test observes.
    def _recorder(_df, _chart_type, _x_col, _y_cols, **kwargs):
        seen.update(kwargs)
        return _ONE_PIXEL_PNG

    monkeypatch.setattr("highcharts_builder.build_chart_png", _recorder)

    app.segmented_control[1].set_value("Static PNG").run()  # Render mode -> Static PNG

    assert not app.exception
    assert seen, "selecting Static PNG did not reach build_chart_png"
    missing = [name for name in _FORWARDED if name not in seen]
    assert not missing, (
        f"cached_chart_png did not forward {missing} to build_chart_png — the Static PNG "
        f"path would silently ignore those columns"
    )
    # The bytes reached the PAGE, not merely the wrapper's return. `st.image` decodes
    # through PIL, so a rendered `image` element is itself proof that valid image bytes
    # arrived — a truncated or corrupted payload raises "cannot identify image file" and
    # surfaces as `app.exception` above. (That is not hypothetical: this test was first
    # written with a `b"not-a-png"` stand-in and failed exactly that way, which is why
    # `_ONE_PIXEL_PNG` is a real PNG.) The caption alone would prove nothing — the Static
    # PNG branch emits it unconditionally, before and regardless of what st.image got.
    #
    # Byte-EQUALITY is deliberately NOT asserted: Streamlit serves both sinks as media
    # URLs whose hash is salted with filename and mimetype rather than being a digest of
    # the content, and `st.image` re-encodes to .jpg besides — so matching bytes would
    # mean reaching into private media-manager API for no guarantee this does not give.
    #
    # `app.image`, not `app.get("imgs")`: Streamlit 1.59.0 gave `st.image` a first-class
    # AppTest node (`testing.v1.element_tree.Image`, and the `.image` accessor with it),
    # and that node reports `type == "image"` where the untyped element it replaced
    # reported the PROTO field name, `imgs`. The proto still spells it `imgs` — only the
    # harness's name for it moved — so the old lookup did not raise on the 1.58 -> 1.62
    # bump, it silently returned an EMPTY list, and this assertion is what caught it. A
    # lookup keyed on element TYPE is the one thing this file's find-by-LABEL convention
    # cannot protect: a renamed label fails loudly at `.set_value`, a renamed type reads
    # as "the element is not there".
    assert len(app.image) == 1, "the PNG never reached st.image"
    downloads = app.get("download_button")
    assert len(downloads) == 1 and downloads[0].proto.url.endswith(".png"), (
        "the Static PNG branch did not offer its bytes as a .png download"
    )
    assert any("export server" in caption.value for caption in app.caption)


# --------------------------------------------------------------------------- #
# The DOCS' counts — the tallies that scale with chart types
# --------------------------------------------------------------------------- #
# CLAUDE.md and docs/chart-types.md are dense with numbers that are really facts about
# the CODE ("29 supported types", "Nine exist"), and a number in prose is the classic
# fact with no second home: nothing recomputes it, so adding a chart type silently
# falsifies it. That is not hypothetical here — "the four type-specific extra column
# selectors" sat in docs/chart-types.md while there were nine, and the same claim had
# drifted independently in this file's own AppTest preamble.
#
# The grep sweeps in CLAUDE.md's conventions cannot close this. They match uniqueness
# claims ("the one X") and ORDINALS ("the third"), and a bare cardinal is neither; a
# sweep widened to cardinals turns up ~59 hits across the docs and the source, almost
# all of them structurally fixed ("the two ends of a bar", "the three builders") — a
# signal rate too low to survive being run by hand on every added type.
#
# So the counts that scale get pinned mechanically instead, the same idea as
# test_theme_colors_stay_in_sync_with_config and test_packaging.py's README guards.
# Prose that does NOT scale keeps its numbers; prose that does should prefer a rule to a
# tally (both drifted sentences have been rewritten that way).
def _claude_md() -> str:
    return (ROOT / "CLAUDE.md").read_text()


def _chart_types_md() -> str:
    return (ROOT / "docs" / "chart-types.md").read_text()


_KWARG_TABLE_HEADER = "| Kwarg | Control label | Types |"


def _kwarg_table_names(text: str) -> set[str]:
    r"""The kwarg names in CLAUDE.md's extra-column table, and ONLY that table.

    Scoped to the table rather than run over the whole file. An unanchored
    ``^\| `([a-z_]+)` \|`` matches any row whose first cell is a backticked lowercase
    identifier, which today is only this table — the MARK_METRICS table one section down
    happens to lead with capitalised nouns. That is luck, not a guarantee: a future table
    keyed by helper, constant, or module name (all plausible in this doc) would have its
    rows read as kwargs and fail this test with "stale rows" pointing at rows that are
    neither stale nor kwargs.

    Asserting the header also keeps the slice honest — a renamed or moved table would
    otherwise yield an empty set, and an empty set is a vacuous pass waiting for the day
    `expected` is empty too.
    """
    assert _KWARG_TABLE_HEADER in text, (
        f"CLAUDE.md's kwarg table header {_KWARG_TABLE_HEADER!r} is gone — this test "
        f"can no longer find the table it pins"
    )
    # The table runs from its header to the first blank line (Markdown ends it there).
    table = text.split(_KWARG_TABLE_HEADER, 1)[1].split("\n\n", 1)[0]
    return set(re.findall(r"^\| `([a-z_]+)` \|", table, flags=re.MULTILINE))


def test_docs_state_the_real_number_of_supported_types():
    """Both docs open by counting the supported types; adding one falsifies both."""
    count = len(SUPPORTED_TYPES)
    assert f"{count} supported types" in _claude_md(), (
        f"CLAUDE.md's chart-types heading no longer says '{count} supported types' — "
        f"there are now {count}"
    )
    assert f"the {count} supported" in _chart_types_md(), (
        f"docs/chart-types.md's preamble no longer says 'the {count} supported' types"
    )


def test_claude_md_states_the_real_extra_column_kwarg_count():
    """CLAUDE.md's "9 extra column kwargs" is a claim about `_EXTRA_COLUMN_KWARGS`.

    The extra COLUMN kwargs are the forwarded set minus the gauge family's two that name
    a policy and a scale rather than a column — the same distinction the docstring of
    `_forwarded_arguments` draws, and the reason CLAUDE.md's two counts differ.

    A DIGIT, matching `test_docs_state_the_real_number_of_supported_types` above. CLAUDE.md
    used to spell this one as a word, which cost a 12-entry int-to-word map here purely to
    rebuild the substring — a second thing to keep in sync, capped at an arbitrary 12, in
    service of a number the code already has as an `int`. Spelling the count as a digit in
    the prose deleted the map and this test's whole lookup layer: a word is only harder to
    keep in sync than the number it spells.
    """
    count = len(_EXTRA_COLUMN_KWARGS)
    assert f"{count} extra column kwargs" in _claude_md(), (
        f"CLAUDE.md states a different number of extra column kwargs — there are now "
        f"{count}: {list(_EXTRA_COLUMN_KWARGS)}"
    )


def test_claude_md_kwarg_table_names_every_extra_column_kwarg():
    """The table is the count's real second home: it must list each kwarg BY NAME.

    Stronger than the count above, and the check that actually pays off — a tenth kwarg
    added to the builders without a table row is undocumented, and a row left behind for
    a kwarg that no longer exists is worse than no row. Pinning names rather than a
    length also means a rename cannot pass by keeping the total the same.
    """
    documented = _kwarg_table_names(_claude_md())
    expected = set(_EXTRA_COLUMN_KWARGS)
    assert documented == expected, (
        f"CLAUDE.md's kwarg table is out of sync with the builders — "
        f"undocumented: {sorted(expected - documented)}; "
        f"stale rows: {sorted(documented - expected)}"
    )


# The MARK_METRICS table was the last type-scaled tally in CLAUDE.md with no second home.
# The kwarg table above is pinned by name; this one was not, so a new entry in the app's
# dict could ship with the docs still describing the old set — the same class of drift as
# "the four extra column selectors", and the reason the sibling tests exist at all.
#
# Read STATICALLY, like the cache-layer tests and for the same reason: `import
# streamlit_app` executes the whole Streamlit script. `ast.literal_eval` is enough because
# the dict is a literal of literals, and it will raise rather than guess if that stops
# being true.
_MARK_METRICS_TABLE_HEADER = "| Noun | Types |"


def _app_mark_metrics() -> dict[str, str]:
    """`MARK_METRICS` as the app defines it, without executing the app."""
    tree = ast.parse((ROOT / "streamlit_app.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "MARK_METRICS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("streamlit_app.py no longer assigns MARK_METRICS")


def _mark_metrics_table(text: str) -> dict[str, str]:
    r"""CLAUDE.md's noun table, flattened back to the {type: noun} mapping it encodes.

    The table groups types that share a noun to stay readable — one row pairs N nouns
    (``a / b / c``) with N groups (``x, y · z · w``), positionally. Asserting the counts
    match per row is what stops a silently truncated row from parsing as a shorter,
    still-plausible mapping.
    """
    assert _MARK_METRICS_TABLE_HEADER in text, (
        f"CLAUDE.md's MARK_METRICS table header {_MARK_METRICS_TABLE_HEADER!r} is gone — "
        f"this test can no longer find the table it pins"
    )
    table = text.split(_MARK_METRICS_TABLE_HEADER, 1)[1].split("\n\n", 1)[0]
    mapping: dict[str, str] = {}
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or set(cells[0]) <= {"-"}:
            continue
        nouns = [n.strip() for n in cells[0].split("/")]
        groups = [g.strip() for g in cells[1].split("·")]
        assert len(nouns) == len(groups), (
            f"CLAUDE.md's MARK_METRICS row {line.strip()!r} pairs {len(nouns)} nouns "
            f"with {len(groups)} type groups — they are positional, so the counts must "
            f"match"
        )
        for noun, group in zip(nouns, groups, strict=True):
            for chart_type in group.split(","):
                mapping[chart_type.strip()] = noun
    return mapping


def test_claude_md_mark_metrics_table_matches_the_app():
    """The KPI's noun table is UI copy, and UI copy scales with chart types.

    Pinned by TYPE and by NOUN, not by length: a type moved from one noun to another
    keeps the total the same, and that is exactly the edit a reader of the docs would be
    misled by.
    """
    documented = _mark_metrics_table(_claude_md())
    expected = _app_mark_metrics()
    assert documented == expected, (
        f"CLAUDE.md's MARK_METRICS table is out of sync with streamlit_app.py — "
        f"missing: {sorted(set(expected) - set(documented))}; "
        f"stale: {sorted(set(documented) - set(expected))}; "
        f"wrong noun: "
        f"{sorted(k for k in set(documented) & set(expected) if documented[k] != expected[k])}"
    )
