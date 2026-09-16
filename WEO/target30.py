from pathlib import Path
import heapq
import math
import random

import networkx as nx
import pandas as pd


# ============================================================
# Settings
# ============================================================

TARGET_K = 30
#because the real party is 30
N_RUNS = 10
#use random number to get different result can get the best one
SPLIT_RESTARTS = 1

SEED = 42
WEIGHT = "weight"
RESOLUTION = 1.0
ALPHA = 1.0


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data cleaning"
    / "political_network_clean_lcc.gml"
)

OUTPUT_DIR = (
    Path(__file__).resolve().parent
    / "results"
    / "target_k30_clean"
)


# ============================================================
# 1. Weighted modularity
# ============================================================

def modularity(G, partition):

    return nx.community.modularity(
        G,
        partition,
        weight=WEIGHT,
        resolution=RESOLUTION
    )


# ============================================================
# 2. WEO node fitness
# ============================================================

def node_fitness(
    G,
    partition,
    target_nodes,
    strength,
    total_strength
):

    membership = {}
    community_fraction = {}

    for community_id, community in enumerate(partition):

        community_strength = sum(
            strength[node]
            for node in community
        )

        community_fraction[community_id] = (
            community_strength / total_strength
        )

        for node in community:
            membership[node] = community_id

    fitness = {}

    for node in target_nodes:

        s_i = strength[node]

        if s_i == 0:
            fitness[node] = 0.0
            continue

        community_id = membership[node]

        internal_weight = sum(
            float(data.get(WEIGHT, 1.0))
            for neighbor, data in G[node].items()
            if membership.get(neighbor) == community_id
        )

        fitness[node] = (
            internal_weight / s_i
            - RESOLUTION
            * community_fraction[community_id]
        )

    return fitness


# ============================================================
# 3. tau-EO node selection
# ============================================================

def select_node(nodes, fitness, side, rng):

    # Do not allow either temporary group to become empty
    counts = {
        0: sum(side[node] == 0 for node in nodes),
        1: sum(side[node] == 1 for node in nodes)
    }

    movable = [
        node
        for node in nodes
        if counts[side[node]] > 1
    ]

    if not movable:
        return None

    # Worst fitness first
    ranked = sorted(
        movable,
        key=lambda node: fitness[node]
    )

    tau = 1.0 + 1.0 / math.log(len(nodes))

    probabilities = [
        (rank + 1) ** (-tau)
        for rank in range(len(ranked))
    ]

    return rng.choices(
        ranked,
        weights=probabilities,
        k=1
    )[0]


# ============================================================
# 4. Find the best binary WEO split for one community
# ============================================================

def best_binary_split(
    G,
    target,
    rng,
    strength,
    total_strength
):

    target = set(target)
    nodes = list(target)

    if len(nodes) < 2:
        return None, float("-inf")

    outside = set(G.nodes()) - target

    # Q before splitting this community
    before_partition = [target]

    if outside:
        before_partition.append(outside)

    q_before = modularity(
        G,
        before_partition
    )

    overall_split = None
    overall_delta = float("-inf")

    # Try several random initial binary partitions
    for _ in range(SPLIT_RESTARTS):

        shuffled = nodes.copy()
        rng.shuffle(shuffled)

        midpoint = len(nodes) // 2

        side = {
            node: 0 if i < midpoint else 1
            for i, node in enumerate(shuffled)
        }

        def groups():

            group_a = {
                node
                for node in nodes
                if side[node] == 0
            }

            group_b = {
                node
                for node in nodes
                if side[node] == 1
            }

            return group_a, group_b

        group_a, group_b = groups()

        partition = [
            group_a,
            group_b
        ]

        if outside:
            partition.append(outside)

        best_q = modularity(
            G,
            partition
        )

        best_split = [
            set(group_a),
            set(group_b)
        ]

        patience = max(
            1,
            math.ceil(ALPHA * len(nodes))
        )

        no_improvement = 0

        # ----------------------------------------------------
        # Extremal optimization
        # ----------------------------------------------------

        while no_improvement < patience:

            group_a, group_b = groups()

            partition = [
                group_a,
                group_b
            ]

            if outside:
                partition.append(outside)

            fitness = node_fitness(
                G,
                partition,
                nodes,
                strength,
                total_strength
            )

            node = select_node(
                nodes,
                fitness,
                side,
                rng
            )

            if node is None:
                break

            # Move node to the opposite group
            side[node] = 1 - side[node]

            group_a, group_b = groups()

            new_partition = [
                group_a,
                group_b
            ]

            if outside:
                new_partition.append(outside)

            q_new = modularity(
                G,
                new_partition
            )

            if q_new > best_q + 1e-12:

                best_q = q_new

                best_split = [
                    set(group_a),
                    set(group_b)
                ]

                no_improvement = 0

            else:
                no_improvement += 1

        delta_q = best_q - q_before

        if delta_q > overall_delta:

            overall_delta = delta_q

            overall_split = [
                set(best_split[0]),
                set(best_split[1])
            ]

    return overall_split, overall_delta


# ============================================================
# 5. Hierarchical WEO until K communities
# ============================================================

