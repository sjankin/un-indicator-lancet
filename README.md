# UN General Debate Climate-Health Indicator
## Lancet Countdown Indicator 5.4.1

Computational pipeline for measuring the proportion of UN member states that
co-mention climate change and health in their annual UN General Debate statements.

---

## Repository structure

```
/                   2025 report code (root — Lancet Countdown 2025, data year 2024)
  config.py         Dictionaries, compound map, pipeline parameters
  pipeline.py       Corpus ingestion → tokenisation → matching → aggregation
  visualize.py      All numbered PDF figures and paired CSVs
  run.py            CLI entry point
  requirements.txt  Python dependencies
  ANALYSIS.md       Full analytical documentation and validation notes

2026/               2026 report code (Lancet Countdown 2026, data year 2025)
  config.py
  pipeline.py
  run.py
  visualize.py
  requirements.txt
```

Each year's code is self-contained. The root-level files are the **2025 report**
(data year 2024); the `2026/` subdirectory is the **2026 report** (data year 2025).

---

## Quick start

```bash
# 2026 report
cd 2026/
python run.py \
  --corpus "/path/to/UNGDC projects/UN Data/TXT" \
  --output "/path/to/hardened/2026 report/output" \
  --metadata "/path/to/Notebook/2025 report/data/Country Names and groupings - 2023 Report.xlsx"
```

Outputs are written to the specified `--output` directory: 16 PDF figures each
with a paired CSV of identical data, plus summary CSVs 1–5 and per-country
time-series CSVs.

---

## Key methodology

- **Window**: 25 tokens (post stopword removal), validated against R/quanteda baseline
- **Tokenisation**: `[a-z][a-z0-9_'-]*` after lowercasing and whitespace normalisation
- **Multi-word expressions**: longest-first compounding (e.g. `climate_change`, `sea_level`)
- **Stopwords**: NLTK Snowball English (198 words), identical to quanteda default
- **Data year / Report year**: `DATA_YEAR + 1 = REPORT_YEAR` (e.g. 2025 data → 2026 report)

Full details and validation results are in `ANALYSIS.md`.

---

## 2026 report changes vs 2025

- Session 80 (2025) corpus constructed from audio transcription (Whisper API) across
  all six official UN languages, merged into a single English-language corpus
- Paris Agreement baseline (2016) reference line added to main time-series figure
- Figure CSVs now contain exactly and only the data plotted in each figure,
  matching Lancet Countdown data transparency requirements
- HDI metadata updated to 2025 vintage (`HDI Group 2025`)
- Subgroup plots filtered to `year >= CORPUS_START_YEAR` before CSV export

---

## Citation

Dasandi, N. & Jankin, S. (2026). Indicator 5.4.1: Climate Change and Health in the
UN General Debate. In: *The Lancet Countdown on Health and Climate Change: 2026 Report*.
