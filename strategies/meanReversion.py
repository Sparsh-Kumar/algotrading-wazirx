## IMPORTANT : This Strategy is in WIP

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
from pymongo import ReturnDocument


class MeanReversion(WazirXHelper):

    def __init__(self, creds, requestInstance, loggerInstance):
        super().__init__(creds, requestInstance, loggerInstance)
        self.lookBackPeriod = 20
        self.entryThreshold = 1.5
        self.exitThreshold = 0.5
        self.buyAssetPrice = None
        self.totalAssetBuyPrice = None
        self.sellAssetPrice = None
        self.totalAssetSellPrice = None
        self.timeOfBuy = None
        self.humanReadableTimeofBuy = None
        self.timeOfSell = None
        self.humanReadableTimeOfSell = None
        self.uuidOfTrade = None
        self.position = None
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
            kLineDataBeforeXMinsJSONData = json.loads(self.kLineDataBeforeXMin(symbol, None, mins).content)
            kLineDataFrameBeforeXMins = pd.DataFrame(kLineDataBeforeXMinsJSONData)
            kLineDataFrameBeforeXMins.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            '''
              We can make Time as an index column using the line below.
              kLineDataFrameBeforeXMins.set_index('Time', inplace=True, drop=True)
              Converting values to floating
            '''
            kLineDataFrameBeforeXMins = kLineDataFrameBeforeXMins.astype(float)
            kLineDataFrameBeforeXMins['HumanReadableTime'] = pd.to_datetime(kLineDataFrameBeforeXMins['Time'], unit='s')
            return kLineDataFrameBeforeXMins
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def calculateMean(self, kLineDataFrame = None):
        if kLineDataFrame is None or kLineDataFrame.empty:
            return None
        kLineDataFrame['Mean'] = kLineDataFrame['Close'].rolling(self.lookBackPeriod).mean()
        return kLineDataFrame

    def calculateStd(self, kLineDataFrame = None):
        if kLineDataFrame is None or kLineDataFrame.empty:
            return None
        kLineDataFrame['StdDev'] = kLineDataFrame['Close'].rolling(self.lookBackPeriod).std()
        return kLineDataFrame

    def executeStrategy(self, symbol = None, quantityToTrade = None):
        try:
            if not symbol:
                raise Exception('Asset symbol to trade is required.')
            if not quantityToTrade or quantityToTrade < 0:
                raise Exception('Asset Quantity to trade is required.')
            self.collectionHandle.find_one_and_update({ 'tradeId': self.uuidOfTrade}, { '$set': {'assetSymbol': symbol } })

            # Buying Loop
            while True:
                time.sleep(3)
                kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.lookBackPeriod + 1)
                kLineDataFrame = self.calculateMean(kLineDataFrame)
                kLineDataFrame = self.calculateStd(kLineDataFrame)
                
                # Getting the best Ask from the order book
                latestOrderBookData = self.getOrderBookData(symbol, 5)
                latestOrderBookData = latestOrderBookData.json()
                print('In Buy Condition')
                print(latestOrderBookData);
                bestAsk = float(latestOrderBookData['asks'][0][0])
                
                if self.position is None and (bestAsk < (kLineDataFrame.iloc[-1]['Mean'] - (self.entryThreshold * kLineDataFrame.iloc[-1]['StdDev']))):
                    self.position = 'long'
                    self.buyAssetPrice = float(bestAsk)
                    self.totalAssetBuyPrice = float(self.buyAssetPrice) * float(quantityToTrade)
                    self.timeOfBuy = kLineDataFrame.iloc[-1]['Time']
                    self.humanReadableTimeofBuy = kLineDataFrame.iloc[-1]['HumanReadableTime']

                    ## Make Actual Order
                    ## Do Database Operations.
                    print(f"Bought {quantityToTrade} {symbol}(s) at {self.buyAssetPrice} each with Total Buy Price equals to {self.totalAssetBuyPrice}")
                    break

                os.system('cls' if os.name == 'nt' else 'clear')
                print('\nTrying to Buy\n=============')
                print(f"Best Ask Till Now is {bestAsk}")
                print(kLineDataFrame)
            
            # Sell Loop
            while True:
                time.sleep(3)
                kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.lookBackPeriod + 1)
                # kLineDataFrame = kLineDataFrame[kLineDataFrame.Time > self.timeOfBuy]
                # if kLineDataFrame is None or kLineDataFrame.empty:
                #     continue

                kLineDataFrame = self.calculateMean(kLineDataFrame)
                kLineDataFrame = self.calculateStd(kLineDataFrame)
                
                # Getting the best Bid from the order book
                latestOrderBookData = self.getOrderBookData(symbol, 5)
                latestOrderBookData = latestOrderBookData.json()
                print('In Sell Condition')
                print(latestOrderBookData)
                bestBid = float(latestOrderBookData['bids'][0][0])

                if self.position == 'long' and (bestBid > (kLineDataFrame.iloc[-1]['Mean'] + (self.entryThreshold * kLineDataFrame.iloc[-1]['StdDev']))):
                    self.position = None
                    self.sellAssetPrice = float(bestBid)
                    self.totalAssetSellPrice = float(self.sellAssetPrice) * float(quantityToTrade)
                    self.timeOfSell = kLineDataFrame.iloc[-1]['Time']
                    self.humanReadableTimeOfSell = kLineDataFrame.iloc[-1]['HumanReadableTime']

                    ## Make Actual Order
                    ## Do Database Operations
                    print(f"Bought {quantityToTrade} {symbol}(s) at {self.buyAssetPrice} each with Total Buy Price equals to {self.totalAssetBuyPrice}")
                    print(f"Sold {quantityToTrade} {symbol}(s) at {self.sellAssetPrice} each with Total Buy Price equals to {self.totalAssetSellPrice}")
                    break

                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"Bought {quantityToTrade} {symbol}(s) at {self.buyAssetPrice} each with Total Buy Price equals to {self.totalAssetBuyPrice}")
                print('\nTrying to Sell\n=============')
                print(f"Best Bid Till Now is {bestBid}")
                print(kLineDataFrame)

        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def __del__(self):
        pass

