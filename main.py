import argparse
from logger import Logger
from loadenv import loadEnvironmentVariables
from request import Requests
from strategies.scalpingATR import ScalpingATR
from strategyCodes import SCALPING_ATR, SMA_CROSSOVER


def main():
    strategyCode = None
    strategyInstance = None
    argumentParser = argparse.ArgumentParser(description='Algo Trading Bot.')
    argumentParser.add_argument(
        'quantity', type=float, help='Quantity of asset to trade.')
    argumentParser.add_argument('strategy', type=str, choices=[
                                SCALPING_ATR, SMA_CROSSOVER], help=f'Strategy code to use ({ SCALPING_ATR }, { SMA_CROSSOVER })')
    arguments = argumentParser.parse_args()
    loggerInstance = Logger()
    jsonEnvContent = loadEnvironmentVariables(loggerInstance, 'wazirx.json')
    requestInstance = Requests(jsonEnvContent['baseURI'], {
        'X-API-KEY': jsonEnvContent['ApiKey']
    })
    strategyCode = arguments.strategy
    if strategyCode == SCALPING_ATR:
        strategyInstance = ScalpingATR(
            jsonEnvContent, requestInstance, loggerInstance)
    strategyInstance.executeStrategy()


if __name__ == '__main__':
    main()
