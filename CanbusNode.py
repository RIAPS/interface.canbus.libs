import time
from libs.CanbusSystemSettings import CanbusSystem
import libs.Terminal as TerminalColors
import yaml
import spdlog
import os
import struct
import can
import threading
import queue
import zmq
import time
import datetime as dt

def StartCANBus( dev, spd, logger ):
    logger.info( f"{TerminalColors.Yellow}Starting CAN bus hardware...{TerminalColors.RESET}" ) 
    result = os.WEXITSTATUS( os.system( f"sudo ip link set {dev} up type can bitrate {spd}") )
    if result > 0 :
        if result == 2 :
            logger.info( f"{TerminalColors.Yellow}CAN Bus already started. Code=[{result}]{TerminalColors.RESET}" )
        elif result == 1 :
            logger.info( f"{TerminalColors.Red}CAN Bus device {dev} not found! Code=[{result}]{TerminalColors.RESET}" )
        else:
            pass
    return result

class CanbusNode( threading.Thread ) :
    def __init__(self, logger, canport, dev="can0", filters=None ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.events_active = threading.Event()
        self.events_active.set()
        self.commands_active = threading.Event()
        self.commands_active.set()
        self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)
        self.filters = filters
        self.dev = dev
        self.canbus = None
        self.plug = None
        self.event_thread = None
        try:   
            self.canbus = can.ThreadSafeBus(channel=self.dev, bustype='socketcan_native', can_filters=self.filters )
            self.canbus.set_filters( filters=self.filters )
        except OSError as oex :
            self.logger.info(f"{TerminalColors.Red}CANBus device error: {oex}{TerminalColors.RESET}")    

    def Deactivate(self):
        self.events_active.clear()
        self.commands_active.clear()

    def updateFilters(self, newfilters=None ):
        if self.canbus != None :
            self.canbus.set_filters( filters=newfilters )

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        self.poller = zmq.Poller()
        self.poller.register( self.plug, zmq.POLLIN )
        
        self.event_thread = threading.Thread( target=self.event_listener )
        self.event_thread.start()

        if self.canbus != None and self.poller != None :
            while self.commands_active.is_set() :
                s = dict( self.poller.poll( 1000.0 ) )
                if len(s) > 0 :
                    msg = self.plug.recv_pyobj()
                    self.canbus.send( msg )
                    self.logger.info( f"{TerminalColors.Yellow}Command msg:{msg}{TerminalColors.RESET}" )
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread stopped{TerminalColors.RESET}" ) 

    def event_listener(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread started{TerminalColors.RESET}" ) 
        if self.canbus != None :
            while self.events_active.is_set() :
                msg = self.canbus.recv( timeout=self.timeout )
                if msg != None :    
                    self.plug.send_pyobj( msg )
        else:
            msg = can.Message   (arbitration_id=0x000,
                                data=[0x45, 0x52, 0x52, 0x4F, 0x52, 0x3D, 0x31, 0x00 ],
                                timestamp=dt.datetime.timestamp( dt.datetime.now() ))
            self.plug.send_pyobj( msg )
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread stopped{TerminalColors.RESET}" ) 
             