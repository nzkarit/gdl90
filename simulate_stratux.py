#!/usr/bin/env python
#
# simulate_stratux.py
#
"""Stratux Simulator

This program implements a sender of the GDL-90 data format used by Stratux.

Copyright (c) 2013 by Eric Dey; All rights reserved
Then edited in 2020 by Karit
"""

import time
import socket
import gdl90.encoder
import math
import os
import argparse
import configparser
import csv


LATLONG_TO_RADIANS = math.pi / 180.0
RADIANS_TO_NM = 180.0 * 60.0 / math.pi

def argParser():
    description = 'This tool will send the heartbeat messages related to making an EFB beileve that it is talking to a Stratux device. The defaults for the command line parameters can be specified in config.cfg'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--efb_ip', action='store', type=str, dest='efb_ip', default=cfg.get('efb', 'ip'), help='This is the IP address of the device on which the EFB under test is running on. Default: %(default)s')
    parser.add_argument('--efb_port', action='store', type=int, dest='efb_port', default=cfg.get('efb', 'port'), help='This is the port which the EFB under test is listening on. Default: %(default)s')
    return parser.parse_args()

def distance(lat0, lon0, lat1, lon1):
    """compute distance between two points"""
    lat0 *= LATLONG_TO_RADIANS
    lat1 *= LATLONG_TO_RADIANS
    lon0 *= -LATLONG_TO_RADIANS
    lon1 *= -LATLONG_TO_RADIANS
    radians = math.acos(math.sin(lat0)*math.sin(lat1)+math.cos(lat0)*math.cos(lat1)*math.cos(lon0-lon1))
    return(radians*RADIANS_TO_NM)


def distance_short(lat0, lon0, lat1, lon1):
    """compute distance between two points that are close to each other"""
    lat0 *= LATLONG_TO_RADIANS
    lat1 *= LATLONG_TO_RADIANS
    lon0 *= -LATLONG_TO_RADIANS
    lon1 *= -LATLONG_TO_RADIANS
    radians = 2.0*math.asin(math.sqrt((math.sin((lat0-lat1)/2.0))**2 + math.cos(lat0)*math.cos(lat1)*(math.sin((lon0-lon1)/2.0))**2))
    return(radians*RADIANS_TO_NM)


def horizontal_speed(distance, seconds):
    """compute integer speed for a distance traveled in some number of seconds"""
    return(int(3600.0 * distance / seconds))

def get_traffic(iteration):
    if cfg.getboolean('traffic', 'enabled'):
        traffic = []
        if cfg.getboolean('traffic', 'csv'):
            step = iteration % cfg.getint('traffic', 'csvNumberOfSteps')
            csvFileName = cfg.get('traffic', 'csvFileName')
            with open(csvFileName) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=',')
                for row in reader:
                    if int(row['step']) == step:
                        plane = {}
                        plane['latitude'] = float(row['latitude'])
                        plane['longitude'] = float(row['longitude'])
                        plane['altitude'] = float(row['altitude'])
                        plane['horizontalSpeed'] = int(row['horizontalSpeed'])
                        plane['verticalSpeed'] = float(row['verticalSpeed'])
                        plane['heading'] = float(row['heading'])
                        plane['callSign'] = row['callSign']
                        icao = row['icaoAddress']
                        icao = int(icao, 0)
                        plane['icaoAddress'] = icao
                        traffic.append(plane)
        else:
            plane = {}
            plane['latitude'] = cfg.getfloat('traffic', 'latitude')
            plane['longitude'] = cfg.getfloat('traffic', 'longitude')
            plane['altitude'] = cfg.getfloat('traffic', 'altitude')
            plane['horizontalSpeed'] = cfg.getint('traffic', 'horizontalSpeed')
            plane['verticalSpeed'] = cfg.getfloat('traffic', 'verticalSpeed')
            plane['heading'] = cfg.getfloat('traffic', 'heading')
            plane['callSign'] = cfg.get('traffic', 'callSign')
            icao = cfg.get('traffic', 'icaoAddress')
            icao = int(icao, 0)
            plane['icaoAddress'] = icao
            traffic.append(plane)
        return traffic
    else:
        return None

if __name__ == '__main__':
    
    global cfg
    cfg = configparser.ConfigParser()
    cfg.read('config.cfg')
    arguments = argParser()

    destAddr = arguments.efb_ip
    destPort = arguments.efb_port

    print "Simulating Stratux unit."
    print "Transmitting to %s:%s" % (destAddr, destPort)
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    packetTotal = 0
    encoder = gdl90.encoder.Encoder()
    
    callSign = 'N12345'
    latCenter = 30.456447222222224
    longCenter = -98.2941888888889
    pathRadius = 0.25  # degrees
    angle = 0.0
    altitude = 0
    heading = 0
    groundspeed = 0
    verticalspeed = 0
    
    # ADS-B towers:
    towers = [
        (29.888890, -97.865556, 'HYI01'),
        (30.463333, -99.736390, 'TX009'),
        (31.203056, -97.051111, 'TX021'),
        (30.586667, -97.682222, 'TX024'),
        (31.598056, -100.160000, 'TX028'),
    ]


    uptime = 0
    latitudePrev = 0.0
    longitudePrev = 0.0
    iteration = 0
    
    while True:
        
        timeStart = time.time()  # mark start time of message burst
        
        #Move ourself
        angle += 0.66666  # degrees
        while angle >= 360.0:
            angle -= 360.0
        angleRadians = (angle / 180.0) * math.pi
        latitude = latCenter - (pathRadius * math.sin(angleRadians))
        longitude = longCenter + (pathRadius * math.cos(angleRadians))
        altitude = 2500 + 1000 * math.sin(uptime / 20.0)
        heading = (180 + int(angle)) % 360
        
        distanceMoved = distance_short(latitudePrev, longitudePrev, latitude, longitude)
        groundspeed = horizontal_speed(distanceMoved, 1.0)
        latitudePrev = latitude
        longitudePrev = longitude
        
        # Heartbeat Message
        buf = encoder.msgHeartbeat()
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1

        # Stratux Heartbeat Message
        buf = encoder.msgStratuxHeartbeat()
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1
        
        # Hiltonsoftware SX Heartbeat Message
        buf = encoder.msgSXHeartbeat(towers=towers)
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1
        
        # Ownership Report
        buf = encoder.msgOwnershipReport(latitude=latitude, longitude=longitude, altitude=altitude, hVelocity=groundspeed, vVelocity=verticalspeed, trackHeading=heading, callSign=callSign)
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1
        
        # Ownership Geometric Altitude
        buf = encoder.msgOwnershipGeometricAltitude(altitude=altitude)
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1
        
        # Traffic Reports
        traffic = get_traffic(iteration)
        for t in traffic:
            buf = encoder.msgTrafficReport(latitude=t['latitude'], longitude=t['longitude'], altitude=t['altitude'], hVelocity=t['horizontalSpeed'], vVelocity=t['verticalSpeed'], trackHeading=t['heading'], callSign=t['callSign'], address=t['icaoAddress'])
            s.sendto(buf, (destAddr, destPort))
            packetTotal += 1
        
        # GPS Time, Custom 101 Message
        buf = encoder.msgGpsTime(count=packetTotal)
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1
        
        # On-screen status output
        uptime += 1
        if uptime % 10 == 0:
            print "Uptime %d, lat=%3.6f, long=%3.6f, altitude=%d, heading=%d, angle=%3.3f" % (uptime, latitude, longitude, altitude, heading, angle)
        
        # Delay for the rest of this second
        time.sleep(1.0 - (time.time() - timeStart))
        iteration += 1
