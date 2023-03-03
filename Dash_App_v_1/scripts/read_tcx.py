#!/usr/bin/env python
#
# file: tcx.py
#
# description: functions to parse garmin tcx files
#
# usage: import in other scripts
#
# requires: ElementTree, BeautifulSoup
#
# author: jake hofman (gmail: jhofman)
# edited by: Jaydeep

from xml.etree.ElementTree import fromstring
from time import strptime, strftime
from optparse import OptionParser
import sys
import argparse
import re
import pandas as pd
import numpy as np

def findtext(e, name, default=None):
    """
    findtext
    helper function to find sub-element of e with given name and
    return text value
    returns default=None if sub-element isn't found
    """
    try:
        return e.find(name).text
    except:
        return default

def get_tcx(file_name=None, xml_string=None):
    """
    parsetcx
    parses tcx data, returning a list of all Trackpoints where each
    point is a tuple of 
      (activity, lap, timestamp, seconds, lat, long, alt, dist, heart, cad)
    xml is a string of tcx data
    """

    # remove xml namespace (xmlns="...") to simplify finds
    # note: do this using ET._namespace_map instead?
    # see http://effbot.org/zone/element-namespaces.htm
    if (file_name is None)&(xml_string is None):
        print("Specify xml file name or give xml_string block.")
        return None
    elif file_name is not None:
        with open(file_name, 'r') as f:
            xml_string = f.read()
    elif xml_string is not None:
        xml_string = xml_string

    xml_string = re.sub('xmlns=".*?"','',xml_string)

    # parse xml
    tcx_object=fromstring(xml_string)
    return tcx_object

def get_dist_km(file_name=None, xml_string=None):
    tcx_object=get_tcx(file_name, xml_string)

    distantance_meters = []
    for element in tcx_object.findall('.//Lap/'):
        if element.tag == "DistanceMeters":
            v = element.text
            if v is not None:
                distantance_meters.append(float(v))
    if distantance_meters:
        distantance_meters = np.sum(distantance_meters)
        distantance_km = distantance_meters/1000.0
        return distantance_km
    else:
        return None

def get_tcx_points_df(file_name=None, xml_string=None):
    tcx_object=get_tcx(file_name, xml_string)

    activity = tcx_object.find('.//Activity').attrib['Sport']

    lapnum=1
    points=[]
    dist_meters_Lap_level = []
    for lap in tcx_object.findall('.//Lap/'):
        for point in lap.findall('.//Trackpoint'):

            # time, both as string and in seconds GMT
            # note: adjust for timezone?
            timestamp = findtext(point, 'Time')
            if timestamp:
                seconds = strftime('%s', strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ'))

            else:
                seconds = None

            # cummulative distance
            dist = findtext(point, 'DistanceMeters')
                
            # latitude and longitude
            position = point.find('Position')
            lat = findtext(position, 'LatitudeDegrees')
            long = findtext(position, 'LongitudeDegrees')

            # altitude
            alt = float(findtext(point, 'AltitudeMeters',0))
            
            # heart rate
            heart = int(findtext(point.find('HeartRateBpm'),'Value',0))

            # cadence
            cad = int(findtext(point, 'Cadence',0))

            # append to list of points
            points.append((activity,
                           lapnum,
                           timestamp, 
                           seconds, 
                           lat,
                           long,
                           alt,
                           dist,
                           heart,
                           cad))

        # next lap
        lapnum+=1
    col_names = ['activity', 'lap', 'timestamp', 'seconds', 'lat', 'long', 'alt', 'dist', 'heart', 'cad']
    df_points = pd.DataFrame(points, columns = col_names)
    df_points['lap'] -= df_points['lap'][0]
    return df_points

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( '-f', '--file_name', dest='file_name', type=str, help='XML file name', default=None)
    parser.add_argument( '-xml', '--xml_string', dest='xml_string', type=str, help='XML string block', default=None)
    args = parser.parse_args()

    # parse tcx file
    df_points = get_tcx_points_df(file_name = args.file_name, xml_string = args.xml_string)
    print(df_points.shape)
    # print results
    # (activity, lap, timestamp, seconds, lat, long, alt, dist, heart, cad)

    