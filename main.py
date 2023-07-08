from logger import Logger
from loadenv import loadEnvironmentVariables
from request import Requests


def main():
    loggerInstance = Logger()
    jsonEnvContent = loadEnvironmentVariables(loggerInstance, 'wazirx.json')
    requestInstance = Requests(jsonEnvContent['baseURI'], {
        'X-API-KEY': jsonEnvContent['ApiKey']
    })


if __name__ == '__main__':
    main()
