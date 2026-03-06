"""
Configuration for the UN General Debate Climate-Health Indicator.
Lancet Countdown Indicator 5.4.1

All dictionary terms use canonical underscore form.
All multi-word surface forms (space-separated and hyphenated) are handled
by COMPOUND_MAP, which is applied to lowercased text before tokenization.
See ANALYSIS.md §3.3 and §4 for full rationale.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — relative to this file's parent; override in run.py if needed
# ---------------------------------------------------------------------------
# Layout:
#   UN Indicator/
#     hardened/
#       2025 report/
#         code/       ← this file lives here
#         output/     ← report-ready PDFs and CSVs go here
#     Notebook/
#       2025 report/
#         data/       ← metadata Excel and iso_3.csv (shared, read-only)
#         txt/        ← corpus speeches (shared, read-only)
PROJECT_ROOT  = Path(__file__).parent                          # .../hardened/2025 report/code
REPORT_ROOT   = PROJECT_ROOT.parent                            # .../hardened/2025 report
UNGDC_ROOT    = PROJECT_ROOT.parent.parent.parent              # .../UN Indicator
NOTEBOOK_ROOT = UNGDC_ROOT / "Notebook"

# Default corpus and data paths (Notebook/ stays as the source-of-truth for raw data)
DEFAULT_TXT_ROOT   = NOTEBOOK_ROOT / "2025 report" / "txt"
DEFAULT_DATA_DIR   = NOTEBOOK_ROOT / "2025 report" / "data"
DEFAULT_OUTPUT_DIR = REPORT_ROOT / "output"

# ---------------------------------------------------------------------------
# Analysis parameters
# ---------------------------------------------------------------------------
WINDOW = 25            # token window for intersection (±WINDOW tokens around health term)
DATA_YEAR = 2024       # most recent UNGD session year in this run
REPORT_YEAR = 2025     # Lancet Countdown report year (DATA_YEAR + 1)
CORPUS_START_YEAR = 1970  # analyses exclude pre-1970 sessions

# ---------------------------------------------------------------------------
# Multi-word expression compound map
# Rules:
#   - applied to lowercased text before tokenization
#   - sorted longest-first to avoid partial-match shadowing
#   - both space-separated AND hyphenated surface forms → canonical underscore
# ---------------------------------------------------------------------------
_COMPOUND_MAP_UNSORTED = [
    # --- climate MWEs (space forms) ---
    ("global environmental change",  "global_environmental_change"),
    ("climate variability",          "climate_variability"),
    ("climate neutrality",           "climate_neutrality"),
    ("climate emergency",            "climate_emergency"),
    ("carbon neutrality",            "carbon_neutrality"),
    ("changing climate",             "changing_climate"),
    ("renewable energy",             "renewable_energy"),
    ("carbon emissions",             "carbon_emissions"),
    ("extreme weather",              "extreme_weather"),
    ("carbon emission",              "carbon_emission"),
    ("climate change",               "climate_change"),
    ("climate crisis",               "climate_crisis"),
    ("global warming",               "global_warming"),
    ("carbon dioxide",               "carbon_dioxide"),
    ("climate action",               "climate_action"),
    ("carbon neutral",               "carbon_neutral"),
    ("co2 emissions",                "co2_emissions"),
    ("co2 emission",                 "co2_emission"),
    ("low carbon",                   "low_carbon"),
    ("net zero",                     "net_zero"),
    ("green house",                  "green_house"),
    ("fossil fuels",                 "fossil_fuels"),
    ("fossil fuel",                  "fossil_fuel"),
    ("sea levels",                   "sea_level"),   # plural normalised to same token
    ("sea level",                    "sea_level"),
    ("paris agreement",              "paris_agreement"),
    ("paris accord",                 "paris_agreement"),  # variant → same canonical
    ("loss and damage",              "loss_and_damage"),
    ("climate finance",              "climate_finance"),
    # --- climate MWEs (hyphen forms → same canonical) ---
    ("net-zero",                     "net_zero"),
    ("carbon-neutral",               "carbon_neutral"),
    ("carbon-dioxide",               "carbon_dioxide"),
    ("greenhouse-gases",             "greenhouse_gases"),
    ("greenhouse-gas",               "greenhouse_gas"),
    # --- health MWEs (space forms) ---
    ("non-communicable diseases",    "non_communicable_diseases"),
    ("non-communicable disease",     "non_communicable_disease"),
    ("non communicable diseases",    "non_communicable_diseases"),
    ("non communicable disease",     "non_communicable_disease"),
    ("mental disorders",             "mental_disorders"),   # kept for legacy; 0 hits
    ("mental disorder",              "mental_disorder"),    # kept for legacy; 0 hits
    ("mental health",                "mental_health"),
    ("air pollution",                "air_pollution"),
    # --- greenhouse gas (space forms) ---
    ("greenhouse gases",             "greenhouse_gases"),
    ("greenhouse gas",               "greenhouse_gas"),
]

# Sort longest phrase first to avoid partial-match shadowing
COMPOUND_MAP = sorted(_COMPOUND_MAP_UNSORTED, key=lambda x: -len(x[0]))

# ---------------------------------------------------------------------------
# Climate dictionary
# All terms in canonical underscore form.
# See ANALYSIS.md §4.2 for full rationale and corpus frequencies.
# ---------------------------------------------------------------------------
CLIMATE_TERMS = frozenset([
    # Core climate science terms
    "climate_change",
    "changing_climate",
    "climate_emergency",
    "climate_crisis",
    "climate_decay",
    "global_warming",
    "greenhouse",
    "greenhouse_gas",
    "greenhouse_gases",
    "temperature",
    "temperatures",          # added: 184 corpus occurrences
    "extreme_weather",
    "climate_variability",
    "global_environmental_change",
    # GHG / energy
    "low_carbon",
    "renewable_energy",
    "carbon_emission",
    "carbon_emissions",
    "carbon_dioxide",
    "co2_emission",
    "co2_emissions",
    "climate_pollutant",
    "climate_pollutants",
    "decarbonization",
    "decarbonisation",
    "carbon_neutral",
    "carbon_neutrality",
    "climate_neutrality",
    "climate_action",
    "net_zero",
    "ghge",                  # abbreviation stub (0 corpus hits; retained for completeness)
    "ghges",                 # abbreviation stub (0 corpus hits; retained for completeness)
    "emissions",             # added: 1,468 occurrences; zero non-climate uses in corpus
    "fossil_fuel",           # added: 256 occurrences
    "fossil_fuels",          # added: plural
    # Extreme weather / physical impacts
    "sea_level",             # added: 543 combined occurrences
    "drought",               # added: 1,375 occurrences
    "droughts",              # added: plural
    "flood",                 # added: 197 occurrences
    "floods",                # added: 702 occurrences
    "flooding",              # added: 235 occurrences
    "hurricane",             # added: 561 occurrences
    "hurricanes",            # added: plural
    "cyclone",               # added: 110 occurrences
    "cyclones",              # added: plural
    # Climate policy vocabulary
    "paris_agreement",       # added: 1,127 occurrences
    "loss_and_damage",       # added: 170 occurrences (98 recent)
    "climate_finance",       # added: 144 occurrences (122 recent)
    "adaptation",            # added: 1,132 occurrences; UNFCCC term of art; <1% non-climate
    "mitigation",            # added: 577 occurrences; UNFCCC term of art; ~3% non-climate
    # Legacy surface forms kept for backward compatibility with old hyphenated corpus text
    # (these will only match if MWE compounding somehow misses them)
    "green_house",           # from "green house" (1 corpus hit; inert but harmless)
])

# ---------------------------------------------------------------------------
# Health dictionary
# See ANALYSIS.md §4.3 for rationale.
# ---------------------------------------------------------------------------
HEALTH_TERMS = frozenset([
    "malaria",
    "diarrhoea",
    "diarrhea",              # added: US spelling
    "infection",
    "infections",            # added: plural (48 corpus occurrences)
    "disease",
    "diseases",
    "sars",
    "measles",
    "pneumonia",
    "epidemic",
    "epidemics",
    "pandemic",
    "pandemics",
    "epidemiology",
    "healthcare",
    "health",
    "mortality",
    "morbidity",
    "nutrition",
    "illness",
    "illnesses",
    "ncd",
    "ncds",
    "air_pollution",
    "malnutrition",
    "malnourishment",
    "mental_health",         # added: 51 occurrences; fixes R bug (mental_disorder = 0 hits)
    "stunting",
    "non_communicable_disease",   # added: spelled-out form
    "non_communicable_diseases",  # added: 214 occurrences (5× more common than ncds)
    # Legacy — kept in compound_map for safety but 0 corpus hits:
    # "mental_disorder", "mental_disorders" — intentionally removed
])

# ---------------------------------------------------------------------------
# Supplementary dictionaries
# ---------------------------------------------------------------------------
COVID_TERMS = frozenset([
    "covid-19",
    "covid19",
    "corona",
    "coronavirus",
    "sars-cov-2",
])

GENDER_TERMS = frozenset([
    "gender",
    "male",
    "female",
    "man",
    "men",
    "woman",
    "women",
    "sex",
])

# Years for COVID sub-analysis
COVID_YEARS = frozenset(["2020", "2021", "2022", "2023", "2024"])
