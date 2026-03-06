"""
UN General Debate Climate-Health Indicator — core pipeline.

Stages:
  1. ingest()      — read corpus, extract metadata from filenames
  2. tokenize()    — lowercase, MWE compound, tokenize, remove stopwords
  3. match()       — count health/climate/intersection hits per document
  4. aggregate()   — merge metadata, compute yearly and subgroup tallies
  5. kwic()        — keyword-in-context extraction

All heavy work is on plain Python lists; pandas only for final aggregation.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Iterator

import nltk
import pandas as pd
from tqdm import tqdm

import config

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NLTK stopwords — download once if not present
# ---------------------------------------------------------------------------
def _ensure_nltk_resources() -> None:
    for resource in ("tokenizers/punkt_tab", "corpora/stopwords"):
        try:
            nltk.data.find(resource)
        except LookupError:
            name = resource.split("/")[1]
            log.info("Downloading NLTK resource: %s", name)
            nltk.download(name, quiet=True)


_ensure_nltk_resources()

from nltk.corpus import stopwords as _nltk_sw
from nltk.tokenize import sent_tokenize

STOPWORDS: frozenset[str] = frozenset(_nltk_sw.words("english"))


# ---------------------------------------------------------------------------
# 1. Ingest
# ---------------------------------------------------------------------------

def iter_corpus(txt_root: Path) -> Iterator[dict]:
    """
    Yield one dict per speech file:
        {doc_id, country, session, year, text}

    Files named: {ISO3}_{SESSION}_{YEAR}.txt
    Silently skips files that don't match the naming convention.
    """
    for path in sorted(txt_root.rglob("*.txt")):
        parts = path.stem.split("_")
        if len(parts) != 3:
            continue
        country, session, year = parts
        doc_id = f"{country}_{year}"
        try:
            text = path.read_text(errors="replace")
        except OSError as e:
            log.warning("Cannot read %s: %s", path, e)
            continue
        yield {
            "doc_id":  doc_id,
            "country": country,
            "session": session,
            "year":    year,
            "text":    text,
        }


def build_corpus_df(txt_root: Path, show_progress: bool = True) -> pd.DataFrame:
    """
    Read all speeches into a DataFrame with columns:
        doc_id, country, session, year, text
    """
    records = list(tqdm(iter_corpus(txt_root),
                        desc="Reading corpus",
                        disable=not show_progress))
    df = pd.DataFrame(records)
    df["year"] = df["year"].astype(int)
    return df


# ---------------------------------------------------------------------------
# 2. Tokenize
# ---------------------------------------------------------------------------

def _apply_compounds(text: str) -> str:
    """Apply MWE compounding to lowercased text (longest-first, pre-sorted in config)."""
    for phrase, replacement in config.COMPOUND_MAP:
        text = text.replace(phrase, replacement)
    return text


_TOKEN_RE = re.compile(r"[a-z][a-z0-9_'-]*")


_WHITESPACE_RE = re.compile(r"\s+")


def tokenize(text: str) -> list[str]:
    """
    Full pre-processing pipeline for one document:
      1. lowercase
      2. whitespace normalisation (collapse \\n, \\t, multiple spaces → single space)
         — required so MWE phrases split across lines are compounded correctly,
           matching quanteda's token-level compound matching behaviour
      3. MWE compounding
      4. regex tokenization
      5. stopword removal (NLTK Snowball, matching quanteda)

    Returns list of tokens.
    """
    lowered = text.lower()
    normalised = _WHITESPACE_RE.sub(" ", lowered)
    compounded = _apply_compounds(normalised)
    raw_tokens = _TOKEN_RE.findall(compounded)
    return [t for t in raw_tokens if t not in STOPWORDS and len(t) > 1]


def corpus_summary_row(text: str, year: int) -> dict:
    """Compute sentences and word tokens for corpus summary."""
    sentences = sent_tokenize(text)
    words = _TOKEN_RE.findall(text.lower())
    return {"year": year, "sentences": len(sentences), "tokens": len(words)}


# ---------------------------------------------------------------------------
# 3. Match
# ---------------------------------------------------------------------------

def count_matches(tokens: list[str]) -> tuple[int, int, int]:
    """
    Returns (health_count, climate_count, intersection_count).

    intersection_count = number of climate term matches that fall within
    ±WINDOW tokens of any health term match (after stopword removal).
    """
    health_pos = [i for i, t in enumerate(tokens) if t in config.HEALTH_TERMS]
    climate_pos = [i for i, t in enumerate(tokens) if t in config.CLIMATE_TERMS]

    health_count = len(health_pos)
    climate_count = len(climate_pos)

    if health_count == 0 or climate_count == 0:
        return health_count, climate_count, 0

    # Build union of ±WINDOW bubbles around each health position
    n = len(tokens)
    w = config.WINDOW
    covered: set[int] = set()
    for pos in health_pos:
        covered.update(range(max(0, pos - w), min(n, pos + w + 1)))

    intersection_count = sum(1 for i in covered if tokens[i] in config.CLIMATE_TERMS)
    return health_count, climate_count, intersection_count


def count_supplementary(tokens: list[str],
                         term_set: frozenset[str]) -> int:
    """Count matches for a supplementary dictionary (COVID, gender) in a token list."""
    return sum(1 for t in tokens if t in term_set)


# ---------------------------------------------------------------------------
# 4. KWIC
# ---------------------------------------------------------------------------

def extract_kwic(doc_id: str,
                 tokens: list[str],
                 term_set: frozenset[str],
                 window: int = 25) -> list[dict]:
    """
    Keyword-in-context extraction matching quanteda kwic() output format.

    Returns list of dicts with:
        docname, from, to, pre, keyword, post, pattern
    """
    results = []
    for i, token in enumerate(tokens):
        if token not in term_set:
            continue
        pre = " ".join(tokens[max(0, i - window): i])
        post = " ".join(tokens[i + 1: min(len(tokens), i + window + 1)])
        results.append({
            "docname": doc_id,
            "from":    i,
            "to":      i,
            "pre":     pre,
            "keyword": token,
            "post":    post,
            "pattern": _pattern_label(token),
        })
    return results


def _pattern_label(token: str) -> str:
    if token in config.HEALTH_TERMS:
        return "health"
    if token in config.CLIMATE_TERMS:
        return "climate"
    return "other"


def extract_intersection_kwic(doc_id: str,
                               tokens: list[str],
                               window: int = 25) -> list[dict]:
    """
    KWIC for climate terms that appear within ±window of a health term.
    Mirrors the R kwic(health_windowed, climate_dict) approach.
    """
    health_pos = [i for i, t in enumerate(tokens) if t in config.HEALTH_TERMS]
    if not health_pos:
        return []

    n = len(tokens)
    covered: set[int] = set()
    for pos in health_pos:
        covered.update(range(max(0, pos - window), min(n, pos + window + 1)))

    results = []
    for i in sorted(covered):
        if tokens[i] not in config.CLIMATE_TERMS:
            continue
        pre = " ".join(tokens[max(0, i - window): i])
        post = " ".join(tokens[i + 1: min(n, i + window + 1)])
        results.append({
            "docname": doc_id,
            "from":    i,
            "to":      i,
            "pre":     pre,
            "keyword": tokens[i],
            "post":    post,
            "pattern": "climate",
        })
    return results


# ---------------------------------------------------------------------------
# 5. Aggregate
# ---------------------------------------------------------------------------

def run_pipeline(txt_root: Path,
                 show_progress: bool = True) -> dict[str, pd.DataFrame]:
    """
    Run the full pipeline on a corpus directory.

    Returns a dict with keys:
        corpus_summary  — year-level token/sentence counts
        doc_counts      — per-document health/climate/intersection counts
        kwic_health     — full KWIC for health terms
        kwic_climate    — full KWIC for climate terms
        kwic_intersection — KWIC for intersection (climate in health window)
    """
    corpus_df = build_corpus_df(txt_root, show_progress=show_progress)

    summary_rows: list[dict] = []
    count_rows:   list[dict] = []
    kwic_h:       list[dict] = []
    kwic_c:       list[dict] = []
    kwic_i:       list[dict] = []

    for _, row in tqdm(corpus_df.iterrows(),
                       total=len(corpus_df),
                       desc="Processing documents",
                       disable=not show_progress):

        # Corpus summary
        s = corpus_summary_row(row["text"], row["year"])
        summary_rows.append(s)

        # Tokenize
        tokens = tokenize(row["text"])

        # Counts
        hc, cc, ic = count_matches(tokens)
        count_rows.append({
            "doc_id":             row["doc_id"],
            "country":            row["country"],
            "year":               row["year"],
            "health_count":       hc,
            "climate_count":      cc,
            "intersection_count": ic,
        })

        # KWIC
        kwic_h.extend(extract_kwic(row["doc_id"], tokens, config.HEALTH_TERMS))
        kwic_c.extend(extract_kwic(row["doc_id"], tokens, config.CLIMATE_TERMS))
        kwic_i.extend(extract_intersection_kwic(row["doc_id"], tokens))

    # --- Corpus summary ---
    summary_df = (
        pd.DataFrame(summary_rows)
        .groupby("year", as_index=False)
        .agg(total_sentences=("sentences", "sum"),
             total_words=("tokens", "sum"))
    )
    speech_counts = corpus_df.groupby("year", as_index=False).size().rename(columns={"size": "total_speeches"})
    corpus_summary = speech_counts.merge(summary_df, on="year").sort_values("year")

    return {
        "corpus_summary":    corpus_summary,
        "doc_counts":        pd.DataFrame(count_rows),
        "kwic_health":       pd.DataFrame(kwic_h),
        "kwic_climate":      pd.DataFrame(kwic_c),
        "kwic_intersection": pd.DataFrame(kwic_i),
    }


def merge_metadata(doc_counts: pd.DataFrame,
                   metadata_path: Path) -> pd.DataFrame:
    """
    Join per-document counts with country grouping metadata.
    Metadata Excel columns used: ISO3, WHO Region, LC Grouping, HDI Level (2021).
    """
    meta = pd.read_excel(metadata_path, engine="openpyxl")
    # Normalise column names; keep only what we need
    iso_col = next(c for c in meta.columns if c.strip().upper() in ("ISO3", "ISO_3", "CODE"))
    meta = meta.rename(columns={iso_col: "ISO3"})

    merged = doc_counts.merge(meta, left_on="country", right_on="ISO3", how="left")
    return merged


def build_yearly_tallies(doc_counts: pd.DataFrame,
                         corpus_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-year counts and proportions for health / climate / intersection.
    """
    flagged = doc_counts.assign(
        climate_flag=      (doc_counts["climate_count"]      > 0).astype(int),
        health_flag=       (doc_counts["health_count"]        > 0).astype(int),
        intersection_flag= (doc_counts["intersection_count"]  > 0).astype(int),
    )

    yearly = (
        flagged
        .groupby("year", as_index=False)
        .agg(climate_texts=      ("climate_flag",      "sum"),
             health_texts=       ("health_flag",       "sum"),
             intersection_texts= ("intersection_flag", "sum"))
    )

    tallies = corpus_summary[["year", "total_speeches"]].merge(yearly, on="year", how="left").fillna(0)
    for col in ("climate", "health", "intersection"):
        tallies[f"{col}_prop"] = tallies[f"{col}_texts"] / tallies["total_speeches"]

    return tallies.sort_values("year")


