"""Built-in sample datasets so the app works with no upload.

Pure pandas — no Streamlit — so it stays independently importable and testable,
like ``highcharts_builder``. Each factory returns a fresh DataFrame.
"""

from __future__ import annotations

import pandas as pd


def _revenue_vs_cost() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "revenue": [120, 135, 128, 150, 162, 171],
            "cost": [80, 88, 90, 95, 101, 108],
        }
    )


def _fruit_sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fruit": ["Apples", "Bananas", "Cherries", "Grapes", "Oranges"],
            "units_sold": [620, 540, 210, 380, 470],
        }
    )


def _height_vs_weight() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "height_cm": [152, 158, 161, 165, 168, 172, 175, 180, 185, 190],
            "weight_kg": [50, 55, 58, 61, 65, 70, 74, 80, 86, 94],
        }
    )


def _daily_temperature() -> pd.DataFrame:
    """Hourly temperature across one day — a smooth rise to an afternoon peak and
    back down overnight. Tailored to areaspline: the rounded rise-then-fall puts a
    curved peak where a straight-segment ``area`` chart would show a sharp elbow,
    so the spline smoothing actually shows."""
    return pd.DataFrame(
        {
            "hour": [f"{h:02d}:00" for h in range(24)],
            "temp_c": [
                12,
                11,
                11,
                10,
                10,
                11,
                12,
                14,
                16,
                18,
                20,
                22,
                23,
                24,
                24,
                23,
                21,
                19,
                17,
                16,
                15,
                14,
                13,
                12,
            ],
        }
    )


def _country_economics() -> pd.DataFrame:
    """GDP per capita vs life expectancy, sized by population — the classic
    Gapminder-style bubble where the marker area carries a third dimension.
    Tailored to bubble: a numeric GDP (X) and life-expectancy (Y) pair plus a
    population column whose wide range (tens to ~1,400 millions) makes the size
    encoding legible."""
    return pd.DataFrame(
        {
            "country": [
                "USA",
                "China",
                "India",
                "Germany",
                "Brazil",
                "Nigeria",
                "Japan",
                "Indonesia",
            ],
            "gdp_per_capita_k": [76.0, 12.6, 2.5, 52.7, 8.9, 2.1, 33.8, 4.8],
            "life_expectancy": [77.5, 78.2, 70.1, 81.2, 73.4, 52.7, 84.0, 71.7],
            "population_m": [335, 1412, 1428, 84, 216, 224, 125, 278],
        }
    )


def _product_ratings() -> pd.DataFrame:
    """Two competing products scored 0–10 across the same attributes — the
    natural radar (spider) chart, where each product is one closed polygon over
    the shared axes and the comparison is the difference in their shapes.
    Tailored to radar: a category axis (attribute) plus two numeric series whose
    values share a common 0–10 range, so the overlaid webs are directly
    comparable (and neither dominates the auto-scaled radial axis)."""
    return pd.DataFrame(
        {
            "attribute": [
                "Design",
                "Performance",
                "Battery",
                "Camera",
                "Price",
                "Support",
            ],
            "Aurora": [9, 7, 6, 8, 5, 7],
            "Zephyr": [6, 9, 8, 5, 8, 6],
        }
    )


def _weekly_activity() -> pd.DataFrame:
    """Website visits by weekday × time-of-day block — the activity matrix a
    heatmap is built for: each (weekday, block) cell's color shows how busy that
    slot is, so the weekday midday peak and the weekend evening shift read at a
    glance. Tailored to the wide-form heatmap: a category column (weekday) plus
    four numeric columns (the time blocks) whose values share one intensity scale,
    so the color axis is directly comparable across every cell."""
    return pd.DataFrame(
        {
            "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "Night": [12, 10, 11, 13, 18, 26, 22],
            "Morning": [48, 52, 50, 55, 60, 34, 28],
            "Afternoon": [66, 70, 72, 74, 80, 46, 41],
            "Evening": [40, 42, 45, 47, 68, 78, 64],
        }
    )


def _company_market_cap() -> pd.DataFrame:
    """Market capitalization of the largest tech companies — the part-of-whole a
    treemap is built for: each tile's area shows one company's share, and the
    ~10-way split stays readable where a 10-slice pie would be a cluttered ring.
    Tailored to treemap: a single label column (company) + one numeric value
    column (market_cap_b) whose wide range makes the nested-rectangle sizing
    legible."""
    return pd.DataFrame(
        {
            "company": [
                "Apple",
                "Microsoft",
                "Nvidia",
                "Alphabet",
                "Amazon",
                "Meta",
                "TSMC",
                "Broadcom",
                "Tesla",
                "Netflix",
            ],
            "market_cap_b": [3400, 3100, 2900, 2100, 1900, 1300, 950, 780, 720, 380],
        }
    )


def _conversion_funnel() -> pd.DataFrame:
    """A marketing conversion funnel — the part-of-whole *stages* a funnel is built for: each
    band is one step of a purchase journey, sized by how many people reach it, and the strict
    top-to-bottom narrowing IS the story (where a pie would only show each step's share of the
    sum). Tailored to funnel: a single stage-label column (stage) leading the frame — so the app
    opens cleanly on ``line`` with a category X — plus one numeric value column (visitors) whose
    values *decrease* down the funnel. The clean monotone sequence is the demo's job; a missing or
    out-of-order stage is the tests'."""
    return pd.DataFrame(
        {
            "stage": [
                "Visitors",
                "Product views",
                "Added to cart",
                "Checkout started",
                "Purchased",
            ],
            "visitors": [48000, 21500, 9200, 4100, 1600],
        }
    )


