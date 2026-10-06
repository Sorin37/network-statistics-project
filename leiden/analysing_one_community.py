import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path


# =========================================================
# Largest Leiden Community: Cross-Party Analysis
#
# Purpose:
# Examine the largest detected Leiden community in more
# detail to understand the low correspondence between
# collaboration communities and political party membership.
#
# Analysis:
# 1. Identify the largest Leiden community
# 2. Examine its party composition
# 3. Identify collaborations between MPs from different parties
# 4. Aggregate cross-party edges by party pair
# 5. Visualize the most frequent cross-party connections
# =========================================================


# ---------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------

base_dir = Path(__file__).resolve().parent

artifacts_dir = base_dir / "artifacts"

graph_path = base_dir / "political_network_clean_full.gml"

# Leiden community assignment for each MP
df = pd.read_csv(
    artifacts_dir / "mp_community_mapping.csv"
)

# Full collaboration network used for the Leiden analysis
G = nx.read_gml(graph_path)


print("\nGraph loaded:")
print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")


# ---------------------------------------------------------
# 2. Select the largest Leiden community
# ---------------------------------------------------------

community_sizes = (
    df.groupby("Leiden_Community")
    .size()
    .sort_values(ascending=False)
)

print("\nCommunity sizes:")
print(community_sizes)

community_id = community_sizes.index[0]

community = df[
    df["Leiden_Community"] == community_id
].copy()

print(f"\nAnalysing Community {community_id}")
print(f"Number of MPs: {len(community)}")


# ---------------------------------------------------------
# 3. Examine party composition
# ---------------------------------------------------------

party_counts = (
    community["Actual_Party"]
    .value_counts()
    .reset_index()
)

party_counts.columns = ["Party", "MP_Count"]

party_counts["Percentage"] = (
    party_counts["MP_Count"]
    / len(community)
    * 100
).round(1)

print("\n--- Party composition ---")
print(party_counts.to_string(index=False))


# Community summary
n_party_labels = community["Actual_Party"].nunique()

dominant_party = party_counts.iloc[0]["Party"]
dominant_count = party_counts.iloc[0]["MP_Count"]
dominant_percentage = party_counts.iloc[0]["Percentage"]

print("\n--- Community summary ---")
print(f"Community: {community_id}")
print(f"MPs: {len(community)}")
print(f"Party labels represented: {n_party_labels}")
print(f"Dominant party: {dominant_party}")
print(
    f"Dominant party share: "
    f"{dominant_count}/{len(community)} "
    f"({dominant_percentage}%)"
)


# Save party composition and MP membership
party_counts.to_csv(
    artifacts_dir
    / f"community_{community_id}_party_composition.csv",
    index=False
)

community.to_csv(
    artifacts_dir
    / f"community_{community_id}_MPs.csv",
    index=False
)


# ---------------------------------------------------------
# 4. Identify cross-party collaborations
# ---------------------------------------------------------

# Lookups connecting each MP to their Leiden community
# and political party
community_lookup = dict(
    zip(
        df["MP_ID"].astype(str),
        df["Leiden_Community"]
    )
)

party_lookup = dict(
    zip(
        df["MP_ID"].astype(str),
        df["Actual_Party"]
    )
)

cross_party_edges = []

for source, target, edge_data in G.edges(data=True):

    source_id = str(source)
    target_id = str(target)

    # Ignore nodes that are not present in the Leiden mapping
    if (
        source_id not in community_lookup
        or target_id not in community_lookup
    ):
        continue

    # Only consider edges within the selected community
    if (
        community_lookup[source_id] == community_id
        and community_lookup[target_id] == community_id
    ):

        source_party = party_lookup[source_id]
        target_party = party_lookup[target_id]

        # Keep only edges connecting MPs from different parties
        if source_party != target_party:

            cross_party_edges.append({
                "MP_1": G.nodes[source].get(
                    "name", source_id
                ),
                "Party_1": source_party,
                "MP_2": G.nodes[target].get(
                    "name", target_id
                ),
                "Party_2": target_party,
                "Weight": edge_data.get("weight", 1)
            })


cross_party_df = pd.DataFrame(cross_party_edges)

print(
    f"\nCross-party edges inside Community "
    f"{community_id}: {len(cross_party_df)}"
)


# ---------------------------------------------------------
# 5. Analyse cross-party connections by party pair
# ---------------------------------------------------------

if not cross_party_df.empty:

    # Sort individual MP-pair collaborations by edge weight.
    # Weight represents the number of joint motions for that
    # particular pair of MPs.
    cross_party_df = cross_party_df.sort_values(
        by="Weight",
        ascending=False
    )

    print("\n--- Strongest individual cross-party edges ---")
    print(
        cross_party_df.head(20).to_string(index=False)
    )

    # Save all cross-party MP-pair edges
    cross_party_df.to_csv(
        artifacts_dir
        / f"community_{community_id}_cross_party_edges.csv",
        index=False
    )

    # Treat A-B and B-A as the same party pair
    cross_party_df["Party_Pair"] = cross_party_df.apply(
        lambda row: " - ".join(
            sorted([
                row["Party_1"],
                row["Party_2"]
            ])
        ),
        axis=1
    )

    # Count distinct MP-pair edges for each combination
    # of political parties
    party_pair_counts = (
        cross_party_df
        .groupby("Party_Pair")
        .size()
        .reset_index(name="Edge_Count")
        .sort_values(
            "Edge_Count",
            ascending=False
        )
    )

    print("\n--- Cross-party edges by party pair ---")
    print(
        party_pair_counts.to_string(index=False)
    )

    party_pair_counts.to_csv(
        artifacts_dir
        / f"community_{community_id}_party_pair_edges.csv",
        index=False
    )


    # -----------------------------------------------------
    # 6. Plot most frequent cross-party connections
    # -----------------------------------------------------

    top_pairs = (
        party_pair_counts
        .head(10)
        .sort_values(
            "Edge_Count",
            ascending=True
        )
    )

    plt.figure(figsize=(8, 5))

    plt.barh(
        top_pairs["Party_Pair"],
        top_pairs["Edge_Count"]
    )

    plt.xlabel(
        "Number of cross-party MP-pair edges"
    )
    plt.ylabel("Party pair")

    plt.title(
        f"Most Frequent Cross-Party Connections "
        f"in Community {community_id}"
    )

    plt.tight_layout()

    plt.savefig(
        artifacts_dir
        / f"community_{community_id}_cross_party_pairs.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()


else:

    print(
        "\nNo cross-party edges were found. "
        "Check whether the NetworkX node IDs match "
        "the MP_IDs in the Leiden mapping."
    )