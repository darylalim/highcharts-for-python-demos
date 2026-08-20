# Highcharts Studio

[![CI](https://github.com/darylalim/highcharts-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/darylalim/highcharts-studio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit 1.59+](https://img.shields.io/badge/streamlit-1.59%2B-ff4b4b.svg)](https://streamlit.io)

A [Streamlit](https://streamlit.io) application for building data visualizations
with [Highcharts](https://github.com/highcharts-for-python) — **every chart is
produced by `highcharts-core`** (the Highcharts for Python toolkit), with no
native Streamlit charts.

## Contents

[Setup](#setup) · [Run](#run) · [Features](#features) ·
[Chart types](#chart-types) · [Development](#development) · [Notes](#notes) ·
[License](#license)

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

## Run

```bash
uv run streamlit run streamlit_app.py
```

Then open <http://localhost:8501>. Pick a sample dataset (or upload a CSV),
choose a chart type and map its columns, and switch between two render modes:
interactive (CDN iframe) or a static PNG. Charts follow the app's light/dark
theme, which you can toggle from Streamlit's settings menu.

## Features

- **Data in** — built-in sample datasets or your own CSV upload. Map columns to
  the chart with compact pills, falling back to `st.multiselect` on wide CSVs.
- **Two render modes** — *Interactive* runs Highcharts JS from the CDN, embedded
  via `st.iframe`; *Static (PNG)* renders server-side through the Highcharts
  export server and shows the image with a download button.
- **Theme-aware** — charts flip their background, text, axes, and tooltip to match
  the light/dark theme in both render modes, while each series keeps its palette
  color. Follows your OS by default.
- **KPI row** — rows, numeric columns, and a chart-type-adaptive third metric
  (series plotted, or the mark count: cells, tiles, stages, flows, links, boxes,
  steps, sectors, bars, or ranges).
- **See the config** — a toggle reveals the generated Highcharts config
  (`to_js_literal()` output).
- **Consistent palette** — every series uses the brand palette (`DEFAULT_COLORS`),
  kept in sync with the Streamlit theme in `.streamlit/config.toml`.

## Chart types

| Type | What it shows | Extra input |
| --- | --- | --- |
| `line`, `spline`, `area`, `areaspline`, `column`, `bar` | One or more Y series over a category X | — |
| `pie` | Each label's share of a single value column | — |
| `scatter` | Y vs. X as points | — |
| `bubble` | Scatter plus a third dimension sizing each marker | Size (Z) |
| `radar` | A polar spider/web line over a category axis | — |
| `heatmap` | A category × category grid, cells colored by value | — |
| `treemap` | Nested rectangles sized by a value column | — |
| `funnel` | Part-of-whole stages, sized top-to-bottom (a narrowing funnel) | — |
| `pyramid` | Funnel's inverted mirror: stages widening top-to-bottom | — |
| `sankey` | A flow diagram: each row links two node columns, weighted by a value | Target |
| `dependencywheel` | A circular sankey: the same weighted links drawn as nodes on a ring | Target |
| `networkgraph` | A force-directed graph of unweighted edges between two node columns | Target (no Y) |
| `organization` | A top-down org chart: titled boxes linked employee→manager | Manager, Title (no Y) |
| `boxplot` | Per-category Tukey distributions from repeated observations | — |
| `waterfall` | A cumulative bridge of signed deltas, with a closing Total bar | — |
| `sunburst` | A hierarchy as concentric rings from a parent column and leaf values | Parent |
| `xrange` | A Gantt-style timeline; bars span Start→End on named lanes (dates or numbers) | End |
| `columnrange` | Floating bars, each spanning a Low→High per category (a min–max range) | High |
| `arearange` | A continuous filled band spanning a Low→High per category (columnrange's area mirror) | High |
| `bullet` | A KPI strip: a Measure bar read against a Goal crossbar, one pair per category | Goal |
| `variwide` | Columns whose Width is a second magnitude, so each bar's *area* is the reading | Width |
| `dumbbell` | Two markers per category joined by a connector: a Before and an After | After |
| `solidgauge` | An activity gauge: each column reduced to one reading, drawn as an arc | Aggregation, Dial (no X) |
| `gauge` | A needle per column on a drawn tick scale | Aggregation, Dial (no X) |

The gauge family (`solidgauge`, `gauge`) is the only pair with no label column —
each *selected* column becomes one mark, reduced to a single reading by the
aggregation you pick (sum / mean / median / min / max / last). `networkgraph` is
its mirror: edges with no value column. See
[`docs/chart-types.md`](docs/chart-types.md) for the per-chart design notes.

## Development

The core chart logic lives in `highcharts_builder.py` — pure, Streamlit-free
functions (DataFrame → Highcharts options → `Chart` → HTML/PNG) that are
independently unit-testable. `streamlit_app.py` is the UI and `sample_data.py`
the built-in datasets. See [`CLAUDE.md`](CLAUDE.md) for the architecture and the
project conventions, and [`docs/chart-types.md`](docs/chart-types.md) for the
per-type design record.

```bash
uv run pytest                                       # tests
uv run ruff check --fix . && uv run ruff format .   # lint + format
uv run ty check                                     # type check
```

GitHub Actions runs all three on every push to `main` and every pull request
(`.github/workflows/ci.yml`). Committed
[Claude Code](https://claude.com/claude-code) hooks in `.claude/` mirror those
gates locally so edits stay green before a push (see `CLAUDE.md`).

## Notes

- There is **no official Streamlit ↔ Highcharts component** for the
  `highcharts-core` object model, so interactive mode uses a dependency-free
  `Chart` → HTML → `st.iframe` bridge.
- **Interactive** mode loads Highcharts JS from the CDN
  (`https://code.highcharts.com/`), so the browser needs network access; the
  iframe has a fixed height (it does not auto-grow).
- **Static** mode needs the running process to reach the Highcharts export server
  (`export.highcharts.com` by default). Self-host one and pass `server_instance`
  to `download_chart` to remove that external dependency.

## License

This project's own source code (the Streamlit app and its helpers) is released
under the [MIT License](LICENSE) — you're free to use, modify, and distribute
it.

The MIT license covers **only this project's code**, not the third-party tools
it renders with. Two of its dependencies are proprietary and separately
licensed, and the MIT grant does not extend to them:

- **Highcharts JS** (loaded from the CDN) and the **Highcharts export server**
  are owned by Highsoft — free for personal/non-commercial use; commercial use
  requires a paid Highcharts license.
- **`highcharts-core`** (the Highcharts for Python toolkit) is itself
  proprietary, governed by the Highcharts for Python Toolkit License (which
  presupposes a Highcharts Software license — paid for commercial use, or a
  Personal/Educational license otherwise).

If you fork or deploy this, obtaining the required Highcharts and
Highcharts-for-Python licenses for your usage is your responsibility. Streamlit
(Apache-2.0) and pandas (BSD-3-Clause) are permissively licensed. See the
[`LICENSE`](LICENSE) file for the full MIT text and [`NOTICE`](NOTICE) for the
third-party notice.
