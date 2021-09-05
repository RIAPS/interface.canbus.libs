import time
from libs.CanbusSystemSettings import CanbusSystem
import libs.Terminal as TerminalColors
import yaml
import os
import struct
import can
import threading
import queue
import zmq
import time
import datetime as dt
import spdlog

class CanbusControl( ) :
    def __init__(self, dev="can0", spd="500000", logger=None ) :
        self.dev = dev
        self.spd = spd
        if logger != None :
            self.logger = logger
        else:
            self.logger = spdlog.ConsoleLogger( "CAN Lib" )

        self.cbus = None
        self.event_thread = None
        self.command_thread = None
        logger.info( f"{TerminalColors.Yellow}CanbusControl __init__ complete{TerminalColors.RESET}" )

    def CreateCANBus( self, startbus=True ):
        result = 0
        self.logger.info( f"{TerminalColors.Yellow}Starting CAN bus hardware...{TerminalColors.RESET}" ) 
        if startbus :
            result = os.WEXITSTATUS( os.system( f"sudo ip link set {self.dev} up type can bitrate {self.spd}") )
            if result > 0 :
                if result == 2 :
                    self.logger.info( f"{TerminalColors.Yellow}CAN Bus already started. Code=[{result}]{TerminalColors.RESET}" )
                elif result == 1 :
                    self.logger.info( f"{TerminalColors.Red}CAN Bus device {self.dev} not found! Code=[{result}]{TerminalColors.RESET}" )
                else:
                    pass
        if result != 1 :
            try:   
                self.cbus = can.ThreadSafeBus( channel=self.dev, bustype='socketcan_native', can_filters=None )
            except OSError as oex :
                self.logger.info( f"{TerminalColors.Red}CANBus device error: {oex}{TerminalColors.RESET}" ) 

        return self.cbus
    
    def StartEventHandler(self, canport, filters=None):
        self.event_thread = CanbusEventNode( self.logger, canport, filters  )                    
        self.event_thread.start()

    def StartCommandHandler(self, canport, filters=None):
        self.command_thread = CanbusCommandNode( self.logger, canport, filters  )                    
        self.command_thread.start()
    
    def Stop(self):
        if self.event_thread != None :
            self.event_thread.Deactivate()
            self.event_thread.join(timeout=10.0)
            if self.event_thread.is_alive() :
                self.logger.info( f"{TerminalColors.Red}Failed to terminate CAN bus event thread!{TerminalColors.RESET}" )
        
        if self.command_thread != None :
            self.command_thread.Deactivate()
            self.command_thread.join(timeout=10.0)
            if self.command_thread.is_alive() :
                self.logger.info( f"{TerminalColors.Red}Failed to terminate CAN bus command thread!{TerminalColors.RESET}" )



class CanbusCommandNode( threading.Thread ) :
    def __init__(self, logger, canport, canbus, filters=None ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.commands_active = threading.Event()
        self.commands_active.set()
        self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)
        self.filters = filters
        self.canbus = canbus
        if self.canbus != None :
            self.canbus.set_filters( filters=self.filters )
        self.plug = None

    def Deactivate(self):
        self.commands_active.clear()

    def updateFilters(self, newfilters=None ):
        if self.canbus != None :
            self.canbus.set_filters( filters=newfilters )

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        self.poller = zmq.Poller()
        self.poller.register( self.plug, zmq.POLLIN )
        
        if self.canbus != None :
            while self.commands_active.is_set() :
                s = dict( self.poller.poll( 1000.0 ) )
                if len(s) > 0 :
                    msg = self.plug.recv_pyobj()
                    self.canbus.send( msg )
                    self.logger.info( f"{TerminalColors.Yellow}Command msg:{msg}{TerminalColors.RESET}" )
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread stopped{TerminalColors.RESET}" ) 


class CanbusEventNode( threading.Thread ) :
    def __init__(self, logger, canport, canbus, filters=None ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.events_active = threading.Event()
        self.events_active.set()
        self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)
        self.filters = filters
        self.canbus = canbus
        if self.canbus != None :
            self.canbus.set_filters( filters=self.filters )
        self.plug = None

    def Deactivate(self):
        self.events_active.clear()

    def updateFilters(self, newfilters=None ):
        if self.canbus != None :
            self.canbus.set_filters( filters=newfilters )

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        
        if self.canbus != None :
            while self.events_active.is_set() :
                msg = self.canbus.recv( timeout=self.timeout )
                if msg != None :    
                    self.plug.send_pyobj( msg )
        else:
            # send an error frame "ERROR=1"
            msg = can.Message(  arbitration_id=0x000,
                                data=[0x45, 0x52, 0x52, 0x4F, 0x52, 0x3D, 0x31, 0x00 ],
                                timestamp=dt.datetime.timestamp( dt.datetime.now() ))
            self.plug.send_pyobj( msg )
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread stopped{TerminalColors.RESET}" ) 
