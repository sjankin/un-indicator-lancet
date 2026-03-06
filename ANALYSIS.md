# UN General Debate Climate-Health Indicator: Analytical Plan

**Lancet Countdown Indicator 5.4.1**
Last updated: 2026-03-06

---

## 1. Overview

This indicator measures the degree to which national governments frame climate change as a health issue in their official statements to the United Nations General Debate (UNGD). It tracks three parallel constructs annually:

- **Health**: proportion of countries mentioning health-related terms
- **Climate**: proportion of countries mentioning climate-related terms
- **Intersection**: proportion of countries co-mentioning climate and health terms within a defined proximity window

The data source is the UN General Debate Corpus (UNGDC), covering Sessions 1–N (1946–present). The report year covers data through the previous UNGD session (e.g., the 2025 report covers through Session 79 / 2024).

---

## 2. Data

### 2.1 Corpus

- **Source**: UN General Debate Corpus (Baturo et al., 2017; updated annually)
- **Coverage**: ~10,952 speeches from 193 UN member states, 1946–2024 (Sessions 1–79)
- **File format**: Plain text, one file per speech
- **File naming convention**: `{ISO3}_{SESSION}_{YEAR}.txt` (e.g. `GBR_54_1999.txt`)
- **Directory structure**: `txt/Session {NN} - {YYYY}/{ISO3}_{NN}_{YYYY}.txt`

### 2.2 Metadata

- **Country groupings**: `data/Country Names and groupings - 2023 Report.xlsx`
  - Columns used: `ISO3`, `WHO Region`, `LC Grouping`, `HDI Level (2021)`
  - Note: HDI column name is vintage-pinned to 2021 dataset; update when refreshing metadata
- **ISO3 lookup**: `data/iso_3.csv` (country name ↔ ISO3 code, used for maps)

---

## 3. Pre-processing Pipeline

### 3.1 File ingestion

Read all `.txt` files matching the naming convention. Extract `country` (ISO3), `session`, and `year` from the filename stem. Construct `doc_id = f"{country}_{year}"`.

Note: multiple sessions per year do not occur in this corpus (one session per calendar year).

### 3.2 Corpus summary

For each year, compute:
- Number of speeches
- Number of sentences (via NLTK punkt tokenizer)
- Number of word tokens

Analysis uses years ≥ 1970 for plots (earlier sessions exist but have sparse coverage).

### 3.3 Multi-word expression (MWE) compounding

Before tokenization, apply string replacement to collapse multi-word phrases into single underscore-joined tokens. This ensures dictionary terms are matched as atomic units.

**Rules:**
1. Apply to lowercased text
2. Sort replacements longest-phrase-first to avoid partial matches (e.g. `"carbon emissions"` before `"carbon emission"`)
3. Both space-separated AND hyphenated surface forms map to the same canonical underscore form

See `config.py: COMPOUND_MAP` for the full list (N=31 patterns).

### 3.4 Tokenization

```python
tokens = re.findall(r"[a-z][a-z0-9_'-]*", text)
```

This regex:
- Captures word tokens starting with a letter
- Retains hyphens and underscores within tokens (preserving `net-zero`, `co2`, `climate_change`)
- Discards punctuation, numbers-only tokens, URLs

### 3.5 Stopword removal

Remove English stopwords using the NLTK Snowball list (`nltk.corpus.stopwords.words("english")`, 198 words). This matches the stopword list used by the original R/quanteda implementation.

**Validated**: using NLTK stopwords produces identical intersection counts to the R/quanteda pipeline (tested against 2024 session: 57/192 documents in both implementations).

---

## 4. Dictionary Design

### 4.1 Design principles

- Terms are **fixed strings** (no regex wildcards in the dictionary itself)
- All multi-word terms use underscore canonical form after MWE compounding
- Both singular and plural forms are included where both occur in the corpus
- Both British and American English spellings are included where both occur
- Hyphenated surface forms are normalised to underscore at the MWE stage; the dictionary contains only canonical forms
- Terms are chosen to be specific enough to discriminate climate/health discourse from general diplomatic language

### 4.2 Climate dictionary

