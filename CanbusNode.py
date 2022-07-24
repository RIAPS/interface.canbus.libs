import time
import canbuslibs.CanbusSystemSettings as CanSys
import canbuslibs.Terminal as TerminalColors
import os
import can
import threading
import queue
import zmq
import time
import spdlog

testq = queue.Queue()
hbq = queue.Queue()
candev = "can0"

def ResetBus(logger):
    os.WEXITSTATUS( os.system( f"sudo ifconfig {candev} down") )
    result = os.WEXITSTATUS( os.system( f"sudo ifconfig {candev} up") )
    logger.info( f"{TerminalColors.Red}Reset can bus operation returned: {result}{TerminalColors.RESET}" )


# starts all the canbus threads and creates the canbus interface
class CanbusControl( ) :
    def __init__(self, dev="can0", spd="500000", logger=None, filters=None ) :
        candev = dev
        self.dev = dev
        self.spd = spd
        if logger != None :
            self.logger = logger
        else:
            self.logger = spdlog.ConsoleLogger( "CAN Lib" )

        # the list of CAN bus ids the application interested in
        self.filters = filters
        # CAN bus object that handles the data transmission
        self.cbus = None
        # event thread that receives asynchronus CAN messages
        self.event_thread = None
        # command thread tha transmits RIAPS generated commands
        self.command_thread = None
        # thread the periodically transmits a heartbeat or keep alive message
        # this thread is option if not configure in the YAML file
        self.heartbeat_thread = None
        logger.info( f"{TerminalColors.Yellow}CanbusControl __init__ complete{TerminalColors.RESET}" )

    # Starts the Linux CAN bus interface using the desired device and speed
    # create the CAN bus object for bus interface
    # if startbus == True the function attempts to start the Linux canbus device
    # if loopback == True the canbus is not used and the internal queue is used for testing
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
            # if the bus is started then create the CAN bus 
            if result != 1 :
                try:   
                    self.cbus = can.ThreadSafeBus( channel=self.dev, bustype='socketcan', can_filters=self.filters )
                except OSError as oex :
                    self.logger.info( f"{TerminalColors.Red}CANBus device error: {oex}{TerminalColors.RESET}" ) 
        else:
            self.cbus = None
            
        return self.cbus

    # update the filter list
    def UpdateFilters(self, newfilters=None ):
        if self.cbus != None :
            self.cbus.set_filters( filters=newfilters )

    # creates and starts the canbus event handler thread
    def StartEventHandler(self, canport, filters=None):
        self.event_thread = CanbusEventNode( self.logger, canport, filters  )                    
        self.event_thread.start()

    # creates and starts the canbus command thread
    def StartCommandHandler(self, canport, filters=None):
        self.command_thread = CanbusCommandNode( self.logger, canport, filters  )                    
        self.command_thread.start()

    # creates and starts the canbus heartbeat thread
    def StartHeartbeatHandler(self, hbmsg, frequency = 1.0 ):
        self.CanbusHeartBeat = CanbusHeartBeat( self.logger, hbmsg, freq=frequency  )                    
        self.CanbusHeartBeat.start()
    
    # stops all running canbus threads
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

# Thread object that encapsulates the heartbeat functionality
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
    
    # allows the run run() loop to exit
    def Deactivate(self):
        self.heartbeat_active.clear()

    # sets a new heartbeat nessage that is transmitted on the canbus
    def hearbbeat_message(self, hbmsg ):
        self.heartbeat_skip.set()
        self.hbmsg = hbmsg
        self.logger.info( f"{TerminalColors.Yellow}New Heartbeat message:{self.hbmsg}{TerminalColors.RESET}" )
        self.heartbeat_skip.clear()

    # work loop for the heartbeat thread
    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Heartbeat Thread started{TerminalColors.RESET}" ) 
        self.logger.info( f"{TerminalColors.Yellow}Heartbeat message:{self.hbmsg}{TerminalColors.RESET}" )
        sleep_time = 1.0 / self.frequency
        if self.canbus != None :
            self.logger.info( f"{TerminalColors.Yellow}CAN Bus is available.{TerminalColors.RESET}" )
            while self.heartbeat_active.is_set() :
                # sleep for the time requested in the YAML configuration
                time.sleep( sleep_time )
                # send the heartbeat if not actively skipping
                if not self.heartbeat_skip.is_set() :
                    if self.hbmsg != None :
                        try:
                            self.canbus.send( self.hbmsg )
                        except can.CanOperationError as ex :
                            # ResetBus(self.logger)
                            # recover if the event the xmit buffer becomes full
                            self.canbus.flush_tx_buffer()
                            self.logger.info( f"{TerminalColors.Red}Heartbeat thread->CAN Bus Error: {ex}.{TerminalColors.RESET}" )
        else :
            # do nothing since the canbus object is not valid
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
            while self.heartbeat_active.is_set() :
                time.sleep( sleep_time )

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Heartbeat Thread stopped{TerminalColors.RESET}" ) 

