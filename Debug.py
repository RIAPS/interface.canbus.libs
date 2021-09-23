import libs.Terminal as tc
import spdlog


def debug( logger, message, level=spdlog.LogLevel.CRITICAL, color=None ) :
    if level == spdlog.LogLevel.CRITICAL :
        logger.critical( f"{tc.Red}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.ERR :
        logger.err( f"{tc.Yellow}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.WARN :
        if color == None:
            color = tc.Orange
        logger.info( f"{tc.Purple}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.INFO :
        if color == None:
            color = tc.Green
        logger.debug( f"{color}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.DEBUG :
        if color == None:
            color = tc.Cyan
        logger.trace( f"{color}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.TRACE :
        if color == None:
            color = tc.LightGray
        logger.trace( f"{color}{message}{tc.RESET}" ) 
    else:
        logger.trace( message ) 
