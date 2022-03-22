### CAN bus device interface for RIAPS

    This module is configured using a YAML file with setting for:
        - Bus device name
        - Bus speed
        - Request Message IDs
        - Published Message IDs

##### Sample configuration file is located in the CANApp example: 

https://github.com/RIAPS/interface.canbus.apps/tree/main/CANApp/cfg/sample.yaml

The contents are shown below

---
    BATT1: 
       Description: BATTERY CHARGER
       CAN:
          # CAN bus system device name
          device: can0
          # CAN bus speed, in Hertz
          speed: 500000 
          # hardware level filter to reduce data processing
          filters:
             # set can_id=0x000 and can_mask=0x000 to receive all messages
             a: {"can_id": 0x001, "can_mask": 0x3FF, "extended": False} 
             b: {"can_id": 0x002, "can_mask": 0x3FF, "extended": False}
             c: {"can_id": 0x003, "can_mask": 0x3FF, "extended": False}
             d: {"can_id": 0x004, "can_mask": 0x3FF, "extended": False}
             e: {"can_id": 0x005, "can_mask": 0x3FF, "extended": False}
             f: {"can_id": 0x006, "can_mask": 0x3FF, "extended": False}
             g: {"can_id": 0x007, "can_mask": 0x3FF, "extended": False}
          startbus: True  #if the OS starts the CAN bus this can be set to False
       Interval: 5000 # msec
       # RIAPS neighbors
       Neighbors: []
       #### Control the level of debug messages ####
       # 0=CRIT, 
       # 1=CRIT+ERR, 
       # 2=CRIT+ERR+WARN, 
       # 3=CRIT+ERR+WARN+INFO, 
       # 4=CRIT+ERR+WARN+INFO+DEBUG, 
       # >4=ALL
       Debuglevel: 10

       # define any hearbeat that should be updated automatically
       Heartbeat:
          freq: 8.0   #hz 
          id: 0x001
          dlen: 8
          remote: False
          extended: False
          # value entries describe the data location and format as read or written on the CAN bus
          data: [1,2,3,4,5,6,7,8]
          event: 799.0 > HB > 801.0
       # Parameter mapping for each allowed CAN message ID
       Parameters:
          BatteryInfo:
             mode: event
             id: 0x001
             dlen: 8
             remote: False
             extended: False
             # value entries describe the data location and format as read from the CAN device
             values:
                - { "name": "Current", "index": 0, "size": 4, "scaler": 1, "units": "Amperes", "format": ">f" }
                - { "name": "Temperature", "index": 4, "size": 2, "scaler": 10, "units": "Celcius", "format": ">h" }
                - { "name": "Voltage", "index": 6, "size": 2, "scaler": 10, "units": "Volts", "format": ">H" }  
          BatteryState:
             mode: event
             id: 0x002
             dlen: 8
             remote: False
             extended: False
             # value entries describe the data location and format as read from the CAN device
             values:
                - { "name": "Cycles", "index": 0, "size": 4, "scaler": 1, "units": "", "format": ">f" }
                - { "name": "Charge", "index": 4, "size": 2, "scaler": 10, "units": "Percent", "format": ">H" }  
          CurrentLimit:
             mode: response
             id: 0x003
             dlen: 8
             remote: False
             extended: False
             # value entries describe the data location and format as read from the CAN device
             values:
                - { "name": "Current", "index": 0, "size": 4, "scaler": 1, "units": "Amps", "format": ">f" }
          CurrentLimit=:
             mode: command
             id: 0x004
             dlen: 8
             remote: False
             extended: False
             # value entries describe the data location and format as written to the CAN device
             values:
                - { "name": "t1", "index": 0, "size": 4, "scaler": 1, "units": "Amps", "format": ">f" }
                - { "name": "t2", "index": 4, "size": 2, "scaler": 10, "units": "Amps", "format": ">H" }
          VoltageLimit=:
             mode: command
             id: 0x005
             dlen: 8
             remote: False
             extended: False
             # value entries describe the data location and format as written to the CAN device
             values:
                - { "name": "v1", "index": 0, "size": 4, "scaler": 1, "units": "Amps", "format": ">f" }
                - { "name": "v2", "index": 4, "size": 2, "scaler": 10, "units": "Amps", "format": ">H" }
          PowerLimit=:
             mode: query
             id: 0x006
             dlen: 8
             remote: False
             extended: False
             # value entries describe the data location and format as written to the CAN device
             values:
                - { "name": "p1", "index": 0, "size": 4, "scaler": 1, "units": "Watts", "format": ">f" }
                - { "name": "p2", "index": 4, "size": 4, "scaler": 1, "units": "Watts", "format": ">f" }
    #
    #
    # Data formatting specifiers as defined in python struct module
    #
    #
    #  Format   C Type               Python type  		Standard size
    #  x	      pad 			         byte			      
    #  c	      char			         byte	            1
    #  b	      signed char		      integer		      1
    #  B	      unsigned char	      integer		      1
    #  ?	      _Bool			         bool			      1
    #  h	      short			         integer		      2
    #  H	      unsigned short	      integer		      2
    #  i	      int			         integer		      4
    #  I	      unsigned int	      integer		      4
    #  l	      long			         integer		      4
    #  L	      unsigned long	      integer		      4
    #  q	      long long		      integer		      8
    #  Q	      unsigned long long	integer		      8
    #  n	      ssize_t			      integer		       
    #  N	      size_t			      integer		       
    #  f	      float			         float			      4
    #  d	      double			      float			      8
    #  s        string               string            max 8 bytes


##### CAN bus message format

      message
      (
         timestamp,                  
         arbitration_id,             
         is_extended_id,             
         is_remote_frame,            
         is_error_frame,             
         channel,                    
         dlc,                        
         data,                       
         is_fd,                      
         bitrate_switch,             
         error_state_indicator
      )

      THe CAN driver passes the python-can message structure to the RIAPS driver module via the inside port mechanism. Upon receiveing the message the       

        

