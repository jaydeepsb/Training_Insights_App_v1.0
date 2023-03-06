# Author: https://github.com/jaydeepsb
#=== to kill previously running ports
# to list: sudo lsof -iTCP:8050 -sTCP:LISTEN
# to kill: kill -9 $(lsof -t -i:"8050")
#==================== for training_insights ===============
import os
import sys


from scripts.utils import *
from scripts.training_insights import training_insights, pull_api_data
#==================== for dashboard ===============

import time
import numpy as np
from datetime import datetime, date
import pandas as pd
from copy import deepcopy
from collections import Counter

import plotly.express as px
import plotly.graph_objs as go
import seaborn as sns

import dash
from dash import Dash, dcc, html, Input, Output, ctx, State
from dash import dash_table as dt
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import logging
#====================================================================
#-------------------  Fix setting values
#====================================================================
my_text_color_vio = 'blueviolet'
min_date = "2015-01-01"

def get_user_object_dict():
    user_object_dict = {'unique_user_name_1':training_insights('unique_user_name_1'), 'unique_user_name_2':training_insights('unique_user_name_2')}
    return user_object_dict
#====================================================================
top_title = html.H1(id="1_top_title", children='Training Insights 1.X', style={"width": "100%", 'text-align':'center', 'color':my_text_color_vio})

settings_label = html.H5('Settings', className='text-center', style={"width": "100%", 'text-align':'center', 'color':my_text_color_vio})
user_1_label = html.H5('User_1:', style={"width": "100%", 'text-align':'left', 'color':my_text_color_vio})
user_2_label = html.H5('User_2:', style={"width": "100%", 'text-align':'left', 'color':my_text_color_vio})

pull_btn = dbc.Spinner(children=[
            dbc.Button(children="Pull Recent", id='pull_btn', style={"width":"100%", 'color': my_text_color_vio }, 
                        outline=True, color="success", class_name="border rounded border-2 border-info")
            ], type='grow', spinner_class_name="spinner", color='info')

update_btn = dbc.Button("Update", id='update_btn',style={"width":"100%", 'color': my_text_color_vio}, 
                        outline=True, color="success", class_name="me-2 border rounded border-2 border-info")

interval_1hr = dcc.Interval(
            id='interval_1hr',
            interval=1*60*60*1*1000, # in milliseconds
            n_intervals=0)

preset_time_ranges = dbc.RadioItems(
                            id="preset_time_ranges",
                            options=[{'label':'Past Week', 'value':'past_week'}, 
                                    {'label':'Past Month', 'value':'past_month'}, 
                                    {'label':'Past 3 Month', 'value':'past_3_month'},
                                    {'label':'Past Year', 'value':'past_year'},
                                    {'label':'Custom', 'value':'custom'},
                                    ],
                            value= 'past_month',
                            )

calendar_range = dcc.DatePickerRange(
                        id='calendar_range',
                        min_date_allowed=min_date,
                        max_date_allowed=date.today(),
                        initial_visible_month=date.today(),
                        start_date = trailing_1_month_range()[0], 
                        end_date = trailing_1_month_range()[1],
                        first_day_of_week=1,
                        show_outside_days=True,
                        number_of_months_shown=3,
                        day_size=24,
                        display_format = "DD-MMM-YYYY",
                        style={'color': my_text_color_vio, "width": "100%"},
                        className="me-2 border border-dark",
                        )

overview_user_1 = dbc.Card(dbc.CardBody(id='ov_user_1', children=[user_1_label,]))
overview_user_2 = dbc.Card(dbc.CardBody(id='ov_user_2', children=[user_2_label,]))

fig_with_boarder_user_1 = dbc.Card(dbc.CardBody([
                            user_1_label, 
                            dbc.Spinner(dcc.Graph(id="fig_with_boarder_user_1",  figure={}, style={"width":"100%"}),
                                        type='grow', spinner_class_name="spinner", color='info'),
                            ], className="div-Boarder"))
fig_with_boarder_user_2 = dbc.Card(dbc.CardBody([
                            user_2_label, 
                            dbc.Spinner(dcc.Graph(id="fig_with_boarder_user_2",  figure={}, style={"width":"100%"}),
                                        type='grow', spinner_class_name="spinner", color='info'),
                            ], className="div-Boarder"))

param_list = [{'label':'Count', 'value':'count'}, 
                {'label':'Duration', 'value':'duration'}, 
                {'label':'Distance', 'value':'distance'},
                {'label':'Calories', 'value':'calories'},
                {'label':'Avg. Speed', 'value':'speed_avg'}, 
                {'label':'Avg. HR', 'value':'heart_rate_average'},
                {'label':'Weight', 'value':'weight'},
                #{'label':'Break-down', 'value':'break-down'},
                ]


def get_btn_for(param_dict):
    label, value = param_dict['label'], param_dict['value']
    btn = dbc.Button(label, id=value, 
                        style={"width":"100%", 'color': my_text_color_vio}, 
                        outline=True, color="success", class_name="me-0 border rounded border-2 border-info"
                    )
    return btn

