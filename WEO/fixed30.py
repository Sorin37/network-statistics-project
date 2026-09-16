from pathlib import Path
import random
import math
import heapq

import networkx as nx
import pandas as pd


# ============================================================
# Settings
# ============================================================

# Experiment 2:
# Target-K Hierarchical Weighted Extremal Optimization
TARGET_K = 30

# For testing use 1.
# For the final experiment you can increase this to 5.
N_RUNS = 5

# Number of random WEO initializations tried for EACH split.
# Testing: 1
# Final experiment: 3 is reasonable.
SPLIT_RESTARTS = 1

SEED = 42

WEIGHT = "weight"

# Keep gamma = 1.0 so Experiment 2 changes only K,
# not the modularity resolution.
RESOLUTION = 1.0

# WEO stopping parameter for each binary split.
# Stop after approximately alpha * N moves without improvement.
ALPHA = 1.0


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GRAPH_PATH = (
    PROJECT_ROOT
    / "data cleaning"
    / "political_network_clean_lcc.gml"
)

# Intentionally use the same Experiment 2 folder
# so the old fixed-K results are overwritten.
OUTPUT_DIR = (
    Path(__file__).resolve().parent
    / "results"
    / f"fixed_k_{TARGET_K}"
)


# ============================================================
# Weighted modularity
# ============================================================

def weighted_modularity(G, communities):
    """
    Weighted modularity with resolution parameter gamma.
    """

    return nx.community.modularity(
        G,
        communities,
        weight=WEIGHT,
        resolution=RESOLUTION
    )


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

        lambda_i =
            w_i,r / s_i
            -
            gamma * a_r

    where:

        w_i,r = total edge weight from node i
                to its current community

        s_i   = weighted degree / strength of node i

        a_r   = fraction of total network strength
                belonging to the current community
    """

    membership = {}
    community_fraction = {}

    # --------------------------------------------------------
    # Community membership and community strength
    # --------------------------------------------------------

    for community_id, community in enumerate(
        full_partition
    ):

        community_strength = sum(
            strength[node]
            for node in community
        )

        community_fraction[community_id] = (
            community_strength / total_strength
            if total_strength > 0
            else 0.0
        )

        for node in community:
            membership[node] = community_id

    # --------------------------------------------------------
    # Fitness
    # --------------------------------------------------------

    fitness = {}

    for node in target_nodes:

        node_strength = strength[node]

        if node_strength == 0:
            fitness[node] = 0.0
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
            - RESOLUTION
            * community_fraction[current_community]
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

    Select rank q with probability:

        P(q) proportional to q^(-tau)

    where:

        tau ~= 1 + 1 / ln(N)
    """

    # --------------------------------------------------------
    # Number of nodes on each temporary side
    # --------------------------------------------------------

    counts = {
        0: sum(
            side[node] == 0
            for node in nodes
        ),
        1: sum(
            side[node] == 1
            for node in nodes
        )
    }

    # Do not move the final node out of a side,
    # otherwise one child community would disappear.
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

    tau = (
        1.0
        + 1.0 / math.log(n)
    )

    probabilities = [
        (rank + 1) ** (-tau)
        for rank in range(
            len(ranked_nodes)
        )
    ]

    selected_node = rng.choices(
        ranked_nodes,
        weights=probabilities,
        k=1
    )[0]

    return selected_node


# ============================================================
# Optimize ONE binary split
# ============================================================