| Term | Notes |
|---|---|
| `climate_change` | Core term |
| `changing_climate` | Variant phrasing |
| `climate_emergency` | Post-2019 escalation framing |
| `climate_crisis` | Post-2019 escalation framing |
| `climate_decay` | Less common variant |
| `global_warming` | Established scientific term |
| `greenhouse` | Single-word form |
| `greenhouse_gas` | Compounded from "greenhouse gas" / "greenhouse-gas" |
| `greenhouse_gases` | Plural |
| `temperature` | Validated in context: used exclusively in climate sense in recent UNGD |
| `temperatures` | Plural (184 corpus occurrences; previously missing) |
| `extreme_weather` | Compounded |
| `climate_variability` | IPCC vocabulary |
| `global_environmental_change` | Compounded |
| `low_carbon` | Policy term |
| `renewable_energy` | Compounded |
| `carbon_emission` | Compounded |
| `carbon_emissions` | Compounded plural |
| `carbon_dioxide` | Compounded; normalises `carbon-dioxide` |
| `co2_emission` | Compounded |
| `co2_emissions` | Compounded plural |
| `climate_pollutant` | Less common |
| `climate_pollutants` | Less common plural |
| `decarbonization` | US spelling |
| `decarbonisation` | British spelling |
| `carbon_neutral` | Compounded; normalises `carbon-neutral` |
| `carbon_neutrality` | Compounded |
| `climate_neutrality` | Compounded |
| `climate_action` | Post-2015 policy term |
| `net_zero` | Compounded; normalises `net-zero` (25 net-zero occurrences in 2024) |
| `ghge` | Abbreviation (rare; kept for completeness) |
| `ghges` | Abbreviation plural |
| `fossil_fuel` | **Added** — 256 corpus occurrences, unambiguous |
| `fossil_fuels` | **Added** — plural |
| `sea_level` | **Added** — 543 combined occurrences (space + hyphen forms) |
| `drought` | **Added** — 1,375 corpus occurrences, direct climate impact |
| `droughts` | **Added** — plural |
| `flood` | **Added** — 197 occurrences |
| `floods` | **Added** — 702 occurrences |
| `flooding` | **Added** — 235 occurrences |
| `hurricane` | **Added** — 561 occurrences |
| `hurricanes` | **Added** — 463 occurrences |
| `cyclone` | **Added** — 110 occurrences |
| `cyclones` | **Added** — 137 occurrences |
| `paris_agreement` | **Added** — 1,127 occurrences; the UNFCCC 2015 climate accord |
| `loss_and_damage` | **Added** — 170 occurrences (98 recent); UNFCCC compensation framework |
| `climate_finance` | **Added** — 144 occurrences (122 recent); climate policy vocabulary |
| `emissions` | **Added** — 1,468 occurrences; zero non-climate uses found in corpus |
| `adaptation` | **Added** — 1,132 occurrences; UNFCCC term of art in UNGD context; <1% non-climate use |
| `mitigation` | **Added** — 577 occurrences; UNFCCC term of art; ~3% non-climate use (disaster/risk mitigation) |

**Removed from R version:** `green_house` (1 corpus occurrence; inert), `greenhouse-gas` / `carbon-neutral` / `carbon-dioxide` / `net-zero` (replaced by normalised underscore forms), `ghge`/`ghges` (0 corpus occurrences — retained in config as stub for completeness but noted as non-contributing).

### 4.3 Health dictionary

| Term | Notes |
|---|---|
| `malaria` | Specific disease |
| `diarrhoea` | British spelling (15 occurrences) |
| `diarrhea` | **Added** — US spelling (2 occurrences; rare but complete) |
| `infection` | 86 occurrences |
| `infections` | **Added** — plural (48 occurrences; previously missing) |
| `disease` | 2,597 occurrences |
| `diseases` | 1,414 occurrences |
| `sars` | SARS-CoV-1; validated in context as disease use (36 occurrences) |
| `measles` | Specific disease |
| `pneumonia` | Specific disease |
| `epidemic` | 346 occurrences |
| `epidemics` | 294 occurrences |
| `pandemic` | 3,513 occurrences |
| `pandemics` | 368 occurrences |
| `epidemiology` | Technical term |
| `healthcare` | Single-word form |
| `health` | 7,312 occurrences; primary indicator term |
| `mortality` | 294 occurrences |
| `morbidity` | Technical term |
| `nutrition` | 294 occurrences; food/health nexus |
| `illness` | 126 occurrences |
| `illnesses` | 70 occurrences |
| `ncd` | Abbreviation for non-communicable disease |
| `ncds` | Plural abbreviation (139 occurrences) |
| `air_pollution` | Compounded; climate-health nexus term |
| `malnutrition` | 672 occurrences |
| `malnourishment` | 4 occurrences; British/variant form |
| `stunting` | Child stunting; 11 occurrences |
| `mental_health` | **Added** — 51 occurrences; replaces `mental_disorder`/`mental_disorders` which had 0 corpus occurrences (bug in R version) |
| `non_communicable_disease` | **Added** — compounded from "non-communicable disease"; spelled-out form (5 occurrences) |
| `non_communicable_diseases` | **Added** — compounded from "non-communicable diseases"; 214 occurrences; 5× more common than `ncds` |

