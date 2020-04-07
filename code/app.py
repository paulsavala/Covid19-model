import pandas

import dash
import dash_html_components as html
from dash.dependencies import Input, Output

from plotly import graph_objects as go
from plotly.subplots import make_subplots

from models.seir import SeirCovidModel
from widgets.models import SeirModelWidget

# ##########################################
# ################## APP ###################
# ##########################################

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Initialize the SEIR model
seir_model = SeirCovidModel(pop_size=10000, num_weeks=52, start_date=pandas.to_datetime('3/11/2020').date())
seir_model_view = SeirModelWidget(name='SeirModelView', model=seir_model, title='Covid-19 SEIR Model [K-T-L-G]')

# Build the layout
app.layout = html.Div(children=[
    html.Div(id='seir-model', children=[
        seir_model_view.header(),
        seir_model_view.sliders(),
        seir_model_view.graph()
    ])
])

# ##########################################
# ############### CALLBACKS ################
# ##########################################

# SEIR
tunable_params = [p for p in seir_model.params if not p.is_constant]
param_names = [p.name for p in tunable_params] + ['prevalence']


@app.callback(
    Output(f'{seir_model_view.name}-graph', 'figure'),
    [Input(f'{seir_model_view.name}-{p.name}-slider', 'value') for p in tunable_params]
    + [Input(f'{seir_model_view.name}-prevalence-checkbox', 'value')]
)
def update_seir_graph(*params):
    params_dict = dict(zip(param_names, params))
    for k, v in params_dict.items():
        if hasattr(seir_model, k):
            setattr(seir_model, k, v)

    S, E, I_R, I_H, I_C, R_R, H_H, H_C, R_H, C_C, R_C = seir_model.solve()
    if not params_dict['prevalence']:
        S = S / seir_model.pop_size
        E = E / seir_model.pop_size
        I_R = I_R / seir_model.pop_size
        I_H = I_H / seir_model.pop_size
        I_C = I_C / seir_model.pop_size
        R_R = R_R / seir_model.pop_size
        H_H = H_H / seir_model.pop_size
        H_C = H_C / seir_model.pop_size
        R_H = R_H / seir_model.pop_size
        C_C = C_C / seir_model.pop_size
        R_C = R_C / seir_model.pop_size
        primary_y_title = 'Percent of population'
    else:
        primary_y_title = f'Prevalence per {seir_model.pop_size}'

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(go.Scatter(x=seir_model.t_weeks,
                                y=I_C + H_C + C_C,
                                mode='lines',
                                name='Critical',
                                line={'color': 'red',
                                      'dash': 'dash'}),
                     secondary_y=True)
    figure.add_trace(go.Scatter(x=seir_model.t_weeks,
                                y=I_R + I_H + I_C,
                                mode='lines',
                                name='Infected',
                                line={'color': 'red'})
                     ),
    # figure.add_trace(go.Scatter(x=seir_model.t_weeks,
    #                             y=E,
    #                             mode='lines',
    #                             name='Exposed',
    #                             line={'color': 'blue'})
    #                  )

    figure.update_layout(
        shapes=[
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
        ]
    )

    figure.update_yaxes(title_text=primary_y_title,
                        secondary_y=False,
                        showgrid=False,
                        zerolinecolor='black')
    figure.update_yaxes(title_text=f"{primary_y_title} (critical)",
                        secondary_y=True,
                        showgrid=False,
                        zerolinecolor='black')
    figure.update_xaxes(title_text='Weeks',
                        showgrid=True,
                        gridcolor='gray',
                        zerolinecolor='black')

    figure.update_layout(plot_bgcolor='white')

    return figure


if __name__ == '__main__':
    app.run_server(debug=True)
