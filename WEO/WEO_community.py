from pathlib import Path
from collections import deque
import random
import math
import time

import networkx as nx
import pandas as pd


# ============================================================
# Settings
# ============================================================
WEIGHT = "weight"
RESOLUTION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data cleaning"
    / "political_network_clean_lcc.gml"
)

OUTPUT_DIR = Path(__file__).resolve().parent / "results"

WEIGHT = "weight"

# First try 5 runs.
# For the final experiment you can increase this to 20.
N_RUNS = 10

SEED = 42

# Paper uses alpha = 1:
# stop if Q has not improved for alpha * N steps
ALPHA = 1.0


# ============================================================
# Weighted modularity
# ============================================================

def weighted_modularity(G, communities):
    return nx.community.modularity(
        G,
        communities,
        weight=WEIGHT,
        resolution=RESOLUTION
    )


# ============================================================
# Convert the two WEO partitions into communities
# ============================================================

def communities_from_sides(G, nodes, side):
    """
    WEO has two temporary partitions.

    IMPORTANT:
    each connected component inside either partition
    is treated as a community.
    """

    communities = []

    for group in (0, 1):

        group_nodes = [
            node
            for node in nodes
            if side[node] == group
        ]

        if not group_nodes:
            continue

        subgraph = G.subgraph(group_nodes)

        for component in nx.connected_components(subgraph):
            communities.append(set(component))

    return communities


# ============================================================
# Weighted node fitness
# ============================================================

def calculate_fitness(
    G,
    full_partition,
    target_nodes,
    strength,
    total_strength
):
    """
    Weighted Extremal Optimization fitness:

        lambda_i^w
        =
        w_r(i) / w_i
        -
        a_r(i)^w

    where

        w_i       = total weighted degree of node i
        w_r(i)    = weight from node i to its own community
        a_r(i)^w  = fraction of total network strength
                    belonging to that community
    """

    membership = {}
    community_fraction = {}

    # Determine which community each node belongs to
    for community_id, community in enumerate(full_partition):

        community_strength = sum(
            strength[node]
            for node in community
        )

        community_fraction[community_id] = (
            community_strength / total_strength
            if total_strength > 0
            else 0
        )

        for node in community:
            membership[node] = community_id

    fitness = {}

    for node in target_nodes:

        node_strength = strength[node]

        if node_strength == 0:
            fitness[node] = 0
            continue

        current_community = membership[node]

        internal_weight = 0.0

        for neighbor, edge_data in G[node].items():

            if (
                membership.get(neighbor)
                == current_community
            ):
                internal_weight += float(
                    edge_data.get(WEIGHT, 1.0)
                )

        fitness[node] = (
                internal_weight / node_strength
                - RESOLUTION * community_fraction[current_community]
        )

    return fitness


# ============================================================
# tau-EO node selection
# ============================================================

def select_node_tau_eo(
    nodes,
    fitness,
    side,
    rng
):
    """
    Rank nodes from worst fitness to best fitness.

    Select rank q with probability

        P(q) proportional to q^(-tau)

    where

        tau ~= 1 + 1 / ln(N)
    """

    # Do not allow a move that makes one side empty
    counts = {
        0: sum(side[n] == 0 for n in nodes),
        1: sum(side[n] == 1 for n in nodes)
    }

    movable_nodes = [
        node
        for node in nodes
        if counts[side[node]] > 1
    ]

    if not movable_nodes:
        return None

    # Worst fitness first
    ranked_nodes = sorted(
        movable_nodes,
        key=lambda node: fitness[node]
    )

    n = len(nodes)

    if n <= 1:
        return None

    tau = 1.0 + 1.0 / math.log(n)

    probabilities = [
        (rank + 1) ** (-tau)
        for rank in range(len(ranked_nodes))
    ]

    selected = rng.choices(
        ranked_nodes,
        weights=probabilities,
        k=1
    )[0]

    return selected


# ============================================================
# Optimize one recursive cut
# ============================================================

