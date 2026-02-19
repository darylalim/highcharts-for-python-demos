# CLAUDE.md

## Project Overview

Jupyter notebook demos for the Highcharts for Python toolkit. Each `.ipynb` file is a self-contained example of a specific chart type.

## Architecture

Notebooks are organized by Highcharts product, then by chart category:

- `highcharts-core/` — line, area, column/bar, pie, heat/tree maps, trees/networks, other
- `highcharts-stock/` — candlestick, OHLC, HLC, heikin-ashi, and other financial charts
- `highcharts-gantt/` — Gantt/project timeline charts

### Notebook structure

Every notebook follows the same cell pattern — each step is an H2 markdown cell followed by a code cell:

1. `# <Chart Name>` — title and one-line description
2. `## Import Dependencies` — imports from the appropriate `highcharts_*` package
3. `## Retrieve Data` (optional) — fetches external data via `requests`
4. `## Prepare Data` (optional) — transforms fetched or inline data
5. `## Configure Options` — chart config as either:
   - `options_as_str` — JS literal string (many core demos)
   - `options_as_dict` — Python dict (some core demos, all stock and gantt demos)
6. `## Assemble Chart and Options` — creates the `Chart` object
7. `## Render Visualization` — calls `chart.display()`

Some notebooks add extra sections (e.g., `## Add Technical Indicators`, `## Add Series`) or combine assembly and render into `## Assemble and Display Chart`.

### API patterns

**highcharts-core** — imports from `highcharts_core.chart` and `highcharts_core.options`:

```python
options = HighchartsOptions.from_js_literal(options_as_str)  # or .from_dict(options_as_dict)
chart = Chart.from_options(options)
```

**highcharts-stock** — imports from `highcharts_stock.chart`; passes dict directly to `Chart.from_options()` without a `HighchartsOptions` intermediate:

```python
chart = Chart.from_options(options_as_dict)
chart.is_stock_chart = True  # only when stock chart mode is explicitly needed
```

**highcharts-gantt** — imports from `highcharts_gantt.chart`:

```python
chart = Chart.from_options(options_as_dict, chart_kwargs={'is_gantt_chart': True})
```

**Technical indicators** (stock only) — returns the updated chart:

```python
chart = chart.options.series[0].add_indicator(chart, 'macd', indicator_kwargs={'y_axis': 1})
```

**Data fetching** (stock only) — passes raw JSON string as the series `data` value:

```python
stock_response = requests.get('https://demo-live-data.highcharts.com/aapl-ohlcv.json')
stock_data = stock_response.text
```

## Conventions

- Follow the existing notebook cell structure and markdown heading pattern
- Place notebooks in the subfolder matching their Highcharts product and chart category
- Notebook filenames use lowercase kebab-case (e.g., `spline-with-plot-bands.ipynb`)
