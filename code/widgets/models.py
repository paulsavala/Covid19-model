import dash_core_components as dcc
import dash_html_components as html

import numpy as np
from collections import defaultdict


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
                    'title': self.title
                }
            }
        )
        return graph

    def sliders(self):
        return None

    def header(self):
        return None

    def footer(self):
        return None


class SeirModelWidget(GenericModelWidget):
    def sliders(self):
        slider_children = []
        for param in self.model.params:
            if not param.is_constant:
                steps = (param.max_value - param.min_value) / 10
                slider_children.append(
                    html.Label(f'{param.desc} ({param.name}):')
                )
                if param.is_int:
                    slider_children.append(
                        dcc.Slider(id=f'{self.name}-{param.name}-slider', min=param.min_value, max=param.max_value,
                                   step=int(np.floor(steps)), value=param.default_value,
                                   marks={np.floor(s): str(np.floor(s)) for s in range(param.min_value,
                                                                                       param.max_value,
                                                                                       int(np.floor(steps))
                                                                                       )
                                          }
                                   )
                    )
                else:
                    slider_children.append(
                        dcc.Slider(id=f'{self.name}-{param.name}-slider', min=param.min_value, max=param.max_value,
                                   step=steps, value=param.default_value,
                                   marks={s: str(np.round(s, 3)) for s in
                                          np.arange(param.min_value, param.max_value, steps)})
                    )
        slider_children.append(
            dcc.Checklist(id=f'{self.name}-prevalence-checkbox',
                          options=[
                              {'label': 'Prevalence', 'value': 'prevalence'}
                          ],
                          value=[]
                          )
        )

        sliders = html.Div(id=f'{self.name}-sliders', children=slider_children)
        return sliders

    def header(self):
        return html.H1(children='Covid-19 SEIR Model [K-T-L-G]')
