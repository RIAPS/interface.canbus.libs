import spdlog

import canbus.libs.Terminal as tc


def debug(logger, message, level=spdlog.LogLevel.CRITICAL, color=None):
    if level == spdlog.LogLevel.CRITICAL:
        logger.critical(f"{tc.Red}{message}{tc.RESET}")
    elif level == spdlog.LogLevel.ERR:
        logger.err(f"{tc.Yellow}{message}{tc.RESET}")
    elif level == spdlog.LogLevel.WARN:
        if color is None:
            color = tc.Orange
        logger.warn(f"{tc.Purple}{message}{tc.RESET}")
    elif level == spdlog.LogLevel.INFO:
        if color is None:
            color = tc.Green
        logger.info(f"{color}{message}{tc.RESET}")
    elif level == spdlog.LogLevel.DEBUG:
        if color is None:
            color = tc.Cyan
        logger.debug(f"{color}{message}{tc.RESET}")
    elif level == spdlog.LogLevel.TRACE:
        if color is None:
            color = tc.LightGray
        logger.trace(f"{color}{message}{tc.RESET}")
    else:
        logger.trace(message)