def _loyalty_pyramid() -> pd.DataFrame:
    """A customer-loyalty pyramid — funnel's inverted mirror, drawn as pyramid's own series type.
    Like a funnel it leads with its LARGEST stage, but where a funnel puts that stage at the top
    and narrows downward, a Highcharts pyramid draws the first row at the BASE and narrows UPWARD
    to an apex (verified by rendering) — the classic broad-based loyalty pyramid. Tailored to
    pyramid exactly as the funnel sample is to funnel: a stage-label column (tier) first, one
    numeric value column (people) *decreasing* from the broad Audience base to the Advocates apex.
    Reading the two side by side is the fastest way to see the only difference is which way the
    shape points, not the data."""
    return pd.DataFrame(
        {
            "tier": [
                "Audience",
                "Leads",
                "Customers",
                "Repeat buyers",
                "Advocates",
            ],
            "people": [25000, 8000, 3200, 900, 250],
        }
    )


def _energy_flow() -> pd.DataFrame:
    """Primary energy sources feeding electricity generation, which then splits to
    end-use sectors — the multi-level flow a sankey is built for: each link's width
    shows how much energy moves from one stage to the next, and the two hops
    (fuel → Electricity → sector) trace the whole system in one diagram.
    Tailored to sankey: a source and a target column of node *labels* plus a numeric
    weight, balanced so the 150 units generated are the 150 consumed. Unlike every
    other sample — each of which has one row per unique x value — the source labels
    REPEAT, and ``Electricity`` is both a target and a source. That is the from/to
    link shape sankey reads, and it is what makes the second hop appear."""
    return pd.DataFrame(
        {
            "source": [
                "Coal",
                "Natural Gas",
                "Nuclear",
                "Solar",
                "Wind",
                "Hydro",
                "Electricity",
                "Electricity",
                "Electricity",
            ],
            "target": [
                "Electricity",
                "Electricity",
                "Electricity",
                "Electricity",
                "Electricity",
                "Electricity",
                "Residential",
                "Industry",
                "Commercial",
            ],
            "terawatt_hours": [42, 38, 20, 14, 26, 10, 60, 55, 35],
        }
    )


def _regional_migration() -> pd.DataFrame:
    """Population moving between regions over a year — the who-flows-to-whom a dependencywheel is
    built for: nodes sit on a ring and each curved ribbon's width shows how many people moved from
    one region to another, so the whole migration matrix reads in one circle.

    Tailored to dependencywheel, and the deliberate MIRROR of the sankey energy sample above. Both
    read the same {from, to, weight} link shape, but the SHAPE OF THE DATA is opposite, which is the
    whole point of reading them side by side: the energy sample is a layered DAG — fuel flows one
    way into ``Electricity`` and on to a sector, and the source set and the target set barely
    overlap, so it draws cleanly as a left-to-right flow. Here EVERY region is BOTH an origin and a
    destination (North sends to South and East, and receives from South, East and Central), so the
    flow is a symmetric, cyclic matrix with no layers — exactly the graph a straight sankey draws as
    a tangle of back-crossing links and a ring draws as a clean wheel. Ten links, well under the
    label gate, so each ribbon carries its own count.

    Leads with a *label* column (``origin``) — load-bearingly so, like every sample: the app opens
    on ``line`` with the first column as X, and a numeric first column would trip the x-in-y guard
    the moment the dataset is selected. ``people`` is the numeric weight the wheel sizes ribbons by,
    which also gives the app's no-numeric-columns gate something to find."""
    return pd.DataFrame(
        {
            "origin": [
                "North",
                "North",
                "South",
                "South",
                "East",
                "East",
                "West",
                "West",
                "Central",
                "Central",
            ],
            "destination": [
                "South",
                "East",
                "North",
                "Central",
                "West",
                "North",
                "Central",
                "South",
                "North",
                "East",
            ],
            "people": [1200, 800, 950, 700, 600, 450, 500, 400, 650, 550],
        }
    )


def _service_dependencies() -> pd.DataFrame:
    """A microservice call graph — the who-connects-to-whom a networkgraph is built for: each row
    is one dependency edge, and the force layout pulls tightly-coupled services together so the
    clusters (an ``Orders`` hub, an ``Auth`` shared by several callers) fall out of the physics.

    Tailored to networkgraph, and the deliberate MIRROR of the sankey sample above: two columns of
    node *labels* and NO weight, because a networkgraph edge is unweighted. Like sankey the source
    labels REPEAT and many nodes are BOTH a source and a target (``API Gateway`` calls Auth and is
    itself called by Web and Mobile; ``Orders`` sits mid-graph) — which is what makes this a
    connected network rather than a star. Unlike sankey it also contains a CYCLE (``Catalog`` ⇄
    ``Search`` call each other), which a networkgraph draws without complaint where the sunburst
    sample's *tree* could not — the one graph shape no hierarchy can hold.

    The first column is the source, a *label*, so — like every sample and load-bearingly so — the
    app can open it on ``line`` without a numeric first column tripping the x-in-y guard. The
    networkgraph itself reads only the two label columns (an edge is unweighted), but ``calls_per_min``
    is a genuine numeric column carried for the same reason ``_release_plan``'s ``headcount`` is: so
    the dataset stays usable by the value-based types and the app's no-numeric-columns gate has
    something to find. It is per-EDGE traffic, so networkgraph ignores it rather than sizing anything
    by it — the honest place for a magnitude a graph cannot draw."""
    return pd.DataFrame(
        {
            "service": [
                "Web",
                "Mobile",
                "API Gateway",
                "API Gateway",
                "API Gateway",
                "Orders",
                "Orders",
                "Orders",
                "Payments",
                "Inventory",
                "Catalog",
                "Search",
                "Auth",
            ],
            "depends_on": [
                "API Gateway",
                "API Gateway",
                "Auth",
                "Orders",
                "Catalog",
                "Payments",
                "Inventory",
                "Auth",
                "Ledger",
                "Warehouse",
                "Search",
                "Catalog",
                "Sessions",
            ],
            "calls_per_min": [
                1200,
                800,
                1500,
                600,
                900,
                300,
                450,
                600,
                300,
                200,
                700,
                650,
                2100,
            ],
        }
    )


