import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import html
from sklearn.metrics import normalized_mutual_info_score
import igraph as ig


class CommunityReporter:
    def __init__(self, graph, membership: list, artifacts_dir: Path):
        self.graph = graph
        self.membership = membership
        self.artifacts_dir = artifacts_dir
        
        self.df = pd.DataFrame({
            "MP_ID": self.graph.vs["label"],
            "Name": [html.unescape(name) for name in self.graph.vs["name"]],
            "Actual_Party": self.graph.vs["party"],
            "Leiden_Community": self.membership
        })

    def export_mapping_table(self):
        """Saves the granular MP mapping table."""
        out_path = self.artifacts_dir / "mp_community_mapping.csv"
        self.df.to_csv(out_path, index=False)

    def export_purity_matrix(self):
        """Calculates and saves the analytical Purity Matrix."""
        matrix = self.df.groupby(['Leiden_Community', 'Actual_Party']).size().reset_index(name='Count')
        matrix = matrix.sort_values(['Leiden_Community', 'Count'], ascending=[True, False])
        
        purity_data = []
        for comm, group in matrix.groupby('Leiden_Community'):
            total_mps = group['Count'].sum()
            dominant_row = group.iloc[0]
            dominant_party = dominant_row['Actual_Party']
            dominant_count = dominant_row['Count']
            purity = (dominant_count / total_mps) * 100
            
            purity_data.append({
                "Leiden_Community": comm,
                "Total_MPs": total_mps,
                "Dominant_Party": dominant_party,
                "Dominant_Party_Count": dominant_count,
                "Purity_Score_Pct": round(purity, 2)
            })
            
        purity_df = pd.DataFrame(purity_data)
        out_path = self.artifacts_dir / "community_purity_matrix.csv"
        purity_df.to_csv(out_path, index=False)

    def plot_resolution_profile(self, gammas: list, n_communities: list):
        """Generates an interactive step-plot of the resolution profile."""
        fig = go.Figure(data=go.Scatter(
            x=gammas, 
            y=n_communities, 
            mode='lines',
            line=dict(color='blue', width=2),
            line_shape='hv',
            fill='tozeroy',
            fillcolor='rgba(0, 0, 255, 0.1)'
        ))
        
        fig.update_layout(
            title="Resolution Profile: Community Fragmentation",
            xaxis_title="Resolution Parameter (Gamma)",
            yaxis_title="Number of Detected Communities",
            hovermode="x unified",
            template="plotly_white"
        )
        
        out_path = self.artifacts_dir / "resolution_profile.html"
        fig.write_html(str(out_path))

    def plot_network_graph(self):
        """Generates the interactive network topology with visible co-sponsorship edges."""
        layout = self.graph.layout_fruchterman_reingold(weights="weight")
        
        edge_x, edge_y = [], []
        for edge in self.graph.es:
            x0, y0 = layout[edge.source]
            x1, y1 = layout[edge.target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, 
            mode='lines', 
            line=dict(width=0.5, color='rgba(150, 150, 150, 0.4)'), 
            hoverinfo='none'
        )

        node_x = [loc[0] for loc in layout]
        node_y = [loc[1] for loc in layout]
        
        node_trace = go.Scatter(
            x=node_x, y=node_y, 
            mode='markers',
            marker=dict(
                size=12,
                color=self.df['Leiden_Community'],
                colorscale='Turbo', 
                line=dict(width=1, color='black'),
                showscale=False
            ),
            text=self.df['Name'] + " (" + self.df['Actual_Party'] + ")<br>Community: " + self.df['Leiden_Community'].astype(str),
            hoverinfo='text'
        )
        
        net_fig = go.Figure(data=[edge_trace, node_trace],
                            layout=go.Layout(
                                title='Dutch MP Collaboration Network (Colored by Leiden Community)',
                                showlegend=False,
                                hovermode='closest',
                                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                plot_bgcolor='white'
                            ))
        
        out_path = self.artifacts_dir / "network_graph_with_edges.html"
        net_fig.write_html(str(out_path))

    def plot_sankey_diagram(self):
        """Generates a structural flow diagram mapping Leiden communities to formal parties."""
        flow_df = self.df.groupby(['Leiden_Community', 'Actual_Party']).size().reset_index(name='Count')
        
        comm_labels = ["Community " + str(c) for c in sorted(self.df['Leiden_Community'].unique())]
        party_labels = sorted(self.df['Actual_Party'].unique().tolist())
        all_labels = comm_labels + party_labels
        
        label_map = {label: i for i, label in enumerate(all_labels)}
        
        sources = [label_map["Community " + str(c)] for c in flow_df['Leiden_Community']]
        targets = [label_map[p] for p in flow_df['Actual_Party']]
        values = flow_df['Count'].tolist()
        
        sankey_fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_labels,
                color="rgba(31, 119, 180, 0.8)"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color="rgba(180, 180, 180, 0.4)"
            )
        )])
        
        sankey_fig.update_layout(
            title_text="Structural Flow: Leiden Communities vs. Formal Political Parties", 
            font_size=12
        )
        
        out_path = self.artifacts_dir / "sankey_diagram.html"
        sankey_fig.write_html(str(out_path))

    def calculate_nmi(self) -> float:
        """Calculates and logs the Normalized Mutual Information (NMI)."""
        nmi_score = normalized_mutual_info_score(
            self.df['Actual_Party'], 
            self.df['Leiden_Community'], 
            average_method='arithmetic'
        )
            
        return nmi_score

    def compute_modularity(self, graph: ig.Graph, membership) -> float:
        """Computes modularity of the given membership on the given graph."""
        return graph.modularity(membership=membership, weights="weight")