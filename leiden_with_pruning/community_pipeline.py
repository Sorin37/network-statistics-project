import logging
import igraph as ig
import leidenalg as la
from typing import List, Tuple
from sklearn.metrics import normalized_mutual_info_score

logger = logging.getLogger(__name__)


class LeidenCommunityPipeline:
    """Core class for loading a network, detecting communities via Leiden,
    and performing edge-pruning operations.

    Pruning logic: an edge is removable only if it is NOT the max-weight edge
    incident to either endpoint. Removable edges are sorted weakest-first.
    """

    def __init__(self, gml_path: str, seed: int = 42):
        self.gml_path = gml_path
        self.seed = seed
        self.graph = None
        self._removal_order = None

    def load_network(self) -> None:
        """Loads the cleaned connected component graph."""
        self.graph = ig.Graph.Read_GML(self.gml_path)

    # ------------------------------------------------------------------
    # Pruning helpers
    # ------------------------------------------------------------------

    def _protected_edge_indices(self) -> set:
        """Returns the set of edge indices that must NOT be removed (each
        node's strongest incident edge is always protected)."""
        graph = self.graph
        protected = set()
        for vertex in range(graph.vcount()):
            incident = graph.incident(vertex)
            max_weight = max(graph.es[e]["weight"] for e in incident)
            for e in incident:
                if graph.es[e]["weight"] == max_weight:
                    protected.add(e)
        return protected

    def _ensure_removal_order(self) -> None:
        """Computes (and caches) the ordered list of removable edge indices,
        sorted weakest-first."""
        if self._removal_order is not None:
            return
        if self.graph is None:
            self.load_network()
        protected = self._protected_edge_indices()
        removable = [e for e in range(self.graph.ecount()) if e not in protected]
        removable.sort(key=lambda e: (self.graph.es[e]["weight"], e))
        self._removal_order = removable

    def pruned_graph_for(self, pruning_pct: float) -> ig.Graph:
        """Returns a copy of the graph with the weakest edges removed at the
        given pruning percentage."""
        self._ensure_removal_order()
        total_edges = self.graph.ecount()
        n_remove = min(
            int(round(pruning_pct / 100.0 * total_edges)),
            len(self._removal_order),
        )
        pruned = self.graph.copy()
        pruned.delete_edges(self._removal_order[:n_remove])
        return pruned

    def select_gamma(self, graph: ig.Graph, target_communities: int,
                     res_range: tuple = (0.05, 5.0)) -> tuple:
        """Picks the resolution parameter whose plateau is closest to the
        target community count. Returns (gamma, plateau_n_communities)."""
        optimiser = la.Optimiser()
        profile = optimiser.resolution_profile(
            graph,
            la.RBConfigurationVertexPartition,
            resolution_range=res_range,
            weights="weight",
        )

        best = None
        for i in range(len(profile) - 1):
            start = profile[i].resolution_parameter
            end = profile[i + 1].resolution_parameter
            n_comms = len(profile[i])
            diff = abs(n_comms - target_communities)
            if best is None or diff < best[0]:
                best = (diff, start, end, n_comms)

        # The final profile stage extends past the top of the range; pin to
        # its left edge.
        start = profile[-1].resolution_parameter
        n_comms = len(profile[-1])
        diff = abs(n_comms - target_communities)
        if diff < best[0]:
            best = (diff, start, start, n_comms)

        _, start, end, plateau_n = best
        gamma = (start + end) / 2.0
        return gamma, plateau_n

    # ------------------------------------------------------------------
    # Community detection
    # ------------------------------------------------------------------

    def find_partition(self, graph: ig.Graph, gamma: float) -> la.VertexPartition:
        """Finds a Leiden partition on the given graph at the specified gamma."""
        return la.find_partition(
            graph,
            la.RBConfigurationVertexPartition,
            resolution_parameter=gamma,
            weights="weight",
            seed=self.seed,
        )

    def compute_modularity(self, graph: ig.Graph, membership: list) -> float:
        """Computes modularity of the given membership on the given graph."""
        return graph.modularity(membership, weights="weight")

    def compute_nmi(self, membership: list, party_labels: list = None) -> float:
        """Computes Normalized Mutual Information between a community
        assignment and party labels (defaults to self.graph.vs['party'])."""
        if party_labels is None:
            party_labels = self.graph.vs["party"]
        return normalized_mutual_info_score(
            party_labels, membership, average_method="arithmetic"
        )

    # ------------------------------------------------------------------
    # Resolution profile (used for best-case artifact generation)
    # ------------------------------------------------------------------

    def generate_resolution_profile_data(self, res_range=(0.01, 5.0),
                                         graph: ig.Graph = None) -> Tuple[List[float], List[int]]:
        """Executes a bisection sweep and extracts coordinates for step-plotting."""
        if graph is None:
            graph = self.graph

        optimiser = la.Optimiser()
        profile = optimiser.resolution_profile(
            graph,
            la.RBConfigurationVertexPartition,
            resolution_range=res_range,
        )

        gammas = []
        n_communities = []

        for i in range(len(profile) - 1):
            start_gamma = profile[i].resolution_parameter
            end_gamma = profile[i + 1].resolution_parameter
            n_comm = len(profile[i])
            gammas.extend([start_gamma, end_gamma])
            n_communities.extend([n_comm, n_comm])

        return gammas, n_communities

    def generate_final_partition(self, gamma: float) -> la.VertexPartition:
        """Generates the final partition using the selected resolution parameter."""
        return la.find_partition(
            self.graph,
            la.RBConfigurationVertexPartition,
            resolution_parameter=gamma,
            weights="weight",
            seed=self.seed,
        )