def optimize_binary_community(
    G,
    target,
    rng,
    strength,
    total_strength
):
    """
    Use WEO to divide one existing community into
    exactly TWO non-empty child communities.

    This function does not decide whether splitting
    should stop globally.

    It only answers:

        "If this community has to be split,
         what is the best binary WEO split we can find?"

    Returns
    -------
    best_split:
        [child_A, child_B]

    best_delta_q:
        modularity change caused by this split
    """

    target = set(target)

    nodes = list(target)

    n = len(nodes)

    if n < 2:

        return (
            None,
            float("-inf")
        )

    # --------------------------------------------------------
    # Nodes outside this community stay unchanged.
    #
    # They can be represented as one outside set here because
    # their modularity contribution is identical before and
    # after this local split, so it cancels in Delta Q.
    # --------------------------------------------------------

    outside = (
        set(G.nodes())
        - target
    )

    # --------------------------------------------------------
    # Modularity BEFORE splitting target
    # --------------------------------------------------------

    parent_partition = [
        target
    ]

    if outside:
        parent_partition.append(
            outside
        )

    q_before = weighted_modularity(
        G,
        parent_partition
    )

    overall_best_split = None

    overall_best_delta = (
        float("-inf")
    )

    # ========================================================
    # Random restarts
    # ========================================================

    for restart in range(
        SPLIT_RESTARTS
    ):

        shuffled = nodes.copy()

        rng.shuffle(shuffled)

        midpoint = n // 2

        # ----------------------------------------------------
        # Initial random binary split
        # ----------------------------------------------------

        side = {}

        for index, node in enumerate(
            shuffled
        ):

            side[node] = (
                0
                if index < midpoint
                else 1
            )

        # ----------------------------------------------------
        # Helper
        # ----------------------------------------------------

        def get_two_groups():

            group_0 = {
                node
                for node in nodes
                if side[node] == 0
            }

            group_1 = {
                node
                for node in nodes
                if side[node] == 1
            }

            return (
                group_0,
                group_1
            )

        # ----------------------------------------------------
        # Initial Q
        # ----------------------------------------------------

        group_0, group_1 = (
            get_two_groups()
        )

        current_partition = [
            group_0,
            group_1
        ]

        if outside:

            current_partition.append(
                outside
            )

        current_q = (
            weighted_modularity(
                G,
                current_partition
            )
        )

        best_q = current_q

        best_split = [
            set(group_0),
            set(group_1)
        ]

        # ----------------------------------------------------
        # WEO stopping rule
        # ----------------------------------------------------

        patience = max(
            1,
            math.ceil(
                ALPHA * n
            )
        )

        no_improvement = 0

        # ====================================================
        # Extremal optimization
        # ====================================================

        while (
            no_improvement
            < patience
        ):

            group_0, group_1 = (
                get_two_groups()
            )

            current_partition = [
                group_0,
                group_1
            ]

            if outside:

                current_partition.append(
                    outside
                )

            # ------------------------------------------------
            # Calculate node fitness
            # ------------------------------------------------

            fitness = calculate_fitness(
                G=G,
                full_partition=current_partition,
                target_nodes=nodes,
                strength=strength,
                total_strength=total_strength
            )

            # ------------------------------------------------
            # tau-EO selection
            # ------------------------------------------------

            selected_node = (
                select_node_tau_eo(
                    nodes=nodes,
                    fitness=fitness,
                    side=side,
                    rng=rng
                )
            )

            if selected_node is None:
                break

            # ------------------------------------------------
            # Move selected node to opposite side
            # ------------------------------------------------

            side[selected_node] = (
                1
                - side[selected_node]
            )

            # ------------------------------------------------
            # Recalculate Q
            # ------------------------------------------------

            group_0, group_1 = (
                get_two_groups()
            )

            new_partition = [
                group_0,
                group_1
            ]

            if outside:

                new_partition.append(
                    outside
                )

            new_q = weighted_modularity(
                G,
                new_partition
            )

            # ------------------------------------------------
            # Keep the best state found
            # ------------------------------------------------

            if (
                new_q
                > best_q + 1e-12
            ):

                best_q = new_q

                best_split = [
                    set(group_0),
                    set(group_1)
                ]

                no_improvement = 0

            else:

                no_improvement += 1

        # ----------------------------------------------------
        # Modularity change produced by this candidate split
        # ----------------------------------------------------

        delta_q = (
            best_q
            - q_before
        )

        if (
            delta_q
            > overall_best_delta
        ):

            overall_best_delta = (
                delta_q
            )

            overall_best_split = [
                set(best_split[0]),
                set(best_split[1])
            ]

    return (
        overall_best_split,
        overall_best_delta
    )


# ============================================================
# Target-K hierarchical WEO
# ============================================================

