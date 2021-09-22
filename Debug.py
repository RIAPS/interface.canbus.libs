import libs.Terminal as tc
import spdlog


def debug( logger, message, level=spdlog.LogLevel.CRITICAL ) :
    if level == spdlog.LogLevel.CRITICAL :
        logger.critical( f"{tc.Red}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.ERR :
        logger.err( f"{tc.Yellow}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.WARN :
        logger.info( f"{tc.Purple}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.INFO :
        logger.debug( f"{tc.Green}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.DEBUG :
        logger.trace( f"{tc.Cyan}{message}{tc.RESET}" ) 
    elif level == spdlog.LogLevel.TRACE :
        logger.trace( f"{tc.LightGray}{message}{tc.RESET}" ) 
    else:
        logger.trace( message ) 
