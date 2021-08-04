# define any bus setup constants for the Modbus communication here

class CanbusSystem:
    class Timeouts:
        Comm = 2000      # milliseconds
        RetriesTCP = -1        
        RetriesTTYS = -1     
    class Errors:
        Unknown = -1
        AppPollExit = -2
        CommError = -3
        PollTimerOverrun = -4
    class Debugging:
        Verbose = True      # modbus communication informational message level
        Diagnostics = False
        DebugLevel = 1
        
           