def build_subgroup_counts(doc_counts: pd.DataFrame,
                          group_col: str) -> pd.DataFrame:
    """
    Total and proportion of documents mentioning each category,
    grouped by group_col (e.g. 'WHO Region', 'LC Grouping', 'HDI Level (2021)').
    """
    df = doc_counts.copy()
    df["climate_n"]      = (df["climate_count"]      >= 1).astype(int)
    df["health_n"]       = (df["health_count"]        >= 1).astype(int)
    df["intersection_n"] = (df["intersection_count"]  >= 1).astype(int)

    grp = (
        df.groupby(["year", group_col], as_index=False)
        .agg(
            total_docs=      ("doc_id",         "count"),
            climate_refs=    ("climate_count",   "sum"),
            health_refs=     ("health_count",    "sum"),
            intersection_refs=("intersection_count", "sum"),
            climate_prop=    ("climate_n",       "mean"),
            health_prop=     ("health_n",        "mean"),
            intersection_prop=("intersection_n", "mean"),
        )
        .dropna(subset=[group_col])
    )
    return grp.sort_values(["year", group_col])


def build_covid_gender_analysis(doc_counts: pd.DataFrame,
                                txt_root: Path,
                                show_progress: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Within intersection documents only:
      - COVID mentions (2020–DATA_YEAR)
      - Gender mentions (all years)

    Returns (intersection_covid_df, intersection_gender_df).
    """
    intersection_docs = set(
        doc_counts.loc[doc_counts["intersection_count"] > 0, "doc_id"]
    )

    covid_rows:  list[dict] = []
    gender_rows: list[dict] = []

    for path in tqdm(sorted(txt_root.rglob("*.txt")),
                     desc="COVID/gender analysis",
                     disable=not show_progress):
        parts = path.stem.split("_")
        if len(parts) != 3:
            continue
        country, _, year = parts
        doc_id = f"{country}_{year}"
        if doc_id not in intersection_docs:
            continue

        tokens = tokenize(path.read_text(errors="replace"))

        covid_count  = count_supplementary(tokens, config.COVID_TERMS)
        gender_count = count_supplementary(tokens, config.GENDER_TERMS)

        if year in config.COVID_YEARS:
            covid_rows.append({"doc_id": doc_id, "country": country,
                                "year": year, "covid_count": covid_count})
        gender_rows.append({"doc_id": doc_id, "country": country,
                             "year": year, "gender_count": gender_count})

    def _summarise(rows: list[dict], count_col: str) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        total_by_year = (
            df.groupby("year", as_index=False)
            .agg(total_docs=("doc_id", "nunique"))
        )
        hits_by_year = (
            df[df[count_col] > 0]
            .groupby("year", as_index=False)
            .agg(hits=(count_col, "sum"),
                 documents=("country", "nunique"))
        )
        out = total_by_year.merge(hits_by_year, on="year", how="left").fillna(0)
        out["prop_doct"] = (out["documents"] / out["total_docs"]).round(2)
        return out.sort_values("year")

    return _summarise(covid_rows, "covid_count"), _summarise(gender_rows, "gender_count")