def target_k_hierarchical_run(
    G,
    target_k,
    seed
):
    """
    Experiment 2:

    Target-K Hierarchical Weighted Extremal Optimization.

    Start:
        1 community

    Repeatedly:
        choose the current community whose best WEO
        binary split gives the largest Delta Q

    Continue:
        until exactly target_k communities exist

    Unlike Standard WEO, negative Delta Q splits may be
    accepted after all positive Delta Q splits are exhausted,
    because this experiment explicitly requires K communities.
    """

    rng = random.Random(seed)

    n_nodes = G.number_of_nodes()

    if target_k < 1:

        raise ValueError(
            "TARGET_K must be at least 1."
        )

    if target_k > n_nodes:

        raise ValueError(
            "TARGET_K cannot exceed "
            "the number of nodes."
        )

    # --------------------------------------------------------
    # Weighted node strength
    # --------------------------------------------------------

    strength = {
        node: float(value)
        for node, value
        in G.degree(weight=WEIGHT)
    }

    total_strength = sum(
        strength.values()
    )

    # --------------------------------------------------------
    # Input should be the largest connected component
    # --------------------------------------------------------

    initial_components = [
        set(component)
        for component
        in nx.connected_components(G)
    ]

    if (
        len(initial_components)
        != 1
    ):

        raise ValueError(
            "Target-K experiment expects "
            "the LCC as input."
        )

    # --------------------------------------------------------
    # Current communities
    #
    # dictionary:
    # internal_id -> set(nodes)
    # --------------------------------------------------------

    next_id = 0

    communities = {
        next_id:
            initial_components[0]
    }

    next_id += 1

    # --------------------------------------------------------
    # Priority queue
    #
    # Stored as:
    #
    # (-Delta Q, community_id, split)
    #
    # heapq returns smallest value first,
    # therefore -Delta Q makes the largest
    # Delta Q appear first.
    # --------------------------------------------------------

    candidates = []

    # --------------------------------------------------------
    # Calculate candidate split for one community
    # --------------------------------------------------------

    def add_split_candidate(
        community_id,
        community
    ):

        if len(community) < 2:
            return

        split, delta_q = (
            optimize_binary_community(
                G=G,
                target=community,
                rng=rng,
                strength=strength,
                total_strength=total_strength
            )
        )

        if split is None:
            return

        heapq.heappush(
            candidates,
            (
                -delta_q,
                community_id,
                split
            )
        )

    # --------------------------------------------------------
    # Candidate for initial whole network
    # --------------------------------------------------------

    add_split_candidate(
        0,
        communities[0]
    )

    # ========================================================
    # Hierarchical splitting
    # ========================================================

    while (
        len(communities)
        < target_k
    ):

        if not candidates:

            raise RuntimeError(
                "No further community "
                "can be split."
            )

        (
            negative_delta_q,
            community_id,
            split
        ) = heapq.heappop(
            candidates
        )

        # Candidate may be stale if its parent
        # has already been split.
        if (
            community_id
            not in communities
        ):
            continue

        old_community = (
            communities.pop(
                community_id
            )
        )

        delta_q = (
            -negative_delta_q
        )

        child_a = set(
            split[0]
        )

        child_b = set(
            split[1]
        )

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if (
            not child_a
            or not child_b
        ):

            raise RuntimeError(
                "Invalid empty child "
                "community generated."
            )

        # ----------------------------------------------------
        # Add two children
        # ----------------------------------------------------

        child_a_id = next_id
        next_id += 1

        child_b_id = next_id
        next_id += 1

        communities[
            child_a_id
        ] = child_a

        communities[
            child_b_id
        ] = child_b

        print(
            f"K: "
            f"{len(communities) - 1}"
            f" -> "
            f"{len(communities)}"
            f" | "
            f"{len(old_community)} nodes"
            f" -> "
            f"{len(child_a)} + "
            f"{len(child_b)}"
            f" | "
            f"Delta Q = "
            f"{delta_q:.6f}"
        )

        # ----------------------------------------------------
        # Only the two new child communities need
        # new candidate splits.
        # ----------------------------------------------------

        add_split_candidate(
            child_a_id,
            child_a
        )

        add_split_candidate(
            child_b_id,
            child_b
        )

    # ========================================================
    # Final result
    # ========================================================

    final_partition = list(
        communities.values()
    )

    if (
        len(final_partition)
        != target_k
    ):

        raise RuntimeError(
            f"Expected {target_k} "
            f"communities, got "
            f"{len(final_partition)}."
        )

    final_q = weighted_modularity(
        G,
        final_partition
    )

    return (
        final_partition,
        final_q
    )


# ============================================================
# Multiple independent runs
# ============================================================

