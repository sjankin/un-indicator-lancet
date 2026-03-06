"""
Visualisation module for the UN General Debate Climate-Health Indicator.
Produces all numbered PDF + CSV outputs matching the R/2025 report structure.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for script runs
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import geopandas as gpd

import config

# Colour palette (matches R report)
COL_HEALTH      = "#619cff"
COL_CLIMATE     = "#238b45"
COL_INTERSECTION = "#cb181d"

LTYPE = {"Health": "dashed", "Climate": "dashdot", "Intersection": "solid"}
FIGSIZE = (10, 7)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _pct_fmt(x, _):
    return f"{x:.0%}"


# ---------------------------------------------------------------------------
# Plot 6: proportion of countries mentioning each category — main figure
# ---------------------------------------------------------------------------

def plot_prop_countries(tallies: pd.DataFrame, output_dir: Path) -> None:
    df = tallies[tallies["year"] >= config.CORPUS_START_YEAR].copy()

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for col, label, colour in [
        ("health_prop",        "Health",       COL_HEALTH),
        ("climate_prop",       "Climate",      COL_CLIMATE),
        ("intersection_prop",  "Intersection", COL_INTERSECTION),
    ]:
        ax.plot(df["year"], df[col], label=label, color=colour,
                linestyle=LTYPE[label], linewidth=1.5)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_pct_fmt))
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Proportion of countries, %")
    ax.legend(loc="upper left")
    ax.set_title(f"Climate-health discourse in UNGD speeches ({config.CORPUS_START_YEAR}–{config.DATA_YEAR})")
    fig.tight_layout()

    _save(fig, output_dir / "6-prop-countries.pdf")

    out = df[["year", "health_prop", "climate_prop", "intersection_prop"]].rename(
        columns={"health_prop": "Health", "climate_prop": "Climate",
                 "intersection_prop": "Intersection"})
    out.to_csv(output_dir / "6-prop-countries.csv", index=False)


# ---------------------------------------------------------------------------
# Plot 7: total references per year
# ---------------------------------------------------------------------------

def _build_reference_df(doc_counts: pd.DataFrame) -> pd.DataFrame:
    df = doc_counts[doc_counts["year"] >= config.CORPUS_START_YEAR]
    return (
        df.groupby("year", as_index=False)
        .agg(Health=       ("health_count",       "sum"),
             Climate=      ("climate_count",       "sum"),
             Intersection= ("intersection_count",  "sum"),
             Health_avg=   ("health_count",        "mean"),
             Climate_avg=  ("climate_count",       "mean"),
             Intersection_avg=("intersection_count","mean"))
    )


def plot_total_references(doc_counts: pd.DataFrame, output_dir: Path) -> None:
    ref = _build_reference_df(doc_counts)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for col, colour in [("Health", COL_HEALTH), ("Climate", COL_CLIMATE),
                         ("Intersection", COL_INTERSECTION)]:
        ax.plot(ref["year"], ref[col], label=col, color=colour,
                linestyle=LTYPE[col], linewidth=1.2)

    ax.set_xlabel("Year")
    ax.set_ylabel("Total number of references")
    ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, output_dir / "7-total-references.pdf")

    ref[["year", "Health", "Climate", "Intersection"]].to_csv(
        output_dir / "7-total-references.csv", index=False)


# ---------------------------------------------------------------------------
# Plot 8: intersection references only
# ---------------------------------------------------------------------------

def plot_intersection_references(doc_counts: pd.DataFrame, output_dir: Path) -> None:
    ref = _build_reference_df(doc_counts)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(ref["year"], ref["Intersection"], color=COL_INTERSECTION, linewidth=1.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Total number of references")
    ax.set_title("Intersection (climate within health context)")
    fig.tight_layout()
    _save(fig, output_dir / "8-total-references-intersection.pdf")
    ref[["year", "Intersection"]].to_csv(
        output_dir / "8-total-references-intersection.csv", index=False)


# ---------------------------------------------------------------------------
# Plot 9: proportion of countries — intersection only
# ---------------------------------------------------------------------------

def plot_intersection_prop(tallies: pd.DataFrame, output_dir: Path) -> None:
    df = tallies[tallies["year"] >= config.CORPUS_START_YEAR].copy()

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(df["year"], df["intersection_prop"], color=COL_INTERSECTION, linewidth=1.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_pct_fmt))
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Proportion of countries, %")
    fig.tight_layout()
    _save(fig, output_dir / "9-prop-references-intersection.pdf")
    df[["year", "intersection_prop"]].rename(
        columns={"intersection_prop": "Intersection"}).to_csv(
        output_dir / "9-prop-references-intersection.csv", index=False)


# ---------------------------------------------------------------------------
# Plot 10: average references per country
# ---------------------------------------------------------------------------

def plot_avg_references(doc_counts: pd.DataFrame, output_dir: Path) -> None:
    ref = _build_reference_df(doc_counts)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for col, colour in [("Health_avg", COL_HEALTH), ("Climate_avg", COL_CLIMATE),
                         ("Intersection_avg", COL_INTERSECTION)]:
        label = col.replace("_avg", "")
        ax.plot(ref["year"], ref[col], label=label, color=colour,
                linestyle=LTYPE[label], linewidth=1.2)

    ax.set_xlabel("Year")
    ax.set_ylabel("Average number of references per country")
    ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, output_dir / "10-avg-references.pdf")
    ref[["year", "Health_avg", "Climate_avg", "Intersection_avg"]].rename(
        columns={"Health_avg": "Health", "Climate_avg": "Climate",
                 "Intersection_avg": "Intersection"}).to_csv(
        output_dir / "10-avg-references.csv", index=False)


# ---------------------------------------------------------------------------
# Subgroup plots (WHO region, LC Grouping, HDI) — plots 11–16
# ---------------------------------------------------------------------------

def _subgroup_plot(grp: pd.DataFrame,
                   group_col: str,
                   metric: str,
                   ylabel: str,
                   title: str,
                   out_path: Path,
                   pct: bool = False) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for label, sub in grp.groupby(group_col):
        sub = sub[sub["year"] >= config.CORPUS_START_YEAR]
        ax.plot(sub["year"], sub[metric], label=label, linewidth=1.2)

    if pct:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_pct_fmt))
        ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout()
    _save(fig, out_path)


def plot_who_references(grp: pd.DataFrame, output_dir: Path) -> None:
    valid = grp[grp["WHO Region"].notna() & (grp["WHO Region"] != "N/A")]
    inter = valid[valid["year"] >= config.CORPUS_START_YEAR]
    _subgroup_plot(inter, "WHO Region", "intersection_refs",
                   "Total references", "Intersection by WHO Region",
                   output_dir / "11-who-references.pdf")
    valid.to_csv(output_dir / "11-who-references.csv", index=False)


def plot_who_prop(grp: pd.DataFrame, output_dir: Path) -> None:
    valid = grp[grp["WHO Region"].notna() & (grp["WHO Region"] != "N/A")]
    _subgroup_plot(valid[valid["year"] >= config.CORPUS_START_YEAR],
                   "WHO Region", "intersection_prop",
                   "Proportion of countries, %", "Intersection (%) by WHO Region",
                   output_dir / "12-who-prop-references.pdf", pct=True)
    valid.to_csv(output_dir / "12-who-prop-references.csv", index=False)


def plot_lc_references(grp: pd.DataFrame, output_dir: Path) -> None:
    valid = grp[grp["LC Grouping"].notna()]
    _subgroup_plot(valid[valid["year"] >= config.CORPUS_START_YEAR],
                   "LC Grouping", "intersection_refs",
                   "Total references", "Intersection by LC Grouping",
                   output_dir / "13-lc-references.pdf")
    valid.to_csv(output_dir / "13-lc-references.csv", index=False)


def plot_lc_prop(grp: pd.DataFrame, output_dir: Path) -> None:
    valid = grp[grp["LC Grouping"].notna()]
    _subgroup_plot(valid[valid["year"] >= config.CORPUS_START_YEAR],
                   "LC Grouping", "intersection_prop",
                   "Proportion of countries, %", "Intersection (%) by LC Grouping",
                   output_dir / "14-lc-prop-references.pdf", pct=True)
    valid.to_csv(output_dir / "14-lc-prop-references.csv", index=False)


def plot_hdi_references(grp: pd.DataFrame, output_dir: Path) -> None:
    hdi_col = "HDI Level (2021)"
    valid = grp[grp[hdi_col].notna() & (grp[hdi_col] != "N/A")]
    _subgroup_plot(valid[valid["year"] >= config.CORPUS_START_YEAR],
                   hdi_col, "intersection_refs",
                   "Total references", "Intersection by HDI Level",
                   output_dir / "15-hdi-references.pdf")
    valid.to_csv(output_dir / "15-hdi-references.csv", index=False)


def plot_hdi_prop(grp: pd.DataFrame, output_dir: Path) -> None:
    hdi_col = "HDI Level (2021)"
    valid = grp[grp[hdi_col].notna() & (grp[hdi_col] != "N/A")]
    _subgroup_plot(valid[valid["year"] >= config.CORPUS_START_YEAR],
                   hdi_col, "intersection_prop",
                   "Proportion of countries, %", "Intersection (%) by HDI Level",
                   output_dir / "16-hdi-prop-references.pdf", pct=True)
    valid.to_csv(output_dir / "16-hdi-prop-references.csv", index=False)


# ---------------------------------------------------------------------------
# COVID / gender plots (17–18)
# ---------------------------------------------------------------------------

def plot_covid_intersection(covid_df: pd.DataFrame, output_dir: Path) -> None:
    if covid_df.empty:
        return
    covid_df.to_csv(output_dir / "17-intersection-covid.csv", index=False)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(covid_df["year"].astype(int), covid_df["prop_doct"],
            color="#0072B2", linewidth=1.5, marker="o")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_pct_fmt))
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Proportion of intersection documents (%)")
    ax.set_title("COVID mentions within intersection documents (2020–present)")
    fig.tight_layout()
    _save(fig, output_dir / "17-intersection-covid.pdf")


def plot_gender_intersection(gender_df: pd.DataFrame, output_dir: Path) -> None:
    if gender_df.empty:
        return
    gender_df.to_csv(output_dir / "18-intersection_gender.csv", index=False)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.plot(gender_df["year"].astype(int), gender_df["prop_doct"],
            color="#cc0055", linewidth=1.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_pct_fmt))
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Proportion of intersection documents with gender mention (%)")
    fig.tight_layout()
    _save(fig, output_dir / "18-intersection-gender.pdf")


# ---------------------------------------------------------------------------
# Maps: plots 27–29
# ---------------------------------------------------------------------------

def _world_map_data(iso_csv: Path) -> gpd.GeoDataFrame:
    """Return world GeoDataFrame with ISO3 codes joined."""
    world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    # naturalearth_lowres uses iso_a3; handle -99 (missing) entries
    world = world[world["iso_a3"] != "-99"].copy()
    return world


def _choropleth(world: gpd.GeoDataFrame,
                data: pd.DataFrame,
                value_col: str,
                title: str,
                high_colour: str,
                out_path: Path) -> None:
    merged = world.merge(data[["country", value_col]],
                         left_on="iso_a3", right_on="country", how="left")

    fig, ax = plt.subplots(figsize=(14, 8))
    merged.plot(column=value_col, ax=ax,
                cmap=None,
                missing_kwds={"color": "#f0f0f0", "label": "No data"},
                legend=True,
                legend_kwds={"label": "Number of references",
                             "orientation": "horizontal",
                             "shrink": 0.5})
    # Custom colour scale
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("custom", ["#ffffff", high_colour])
    merged.plot(column=value_col, ax=ax, cmap=cmap,
                missing_kwds={"color": "#f0f0f0"},
                legend=False)
    merged[merged[value_col].isna()].plot(ax=ax, color="#f0f0f0")
    merged[~merged[value_col].isna()].plot(
        column=value_col, ax=ax, cmap=cmap, legend=True,
        legend_kwds={"label": "References", "orientation": "horizontal", "shrink": 0.4})

    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    _save(fig, out_path)


def plot_maps(doc_counts: pd.DataFrame,
              iso_csv: Path,
              output_dir: Path,
              data_year: int | None = None) -> None:
    year = data_year or config.DATA_YEAR
    world = _world_map_data(iso_csv)

    year_df = doc_counts[doc_counts["year"] == year]

    for col, label, num, colour in [
        ("health_count",       "Health",       "27", COL_HEALTH),
        ("climate_count",      "Climate",      "28", COL_CLIMATE),
        ("intersection_count", "Intersection", "29", COL_INTERSECTION),
    ]:
        data = year_df[["country", col]].rename(columns={col: "count"})
        out_csv = output_dir / f"{num}-{label.lower()}-map.csv"
        data.to_csv(out_csv, index=False)

        try:
            merged = world.merge(data, left_on="iso_a3", right_on="country", how="left")
            cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
                "c", ["#ffffff", colour])

            fig, ax = plt.subplots(figsize=(14, 8))
            world.plot(ax=ax, color="#f0f0f0", linewidth=0.3, edgecolor="#aaaaaa")
            merged[~merged["count"].isna()].plot(
                column="count", ax=ax, cmap=cmap, linewidth=0.3,
                edgecolor="#aaaaaa", legend=True,
                legend_kwds={"label": "Number of references",
                             "orientation": "horizontal", "shrink": 0.4})
            ax.set_title(f"{label} references — {year}")
            ax.axis("off")
            fig.tight_layout()
            _save(fig, output_dir / f"{num}-{label.lower()}-map.pdf")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Map plot failed for %s: %s", label, e)


# ---------------------------------------------------------------------------
# CSV outputs (tables)
# ---------------------------------------------------------------------------

def write_all_csvs(tallies: pd.DataFrame,
                   corpus_summary: pd.DataFrame,
                   output_dir: Path) -> None:
    """Write numbered summary CSVs matching R output format."""
    output_dir.mkdir(parents=True, exist_ok=True)

    corpus_summary[corpus_summary["year"] >= config.CORPUS_START_YEAR].to_csv(
        output_dir / "1-corpus-summary.csv", index=False)

    df = tallies[tallies["year"] >= config.CORPUS_START_YEAR].copy()

    # 2: full yearly breakdown
    df.rename(columns={
        "total_speeches": "Speeches",
        "climate_texts": "Climate (N)", "health_texts": "Health (N)",
        "intersection_texts": "Intersection (N)",
        "climate_prop": "Climate (Prop)", "health_prop": "Health (Prop)",
        "intersection_prop": "Intersection (Prop)",
    }).to_csv(output_dir / "2-yearly-breakdown.csv", index=False)

    for num, cat, n_col, p_col in [
        ("3", "Health",       "Health (N)",       "Health (Prop)"),
        ("4", "Climate",      "Climate (N)",      "Climate (Prop)"),
        ("5", "Intersection", "Intersection (N)", "Intersection (Prop)"),
    ]:
        sub = df.rename(columns={
            "total_speeches": "Speeches",
            f"{cat.lower()}_texts": n_col,
            f"{cat.lower()}_prop":  p_col,
        })[["year", "Speeches", n_col, p_col]]
        sub.to_csv(output_dir / f"{num}-yearly-breakdown-{cat.lower()}.csv", index=False)


def write_country_csvs(doc_counts: pd.DataFrame, output_dir: Path) -> None:
    """Write one CSV per country with yearly time series (1970–DATA_YEAR)."""
    cdir = output_dir / "country_counts"
    cdir.mkdir(parents=True, exist_ok=True)

    full_years = list(range(config.CORPUS_START_YEAR, config.DATA_YEAR + 1))

    for country, sub in doc_counts.groupby("country"):
        pivot = (
            sub[["year", "health_count", "climate_count", "intersection_count"]]
            .rename(columns={"health_count": "Health",
                             "climate_count": "Climate",
                             "intersection_count": "Intersection"})
            .set_index("year")
            .reindex(full_years, fill_value=0)
            .reset_index()
            .rename(columns={"index": "year"})
        )
        pivot.to_csv(cdir / f"{country}.csv", index=False)
