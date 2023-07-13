import logging


class Logger:
    def __init__(self, logFileName='app.log', fileMode='w', loggingFormat='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'):
        logging.basicConfig(
            level=logging.DEBUG,
            format=loggingFormat,
            handlers=[
                logging.FileHandler(logFileName, mode=fileMode),
                logging.StreamHandler()
            ]
        )

    def logDebug(self, message):
        logging.debug(message)

    def logInfo(self, message):
        logging.info(message)

    def logWarning(self, message):
        logging.warning(message)

    def logError(self, message):
        logging.error(message)

    def logCritical(self, message):
        logging.critical(message)

    def __del__(self):
        pass