type_of_plot = dbc.RadioItems(
                            id="type_of_plot",
                            options=[{'label':'Steps', 'value':'steps'},
                                     {'label':'Break-up', 'value':'break_up'},
                                     {'label':'Calendar', 'value':'calendar'},  
                                    ],
                            value='steps',
                            inline=True,
                            labelStyle={'color': my_text_color_vio},
                            style={'text-align':'center'}
                            )

param_btn_group = button_group = dbc.ButtonGroup(id="param_btn_group", children=
    [ get_btn_for(param_dict) for param_dict in param_list], 
    style={"width":"100%"},
)



param_id_div = html.Div(id="param_id_div", children="duration")

set_weight_title = html.Div([html.H5( children='Set weight:')],style={'margin-left': '10px'})
set_weight_info = html.Div([html.P(id='set_weight_info', children='To delete type "del", "delete", or "remove".')],style={'text-align':'left'})

weight_user_name = dbc.RadioItems(
                            id="weight_user_name",
                            options=[{'label':'user_1', 'value':'unique_user_name_1'},
                                     {'label':'user_2', 'value':'unique_user_name_2'}  
                                    ],
                            value='unique_user_name_1',
                            labelStyle={'color': my_text_color_vio},
                            )

weight_date_picker = dcc.DatePickerSingle(
        id='weight_date_picker',
        min_date_allowed=date(1980, 1, 1),
        max_date_allowed=date.today(),
        initial_visible_month=date.today(),
        date=date.today(),
        display_format = "DD-MMM-YYYY",
        style={"width": "100%"},
        className="me-2 border border-dark",
    )

weight_input = html.Div(
    [
        dbc.Input(id="weight_input", 
                    placeholder="Weight...", 
                    type="text", 
                    value=None,
                    style={"width":"100%", 'color': my_text_color_vio, 'text-align':'center'},
                    class_name="me-2 border rounded border-2 border-info"),
        html.Br(),
    ], style={"verticalAlign": "middle",}
)
#weight_date_OEC = html.Div(id='weight-date-picker-OEC')
#weight_input_OEC = html.Div(id='output-weight')
weight_submit_btn = dbc.Button(id="weight_submit_btn", children=["Submit"], 
                outline=True, color="success", 
                style={"width":"100%", 'color': my_text_color_vio, 'text-align':'center'},
                class_name="me-2 border rounded border-2 border-info")
#update_CSVs_empty container
weight_submit_btn_OEC = html.Div(id='weight_submit_btn_OEC')

weight_set_card = dbc.Card(dbc.CardBody([
                                set_weight_title, weight_user_name, 
                                weight_date_picker, weight_input, 
                                weight_submit_btn,
                                ]),)


empty_box1 = html.Div(id="empty_box1", children=[])
empty_box2 = html.Div(id="empty_box2", children=[])

#spinner_btn = dbc.Spinner([dbc.Button(id="spinner_btn", children=[1],style={"width":"100%"})])

btn_ex = dbc.Button("row 1 col 1",style={"width":"100%"})
fig_ex = dcc.Graph(figure={}, style={"width":"100%"})

#====================================================================
#dbc.Row([])
#dbc.Col([])

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX, dbc.icons.BOOTSTRAP, "my_theme.css"])
#app = dash.Dash(external_stylesheets=["my_theme_2.css"]) #dbc.themes.CYBORG

#====================================================================

#====================================================================
#df = px.data.gapminder()
#=================================================================================
#============================ LAYOUT =============================================
app.layout = dbc.Container(
    [   html.Br(),
        dbc.Row(dbc.Col([top_title])),  # header-row
        html.Br(),
        #==================
        dbc.Row([
            dbc.Col([  # first column on third row
            ], width=2),  # width first column on second-row
            dbc.Col([  # second column on third row
                param_btn_group,
                type_of_plot,
            ], width=10),  # width second column on third-row
            dbc.Col([  # third column on second row
            ], width=0),  # width third column on third-row
        ], className="g-0"),  # buttons row
        html.Br(), 
        #==================
        dbc.Row([  # start of second row
            dbc.Col([  # first column on second-row
                dbc.Card(dbc.CardBody([
                    settings_label, pull_btn, update_btn, 
                    dbc.Card(dbc.CardBody([preset_time_ranges, calendar_range])), 
                    weight_set_card]
                )),
                html.Br(),
            ], width=2),  # width first column on second-row
            dbc.Col([  # second column on second row
                fig_with_boarder_user_1,
                html.Br()
            ], width=5),  # width second column on second-row
            dbc.Col([  # third column on second row
                fig_with_boarder_user_2,
                html.Br()
            ], width=5),  # width third column on second-row
        ]),  # end of second row
        html.Br(),   
        dbc.Row([interval_1hr, param_id_div]),  # empty box row
        html.Br(),
    ], fluid=True)

#=================================================================================
#=========================== CALLBACKS ===========================================

#======= test button group ==================
@app.callback(
    Output(component_id=param_id_div, component_property='children'),
    [Input(component_id=param_dict['value'], component_property='n_clicks') for param_dict in param_list]
)
def update_output(*clicks):
    btn_id_list = [param_dict['value'] for param_dict in param_list]
    if list(filter(None,clicks)):
        if ctx.triggered_id in btn_id_list:
            return ctx.triggered_id
        else:
            return dash.no_update
    else:
        return dash.no_update

