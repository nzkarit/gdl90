#!/usr/bin/env python2
#
# simulate_stratux_heartbeat.py
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

# Default values for options
# DEF_SEND_ADDR="192.168.10.61"
# DEF_SEND_PORT=4000

def argParser():
    description = 'This tool will send the heartbeat messages related to making an EFB beileve that it is talking to a Stratux device. The defaults for the command line parameters can be specified in config.cfg'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--efb_ip', action='store', type=str, dest='efb_ip', default=cfg.get('efb', 'ip'), help='This is the IP address of the device on which the EFB under test is running on. Default: %(default)s')
    parser.add_argument('--efb_port', action='store', type=int, dest='efb_port', default=cfg.get('efb', 'port'), help='This is the port which the EFB under test is listening on. Default: %(default)s')
    return parser.parse_args()

if __name__ == '__main__':
    
    global cfg
    cfg = configparser.ConfigParser()
    cfg.read('config.cfg')
    
    arguments = argParser()


    destAddr = arguments.efb_ip

    destPort = arguments.efb_port

    print("Simulating Stratux Heartbeat.")
    print("Transmitting to %s:%s" % (destAddr, destPort))
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    packetTotal = 0
    encoder = gdl90.encoder.Encoder()
    
    uptime = 0
    
    while True:
        
        timeStart = time.time()  # mark start time of message burst
        
        # Heartbeat Message
        buf = encoder.msgHeartbeat()
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1

        # Stratux Heartbeat Message
        buf = encoder.msgStratuxHeartbeat()
        s.sendto(buf, (destAddr, destPort))
        packetTotal += 1
        
        # On-screen status output
        uptime += 1
        if uptime % 10 == 0:
            print("Uptime %d" % (uptime))
        
        # Delay for the rest of this second
        time.sleep(1.0 - (time.time() - timeStart))
