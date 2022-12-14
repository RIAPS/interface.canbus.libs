from interfaces.canbus import CanbusDevice


class Driver(CanbusDevice):
    def __init__(self, config):
        super().__init__(config)
