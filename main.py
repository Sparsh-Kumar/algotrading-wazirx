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
        '--quantity', type=float, dest='quantity', help='Quantity of asset to trade.')
    argumentParser.add_argument(
        '--symbol', type=str, dest='symbol', help='Asset Symbol.')
    argumentParser.add_argument('--strategy', type=str, choices=[
                                SCALPING_ATR, SMA_CROSSOVER], dest='strategy', help=f'Strategy code to use ({ SCALPING_ATR }, { SMA_CROSSOVER })')
    arguments = argumentParser.parse_args()
    loggerInstance = Logger()
    jsonEnvContent = loadEnvironmentVariables(loggerInstance, 'wazirx.json')
    requestInstance = Requests(jsonEnvContent['baseURI'], {
        'X-API-KEY': jsonEnvContent['ApiKey'],
        'Content-Type': 'application/x-www-form-urlencoded'
    })
    strategyCode = arguments.strategy
    assetSymbol = arguments.symbol
    quantityToTrade = arguments.quantity
    if strategyCode == SCALPING_ATR:
        while True:
            strategyInstance = ScalpingATR(jsonEnvContent, requestInstance, loggerInstance)
            strategyInstance.executeStrategy(assetSymbol, quantityToTrade)


if __name__ == '__main__':
    main()