def _response_times() -> pd.DataFrame:
    """Per-service API response times in milliseconds — the per-category *distribution*
    a boxplot is built for: each service's spread of raw observations becomes one box,
    so the reader sees center AND spread at once, and a genuine tail latency reads as an
    outlier dot instead of quietly dragging a mean upward. Tailored to the long/tidy
    boxplot shape, the only one in this file: a category column (``service``) whose
    values REPEAT — one row per observation, ~15 per service — plus one numeric column
    of raw measurements (``response_ms``). ``search`` is right-skewed around a single
    890 ms tail spike, the lone Tukey outlier across the whole frame, so the linked
    outlier series has exactly one point to draw. The boxes appear in first-appearance
    order (auth, search, checkout, profile), which is also roughly increasing latency.
    """
    services = ["auth"] * 15 + ["search"] * 15 + ["checkout"] * 15 + ["profile"] * 15
    response_ms = [
        # auth — fast and tight
        42, 45, 38, 51, 47, 55, 44, 49, 60, 41, 48, 52, 46, 58, 50,
        # search — right-skewed, with the one 890 ms spike that becomes the outlier
        88, 95, 102, 91, 110, 85, 120, 99, 105, 890, 93, 108, 97, 115, 101,
        # checkout — slower and wider, but no tail
        150, 165, 148, 172, 159, 180, 155, 168, 175, 161, 152, 170, 158, 166, 163,
        # profile — slowest, and the widest box
        210, 225, 198, 240, 215, 230, 205, 220, 235, 212, 208, 228, 218, 222, 216,
    ]  # fmt: skip
    return pd.DataFrame({"service": services, "response_ms": response_ms})


def _profit_bridge() -> pd.DataFrame:
    """A quarterly profit bridge — how gross revenue BECOMES net profit, one signed step
    at a time. Tailored to the waterfall shape, the only one in this file whose numeric
    column holds *deltas* rather than levels: every other dataset's values stand on their
    own, while these only mean anything cumulatively, each starting where the last ended.

    The steps mix signs (the point of the type — a same-signed column would just be a
    column chart drawn oddly) and are ordered as a P&L reads: an opening revenue figure,
    then the costs that eat into it, then the one mid-sequence *rise* (``Other income``)
    that proves the up/down coloring is driven by each value's sign rather than by
    position. No total row: the builder appends the closing ``Total`` bar itself, summing
    these to 79.
    """
    return pd.DataFrame(
        {
            "step": [
                "Gross revenue",
                "COGS",
                "Salaries",
                "Marketing",
                "Other income",
                "Tax",
            ],
            "delta": [420.0, -155.0, -120.0, -64.0, 38.0, -40.0],
        }
    )


def _org_headcount() -> pd.DataFrame:
    """Company headcount as an ADJACENCY LIST — one row per node, each naming its parent.

    Tailored to sunburst, and to nothing else in this file, on four counts:

    * It is the only sample whose rows are a HIERARCHY. Sankey's ``_energy_flow`` is the near
      miss worth naming: its rows are edges of a *graph*, and ``Electricity`` is both a source
      and a target — which no tree can be. Here every node has exactly one parent.
    * It is the only sample whose value column is deliberately BLANK on some rows. Everywhere
      else a blank means missing data; here it means *"ask my children"*. Engineering's 80 is
      nowhere in this frame — it is 80 *because its teams are*, and the chart is what does that
      addition. The centre reads a total the builder never computed.
    * Three levels of nesting (division → group → team) plus the synthesized root make FOUR
      rings, which is what makes the colour *inheritance* and the *alternating* sign of the
      ``colorVariation`` visible at all. A two-level tree would show neither.
    * ``Other`` appears TWICE, under two different divisions — the exact case a label-keyed
      node identity would silently MERGE into one 9-person sector under whichever parent won
      (and which Highcharts itself rejects outright, as error #31, "Non-unique point or node
      id"). Nothing *names* ``Other`` as a parent, so the ambiguity never arises and the two
      stay honest 5- and 4-person leaves. It is the sample's whole argument for synthesized
      ids.

    The blank ``reports_to`` cells are the three top-level branches. Headcount sums to 143
    (Engineering 80, Sales 39, Marketing 24).
    """
    return pd.DataFrame(
        {
            "team": [
                "Engineering",  # the three top-level branches (blank parent)
                "Sales",
                "Marketing",
                "Platform",  # under Engineering
                "Product",
                "Backend",  # under Platform
                "Infrastructure",
                "Mobile",  # under Product
                "Web",
                "Enterprise",  # under Sales
                "SMB",
                "Other",
                "Brand",  # under Marketing
                "Growth",
                "Other",  # ...the second one: a different team, the same name
            ],
            "reports_to": [
                None,
                None,
                None,
                "Engineering",
                "Engineering",
                "Platform",
                "Platform",
                "Product",
                "Product",
                "Sales",
                "Sales",
                "Sales",
                "Marketing",
                "Marketing",
                "Marketing",
            ],
            "headcount": [
                # The five internal nodes state no headcount: Highcharts sums it from the
                # leaves below them. Only the ten leaf teams carry a number.
                None,
                None,
                None,
                None,
                None,
                24.0,
                16.0,
                18.0,
                22.0,
                20.0,
                14.0,
                5.0,
                9.0,
                11.0,
                4.0,
            ],
        }
    )


