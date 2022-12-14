# riaps:keep_import:begin
import can
import datetime as dt
import os
import spdlog
import struct
import time
import yaml

from riaps.run.comp import Component
from canbus.libs.CanbusNode import CanbusEventNode, CanbusCommandNode, CanbusControl, CanbusHeartBeat
from canbus.libs.Debug import debug
import canbus.libs.Terminal as tc


# riaps:keep_import:end

class Driver(Component):

    # riaps:keep_constr:begin
    def __init__(self, config):
        super(Driver, self).__init__()
        debug(self.logger, f"Configuration file:{config}", level=3)
        self.can_event_thread = None
        self.can_command_thread = None
        self.can_heartbeat_thread = None
        self.can_node_cfg = None
        self.cannodename = None
        self.filters = None
        self.candev = None
        self.canspeed = 500000
        self.filterlist = list()
        self.startbus = False
        self.cancontrol = None
        self.cmdplug = None
        self.evtplug = None
        self.parameters = None
        self.bus_setup = None
        self.interval_timer = 10000
        self.query_id = None
        self.sendmsg = None
        self.hb_msg = None
        self.logger.set_level(spdlog.LogLevel.TRACE)

        try:
            if os.path.exists(config):
                # Load config file
                with open(config, 'r') as cfg:
                    self.cfg = yaml.safe_load(cfg)
            else:
                self.cfg = None
                debug(self.logger, f"Configuration file does not exist:{config}", level=spdlog.LogLevel.CRITICAL)
        except OSError:
            debug(self.logger, f"File I/O error:{config}", level=spdlog.LogLevel.CRITICAL)

        if self.cfg is not None:
            keys = list(self.cfg.keys())
            self.cannodename = keys[0]
            self.can_node_cfg = self.cfg[self.cannodename]
            self.interval_timer = self.can_node_cfg["Interval"]
            self.bus_setup = self.can_node_cfg["CAN"]
            self.parameters = self.can_node_cfg["Parameters"]
            self.debug_level = self.can_node_cfg["Debuglevel"]
            if self.debug_level == 0:
                self.logger.set_level(spdlog.LogLevel.CRITICAL)
            elif self.debug_level == 1:
                self.logger.set_level(spdlog.LogLevel.ERR)
            elif self.debug_level == 2:
                self.logger.set_level(spdlog.LogLevel.WARN)
            elif self.debug_level == 3:
                self.logger.set_level(spdlog.LogLevel.INFO)
            elif self.debug_level == 4:
                self.logger.set_level(spdlog.LogLevel.DEBUG)
            else:
                self.logger.set_level(spdlog.LogLevel.TRACE)

            # debug( self.logger, f"logging level is {self.logger.get_level()}", level=spdlog.LogLevel.CRITICAL )

            debug(self.logger, f"CAN Node Name: {self.cannodename}", level=spdlog.LogLevel.TRACE)
            self.startbus = self.bus_setup["startbus"]
            debug(self.logger, f"CAN Bus Start: {self.startbus}", level=spdlog.LogLevel.TRACE)
            self.candev = self.bus_setup["device"]
            debug(self.logger, f"CAN Bus Device: {self.candev}", level=spdlog.LogLevel.TRACE)
            self.canspeed = self.bus_setup["speed"]
            debug(self.logger, f"CAN Bus Speed: {self.canspeed}", level=spdlog.LogLevel.TRACE)
            self.filters = self.bus_setup["filters"]
            for f in self.filters:
                afilter = self.filters[f]
                self.filterlist.append(afilter)
                mask = afilter["can_mask"]
                mid = afilter["can_id"]
                ext = afilter["extended"]
                debug(self.logger, f"Filter {f}=0x{hex(mask)[2:].zfill(3)}, 0x{hex(mid)[2:].zfill(3)}, {ext}",
                      level=spdlog.LogLevel.TRACE)

        debug(self.logger, f"__init__() complete", level=spdlog.LogLevel.INFO)

    # riaps:keep_constr:end

    # riaps:keep_canbusqryans:begin
    def on_canbusqryans(self):
        cmdriaps = self.canbusqryans.recv_pyobj()
        (query_id, dta, rtr, ext) = cmdriaps
        cmdmsg = can.Message(timestamp=dt.datetime.timestamp(dt.datetime.now()),
                             dlc=len(dta),
                             arbitration_id=query_id,
                             data=dta,
                             is_remote_frame=rtr,
                             is_extended_id=ext)
        self.query_id = query_id
        self.canport.set_identity(self.canport.get_plug_identity(self.cmdplug))
        self.canport.send_pyobj(cmdmsg)
        self.sendmsg = cmdriaps
        value = (query_id, dta)
        debug(self.logger, f"Driver->CANBus:Query:{value}", level=spdlog.LogLevel.TRACE)
        self.timeout.setPeriod(0.250)
        self.timeout.launch()

    # riaps:keep_canbusqryans:end

    # riaps:keep_canport:begin
    def on_canport(self):
        msg = self.canport.recv_pyobj()
        value = self.Format(msg.arbitration_id, msg.data)
        dl = list(msg.data)
        if self.queryid == msg.arbitration_id:
            self.timeout.halt()
            self.query_id = None
            self.canbusqryans.send_pyobj(value)
            debug(self.logger, f"Canbus->Driver:Answer:{(msg.arbitration_id, dl)}", level=spdlog.LogLevel.TRACE)
        else:
            self.event_can_pub.send_pyobj(value)
            debug(self.logger, f"Canbus->Driver:Event:{(msg.arbitration_id, dl)}", level=spdlog.LogLevel.TRACE)
        # riaps:keep_canport:end

    # riaps:keep_command_can_sub:begin
    def on_command_can_sub(self):
        cmdriaps = self.command_can_sub.recv_pyobj()
        (arbitration_id, dta, rtr, ext) = cmdriaps
        cmdmsg = can.Message(timestamp=dt.datetime.timestamp(dt.datetime.now()),
                             dlc=len(dta),
                             arbitration_id=arbitration_id,
                             data=dta,
                             is_remote_frame=rtr,
                             is_extended_id=ext)
        self.canport.set_identity(self.canport.get_plug_identity(self.cmdplug))
        self.canport.send_pyobj(cmdmsg)
        debug(self.logger, f"Driver->CANBus:{cmdriaps}", level=spdlog.LogLevel.TRACE)

    # riaps:keep_command_can_sub:end

    # riaps:keep_timeout:begin
    def on_timeout(self):
        now = self.timeout.recv_pyobj()
        self.timeout.halt()
        value = ("timeout", self.sendmsg)
        self.event_can_pub.send_pyobj(value)
        debug(self.logger, f"Driver communication timeout triggered.", level=spdlog.LogLevel.CRITICAL)

    # riaps:keep_timeout:end

    # riaps:keep_impl:begin
    def __destroy__(self):
        if self.can_heartbeat_thread is not None:
            self.can_heartbeat_thread.Deactivate()
            debug(self.logger, f"Deactivaiting hearbeat thread...", level=spdlog.LogLevel.TRACE, color=tc.Yellow)
        if self.can_event_thread is not None:
            self.can_event_thread.Deactivate()
            debug(self.logger, f"Deactivaiting event thread...", level=spdlog.LogLevel.TRACE, color=tc.Yellow)
        if self.can_command_thread is not None:
            self.can_command_thread.Deactivate()
            debug(self.logger, f"Deactivaiting command thread...", level=spdlog.LogLevel.TRACE, color=tc.Yellow)

        if self.can_heartbeat_thread.is_alive():
            self.can_heartbeat_thread.join(timeout=10.0)
            if self.can_heartbeat_thread.is_alive():
                debug(self.logger, f"Failed to terminate CAN bus hearbeat thread!", level=spdlog.LogLevel.CRITICAL)

        if self.can_event_thread.is_alive():
            self.can_event_thread.join(timeout=10.0)
            if self.can_event_thread.is_alive():
                debug(self.logger, f"Failed to terminate CAN bus event thread!", level=spdlog.LogLevel.CRITICAL)

        if self.can_command_thread.is_alive():
            self.can_command_thread.join(timeout=10.0)
            if self.can_command_thread.is_alive():
                debug(self.logger, f"Failed to terminate CAN bus command thread!", level=spdlog.LogLevel.CRITICAL)

        debug(self.logger, f"__destroy__() complete", level=spdlog.LogLevel.INFO)

    def handleActivate(self):
        self.timeout.halt()
        self.cancontrol = CanbusControl(dev=self.candev, spd=self.canspeed, logger=self.logger, filters=self.filterlist)
        cbus = self.cancontrol.CreateCANBus()

        if cbus is not None:
            # start the canbus threads
            self.can_event_thread = CanbusEventNode(self.logger, self.canport, cbus)
            self.can_command_thread = CanbusCommandNode(self.logger, self.canport, cbus)
            # see if a heartbeat is configured
            if "Heartbeat" in self.can_node_cfg.keys():
                hbparm = self.can_node_cfg["Heartbeat"]
                freq = float(hbparm["freq"])
                arbitration_id = int(hbparm["id"])
                dlen = int(hbparm["dlen"])
                rtr = bool(hbparm["remote"])
                ext = bool(hbparm["extended"])
                dta = hbparm["data"]

                self.hb_msg = can.Message(timestamp=dt.datetime.timestamp(dt.datetime.now()),
                                          dlc=dlen,
                                          arbitration_id=arbitration_id,
                                          data=dta,
                                          is_remote_frame=rtr,
                                          is_extended_id=ext)

                self.can_heartbeat_thread = CanbusHeartBeat(self.logger, self.hb_msg, cbus, freq)
                self.can_heartbeat_thread.start()
            else:
                debug(self.logger, f"No heartbeat message configured, heartbeat was thread not created.",
                      level=spdlog.LogLevel.WARN)

            self.can_event_thread.start()
            self.can_command_thread.start()
            # delay to let the threads start an configure the comm plugs
            done = False
            while not done:
                self.cmdplug = self.can_command_thread.get_plug()
                self.evtplug = self.can_event_thread.get_plug()
                if self.cmdplug is None or self.evtplug is None:
                    time.sleep(0.100)
                else:
                    done = True
                    # signal components that threads and connections are in active
            value = ("config", [self.can_node_cfg, ])
            self.event_can_pub.send_pyobj(value)
        else:
            debug(self.logger, f"Error in CAN bus configuration", level=spdlog.LogLevel.CRITICAL)

        debug(self.logger, f"handleActivate() complete", level=spdlog.LogLevel.INFO)

    def get_bus_setup(self):
        return self.bus_setup

    def get_parameters(self):
        return self.parameters

    def get_config(self):
        return self.can_node_cfg

    # format the CAN message values
    def Format(self, msgid, data):
        mode = None
        result = []
        params = self.parameters
        for p in params:
            id = int(params[p]["id"])
            if id == msgid:
                len = int(params[p]["dlen"])
                values = params[p]["values"]
                mode = params[p]["mode"]
                for v in values:
                    name = v["name"]
                    index = int(v["index"])
                    size = int(v["size"])
                    scaler = int(v["scaler"])
                    units = v["units"]
                    format = v["format"]
                    val = []
                    for i in range(index, index + size):
                        val.append(data[i])
                        # convert to float ( tuple )
                    cvtval = struct.unpack(format, bytearray(val))
                    # apply scaling
                    cvtval = float(cvtval[0])
                    cvtval = cvtval / scaler
                    # add the result to the list of dictionaries
                    result.append({"name": name, "value": cvtval, "units": units})
        # returns a tuple with mode and dictionaries in the form { name, value, units }
        return mode, result

# riaps:keep_impl:end
