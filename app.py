import os
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
server = app.server

# Initialize the SEIR model
seir_model = SeirCovidModel(pop_size=10000, num_weeks=2*52, start_date=pandas.to_datetime('3/11/2020').date())
seir_model_view = SeirModelWidget(name='SeirModelView', model=seir_model, title='Covid-19 SEIR Model [K-T-L-G]')

# Create the app
app.layout = dbc.Container(
    [
        seir_model_view.header(),
        html.Hr(),
        html.Div(seir_model_view.main_text()),
        dbc.Row([dbc.Col(seir_model_view.graph(), align='center')]),
        seir_model_view.sd_switches(),
        dbc.Row([dbc.Col(seir_model_view.sliders()['static_social_distancing'])]),
        dbc.Row([dbc.Col(seir_model_view.sliders()['dynamic_social_distancing'])]),
        dbc.Row([dbc.Col(seir_model_view.sliders()['advanced'])]),
        seir_model_view.footer()
    ],
    fluid=True
)

app.title = 'Social distancing and COVID-19'

# ##########################################
# ############### CALLBACKS ################
# ##########################################

# SEIR
tunable_params = [p for p in seir_model.params if not p.is_constant]
param_names = [p.name for p in tunable_params] + ['sd_switches']


@app.callback(
    Output(f'{seir_model_view.name}-graph', 'figure'),
    [Input(f'{seir_model_view.name}-{p.name}-slider', 'value') for p in tunable_params] +
    [Input(f'{seir_model_view.name}-social_distancing-switches-input', 'value')]
)
def update_seir_graph(*params):
    params_dict = dict(zip(param_names, params))
    for k, v in params_dict.items():
        if hasattr(seir_model, k):
            setattr(seir_model, k, v)

    S, E, I_R, I_H, I_C, R_R, H_H, H_C, R_H, C_C, R_C = seir_model.solve()
    total_infected = I_R + I_H + I_C
    total_critical = I_C + H_C + C_C

    max_critical_index = np.where(total_critical == max(total_critical))[0][0]
    max_critical_value = total_critical[max_critical_index]
    critical_above_capacity = np.sum(total_critical > 0.89)
    avg_needed_beds = np.round(np.average(total_critical[np.where(total_critical > 0.89)]), 1)

    primary_y_title = 'Prevalence per {:,} people'.format(seir_model.pop_size)

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    # All cases
    figure.add_trace(go.Scatter(x=seir_model.t_weeks,
                                y=total_infected,
                                mode='lines',
                                name='Infected',
                                line={'color': 'blue'},
                                fill='tozeroy')
                     )
    # Critical cases
    figure.add_trace(go.Scatter(x=seir_model.t_weeks,
                                y=total_critical,
                                mode='lines',
                                name='Critical',
                                line={'color': 'red',
                                      'dash': 'dash'},
                                fill='tozeroy'),
                     secondary_y=True
                     )

    shapes = []

    annotations = [
        # Annotate the critical cases
        dict(
            xref="x",
            yref="paper",
            x=seir_model.t_weeks[min(max_critical_index + 6, len(seir_model.t_weeks) - 1)],
            y=0.75,
            text=f'{critical_above_capacity} days above critical care open bed capacity',
            showarrow=False,
            bgcolor='rgba(255,255,255,1)',
            bordercolor='red'
        ),
        # Annotate the avg number of beds needed
        dict(
            xref="x",
            yref="paper",
            x=seir_model.t_weeks[min(max_critical_index + 6, len(seir_model.t_weeks) - 1)],
            y=0.5,
            text=f'Average daily shortage of {avg_needed_beds} beds per 10,000 people',
            showarrow=False,
            bgcolor='rgba(255,255,255,1)',
            bordercolor='red'
        )
    ]

    if params_dict.get('sd_switches'):
        if 'static' in params_dict['sd_switches']:
            shapes += seir_model_view.static_sd_overlay_shape(seir_model)
            annotations += seir_model_view.static_sd_overlay_annotation(seir_model)

    figure.update_layout(shapes=shapes, annotations=annotations)

    figure.update_yaxes(title_text=primary_y_title,
                        tickfont=dict(
                            color="blue"
                        ),
                        secondary_y=False,
                        showgrid=False,
                        zerolinecolor='black',
                        range=[0, max([1.1*(max(I_R + I_H + I_C)), 1000])])
    figure.update_yaxes(title_text=f"{primary_y_title} (critical)",
                        tickfont=dict(
                            color="red"
                        ),
                        secondary_y=True,
                        showgrid=False,
                        zerolinecolor='black',
                        range=[0, max([1.1*(max(I_C + H_C + C_C)), 60])])
    figure.update_xaxes(title_text='Weeks',
                        showgrid=True,
                        gridcolor='gray',
                        zerolinecolor='black',
                        range=[seir_model.t_weeks[0], seir_model.t_weeks[-1]])

    figure.update_layout(plot_bgcolor='white')

    return figure


# Toggle the different types of social distancing
@app.callback(
    [Output(f'{seir_model_view.name}-static_social_distancing-collapse', 'is_open'),
     Output(f'{seir_model_view.name}-dynamic_social_distancing-collapse', 'is_open')],
    [Input(f'{seir_model_view.name}-social_distancing-switches-input', 'value')]
)
def toggle_sd_method(values):
    static_sd = False
    dynamic_sd = False

    static_is_open = False
    dynamic_is_open = False

    if 'static' in values:
        static_sd = True
        static_is_open = True
    if 'dynamic' in values:
        dynamic_sd = True
        dynamic_is_open = True

    seir_model.static_sd = static_sd
    seir_model.dynamic_sd = dynamic_sd

    update_seir_graph()

    return static_is_open, dynamic_is_open


# Toggle the advanced parameters
@app.callback(
    Output(f"{seir_model_view.name}-advanced-collapse", "is_open"),
    [Input(f"{seir_model_view.name}-advanced-collapse-button", "n_clicks")],
    [State(f"{seir_model_view.name}-advanced-collapse", "is_open")],
)
def toggle_advanced_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


if __name__ == '__main__':
    app.run_server(debug=False)
