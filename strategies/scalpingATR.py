import sys
import time
import json
import os
import pandas as pd
import numpy as np
import uuid
from datetime import datetime
from wazirxHelper import WazirXHelper
from pymongo import MongoClient

class ScalpingATR(WazirXHelper):

    def __init__(self, creds, requestInstance, loggerInstance):
        super().__init__(creds, requestInstance, loggerInstance)
        self.atrPeriod = 5
        self.entryThreshold = 0.01
        self.exitThreshold = 0.005
        self.timeOfBuy = None
        self.timeOfSell = None
        self.humanReadableTimeofBuy = None
        self.humanReadableTimeOfSell = None
        self.position = None
        self.entryPrice = None
        self.exitPrice = None
        self.totalBuyPrice = None
        self.totalSellPrice = None
        self.buyOrderDetails = None
        self.sellOrderDetails = None
        self.uuidOfTrade = None
        self.dbClient = None
        self.databaseHandle = None
        self.collectionHandle = None
        self.dbConnect()
        self.initializeTradeInDB()

    def dbConnect(self):
        try:
            self.dbClient = MongoClient(self.creds['databaseURI'])
            self.databaseHandle = self.dbClient.get_database(self.creds['databaseName'])
            self.collectionHandle = self.databaseHandle[f"trades-{datetime.now().strftime('%Y-%m-%d')}"]
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def initializeTradeInDB(self):
        try:
            self.uuidOfTrade = str(uuid.uuid4())
            if self.collectionHandle is not None:
                self.collectionHandle.insert_one({ 'tradeId': self.uuidOfTrade })
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def getDataWithXMinTimeFrame(self, symbol=None, mins=30):
        try:
            if not symbol:
                raise Exception('symbol is required.')
            kLineDataBefore30MinsJSONData = json.loads(self.kLineDataBeforeXMin(symbol, None, mins).content)
            kLineDataFrameBefore30Mins = pd.DataFrame(kLineDataBefore30MinsJSONData)
            kLineDataFrameBefore30Mins.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            '''
              We can make Time as an index column using the line below.
              kLineDataFrameBefore30Mins.set_index('Time', inplace=True, drop=True)
              Converting values to floating
            '''
            kLineDataFrameBefore30Mins = kLineDataFrameBefore30Mins.astype(float)
            kLineDataFrameBefore30Mins['HumanReadableTime'] = pd.to_datetime(kLineDataFrameBefore30Mins['Time'], unit='s')
            return kLineDataFrameBefore30Mins
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def calculateATR(self, kLineDataFrame = None):
        if kLineDataFrame is None or kLineDataFrame.empty:
            return None
        finalTrueRange = np.zeros(len(kLineDataFrame))
        trueRangeOne = np.zeros(len(kLineDataFrame))
        trueRangeTwo = np.zeros(len(kLineDataFrame))
        trueRangeThree = np.zeros(len(kLineDataFrame))
        for i in range(1, len(kLineDataFrame)):
            currentHigh = kLineDataFrame.iloc[i]['High']
            currentLow = kLineDataFrame.iloc[i]['Low']
            previousClose = kLineDataFrame.iloc[i - 1]['Close']
            trueRangeOne[i] = currentHigh - currentLow
            trueRangeTwo[i] = abs(currentHigh - previousClose)
            trueRangeThree[i] = abs(currentLow - previousClose)
            finalTrueRange[i] = max(trueRangeOne[i], trueRangeTwo[i], trueRangeThree[i])
        kLineDataFrame['TR-1'] = trueRangeOne
        kLineDataFrame['TR-2'] = trueRangeTwo
        kLineDataFrame['TR-3'] = trueRangeThree
        kLineDataFrame['TR'] = finalTrueRange
        kLineDataFrame['ATR'] = kLineDataFrame['TR'].rolling(window=self.atrPeriod).mean()
        return kLineDataFrame

    def executeStrategy(self, symbol=None, quantityToTrade=1):
        try:
            if not symbol:
                raise Exception('Asset symbol to trade is required.')
            if not quantityToTrade or quantityToTrade < 0:
                raise Exception('Asset Quantity to trade is required.')

            self.collectionHandle.find_one_and_update({ 'tradeId': self.uuidOfTrade}, { '$set': {'assetSymbol': symbol } })

            # Buying Loop
            while True:
                time.sleep(5)
                kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.atrPeriod + 1)
                kLineDataFrame = self.calculateATR(kLineDataFrame)

                if self.position is None and (kLineDataFrame.iloc[-1]['ATR'] < (self.entryThreshold * kLineDataFrame.iloc[-1]['Close'])) and (kLineDataFrame.iloc[-1]['Close'] > kLineDataFrame.iloc[-2]['Close']):
                    self.position = 'long'
                    self.entryPrice = kLineDataFrame.iloc[-1]['Close']
                    self.totalBuyPrice = self.entryPrice * quantityToTrade
                    self.exitPrice = self.entryPrice + (self.exitThreshold * kLineDataFrame.iloc[-1]['ATR'])
                    self.timeOfBuy = kLineDataFrame.iloc[-1]['Time']
                    self.humanReadableTimeofBuy = kLineDataFrame.iloc[-1]['HumanReadableTime']
                    self.collectionHandle.find_one_and_update({ 'tradeId': self.uuidOfTrade }, { '$set': {'entryPrice': self.entryPrice, 'assetSymbol': symbol, 'quantity': quantityToTrade, 'timeOfBuy': self.timeOfBuy, 'humanReadableTimeOfBuy': self.humanReadableTimeofBuy, 'totalBuyPrice': self.totalBuyPrice } })
                    #self.buyOrderDetails = self.sendOrder(symbol, self.entryPrice, quantityToTrade, 'buy')
                    #print(self.buyOrderDetails.json())
                    print(f"Bought Quantity = {quantityToTrade} of Asset = {symbol} at {self.entryPrice} price. Total Buy at {self.timeOfBuy} timestamp is {self.humanReadableTimeofBuy}")
                    break

                os.system('cls' if os.name == 'nt' else 'clear')
                print('\nTrying to Buy\n=============')
                print(kLineDataFrame)

            # Selling Condition
            if self.position == 'long':
                while True:
                    time.sleep(5)
                    kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.atrPeriod + 1)
                    kLineDataFrame = kLineDataFrame[kLineDataFrame.Time > self.timeOfBuy]
                    if kLineDataFrame is None or kLineDataFrame.empty:
                        continue
                    kLineDataFrame = self.calculateATR(kLineDataFrame)

                    if kLineDataFrame.iloc[-1]['Close'] >= self.exitPrice:
                        self.position = None
                        self.exitPrice = kLineDataFrame.iloc[-1]['Close']
                        self.timeOfSell = kLineDataFrame.iloc[-1]['Time']
                        self.humanReadableTimeOfSell = kLineDataFrame.iloc[-1]['HumanReadableTime']
                        self.totalSellPrice = self.exitPrice * quantityToTrade
                        self.collectionHandle.find_one_and_update({ 'tradeId': self.uuidOfTrade }, { '$set': { 'exitPrice': self.exitPrice, 'assetSymbol': symbol, 'quantity': quantityToTrade, 'timeOfSell': self.timeOfSell, 'humanReadableTimeOfSell': self.humanReadableTimeOfSell, 'totalSellPrice': self.totalSellPrice, 'netProfitOrLoss': (self.totalSellPrice - self.totalBuyPrice) } })
                        #self.sellOrderDetails = self.sendOrder(symbol, self.exitPrice, quantityToTrade, 'sell')
                        #print(self.sellOrderDetails.json())
                        print(f"Sold Quantity = {quantityToTrade} of Asset = {symbol} at {self.exitPrice} price. Total Sold at {self.timeOfSell} timestamp is {self.humanReadableTimeOfSell}")
                        break

                    os.system('cls' if os.name == 'nt' else 'clear')
                    print('\nTrying to Sell\n=============')
                    #print(self.buyOrderDetails.json())
                    print(f"Bought Quantity = {quantityToTrade} of Asset = {symbol} at {self.entryPrice} price. Total Buy at {self.timeOfBuy} timestamp is {self.totalBuyPrice}")
                    print(kLineDataFrame)

        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()
