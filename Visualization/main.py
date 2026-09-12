from dash import Dash, html, dcc, Input, Output
from components import mp_info, party_info, graph_info
import json
import networkx as nx


app = Dash(__name__, suppress_callback_exceptions=True)


# Load data
mp_data = []

with open("data/MP.json", "r") as f:
    data = json.load(f)
    mp_dict = data

    for key, value in data.items():
        value["Id"] = key
        mp_data.append(value)


with open("data/Party.json", "r") as f:
    parties_dict = json.load(f)


G = nx.read_gml("data/political_network.gml")


app.layout = html.Div([

    dcc.Tabs(
        id="tabs",
        value="tab-1",
        children=[
            dcc.Tab(label="MP Info", value="tab-1"),
            dcc.Tab(label="Party Info", value="tab-2"),
            dcc.Tab(label="Graph Info", value="tab-3"),
        ]
    ),

    html.Div(id="tab-content")
])


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value")
)
def render_tab(tab):

    if tab == "tab-1":
        return mp_info.render(
            mp_data,
            parties_dict
        )

    elif tab == "tab-2":
        return party_info.render(
            mp_data,
            parties_dict
        )

    elif tab == "tab-3":
        return graph_info.render(
            G,
            mp_dict,
            parties_dict
        )


@app.callback(
    Output("graph", "figure"),
    Output("weight-sum", "children"),
    Input("mp-dropdown", "value")
)
def update_graph(selected_mp):

    figure = graph_info.create_figure(
        G,
        mp_dict,
        parties_dict,
        selected_mp
    )

    weight_sum = graph_info.get_weight_sum(
        G,
        mp_dict,
        selected_mp
    )

    return figure, weight_sum


if __name__ == "__main__":
    app.run(debug=True)