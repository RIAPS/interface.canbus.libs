#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
Requires Modbus-tk 

This slave implements the 4 main memory blocks of a Modbus device.

Creates a local master to allow active update of some modbus parameters as needed 

"""
import can
import sys
import select
import time
import argparse
import struct
import yaml
import os
import platform
import threading
import time
from random import random

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--CH', required=False , help="The CAN bus channel. Default = 'can0'")
    parser.add_argument('--ID', required=False, help="The CANbus message ID to publish on the bus. Default = 0x123" )
    parser.add_argument('--DATA', required=False, help="The data to send, a list in the format [1,2,3,4]. Default = [0,]" )
    parser.add_argument('--FREQ', required=False , help="The frequency at which to send the data. Default = 1.0 Hz")

    if platform.system().upper() == 'WINDOWS' :
        pass
    elif platform.system().upper() == 'LINUX' :
        pass
    else :
        pass

    args = parser.parse_args()

    if args.CH == None :
        CH = 'can0'
    else:
        CH = args.CH

    if args.ID == None :
        ID = 0x123
    else:
        ID = args.ID

    if args.DATA == None :
        DATA = [0,]
    else:
        DATA = args.DATA
    
    if args.FREQ == None :
        FREQ = 1.0
    else:
        FREQ = args.FREQ     
    
    msg_period = 1E9/FREQ

    active = threading.Event()
    active.set()

    bus = can.interface.Bus(channel=CH, bustype='socketcan_native')
    msg = can.Message( arbitration_id=ID, data=DATA )

    t1 = float( time.time_ns )
    while active.is_set :
        t2 = float( time.time_ns )
        if (t2 - t1) > msg_period :
            t1 = t2
            bus.send( msg )

    print( "CAN Bus simulation has exited normally." )

if __name__ == "__main__":
    main()