def run_weo(
    G,
    n_runs=N_RUNS,
    seed=SEED
):
    """
    Repeat the Target-K hierarchical WEO several times.

    Every run produces exactly TARGET_K communities.

    The run with the highest final weighted modularity
    is retained.
    """

    master_rng = random.Random(
        seed
    )

    best_partition = None

    best_q = float("-inf")

    summary = []

    for run in range(
        1,
        n_runs + 1
    ):

        run_seed = (
            master_rng.randint(
                0,
                1_000_000_000
            )
        )

        print()
        print("=" * 60)
        print(
            f"TARGET-K WEO RUN {run}"
        )
        print("=" * 60)

        partition, q = (
            target_k_hierarchical_run(
                G=G,
                target_k=TARGET_K,
                seed=run_seed
            )
        )

        print()
        print(
            f"Run {run}: "
            f"Qw = {q:.6f}, "
            f"communities = "
            f"{len(partition)}"
        )

        summary.append({
            "run": run,
            "seed": run_seed,
            "target_k": TARGET_K,
            "resolution": RESOLUTION,
            "split_restarts":
                SPLIT_RESTARTS,
            "weighted_modularity": q,
            "number_of_communities":
                len(partition)
        })

        if q > best_q:

            best_q = q

            best_partition = [
                set(community)
                for community
                in partition
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
    # Load network
    # ========================================================

    G = nx.read_gml(
        GRAPH_PATH
    )

    if G.is_directed():

        raise ValueError(
            "This implementation expects "
            "an undirected network."
        )

    # --------------------------------------------------------
    # Convert weights to float
    # --------------------------------------------------------

    for u, v, data in G.edges(
        data=True
    ):

        data[WEIGHT] = float(
            data.get(
                WEIGHT,
                1.0
            )
        )

        if (
            data[WEIGHT]
            < 0
        ):

            raise ValueError(
                "WEO requires "
                "non-negative edge weights."
            )

    print()
    print(
        "Network loaded"
    )

    print(
        "----------------------------"
    )

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

    print(
        "Target K:",
        TARGET_K
    )

    print(
        "Resolution:",
        RESOLUTION
    )

    # ========================================================
    # Run Experiment 2
    # ========================================================

    (
        best_partition,
        best_q,
        run_summary
    ) = run_weo(G)

    # --------------------------------------------------------
    # Largest community first
    # --------------------------------------------------------

    best_partition = sorted(
        best_partition,
        key=len,
        reverse=True
    )

    # ========================================================
    # Community assignment
    # ========================================================

    community_map = {}

    for (
        community_id,
        community
    ) in enumerate(
        best_partition,
        start=1
    ):

        for node in community:

            community_map[
                node
            ] = community_id

    # ========================================================
    # Node-level result
    # ========================================================

    weighted_degree = dict(
        G.degree(
            weight=WEIGHT
        )
    )

    rows = []

    for node in G.nodes():

        node_data = G.nodes[
            node
        ]

        rows.append({
            "node_id":
                node,

            "name":
                node_data.get(
                    "name",
                    ""
                ),

            "weighted_degree":
                weighted_degree[node],

            "weo_community":
                community_map[node]
        })

    result_df = (
        pd.DataFrame(rows)
    )

    result_df = (
        result_df.sort_values(
            [
                "weo_community",
                "weighted_degree"
            ],
            ascending=[
                True,
                False
            ]
        )
    )

    result_df.to_csv(
        OUTPUT_DIR
        / "weo_communities.csv",
        index=False
    )

    # ========================================================
    # Community summary
    # ========================================================

    community_summary = []

    for (
        community_id,
        community
    ) in enumerate(
        best_partition,
        start=1
    ):

        community_summary.append({
            "weo_community":
                community_id,

            "number_of_MPs":
                len(community),

            "total_strength":
                sum(
                    weighted_degree[node]
                    for node
                    in community
                )
        })

    pd.DataFrame(
        community_summary
    ).to_csv(
        OUTPUT_DIR
        / "weo_community_summary.csv",
        index=False
    )

    # ========================================================
    # Run summary
    # ========================================================

    run_summary.to_csv(
        OUTPUT_DIR
        / "weo_run_summary.csv",
        index=False
    )

    # ========================================================
    # Save GML
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
    # Final output
    # ========================================================

    print()
    print("=" * 60)
    print(
        "BEST TARGET-K "
        "HIERARCHICAL WEO RESULT"
    )
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

    for (
        community_id,
        community
    ) in enumerate(
        best_partition,
        start=1
    ):

        print(
            f"Community "
            f"{community_id}: "
            f"{len(community)} MPs"
        )

    print()

    print(
        "Results saved in:",
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()