#============= update dates =================
@app.callback([Output('calendar_range', 'start_date'),
            Output('calendar_range', 'end_date'),
            Output('weight_date_picker', 'date')],
            [Input('interval_1hr', 'n_intervals'),
            Input('preset_time_ranges', 'value'),
            Input('calendar_range', 'start_date'),
            Input('calendar_range', 'end_date')])
def update_calendar_dates(n_intervals, preset_name, start_date, end_date):
    today = date.today()
    if preset_name == 'past_week':
        start_date, end_date  = trailing_1_week_range()
    elif preset_name == 'past_month':
        start_date, end_date  = trailing_1_month_range()
    elif preset_name == 'past_3_month':
        start_date, end_date  = trailing_3_months_range()
    elif preset_name == 'past_year':
        start_date, end_date  = trailing_1_year_range()
    elif preset_name == 'custom':
        start_date, end_date  = start_date, end_date
    else:
        start_date, end_date  = trailing_1_month_range()
    return start_date, end_date, today

#========= Pull data ================
@app.callback(
    Output('pull_btn', 'children'),
    Input('pull_btn', 'n_clicks'),
    prevent_initial_call=True,
    )
def pull_and_update_data(n_clicks):
    if n_clicks:    
        for user_id in unique_user_id_list:
            p = pull_api_data(user_name=user_id, saveit=True)
            p.check_recent_data()
        #user_object_dict = get_user_object_dict()
        for user_id in unique_user_id_list:
            p = training_insights(user_id)
            #p = user_object_dict.get(user_id)
            p.update_csv_apied_jsons()
    return dash.no_update

#========== Update CSVs =================
@app.callback(
    Output('update_btn', 'children'),
    Input('update_btn', 'n_clicks'),
    prevent_initial_call=True,)
def pull_and_update_data(n_clicks):
    if n_clicks:
        #user_object_dict = get_user_object_dict()
        for user_id in unique_user_id_list:
            p = training_insights(user_id)
            p.update_csv_apied_jsons()
    return dash.no_update

#========== Update Plots =================
@app.callback(
    [Output('fig_with_boarder_user_1', 'figure'),
    Output('fig_with_boarder_user_2', 'figure'),],
    [Input('update_btn', 'n_clicks'),
    Input('param_id_div', 'children'),
    Input('type_of_plot', 'value'),
    Input('calendar_range', 'start_date'),
    Input('calendar_range', 'end_date')],
    prevent_initial_call=False,)
def update_plots(param_id, col_name, type_of_plot, start_date, end_date):
    figs = [{}, {}]
    for i,user_id in enumerate(unique_user_id_list):
        p = training_insights(user_id)
        #p = user_object_dict.get(user_id)
        fig = p.get_fig_any_col(start_date=start_date, end_date=end_date, col_name=col_name, type=type_of_plot)
        figs[i] = fig
    figs = set_similar_ylim(figs)
    return figs[0], figs[1]

# #=========== Input weight =======

def isDigit(x):
    try:
        float(x)
        return True
    except ValueError:
        return False

# set_weight_title, weight_user_name, 
# weight_date_picker, weight_input, 
# weight_submit_btn, weight_submit_btn_OEC

@app.callback(Output('update_btn', 'n_clicks'),
            [Input("weight_submit_btn", "n_clicks"),
            State("weight_user_name", "value"),
            State('weight_date_picker', 'date'),
            State("weight_input", "value"),])
def Update_weight(n_clicks, user_name, given_date, weight_value):
    #p = user_object_dict.get(user_name)
    p = training_insights(user_name)
    if (weight_value is None)or(weight_value == ''):
        return dash.no_update
    elif isDigit(weight_value):
        if (float(weight_value)<0):
            return 0
        else:
            weight_value_float = np.round(float(weight_value),1)
            p.add_weight_entry(new_date=given_date, weight=weight_value_float,saveit=True)
            return 1
    elif weight_value.isalpha():
        if weight_value.lower() in ["del", "delete", "remove"]:
            p.delete_weight_at_date(at_date=given_date, saveit=True)
            return 1
        else:
            return 1
    else:
        return 1


def set_similar_ylim(list_of_figs=[]):
    try:
        ymax = []
        ymin = []
        for i in np.arange(len(list_of_figs)):
            fig = list_of_figs[i]
            ymax.append(np.max(fig.data[0]['y']))
            ymin.append(np.min(fig.data[0]['y']))
        ymax = np.max(ymax)
        ymax *= 1.05
        ymin = np.min(ymin)
        if ymin != 0:
            ymin *= 0.95
        for i in np.arange(len(list_of_figs)):
            fig = list_of_figs[i]
            fig.update_layout(yaxis_range=[ymin, ymax])
            list_of_figs[i] = fig
        return list_of_figs
    except:
        return list_of_figs

if __name__ == "__main__":
    #app.run_server(debug=False, port=8050, host='0.0.0.0')
    app.run_server(debug=True, port=8050, host='127.0.0.1')
