import argparse
import gc
from logger import Logger
from loadenv import loadEnvironmentVariables
from request import Requests
from strategies.scalpingATR import ScalpingATR
from strategies.smaCrossoverkLines import SMACrossover
from livedatasync.livedatasync import LiveDataSync
from strategyCodes import SCALPING_ATR, SMA_CROSSOVER


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
    argumentParser.add_argument(
        '--mode', type=str, dest='mode', help='Mode to run the script in.')
    argumentParser.add_argument('--strategy', type=str, choices=[
                                SCALPING_ATR, SMA_CROSSOVER], dest='strategy', help=f'Strategy code to use ({ SCALPING_ATR }, { SMA_CROSSOVER })')
    arguments = argumentParser.parse_args()
    loggerInstance = Logger()
    jsonEnvContent = loadEnvironmentVariables(loggerInstance, 'wazirx.json')
    requestInstance = Requests(jsonEnvContent['baseURI'], jsonEnvContent['liveDataURI'], {
        'X-API-KEY': jsonEnvContent['ApiKey'],
        'Content-Type': 'application/x-www-form-urlencoded'
    })

    mode = arguments.mode
    if mode == 'LIVE_SYNC':
        liveSyncInstance = LiveDataSync(jsonEnvContent, requestInstance, loggerInstance)
        liveSyncInstance.liveDataSync()
        return

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
    elif strategyCode == SMA_CROSSOVER:
        for i in range(numberOfTrades):
            strategyInstance = SMACrossover(jsonEnvContent, requestInstance, loggerInstance)
            strategyInstance.executeStrategy(assetSymbol, quantityToTrade)
            # After completion, free the allocated memory
            del strategyInstance
            gc.collect()


if __name__ == '__main__':
    main()
