# CAN Device simulation

Run this on a bbb and the current app configuration wil lwork without timeouts. 
```python
python3 Charger.py --CH can1 --ID 0x006 --DATA 65,69,112,164,0,245,2,10 --FREQ 0.2 --MODE SR
```

### Required Raspberry Pi3 
### PiCAN2 module attached and connected to an operational CAN bus
    Note: Jumper JP3 is required on at least 2 modules connected to a single CAN bus.

### Complete all updates and upgrades.

    $ sudo apt-get update
    $ sudo apt-get upgrade
    
### Install python-can
    $ pip3 install python-can

### Edit /boot/firmware/usercfg.txt 

    Add the following lines:

    dtparam=spi=on # this is optional on riaps raspberry PI images
    dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
    dtoverlay=spi-bcm2835-overlay  

### Reboot

    $ sudo reboot

### After restart bring up the CAN interface

    $ sudo ip link set can0 up type can bitrate 500000  

### Run CanbusSim.py   

    $ python3 CanbusSim.py --CH can0 --ID 0x043 --DATA 0,25,0,1,3,0,150 --FREQ 1.0 --IDLIST 0x044 --FILTER 0x3FF,0x44 --MODE SR

    --CH = The can channel (device).
    --ID = The message ID to publish on the CAN bus.
    --DATA = List of data bytes to send with the message ID.
    --FREQ = The frequency at which to publish the message.
    --IDLIST = High level Filter for received messages IDs that should be printed.
    --MODE = Send(S), Receive(R), Both(SR)
    --FILTER =  CAN Bus low level filter (can_mask, can_id). 
                Note 1: Discards unwanted messages at the lowest level of the CAN bus driver.
                Note 2: Match occurs if: <received_can_id> & can_mask == can_id & can_mask.



