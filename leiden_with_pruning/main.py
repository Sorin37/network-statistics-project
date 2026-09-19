import logging
from pathlib import Path

from community_pipeline import LeidenCommunityPipeline
from reporting import CommunityReporter
from edge_pruning import EdgePruningExperiment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    pipeline = LeidenCommunityPipeline("political_network_clean_lcc.gml")

    logger.info("Running edge pruning experiment...")
    experiment = EdgePruningExperiment(pipeline, artifacts_dir)
    pruning_results = experiment.run()

    # Full-graph resolution profile (computed once, shared by both best cases).
    full_gammas, full_n_comms = pipeline.generate_resolution_profile_data(
        graph=pipeline.graph,
    )

    best_cases = [
        ("best_nmi", pruning_results["nmi"].idxmax()),
        ("best_modularity", pruning_results["modularity"].idxmax()),
    ]

    # Every artifact is rendered on the full (unpruned) graph so the topology
    # and labels stay intact, using the community assignment found on the
    # pruned network.
    for label, row_index in best_cases:
        row = pruning_results.loc[row_index]
        pct, gamma = float(row["pruning_pct"]), float(row["gamma"])
        logger.info(
            "Generating artifacts for %s (pruning=%.1f%%, gamma=%.4f, "
            "modularity=%.4f, nmi=%.4f)",
            label, pct, gamma, row["modularity"], row["nmi"],
        )

        pruned = pipeline.pruned_graph_for(pct)
        partition = pipeline.find_partition(pruned, gamma)

        reporter = CommunityReporter(
            pipeline.graph, partition.membership, artifacts_dir,
            file_prefix=f"_{label}",
        )

        reporter.export_mapping_table()
        reporter.export_purity_matrix()
        reporter.plot_resolution_profile(full_gammas, full_n_comms)
        reporter.plot_network_graph()
        reporter.plot_party_stacked_bar()
        reporter.plot_sankey_diagram()

        label_nmi = reporter.calculate_nmi()
        logger.info(
            "Saved %s artifacts to artifacts/ "
            "(reported NMI on full graph with pruned partition: %.4f)",
            label, label_nmi,
        )

    logger.info("Pipeline execution complete. Check the /artifacts directory.")
