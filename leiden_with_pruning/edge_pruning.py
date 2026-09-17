import logging
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from community_pipeline import LeidenCommunityPipeline

logger = logging.getLogger(__name__)


class EdgePruningExperiment:
    """Orchestrates the edge-pruning sweep by delegating pruning and
    community-detection logic to a LeidenCommunityPipeline instance.

    For every pruning level (0%, 2%, …, max_pct%) the experiment:
      1. Prunes the graph via pipeline.pruned_graph_for().
      2. Selects gamma via pipeline.select_gamma() to target a given number
         of communities.
      3. Finds a partition via pipeline.find_partition().
      4. Evaluates modularity (on the full graph) and NMI via the pipeline.

    Results are saved to edge_pruning_results.csv and a two-row plotly figure.
    """

    def __init__(self, pipeline: LeidenCommunityPipeline, artifacts_dir: Path,
                 step_pct: float = 2.0, max_pct: float = 50.0,
                 target_communities: int = 28, res_range: tuple = (0.05, 5.0)):
        self.pipeline = pipeline
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.step_pct = float(step_pct)
        self.max_pct = float(max_pct)
        self.target_communities = target_communities
        self.res_range = res_range
        self.graph = None  # set in run()

    def run(self) -> pd.DataFrame:
        """Executes the pruning sweep and returns a DataFrame of results."""
        self.pipeline.load_network()
        self.graph = self.pipeline.graph
        self.pipeline._ensure_removal_order()

        total_edges = self.graph.ecount()
        removable_count = len(self.pipeline._removal_order)
        logger.info("Total edges: %d | protected: %d | removable: %d",
                     total_edges, total_edges - removable_count, removable_count)
        logger.info("Target communities: %s | res range: %s",
                     self.target_communities, self.res_range)

        rows = []
        pct = 0.0
        while pct <= self.max_pct + 1e-9:
            pruned = self.pipeline.pruned_graph_for(pct)

            gamma, plateau_n = self.pipeline.select_gamma(
                pruned, self.target_communities, self.res_range,
            )

            partition = self.pipeline.find_partition(pruned, gamma)
            membership = partition.membership

            modularity = self.pipeline.compute_modularity(self.graph, membership)
            nmi = self.pipeline.compute_nmi(membership)

            n_remove = min(
                int(round(pct / 100.0 * total_edges)),
                removable_count,
            )
            rows.append({
                "pruning_pct": pct,
                "n_edges_removed": n_remove,
                "n_edges_remaining": pruned.ecount(),
                "gamma": gamma,
                "target_communities": self.target_communities,
                "plateau_n_communities": plateau_n,
                "n_communities": len(partition),
                "n_components": len(pruned.components()),
                "modularity": modularity,
                "nmi": nmi,
            })
            logger.info(
                "pruning_pct=%.1f%% | nodes=%d edges=%d | gamma=%.4f "
                "(plateau=%s) | comm=%d comps=%d | "
                "modularity_on_full_graph=%.4f nmi=%.4f",
                pct, pruned.vcount(), pruned.ecount(), gamma, plateau_n,
                len(partition), len(pruned.components()), modularity, nmi,
            )
            pct += self.step_pct

        results = pd.DataFrame(rows)
        results.to_csv(self.artifacts_dir / "edge_pruning_results.csv", index=False)
        logger.info("Saved results to artifacts/edge_pruning_results.csv")

        self.plot_results(results)
        return results

    def plot_results(self, results: pd.DataFrame) -> None:
        """Saves a two-row plotly figure (quality + config) to artifacts."""
        best_mod_row = results.loc[results["modularity"].idxmax()]
        best_nmi_row = results.loc[results["nmi"].idxmax()]
        quality_max = max(results["modularity"].max(), results["nmi"].max()) * 1.1

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
            row_heights=[0.55, 0.45],
            specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
            subplot_titles=(
                "Community Quality vs Pruning",
                "Selected Gamma and Community Count vs Pruning (target communities: "
                + str(self.target_communities) + ")",
            ),
        )

        fig.add_trace(go.Scatter(
            x=results["pruning_pct"], y=results["modularity"],
            mode="lines+markers", name="Modularity",
            legendgroup="quality",
            line=dict(color="blue"), marker=dict(size=7, color="blue"),
            hovertemplate="Pruning %{x:.1f}%<br>Modularity %{y:.4f}<extra></extra>",
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=results["pruning_pct"], y=results["nmi"],
            mode="lines+markers", name="NMI (vs actual parties)",
            legendgroup="quality",
            line=dict(color="green"), marker=dict(size=7, color="green"),
            hovertemplate="Pruning %{x:.1f}%<br>NMI %{y:.4f}<extra></extra>",
        ), row=1, col=1, secondary_y=True)

        fig.add_trace(go.Scatter(
            x=results["pruning_pct"], y=results["gamma"],
            mode="lines+markers", name="Selected gamma",
            legendgroup="config",
            text=[f"{g:.3f}" for g in results["gamma"]],
            textposition="top center", textfont=dict(size=9),
            line=dict(color="purple"), marker=dict(size=7, color="purple"),
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=results["pruning_pct"], y=results["n_communities"],
            mode="lines+markers", name="Number of communities",
            legendgroup="config",
            text=results["n_communities"].astype(str),
            textposition="bottom center", textfont=dict(size=9),
            line=dict(color="orange", dash="dash"), marker=dict(size=9, color="orange"),
        ), row=2, col=1, secondary_y=True)

        fig.add_vline(x=best_mod_row["pruning_pct"], line_dash="dash",
                      line_color="blue", annotation_text="best modularity")
        fig.add_vline(x=best_nmi_row["pruning_pct"], line_dash="dash",
                      line_color="green", annotation_text="best NMI")
        fig.add_hline(y=self.target_communities, line_dash="dot",
                      line_color="black", row=2, col=1)

        fig.update_yaxes(title_text="Modularity (full graph)",
                         range=[0, quality_max], row=1, col=1)
        fig.update_yaxes(title_text="NMI", range=[0, quality_max], row=1, col=1,
                         secondary_y=True)
        fig.update_yaxes(title_text="Selected gamma", row=2, col=1)
        fig.update_yaxes(title_text="Communities", row=2, col=1, secondary_y=True)
        fig.update_xaxes(title_text="Pruned Edges (%)", row=2, col=1)

        fig.update_layout(
            title=f"Edge Pruning Impact on Leiden Partition "
                  f"(gamma auto-selected for {self.target_communities} communities)",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(x=0.01, y=0.5, yanchor="middle"),
        )

        out_path = self.artifacts_dir / "edge_pruning_results.html"
        fig.write_html(str(out_path))
        logger.info("Saved plot to artifacts/edge_pruning_results.html")
