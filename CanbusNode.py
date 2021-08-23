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

class CanbusNode( threading.Thread ) :
    def __init__(self, logger, canport, filters=None ) :
        threading.Thread.__init__( self )
        self.logger = logger
        self.canport = canport
        self.active = threading.Event()
        self.active.set()
        self.plug = None
        self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)
        self.filters = filters
        self.canbus = None
        
        try:   
            self.canbus = can.interface.Bus(channel='can0', bustype='socketcan_native', can_filters=self.filters )
        except OSError as oex :
            self.logger.info(f"{TerminalColors.Red}CANBus device error: {oex}{TerminalColors.RESET}")    

    def Deactivate(self):
        self.active.clear()

    def run(self):
        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Thread started{TerminalColors.RESET}" ) 
        self.plug = self.canport.setupPlug(self)
        self.poller = zmq.Poller()
        self.poller.register( self.plug, zmq.POLLIN )

        while self.active.is_set() :
            if self.canbus != None :
                msg = self.canbus.recv( timeout=self.timeout )
            else:
                msg = can.Message(arbitration_id=0x001,
                                  data=[0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF ],
                                  timestamp=dt.datetime.timestamp( dt.datetime.now() ))
                time.sleep(self.timeout)   
                
            self.plug.send_pyobj( msg )

        self.logger.info( f"{TerminalColors.Yellow}CAN Bus Thread stopped{TerminalColors.RESET}" ) 




# class CanbusDevice():
#     def __init__(self, config, logger):
#         self.config = config
        
#         self.logger = logger
        
#         self.CanbusConfigError = True

#         self.poll_exit = False

#         self.logger.info(f"{TerminalColors.Yellow}Starting CanbusDevice...{TerminalColors.RESET}" )

#         self.pid = os.getpid()

#         self.bus = None
        
#         self.canTimeout = CanbusSystem.Timeouts.Comm
        
#         self.eventthread = None
        
#         self.recvQueue = queue.Queue()

#         try:
#             if os.path.exists( self.config ) :
#                 with open(config, 'r') as cfg:
#                     self.cfg = yaml.safe_load(cfg)

#                 self.CanbusConfigError = False
#             else:
#                 self.logger.info( '{1}Configuration file does not exist [{0}].{2}'.format( self.config, 
#                                                                                            TerminalColors.Red, 
#                                                                                            TerminalColors.RESET) )

#         except OSError:
#             self.logger.info( f"File I/O error [{config}]." )

#         if not self.CanbusConfigError :
#             try : # handle dictionary key errors
#                 self.logger.info( f"Configuration file : {self.config}." )                    
#                 #self.logger.info( f"Configuration data - {self.cfg}." )
#                 try:   
#                     self.bus = can.interface.Bus(channel='can0', bustype='socketcan_native' )
#                 except OSError as oex :
#                     self.bus = None
#                     self.logger.info(f"CANBus device error: {oex}")    

#                 self.eventthread = CANMsgThread( self.bus, self.cfg, self.logger, self.recvQueue )
#                 self.eventthread.start()
#             except KeyError as kex:
#                 self.logger.info(f"CANBus configuration is missing required setting: {kex}")    
#                 self.CanbusConfigError = True
#         else:
#             pass # Device cannot operate due to configuration error
    
        
#     def __destroy__(self): 
#         if self.eventthread != None :
#             self.eventthread.Deactivate()
#             while self.eventthread.is_alive() :
#                 pass
        
#         self.logger.info("__destroy__: CanbusDevice has exited cleanly")
        
# class CANMsgThread( threading.Thread ):
#     def __init__(self, canbus, msglist, logger, recvQ ):
#         threading.Thread.__init__(self)
#         self.recvQ = recvQ
#         self.logger = logger
#         self.msglist = msglist
#         self.canbus = canbus
#         self.active = threading.Event()
#         self.active.set()
#         self.timeout = (float(CanbusSystem.Timeouts.Comm)/1000.0)

#     def Deactivate(self):
#         self.active.clear()
#         self.logger.info( "Deactivating CAN bus receive thread..." )
        
#     # helper function to execute the threads
#     def run(self):
#         count = 0
#         self.logger.info( "CAN bus receive thread is running." )
#         while self.active.is_set() :
#             if self.canbus != None :
#                 msg = self.canbus.recv( timeout=self.timeout )
#             else:
#                 msg = None
#                 time.sleep(self.timeout)   
                
#             if( msg != None ) :
#                 try:
#                     self.recvQ.put( msg, block=False )
#                 except queue.Full:
#                     self.logger.info( f"{TerminalColors.Red}Received CAN message [{msg}] could not be queued.{TerminalColors.RESET}")
#             else:
#                 #send a counter if no canbus is available
#                 if self.canbus == None :
#                     try:
#                         self.recvQ.put( count, block=False )
#                         count = count + 1
#                     except queue.Full:
#                         self.logger.info( f"{TerminalColors.Red}Received CAN message [{msg}] could not be queued.{TerminalColors.RESET}")


#         self.logger.info( "CAN bus receive thread has exited." )
        
    