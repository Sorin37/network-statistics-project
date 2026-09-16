from pathlib import Path

import pandas as pd
from sklearn.metrics import normalized_mutual_info_score


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ACTUAL_PATH = (
    PROJECT_ROOT
    / "data cleaning"
    / "nodes_clean.csv"
)

# Experiment 1: Standard WEO
STANDARD_WEO_PATH = (
    Path(__file__).resolve().parent
    / "results"
    / "weo_communities.csv"
)

# Experiment 2: Target-K WEO
TARGET_K_WEO_PATH = (
    Path(__file__).resolve().parent
    / "results"
    / "fixed_k_30"
    / "weo_communities.csv"
)


# ============================================================
# Calculate NMI
# ============================================================

def calculate_nmi(result_path, experiment_name):

    actual = pd.read_csv(ACTUAL_PATH)
    detected = pd.read_csv(result_path)

    # Make node IDs consistent
    actual["node_id"] = actual["node_id"].astype(str)
    detected["node_id"] = detected["node_id"].astype(str)

    # Match WEO nodes with actual party labels
    merged = detected.merge(
        actual[["node_id", "party"]],
        on="node_id",
        how="left"
    )

    # Check whether every WEO node has a party label
    missing = merged["party"].isna().sum()

    print(f"\n{experiment_name}")
    print("-" * 40)
    print(f"Matched nodes: {len(merged)}")
    print(f"Missing party labels: {missing}")

    if missing > 0:
        raise ValueError(
            "Some WEO nodes could not be matched to party labels."
        )

    nmi = normalized_mutual_info_score(
        merged["party"],
        merged["weo_community"],
        average_method="arithmetic"
    )

    print(f"NMI: {nmi:.4f}")

    return nmi


# ============================================================
# Main
# ============================================================

standard_nmi = calculate_nmi(
    STANDARD_WEO_PATH,
    "Standard WEO"
)

target_k_nmi = calculate_nmi(
    TARGET_K_WEO_PATH,
    "Target-K WEO (K=30)"
)

print("\n==============================")
print("NMI COMPARISON")
print("==============================")
print(f"Standard WEO:      {standard_nmi:.4f}")
print(f"Target-K WEO:      {target_k_nmi:.4f}")