def _release_plan() -> pd.DataFrame:
    """A product release plan as INTERVALS — one row per scheduled bar, each on a workstream
    lane, spanning a start date and an end date.

    Tailored to xrange, and to nothing else in this file, on four counts:

    * Its value columns are COORDINATES rather than magnitudes — where most datasets here
      answer "how much", these two answer "when". It shares that with exactly one other sample,
      and the pair is a deliberate mirror: ``_company_milestones`` carries ONE date per row and
      means an INSTANT, these two carry a pair and mean an INTERVAL. (This note read "the only
      sample" until that mirror arrived.) The dates are written as ISO-8601 *strings* on
      purpose: that is what
      ``pd.read_csv`` hands back for a date column, so the sample exercises the real
      ``_coordinates`` sniff (an object column parsed to a datetime axis) rather than a
      pre-parsed ``datetime64`` a CSV upload would never produce.
    * Its label column REPEATS, like ``_response_times``' does — but for a different reason.
      A boxplot's repeats are observations to be aggregated into one box; here each repeat is
      its own bar, so ``Backend`` and ``Frontend`` each run twice with a GAP between them
      (build, then a later hardening pass). That is what proves the per-lane hue: a lane's two
      bars must come back the same color, or a workstream stops reading as one thing.
    * ``Launch`` is a zero-length row — a MILESTONE, the commonest Gantt row after a task, and
      the one Highcharts draws nothing for unaided. It is here so the sample renders the
      ``minPointLength`` floor rather than leaving it to a test.
    * ``headcount`` is a genuine numeric column, so the dataset is still usable by the other
      chart types (and so the app's no-numeric-columns gate has something to find).
    """
    return pd.DataFrame(
        {
            "workstream": [
                "Discovery",
                "Design",
                "Backend",
                "Frontend",
                "Backend",
                "Frontend",
                "QA",
                "Launch",
            ],
            "start": [
                "2026-01-05",
                "2026-01-26",
                "2026-02-16",
                "2026-03-02",
                "2026-04-27",  # the second Backend bar, after a gap
                "2026-05-04",  # the second Frontend bar, after a gap
                "2026-05-11",
                "2026-06-01",  # the milestone: start == end
            ],
            "end": [
                "2026-01-23",
                "2026-02-20",
                "2026-04-17",
                "2026-04-24",
                "2026-05-08",
                "2026-05-15",
                "2026-05-29",
                "2026-06-01",
            ],
            "headcount": [2, 3, 5, 4, 2, 2, 3, 1],
        }
    )


def _temperature_range() -> pd.DataFrame:
    """A city's monthly record temperatures as RANGES — one row per month, each a record low
    and a record high in °C.

    Tailored to columnrange, and it is the mirror of ``_release_plan`` on the one axis that
    matters: its two value columns are a LOW and a HIGH of the SAME quantity (°C), so they are
    MAGNITUDES, not xrange's coordinates — they answer "how much", never "when", and can never be
    dates. That is the whole difference the type turns on, and reading this sample beside the
    release plan is the fastest way to see it: both draw a bar from a low to a high, but one bar
    spans a temperature and the other a calendar.

    ``record_low`` leads with the category column (``month``) rather than a value, like every
    sample here and for the same load-bearing reason: the app opens on ``line`` with the first
    column as X, so a numeric first column would trip the x-in-y guard the instant the dataset is
    selected. Both value columns are genuine numbers, so the dataset stays usable by the other
    chart types (and the no-numeric-columns gate has something to find). Every ``low`` sits below
    its ``high`` — a clean, honest range — because the type's headline is "a min–max per category"
    and this sample is meant to SHOW that; the missing-slot and inverted-range edge cases are the
    tests' job, not a demo dataset's. One measurement drawn in one hue: a columnrange does not
    colour its bars by category, since the months are positions on an axis, not separate kinds.
    """
    return pd.DataFrame(
        {
            "month": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
            "record_low": [-8, -6, -2, 2, 7, 11, 14, 13, 9, 3, -3, -7],
            "record_high": [14, 16, 22, 27, 31, 34, 37, 36, 32, 26, 19, 15],
        }
    )


def _forecast_range() -> pd.DataFrame:
    """A product's projected monthly active users as a low/high FORECAST BAND — one row per month,
    each a low and a high estimate (thousands of MAU).

    Tailored to arearange, and deliberately NOT another temperature range: it is the mirror of
    ``_temperature_range`` on the axis that matters, which is not the data shape (both are a low and
    a high per category) but the USE. A record-temperature range is a set of INDEPENDENT monthly
    facts, so columnrange draws it as separate bars. A forecast is a CONTINUOUS estimate that
    tightens or widens as it runs, so its natural shape is a band you read for its OUTLINE — the
    uncertainty cone — which is exactly what an arearange draws and what a row of discrete bars
    cannot show. Reading this sample beside the temperature range is the fastest way to see the
    columnrange/arearange split: same two magnitude columns, but one is a set of bars and the other
    a shape over time.

    The band WIDENS month over month (``low`` climbs slowly while ``high`` climbs faster), because
    the point of the type is the outline and the point of a forecast is that it grows less certain
    the further out it runs — so the sample is built to SHOW the cone opening. Every ``low`` sits
    below its ``high`` (a clean band), like the temperature sample and for the same reason: the
    headline is "a continuous min–max band" and the demo is meant to draw it cleanly; the
    missing-slot (band break) and inverted-range edge cases are the tests' job, not a demo's.

    ``month`` leads with the category column rather than a value, like every sample here and for the
    same load-bearing reason: the app opens on ``line`` with the first column as X, so a numeric
    first column would trip the x-in-y guard the instant the dataset is selected. Both value columns
    are genuine numbers, so the frame stays a good citizen for line/area/column and the no-numeric
    gate has something to find. One estimate drawn in one hue: an arearange does not colour its band
    by month, since the months are positions along the band, not separate kinds.
    """
    return pd.DataFrame(
        {
            "month": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
            # thousands of MAU: low climbs slowly, high faster, so the cone opens over the year.
            "forecast_low": [
                120,
                128,
                137,
                145,
                154,
                162,
                171,
                180,
                188,
                197,
                205,
                214,
            ],
            "forecast_high": [
                130,
                142,
                155,
                168,
                182,
                196,
                212,
                228,
                244,
                262,
                280,
                300,
            ],
        }
    )


