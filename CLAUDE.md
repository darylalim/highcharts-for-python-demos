# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jupyter notebook demos for the Highcharts for Python toolkit. Each `.ipynb` file is a self-contained example of a specific chart type.

## Setup

```bash
uv sync
uv run jupyter lab
```

## Commands

These apply when Python source files (`.py`) are added to the project:

```bash
ruff check .    # lint
ruff format .   # format
ty check .      # type check
pytest          # run all tests
pytest tests/path/test_file.py::test_name  # run single test
```

## Code Style

These apply when Python source files (`.py`) are added to the project:

- `snake_case` for functions/variables, `PascalCase` for classes
- Type annotations on all parameters and returns
- isort with combine-as-imports (configured in `pyproject.toml`)
- Use dataclasses and abstract base classes

## Dependencies

- `highcharts-core` — Python wrapper for core Highcharts JS charting library
- `highcharts-stock` — Python wrapper for Highcharts Stock (financial/time-series charts)
- `highcharts-gantt` — Python wrapper for Highcharts Gantt (project timeline charts)
- `jupyterlab` — notebook runtime environment
- `requests` — HTTP client used by some stock demos to fetch external data

## Configuration

`pyproject.toml` is the central config file for:

- **Project metadata and dependencies** — `[project]` section (managed by `uv`)
- **Ruff** — `[tool.ruff]` for linting rules and `[tool.ruff.format]` for formatting
- **isort** — `[tool.ruff.lint.isort]` with `combine-as-imports = true`
- **pytest** — `[tool.pytest.ini_options]` for test configuration

## Architecture

Notebooks are organized by Highcharts product, then by chart category:

- `highcharts-core/` — line, area, column/bar, pie, heat/tree maps, trees/networks, other
- `highcharts-stock/` — candlestick, OHLC, HLC, and other financial charts
- `highcharts-gantt/` — Gantt/project timeline charts

### Notebook structure

Every notebook follows the same cell pattern:

1. **Title & description** — chart name and one-line summary
2. **Import Dependencies** — imports from the appropriate `highcharts_*` package
3. **Retrieve Data** (optional) — fetches external data via `requests` (some stock demos)
4. **Configure Options** — chart config as either:
   - `options_as_str`: JS literal string parsed via `HighchartsOptions.from_js_literal()` (most core demos)
   - `options_as_dict`: Python dict passed to `Chart.from_options()` (stock and gantt demos)
5. **Assemble Chart and Options** — creates the `Chart` object
6. **Render Visualization** — calls `chart.display()`

### Key API patterns

- **highcharts-core**: imports from `highcharts_core.chart`, `highcharts_core.options`
- **highcharts-stock**: imports from `highcharts_stock.chart`; set `chart.is_stock_chart = True`
- **highcharts-gantt**: imports from `highcharts_gantt.chart`; pass `chart_kwargs={'is_gantt_chart': True}` to `Chart.from_options()`
- **Technical indicators** (stock only): `series.add_indicator(chart, 'indicator_name', indicator_kwargs={...})`

## Conventions

- Follow the existing notebook cell structure and markdown heading pattern
- Place notebooks in the subfolder matching their Highcharts product and chart category
- Notebook filenames use lowercase kebab-case (e.g., `spline-with-plot-bands.ipynb`)
