# riaps:keep_import:begin
import time

from riaps.run.comp import Component
from CanbusSystemSettings import CanbusSystem
import yaml
import spdlog
import capnp
#import device_capnp
import os
import datetime
import struct
import serial

import helper as helper


# riaps:keep_import:end


class CanbusDevice(Component):
    # riaps:keep_constr:begin
    def __init__(self, config):
        super(CanbusDevice, self).__init__()

        self.CanbusConfigError = True

        self.poll_exit = False

        self.logger.info("starting")

        self.pid = os.getpid()

        try:
            if os.path.exists( config ) :
                # Load config file to interact with Modbus device
                with open(config, 'r') as cfg:
                    self.cfg = yaml.safe_load(cfg)

                self.CanbusConfigError = False
            else:
                self.logger.info( 'Configuration file does not exist [{0}].'.format( config ) )

        except OSError:
            self.logger.info( 'File I/O error [{0}].'.format( config ) )

        if not self.CanbusConfigError :
            try : # handle dictionary key errors
                pass                    
            except KeyError as kex:
                self.logger.info(f"CANBus configuration is missing required setting: {kex}")    
                self.CanbusConfigError = True

        else:
            pass # Device cannot operate due to configuration error

    # riaps:keep_constr:end

    # riaps:keep_device_port:begin
    def on_device_port(self):
        # receive
        start = datetime.datetime.now()  # measure how long it takes to complete query
        msg_bytes = self.device_port.recv()  # required to remove message from queue
        # msg = device_capnp.DeviceQry.from_bytes(msg_bytes)

    # riaps:keep_device_port:end

    # riaps:keep_poller:begin
    def on_poller(self):
        """Poll all variable names specified in yaml file"""

        now = self.poller.recv_pyobj()
        if self.dvc["debugMode"]:
            self.logger.info(f"on_poller now: {now}")
            
    # riaps:keep_poller:end

    # riaps:keep_impl:begin
    def handleActivate(self):
        if not self.dvc["poll"]:
            if self.poller != None:
                self.poller.halt()
                self.logger.info("No parameters configured for polling. Modbus poller timer has been stopped!")
        else:    
            if self.poller != None:
                cur_period = self.poller.getPeriod() * 1000
                self.poller.setPeriod(self.interval / 1000.0)
                new_period = self.poller.getPeriod() * 1000
                self.logger.info(f"Modbus Poller Interval changed from {cur_period} msec to {new_period} msec")
                comm_time_out = CanbusSystem.Timeouts.Comm
                self.logger.info( f"Modbus TCP device comm timeout is {comm_time_out} msec" )  
                
                if new_period < comm_time_out :
                    self.logger.info( f"Modbus Poller Interval is less than communication timeout of {comm_time_out} msec. " )  
                    self.disable_polling()

   # Should be called before __destroy__ when app is shutting down.  
   # this does not appear to work correctly       
    def handleDeactivate( self ):
        self.logger.info( "Deactivating Modbus Device" )
        self.logger.info( f"self.master is {self.master}" )

    # Format and error event message that will get passed to an upper level
    # RIAPS component
    def error( self, evt, error, vals, errnum = -1, et=None ):
        evt.device = self.device_name
        evt.event = 'ERROR'
        evt.error = errnum
        evt.values = [-1.0, ]
        evt.names = [f"{error} ({vals})"]
        evt.units = ['ERROR', ]
        if et != None:
            evt.et = et
        return evt

    # Clean up and shutdown 
    def __destroy__(self):
        if self.poller.running() == True :
            self.disable_polling()
            self.poller.terminate() 

        self.logger.info("__destroy__ complete for - %s" % self.device_name)    
 
    # Do not allow the polling loop to send messages to the modbus device
    def disable_polling(self):
        self.logger.info("Disabling modbus polling for - %s" % self.device_name)
        self.poll_exit = True

    # Allow the polling loop to send messages to the modbus device
    def enable_polling(self):
        self.logger.info("Enabling modbus polling for - %s" % self.device_name)
        self.poll_exit = False

    # set an individual bit on a value
    def set_bit(self, value, bit):
        """ Sets a bit in the data 'value' at position index specified by 'bit' """
        return value | (1 << bit)

    # clear an individual bit on a value
    def clr_bit(self, value, bit):
        """ Clears a bit in the data 'value' at position index specified by 'bit' """
        return value & ~(1 << bit)

# riaps:keep_impl:end