**Removed from R version:** `mental_disorder`, `mental_disorders` — zero corpus occurrences; replaced by `mental_health`.

### 4.4 Supplementary dictionaries

**COVID dictionary** (used in intersection sub-analysis, 2020–2024 only):
`covid-19`, `covid19`, `corona`, `coronavirus`, `sars-cov-2`

**Gender dictionary** (used in intersection sub-analysis, all years):
`gender`, `male`, `female`, `man`, `men`, `woman`, `women`, `sex`

---

## 5. Core Analysis

### 5.1 Document-level counts

For each document, compute:
- `health_count`: number of health dictionary matches (after stopword removal and MWE compounding)
- `climate_count`: number of climate dictionary matches
- `intersection_count`: number of climate matches within a ±25-token window of any health match

A document is **flagged** for a category if its count ≥ 1.

### 5.2 Windowed intersection — methodology

The intersection operationalises "climate and health co-mentioned in close proximity". Implementation:

```python
# Find positions of all health term matches in the token list
health_positions = [i for i, t in enumerate(tokens) if t in health_terms]

# Expand each position into a ±WINDOW bubble; take the union
covered = set()
for pos in health_positions:
    covered.update(range(max(0, pos - WINDOW), min(len(tokens), pos + WINDOW + 1)))

# Count climate matches within the covered positions
intersection_count = sum(1 for i in covered if tokens[i] in climate_terms)
```

**Window size**: `WINDOW = 25` tokens (post-stopword-removal). This matches the original R/quanteda implementation and was validated to produce identical results.

**Methodological note**: quanteda's `tokens_select(window=25, padding=TRUE)` uses positions in the stopword-removed token sequence, which is what this implementation replicates. The Python and R implementations produce identical document-level flags when using the NLTK Snowball stopword list (validated against all 192 documents in the 2024 session: exact match).

**Window sensitivity** (2024, n=192): window=10 → 45 docs (23%); window=25 → 57 docs (30%); window=50 → 74 docs (39%). The chosen value of 25 sits in the stable mid-range.

### 5.3 Yearly aggregation

Per year, compute:
- `total_speeches`: total number of documents
- `climate_texts`: documents with climate_count ≥ 1
- `health_texts`: documents with health_count ≥ 1
- `intersection_texts`: documents with intersection_count ≥ 1
- Proportions: each divided by `total_speeches`

### 5.4 Keyword-in-context (KWIC)

For each dictionary match, record a ±25-token context window. Output columns match the R/quanteda `kwic()` format: `docname`, `from`, `to`, `pre`, `keyword`, `post`, `pattern`.

### 5.5 Subgroup analyses

All analyses are run on the full corpus; the following breakdowns are computed in the output stage:

- **By WHO region** (6 regions; Liechtenstein excluded as non-WHO member)
- **By LC Grouping** (Lancet Countdown regional groupings)
- **By HDI level** (Very High / High / Medium / Low; column `HDI Level (2021)`)

### 5.6 COVID and gender sub-analyses

Within documents flagged for intersection only:
- **COVID**: proportion mentioning COVID dictionary terms (2020–2024 only)
- **Gender**: proportion mentioning gender dictionary terms (all years)

### 5.7 Country-level output

Per-country time series (1970–present) of climate/health/intersection reference counts, output as one CSV per ISO3 country code.

---

## 6. Outputs

| File | Content |
|---|---|
| `1-corpus-summary.csv` | Year, speeches, sentences, words |
| `2-yearly-breakdown.csv` | Year, N and proportion for all three categories |
| `3-yearly-breakdown-health.csv` | Health only |
| `4-yearly-breakdown-climate.csv` | Climate only |
| `5-yearly-breakdown-intersection.csv` | Intersection only |
| `6-prop-countries.{csv,pdf}` | **Main figure**: proportion of countries by year |
| `7-total-references.{csv,pdf}` | Total keyword hits by year |
| `8-total-references-intersection.{csv,pdf}` | Intersection references only |
| `9-prop-references-intersection.{csv,pdf}` | Intersection proportion only |
| `10-avg-references.{csv,pdf}` | Average references per country by year |
| `11-who-references.{csv,pdf}` | By WHO region (total) |
| `12-who-prop-references.{csv,pdf}` | By WHO region (proportion) |
| `13-lc-references.{csv,pdf}` | By LC Grouping (total) |
| `14-lc-prop-references.{csv,pdf}` | By LC Grouping (proportion) |
| `15-hdi-references.{csv,pdf}` | By HDI level (total) |
| `16-hdi-prop-references.{csv,pdf}` | By HDI level (proportion) |
| `17-intersection-covid.csv` | COVID in intersection docs, 2020–data_year |
| `18-intersection-gender.{csv,pdf}` | Gender in intersection docs |
| `27-health-map.{csv,pdf}` | World map of health references, most recent year |
| `28-climate-map.{csv,pdf}` | World map of climate references, most recent year |
| `29-intersection-map.{csv,pdf}` | World map of intersection references, most recent year |
| `country_counts/{ISO3}.csv` | Per-country time series (1970–data_year) |
| `health_kwic.csv` | Full KWIC for health matches |
| `climate_kwic.csv` | Full KWIC for climate matches |
| `intersection_kwic.csv` | Full KWIC for intersection matches |