def optimize_cut(
    G,
    partition,
    target_index,
    rng,
    strength,
    total_strength
):
    """
    Apply WEO to one current community.

    The community is randomly split into two partitions.
    Nodes are then moved between the two partitions
    according to weighted extremal optimization.
    """

    target = set(partition[target_index])
    nodes = list(target)

    n = len(nodes)

    if n < 2:
        return None, weighted_modularity(
            G,
            partition
        )

    # Communities not currently being split
    fixed_communities = [
        set(community)
        for index, community in enumerate(partition)
        if index != target_index
    ]

    q_before = weighted_modularity(
        G,
        partition
    )

    # ========================================================
    # STEP 1
    # Randomly divide nodes into two roughly equal partitions
    # ========================================================

    shuffled = nodes.copy()
    rng.shuffle(shuffled)

    midpoint = n // 2

    side = {}

    for index, node in enumerate(shuffled):

        if index < midpoint:
            side[node] = 0
        else:
            side[node] = 1

    initial_components = communities_from_sides(
        G,
        nodes,
        side
    )

    initial_partition = (
        fixed_communities
        + initial_components
    )

    initial_q = weighted_modularity(
        G,
        initial_partition
    )

    # We only want splits that improve the original Q
    best_q = q_before
    best_components = None

    if initial_q > best_q:

        best_q = initial_q

        best_components = [
            set(c)
            for c in initial_components
        ]

    # ========================================================
    # STEP 2
    # Extremal optimization
    # ========================================================

    patience = max(
        1,
        math.ceil(ALPHA * n)
    )

    no_improvement = 0

    while no_improvement < patience:

        current_components = communities_from_sides(
            G,
            nodes,
            side
        )

        current_full_partition = (
            fixed_communities
            + current_components
        )

        # ----------------------------------------------------
        # Calculate lambda_i for every node in this component
        # ----------------------------------------------------

        fitness = calculate_fitness(
            G=G,
            full_partition=current_full_partition,
            target_nodes=nodes,
            strength=strength,
            total_strength=total_strength
        )

        # ----------------------------------------------------
        # Select a low-fitness node using tau-EO
        # ----------------------------------------------------

        selected_node = select_node_tau_eo(
            nodes,
            fitness,
            side,
            rng
        )

        if selected_node is None:
            break

        # ----------------------------------------------------
        # Move it to the other partition
        # ----------------------------------------------------

        side[selected_node] = (
            1 - side[selected_node]
        )

        # ----------------------------------------------------
        # Recalculate communities and Q
        # ----------------------------------------------------

        new_components = communities_from_sides(
            G,
            nodes,
            side
        )

        new_partition = (
            fixed_communities
            + new_components
        )

        new_q = weighted_modularity(
            G,
            new_partition
        )

        # ----------------------------------------------------
        # Keep the best solution found
        # ----------------------------------------------------

        if new_q > best_q + 1e-12:

            best_q = new_q

            best_components = [
                set(c)
                for c in new_components
            ]

            no_improvement = 0

        else:

            no_improvement += 1

    return best_components, best_q


# ============================================================
# One complete WEO run
# ============================================================

def weo_single_run(G, seed):
    """
    Complete recursive WEO community detection.
    """

    rng = random.Random(seed)

    # --------------------------------------------------------
    # Weighted node degree / strength
    # --------------------------------------------------------

    strength = {
        node: float(value)
        for node, value
        in G.degree(weight=WEIGHT)
    }

    # For an undirected weighted network:
    #
    # total_strength = 2 * total edge weight
    #
    total_strength = sum(
        strength.values()
    )

    # --------------------------------------------------------
    # Initial network
    # --------------------------------------------------------

    # Since you use the LCC, normally this starts with
    # exactly one component.
    partition = [
        set(component)
        for component in nx.connected_components(G)
    ]

    queue = deque(
        set(community)
        for community in partition
        if len(community) >= 2
    )

    # ========================================================
    # Recursive WEO
    # ========================================================

    while queue:

        target = queue.popleft()

        target_index = None

        # Find this community in the current partition
        for index, community in enumerate(partition):

            if community == target:
                target_index = index
                break

        if target_index is None:
            continue

        q_before = weighted_modularity(
            G,
            partition
        )

        new_components, q_after = optimize_cut(
            G=G,
            partition=partition,
            target_index=target_index,
            rng=rng,
            strength=strength,
            total_strength=total_strength
        )

        # ----------------------------------------------------
        # Accept the cut only when modularity improves
        # ----------------------------------------------------

        if (
            new_components is not None
            and q_after > q_before + 1e-12
            and len(new_components) > 1
        ):

            # Remove old community
            old_community = partition.pop(
                target_index
            )

            # Add newly discovered communities
            partition.extend(
                new_components
            )

            print(
                f"Accepted split: "
                f"{len(old_community)} nodes "
                f"-> "
                f"{[len(c) for c in new_components]} "
                f"| Qw: {q_before:.5f} -> {q_after:.5f}"
            )

            # Recursively process every new component
            for component in new_components:

                if len(component) >= 2:
                    queue.append(
                        set(component)
                    )

    final_q = weighted_modularity(
        G,
        partition
    )

    return partition, final_q


# ============================================================
# Multiple random runs
# ============================================================

