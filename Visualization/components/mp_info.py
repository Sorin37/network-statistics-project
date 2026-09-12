from dash import html, dcc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def render(mp_data, parties_dict):

    return html.Div([
        html.H2("Total number of MPs: " + str(len(mp_data))),
        parties_bar_chart(mp_data, parties_dict),
        political_compass(mp_data, parties_dict),
    ])


def parties_bar_chart(mp_data, parties_dict):
    counts = {"Independent": 0}

    for mp in mp_data:
        if mp["PartyID"] in parties_dict:
            party_name = parties_dict[mp["PartyID"]]["Name"]

            if party_name in counts:
                counts[party_name] += 1
            else:
                counts[party_name] = 1
        else:
            counts["Independent"] += 1

    # Sort by number of MPs, highest first
    counts = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))

    fig = px.bar(
        x=list(counts.keys()),
        y=list(counts.values()),
        labels={
            "x": "Party",
            "y": "Number of MPs"
        },
        title="MPs by Party",
    )

    fig.update_traces(
        marker_color=[
            "green" if party == "Independent" else '#636EFA'
            for party in counts.keys()
        ]
    )

    return dcc.Graph(figure=fig)


def political_compass(mp_data, parties_dict):
    counts = {}

    for mp in mp_data:
        if mp["PartyID"] in parties_dict:
            party_name = parties_dict[mp["PartyID"]]["Name"]

            if party_name in counts:
                counts[party_name]["count"] += 1
            else:
                counts[party_name] = {}
                counts[party_name]["count"] = 1
                counts[party_name]["x"] = float(parties_dict[mp["PartyID"]]["x"])
                counts[party_name]["y"] = float(parties_dict[mp["PartyID"]]["y"])

    for k, v in counts.items():
        v["dot_size"] = np.sqrt(v["count"]) * 50

    df = pd.DataFrame.from_dict(counts, orient="index")
    df.index.name = "party"
    df = df.reset_index()

    fig = px.scatter(
        df,
        x="x",
        y="y",
        size="dot_size",
        color="party",
        size_max=40,
        hover_name="party",
        hover_data={
            "x": True,
            "y": True,
            "count": True,
        },
        labels={
            "count": "Number of MPs"
        },
        title="Political Compass"
    )

    # Center at (0, 0)
    fig.update_xaxes(
        zeroline=True,
        zerolinewidth=2,
        range=[-10, 10]
    )

    fig.update_yaxes(
        zeroline=True,
        zerolinewidth=2,
        range=[-10, 10],
        scaleanchor="x",
        scaleratio=1
    )

    # Vertical axis
    fig.add_shape(
        type="line",
        x0=0, x1=0,
        y0=-1, y1=1,
        line=dict(width=1)
    )

    # Horizontal axis
    fig.add_shape(
        type="line",
        x0=-1, x1=1,
        y0=0, y1=0,
        line=dict(width=1)
    )

    fig.update_layout(
        title="Political Compass",
        showlegend=False,

        xaxis=dict(
            range=[-1.2, 1.2],
            showticklabels=False,
            zeroline=False
        ),

        yaxis=dict(
            range=[-1.2, 1.2],
            showticklabels=False,
            zeroline=False
        ),

        annotations=[
            dict(x=-1.1, y=0, text="Left", showarrow=False),
            dict(x=1.1, y=0, text="Right", showarrow=False),
            dict(x=0, y=1.1, text="Progressive", showarrow=False),
            dict(x=0, y=-1.1, text="Conservative", showarrow=False)
        ],

        width=700,
        height=700
    )

    return dcc.Graph(figure=fig)