---

## 7. Implementation Notes

### 7.1 Technology stack

| Component | Package | Notes |
|---|---|---|
| File ingestion | `pathlib` (stdlib) | Replaces R `readtext` |
| Tokenization | `re` (stdlib) | Replaces R `quanteda::tokens()` |
| MWE compounding | `str.replace` (stdlib) | Replaces R `tokens_compound()` |
| Stopword removal | `nltk.corpus.stopwords` | Matches quanteda Snowball list exactly |
| Windowed intersection | Custom (stdlib) | No direct Python equivalent; validated against R |
| KWIC | Custom | Matches R `kwic()` output format |
| Data manipulation | `pandas` | Replaces R tidyverse |
| Plotting | `matplotlib` + `seaborn` | Replaces R ggplot2 |
| Maps | `geopandas` | Replaces R `ggplot2::map_data()` |
| Excel reading | `pandas` + `openpyxl` | Replaces R `readxl` |
| Serialization | `parquet` (pyarrow) | Replaces R `.RData` binary files |

### 7.2 Reproducibility

- All package versions pinned in `requirements.txt`
- NLTK stopwords corpus version: stable (not versioned by NLTK)
- Random seed: not required (no stochastic components)
- Pipeline is fully deterministic given the same input corpus

### 7.3 Incremental updates

The tokenized corpus is serialized to `data/corpus.parquet` after the first run. Subsequent runs detect new sessions (by comparing available session directories against the parquet file) and process only new documents, appending to the existing data.

### 7.4 Parameters (config.py)

| Parameter | Default | Description |
|---|---|---|
| `WINDOW` | 25 | Token window for intersection detection |
| `DATA_YEAR` | 2024 | Most recent UNGD session year |
| `REPORT_YEAR` | 2025 | Lancet Countdown report year (DATA_YEAR + 1) |
| `CORPUS_START_YEAR` | 1970 | First year included in analyses (earlier sessions exist) |

---

## 8. Validation

The Python pipeline is validated against the R/quanteda 2025 report outputs:

- **2024 session** (192 documents): Health=127, Climate=156, Intersection=57 — exact match
- Full historical comparison run after each implementation change
- Gold-standard R outputs stored in `Notebook/2025 report/output/` for reference

---

## 9. Known differences from R version

| Item | R (old) | Python (new) | Impact |
|---|---|---|---|
| `mental_disorder`/`mental_disorders` | In dict (0 hits) | Removed | None on counts; clean-up |
| `mental_health` | Not in dict | Added | Small increase in health counts |
| `ghost entries` (`ghge`, `ghges`, `green_house`) | In dict (0 hits) | Retained in config, noted | None |
| `greenhouse gas` (space form) | Caught only via `greenhouse` standalone | Explicitly compounded to `greenhouse_gas` | Minor increase in compound-form counts; `greenhouse` still catches both |
| Hyphenated forms (`net-zero` etc.) | Separate dict entries | Normalised to underscore; single dict entry | Identical coverage, cleaner |
| New climate terms (see §4.2) | Not in dict | Added | Increased climate/intersection counts |
| New health terms (see §4.3) | Not in dict | Added | Small increase in health counts |
| Surface form normalisation | Two mechanisms (compound + hyphen dict entries) | Single mechanism (compound map handles all) | Cleaner; identical results for validated terms |

---

## 10. Word2vec validation

The file `relationships_words.txt` contains nearest-neighbour similarity scores computed from a word2vec model trained on the UNGD corpus (from earlier research). These provide independent empirical validation that dictionary terms cluster as expected:

- `greenhouse` → neighbours: `carbon` (0.86), `dioxide` (0.86), `gases` (0.86), `emissions` (0.86) — confirms `emissions` is overwhelmingly climate-associated
- `climate_change` → neighbours: `global_warming` (0.76), `desertification` (0.62), `ncds` (0.56), `mitigation` (0.51) — confirms shared discourse space
- `temperature` → neighbours: `temperatures` (0.84), `1.5°c` (0.81), `2°c` (0.78) — confirms climate use

Potential future additions flagged by word2vec (not currently in dict, for consideration in later reports): `desertification`, `co2` (standalone), `warming` (standalone), `pollution` (standalone).
