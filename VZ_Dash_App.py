# --------------------------------
# Name: VZ_Dash_App.py
# Purpose: This script intended to create a quick interactive dashboard based on input TIMS data.
# Current Owner: David Wasserman
# Last Modified: 7/16/2017
# Copyright:   (c) CoAdapt
# --------------------------------
# Copyright 2016 David J. Wasserman
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# --------------------------------
import dash
from dash.dependencies import Input, Output, State, Event
import dash_core_components as dcc
import dash_html_components as html
import plotly.plotly as py
from plotly import graph_objs as go
from plotly.graph_objs import *
from flask import Flask
import pandas as pd

import numpy as np
import datetime
import os

server = Flask('my app')

app = dash.Dash('Vision Zero App', server=server, csrf_protect=False)

if 'DYNO' in os.environ:
    app.scripts.append_script({
        'external_url': 'https://cdn.rawgit.com/chriddyp/ca0d8f02a1659981a0ea7f013a378bbd/raw/e79f3f789517deec58f41251f7dbb6bee72c44ab/plotly_ga.js'
    })


mapbox_access_token = 'pk.eyJ1IjoiaG9saXN0aWNieW5hdHVyZSIsImEiOiJjaWYwNDVxZjMwMHFoc2lsdXl5MW9rNXA4In0.JhBLZIdBZ5i8sse_f9K7Hw'

def make_df_list(str_in):
    return str([('"'+i+'"').strip("'") for i in str_in.split(",")]).replace("'","")


def initialize_collision_report(df):
    """Sets ups charts data for report and reports it through dictionary. New charts added by adds to dictionary.
    DF assumed to have 'related_collisions.csv' field schema."""
    severity_counts = {i:df[df["PrimeModeClass"]== i]['CRASHSEV'].value_counts() for i in ["Motor Vehicle","Bicycle","Pedestrian"]}
    bike_sev= severity_counts["Bicycle"].reset_index()
    ped_sev = severity_counts["Pedestrian"].reset_index()
    motor_sev = severity_counts["Motor Vehicle"].reset_index()
    bike_sev["PrimeModeClass"]= "Bicycle"
    ped_sev["PrimeModeClass"]= "Pedestrian"
    motor_sev["PrimeModeClass"] = "Motor Vehicle"
    severity_counts = pd.concat([motor_sev,bike_sev,ped_sev]).rename(index=str, columns={"index":"SEVERITY"})
    age_counts = pd.DataFrame({"Count of Minors":[df["VAGE_Minor"].sum()],"Count of 16-65":[df["VAGE_Working"].sum()],
    "Count of Seniors":[df["VAGE_Senior"].sum()]},index=None)
    df["TIME_PAD"]= df["TIME_"].apply(lambda  x: str(x).zfill(4))
    df["DateTimeStr"]= df["DATE_"].map(str)+" "+ df['TIME_PAD'].map(str)
    df["TimeStamp"] = pd.to_datetime(df["DateTimeStr"],format="%Y-%m-%d %H%M",errors='coerce')
    df["Hour"] = df["TimeStamp"].dt.hour.dropna().astype(int)
    time_df = df[["TimeStamp","Hour","CRASHSEV"]].dropna()
    race_counts= df[["F_A_PRACE", "F_H_PRACE", "F_W_PRACE", "F_O_PRACE", "F_B_PRACE"]].sum()

    return df,severity_counts,age_counts,race_counts,time_df

data_path="data/related_collisions.csv"
collisions_path="data/Collisions.csv"
victims_path="data/Victims.csv"
parties_path="data/Parties.csv"

if not os.path.isfile(data_path):
    import SWITRSProcessor
    print("Processing input CSVs once.")
    SWITRSProcessor.summarize_switrs(data_path,collisions_path,victims_path,parties_path)

df, severity_counts, age_counts, race_counts, time_df=initialize_collision_report(pd.read_csv(data_path))

#Reference Variables
colors = {'background': '#333333',
        'text': '#FFFFFF'
        ,'severity_bars':['#fed976','#fd8d3c','#f03b20','#99001e']
        ,'age_bars':['#edf8b1','#7fcdbb','#1565C0']}
severity_values=[4, 3, 2, 1]
severity_labels=['Complaint of Pain', 'Visible Injury', 'Severe Injury','Fatality']
mode_labels = severity_counts["PrimeModeClass"].unique()
center_point = dict(lon=df["POINT_X"].mean(),lat=df["POINT_Y"].mean())

