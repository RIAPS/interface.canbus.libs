import platform

# code to color terminal text color

if platform.system().upper() == 'WINDOWS' :
    Red = "\033[38;2;255;0;0m"
    Green = "\033[38;2;0;255;0m"
    Yellow = "\033[38;2;255,215,0m"
    LightPurple = "\033[38;2;204,0,204m"
    Purple = "\033[38;2;153,0,153m"
    Cyan = "\033[38;2;0,255,255m"
    LightGray = "\033[38;2;192,192,192m"
    Black = "\033[38;2;0,0,0m"
    RESET = "\033[0m"
elif platform.system().upper() == 'LINUX' :
    Red = "\033[91m"
    Green = "\033[92m"
    Yellow = "\033[93m"
    LightPurple = "\033[94m"
    Purple = "\033[95m"
    Cyan = "\033[96m"
    LightGray = "\033[97m"
    Black = "\033[98m"
    RESET = "\033[00m"
else:
    Red = ""
    Green = ""
    Yellow = ""
    LightPurple = ""
    Purple = ""
    Cyan = ""
    LightGray = ""
    Black = ""
    RESET = ""


