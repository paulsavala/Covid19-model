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
        html.Div(seir_model_view.main_text()),
        dbc.Row([dbc.Col(seir_model_view.graph(), align='center')]),
        seir_model_view.sd_switches(),
        dbc.Row([dbc.Col(seir_model_view.sliders()['static_social_distancing'])]),
        dbc.Row([dbc.Col(seir_model_view.sliders()['advanced'])])
    ],
    fluid=True
)

# ##########################################
# ############### CALLBACKS ################
# ##########################################

# SEIR
tunable_params = [p for p in seir_model.params if not p.is_constant]
param_names = [p.name for p in tunable_params]


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

    max_critical_index = np.where(total_critical == max(total_critical))[0][0]
    max_critical_value = total_critical[max_critical_index]
    critical_above_capacity = np.sum(total_critical > 0.89)
    avg_needed_beds = np.round(np.average(total_critical[np.where(total_critical > 0.89)]), 1)

    primary_y_title = f'Prevalence per {seir_model.pop_size}'

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

    figure.update_layout(
        shapes=[
            # Shade the fixed social distancing
            dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=seir_model.t_weeks[seir_model.start_sd],
                y0=0,
                x1=seir_model.t_weeks[seir_model.start_sd + seir_model.sd_duration],
                y1=1,
                fillcolor=f"rgba(0,255,0,{seir_model.sd_reduction})",
                opacity=0.3,
                layer="below",
                line_width=0
            ),
            # Critical care capacity
            dict(
                type='line',
                xref='paper',
                yref='y2',
                x0=0,
                y0=0.89,
                x1=1,
                y1=0.89,
                line=dict(
                    color='black',
                    width=3,
                    dash='dot'
                )
            )
        ],
        annotations=[
            # Annotate the critical cases
            dict(
                xref="x",
                yref="y2",
                x=seir_model.t_weeks[max_critical_index + 6],
                y=0.9 * max_critical_value,
                text=f'{critical_above_capacity} days above critical care open bed capacity',
                showarrow=False,
                bgcolor='rgba(255,255,255,1)',
                bordercolor='red'
            ),
            # Annotate the avg number of beds needed
            dict(
                xref="x",
                yref="y2",
                x=seir_model.t_weeks[max_critical_index + 6],
                y=0.7 * max_critical_value,
                text=f'Average shortage of {avg_needed_beds} beds per 10,000 people',
                showarrow=False,
                bgcolor='rgba(255,255,255,1)',
                bordercolor='red'
            ),
            # Annotate the social distancing period
            dict(
                xref="x",
                yref="paper",
                x=seir_model.t_weeks[int((seir_model.start_sd + seir_model.sd_duration)/2)],
                y=1.1,
                text=f'Social distancing from {seir_model.t_weeks[seir_model.static_sd]} to '
                     f'{seir_model.t_weeks[seir_model.static_sd + seir_model.sd_duration]}',
                showarrow=False,
                bgcolor='rgba(255,255,255,1)',
                bordercolor='green'
            ),
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
                        range=[0, max([1.1*(max(I_C + H_C + C_C)), 60])])
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
def toggle_advanced_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output(f'{seir_model_view.name}-static_social_distancing-collapse', 'is_open'),
    [Input(f'{seir_model_view.name}-social_distancing-switches-input', 'value')]
)
def toggle_sd_method(value):
    if value == ['static']:
        seir_model.static_sd = True
        return True


if __name__ == '__main__':
    app.run_server(debug=True)
