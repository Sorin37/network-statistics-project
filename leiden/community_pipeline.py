import igraph as ig
import leidenalg as la
from typing import List, Tuple

class LeidenCommunityPipeline:
    def __init__(self, gml_path: str):
        self.gml_path = gml_path
        self.graph = None

    def load_network(self) -> None:
        """Loads the cleaned connected component graph."""
        self.graph = ig.Graph.Read_GML(self.gml_path)

    def generate_resolution_profile_data(self, res_range=(0.01, 5.0)) -> Tuple[List[float], List[int]]:
        """Executes a bisection sweep and extracts coordinates for step-plotting."""
        optimiser = la.Optimiser()
        profile = optimiser.resolution_profile(
            self.graph, 
            la.RBConfigurationVertexPartition, 
            resolution_range=res_range
        )
        
        gammas = []
        n_communities = []
        
        for i in range(len(profile) - 1):
            start_gamma = profile[i].resolution_parameter
            end_gamma = profile[i+1].resolution_parameter
            n_comm = len(profile[i])
            
            gammas.extend([start_gamma, end_gamma])
            n_communities.extend([n_comm, n_comm])
            
        return gammas, n_communities

    def generate_final_partition(self, gamma: float) -> la.VertexPartition:
        """Generates the final partition using the selected resolution parameter."""
        final_partition = la.find_partition(
            self.graph, 
            la.RBConfigurationVertexPartition, 
            resolution_parameter=gamma, 
            weights='weight',
            seed=42 # Fix seed for output reproducibility 
        )
        return final_partition

