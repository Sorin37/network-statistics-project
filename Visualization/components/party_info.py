from dash import html

def render(mp_data, parties_dict):
    parties = list(parties_dict.keys())

    for mp in mp_data:
        if mp["PartyID"] not in parties:
            continue
        else:
            parties.remove(mp["PartyID"])

    return html.Div([
        html.H2("Total number of parties: " + str(len(parties_dict))),
        html.H2("Number of parties that have no MPs: " + str(len(parties))),
    ])