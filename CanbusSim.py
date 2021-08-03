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
    parser.add_argument('--ID', required=False, help="The CANbus message ID to publish on the bus. Default = 0x123" )
    parser.add_argument('--DATA', required=False, help="The data to send, a list in the format [1,2,3,4]. Default = [0,]" )
    parser.add_argument('--FREQ', required=False , help="The frequency at which to send the data. Default = 1.0 sec")

    if platform.system().upper() == 'WINDOWS' :
        pass
    elif platform.system().upper() == 'LINUX' :
        pass
    else :
        pass

    args = parser.parse_args()

    if args.ID == None :
        args.ID = 0x123

    if args.DATA == None :
        args.DATA = [0,]
    
    if args.FREQ == None :
        args.FREQ = 1.0
     
    
    active = threading.Event()
    active.set()
    
    with open(args.config) as f:
        data = yaml.safe_load( f )
    
    parms = data.keys()  

    while active.is_set :
        pass

    print( "CAN Bus simulation has exited normally." )

if __name__ == "__main__":
    main()