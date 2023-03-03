from scripts.utils import *
import pandas as pd
import numpy as np
from copy import deepcopy
from collections import Counter
import datetime, isodate, calendar
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import read_tcx

import requests
from xml.dom import minidom
import json

from plotly_calplot import calplot
import plotly.express as px
import plotly.graph_objs as go
import seaborn as sns
from matplotlib import colors

#=============================================
#============ PULL RECENT JSONS ==============
#=============================================
class pull_api_data(object):
    def __init__(self, user_name='unique_user_name_1', saveit=True):
        """
        user_name : user name
        saveit : True or False
        """
        self.user_name = user_name
        self.saveit = saveit
        self.user_dict = get_user_dict(user_name=user_name)
        self.config = load_config(self.user_dict['credentials_file'])
        self.headers = {'Accept': '*/*',  'Authorization': 'Bearer {}'.format(self.config['access_token'])}
        self.base_polaraccesslink = 'https://www.polaraccesslink.com/v3/exercises'
        if len(self.config['access_token']) == 0:
            print("Authorization is required. Obtain access token first. Then copy the token in config file.")
            return
        
    def check_recent_data(self, saveit=None):
        if saveit is not None:
            self.saveit = saveit
        #get list of exercises 
        response = requests.get(self.base_polaraccesslink, headers = self.headers)
        print("========= User: ", self.user_name, " =========")
        if response.status_code >= 200 and response.status_code < 400:
            self.list_of_sessions = json.loads(response.content)
            print(len(self.list_of_sessions), " new activities available.")
            if len(self.list_of_sessions) > 0:
                for v in self.list_of_sessions:
                    print(v['start_time'], v['id'], v['detailed_sport_info'])
                    if self.saveit:
                        self.save_json_file(activity_json=v)
                        self.download_and_save_TCX_file(activity_json=v)
        else:
            self.list_of_sessions = []
            print("No new activities available.")

    def create_full_fname(self,activity_json, file_ext='json'):
        start_time = activity_json['start_time']
        start_time = datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
        start_time = start_time.strftime('%Y-%m-%d_T_%H%M%S')
        fname = '_'.join([start_time, activity_json['detailed_sport_info']])
        fname = os.path.join(self.user_dict['polar_api_pulled_data_'+file_ext], fname + '.' + file_ext)
        return fname
                
    def save_json_file(self, activity_json):
        fname = self.create_full_fname(activity_json, file_ext='json')
        with open(fname, 'w') as f:
            json.dump(activity_json, f, indent=4)
            
    def download_and_save_TCX_file(self, activity_json):
        exerciseId = activity_json['id']
        #get tcx files
        response = requests.get(self.base_polaraccesslink+'/{}/tcx'.format(exerciseId), 
                                     headers = self.headers)
        if response.status_code >= 200 and response.status_code < 400:
            # Parse the byte string
            xml = minidom.parseString(response.content)
            # Use the prettify() method to format the XML
            pretty_xml_str = xml.toprettyxml()
            # Save the formatted XML string to a file
            fname = self.create_full_fname(activity_json, file_ext='tcx')
            with open(fname, 'w') as f:
                f.write(pretty_xml_str)
            



