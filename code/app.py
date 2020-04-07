import pandas
import numpy as np

import dash
import dash_html_components as html
from dash.dependencies import Input, Output, State

import dash_bootstrap_components as dbc

from plotly import graph_objects as go
from plotly.subplots import make_subplots

from models.seir import SeirCovidModel
from widgets.models import SeirModelWidget

# ##########################################
# ################## APP ###################
# ##########################################

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Initialize the SEIR model
seir_model = SeirCovidModel(pop_size=10000, num_weeks=52, start_date=pandas.to_datetime('3/11/2020').date())
seir_model_view = SeirModelWidget(name='SeirModelView', model=seir_model, title='Covid-19 SEIR Model [K-T-L-G]')

# Create the app
app.layout = dbc.Container(
    [
        seir_model_view.header(),
        html.Hr(),
        dbc.Row([dbc.Col(seir_model_view.graph(), align='center')]),
        dbc.Row([dbc.Col(seir_model_view.sliders()['social_distancing'])]),
        dbc.Row([dbc.Col(seir_model_view.sliders()['advanced'])]),
        seir_model_view.footer()
    ],
    fluid=True
)

# ##########################################
# ############### CALLBACKS ################
# ##########################################

# SEIR
tunable_params = [p for p in seir_model.params if not p.is_constant]
param_names = [p.name for p in tunable_params] + ['prevalence']


@app.callback(
    Output(f'{seir_model_view.name}-graph', 'figure'),
    [Input(f'{seir_model_view.name}-{p.name}-slider', 'value') for p in tunable_params]
)
def update_seir_graph(*params):
    params_dict = dict(zip(param_names, params))
    for k, v in params_dict.items():
        if hasattr(seir_model, k):
            setattr(seir_model, k, v)

    S, E, I_R, I_H, I_C, R_R, H_H, H_C, R_H, C_C, R_C = seir_model.solve()
    total_infected = I_R + I_H + I_C
    total_critical = I_C + H_C + C_C

    max_infected_index = np.where(total_infected == max(total_infected))[0][0]
    max_infected_value = total_infected[max_infected_index]
    num_infected = sum(total_infected)

    max_critical_index = np.where(total_critical == max(total_critical))[0][0]
    max_critical_value = total_critical[max_critical_index]
    num_critical = sum(total_critical)

    primary_y_title = f'Prevalence per {seir_model.pop_size}'

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(go.Scatter(x=seir_model.t_weeks,
                                y=total_infected,
                                mode='lines',
                                name='Infected',
                                line={'color': 'blue'},
                                fill='tozeroy')
                     )
    figure.add_trace(go.Scatter(x=seir_model.t_weeks,
                                y=total_critical,
                                mode='lines',
                                name='Critical',
                                line={'color': 'red',
                                      'dash': 'dash'},
                                fill='tozeroy'),
                     secondary_y=True
                     )

    figure.update_layout(
        shapes=[
            # Shade the fixed social distancing
            dict(
                type="rect",
                # x-reference is assigned to the x-values
                xref="x",
                # y-reference is assigned to the plot paper [0,1]
                yref="paper",
                x0=seir_model.t_weeks[seir_model.start_sd],
                y0=0,
                x1=seir_model.t_weeks[seir_model.start_sd + seir_model.sd_duration],
                y1=1,
                fillcolor=f"rgba(0,0,255,{seir_model.sd_reduction})",
                opacity=0.3,
                layer="below",
                line_width=0,
            )
        ],
        annotations=[
            # Annotate the infected cases
            dict(
                xref="x",
                yref="y",
                x=seir_model.t_weeks[max_infected_index + 6],
                y=0.9*max_infected_value,
                text=f'{int(np.round(num_infected, 0))} infected in total',
                showarrow=False,
                bgcolor='rgba(255,255,255,1)',
                bordercolor='blue'
            ),
            # Annotate the critical cases
            dict(
                xref="x",
                yref="y2",
                x=seir_model.t_weeks[max_critical_index + 6],
                y=0.9 * max_critical_value,
                text=f'{int(np.round(num_critical, 0))} critical in total',
                showarrow=False,
                bgcolor='rgba(255,255,255,1)',
                bordercolor='red'
            )
        ]
    )

    figure.update_yaxes(title_text=primary_y_title,
                        secondary_y=False,
                        showgrid=False,
                        zerolinecolor='black',
                        range=[0, max([1.1*(max(I_R + I_H + I_C)), 1000])])
    figure.update_yaxes(title_text=f"{primary_y_title} (critical)",
                        secondary_y=True,
                        showgrid=False,
                        zerolinecolor='black',
                        range=[0, max([1.1*(max(I_C + H_C + C_C)), 100])])
    figure.update_xaxes(title_text='Weeks',
                        showgrid=True,
                        gridcolor='gray',
                        zerolinecolor='black')

    figure.update_layout(plot_bgcolor='white')

    return figure


@app.callback(
    Output(f"{seir_model_view.name}-advanced-collapse", "is_open"),
    [Input(f"{seir_model_view.name}-advanced-collapse-button", "n_clicks")],
    [State(f"{seir_model_view.name}-advanced-collapse", "is_open")],
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == '__main__':
    app.run_server(debug=True)
