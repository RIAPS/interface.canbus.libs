# CAN bus device interface for RIAPS

## Install canbus utils
```commandline
sudo apt install can-utils
```

## Configure and enable CANBUS interface.
* Check that CAN interfaces are available. Note that while a Beaglebone black has the capability to support two CAN interfaces (can0 and can1) the default pin configuration only works for can1. A raspberry pi uses can0. 
```commandline
$ ip addr
3: can1: <NOARP,ECHO> mtu 16 qdisc noop state DOWN group default qlen 10
    link/can 
```

* If interface is down (`state DOWN`):
```commandline
$ sudo ip link set can1 type can bitrate 500000
$ sudo ip link set can1 up 
$ ip addr | grep can 
5: can1: <NOARP,UP,LOWER_UP,ECHO> mtu 16 qdisc pfifo_fast state UP group default qlen 10
    link/can 
```

## Start Automatically
Edit `/etc/systemd/network/80-can.network`
```
[Match]
Name=can*

[Link]
RequiredForOnline=no

[CAN]
BitRate=500K
RestartSec=500ms
```
Reboot. Note: You may have to wait ~10 seconds for the `state` to be `UP`.
```commandline
$ ip addr
5: can0: <NOARP,UP,LOWER_UP,ECHO> mtu 16 qdisc pfifo_fast state UP group default qlen 10
    link/can 
6: can1: <NOARP,UP,LOWER_UP,ECHO> mtu 16 qdisc pfifo_fast state UP group default qlen 10
    link/can 
```

## Test that CANBUS interfaces are functional
Note: These instructions were created using a [BeagleBone Comms Cape](https://www.digikey.com/en/products/detail/ghi-electronics-llc/COMCPE-BBBCAPE/8567318) for BBB and a raspberry pi 3b+ with the [PiCAN2 CAN-Bus Board]. To use a raspberry pi 4 a PiCAN3 is required and may necessitate other changes. 

1. With the boards powered off, connect with wires the RPi and BBB capes.
   1. CAN_H -- CAN_H
   1. CAN_L -- CAN_L
   1. GND -- GND
2. Power on the boards
3. On the RPi run: `candump can0`
4. On the BBB run: `cansend can0 456#00FFAA5501020305`
5. The RPi should write the following message to the terminal:
```
can1  456   [8]  00 FF AA 55 01 02 03 05
```
A similar test can be done, running `candump` and `cansend` on the same board, but the wired connection to another board needs to be present.

# Application Developer Notes

An application using this module requires a YAML file which provides settings for:
* Bus device name
* Bus speed
* Request Message IDs
* Published Message IDs

[Sample configuration file](https://github.com/RIAPS/interface.canbus.apps/tree/main/CANApp/cfg/sample.yaml) is located in the CANApp example.


# Troubleshooting

Q: `ip addr | grep can` does not return any result?

A: If the overlay was just enabled or added, wait a few minutes after boot for the interfaces to be discovered. If you run `dmesg | grep -i can` and see the following this is likely the solution.
```commandline
$ dmesg | grep -i can
[   46.344696] CAN device driver interface
[   46.532384] c_can_platform 481cc000.can: c_can_platform device registered (regs=4e5fa75b, irq=48)
[   46.605519] c_can_platform 481d0000.can: c_can_platform device registered (regs=0c612c34, irq=49)
[   97.135663] c_can_platform 481d0000.can can1: bit-timing not yet defined
[   97.135698] c_can_platform 481d0000.can can1: failed to open can device
```
Note: The overlay used by the Comms cape A2 can be found at `/opt/source/dtb-5.10-ti/src/arm/overlays/BBORG_COMMS-00A2.dts` and is part of the ubuntu distribution. 

Note:  
The Comms cape A2 overlay is part of the ubuntu distribution and is loaded by the `/boot/uEnv.txt` by the line:
```
enable_uboot_cape_universal=1
```

Q: The `config-pin` commands do not work for `p9.24` and `p9.26`?

A: This is because when the Comms cape A2 is attached its overlay is loaded and [when an overlay takes a pin for a specific function, the overlay disables the corresponding config-pin entry.](https://forum.digikey.com/t/pin-mux-p9-26-not/8750/2)
```commandline
 $ config-pin p9.24 can
 ERROR: open() for /sys/devices/platform/ocp/ocp:P9_24_pinmux/state failed, No such file or directory
```

# Package Notes

* I'm not sure if the `__init__.py` file under `interfaces` is required.
* used `[tool.setuptools.packages.find]` because otherwise only interfaces is imported. 
* Cannot use editable packages for riaps components because they do not have access. 


# Ignore below

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

The message structure is found in the [python-can project](https://github.com/hardbyte/python-can).


During normal operation, the CAN driver passes the python-can message structure to the RIAPS driver module via the inside port mechanism. Upon receiving the message
the driver then posts the message as an EVENT or ANSWER-to-QUERY.   

[A simplistic diagram of the driver](https://github.com/RIAPS/interface.canbus.apps/blob/main/Images/CANbus%20App.png)   



The sample CANApp is defined as follows:

https://github.com/RIAPS/interface.canbus.apps/blob/main/CANApp/CANApp.riaps

        app CANApp
        {
	        message CANQry;
	        message CANAns;
	        message CmdQry;
	        message CmdAns;
	        message CANCommands;
	        message CANEvents;
	        message CANControl;
	        message LogMessages;
	        message CmdMessages;
	        message CmdEvents;
	        message CfgSignal;

	        library cfg;
	        library canbuslibs;
	        library res;

	        component DataLogger()
	        {
      	        sub data_logging_sub : LogMessages;			// Receive logging messages		
      	        sub config_signal_sub : CfgSignal;	
	        }
		
	        component Commander()
	        scheduler priority;
	        {
		        qry cmdqryans: (CmdQry, CmdAns) timed;
      	        pub data_logging_pub : LogMessages;			// publish logging messages	
      	        pub command_injector_pub : CmdMessages;		// Send cmd receive test commands	
      	        sub config_signal_sub : CfgSignal;	
		        sub cmd_events_sub : CmdEvents;
		        timer cmdtimer 5000;
	        }	
	
	        // component
            component Scanner() 
	        scheduler priority;
            {
		        ans cmdqryans: (CmdQry, CmdAns) timed;
		        qry canbusqryans: (CANQry, CANAns) timed;
      	        sub event_can_sub : CANEvents ;				// subscribe port for CAN events
      	        sub command_injector_sub : CmdMessages;		
      	        pub command_can_pub : CANCommands ;			// publish port for CAN commands
      	        pub data_logging_pub : LogMessages;			// publish logging messages		
      	        pub config_signal_pub : CfgSignal;
		        pub cmd_events_pub : CmdEvents;
		        timer oneshot 2500;
		        timer periodic 5000;
            }
	
            device Driver(config) 
            {
    	        inside canport;
    	        timer timeout 1000;
       	        sub command_can_sub : CANCommands ;			// subscribe port for CAN commands
      	        pub event_can_pub : CANEvents ;				// Publish port for CAN events
		        ans canbusqryans: (CANQry, CANAns) timed;
            }
	
	        actor CANBus(config) 
	        {
		        local CANCommands, CANEvents, CANControl, CANQry, CANAns;
		        { 
			        scanner : Scanner();
			        driver  : Driver(config=config);
		        }
	        }
	
	        actor CANLogger()
	        {
		        {
			        can_logger : DataLogger();
		        }
	        }	
	
	        actor Injector()
	        {
		        {
			        Injector : Commander();
		        }
	        }	
	
        }
        

