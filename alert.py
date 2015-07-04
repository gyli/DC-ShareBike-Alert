#!/usr/bin/python
# -*-coding:UTF-8 -*-

import sys

_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py2:
    from urllib import urlopen, urlencode
elif is_py3:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
import json
import math
import smtplib
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import sched
import time


class BikeShareDC:
    BIKESHARE_URL = 'http://www.capitalbikeshare.com/data/stations/bikeStations.xml'

    def __init__(self):
        self.station_info = self.bikeparser(url=self.BIKESHARE_URL)

    @staticmethod
    def bikeparser(url):
        tree = ET.ElementTree(file=urlopen(url))
        root = tree.getroot()
        return [{x.tag: x.text for x in station.findall('./*')} for station in root]

    @staticmethod
    def get_coordinates(query, from_sensor=False):
        query = query.encode('utf-8')
        params = {
            'address': query,
            'sensor': "true" if from_sensor else "false"
        }
        url = 'http://maps.googleapis.com/maps/api/geocode/json?' + urlencode(params)

        if is_py2:
            json_response = urlopen(url)
            response = json.loads(json_response.read())
        elif is_py3:
            req = Request(url)
            response = json.loads(urlopen(req).readall().decode('utf-8'))

        if response['results']:
            location = response['results'][0]['geometry']['location']
            latitude, longitude = location['lat'], location['lng']
            # print query, latitude, longitude
        else:
            latitude, longitude = None, None
            # print query, "<no results>"
        return {'lat': latitude, 'long': longitude}

    @staticmethod
    def _distance_of_coordinates(lat1, lat2, long1, long2):
        return math.hypot(float(lat1) - float(lat2), float(long1) - float(long2))

    def get_station(self, address, limit=1):
        # https://secure.capitalbikeshare.com/map/
        coordinate = self.get_coordinates(address)
        self.station_info.sort(
            key=lambda station: self._distance_of_coordinates(coordinate['lat'], station['lat'],
                                                              coordinate['long'], station['long'])
        )
        if limit == 0:
            limit = None
        return [{k: s.get(k) for k in s if k in ['terminalName', 'name']} for s in self.station_info][0:limit]

    def get_station_info(self, name):
        for station in self.station_info:
            if station.get('terminalName') == str(name):
                return station
        return {}

    @staticmethod
    def read_conf():
        with open('conf.json') as conf_file:
            conf = json.load(conf_file)
        options = [u'jobs', u'email_from_address', u'email_from_password', u'email_from_server', u'email_to_address']
        for option in options:
            if option not in conf or not conf.get(option):
                raise ValueError('Missing option ' + option + ' in config file.')

        return conf

    @staticmethod
    def _send_alert(from_addr, from_psw, from_server, to_addr, subject, content):
        server = smtplib.SMTP(from_server + ':587')
        server.starttls()
        server.login(from_addr, from_psw)

        # Send email
        senddate = datetime.strftime(datetime.now(), '%Y-%m-%d')
        subject = "Your job has completed"
        m = "Date: %s\r\nFrom: %s\r\nTo: %s\r\nSubject: %s\r\nX-Mailer: My-Mail\r\n\r\n" % (
            senddate, from_addr, to_addr, subject)
        server.sendmail(from_addr, to_addr, m + content)
        server.quit()

    def _run_alert(self, schedule, conf, alert_log):

        job_options = [u'Start', u'StationID', u'BikeLessThan', u'End', u'DockLessThan']

        # Refresh the station info
        self.station_info = self.bikeparser(url=self.BIKESHARE_URL)

        for job in conf.get('jobs'):
            # Config checking
            for job_option in job_options:
                if job_option not in job or job.get(job_option) is None:
                    raise ValueError('Invalid option ' + job_option + ' in config file.')

            # Get station info by station ID
            this_station_info = self.get_station_info(job.get('StationID'))
            if not this_station_info:
                raise ValueError('StationID ' + job.get('StationID') + ' is invalid.')

            this_station_info = self.get_station_info(job.get('StationID'))
            now = datetime.now()
            # Read the time and add date to them
            start = datetime.strptime(job.get('Start'), "%H:%M:%S").time()
            end = datetime.strptime(job.get('End'), "%H:%M:%S").time()
            start_time = datetime.combine(datetime.today(), datetime.strptime(job.get('Start'), "%H:%M:%S").time())
            end_time = datetime.combine(datetime.today(), datetime.strptime(job.get('End'), "%H:%M:%S").time())
            if end < start:
                end_time += timedelta(days=1)

            if start_time <= now <= end_time:
                if int(job.get('BikeLessThan')) and int(this_station_info.get('nbBikes')) < int(job.get('BikeLessThan')) and not alert_log[this_station_info.get('ID') + '_bike']:
                    self._send_alert(
                        conf.get('email_from_address'),
                        conf.get('email_from_password'),
                        conf.get('email_from_server'),
                        conf.get('email_to_address'),
                        subject=u'BikeShare Alert: Not enough Bikes',
                        content="""
                                Alert: The number of bikes is %s now
                                Station Name: %s
                                Station ID: %s
                                Last Update Time: %s
                                """ % (this_station_info.get('nbBikes'),
                                       this_station_info.get('name'),
                                       this_station_info.get('terminalName'),
                                       datetime.fromtimestamp(
                                           float(this_station_info.get('latestUpdateTime')) / 1000
                                       ).strftime(
                                           '%Y-%m-%d %H:%M:%S')
                                       )
                    )
                    # One email for one alert only
                    alert_log[this_station_info.get('ID') + '_bike'] = 1
                if int(job.get('DockLessThan')) and int(this_station_info.get('nbEmptyDocks')) < int(job.get('DockLessThan')) and not alert_log[this_station_info.get('ID') + '_dock']:
                    self._send_alert(
                        conf.get('email_from_address'),
                        conf.get('email_from_password'),
                        conf.get('email_from_server'),
                        conf.get('email_to_address'),
                        subject=u'BikeShare Alert: Not enough Docks',
                        content="""
                                Alert: The number of docks is %s now
                                Station Name: %s
                                Station ID: %s
                                Last Update Time: %s
                                """ % (this_station_info.get('nbEmptyDocks'),
                                       this_station_info.get('name'),
                                       this_station_info.get('terminalName'),
                                       datetime.fromtimestamp(
                                           float(this_station_info.get('latestUpdateTime')) / 1000
                                       ).strftime(
                                           '%Y-%m-%d %H:%M:%S')
                                       )
                    )
                    alert_log[this_station_info.get('ID') + '_dock'] = 1

        schedule.enter(60, 1, self._run_alert, (schedule, conf, alert_log))

    def set_alert(self):
        conf = self.read_conf()
        alert_log = {}
        s = sched.scheduler(time.time, time.sleep)
        s.enter(60, 1, self._run_alert, (s, conf, alert_log))
        s.run()
        print('Alert is setted.')