#=============================================
#======== PROCESSING OF PULLED JSONS =========
#=============================================
class training_insights(object):
    def __init__(self, user_name='unique_user_name_1', recreate=False):
        """
        user_name : user name
        saveit : True or False
        """
        self.user_name = user_name
        self.recreate = recreate
        self.user_dict = get_user_dict(user_name=user_name)
        self.col_names = ['id', 'start_time', 'year', 'month', 'day', 'week_n', 'sport',\
                           'detailed_sport_info', 'duration', 'distance', 'speed_avg', 'speed_max',\
                           'heart_rate_average', 'heart_rate_maximum', 'training_load',\
                           'has_route', 'calories', 'count', 'file_name', 'device_id', 'device', 'start_time_utc_offset',\
                           'upload_time', 'polar_user']
        self.cols_for_plots = ["start_time", "detailed_sport_info", "distance", "duration", "count", "speed_avg", "heart_rate_average", "calories"]
        self.activity_sorter_dict = {'CYCLING' : 0,
            'HIIT' : 1,
            'RUNNING' : 2,
            'INDOOR_CYCLING' : 3,
            'INDOOR_ROWING' : 4,
            'NO_ACTIVITY' : 5}

        #=============================================
        self.csv_apied_jsons = os.path.join(self.user_dict["processed_data"], "api_data_processed.csv")
        self.csv_expo_jsons = os.path.join(self.user_dict["processed_data"], "exported_data_processed.csv")
        self.csv_combined = os.path.join(self.user_dict["processed_data"], "combined.csv")
        self.weight_file_name = "weight_profile.csv"
        self.weight_file_name = os.path.join(self.user_dict['processed_data'], self.weight_file_name)
        #=============================================
        processed_files_exist = True
        for fname in [self.csv_apied_jsons, self.csv_expo_jsons, self.csv_combined]:
            processed_files_exist *= os.path.isfile(fname)
        if processed_files_exist == False:
            self.create_empty_csvs()
            self.recreate = False
        #=============================================
        if self.recreate:
            self.create_empty_csvs()
        #=============================================
        self.summarize_cols_mode_dict = {'count':'sum','duration':'sum', 'distance':'sum'}
        self.read_processed_csvs()
        self.set_colors_dict_per_activity()
        self.read_weight_profile_df()

    def convert_isotime(self, dt_iso_string="PT1800S", convert_to='hours'): #i.e. 30mins, 'hours'
        dt = isodate.parse_duration(dt_iso_string)
        dt_in_seconds = dt.total_seconds()
        dt_in_minutes = dt_in_seconds / 60
        dt_in_hours = dt_in_seconds / 3600
        if convert_to=='minutes':
            return dt_in_minutes
        elif convert_to=='hours':
            return dt_in_hours

    def set_colors_dict_per_activity(self):
        activity_names = self.df_apied_jsons['detailed_sport_info'].tolist()
        # count = Counter(activity_names)
        # activity_names = [x[0] for x in sorted(count.items(), key=lambda x: (-x[1], activity_names.index(x[0])))]
        # n = len(activity_names)
        # colors_list = sns.color_palette("husl", n)
        # colors_list = [colors.to_hex(color) for color in colors_list]
        # fix_colors_for_activties_dict = dict(zip(activity_names,colors_list))
        # return fix_colors_for_activties_dict
        self.fix_colors_dict = {
            'CYCLING' : "#981ddd", #violet
            'HIIT' : "#70d1a1", # lightgreen
            'RUNNING' : "#e86e4d", #orange shade
            'INDOOR_CYCLING' : "#d170d0", #light violet
            'INDOOR_ROWING' : "#3293f0", # aqua blue
            'NO_ACTIVITY' : "#c0d6e4", #blueish gray
        }
        n = len(self.fix_colors_dict)
        for a in activity_names:
            if a not in list(self.fix_colors_dict.keys()):
                n += 1
                colors_list = sns.color_palette("husl", n)
                self.fix_colors_dict[a] = colors.to_hex(colors_list[-1])
        # print("==============")
        # print(self.fix_colors_dict)

    def create_empty_csvs(self):
        for fname in [self.csv_apied_jsons, self.csv_expo_jsons, self.csv_combined]:
            data_df = pd.DataFrame([], columns=self.col_names)
            data_df.set_index('id', inplace=True)
            data_df.to_csv(fname)
        print("Empty CSV files created.")
        self.read_processed_csvs()

    def read_processed_csvs(self):
        df_list = []
        for fname in [self.csv_apied_jsons, self.csv_expo_jsons, self.csv_combined]:
            df = pd.read_csv(fname, index_col='id')
            df_list.append(df)       
        self.df_apied_jsons, self.df_expo_jsons, self.df_combined = df_list
        self.df_apied_jsons['start_time'] = pd.to_datetime(self.df_apied_jsons['start_time'])

