import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output


def create_figure(G, mp_dict, parties_data, selected_mp=None):

    # Calculate node positions
    pos = nx.spring_layout(
        G,
        seed=42,
        method="energy",
        gravity=1.0
    )

    # Party colors
    party_colors = {}
    colors = px.colors.qualitative.Set3

    # Edges
    normal_edge_x = []
    normal_edge_y = []

    faded_edge_x = []
    faded_edge_y = []

    # Invisible hover points along selected edges
    hover_edge_x = []
    hover_edge_y = []
    hover_edge_text = []

    for u, v, data in G.edges(data=True):

        x0, y0 = pos[u]
        x1, y1 = pos[v]

        weight = data.get("weight", 1)

        # No MP selected
        if selected_mp is None:

            normal_edge_x += [x0, x1, None]
            normal_edge_y += [y0, y1, None]

        else:

            u_mp = mp_dict.get(u)
            v_mp = mp_dict.get(v)

            connected_to_selected = (
                (u_mp and u_mp["MP"] == selected_mp) or
                (v_mp and v_mp["MP"] == selected_mp)
            )

            if connected_to_selected:

                # Draw the visible edge
                normal_edge_x += [x0, x1, None]
                normal_edge_y += [y0, y1, None]

                # Create invisible hover points all along the edge
                number_of_points = 30

                for i in range(number_of_points + 1):

                    t = i / number_of_points

                    x = x0 + t * (x1 - x0)
                    y = y0 + t * (y1 - y0)

                    hover_edge_x.append(x)
                    hover_edge_y.append(y)
                    hover_edge_text.append(f"Weight: {weight}")

            else:

                # Draw faded edge
                faded_edge_x += [x0, x1, None]
                faded_edge_y += [y0, y1, None]

    # Faded edges
    faded_edge_trace = go.Scatter(
        x=faded_edge_x,
        y=faded_edge_y,
        mode="lines",
        line=dict(
            width=0.5,
            color="blue"
        ),
        opacity=0.15,
        hoverinfo="skip",
        showlegend=False
    )

    # Highlighted edges
    normal_edge_trace = go.Scatter(
        x=normal_edge_x,
        y=normal_edge_y,
        mode="lines",
        line=dict(
            width=1.5,
            color="blue"
        ),
        opacity=1.0,
        hoverinfo="skip",
        showlegend=False
    )

    # Invisible hover points covering the whole edge
    hover_edge_trace = go.Scatter(
        x=hover_edge_x,
        y=hover_edge_y,
        mode="markers",
        marker=dict(
            size=10,
            opacity=0
        ),
        text=hover_edge_text,
        hoverinfo="text",
        showlegend=False
    )

    # Nodes
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []
    node_opacities = []

    for node in G.nodes():

        x, y = pos[node]

        node_x.append(x)
        node_y.append(y)

        mp = mp_dict.get(node)

        if mp:

            mp_name = mp["MP"]
            party_id = mp["PartyID"]

            party = parties_data.get(party_id)

            if party:
                party_name = party["Name"]
            else:
                party_name = "Independent"

            # Assign party color
            if party_id not in party_colors:
                party_colors[party_id] = colors[
                    len(party_colors) % len(colors)
                ]

            party_color = party_colors[party_id]

            # Selected MP
            if mp_name == selected_mp:

                node_colors.append(party_color)
                node_sizes.append(20)
                node_opacities.append(1.0)

            else:

                node_colors.append(party_color)
                node_sizes.append(8)

                if selected_mp is None:
                    node_opacities.append(1.0)
                else:
                    node_opacities.append(0.4)

            node_text.append(
                f"MP: {mp_name}<br>"
                f"Party: {party_name}"
            )

        else:

            node_colors.append("gray")
            node_sizes.append(8)
            node_opacities.append(1.0)
            node_text.append("Unknown MP")

    # Node trace
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        text=node_text,
        hoverinfo="text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            opacity=node_opacities
        ),
        showlegend=False
    )

    # Figure
    fig = go.Figure(
        data=[
            faded_edge_trace,
            normal_edge_trace,
            hover_edge_trace,
            node_trace
        ],
        layout=go.Layout(
            title="Graph",
            showlegend=False,
            hovermode="closest",
            margin=dict(
                b=0,
                l=0,
                r=0,
                t=40
            ),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False
            )
        )
    )

    return fig


def get_weight_sum(G, mp_dict, selected_mp):

    if selected_mp is None:
        return ""

    total_weight = 0

    for u, v, data in G.edges(data=True):

        u_mp = mp_dict.get(u)
        v_mp = mp_dict.get(v)

        connected_to_selected = (
            (u_mp and u_mp["MP"] == selected_mp) or
            (v_mp and v_mp["MP"] == selected_mp)
        )

        if connected_to_selected:
            total_weight += data.get("weight", 1)

    return f"Total number of motions for the selected MP: {total_weight}"


def render(G, mp_dict, parties_data):

    mp_options = [
        {
            "label": mp["MP"],
            "value": mp["MP"]
        }
        for mp in mp_dict.values()
    ]

    return html.Div([

        dcc.Dropdown(
            id="mp-dropdown",
            options=mp_options,
            placeholder="Select an MP...",
            clearable=True
        ),

        html.Div(
            id="weight-sum",
            style={
                "marginTop": "10px",
                "marginBottom": "10px",
                "fontSize": "18px"
            }
        ),

        dcc.Graph(
            id="graph",
            figure=create_figure(
                G,
                mp_dict,
                parties_data
            ),
            style={"height": "90vh"}
        )
    ])


