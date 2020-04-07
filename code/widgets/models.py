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
    def _fix_marks(self, marks):
        # Dash bug causes certain marks to not show up.
        # Solution taken from https://github.com/plotly/dash-core-components/issues/159
        marks = {int(i) if i % 1 == 0 else i: '{}'.format(np.round(i, 3)) for i in marks}
        return marks

    def _slider(self, param, steps):
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
                            marks=self._fix_marks(marks_range)
                            )
        return slider

    def sliders(self):
        param_groups = defaultdict(list)
        for param in self.model.params:
            param_groups[param.group].append(param)
        try:
            del param_groups['constant']
        except KeyError:
            pass

        slider_children = defaultdict(list)
        groups = ['advanced', 'social_distancing']
        for group in groups:
            for param in param_groups.get(group):
                steps = (param.max_value - param.min_value) / 10
                slider_children[group].append(html.Div(children=[
                    html.Label(f'{param.desc} ({param.name}):'),
                    self._slider(param, steps)
                ]))

        slider_children['checkboxes'].append(
            dcc.Checklist(id=f'{self.name}-prevalence-checkbox',
                          options=[
                              {'label': 'Prevalence', 'value': 'prevalence'}
                          ],
                          value=[]
                          )
        )
        slider_children_groups = [html.Div(id=f'{self.name}-{group}-sliders',
                                  children=slider_children.get(group))
                                  for group in groups]
        slider_children_groups += [html.Div(id=f'{self.name}-checkboxes-sliders',
                                            children=slider_children.get('checkboxes'))]

        sliders = html.Div(id=f'{self.name}-sliders', children=slider_children_groups)
        return sliders

    # def sliders(self):
    #     slider_children = []
    #     for param in self.model.params:
    #         if not param.is_constant:
    #             steps = (param.max_value - param.min_value) / 10
    #             slider_children.append(
    #                 html.Label(f'{param.desc} ({param.name}):')
    #             )
    #             if param.is_int:
    #                 slider_children.append(
    #                     dcc.Slider(id=f'{self.name}-{param.name}-slider', min=param.min_value, max=param.max_value,
    #                                step=int(np.floor(steps)), value=param.default_value,
    #                                marks={np.floor(s): str(np.floor(s)) for s in range(param.min_value,
    #                                                                                    param.max_value,
    #                                                                                    int(np.floor(steps))
    #                                                                                    )
    #                                       }
    #                                )
    #                 )
    #             else:
    #                 slider_children.append(
    #                     dcc.Slider(id=f'{self.name}-{param.name}-slider', min=param.min_value, max=param.max_value,
    #                                step=steps, value=param.default_value,
    #                                marks={s: str(np.round(s, 3)) for s in
    #                                       np.arange(param.min_value, param.max_value, steps)})
    #                 )
    #     slider_children.append(
    #         dcc.Checklist(id=f'{self.name}-prevalence-checkbox',
    #                       options=[
    #                           {'label': 'Prevalence', 'value': 'prevalence'}
    #                       ],
    #                       value=[]
    #                       )
    #     )
    #
    #     sliders = html.Div(id=f'{self.name}-sliders', children=slider_children)
    #     return sliders

    def header(self):
        return html.H1(children='Covid-19 SEIR Model [K-T-L-G]')