def _sales_vs_quota() -> pd.DataFrame:
    """A sales team's quarterly result against its quota — one row per REGION, each an actual and
    a target (thousands of USD).

    Tailored to bullet, and deliberately the mirror of ``_temperature_range``, which is the sample
    it looks most like and means least like. Both lead with a category column and carry two
    magnitude columns of one unit, and both draw one mark per category — but a record-temperature
    range's two numbers are the two ENDS OF ONE BAR (neither means anything alone; the bar IS the
    span between them), while these two are INDEPENDENT CLAIMS about the same region: what
    happened, and what was meant to happen. So the temperature sample draws N floating bars and
    this one draws N bars from zero, each crossed by a reference line — and reading the two side by
    side is the fastest way to see that "two magnitude columns" is a data SHAPE, not a chart.

    The regions deliberately BEAT, MISS and exactly MATCH their quotas, and the beats are the
    load-bearing part rather than the flattering one: an unstyled bullet's crossbar takes the
    series hue and is drawn WIDER than the bar, so on precisely the rows where the measure exceeds
    the goal it collapses into the fill and survives as two meaningless stubs (the trap the
    builder's ``targetOptions.color`` exists to close). Shipping a sample where every region missed
    would hide the one failure a reader could not diagnose. ``North`` matching its quota exactly is
    the honest-looking edge that a per-ROW equality is fine, unlike the per-COLUMN one the app
    guards against.

    Every value is present: the missing-goal, missing-measure and missing-both cases are the tests'
    job, not a demo's — the ``_temperature_range``/``_forecast_range`` rule. ``region`` leads with
    the category column rather than a value, like every sample here and for the same load-bearing
    reason: the app opens on ``line`` with the first column as X, so a numeric first column would
    trip the x-in-y guard the instant the dataset is selected. ``deals_closed`` is a throwaway
    numeric column the chart never reads, carried for the reason ``_reporting_lines``'s
    ``tenure_years`` and ``_service_dependencies``'s ``calls_per_min`` are — and here it earns a
    second keep: the app's Goal picker defaults to the SECOND numeric column, so this one sits
    below ``quota`` rather than competing with it.
    """
    return pd.DataFrame(
        {
            "region": ["North", "South", "East", "West", "Central", "Nordics"],
            # thousands of USD. North matches its quota exactly; South, West and Nordics beat
            # theirs (the crossbar-contrast case); East and Central fall short.
            "actual": [420, 512, 331, 604, 278, 466],
            "quota": [420, 450, 400, 550, 350, 430],
            "deals_closed": [38, 51, 29, 62, 24, 44],
        }
    )


def _product_line_margin() -> pd.DataFrame:
    """Gross margin per product line, each weighted by the revenue it earns it.

    Tailored to variwide, and the THIRD sample in this file built on "a category plus two
    magnitude columns" — which is the point of it. Read all three side by side and the shape stops
    looking like a chart type:

    * ``_temperature_range`` (columnrange): the two numbers are the two ENDS OF ONE BAR. Neither
      means anything alone; the bar IS the span between them.
    * ``_sales_vs_quota`` (bullet): two INDEPENDENT CLAIMS about one region, on the same channel —
      what happened and what was meant to.
    * this one (variwide): ONE claim spread over TWO GEOMETRIC CHANNELS. The margin is the bar's
      HEIGHT, the revenue is its WIDTH, and the reading is neither number but their PRODUCT — the
      AREA, which is the gross profit the line actually contributes.

    That last reading is what the data is arranged to force, and it is why the two columns
    deliberately ANTI-correlate. ``Analytics`` has the best margin in the table and the smallest
    revenue; ``Services`` has the worst margin and nearly four times the revenue. A tall thin bar
    beside a short wide one is the whole lesson: the highest-margin line is not the biggest
    contributor, and no ordinary column chart of either column alone can say so. Had margin simply
    risen with revenue the chart would draw as a staircase, every bar's area ranked the same way
    its height was, and a reader would never learn that the width was carrying information.

    The revenues span roughly 3x (21 to 76) so the width channel is unmistakable at a glance — a
    range too narrow reads as a rendering artefact rather than as data. Every value is present and
    every width is positive: the missing-width, zero-width and NEGATIVE-width cases are the tests'
    job, not a demo's (the ``_temperature_range``/``_forecast_range``/``_sales_vs_quota`` rule),
    and the negative one especially, since it does not merely fail to draw itself — it shrinks the
    total every OTHER bar's width is a share of.

    ``product_line`` leads with the category column, like every sample here and for the same
    load-bearing reason: the app opens on ``line`` with the first column as X, so a numeric first
    column would trip the x-in-y guard the instant the dataset is selected. ``sku_count`` is a
    throwaway numeric column the chart never reads, carried for ``_reporting_lines``'s
    ``tenure_years`` reason — and, like ``_sales_vs_quota``'s ``deals_closed``, it earns a second
    keep by its POSITION: the app's Width picker defaults to the SECOND numeric column, so
    ``revenue_musd`` must sit directly below ``margin_pct`` and this one below both, or the control
    lands on the wrong column and the sample no longer demonstrates the type on landing.
    """
    return pd.DataFrame(
        {
            "product_line": [
                "Analytics",
                "Platform",
                "Services",
                "Hardware",
                "Support",
            ],
            # Percent. Deliberately ANTI-correlated with revenue: the best margin belongs to the
            # smallest line, so the tallest bar is the narrowest and area != height.
            "margin_pct": [62, 41, 22, 34, 48],
            # Millions of USD — the WIDTH channel. ~3x spread so the varying width is obvious.
            "revenue_musd": [21, 58, 76, 30, 24],
            "sku_count": [12, 34, 8, 51, 19],
        }
    )