def run_weo(
    G,
    n_runs=N_RUNS,
    seed=SEED
):
    """
    WEO contains random initialization and tau-EO
    selection, so perform several independent runs.

    The partition with the largest Q^w is retained.
    """

    master_rng = random.Random(seed)

    best_partition = None
    best_q = float("-inf")

    summary = []

    for run in range(1, n_runs + 1):

        run_seed = master_rng.randint(
            0,
            1_000_000_000
        )

        print()
        print("=" * 60)
        print(f"WEO RUN {run}")
        print("=" * 60)

        start_time = time.perf_counter()

        partition, q = weo_single_run(
            G,
            seed=run_seed
        )

        run_time = time.perf_counter() - start_time

        print()
        print(
            f"Run {run}: "
            f"Qw = {q:.6f}, "
            f"communities = {len(partition)}, "
            f"time = {run_time:.2f} s"
        )

        summary.append({
            "run": run,
            "seed": run_seed,
            "weighted_modularity": q,
            "number_of_communities": len(partition),
            "runtime_seconds": run_time
        })

        if q > best_q:

            best_q = q
            best_partition = [
                set(c)
                for c in partition
            ]

    return (
        best_partition,
        best_q,
        pd.DataFrame(summary)
    )


# ============================================================
# Main
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # Load graph
    # ========================================================

    G = nx.read_gml(
        GRAPH_PATH
    )

    if G.is_directed():
        raise ValueError(
            "This implementation expects an undirected network."
        )

    # Convert edge weight to float
    for u, v, data in G.edges(data=True):

        data[WEIGHT] = float(
            data.get(WEIGHT, 1)
        )

        if data[WEIGHT] < 0:
            raise ValueError(
                "WEO requires non-negative edge weights."
            )

    print("Network loaded")
    print("----------------------------")
    print(
        "Nodes:",
        G.number_of_nodes()
    )
    print(
        "Edges:",
        G.number_of_edges()
    )
    print(
        "Connected:",
        nx.is_connected(G)
    )

    # ========================================================
    # Run WEO
    # ========================================================

    (
        best_partition,
        best_q,
        run_summary
    ) = run_weo(G)

    # Sort communities from largest to smallest
    best_partition = sorted(
        best_partition,
        key=len,
        reverse=True
    )

    # ========================================================
    # Create community assignment
    # ========================================================

    community_map = {}

    for community_id, community in enumerate(
        best_partition,
        start=1
    ):

        for node in community:
            community_map[node] = community_id

    # ========================================================
    # Output community CSV
    # ========================================================

    rows = []

    weighted_degree = dict(
        G.degree(weight=WEIGHT)
    )

    for node in G.nodes():

        node_data = G.nodes[node]

        rows.append({
            "node_id": node,
            "name": node_data.get(
                "name",
                ""
            ),
            "weighted_degree": weighted_degree[node],
            "weo_community": community_map[node]
        })

    result_df = pd.DataFrame(rows)

    result_df = result_df.sort_values(
        [
            "weo_community",
            "weighted_degree"
        ],
        ascending=[
            True,
            False
        ]
    )

    result_df.to_csv(
        OUTPUT_DIR / "weo_communities.csv",
        index=False
    )

    # ========================================================
    # Community summary
    # ========================================================

    community_summary = []

    for community_id, community in enumerate(
        best_partition,
        start=1
    ):

        community_summary.append({
            "weo_community": community_id,
            "number_of_MPs": len(community),
            "total_strength": sum(
                weighted_degree[node]
                for node in community
            )
        })

    pd.DataFrame(
        community_summary
    ).to_csv(
        OUTPUT_DIR / "weo_community_summary.csv",
        index=False
    )

    # ========================================================
    # Save all run results
    # ========================================================

    run_summary.to_csv(
        OUTPUT_DIR / "weo_run_summary.csv",
        index=False
    )

    # ========================================================
    # Save graph with WEO community label
    # ========================================================

    output_graph = G.copy()

    nx.set_node_attributes(
        output_graph,
        community_map,
        "weo_community"
    )

    nx.write_gml(
        output_graph,
        OUTPUT_DIR
        / "political_network_weo.gml"
    )

    # ========================================================
    # Print final result
    # ========================================================

    print()
    print("=" * 60)
    print("BEST WEO RESULT")
    print("=" * 60)

    print(
        f"Weighted modularity Qw: "
        f"{best_q:.6f}"
    )

    print(
        f"Number of communities: "
        f"{len(best_partition)}"
    )

    print()

    for community_id, community in enumerate(
        best_partition,
        start=1
    ):

        print(
            f"Community {community_id}: "
            f"{len(community)} MPs"
        )

    print()
    print(
        "Results saved in:",
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()