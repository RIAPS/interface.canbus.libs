# riaps:keep_import:begin
import can
import datetime as dt
import os
import spdlog
import struct
import time
import yaml

from riaps.run.comp import Component
from riaps.interfaces.canbus.libs.CanbusNode import (
    CanbusEventNode,
    CanbusCommandNode,
    CanbusControl,
    CanbusHeartBeat,
)
from riaps.interfaces.canbus.libs.Debug import debug
import riaps.interfaces.canbus.libs.Terminal as TermColor
from riaps.interfaces.canbus.utils import build_command


# riaps:keep_import:end
class CanbusDevice(Component):
    # riaps:keep_constr:begin
    def __init__(self, config):
        super().__init__()
        self.logger.info(f"start can 1")
        try:
            if os.path.exists(config):
                # Load config file
                with open(config, "r") as f:
                    cfg = yaml.safe_load(f)
            else:
                cfg = None
        except OSError:
            debug(
                self.logger, f"File I/O error:{config}", level=spdlog.LogLevel.CRITICAL
            )

        if cfg is None:
            debug(
                self.logger,
                f"Configuration failed. Configuration file does not exist:{config}",
                level=spdlog.LogLevel.CRITICAL,
            )
            return

        self.cfg = cfg
        self.logger.set_level(cfg["Debuglevel"])
        self.canbus_timeout = cfg["CANBUS_CONFIG"]["timeout"]

        debug(self.logger, f"CAN Node Name: {cfg['Name']}", level=spdlog.LogLevel.TRACE)
        debug(
            self.logger,
            f'Canbus set link up: {cfg["CANBUS_CONFIG"]["do_can_up"]}',
            level=spdlog.LogLevel.TRACE,
        )
        debug(
            self.logger,
            f'Canbus Device network interface: {cfg["CANBUS_CONFIG"]["channel"]}',
            level=spdlog.LogLevel.TRACE,
        )
        debug(
            self.logger,
            f'CAN Bus Speed: {cfg["CANBUS_CONFIG"]["speed"]}',
            level=spdlog.LogLevel.TRACE,
        )

        for f in cfg["CANBUS_CONFIG"]["filters"]:
            debug(
                self.logger,
                f"Filter 0x{hex(f['can_mask'])[2:].zfill(3)}, "
                f"0x{hex(f['can_id'])[2:].zfill(3)}, "
                f"{f['extended']}",
                level=spdlog.LogLevel.TRACE,
            )

        self.threads = {"event": None, "command": None, "heartbeat": None}
        self.arbitration_id = None
        self.query_count = 0
        self.query_response_time = {}

        debug(self.logger, f"__init__() complete", level=spdlog.LogLevel.INFO)

    def handleActivate(self):
        self.logger.info("Activate")
        if not self.cfg:
            debug(
                self.logger,
                f"Cannot activate. " f"self.cfg is {self.cfg}",
                level=spdlog.LogLevel.CRITICAL,
            )
            return

        cancontrol = CanbusControl(
            channel=self.cfg["CANBUS_CONFIG"]["channel"],
            spd=self.cfg["CANBUS_CONFIG"]["speed"],
            logger=self.logger,
            filters=self.cfg["CANBUS_CONFIG"]["filters"],
        )

        cbus = cancontrol.CreateCANBus(do_can_up=self.cfg["CANBUS_CONFIG"]["do_can_up"])

        if cbus is None:
            debug(
                self.logger,
                f"Error in CAN bus configuration",
                level=spdlog.LogLevel.CRITICAL,
            )
            return

        # cbus is not None
        # start the canbus threads
        # These threads are started here because they need the canport which is a riaps `inside` port
        self.threads["event"] = CanbusEventNode(self.logger, self.canport, cbus)
        self.threads["command"] = CanbusCommandNode(self.logger, self.canport, cbus)
        # see if a heartbeat is configured
        if "Heartbeat" in self.cfg:
            hb_msg = can.Message(
                timestamp=dt.datetime.timestamp(dt.datetime.now()),
                dlc=self.cfg["Heartbeat"]["dlen"],
                arbitration_id=self.cfg["Heartbeat"]["id"],
                data=self.cfg["Heartbeat"]["data"],
                is_remote_frame=self.cfg["Heartbeat"]["remote"],
                is_extended_id=self.cfg["Heartbeat"]["extended"],
            )

            self.threads["heartbeat"] = CanbusHeartBeat(
                self.logger, hb_msg, cbus, self.cfg["Heartbeat"]["freq"]
            )
        else:
            debug(
                self.logger,
                f"No heartbeat message configured, heartbeat thread was not created.",
                level=spdlog.LogLevel.WARN,
            )

        for t in self.threads:
            self.threads[t].start()

        # delay to let the threads start and configure the comm plugs
        done = False
        while not done:
            self.cmdplug = self.threads[
                "command"
            ].get_plug()  # get riaps 'plug' to canport inside port
            self.evtplug = self.threads[
                "event"
            ].get_plug()  # get riaps 'plug' to canport inside port
            # TODO: These use the same port... why do we create two of them?
            if self.cmdplug is None or self.evtplug is None:
                time.sleep(0.100)
                # TODO: This is a busy wait...
            else:
                done = True
                # signal components that threads and connections are in active
        value = ("config", self.cfg["Description"])
        self.logger.info(f"handleActivate: {value}")
        self.event_can_pub.send_pyobj(value)  # riaps pub port
        # publish config to other components because the message parameters are used to construct messages.
        debug(self.logger, f"handleActivate() complete", level=spdlog.LogLevel.INFO)

    # riaps:keep_constr:end

    # riaps:keep_canport:begin
    def on_canport(self):
        msg = self.canport.recv_pyobj()  # riaps inside port
        value = self.format(msg.arbitration_id, msg.data)
        self.logger.info(f"dvc on_canport: {msg.data} {value}")
        dl = list(msg.data)
        if self.arbitration_id == msg.arbitration_id:
            self.timeout.cancel()  # riaps sporadic timer
            self.arbitration_id = None
            now = dt.datetime.now()
            self.query_response_time["end"] = now
            duration = (now - self.query_response_time["start"]).total_seconds()
            self.query_response_time["duration"] = duration
            self.canbusqryans.send_pyobj(value)  # riaps ans port
            debug(
                self.logger,
                f"Canbus->Driver:Answer to query {msg.arbitration_id}: {dl} "
                f"time:{self.query_response_time} "
                f"current timeout: {self.canbus_timeout}",
                level=spdlog.LogLevel.TRACE,
            )
            # TODO: I thought arbitration_id (formerly query_id) was incremented on each message. Nope.
            #  canbus uses to prioritize which message is sent... and calls it
            #  an arbitration_id. The id must be unique on the can bus.
        else:
            self.event_can_pub.send_pyobj(value)  # riaps pub port
            debug(
                self.logger,
                f"Canbus->Driver:Event:{(msg.arbitration_id, dl)}",
                level=spdlog.LogLevel.TRACE,
            )
        # riaps:keep_canport:end

    # riaps:keep_canbusqryans:begin
    def on_canbusqryans(self):
        qryriaps = self.canbusqryans.recv_pyobj()  # riaps ans port

        self.query_response_time["start"] = dt.datetime.now()
        self.sendmsg = qryriaps

        self.arbitration_id = self.send_canbus_msg(qryriaps)

        self.timeout.setDelay(self.canbus_timeout)  # riaps sporadic timer
        self.timeout.launch()  # riaps sporadic timer

    # riaps:keep_canbusqryans:end

    # riaps:keep_command_can_sub:begin
    def on_command_can_sub(self):
        cmdriaps = self.command_can_sub.recv_pyobj()  # riaps sub port
        self.send_canbus_msg(cmdriaps)

    # riaps:keep_command_can_sub:end

    # riaps:keep_timeout:begin
    def on_timeout(self):
        now = self.timeout.recv_pyobj()  # riaps sporadic timer
        value = ("timeout", self.sendmsg)
        self.event_can_pub.send_pyobj(value)  # riaps pub port
        debug(
            self.logger,
            f"Driver communication timeout triggered.",
            level=spdlog.LogLevel.CRITICAL,
        )
        debug(self.logger, f"Try increasing timeout", level=spdlog.LogLevel.CRITICAL)

    # riaps:keep_timeout:end

    # riaps:keep_impl:begin

    def send_canbus_msg(self, msg):
        cmd, vals = msg
        arbitration_id, mode, dta, rtr, ext = build_command(
            cfg=self.cfg, cmd=cmd, msg_vals=vals
        )
        cmdmsg = can.Message(
            timestamp=dt.datetime.timestamp(dt.datetime.now()),
            dlc=len(dta),
            arbitration_id=arbitration_id,
            data=dta,
            is_remote_frame=rtr,
            is_extended_id=ext,
        )
        self.canport.set_identity(self.canport.get_plug_identity(self.cmdplug))
        # TODO: What is the purpose of this "set_identity"?
        #  If it is removed I get a "Driver communication timeout triggered"
        self.canport.send_pyobj(cmdmsg)  # riaps inside port
        debug(
            self.logger,
            f"Driver->CANBus:{mode} {arbitration_id, dta}",
            level=spdlog.LogLevel.TRACE,
        )
        return arbitration_id

    def __destroy__(self):

        for f in ["Deactivate", "join", "is_alive"]:
            for name in self.threads:
                t = self.threads[name]
                if t is None:
                    continue
                getattr(t, f)
                debug(
                    self.logger,
                    f"{f} {name} thread...",
                    level=spdlog.LogLevel.TRACE,
                    color=TermColor.Yellow,
                )
        debug(self.logger, f"__destroy__() complete", level=spdlog.LogLevel.INFO)

    def get_bus_setup(self):
        return self.cfg["CANBUS_CONFIG"]

    def get_parameters(self):
        return self.cfg["Parameters"]

    def get_config(self):
        return self.cfg

    def format(self, msgid, data):
        """
        Convert data to CAN message format
        :param msgid:
        :param data:
        :return: returns a tuple with mode and a list of dictionaries in the form [{ name, value, units }, ...]
        """
        mode = None
        result = []
        params = self.cfg["Parameters"]
        for p in params:
            tmp = params[p]["id"]
            self.logger.info(f"format cfgid: {tmp} type: {type(tmp)}")
            self.logger.info(f"format msgid: {msgid} type: {type(msgid)}")
            can_msg_id = int(params[p]["id"], 16)
            self.logger.info(f"format canid: {can_msg_id} type: {type(can_msg_id)}")
            if can_msg_id != msgid:
                continue
            # if can_msg_id == msgid:
            values = params[p]["values"]
            mode = params[p]["mode"]
            self.logger.info(f"format values: {values} type: {type(values)}")
            self.logger.info(f"format mode: {mode} type: {type(mode)}")
            for v in values:
                val = []
                # for i in range(int(v["index"]), int(v["index"]) + int(v["size"])):
                #     pass
                start_index = values[v]["index"]
                end_index = start_index + values[v]["size"]
                for i in range(start_index, end_index):
                    val.append(data[i])
                # convert to float ( tuple )
                self.logger.info(f"what is val: {val}")
                cvtval = struct.unpack(values[v]["format"], bytearray(val))
                self.logger.info(f"what is cvtval: {cvtval}")
                # apply scaling
                cvtval = float(cvtval[0])
                cvtval /= int(values[v]["scaler"])
                result.append({"name": v, "value": cvtval, "units": values[v]["units"]})
        return mode, result


# riaps:keep_impl:end
