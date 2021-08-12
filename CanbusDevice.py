import time
from CanbusSystemSettings import CanbusSystem
import yaml
import os
import datetime
import struct
import serial
import helper as helper

class CanbusDevice:
    def __init__(self, config):

        print("Initializing CAN bus device.")

        self.CanbusConfigError = True

        self.poll_exit = False

        self.pid = os.getpid()

        try:
            if os.path.exists( config ) :
                # Load config file to interact with Modbus device
                with open(config, 'r') as cfg:
                    self.cfg = yaml.safe_load(cfg)

                self.CanbusConfigError = False
            else:
                print( 'Configuration file does not exist [{0}].'.format( config ) )

        except OSError:
            print( 'File I/O error [{0}].'.format( config ) )

        if not self.CanbusConfigError :
            try : # handle dictionary key errors
                pass                    
            except KeyError as kex:
                self.logger.info(f"CANBus configuration is missing required setting: {kex}")    
                self.CanbusConfigError = True

        else:
            pass # Device cannot operate due to configuration error

    # Clean up and shutdown 
    def __destroy__(self):
        print("__destroy__ complete for - %s" % self.device_name)    
 
