#!/usr/bin/env python

import json
import yaml
import datetime, isodate, calendar
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import os
import sys

#============================================
scripts_path = os.path.dirname(__file__)
dir_layout_py = os.path.abspath(os.path.join(scripts_path, '..'))
dir_app_root = os.path.abspath(os.path.join(dir_layout_py, ".."))
assets_path = os.path.abspath(os.path.join(dir_app_root,"assets"))
if scripts_path not in sys.path:
    sys.path.append(scripts_path)
#============================================
unique_user_id_list = ['unique_user_name_1', 'unique_user_name_2']
#============================================


def load_config(filename):
    """Load configuration from a yaml file"""
    with open(filename) as f:
        return yaml.full_load(f)


def save_config(config, filename):
    """Save configuration to a yaml file"""
    with open(filename, "w+") as f:
        yaml.safe_dump(config, f, default_flow_style=False)


def pretty_print_json(data):
    print(json.dumps(data, indent=4, sort_keys=True))

def get_user_dict(user_name='unique_user_name_1'):
    is_user = os.path.join(dir_app_root , 'data', 'users', user_name)
    if os.path.isdir(is_user):
        user_dict = {}
        user_dict['user_name'] = user_name
        user_dict['dir_app'] = dir_app_root
        user_dict['credentials_file'] = os.path.join(dir_app_root,  'credentials','config_'+ user_name +'.yml')
        user_dict['polar_api_pulled_data'] = os.path.join(dir_app_root, 'data', 'users', user_name, 'polar_api_pulled_data')
        user_dict['polar_api_pulled_data_json'] = os.path.join(dir_app_root, 'data', 'users', user_name, 'polar_api_pulled_data', 'json_files')
        user_dict['polar_api_pulled_data_tcx'] = os.path.join(dir_app_root, 'data', 'users', user_name, 'polar_api_pulled_data', 'tcx_files')
        user_dict['polar_exported_data'] = os.path.join(dir_app_root, 'data', 'users', user_name, 'polar_exported_data')
        user_dict['processed_data'] = os.path.join(dir_app_root, 'data', 'users', user_name, 'processed_data')
        return user_dict
    else:
        print("User does not exist.")
        return {}

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def get_default_start_date():
    today = datetime.datetime.today().date()
    first_day_of_month = datetime.datetime.today().replace(day=1).date()
    first_day_of_last_month = today - relativedelta(months=1)
    if today == first_day_of_month:
        return first_day_of_last_month.strftime('%Y-%m-%d')
    else:
        return first_day_of_month.strftime('%Y-%m-%d')

def get_default_end_date():
    today = datetime.datetime.today().date()
    first_day_of_month = datetime.datetime.today().replace(day=1).date()
    endmonth = calendar.monthrange(today.year, today.month)
    last_day_of_month = datetime.datetime(today.year, today.month, endmonth[1])
    return last_day_of_month.strftime('%Y-%m-%d')

def get_default_current_calendar_month_range():
    first_day_of_month = datetime.datetime.today().replace(day=1).date().strftime('%Y-%m-%d')
    last_day_of_month = get_default_end_date()
    return first_day_of_month, last_day_of_month

def trailing_1_week_range():
    today = datetime.datetime.today().date()
    same_day_last_week = today - relativedelta(days=7)
    return same_day_last_week, today

def trailing_1_month_range():
    today = datetime.datetime.today().date()
    same_day_last_month = today - relativedelta(months=1)
    return same_day_last_month, today

def trailing_3_months_range():
    today = datetime.datetime.today().date()
    same_day_last_3_month = today - relativedelta(months=3)
    return same_day_last_3_month, today

def trailing_1_year_range():
    today = datetime.datetime.today().date()
    same_day_last_year = today - relativedelta(months=12)
    return same_day_last_year, today