def _market_share_shift() -> pd.DataFrame:
    """Market share by region at the start and the end of the year.

    Tailored to dumbbell, and the FOURTH sample in this file built on "a category plus two
    magnitude columns" — which, as with the third, is the point of it. Read all four side by side
    and the shape stops looking like a chart type at all:

    * ``_temperature_range`` (columnrange): the two numbers are the two ENDS OF ONE BAR. Neither
      means anything alone; the bar IS the span between them.
    * ``_sales_vs_quota`` (bullet): two INDEPENDENT CLAIMS about one region, on the same channel —
      what happened and what was meant to.
    * ``_product_line_margin`` (variwide): ONE claim over TWO GEOMETRIC CHANNELS, a height and a
      width, whose reading is their PRODUCT — the area.
    * this one (dumbbell): ONE claim AT TWO TIMES. The same measurement, of the same thing, taken
      twice — so the reading is neither number but the DISTANCE between them, and the connector
      joining the two markers is the mark.

    That last reading is what the data is arranged to force, and it is why the directions are
    MIXED rather than uniformly up. ``Nordics`` and ``Iberia`` gained, ``DACH`` and ``Benelux``
    lost, and the losses are the load-bearing half rather than the pessimistic one: a dumbbell's
    two markers are distinguished by hue, and Highcharts paints that hue onto the FIRST array slot
    rather than onto the numerically smaller value. A sample where every region rose would draw
    identically under either rule and so would hide the one way this type can silently lie — a
    falling row whose before/after colours swap, reporting a loss with the same picture a gain
    gets. ``UK & Ireland`` is the honest edge: it moved by 0.3 of a point, a connector barely
    longer than the markers it joins, which is what "no material change" actually looks like here
    and is why the guard against picking one column twice matters (that would draw EVERY region
    that way).

    The two columns are the same quantity in the same unit at two times, which is the type's whole
    premise — unlike ``_sales_vs_quota``'s pair, which share a unit but not a referent (one is the
    world, one is an intention), and unlike ``_temperature_range``'s, which are one measurement's
    two bounds. Every value is present: the missing-before, missing-after and missing-both cases
    are the tests' job, not a demo's
    (the ``_temperature_range``/``_forecast_range``/``_sales_vs_quota``/``_product_line_margin``
    rule), and here that division is sharper than usual, since a half-pair draws literally nothing
    and a demo full of blank ticks would read as a broken chart rather than as a policy.

    ``region`` leads with the category column, like every sample here and for the same
    load-bearing reason: the app opens on ``line`` with the first column as X, so a numeric first
    column would trip the x-in-y guard the instant the dataset is selected. ``accounts`` is a
    throwaway numeric column the chart never reads, carried for ``_reporting_lines``'s
    ``tenure_years`` reason — and, like ``_sales_vs_quota``'s ``deals_closed`` and
    ``_product_line_margin``'s ``sku_count``, it earns a second keep by its POSITION: the app's
    After picker defaults to the SECOND numeric column, so ``q4_share_pct`` must sit directly
    below ``q1_share_pct`` and this one below both, or the control lands on the wrong column and
    the sample no longer demonstrates the type on landing.
    """
    return pd.DataFrame(
        {
            "region": [
                "Nordics",
                "DACH",
                "Iberia",
                "Benelux",
                "UK & Ireland",
            ],
            # Percentage points of a segment. The BEFORE reading — the first numeric column, so
            # the app's Y control lands on it.
            "q1_share_pct": [12.4, 28.1, 9.6, 17.3, 22.8],
            # The same measurement twelve months later. Deliberately MIXED in direction: two rise,
            # two fall, one barely moves. The falls are what prove the before/after hues do not
            # swap on a decrease.
            "q4_share_pct": [18.9, 21.5, 15.2, 13.0, 22.5],
            "accounts": [340, 1210, 275, 590, 880],
        }
    )


