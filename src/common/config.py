from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUTS = PROJECT_ROOT / "outputs"
REPORTS = PROJECT_ROOT / "reports"
DECK = PROJECT_ROOT / "deck"

SECTION1_OUTPUTS = OUTPUTS / "section1"
SECTION1_OUTPUT_CHARTS = SECTION1_OUTPUTS / "charts"
SECTION1_OUTPUT_RESULTS = SECTION1_OUTPUTS / "results"
SECTION1_OUTPUT_FINAL = SECTION1_OUTPUT_RESULTS / "final"
SECTION1_OUTPUT_DIAGNOSTICS = SECTION1_OUTPUT_RESULTS / "diagnostics"

SECTION2_OUTPUTS = OUTPUTS / "section2"
SECTION2_OUTPUT_CHARTS = SECTION2_OUTPUTS / "charts"
SECTION2_OUTPUT_RESULTS = SECTION2_OUTPUTS / "results"

SECTION3_OUTPUTS = OUTPUTS / "section3"
SECTION3_OUTPUT_CHARTS = SECTION3_OUTPUTS / "charts"
SECTION3_OUTPUT_RESULTS = SECTION3_OUTPUTS / "results"

HDB_COLLECTION_ID = "189"
HDB_DATASET_IDS = [
    "d_ebc5ab87086db484f88045b47411ebc5",  # 1990-1999
    "d_43f493c6c50d54243cc1eab0df142d6a",  # 2000-Feb 2012
    "d_2d5ff9ea31397b66239f245f57751537",  # Mar 2012-Dec 2014
    "d_ea9ed51da2787afaf8e51f827c304208",  # Jan 2015-Dec 2016
    "d_8b84c4ee58e3cfc0ece0d773c8ca6abc",  # Jan 2017 onwards
]
MRT_DATASET_ID = "d_b39d3a0871985372d7e1637193335da5"
BUS_STOP_DATASET_ID = "d_3f172c6feb3f4f92a2f47d93eed2908a"
SCHOOL_ZONE_DATASET_ID = "d_abf023b38d9bc451484e3d67b562bc5c"
COE_DATASET_ID = "d_69b3380ad7e51aff3a7dcc84eba52b8a"
PLANNING_AREA_DATASET_ID = "d_4765db0e87b9c86336792efe8a1f7a66"
HDB_BUILDING_DATASET_ID = "d_16b157c52ed637edd6ba1232e026258d"

CBD_COORDS = (1.2834, 103.8607)
LEASE_YEARS = 99
HDB_API_PAGE_SIZE = 5_000

DTL2_TOWNS = {
    "BUKIT PANJANG",
    "BUKIT BATOK",
    "BUKIT TIMAH",
    "CENTRAL AREA",
    "KALLANG/WHAMPOA",
    "QUEENSTOWN",
    "TOA PAYOH",
}


@dataclass(frozen=True)
class DatasetArtifact:
    dataset_id: str
    slug: str
    kind: str


HDB_ARTIFACTS = [
    DatasetArtifact("d_ebc5ab87086db484f88045b47411ebc5", "hdb_1990_1999", "hdb"),
    DatasetArtifact("d_43f493c6c50d54243cc1eab0df142d6a", "hdb_2000_2012", "hdb"),
    DatasetArtifact("d_2d5ff9ea31397b66239f245f57751537", "hdb_2012_2014", "hdb"),
    DatasetArtifact("d_ea9ed51da2787afaf8e51f827c304208", "hdb_2015_2016", "hdb"),
    DatasetArtifact("d_8b84c4ee58e3cfc0ece0d773c8ca6abc", "hdb_2017_onwards", "hdb"),
]


def ensure_directories() -> None:
    for path in (
        DATA_RAW,
        DATA_PROCESSED,
        REPORTS,
        SECTION1_OUTPUT_CHARTS,
        SECTION1_OUTPUT_RESULTS,
        SECTION1_OUTPUT_FINAL,
        SECTION1_OUTPUT_DIAGNOSTICS,
        SECTION2_OUTPUT_CHARTS,
        SECTION2_OUTPUT_RESULTS,
        SECTION3_OUTPUT_CHARTS,
        SECTION3_OUTPUT_RESULTS,
        DECK,
    ):
        path.mkdir(parents=True, exist_ok=True)
