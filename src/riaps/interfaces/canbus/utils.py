import can
import datetime
import struct

data_type_properties = {
    "H": {"min": 0, "max": 65535},
    "h": {"min": -32768, "max": 32787},
    "I": {"min": 0, "max": 4294967295},
    "i": {"min": -2147483648, "max": 2147483647},
    "L": {"min": 0, "max": 4294967295},
    "l": {"min": -2147483648, "max": 2147483647},
    "Q": {"min": 0, "max": 18446744073709551615},
    "q": {"min": -9223372036854775808, "max": 9223372036854775807},
}


def build_command(cfg, cmd, msg_vals):
    sendcmd = (-1, [], False, False)

    if cmd not in cfg["Parameters"]:
        return f"Command {cmd} is not defined. Check Parameters in {cfg['Name']} device yaml file."

    mode = cfg["Parameters"][cmd]["mode"]
    if mode not in ["command", "query"]:
        return f"{cmd} can not be sent, it is a {mode} not a command or query. Check Parameters in device yaml file."

    id = int(cfg["Parameters"][cmd]["id"])
    len = int(cfg["Parameters"][cmd]["dlen"])
    rtr = bool(cfg["Parameters"][cmd]["remote"])
    ext = bool(cfg["Parameters"][cmd]["extended"])
    cfg_values = cfg["Parameters"][cmd]["values"]
    data = [0] * len  # This is what will be populated and sent out with the values.

    # check that the values sent match the values used in the message parameterization
    for value_name in msg_vals:
        if value_name not in cfg_values:
            continue
        cfg_value_properties = cfg_values[value_name]
        newval = msg_vals[value_name]
        # newval = float(d[k])
        index = cfg_values[value_name]["index"]
        # index = int(v["index"])
        size = cfg_values[value_name]["size"]
        # size = int(v["size"])
        scaler = cfg_values[value_name]["scaler"]
        # scaler = int(v["scaler"])
        units = cfg_values[value_name]["units"]
        # units = v["units"]
        value_format = cfg_values[value_name]["format"]
        # format = v["format"]

        newval = newval * scaler
        if "f" not in value_format:
            newval = int(newval)
            data_type = value_format.strip("<,>")  # remove endian spec to identify data type
            if newval > data_type_properties[data_type]["max"] or newval < data_type_properties[data_type]["min"]:
                sendcmd = (-2, [newval, value_format], rtr, ext)
                return f"Could not send command {cmd}, value {newval} is out of bounds for data_type {data_type}. " \
                       f"Check Parameters in device yaml file, and perhaps choose a different data type."

        frame = struct.pack(value_format, newval)
        integer_data = struct.unpack("B" * size, frame)
        i = 0
        for b in integer_data:
            data[index + i] = integer_data[i]
            i += 1

        sendcmd = (id, mode, data, rtr, ext)

    return sendcmd
