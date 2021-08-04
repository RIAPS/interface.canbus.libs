#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
Requires Modbus-tk 

This slave implements the 4 main memory blocks of a Modbus device.

Creates a local master to allow active update of some modbus parameters as needed 

"""
from posixpath import join
import can
from CanbusSystemSettings import CanbusSystem
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
import queue
from random import random

RecvQueue = queue.Queue()
SendQueue = queue.Queue()

def DebugPrint( info ) :
    if CanbusSystem.Debugging.DebugLevel > 0 :
        print( info )

class InputWatcher( threading.Thread ):
    def __init__(self):
        threading.Thread.__init__(self)
    
    def run(self):
        text = input( "Press enter to stop.\r\n")
        print( "User requested exit...\r\n")

class SendMsgThread( threading.Thread ):
    def __init__(self, thread_name, canbus, timing ):
        threading.Thread.__init__(self)
        self.timing = timing
        self.canbus = canbus
        self.thread_name = thread_name
        self.active = threading.Event()
        self.active.set()
    
    def Deactivate(self):
        self.active.clear()
 
        # helper function to execute the threads
    def run(self):
        print( "CAN bus send thread is running." )
        while self.active.is_set() :
            try:
                msg = SendQueue.get( block=True, timeout=self.timing )
                self.canbus.send( msg )
                print( "Sent : {0}".format( msg ) )
            except queue.Empty:
                pass

        print( "SendMsg thread exited." )

class RecvMsgThread( threading.Thread ):
    def __init__(self, thread_name, canbus ):
        threading.Thread.__init__(self)
        self.canbus = canbus
        self.thread_name = thread_name
        self.active = threading.Event()
        self.active.set()

    def Deactivate(self):
        self.active.clear()
 
        # helper function to execute the threads
    def run(self):
        print( "CAN bus receive thread is running." )
        while self.active.is_set() :
            msg = self.canbus.recv( timeout=1.0 )   
            if( msg != None ) :
                try:
                    RecvQueue.put( msg, block=False )
                except queue.Full:
                    print( "Received CAN message [{msg}] could not be queued.")


        print( "RecvMsg thread exited." )

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
        ID = 0x043
    else:
        ID = args.ID

    if args.DATA == None :
        DATA = [0,25,0,1,3,0,150]
    else:
        DATA = args.DATA
    
    if args.FREQ == None :
        FREQ = 1.0
    else:
        FREQ = args.FREQ     
    
    msg_period = 1E9/FREQ

    bus = can.interface.Bus(channel=CH, bustype='socketcan_native')
    msg = can.Message( arbitration_id=ID, data=DATA, extended_id=False )
    
    recv_thread = RecvMsgThread( "CANRecv", bus )
    send_thread = SendMsgThread( "CANSend", bus, 1.0 )
    input_watcher = InputWatcher()

    input_watcher.start()
    recv_thread.start()
    send_thread.start()

    while send_thread.is_alive() or recv_thread.is_alive():
        if not input_watcher.is_alive() :
            recv_thread.Deactivate()
            send_thread.Deactivate()
        else:
            try:
                message = RecvQueue.get( block=False )
                print( "Recv : {0}".format( message ) )
                try:
                    SendQueue.put( msg, block=False )
                except queue.Full:
                    pass
            except queue.Empty:
                pass
        
    print( "CAN Bus simulation has exited normally." )

if __name__ == "__main__":
    main()