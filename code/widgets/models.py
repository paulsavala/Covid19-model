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
    def header(self):
        return html.H1(children='Covid-19 SEIR Model [K-T-L-G]')

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
                group_card_body.append(html.Label(f'{param.desc} ({param.name}):', className='h5'))
            else:
                group_card_body.append(html.Label(f'{param.desc}:', className='h5'))
            group_card_body.append(self._slider(param, class_name='mb-3'))
        group_card = dbc.Card([group_card_header, dbc.CardBody(group_card_body)], id=f'{self.name}-{group_name}-card')
        collapsible_group_card = dbc.Collapse(group_card,
                                              id=f'{self.name}-{group_name}-collapse',
                                              is_open=is_open,
                                              className='mt-3')

        collapse_button = dbc.Button(
            f"Toggle {pretty_var(group_name, upper_only_first=True)} parameters",
            id=f"{self.name}-{group_name}-collapse-button",
            className="mt-3",
            color="primary",
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
        group_names = ['social_distancing', 'advanced']
        slider_card_groups = {group_name: None for group_name in group_names}

        slider_card_groups['social_distancing'] = self._card('social_distancing', param_groups, is_open=True)
        slider_card_groups['advanced'] = self._card('advanced', param_groups, is_open=False)
        return slider_card_groups

        # # Button(s) to collapse cards of sliders
        # collapse_buttons = {group: dbc.Button(
        #     f"Toggle {pretty_var(group)} params",
        #     id=f"{self.name}-{group}-collapse-button",
        #     className="mt-3",
        #     color="primary",
        # ) for group in groups}
        #
        # # Format everything into collapsible cards
        # slider_cards = []
        # slider_card_groups = {group: None for group in groups}
        # for group in groups:
        #     group_card_body = []
        #     group_card_header = dbc.CardHeader(f'{pretty_var(group)} parameters', className='h4')
        #     for param in param_groups.get(group):
        #         # Only show the parameter name for "advanced" parameters
        #         if group == 'advanced':
        #             group_card_body.append(html.Label(f'{param.desc} ({param.name}):', className='h5'))
        #         else:
        #             group_card_body.append(html.Label(f'{param.desc}:', className='h5'))
        #         group_card_body.append(self._slider(param, class_name='mb-3'))
        #     group_card = dbc.Card([group_card_header, dbc.CardBody(group_card_body)], id=f'{self.name}-{group}-card')
        #     if group == 'advanced':
        #         is_open = False
        #     else:
        #         is_open = True
        #     collapsible_group_card = dbc.Collapse(group_card,
        #                                           id=f'{self.name}-{group}-collapse',
        #                                           is_open=is_open,
        #                                           className='mt-3')
        #
        #     sliders = html.Div(id=f'{self.name}-{group}-sliders',
        #                        children=[collapsible_group_card, collapse_buttons[group]])
        #     if group == 'advanced':
        #         sliders = html.Div(id=f'{self.name}-{group}-sliders',
        #                            children=[collapsible_group_card, collapse_buttons[group]])
        #     else:
        #         sliders = html.Div(id=f'{self.name}-{group}-sliders',
        #                            children=[collapsible_group_card])
        #     slider_cards.append(sliders)
        #     slider_card_groups[group] = sliders
        # return slider_card_groups

    def footer(self):
        footer = dcc.Markdown(f'''
        Social distancing has a strong effect on the 
        ''')
        return html.Div(id='footer', children=footer, className='mt-5 h5')