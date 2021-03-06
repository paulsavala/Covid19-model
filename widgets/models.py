import dash_core_components as dcc
import dash_html_components as html

import dash_bootstrap_components as dbc

import numpy as np
from collections import defaultdict

from utils.str import pretty_var


class GenericModelWidget:
    def __init__(self, name='', model=None, title=''):
        self.name = name
        self.model = model
        self.title = title

    def graph(self):
        graph = dcc.Graph(
            id=f'{self.name}-graph',
            figure={
                'data': None,
                'layout': {
                    'title': None
                }
            }
        )
        return graph

    def sliders(self):
        return None

    def header(self):
        return None

    def footer(self):
        return html.Div(className='page-footer mb-5')


class SeirModelWidget(GenericModelWidget):
    def header(self):
        return html.H1(children='The effects of social distancing on the spread of COVID-19')

    def main_text(self):
        main_text = dcc.Markdown(f'''
        Social distancing has an important effect on the spread of the coronavirus. Two possible social distancing
        strategies are illustrated here: static and dynamic.
        
        #### Static social distancing
        Static social distancing refers to implementing social distancing over a fixed period of time. For example, 
        social distancing could begin 4 weeks after the first case is reported, and last for 12 weeks.
        
        #### Dynamic social distancing
        Dynamic social distancing refers to "turning on and off" social distancing based on the number of cases 
        reported.
        
        #### The model
        The model shown here is based on the paper 
        ["Social distancing strategies for curbing the COVID-19 epidemic"]
        (https://www.medrxiv.org/content/10.1101/2020.03.22.20041079v1.article-info)
        by the researchers Kissler, Tedijanto, Lipsitch and Grad at Harvard. I am in no way associated with these
        researchers. For me about me, see my [LinkedIn profile](https://www.linkedin.com/in/paul-savala-ph-d-61153193/).
        
        #### How to use this app
        The graph below shows the expected number of infected people (blue), along with the expected number of critical 
        cases (red) per every 10,000 people. In order to implement different social distancing strategies, click the
        buttons for one (or both) social distancing methods. The parameters to adjust that method will then show up
        below the graph. Try adjusting them to see how infections change based on your method. 
        ''')
        return html.Div(id='main_text', children=main_text, className='mt-2')

    def sd_switches(self):
        sd_switches = dbc.FormGroup(
            [
                dbc.Label("Social distancing method(s)", className='h5'),
                dbc.Checklist(
                    options=[
                        {"label": "Static (fixed time period)", "value": 'static'},
                        {"label": "Dynamic (based on number of cases)", "value": 'dynamic'},
                    ],
                    value=['static'],
                    id=f"{self.name}-social_distancing-switches-input",
                    switch=True,
                )
            ]
        )
        return sd_switches

    def _fix_marks(self, marks, is_pct):
        # Dash bug causes certain marks to not show up.
        # Solution taken from https://github.com/plotly/dash-core-components/issues/159
        if is_pct:
            marks = {int(i) if i % 1 == 0 else i: '{}%'.format(100*np.round(i, 3)) for i in marks}
        else:
            marks = {int(i) if i % 1 == 0 else i: '{}'.format(np.round(i, 3)) for i in marks}
        return marks

    def _slider(self, param, class_name=None):
        # Make an individual pretty slider for the param
        steps = (param.max_value - param.min_value) / 10
        if param.is_int:
            steps = int(np.floor(steps))
            marks_range = range(param.min_value, param.max_value+steps, steps)
        else:
            marks_range = np.arange(param.min_value, param.max_value+steps, steps)

        slider = dcc.Slider(id=f'{self.name}-{param.name}-slider',
                            min=param.min_value,
                            max=param.max_value,
                            step=steps,
                            value=param.default_value,
                            marks=self._fix_marks(marks_range, param.is_pct),
                            className=class_name
                            )
        return slider

    def _card(self, group_name, param_groups, is_open=False):
        group_card_body = []
        group_card_header = dbc.CardHeader(f'{pretty_var(group_name)} parameters', className='h4')
        for param in param_groups.get(group_name):
            if param.show_label:
                group_card_body.append(html.Label(f'{param.desc} ({param.name}):'))
            else:
                group_card_body.append(html.Label(f'{param.desc}:'))
            group_card_body.append(self._slider(param, class_name='mb-3'))
        group_card = dbc.Card([group_card_header, dbc.CardBody(group_card_body)], id=f'{self.name}-{group_name}-card')
        collapsible_group_card = dbc.Collapse(group_card,
                                              id=f'{self.name}-{group_name}-collapse',
                                              is_open=is_open,
                                              className='mt-3')

        collapse_button = dbc.Button(
            f"Toggle {pretty_var(group_name)} parameters",
            id=f"{self.name}-{group_name}-collapse-button",
            className="mt-3",
            color="primary",
            outline=True
        )

        sliders = html.Div(id=f'{self.name}-{group_name}-sliders',
                           children=[collapsible_group_card, collapse_button])
        if group_name == 'advanced':
            sliders = html.Div(id=f'{self.name}-{group_name}-sliders',
                               children=[collapsible_group_card, collapse_button])
        else:
            sliders = html.Div(id=f'{self.name}-{group_name}-sliders',
                               children=[collapsible_group_card])
        return sliders

    def sliders(self):
        # Collect all the sliders into collapsible cards

        # Group the parameters together (for easier/nicer display)
        param_groups = defaultdict(list)
        for param in self.model.params:
            param_groups[param.group].append(param)
        try:
            # The constants aren't actually sliders, so ignore them
            del param_groups['constant']
        except KeyError:
            pass

        # Create actual slider groups
        group_names = ['static_social_distancing', 'dynamic_social_distancing', 'advanced']
        slider_card_groups = {group_name: None for group_name in group_names}

        slider_card_groups['static_social_distancing'] = self._card('static_social_distancing', param_groups)
        slider_card_groups['dynamic_social_distancing'] = self._card('dynamic_social_distancing', param_groups)
        slider_card_groups['advanced'] = self._card('advanced', param_groups, is_open=False)
        return slider_card_groups

    def static_sd_overlay_shape(self, model):
        shapes = [
            # Shade the fixed social distancing
            dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=model.t_weeks[model.start_sd],
                y0=0,
                x1=model.t_weeks[model.start_sd + model.sd_duration],
                y1=1,
                fillcolor=f"rgba(0,0,0,{model.sd_reduction})",
                opacity=0.3,
                layer="below",
                line_width=0
            )
        ]
        return shapes

    def static_sd_overlay_annotation(self, model):
        annotation = [
            # Annotate the social distancing period
            dict(
                xref="x",
                yref="paper",
                x=model.t_weeks[int((model.start_sd + model.sd_duration) / 2)],
                y=1.1,
                text=f'Social distancing',
                align='center',
                showarrow=False,
                bgcolor='white',
                bordercolor='gray'
            )
        ]
        return annotation

