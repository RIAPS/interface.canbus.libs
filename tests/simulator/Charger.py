#!/usr/bin/env python
# -*- coding: utf_8 -*-
"""
Requires Python-CAN 


"""
from posixpath import join
import can
from can import bus
from can import message
from canbuslibs.CanbusSystemSettings import CanbusSystem
import canbuslibs.Terminal as TerminalColors
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
import datetime
import queue
from random import random
import string

the_version = "1.0.0"
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
                print( "{0}Sent :{2} {1}".format( TerminalColors.Green, msg, TerminalColors.RESET ) )
            except queue.Empty:
                pass

        print( "SendMsg thread exited." )

class RecvMsgThread( threading.Thread ):
    def __init__(self, thread_name, canbus, ids ):
        threading.Thread.__init__(self)
        self.ids = ids
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
                    # print( "id={0} : id list={1}".format(   hex( msg.arbitration_id )[2:].zfill(3), 
                    #                                         [ hex( n )[2:].zfill(3) for n in self.ids ] ) )
                    if (self.ids == None) or (msg.arbitration_id in self.ids) : 
                        RecvQueue.put( msg, block=False )
                except queue.Full:
                    print( "Received CAN message [{msg}] could not be queued.")
            else:
                pass
                # print( "Waiting for received message" )


        print( "RecvMsg thread exited." )

def main():
 
    print( f"Charger version {the_version}" ) 

    parser = argparse.ArgumentParser()
    parser.add_argument('--CH', required=False , help="The CAN bus channel. Default = 'can0'")
    parser.add_argument('--ID', required=False, help="The CANbus message ID to publish on the bus. Default = 0x123" )
    parser.add_argument('--DATA', required=False, help="The data to send, a list in the format 1,2,3,4. Default = 0" )
    parser.add_argument('--FREQ', required=False , help="The frequency at which to send the data. Default = 1.0 Hz")
    parser.add_argument('--IDLIST', required=False , help="The list if message IDs to monitor 0x001,0x043,0x310.  Default = 0x000")
    parser.add_argument('--MODE', required=False , help="The send(receive) mode either S, R, or SR.  Default = SR")
    parser.add_argument('--FILTER', required=False , help="The filter and mask settings if required. If not specified all messages are received.")
    

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
        CH = str( args.CH )

    if args.ID == None :
        ID = 0x123
    else:
        ID = int( args.ID, base=16 )

    if args.DATA == None :
        DATA = [0,]
    else:
        strs = str(args.DATA).split(",")
        DATA = [ int(i) for i in strs ]

    if args.FREQ == None :
        FREQ = 1.0
    else:
        FREQ = float( args.FREQ )   

    if args.MODE == None :
        MODE = 'SR'
    else:
        MODE = args.MODE    

    if args.IDLIST == None :
        IDLIST = None
    else:
        strs = str(args.IDLIST).split(",")
        if len( strs ) > 0 :
            IDLIST = [ int(i,base=16) for i in strs ]
        else:
            IDLIST = None

    if args.FILTER == None :
        CANMASK = None
        CANFILTER = None
    else:
        strs = str(args.FILTER).split(",")
        if len( strs ) > 1 :
            CANMASK = int(strs[0],base=16)
            CANFILTER = int(strs[1],base=16)
        else:
            print( "--FILTER Format error. Requires both MASK and FILTER values. Ex: 0x000,0x3FF" )
            CANMASK = None
            CANFILTER = None

    print( "CH={0}".format( CH ) )    
    print( "ID=0x{0}".format( hex( ID )[2:].zfill(3) ) )    
    print( "DATA={0}".format( DATA ) )    
    print( "FREQ={0}".format( FREQ ) )
    if IDLIST != None :    
        print( "IDLIST={0}".format( [ hex( n )[2:].zfill(3) for n in IDLIST ] ) )    
    else:
        print( "IDLIST={0}".format( "No filter message IDs" ) )
    
    if (CANMASK != None) and (CANFILTER != None) :    
        print( "CANMASK={0}, CANFILTER={1}".format( hex( CANMASK )[2:].zfill(3),  hex( CANFILTER )[2:].zfill(3)   ) )    
    else:
        print( "CANMASK={0}, CANFILTER={1}".format( None, None ) )

    print( "MODE={0}".format( MODE ) )

    send_period = 1.0/FREQ

    #bus = can.interface.Bus(channel=CH, bustype='socketcan_native' )
    bus = can.ThreadSafeBus( channel=CH, bustype='socketcan', can_filters=None )
    
    if (CANMASK != None) and (CANFILTER != None ) :
        bus.set_filters([{"can_id": CANFILTER, "can_mask": CANMASK, "extended": False}])

    input_watcher = InputWatcher()
    input_watcher.start()

    recv_thread = RecvMsgThread( "CANRecv", bus, IDLIST )
    if "R" in MODE : 
        recv_thread.start()

    send_thread = SendMsgThread( "CANSend", bus, 1.0 )
    if "S" in MODE :
        send_thread.start()

    p1 = 400.0
    p2 = 800.0
    delta = 0.1
    f = "BBBB"
    while send_thread.is_alive() or recv_thread.is_alive():
        if not input_watcher.is_alive() :
            if recv_thread.is_alive() :
                recv_thread.Deactivate()
            if send_thread.is_alive() :
                send_thread.Deactivate()
        else:
            try:
                message = RecvQueue.get( block=False )
                print( "{0}Recv :{2} {1}".format( TerminalColors.Red, message, TerminalColors.RESET ) )
            except queue.Empty:
                message = None

            if send_thread.is_alive() and message != None :
                try:
                    if message.arbitration_id == ID :
                        dta = [ 0 ] * 8
                        frame = struct.pack(">f", float(p1) )
                        integer_data = struct.unpack(f,frame)
                        i = 0
                        for b in integer_data :
                            dta[i] = integer_data[i]
                            i = i + 1
                        frame = struct.pack(">f", float(p2) )
                        integer_data = struct.unpack(f,frame)
                        i = 0
                        for b in integer_data :
                            dta[i+4] = integer_data[i]
                            i = i + 1
                        t1 = datetime.datetime.now()
                        msg = can.Message(  timestamp=datetime.datetime.timestamp( t1 ), 
                                            arbitration_id=ID, 
                                            data=dta, 
                                            is_extended_id=False )
                        SendQueue.put( msg, block=False )
                except queue.Full:
                    pass
                p1 = p1 + delta
                p2 = p2 - delta
                if p1 > 405.0 or p1 < 395.0:
                    delta = -delta
        
    print( "CAN Bus simulation has exited normally." )

if __name__ == "__main__":
    main()