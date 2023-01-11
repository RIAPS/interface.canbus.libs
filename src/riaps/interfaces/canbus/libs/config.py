class Config:
    def __init__(self, cfg):
        self.device_id = list(self.cfg.keys())

        self.can_node_cfg = None
        self.can_node_name = None
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
