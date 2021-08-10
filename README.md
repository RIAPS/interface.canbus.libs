# CAN Device simulation

### Required Raspberry Pi3 
### PiCAN2 module attached and connected to an operational CAN bus
    Note: Jumper JP3 is required on at least 2 modules connected to a single CAN bus.

### Complete all updates and upgrades

    $ sudo apt-get update
    $ sudo apt-get upgrade
    $ pip3 install python-can


### Edit /boot/firmware/usercfg.txt 
   
    $ sudo nano /boot/firmware/usercfg.txt

    Add the following lines:

    dtparam=spi=on
    dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
    dtoverlay=spi-bcm2835-overlay  

### Reboot

    $ sudo reboot

### After restart bring up the CAN interface

    $ sudo ip link set can0 up type can bitrate 500000  

### Run CanbusSim.py   

    $ python3 CanbusSim.py --CH can0 --ID 0x043 --DATA 0,25,0,1,3,0,150 --FREQ 1.0 --IDLIST 0x044

    --CH = The can channel (device).
    --ID = The message ID to publish on the CAN bus.
    --DATA = List of data bytes to send with the message ID.
    --FREQ = The frequency at which to publish the message.
    --IDLIST = Filter for received messages IDs that should be printed.

