# CAN bus device interface for RIAPS

## Overview
The library provides a device component implementation of canbus for the RIAPS platform.
An example of an application using this library is found in the `example` folder.
The designed use model is to include in the (dot)riaps application specification file a device component with the following content in addition to other elements required by the application:

```text
message CANQry;
message CANAns;
message CANCommands;
message CANEvents;
device Driver(config)
    {
        ans canbusqryans: (CANQry, CANAns) timed;
        inside canport;
        sub command_can_sub : CANCommands ;			// subscribe port for CAN commands
        timer timeout;
        pub event_can_pub : CANEvents ;				// Publish port for CAN events
    }
component Example()
    {
        qry canbusqryans: (CANQry, CANAns) timed;
        pub command_can_pub: CANCommands;
    }
```
Note: The device name `Driver` may be changed, however the ports and messages are required as shown. 

The usage also requires a yaml configuration file for each device. An example can be found [here](https://github.com/RIAPS/interface.canbus.libs/blob/package/example/cfg/bbb_canbus_example.yaml).

## Interfaces
The format for send these messages is a set consisting of the **Parameter** of interest and a dictionary of that parameters values. In the provided [example](https://github.com/RIAPS/interface.canbus.libs/tree/package/example) to send and format a query message to the canbus to write to the `PowerLimit` parameter one can use the following syntax:
```python
self.canbusqryans.send_pyobj("PowerLimit=", {"p1": 12.34, "p2": 56.0})
```
The format of the message returned from the qry interface is a list of dictionaries of the form 
```python
[{ "name", "value", "units" }, ...]
```

For an example of each interface refer back to the above example.
* To send asynchronous query messages (see the `Example` component) to the canbus use the `canbusqryans` port. 
* To publish command messages (see the `Example` component) to the canbus use the`command_can_pub` port. 


* When there is a device event it is published on the `event_can_pub` port. The events included in this library are canbus communication timeouts, responses to published commands, and a messages when a device has been configured.  

# Installation
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
4. On the BBB run: `cansend can1 456#00FFAA5501020305`
5. The RPi should write the following message to the terminal:
```
can1  456   [8]  00 FF AA 55 01 02 03 05
```
A similar test can be done, running `candump` and `cansend` on the same board, but the wired connection to another board needs to be present.

# Library tests
To run the included test example the `interface.canbus.libs/example/canbus_example.depl` and `required_clients` in `interface.canbus.libs/tests/test_canbus.py` must be updated to reflect your canbus device ip address. Then tests can be run with:
```commandline
pytest -s .
```


# Application Developer Notes
The canbus device configuration YAML file must be defined on a per-device basis. The developer must create a class that inherits the `CanbusDevice` class. No additional behavior is required but the class may be extended as needed.  

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
* Cannot use editable packages for riaps components because they do not have access. 

# Notes
[Examples of canbus database files](https://github.com/commaai/opendbc)

[A simplistic diagram of the driver](https://github.com/RIAPS/interface.canbus.apps/blob/main/Images/CANbus%20App.png)

# Roadmap
* isolate canbus functionality from riaps specific requirements.
* test remaining interfaces
  * command_can_pub
  * event_can_pub
  * timeout
* explain the canbus simulator in `tests/simulator`. 