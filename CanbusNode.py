import time

from zmq.sugar.context import T
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

testq = queue.Queue()
hbq = queue.Queue()

class CanbusControl( ) :
    def __init__(self, dev="can0", spd="500000", logger=None, filters=None ) :
        self.dev = dev
        self.spd = spd
        if logger != None :
            self.logger = logger
        else:
            self.logger = spdlog.ConsoleLogger( "CAN Lib" )

        self.filters = filters
        self.cbus = None
        self.event_thread = None
        self.command_thread = None
        self.heartbeat_thread = None
        logger.info( f"{TerminalColors.Yellow}CanbusControl __init__ complete{TerminalColors.RESET}" )

    def CreateCANBus( self, startbus=True, loopback=False ):
        result = 0
        if not loopback :
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
                    self.cbus = can.ThreadSafeBus( channel=self.dev, bustype='socketcan_native', can_filters=self.filters )
                except OSError as oex :
                    self.logger.info( f"{TerminalColors.Red}CANBus device error: {oex}{TerminalColors.RESET}" ) 
        else:
            self.cbus = None
            
        return self.cbus

    def UpdateFilters(self, newfilters=None ):
        if self.cbus != None :
            self.cbus.set_filters( filters=newfilters )

    def StartEventHandler(self, canport, filters=None):
        self.event_thread = CanbusEventNode( self.logger, canport, filters  )                    
        self.event_thread.start()

    def StartCommandHandler(self, canport, filters=None):
        self.command_thread = CanbusCommandNode( self.logger, canport, filters  )                    
        self.command_thread.start()

    def StartHeartbeatHandler(self, hbmsg, frequency = 1.0 ):
        self.CanbusHeartBeat = CanbusHeartBeat( self.logger, hbmsg, freq=frequency  )                    
        self.CanbusHeartBeat.start()
    
    def Stop(self):
        if self.CanbusHeartBeat != None :
            self.CanbusHeartBeat.Deactivate()
            self.CanbusHeartBeat.join(timeout=10.0)
            if self.CanbusHeartBeat.is_alive() :
                self.logger.info( f"{TerminalColors.Red}Failed to terminate CAN bus heartbeat thread!{TerminalColors.RESET}" )

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

class CanbusHeartBeat( threading.Thread ) :
    def __init__( self, logger, hbmsg, canbus, freq=1.0 ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.hbmsg = hbmsg
        self.frequency = freq
        self.canbus = canbus
        self.heartbeat_active = threading.Event()
        self.heartbeat_active.set()
        self.heartbeat_skip = threading.Event()
        self.heartbeat_skip.clear()
        self.logger.info( f"{TerminalColors.Yellow}CanbusHeartBeat __init__ complete{TerminalColors.RESET}" )
    
    def Deactivate(self):
        self.heartbeat_active.clear()

    def hearbbeat_message(self, hbmsg ):
        self.heartbeat_skip.set()
        self.hbmsg = hbmsg
        self.logger.info( f"{TerminalColors.Yellow}New Heartbeat message:{self.hbmsg}{TerminalColors.RESET}" )
        self.heartbeat_skip.clear()

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Heartbeat Thread started{TerminalColors.RESET}" ) 
        self.logger.info( f"{TerminalColors.Yellow}Heartbeat message:{self.hbmsg}{TerminalColors.RESET}" )
        sleep_time = 1.0 / self.frequency
        if self.canbus != None :
            self.logger.info( f"{TerminalColors.Yellow}CAN Bus is available.{TerminalColors.RESET}" )
            while self.heartbeat_active.is_set() :
                time.sleep( sleep_time )
                if not self.heartbeat_skip.is_set() :
                    if self.hbmsg != None :
                        self.canbus.send( self.hbmsg )
        else :
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
            while self.heartbeat_active.is_set() :
                time.sleep( sleep_time )

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Heartbeat Thread stopped{TerminalColors.RESET}" ) 

class CanbusCommandNode( threading.Thread ) :
    def __init__(self, logger, canport, canbus ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.commands_active = threading.Event()
        self.commands_active.set()
        self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)
        self.canbus = canbus
        self.plug = None

    def get_plug( self ):
        return self.plug

    def Deactivate(self):
        self.commands_active.clear()

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        self.poller = zmq.Poller()
        self.poller.register( self.plug, zmq.POLLIN )
        
        if self.canbus != None :
            self.logger.info( f"{TerminalColors.Yellow}CAN Bus is available.{TerminalColors.RESET}" )
            while self.commands_active.is_set() :
                s = dict( self.poller.poll( 1000.0 ) )
                if len(s) > 0 :
                    msg = self.plug.recv_pyobj()
                    self.canbus.send( msg )
                    # self.logger.info( f"{TerminalColors.Yellow}Command msg:{msg}{TerminalColors.RESET}" )
        else :
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
            while self.commands_active.is_set() :
                s = dict( self.poller.poll( 1000.0 ) )
                if len(s) > 0 :
                    msg = self.plug.recv_pyobj()
                    testq.put( msg )

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread stopped{TerminalColors.RESET}" ) 


class CanbusEventNode( threading.Thread ) :
    def __init__(self, logger, canport, canbus ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.events_active = threading.Event()
        self.events_active.set()
        self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)
        self.canbus = canbus
        self.plug = None

    def get_plug( self ):
        return self.plug

    def Deactivate(self):
        self.events_active.clear()

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        self.poller = zmq.Poller()
        self.poller.register( self.plug, zmq.POLLIN )


        if self.canbus != None :
            self.logger.info( f"{TerminalColors.Yellow}CAN Bus is available.{TerminalColors.RESET}" )
            while self.events_active.is_set() :
                msg = self.canbus.recv( timeout=self.timeout )
                if msg != None :    
                    self.plug.send_pyobj( msg )
        else:
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
            while self.events_active.is_set() :
                try:
                    msg = testq.get( block=True, timeout=1.0 )
                    self.plug.send_pyobj( msg )
                except queue.Empty:
                    pass

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread stopped{TerminalColors.RESET}" ) 
