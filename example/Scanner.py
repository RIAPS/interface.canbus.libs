# riaps:keep_import:begin
from riaps.run.comp import Component
import spdlog
import capnp
from riaps.interfaces.canbus.libs import Terminal as tc
from riaps.interfaces.canbus.libs.Debug import debug
from riaps.interfaces.canbus.utils import build_command
import struct
import res.Defines as defs


# riaps:keep_import:end


# riaps:keep_constr:begin
class Scanner(Component):
    def __init__(self):
        super(Scanner, self).__init__()
        self.comms_up = False
        self.Parameters = None
        self.read_parms = False
        self.config = None
        self.Parameters = None
        self.debug_level = 10
        self.logger.set_level(spdlog.LogLevel.TRACE)
        debug(self.logger, f"__init__() complete", level=spdlog.LogLevel.INFO)

    # riaps:keep_constr:end

    # riaps:keep_canbusqryans:begin
    def on_canbusqryans(self):
        newmsg = self.canbusqryans.recv_pyobj()
        # set identity
        (mode, result) = newmsg
        for item in result:
            txt = f"Driver->Scanner:Answer:Received:{item}"
            debug(self.logger, txt, level=spdlog.LogLevel.INFO)

    # riaps:keep_canbusqryans:end

    # riaps:keep_event_can_sub:begin
    def on_event_can_sub(self):
        canmsg = self.event_can_sub.recv_pyobj()
        (msgtype, msg) = canmsg

        if not self.comms_up:
            # the lower level driver code must send a "config" message
            # the config message includes the configuration dictionary
            # with all configured parameters
            if msgtype == "config":
                for d in msg:
                    self.config = d
                    self.Parameters = self.config["Parameters"]
                    self.logger.set_level(self.config["Debuglevel"])

                    newmsg = (msgtype, [self.Parameters, ])
                    self.config_signal_pub.send_pyobj(newmsg)
                    self.comms_up = True
                    dvc = self.config["Description"]
                    debug(self.logger,
                          f"{dvc} is configured and communication active.",
                          level=spdlog.LogLevel.INFO,
                          color=tc.Purple)
            else:
                pass
        else:
            # after initialization CAN messages are received here
            # then publish an event or answer a response
            txt = f"Driver->Scanner:Posted:{msgtype}"
            debug(self.logger, txt, level=spdlog.LogLevel.INFO, color=tc.Yellow)
            for d in msg:
                debug(self.logger, f"Message entry->{d}", level=spdlog.LogLevel.INFO, color=tc.White)

    # riaps:keep_event_can_sub:end

    # riaps:keep_oneshot:begin
    def on_oneshot(self):
        now = self.oneshot.recv_pyobj()
        self.oneshot.halt()
        debug(self.logger, f"on_oneshot() complete", level=spdlog.LogLevel.INFO)

    # riaps:keep_oneshot:end

    # riaps:keep_periodic:begin
    def on_periodic(self):
        now = self.periodic.recv_pyobj()
        if self.comms_up:
            (cmd, vals) = ("PowerLimit=", {"p1": 12.34, "p2": 56.0})
            sendcmd = build_command(self.config, cmd, vals)
            self.canbusqryans.send_pyobj(sendcmd)
            debug(self.logger,
                  f"Periodic timer sending command: {cmd}",
                  level=spdlog.LogLevel.TRACE)

    # riaps:keep_periodic:end

    # riaps:keep_impl:begin
    def handleActivate(self):
        if self.periodic:
            cur_period = self.periodic.getPeriod() * 1000
            debug(self.logger,
                  f"Periodic timer interval is {cur_period} msec",
                  level=spdlog.LogLevel.INFO)

        debug(self.logger,
              f"handleActivate() complete",
              level=spdlog.LogLevel.INFO)

    def __destroy__(self):
        debug(self.logger, f"__destroy__() complete", level=spdlog.LogLevel.INFO)

    def build_error(self, msg, errtype="general"):
        return "error", [{"module": self.getName(), "type": errtype, "message": msg}, ]

    def build_log_msg(self, msg):
        return "Log: ", [{"module": self.getName(), "message": msg}, ]

# riaps:keep_impl:end