def _company_milestones() -> pd.DataFrame:
    """A young company's first year as INSTANTS — one row per dated event, each a moment rather
    than a span.

    Tailored to timeline, and it is best read directly against ``_release_plan``, which is its
    mirror rather than its neighbour: both carry dates and neither carries a magnitude in its
    value slot, but a release plan's rows have EXTENT (a start and an end, so the mark is a bar)
    while these have none (one date, so the mark is a point). That is the whole difference
    between the two types, and reading the two samples side by side is what shows it is a
    difference in the DATA and not merely in the drawing. Four things are deliberate:

    * The date column carries ISO-8601 *strings*, ``_release_plan``'s reason exactly: that is
      what ``pd.read_csv`` hands back, so the sample exercises the real ``_coordinates`` sniff
      (an object column parsed to a datetime axis) rather than a pre-parsed ``datetime64`` no
      CSV upload would ever produce.
    * The gaps are IRREGULAR — six weeks, then two, ten, six, fourteen, six — because a
      timeline's whole claim is that distance on the page is distance in time. Evenly spaced
      events would draw the same chart a category axis draws, and would hide the one thing
      worth checking by eye.
    * It leads with the event NAME, the file's category-column-first rule, and here that rule
      is load-bearing twice over: the name is also the mark's entire identity (a timeline has
      no axis categories and no legend), so a frame whose first column were the date would draw
      a chart labelled with dates in both channels.
    * ``headcount`` is a genuine numeric column, so the dataset stays usable by the other chart
      types and the app's no-numeric-columns gate has something to find. It shares its NAME with
      ``_release_plan``'s spare column on purpose — the two samples differ in their coordinate
      shape and in nothing else, which is the comparison they exist to support.
    """
    return pd.DataFrame(
        {
            "milestone": [
                "Incorporated",
                "Seed round",
                "First hire",
                "Private beta",
                "Public launch",
                "Series A",
                "1,000th customer",
            ],
            "date": [
                "2026-01-12",
                "2026-02-23",  # +6 weeks
                "2026-03-09",  # +2 weeks: the tightest pair, so the labels must stagger
                "2026-05-18",  # +10 weeks
                "2026-06-29",  # +6 weeks
                "2026-10-05",  # +14 weeks: the widest gap, and the axis has to show it
                "2026-11-16",  # +6 weeks
            ],
            "headcount": [2, 3, 5, 9, 14, 26, 34],
        }
    )


def _weekly_bookings() -> pd.DataFrame:
    """Weekly bookings by sales region — four teams, eight weeks of observations.

    Tailored to solidgauge, and to nothing else in this file, on four counts:

    * It is the only sample whose numeric columns are COMPARABLE MEASURES OF ONE THING. Every
      other multi-column dataset mixes units (revenue against cost, GDP against life
      expectancy), and concentric rings sharing ONE dial only mean something when the columns
      share a scale.
    * It is the only sample meant to be read through an AGGREGATION rather than plotted
      directly. Every other dataset's numbers are marks; these are observations that mean
      nothing until they are collapsed — and they collapse six sensible ways: the quarter's
      total (``sum``: north 436, which the dial rounds out to 500, so the headline ring reads
      436 OF 500 rather than being 100% full of itself), a typical week (``mean``), the best
      week (``max``), this week (``last``).
    * ``emea`` goes unreported in two weeks — an ordinary reporting gap. It puts the drop
      INSIDE the aggregate: emea's mean is over six weeks, not eight.
    * ``partner_deals`` is unreported ENTIRELY, and it is the type's headline trap made
      reachable from the app rather than left to a test. ``pd.Series([nan, ...]).sum()`` is
      ``0.0``, so a naive reduction would draw that ring an emphatic, entirely fictional ZERO.
      The builder tests for empty ABOVE the reducer, reads it as no data, and keeps the ring as
      a null — an empty track, named only in the legend. (``float("nan")``, not ``None``: an
      all-``None`` column is OBJECT dtype, so the app's numeric picker could never offer it and
      the trap would be out of reach from the UI.)

    ``week`` is an ordinary category column and the regions ordinary numerics, so the frame is
    still a good citizen for line/column/heatmap/radar — and ``week`` is the one column a gauge
    ignores completely, having no label channel to put it in.
    """
    blank = float("nan")
    return pd.DataFrame(
        {
            "week": ["W01", "W02", "W03", "W04", "W05", "W06", "W07", "W08"],
            "north": [42, 51, 47, 58, 61, 55, 63, 59],  # sum 436 -> a 0..500 dial
            "south": [38, 35, 44, 41, 39, 46, 43, 48],  # sum 334
            "emea": [22, 27, 25, blank, blank, 31, 34, 36],  # sum 175, over SIX weeks
            "partner_deals": [blank] * 8,  # nothing reported: a null ring, not a zero
        }
    )


