import argparse
import gc
from logger import Logger
from loadenv import loadEnvironmentVariables
from request import Requests
from strategies.scalpingATR import ScalpingATR
from strategies.meanReversion import MeanReversion
from strategies.smaCrossover import SMACrossover
from strategyCodes import SCALPING_ATR, SMA_CROSSOVER, MEAN_REVERSION, SMA_CROSSOVER


def main():
    strategyCode = None
    strategyInstance = None
    argumentParser = argparse.ArgumentParser(description='Algo Trading Bot.')
    argumentParser.add_argument(
        '--quantity', type=float, dest='quantity', help='Quantity of asset to trade.')
    argumentParser.add_argument(
        '--symbol', type=str, dest='symbol', help='Asset Symbol.')
    argumentParser.add_argument(
        '--number', type=int, dest='number', help='Number Of Trades to Execute.')
    argumentParser.add_argument('--strategy', type=str, choices=[
                                SCALPING_ATR, SMA_CROSSOVER, MEAN_REVERSION, SMA_CROSSOVER], dest='strategy', help=f'Strategy code to use ({ SCALPING_ATR }, { SMA_CROSSOVER }, { MEAN_REVERSION }, { SMA_CROSSOVER })')
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
    numberOfTrades = int(arguments.number)
    if strategyCode == SCALPING_ATR:
        for i in range(numberOfTrades):
            strategyInstance = ScalpingATR(jsonEnvContent, requestInstance, loggerInstance)
            strategyInstance.executeStrategy(assetSymbol, quantityToTrade)
            # After completion, free the allocated memory
            del strategyInstance
            gc.collect()
    elif strategyCode == MEAN_REVERSION:
        for i in range(numberOfTrades):
            strategyInstance = MeanReversion(jsonEnvContent, requestInstance, loggerInstance)
            strategyInstance.executeStrategy(assetSymbol, quantityToTrade)
            # After completion, free the allocated memory
            del strategyInstance
            gc.collect()
    elif strategyCode == SMA_CROSSOVER:
        for i in range(numberOfTrades):
            strategyInstance = SMACrossover(jsonEnvContent, requestInstance, loggerInstance)
            strategyInstance.executeStrategy(assetSymbol, quantityToTrade)
            # After completion, free the allocated memory
            del strategyInstance
            gc.collect()


if __name__ == '__main__':
    main()
