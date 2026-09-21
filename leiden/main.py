import sys
import logging
import leidenalg as la
from pathlib import Path
from community_pipeline import LeidenCommunityPipeline
from reporting import CommunityReporter
import igraph as ig


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    logger.info("Initializing Leiden Community Pipeline...")
    pipeline = LeidenCommunityPipeline("political_network_clean_full.gml")
    pipeline.load_network()

    graph = ig.Graph.Read_GML("political_network_clean_full.gml")

    logger.info("Generating resolution profile data for visual inspection...")
    gammas, n_comms = pipeline.generate_resolution_profile_data()
    
    dummy_membership = [-1] * pipeline.graph.vcount()
    temp_reporter = CommunityReporter(pipeline.graph, dummy_membership, artifacts_dir)
    temp_reporter.plot_resolution_profile(gammas, n_comms)
    logger.info("Saved resolution profile plot to artifacts/resolution_profile.html")

    # Set optimal gamma based on the community plateau identified in the resolution profile plot
    optimal_gamma = 1
    logger.info(f"Using selected gamma: Gamma = {optimal_gamma}")

    # Generate the final partition using the selected resolution
    logger.info("Generating the final community partition...")
    final_partition = pipeline.generate_final_partition(optimal_gamma)
    
    logger.info(f"Partition complete. Detected {len(final_partition)} distinct communities.")

    modularity_score = temp_reporter.compute_modularity(graph, final_partition.membership)

    logger.info(f"Modularity score: {modularity_score}")

    # Export artifacts
    logger.info("Exporting mapping tables, purity matrix, and visualizations...")
    reporter = CommunityReporter(pipeline.graph, final_partition.membership, artifacts_dir)
    
    reporter.export_mapping_table()
    reporter.export_purity_matrix()
    
    logger.info("Generating network scatter and Sankey diagram...")
    reporter.plot_network_graph()
    reporter.plot_sankey_diagram()

    # Normalized Mutual Information (NMI) Score
    nmi_score = reporter.calculate_nmi()
    logger.info(f"Final NMI Score (Leiden vs. Actual Parties): {nmi_score:.4f}")

    logger.info("Pipeline execution complete. Check the /artifacts directory.")