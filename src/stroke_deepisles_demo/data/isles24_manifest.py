"""ISLES'24 Stroke dataset manifest for Hugging Face loading.

This project targets the Hugging Face dataset repo `hugging-science/isles24-stroke`.
On HF Spaces, calling `datasets.load_dataset(dataset_id, split="train")` can trigger
an eager download/prepare step for ~27GB of Parquet shards, which is not viable for
fast API endpoints like `/api/cases`.

The upstream dataset stores one case per Parquet file at:
`data/train-00000-of-00149.parquet` ... `data/train-00148-of-00149.parquet`

This manifest provides:
- The authoritative list of available case IDs (subject_ids) for the train split.
- A stable mapping from case ID → Parquet shard index (and thus data file path).

SSOT:
- Generated from the dataset at the pinned revision below by reading `subject_id`
  from each Parquet file (without downloading the full dataset).
"""

from __future__ import annotations

ISLES24_DATASET_ID = "hugging-science/isles24-stroke"
# Pinned to the dataset revision used to generate this manifest.
ISLES24_DATASET_REVISION = "9707a7fca6d3dd1a690de010ec4aed06bdcd0417"

ISLES24_TRAIN_NUM_FILES = 149

# Case IDs in the same order as the Parquet shard filenames (train-00000..., train-00001..., ...).
ISLES24_TRAIN_CASE_IDS: tuple[str, ...] = (
    "sub-stroke0001",
    "sub-stroke0002",
    "sub-stroke0003",
    "sub-stroke0004",
    "sub-stroke0005",
    "sub-stroke0006",
    "sub-stroke0007",
    "sub-stroke0008",
    "sub-stroke0009",
    "sub-stroke0010",
    "sub-stroke0011",
    "sub-stroke0012",
    "sub-stroke0013",
    "sub-stroke0014",
    "sub-stroke0015",
    "sub-stroke0016",
    "sub-stroke0017",
    "sub-stroke0019",
    "sub-stroke0020",
    "sub-stroke0021",
    "sub-stroke0022",
    "sub-stroke0025",
    "sub-stroke0026",
    "sub-stroke0027",
    "sub-stroke0028",
    "sub-stroke0030",
    "sub-stroke0033",
    "sub-stroke0036",
    "sub-stroke0037",
    "sub-stroke0038",
    "sub-stroke0040",
    "sub-stroke0043",
    "sub-stroke0045",
    "sub-stroke0047",
    "sub-stroke0048",
    "sub-stroke0049",
    "sub-stroke0052",
    "sub-stroke0053",
    "sub-stroke0054",
    "sub-stroke0055",
    "sub-stroke0057",
    "sub-stroke0062",
    "sub-stroke0066",
    "sub-stroke0068",
    "sub-stroke0070",
    "sub-stroke0071",
    "sub-stroke0073",
    "sub-stroke0074",
    "sub-stroke0075",
    "sub-stroke0076",
    "sub-stroke0077",
    "sub-stroke0078",
    "sub-stroke0079",
    "sub-stroke0080",
    "sub-stroke0081",
    "sub-stroke0082",
    "sub-stroke0083",
    "sub-stroke0084",
    "sub-stroke0085",
    "sub-stroke0086",
    "sub-stroke0087",
    "sub-stroke0088",
    "sub-stroke0089",
    "sub-stroke0090",
    "sub-stroke0091",
    "sub-stroke0092",
    "sub-stroke0093",
    "sub-stroke0094",
    "sub-stroke0095",
    "sub-stroke0096",
    "sub-stroke0097",
    "sub-stroke0098",
    "sub-stroke0099",
    "sub-stroke0100",
    "sub-stroke0101",
    "sub-stroke0102",
    "sub-stroke0103",
    "sub-stroke0104",
    "sub-stroke0105",
    "sub-stroke0106",
    "sub-stroke0107",
    "sub-stroke0108",
    "sub-stroke0109",
    "sub-stroke0110",
    "sub-stroke0111",
    "sub-stroke0112",
    "sub-stroke0113",
    "sub-stroke0114",
    "sub-stroke0115",
    "sub-stroke0116",
    "sub-stroke0117",
    "sub-stroke0118",
    "sub-stroke0119",
    "sub-stroke0133",
    "sub-stroke0134",
    "sub-stroke0135",
    "sub-stroke0136",
    "sub-stroke0137",
    "sub-stroke0138",
    "sub-stroke0139",
    "sub-stroke0140",
    "sub-stroke0141",
    "sub-stroke0142",
    "sub-stroke0143",
    "sub-stroke0144",
    "sub-stroke0145",
    "sub-stroke0146",
    "sub-stroke0147",
    "sub-stroke0148",
    "sub-stroke0149",
    "sub-stroke0150",
    "sub-stroke0151",
    "sub-stroke0152",
    "sub-stroke0153",
    "sub-stroke0154",
    "sub-stroke0155",
    "sub-stroke0156",
    "sub-stroke0157",
    "sub-stroke0158",
    "sub-stroke0159",
    "sub-stroke0161",
    "sub-stroke0162",
    "sub-stroke0163",
    "sub-stroke0164",
    "sub-stroke0165",
    "sub-stroke0166",
    "sub-stroke0167",
    "sub-stroke0168",
    "sub-stroke0169",
    "sub-stroke0170",
    "sub-stroke0171",
    "sub-stroke0172",
    "sub-stroke0173",
    "sub-stroke0174",
    "sub-stroke0175",
    "sub-stroke0176",
    "sub-stroke0177",
    "sub-stroke0178",
    "sub-stroke0179",
    "sub-stroke0180",
    "sub-stroke0181",
    "sub-stroke0182",
    "sub-stroke0183",
    "sub-stroke0184",
    "sub-stroke0185",
    "sub-stroke0186",
    "sub-stroke0187",
    "sub-stroke0188",
    "sub-stroke0189",
)

ISLES24_TRAIN_CASE_ID_TO_FILE_INDEX: dict[str, int] = {
    case_id: idx for idx, case_id in enumerate(ISLES24_TRAIN_CASE_IDS)
}


def isles24_train_data_file(case_id: str) -> str:
    """Return the Parquet data file path in the HF dataset repo for a given case ID."""
    idx = ISLES24_TRAIN_CASE_ID_TO_FILE_INDEX[case_id]
    return f"data/train-{idx:05d}-of-{ISLES24_TRAIN_NUM_FILES:05d}.parquet"