#============================ PROCESS API PULLED JSONS ===========================================================================
    def get_list_of_apied_jsons(self):
        file_names = os.listdir(self.user_dict["polar_api_pulled_data_json"])
        return file_names

    def read_apied_json_file(self, file_name):
        full_file_name = os.path.join(self.user_dict["polar_api_pulled_data_json"], file_name)
        with open(full_file_name) as f:
            json_data = json.load(f)
        data_dict = deepcopy(json_data)
        remove_keys = []
        for k,v in json_data.items():
            if isinstance(v, dict):
                sub_keys = v.keys()
                for sub_key in sub_keys:
                    data_dict[k+'_'+sub_key] = v[sub_key]
                remove_keys.append(k)
        #============================
        date_obj = datetime.datetime.strptime(json_data.get('start_time', None), '%Y-%m-%dT%H:%M:%S') 
        #d.get('start_time', None).split('T')
        data_dict["year"] = date_obj.year
        data_dict["month"] = date_obj.month
        data_dict["day"] = date_obj.day
        data_dict["week_n"] = date_obj.isocalendar().week
        data_dict['duration'] = np.round(self.convert_isotime(data_dict['duration']), 2)
        data_dict['count'] = 1
        data_dict['file_name'] = os.path.splitext(file_name)[0]
        if data_dict['detailed_sport_info'] == "ROAD_BIKING":
            data_dict['detailed_sport_info'] = "CYCLING"
        if data_dict.get('distance', None) is not None:
            data_dict['distance'] = np.round(float(data_dict.get('distance', None))/1000.0,2)
        for k in remove_keys:
            data_dict.pop(k)
        if data_dict['duration'] >= 0.15:
            return data_dict
        else:
            return {}

    def update_csv_apied_jsons(self):
        file_names = self.get_list_of_apied_jsons()
        file_names = [f for f in file_names if f.endswith('.json')]
        for file_name in file_names:
            data_dict = self.read_apied_json_file(file_name)
            exerciseId = data_dict.get('id',None)
            if len(data_dict) > 1:
                self.df_apied_jsons.loc[exerciseId] = data_dict
        self.fill_missing_distances_from_tcx()
        self.fill_missing_avg_speed()
        print(self.df_apied_jsons.shape[0], " Activities summarized.")
        self.df_apied_jsons['start_time'] = pd.to_datetime(self.df_apied_jsons['start_time'])
        self.df_apied_jsons.sort_values(by='start_time', ascending=False, inplace=True)
        self.df_apied_jsons.to_csv(self.csv_apied_jsons)

    def fill_missing_distances_from_tcx(self):
        list_of_exercise_ids = self.df_apied_jsons[self.df_apied_jsons["distance"].isna()].index.to_list()
        if list_of_exercise_ids:
            for v in list_of_exercise_ids:
                file_name = self.df_apied_jsons.loc[v]['file_name'] + '.tcx'
                file_name = os.path.join(self.user_dict["polar_api_pulled_data_tcx"], file_name)
                distantance_km = read_tcx.get_dist_km(file_name)
                self.df_apied_jsons.loc[v,'distance'] = distantance_km

    def fill_missing_avg_speed(self):
        list_of_exercise_ids = self.df_apied_jsons[self.df_apied_jsons["speed_avg"].isna()].index.to_list()
        for v in list_of_exercise_ids:
            d,t = self.df_apied_jsons.loc[v]['distance'], self.df_apied_jsons.loc[v]['duration']
            if (t is not None)or(t!=0.0):
                self.df_apied_jsons.loc[v,'speed_avg'] = d/t

    def summurize_df_apied_jsons(self):
        summarize_cols = list(self.summarize_cols_mode_dict.keys())
        self.df_summarize = \
            self.df_apied_jsons.groupby(by=['year', 'month','detailed_sport_info'])[summarize_cols].agg(self.summarize_cols_mode_dict)
        for y in self.df_apied_jsons['year'].unique():
            for m in self.df_apied_jsons['month'].unique():
                total = self.df_apied_jsons.query(' year==@y & month==@m ')[['count', 'duration', 'distance']].sum(axis=0)
                self.df_summarize.loc[(y, m,        'Total')] = total
        return self.df_summarize
        
    def get_dates_between(self, start_date=None, end_date=None):
        """
            Input datetime is strings of type "%Y-%m-%d" or date objects
            Output list of date objects
        """
        if (start_date is None)or(end_date is None):
            return []
        if isinstance(start_date, str)and(isinstance(end_date, str)):
            start_date, end_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date(), datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        # create a list to store all the dates
        all_dates_between = []
        # loop through all the dates between start_date and end_date
        current_date = start_date
        while current_date <= end_date:
            all_dates_between.append(current_date)
            current_date += timedelta(days=1)
        return all_dates_between

    def get_time_filtered_df_for_plots(self, start_date=None, end_date=None, include_non_activity_days=True):
        """
            Input datetime is strings of type "%Y-%m-%d" or date objects
        """ 
        if start_date is  None:
            start_date = get_default_start_date()
        if end_date is None:
            end_date = get_default_end_date()
        all_dates_between = self.get_dates_between(start_date, end_date)
        if all_dates_between:
            df = deepcopy(self.df_apied_jsons[self.cols_for_plots]).rename(columns={'detailed_sport_info':'Activity'})
            df['start_time'] = df['start_time'].apply(lambda x: x.date())
            all_dates_between = self.get_dates_between(start_date, end_date)
            mask = df["start_time"].apply(lambda x: x).isin(all_dates_between)
            df = df.loc[mask]
            if include_non_activity_days:
                missing_dates = sorted(list(set(all_dates_between) - set(df["start_time"].tolist())))
                col_names = [v for v in df.columns if v != 'start_time']
                df_non_activity = pd.DataFrame([], columns=col_names, index=missing_dates)
                df_non_activity.index.name = 'start_time'
                df_non_activity[col_names] = 0
                #"speed_avg", "heart_rate_average" set to None
                df_non_activity['speed_avg'] = None
                df_non_activity['heart_rate_average'] = None
                df_non_activity['count'] = 1
                df_non_activity['Activity'] = "NO_ACTIVITY"
                #df.set_index('start_time', drop=False, inplace=True)
                df = df.reset_index().set_index('start_time')
                df = pd.concat([df, df_non_activity])
            df = df.sort_values(by='start_time').reset_index(drop=False)
            df['colors'] = df['Activity'].apply(lambda x: self.fix_colors_dict.get(x, "#B2BEB5")) #default ash_gray
            return df
        else:
            return None

    def get_fig_any_col(self, start_date=None, end_date=None, col_name='duration', type='steps'):
        statement = ""
        fig = {}
        #=============================
        if col_name == 'weight':
            fig = self.get_weight_profile_fig()
            return fig
        # elif col_name == 'break-down':
        #     fig = self.get_df_summary_fig(start_date, end_date, col_name='count')
        #     return fig
        elif col_name not in self.cols_for_plots:
            return {}
        #=========  set date ============
        if start_date is  None:
            start_date = get_default_start_date()
        if end_date is None:
            end_date = get_default_end_date()
        df = self.get_time_filtered_df_for_plots(start_date=start_date, end_date=end_date)
        if (df is None)or(df.shape[0]==0):
            return {}
        #=============================
        if col_name in [ 'speed_avg', 'heart_rate_average']:
            #df[col_name].replace(to_replace=[None], value=0, inplace=True)
            fig = px.scatter(df, x="start_time", y=col_name)
            #fig.update_traces(fill='tozeroy') 
            return fig
        #(col_name in [ "distance", "duration", "count", "calories"])&
        if type=='steps':
            fig = self.get_step_fig(start_date, end_date, col_name, mode='cumulative')
            return fig
        elif type=='break_up':
            fig = self.get_df_summary_fig(start_date, end_date, col_name)
            return fig
        #=============================
        # if type == 'steps':
        #     fig = px.line(df, x="start_time", y=col_name, markers=True, line_shape="hv")
        #     fig.update_traces(fill='tozeroy')    
        # if type == 'calendar':
        #     df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
        #     fig = calplot(
        #                 df,
        #                 x="start_time",
        #                 y=col_name,
        #                 dark_theme=False,
        #                 years_title=True,
        #                 colorscale="purples",
        #                 gap=0,
        #                 name=col_name,
        #                 month_lines_width=3, 
        #                 month_lines_color="#fff"
        #             )
        return fig

    def get_df_summary_fig(self, start_date=None, end_date=None, col_name='duration'):
        #=============================
        if start_date is  None:
            start_date = get_default_start_date()
        if end_date is None:
            end_date = get_default_end_date()
        df = self.get_time_filtered_df_for_plots(start_date=start_date, end_date=end_date)
        if (df is None)or(df.shape[0]==0):
            return {}
        #=============================
        total = np.round(df[col_name].sum(),2)
        title = 'Total '+ col_name + " "
        if col_name == "duration":
            df = df.query(' Activity!="NO_ACTIVITY" ')
            h,m = int(total), (total*60)%60
            dt = "%d:%02d"%(h,m)
            title += dt+" hours."
        elif col_name == "distance":
            df = df.query(' Activity!="NO_ACTIVITY" ')
            title += str(total)+" km."
        else:
            total = np.round(df.query(' Activity!="NO_ACTIVITY" ')[col_name].sum(),2)
            title += str(total)+"."
        #color_sequence = [self.fix_colors_dict.get(label, "#B2BEB5") for label in df['Activity']]
        fig = px.pie(df, values=col_name, names='Activity', hole=.3, template='simple_white')
        #fig = px.pie(df, values=col_name, names='Activity', color=color_sequence, color_discrete_sequence=color_sequence, template='plotly_dark')

        fig.update_traces(textposition='outside', textinfo='label+value+percent')
        fig.update_layout(title=title, legend_title="Sport", font=dict(family="Courier New, monospace",
                                                                    size=12,
                                                                    color="purple"))
        fig.update_layout(legend=dict(
                                orientation="h",
                                yanchor="middle",
                                y=-0.3,
                                xanchor="right",
                                x=0.9
                            ))
        return fig

    # def get_df_sorted_by_activities(self, df):
    #     activity_sorter_dict = deepcopy(self.activity_sorter_dict)
    #     v_max = np.max(activity_sorter_dict.values())
    #     for a in df["Activity"].unique():
    #         if a not in activity_sorter_dict.keys():
    #             v_max += 1
    #             activity_sorter_dict[a] = v_max
    #     df['sorter_idx'] = df['Activity'].apply(lambda x: activity_sorter_dict.get(x))
    #     df.sort_values('sorter_idx', inplace=True)
    #     return df

    def get_step_fig(self, start_date=None, end_date=None, col_name='duration', mode='cumulative'):
        today = datetime.datetime.today().date()
        #=============================
        if start_date is  None:
            start_date = get_default_start_date()
        if end_date is None:
            end_date = get_default_end_date()
            #end_date = end_date.strftime("%Y-%m-%d")
        df = self.get_time_filtered_df_for_plots(start_date=start_date, end_date=end_date)
        if (df is None)or(df.shape[0]==0):
            return {}
        #=============================
        if col_name == 'count':
            df.loc[df["Activity"]=="NO_ACTIVITY", "count"] = 0
        total = np.round(df[col_name].sum(),2)
        if mode == 'cumulative':
            df.loc[:,col_name] = df[col_name].cumsum()
        #===============================================
        title = 'Total '+ col_name + " "
        y_label = col_name.title()
        if col_name == "duration":
            h,m = int(total), (total*60)%60
            dt = "%d:%02d"%(h,m)
            title += dt+" hours."
            y_label += " (Hours)"
        elif col_name == "distance":
            title += str(total)+" km."
            y_label += " (Km)"
        else:
            title += str(total)+"."
        #================================================
        fig1 = px.line(df, x="start_time", y=col_name, template='plotly_dark')
        fig1.update_traces(fill='tozeroy')
        #df = self.get_df_sorted_by_activities(df)
        #====================
        fig2 = px.scatter(df[df['start_time']<=today], x="start_time", y=col_name, color='Activity')
        #fig2 = px.scatter(df[df['start_time']<=today], x="start_time", y=col_name, color='colors', color_discrete_sequence=df[df['start_time']<=today]['colors'] )
        comb_fig = go.Figure(data=fig1.data + fig2.data)
        comb_fig.update_layout(
                    title=title,
                    xaxis_title="Date",
                    yaxis_title=y_label,
                    legend_title="Sport",
                    font=dict(
                        family="Courier New, monospace",
                        size=12,
                        color="RebeccaPurple"
                    )
                )
        comb_fig.update_layout(legend=dict(
                            bgcolor='rgba(0,0,0,0)',
                            orientation="v",
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01
                        ))
        return comb_fig

    def read_weight_profile_df(self):
        self.df_weights = pd.read_csv(self.weight_file_name)
        self.df_weights["date"] = pd.to_datetime(self.df_weights["date"], format="%Y-%m-%d")
        self.df_weights.sort_values(by='date', inplace=True)
        self.df_weights.reset_index(drop=True, inplace=True)

    def save_weight_profile_CSV(self):
        self.df_weights.dropna(how='any', inplace=True)
        dates = [d.date().strftime("%Y-%m-%d") for d in self.df_weights["date"].to_list()]
        self.df_weights["date"] = dates
        self.df_weights.to_csv(self.weight_file_name, index=False)
        self.read_weight_profile_df()

    def add_weight_entry(self, new_date=None, weight=None, saveit=False):
        if (new_date is not None)&(weight is not None):
            self.df_weights.set_index('date', drop=True, inplace=True)
            self.df_weights.loc[new_date, "weight"] = weight
            self.df_weights.reset_index(drop=False, inplace=True)
            if saveit:
                self.save_weight_profile_CSV()

    def delete_weight_at_date(self, at_date, saveit=False):
        dates = [d.date().strftime("%Y-%m-%d") for d in self.df_weights["date"].to_list()]
        if at_date is not None:
            if at_date in dates:
                self.df_weights = self.df_weights[self.df_weights["date"] != at_date]
            if saveit:
                self.save_weight_profile_CSV()

    def get_weight_profile_fig(self):
        fig = px.scatter(self.df_weights, x="date", y="weight", trendline="ols")
        fit_results = px.get_trendline_results(fig)
        #print(fit_results)
        fit_results = fit_results.iloc[0]["px_fit_results"].params
        slope = fit_results[1] # this is kg per sec. units
        slope *= 24*3600 # this is kg per day
        slope *= 7 # this is kg/week
        slope *= 1000 # gms/week
        slope = int(slope)
        #print(np.abs(slope))
        title = "Weight loss/gain: " + str(slope) + " (gms/week)." #+ str(self.df_weights['weight'].iloc[-1]) +" kg)"
        fig.add_trace(go.Scatter(x=self.df_weights['date'], y=self.df_weights['weight'],
                    line_shape='spline'))
        fig.update_layout(
                    title=title,
                    xaxis_title="Date",
                    yaxis_title="Weight (kg)",
                    showlegend=False,
                    font=dict(
                        family="Courier New, monospace",
                        size=12,
                        color="RebeccaPurple"
                    )
                )
        return fig
#======================================================================================================
#============================ PROCESS exported JSONS ==================================================





#======================================================================================================
