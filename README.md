# Highcharts for Python Demos

Jupyter notebook demos for the [Highcharts for Python](https://github.com/highcharts-for-python) toolkit. Each `.ipynb` file is a self-contained example of a specific chart type.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
uv run jupyter lab
```

## Project Structure

Notebooks are organized by Highcharts product, then by chart category:

- `highcharts-core/` — line, area, column/bar, pie, heat/tree maps, trees/networks, other
- `highcharts-stock/` — candlestick, OHLC, HLC, heikin-ashi, and other financial charts
- `highcharts-gantt/` — Gantt/project timeline charts

## Dependencies

- `highcharts-core` — core Highcharts JS charting library
- `highcharts-stock` — Highcharts Stock (financial/time-series charts)
- `highcharts-gantt` — Highcharts Gantt (project timeline charts)
- `jupyterlab` — notebook runtime
- `requests` — HTTP client for fetching external data in some stock demos
