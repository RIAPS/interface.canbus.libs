from riaps.interfaces.canbus.CanbusDevice import Driver as CanbusDeviceDriver


class Driver(CanbusDeviceDriver):
    def __init__(self, config):
        super().__init__(config)