def _server_utilization() -> pd.DataFrame:
    """Resource utilization across nine hosts, as percentages — the needle gauge's dataset.

    It is `_weekly_bookings`' sibling and deliberately not its clone: both feed the gauge family,
    but they exercise the dial from OPPOSITE ends, and between them they cover the two ways a
    reader can misread one.

    * These columns are PERCENTAGES, so the reduction that means anything is ``mean``, not
      ``sum`` — and a mean of percentages lands the derived dial almost exactly on 0..100, the
      scale a reader already has in their head. (``sum`` on this frame is nonsense on purpose:
      it reads past 600% and the dial dutifully rounds out to 1000, which is the fastest way to
      SEE what the aggregation picker is actually doing to your numbers. The bookings sample
      makes the same point with the opposite default.)
    * The columns are comparable measures of one thing, which is the family's whole
      precondition: needles sharing ONE dial mean nothing when the columns have different units.
    * ``disk_pct`` is the point of the type. It sits far from the other two, so the three needles
      SPREAD across the face instead of bunching — which is what a gauge is for, and what a
      reader cannot get from three near-identical arcs.
    * ``swap_pct`` is unreported entirely — the family's headline trap, kept reachable from the
      app rather than left to a test, exactly as ``partner_deals`` is. ``pd.Series([nan, ...])``
      sums to ``0.0``, the additive identity, so a naive reduction would swing a needle
      confidently to the floor of the dial and CLAIM zero swap where the truth is "nobody said".
      The builder tests for empty above the reducer and keeps the mark as a null: no needle at
      all, named only in the legend. On a needle this matters MORE than on a ring, because a
      needle at zero is indistinguishable from a real reading of zero. (``float("nan")``, not
      ``None``: an all-``None`` column is object dtype, so the app's numeric picker could never
      offer it and the trap would be out of reach from the UI.)

    ``host`` is an ordinary category column, so the frame stays a good citizen for
    line/column/bar/heatmap — and it is the column a gauge ignores completely, having no label
    channel to put it in. It leads the frame deliberately: the app opens on ``line`` with the
    FIRST column as X, and a numeric first column would trip the x-in-y guard the moment this
    dataset was selected.
    """
    blank = float("nan")
    return pd.DataFrame(
        {
            "host": [
                "web-01",
                "web-02",
                "web-03",
                "api-01",
                "api-02",
                "db-01",
                "db-02",
                "cache-01",
                "batch-01",
            ],
            "cpu_pct": [62, 58, 55, 71, 68, 81, 77, 34, 92],  # mean ~66
            "memory_pct": [71, 68, 74, 66, 70, 88, 85, 41, 79],  # mean ~71
            "disk_pct": [45, 47, 44, 38, 40, 73, 76, 22, 51],  # mean ~48 — the spread
            "swap_pct": [blank]
            * 9,  # nothing reported: a null needle, not a confident zero
        }
    )


def _reporting_lines() -> pd.DataFrame:
    """A company's reporting lines — the who-reports-to-whom an organization chart is built for:
    each row is one PERSON (their name, their manager, their job title), and Highcharts lays the
    boxes out top-down from the manager->report links, printing the title INSIDE each box under the
    name (the title card that makes this an org chart rather than the networkgraph mirror above).

    Tailored to organization. It is the EDGE-LIST cousin of the sunburst sample ``_org_headcount``:
    both describe a hierarchy, but that one sizes concentric rings by a headcount VALUE, while this
    one draws titled boxes and carries no magnitude at all (an org chart is unweighted — a reporting
    line has no width). One row has a BLANK manager — ``Nadia``, the CEO — which the builder reads as
    a ROOT (no incoming link, the top box) exactly as the sunburst sample's blank parent means a
    top-level branch; every other person names a real manager, and several are BOTH a manager and a
    report (``Priya`` reports to Nadia and manages Sana and Tom), which is what gives the chart its
    depth.

    The first column is the employee, a *label*, so — like every sample and load-bearingly so — the
    app can open on ``line`` without a numeric first column tripping the x-in-y guard. ``title`` is
    the THIRD column on purpose: the app's Title control defaults to the column at that index, so the
    sample shows its cards without a click. ``tenure_years`` is a genuine numeric column carried for
    the reason ``_service_dependencies``'s ``calls_per_min`` is — so the roster stays usable by the
    value-based types and the app's no-numeric-columns gate has something to find — and the org chart
    ignores it, the honest place for a per-person number an org chart cannot draw."""
    return pd.DataFrame(
        {
            "employee": [
                "Nadia",
                "Owen",
                "Priya",
                "Raj",
                "Sana",
                "Tom",
                "Uma",
                "Vik",
                "Wei",
                "Xena",
            ],
            "manager": [
                "",  # Nadia is the CEO — a blank manager, so the builder draws her as the root
                "Nadia",
                "Nadia",
                "Nadia",
                "Priya",
                "Priya",
                "Owen",
                "Sana",
                "Sana",
                "Tom",
            ],
            "title": [
                "Chief Executive Officer",
                "VP Product",
                "VP Engineering",
                "Chief Financial Officer",
                "Engineering Manager",
                "Engineering Manager",
                "Product Lead",
                "Senior Engineer",
                "Engineer",
                "Engineer",
            ],
            "tenure_years": [12, 7, 9, 6, 4, 5, 3, 2, 1, 2],
        }
    )


# Label -> factory. Each label hints at the chart types the dataset suits.
SAMPLES = {
    "Monthly revenue vs cost (line/area/column)": _revenue_vs_cost,
    "Fruit sales (pie/bar/column)": _fruit_sales,
    "Height vs weight (scatter)": _height_vs_weight,
    "Daily temperature (areaspline)": _daily_temperature,
    "Country economics (bubble)": _country_economics,
    "Product ratings (radar)": _product_ratings,
    "Website activity by weekday (heatmap)": _weekly_activity,
    "Company market cap (treemap)": _company_market_cap,
    "Marketing conversion funnel (funnel)": _conversion_funnel,
    "Customer loyalty pyramid (pyramid)": _loyalty_pyramid,
    "Energy flow (sankey)": _energy_flow,
    "Regional migration flows (dependencywheel)": _regional_migration,
    "Service dependencies (networkgraph)": _service_dependencies,
    "Company reporting lines (organization)": _reporting_lines,
    "Service response times (boxplot)": _response_times,
    "Quarterly profit bridge (waterfall)": _profit_bridge,
    "Company headcount (sunburst)": _org_headcount,
    "Product release plan (xrange)": _release_plan,
    "Monthly temperature range (columnrange)": _temperature_range,
    "Projected monthly active users (arearange)": _forecast_range,
    "Quarterly sales vs quota (bullet)": _sales_vs_quota,
    "Product line margin by revenue (variwide)": _product_line_margin,
    "Market share shift by region (dumbbell)": _market_share_shift,
    "Company milestones (timeline)": _company_milestones,
    "Weekly bookings by region (solidgauge)": _weekly_bookings,
    "Server utilization (gauge)": _server_utilization,
}