# Thread object that encapsulates the Command handling operation for RIAPS commands sent
# out on the canbus
class CanbusCommandNode( threading.Thread ) :
    def __init__(self, logger, canport, canbus ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.commands_active = threading.Event()
        self.commands_active.set()
        self.timeout = (float(CanSys.CanbusSystem.Timeouts.Comm)/1000.0)
        self.canbus = canbus
        self.plug = None

    # the plug used to communicate with the RIAPS device
    def get_plug( self ):
        return self.plug

    # deactives the command thread and allows the run() function to exit
    def Deactivate(self):
        self.commands_active.clear()

    # thread work function
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
                    try:
                        self.canbus.send( msg )
                        # self.logger.info( f"{TerminalColors.Yellow}Command msg:{msg}{TerminalColors.RESET}" )
                    except can.CanOperationError as ex :
                        # ResetBus(self.logger)
                        # allow the system to recover in the event of a xmit buffer full error
                        self.canbus.flush_tx_buffer()
                        self.logger.info( f"{TerminalColors.Red}Command Thread->CAN Bus Error: {ex}.{TerminalColors.RESET}" )
                    
        else : # no canbus so just post commands to the test queue
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
            while self.commands_active.is_set() :
                s = dict( self.poller.poll( 1000.0 ) )
                if len(s) > 0 :
                    msg = self.plug.recv_pyobj()
                    testq.put( msg )

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Command Thread stopped{TerminalColors.RESET}" ) 

# Thread object that encapsulates functionality to post canbus received
# message events to RIAPS
# canbus is the canbus access object
# canport id the RIAPS port used to communicate to the RAIPS device
# logger is the RIAPS logger
class CanbusEventNode( threading.Thread ) :
    def __init__(self, logger, canport, canbus ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.events_active = threading.Event()
        self.events_active.set()
        self.timeout = (float(CanSys.CanbusSystem.Timeouts.Comm)/1000.0)
        self.canbus = canbus
        self.plug = None

    # returns the RIAPS device plug
    def get_plug( self ):
        return self.plug

    # deactives the event thread and allows the run() function to exit
    def Deactivate(self):
        self.events_active.clear()

    # thread work function
    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        self.poller = zmq.Poller()
        self.poller.register( self.plug, zmq.POLLIN )

        if self.canbus != None : # canbus communication is present and ready for messages
            self.logger.info( f"{TerminalColors.Yellow}CAN Bus is available.{TerminalColors.RESET}" )
            while self.events_active.is_set() :
                try:
                    msg = self.canbus.recv( timeout=self.timeout )
                    if msg != None :    
                        self.plug.send_pyobj( msg )
                except can.CanOperationError as ex:
                    self.logger.info( f"{TerminalColors.Red}Event Thread->CAN Bus Error: {ex}.{TerminalColors.RESET}" )
        else: # no canbus object is available
            self.logger.info( f"{TerminalColors.Red}CAN Bus not available!{TerminalColors.RESET}" )
            while self.events_active.is_set() :
                try:
                    # see if a loopback message is posted and just send it back to RIAPS
                    msg = testq.get( block=True, timeout=1.0 )
                    self.plug.send_pyobj( msg )
                except queue.Empty:
                    pass

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Event Thread stopped{TerminalColors.RESET}" ) 