app.layout = html.Div(style={'backgroundColor': colors['background']},children=[
                html.Div([
                    html.H2("Dash - Vision Zero", style={'font-family': 'Segoe UI','color': colors['text'],'padding': 5}),
                    # html.Div([
                    #     dcc.Slider(
                    #         id='year-slider',
                    #         min=df['YEAR_'].min(),
                    #         max=df['YEAR_'].max(),
                    #         value=df['YEAR_'].max(),
                    #         step=None,
                    #         marks={str(year): str(year) for year in df['YEAR_'].unique()}
                    #     )], style={'font-family': 'Segoe UI', 'color': colors['text'], 'padding': 30}),
                    html.P("Select different collision characteristics to filter data being reported by the dashboard."
                           ,style={'font-family': 'Segoe UI','color': colors['text'],'padding': 5})
                ]),
                html.Hr()
                ,
                dcc.Graph(
                id="collision-map",
                figure={
                "data": Data([
                        Scattermapbox(
                        lat=df[df["CRASHSEV"]==i]["POINT_Y"],
                        lon=df[df["CRASHSEV"]==i]["POINT_X"],
                        name=severity_labels[severity_values.index(i)],
                        mode='markers',
                        text="Severity: {0}".format(severity_labels[severity_values.index(i)]),
                        hoverinfo='text',
                        marker=Marker(
                            size=8,opacity=0.4,color=colors['severity_bars'][severity_values.index(i)]
                        )) for i in severity_values]),

                "layout": Layout(
                    title= "Map of Collisions by Severity",
                    autosize=True,
                    height=600,
                    hovermode='closest',
                    plot_bgcolor = colors['background'],
                    paper_bgcolor = colors['background'],
                    font= {'color': colors['text']},
                    mapbox=dict(
                        accesstoken=mapbox_access_token,
                        bearing=0,
                        style='dark',
                        center=center_point,
                        pitch=0,
                        zoom=10
                    ),
                )},
                    style={'width': '99%', 'display': 'inline-block', 'padding': '5 0'})
                ,
                dcc.Graph(
                        id='collision-severity',
                        figure={
                            'data': [go.Bar(x=mode_labels,
                             y=[severity_counts[(severity_counts["PrimeModeClass"]==j) & (severity_counts["SEVERITY"]==i)]["CRASHSEV"].iloc[0]  for j in mode_labels],
                             marker={'color': colors['severity_bars'][severity_values.index(i)]},
                             name = severity_labels[severity_values.index(i)]) for i in severity_values],
                            'layout': go.Layout(
                                title= "Collisions By Most Vulnerable Mode",
                                xaxis={ 'title': 'Mode'},
                                yaxis={'title': 'Collision Counts'},
                                barmode= "stack",
                                plot_bgcolor = colors['background'],
                                paper_bgcolor = colors['background'],
                                hovermode='closest',
                                font= {'color': colors['text']})},
                        style = {'width': '33%', 'display': 'inline-block', 'padding': '5 0'}
                        ),
                        dcc.Graph(
                        id='victims-age',
                        figure={
                            'data': [
                            {'x': ['Minors (<16)','Working (16-65)','Seniors (>=65)'],
                             'y': [age_counts.at[0,"Count of Minors"],age_counts.at[0,"Count of 16-65"],age_counts.at[0,"Count of Seniors"]],
                             'type': 'bar', 'marker':{'color':colors['age_bars']}}
                            ],
                            'layout': go.Layout(
                                title= "Victim Age Breakdown",
                                xaxis={ 'title': 'Age Category'},
                                yaxis={'title': 'Age Groups Victim Counts'},
                                plot_bgcolor = colors['background'],
                                paper_bgcolor = colors['background'],
                                hovermode='closest',
                                font= {'color': colors['text']}
                                )

                        },
                        style = {'width': '33%', 'display': 'inline-block', 'padding': '5 0'}),

                        dcc.Graph(
                        id='party-race-demographics',
                        figure={
                            'data': [
                            {'labels': ["White", "Black", "Hispanic", "Asian","Other"],
                             'values': [race_counts[i] for i in ["F_W_PRACE", "F_B_PRACE","F_H_PRACE","F_A_PRACE","F_O_PRACE"]],
                             'type': 'pie',"hole":.6, "text":"Ethnicity","hoverinfo":"label+percent+value"}
                            ],
                            'layout': go.Layout(
                                title="Collision Party By Ethnicity",

                                plot_bgcolor = colors['background'],
                                paper_bgcolor = colors['background'],
                                font= {'color': colors['text']}
                                )

                        },
                        style = {'width': '33%', 'display': 'inline-block', 'padding': '5 0'}),
                        dcc.Graph(
                        id='time-of-day-profile',
                        figure={
                            'data': [go.Bar(
                                x=[datetime.time(hour=h).strftime("%I:%M %p").lstrip("0") for h in (list(range(0,24)))],
                                #lstrip is not ideal, but is platform independent for this list comp.
                                y=time_df[time_df["CRASHSEV"] == i]["Hour"].value_counts().sort_index(),
                                marker={'color': colors['severity_bars'][severity_values.index(i)]},
                                name=severity_labels[severity_values.index(i)],width=.75) for i in severity_values]
                            ,
                            'layout': go.Layout(
                                title="Time of Day Collision Profile",
                                plot_bgcolor = colors['background'],
                                paper_bgcolor = colors['background'],
                                barmode='stack',
                                xaxis=dict(tickangle = 45),
                                hovermode='closest',
                                legend = dict(x=0,y=1.0),
                                bargap=.05,
                                font= {'color': colors['text']}

                                )
                        },
                        style = {'width': '99%', 'display': 'inline-block', 'padding': 0})

                ],tabIndex="Dash - Vision Zero")

               # dcc.Graph(id='map-graph')])
external_css = ["https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css",
                "https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css"]


for css in external_css:
    app.css.append_css({"external_url": css})

# @app.server.before_first_request
# def defineTotalDict():
#     global totalDict
#     totalDict = initialize_collision_report(pd.read("data/related_collisions.csv"))

if __name__ == '__main__':
    app.run_server(threaded=True)