def target_k_weo(G, target_k, seed):

    rng = random.Random(seed)

    strength = {
        node: float(value)
        for node, value
        in G.degree(weight=WEIGHT)
    }

    total_strength = sum(
        strength.values()
    )

    # LCC -> start with one community
    communities = {
        0: set(G.nodes())
    }

    next_id = 1

    # Priority queue:
    # highest Delta Q should be split first
    candidates = []

    def add_candidate(
        community_id,
        community
    ):

        if len(community) < 2:
            return

        split, delta_q = best_binary_split(
            G,
            community,
            rng,
            strength,
            total_strength
        )

        if split is not None:

            heapq.heappush(
                candidates,
                (
                    -delta_q,
                    community_id,
                    split
                )
            )

    # First split candidate
    add_candidate(
        0,
        communities[0]
    )

    # --------------------------------------------------------
    # Keep splitting until exactly K communities
    # --------------------------------------------------------

    while len(communities) < target_k:

        if not candidates:

            raise RuntimeError(
                "No community can be split further."
            )

        negative_delta, community_id, split = (
            heapq.heappop(candidates)
        )

        if community_id not in communities:
            continue

        parent = communities.pop(
            community_id
        )

        child_a = set(split[0])
        child_b = set(split[1])

        delta_q = -negative_delta

        id_a = next_id
        next_id += 1

        id_b = next_id
        next_id += 1

        communities[id_a] = child_a
        communities[id_b] = child_b

        print(
            f"K {len(communities) - 1:2d}"
            f" -> {len(communities):2d}"
            f" | {len(parent):3d}"
            f" -> {len(child_a):3d}"
            f" + {len(child_b):3d}"
            f" | Delta Q = {delta_q:.6f}"
        )

        add_candidate(
            id_a,
            child_a
        )

        add_candidate(
            id_b,
            child_b
        )

    final_partition = list(
        communities.values()
    )

    return (
        final_partition,
        modularity(G, final_partition)
    )


# ============================================================
# Multiple independent runs
# ============================================================

def run_experiment(G):

    rng = random.Random(SEED)

    best_partition = None
    best_q = float("-inf")

    run_rows = []

    for run in range(
        1,
        N_RUNS + 1
    ):

        run_seed = rng.randint(
            0,
            1_000_000_000
        )

        print()
        print(
            f"===== RUN {run} ====="
        )

        partition, q = target_k_weo(
            G,
            TARGET_K,
            run_seed
        )

        run_rows.append({
            "run": run,
            "seed": run_seed,
            "Qw": q,
            "number_of_communities":
                len(partition)
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
        pd.DataFrame(run_rows)
    )


# ============================================================
# Save results
# ============================================================

def save_results(
    G,
    partition,
    q,
    run_summary
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Largest first
    partition = sorted(
        partition,
        key=len,
        reverse=True
    )

    community_map = {}

    for community_id, community in enumerate(
        partition,
        start=1
    ):

        for node in community:
            community_map[node] = community_id

    weighted_degree = dict(
        G.degree(weight=WEIGHT)
    )

    # --------------------------------------------------------
    # Node-level output
    # --------------------------------------------------------

    rows = []

    for node in G.nodes():

        rows.append({
            "node_id": node,
            "name": G.nodes[node].get(
                "name",
                ""
            ),
            "weighted_degree":
                weighted_degree[node],
            "weo_community":
                community_map[node]
        })

    pd.DataFrame(rows).to_csv(
        OUTPUT_DIR / "weo_communities.csv",
        index=False
    )

    # --------------------------------------------------------
    # Community summary
    # --------------------------------------------------------

    summary = []

    for community_id, community in enumerate(
        partition,
        start=1
    ):

        summary.append({
            "weo_community":
                community_id,
            "number_of_MPs":
                len(community),
            "total_strength":
                sum(
                    weighted_degree[node]
                    for node in community
                )
        })

    pd.DataFrame(summary).to_csv(
        OUTPUT_DIR
        / "weo_community_summary.csv",
        index=False
    )

    run_summary.to_csv(
        OUTPUT_DIR
        / "weo_run_summary.csv",
        index=False
    )

    # --------------------------------------------------------
    # Save GML
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Console result
    # --------------------------------------------------------

    print()
    print("=" * 50)
    print("TARGET-K WEO RESULT")
    print("=" * 50)

    print(
        f"Weighted modularity Qw: {q:.6f}"
    )

    print(
        f"Number of communities: "
        f"{len(partition)}"
    )

    print()

    for i, community in enumerate(
        partition,
        start=1
    ):

        print(
            f"Community {i}: "
            f"{len(community)} MPs"
        )


# ============================================================
# Main
# ============================================================

def main():

    G = nx.read_gml(
        GRAPH_PATH
    )

    if G.is_directed():

        raise ValueError(
            "Expected an undirected graph."
        )

    for _, _, data in G.edges(
        data=True
    ):

        data[WEIGHT] = float(
            data.get(WEIGHT, 1.0)
        )

    print(
        f"Nodes: {G.number_of_nodes()}"
    )

    print(
        f"Edges: {G.number_of_edges()}"
    )

    print(
        f"Target K: {TARGET_K}"
    )

    partition, q, run_summary = (
        run_experiment(G)
    )

    save_results(
        G,
        partition,
        q,
        run_summary
    )


if __name__ == "__main__":
    main()