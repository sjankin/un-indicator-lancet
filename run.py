"""
run.py — CLI entry point for the UN General Debate Climate-Health Indicator.

Usage:
    python run.py                          # uses defaults from config.py
    python run.py --data-year 2024         # override data year
    python run.py --txt-root /path/to/txt  # override corpus path
    python run.py --no-plots               # skip visualisations
    python run.py --compare-r              # print comparison vs R outputs

Outputs are written to the same output/ directory as the R pipeline.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

import config
import pipeline as pl
import visualize as viz

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Lancet Countdown UNGD Climate-Health Indicator pipeline"
    )
    p.add_argument("--txt-root",  type=Path, default=config.DEFAULT_TXT_ROOT,
                   help="Path to txt/ directory containing session sub-folders")
    p.add_argument("--data-dir",  type=Path, default=config.DEFAULT_DATA_DIR,
                   help="Path to data/ directory (metadata Excel, iso_3.csv)")
    p.add_argument("--output-dir",type=Path, default=config.DEFAULT_OUTPUT_DIR,
                   help="Path to output/ directory")
    p.add_argument("--data-year", type=int, default=config.DATA_YEAR,
                   help="Most recent UNGD session year (default: %(default)s)")
    p.add_argument("--no-plots",  action="store_true",
                   help="Skip all visualisations; write CSVs only")
    p.add_argument("--compare-r", action="store_true",
                   help="After running, compare key statistics against saved R outputs")
    p.add_argument("--quiet",     action="store_true",
                   help="Suppress progress bars")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    # Override config globals if CLI args differ from defaults
    config.DATA_YEAR   = args.data_year
    config.REPORT_YEAR = args.data_year + 1

    txt_root   = args.txt_root
    data_dir   = args.data_dir
    output_dir = args.output_dir
    show       = not args.quiet

    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== UN General Debate Climate-Health Indicator ===")
    log.info("Corpus:      %s", txt_root)
    log.info("Data year:   %d  |  Report year: %d", config.DATA_YEAR, config.REPORT_YEAR)
    log.info("Output:      %s", output_dir)

    # ------------------------------------------------------------------
    # Stage 1: run core pipeline
    # ------------------------------------------------------------------
    t0 = time.perf_counter()
    results = pl.run_pipeline(txt_root, show_progress=show)
    t1 = time.perf_counter()
    log.info("Pipeline complete in %.1fs", t1 - t0)

    corpus_summary = results["corpus_summary"]
    doc_counts     = results["doc_counts"]
    kwic_health    = results["kwic_health"]
    kwic_climate   = results["kwic_climate"]
    kwic_inter     = results["kwic_intersection"]

    # ------------------------------------------------------------------
    # Stage 2: merge metadata
    # ------------------------------------------------------------------
    meta_path = data_dir / "Country Names and groupings - 2023 Report.xlsx"
    if meta_path.exists():
        doc_counts = pl.merge_metadata(doc_counts, meta_path)
        log.info("Metadata merged from %s", meta_path.name)
    else:
        log.warning("Metadata file not found: %s — subgroup analyses will be skipped", meta_path)

    # ------------------------------------------------------------------
    # Stage 3: yearly tallies
    # ------------------------------------------------------------------
    tallies = pl.build_yearly_tallies(doc_counts, corpus_summary)

    # ------------------------------------------------------------------
    # Stage 4: subgroup breakdowns
    # ------------------------------------------------------------------
    who_grp = lc_grp = hdi_grp = None
    for col, name in [("WHO Region", "WHO"), ("LC Grouping", "LC"),
                       ("HDI Level (2021)", "HDI")]:
        if col in doc_counts.columns:
            grp = pl.build_subgroup_counts(doc_counts, col)
            if col == "WHO Region":   who_grp = grp
            elif col == "LC Grouping": lc_grp  = grp
            else:                      hdi_grp  = grp
        else:
            log.warning("Column '%s' not found — %s breakdown skipped", col, name)

    # ------------------------------------------------------------------
    # Stage 5: COVID / gender sub-analyses
    # ------------------------------------------------------------------
    covid_df, gender_df = pl.build_covid_gender_analysis(
        doc_counts, txt_root, show_progress=show)

    # ------------------------------------------------------------------
    # Stage 6: write CSVs
    # ------------------------------------------------------------------
    log.info("Writing CSV outputs…")
    viz.write_all_csvs(tallies, corpus_summary, output_dir)

    kwic_health.to_csv(output_dir / "health_kwic.csv", index=False)
    kwic_climate.to_csv(output_dir / "climate_kwic.csv", index=False)
    kwic_inter.to_csv(output_dir / "intersection_kwic.csv", index=False)

    viz.write_country_csvs(doc_counts, output_dir)

    if not covid_df.empty:
        covid_df.to_csv(output_dir / "17-intersection-covid.csv", index=False)
    if not gender_df.empty:
        gender_df.to_csv(output_dir / "18-intersection_gender.csv", index=False)

    # ------------------------------------------------------------------
    # Stage 7: plots
    # ------------------------------------------------------------------
    if not args.no_plots:
        log.info("Generating plots…")
        viz.plot_prop_countries(tallies, output_dir)
        viz.plot_total_references(doc_counts, output_dir)
        viz.plot_intersection_references(doc_counts, output_dir)
        viz.plot_intersection_prop(tallies, output_dir)
        viz.plot_avg_references(doc_counts, output_dir)

        if who_grp is not None:
            viz.plot_who_references(who_grp, output_dir)
            viz.plot_who_prop(who_grp, output_dir)
        if lc_grp is not None:
            viz.plot_lc_references(lc_grp, output_dir)
            viz.plot_lc_prop(lc_grp, output_dir)
        if hdi_grp is not None:
            viz.plot_hdi_references(hdi_grp, output_dir)
            viz.plot_hdi_prop(hdi_grp, output_dir)

        if not covid_df.empty:
            viz.plot_covid_intersection(covid_df, output_dir)
        if not gender_df.empty:
            viz.plot_gender_intersection(gender_df, output_dir)

        iso_csv = data_dir / "iso_3.csv"
        try:
            viz.plot_maps(doc_counts, iso_csv, output_dir, data_year=config.DATA_YEAR)
        except FileNotFoundError as e:
            log.warning("Map plots skipped: %s", e)

    # ------------------------------------------------------------------
    # Stage 8: summary to console
    # ------------------------------------------------------------------
    log.info("=== Summary for %d ===", config.DATA_YEAR)
    year_row = tallies[tallies["year"] == config.DATA_YEAR]
    if not year_row.empty:
        r = year_row.iloc[0]
        log.info("  Speeches:     %d", int(r["total_speeches"]))
        log.info("  Health:       %d  (%.0f%%)", int(r["health_texts"]),   r["health_prop"]*100)
        log.info("  Climate:      %d  (%.0f%%)", int(r["climate_texts"]),  r["climate_prop"]*100)
        log.info("  Intersection: %d  (%.0f%%)", int(r["intersection_texts"]), r["intersection_prop"]*100)

    # ------------------------------------------------------------------
    # Optional: compare against R outputs
    # ------------------------------------------------------------------
    if args.compare_r:
        _compare_r(tallies, output_dir)

    log.info("Done. Outputs in: %s", output_dir)


# ---------------------------------------------------------------------------
# R comparison helper
# ---------------------------------------------------------------------------

def _compare_r(tallies: pd.DataFrame, output_dir: Path) -> None:
    r_path = output_dir / "2-yearly-breakdown.csv"
    if not r_path.exists():
        log.warning("R output not found at %s — skipping comparison", r_path)
        return

    # The R output lives in the same directory (we just overwrote it).
    # Load a cached copy if it was saved before the run.
    cached = output_dir.parent / "output_r_reference" / "2-yearly-breakdown.csv"
    if not cached.exists():
        log.warning("R reference cache not found at %s", cached)
        log.info("To compare, save the R output CSV before running this pipeline.")
        return

    py_df = tallies[["year", "health_texts", "climate_texts", "intersection_texts",
                      "health_prop", "climate_prop", "intersection_prop"]]
    r_df  = pd.read_csv(cached).rename(columns={
        "Speeches": "speeches",
        "Health (N)": "health_texts", "Climate (N)": "climate_texts",
        "Intersection (N)": "intersection_texts",
        "Health (Prop)": "health_prop", "Climate (Prop)": "climate_prop",
        "Intersection (Prop)": "intersection_prop",
        "Year": "year",
    })

    merged = py_df.merge(r_df[["year", "health_texts", "climate_texts",
                                "intersection_texts"]], on="year", suffixes=("_py", "_r"))
    merged["h_diff"] = merged["health_texts_py"] - merged["health_texts_r"]
    merged["c_diff"] = merged["climate_texts_py"] - merged["climate_texts_r"]
    merged["i_diff"] = merged["intersection_texts_py"] - merged["intersection_texts_r"]

    diffs = merged[merged[["h_diff", "c_diff", "i_diff"]].abs().sum(axis=1) > 0]
    if diffs.empty:
        log.info("COMPARISON: Python and R outputs are identical for all years.")
    else:
        log.info("COMPARISON: %d year(s) differ between Python and R:", len(diffs))
        for _, row in diffs.iterrows():
            log.info("  %d: H=%+d  C=%+d  I=%+d",
                     int(row["year"]),
                     int(row["h_diff"]), int(row["c_diff"]), int(row["i_diff"]))


if __name__ == "__main__":
    main()
