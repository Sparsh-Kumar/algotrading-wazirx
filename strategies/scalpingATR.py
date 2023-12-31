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

class ScalpingATR(WazirXHelper):

    def __init__(self, creds, requestInstance, loggerInstance):
        super().__init__(creds, requestInstance, loggerInstance)
        self.atrPeriod = 14
        self.entryThreshold = 0.01
        self.exitThreshold = 0.03
        self.timeOfBuy = None
        self.timeOfSell = None
        self.humanReadableTimeofBuy = None
        self.humanReadableTimeOfSell = None
        self.position = None
        self.speculatedEntryPrice = None
        self.speculatedExitPrice = None
        self.originalEntryPrice = None
        self.originalExitPrice = None
        self.speculatedTotalBuyPrice = None
        self.speculatedTotalSellPrice = None
        self.originalTotalBuyPrice = None
        self.originalTotalSellPrice = None
        self.stopLossPrice = None
        self.stopLossPercentage = 0.02
        self.buyOrderDetails = None
        self.sellOrderDetails = None
        self.mongoDbBuyOrderDetailsDoc = None
        self.mongoDbSellOrderDetailsDoc = None
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
                time.sleep(3)
                kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.atrPeriod + 1)
                kLineDataFrame = self.calculateATR(kLineDataFrame)

                if self.position is None and (kLineDataFrame.iloc[-1]['ATR'] < (self.entryThreshold * kLineDataFrame.iloc[-1]['Close'])) and (kLineDataFrame.iloc[-1]['Close'] > kLineDataFrame.iloc[-2]['Close']):
                    self.position = 'long'

                    # Getting the best Ask from the order book
                    latestOrderBookData = self.getOrderBookData(symbol, 5)
                    latestOrderBookData = latestOrderBookData.json()
                    bestAsk = float(latestOrderBookData['asks'][0][0])

                    # Calculating Speculated and Original Information
                    self.speculatedEntryPrice = float(kLineDataFrame.iloc[-1]['Close'])
                    self.originalEntryPrice = float(bestAsk)
                    self.speculatedTotalBuyPrice = float(self.speculatedEntryPrice) * float(quantityToTrade)
                    self.originalTotalBuyPrice = float(self.originalEntryPrice) * float(quantityToTrade)
                    self.speculatedExitPrice = float(self.originalEntryPrice) + (float(self.exitThreshold) * float(kLineDataFrame.iloc[-1]['ATR']))
                    self.speculatedTotalSellPrice = float(self.speculatedExitPrice) * float(quantityToTrade)
                    self.stopLossPrice = float(self.originalEntryPrice) * (1 - float(self.stopLossPercentage))

                    self.timeOfBuy = kLineDataFrame.iloc[-1]['Time']
                    self.humanReadableTimeofBuy = kLineDataFrame.iloc[-1]['HumanReadableTime']

                    # Imitiating a Market Order
                    self.buyOrderDetails = self.sendOrder(symbol, bestAsk, quantityToTrade, 'buy')
                    self.buyOrderDetails = self.buyOrderDetails.json()

                    self.mongoDbBuyOrderDetailsDoc = self.collectionHandle.find_one_and_update(
                        {
                            'tradeId': self.uuidOfTrade
                        },
                        {
                            '$set': {
                                'speculatedEntryPrice': self.speculatedEntryPrice,
                                'originalEntryPrice': self.originalEntryPrice,
                                'speculatedExitPrice': self.speculatedExitPrice,
                                'assetSymbol': symbol,
                                'quantity': quantityToTrade,
                                'timeOfBuy': self.timeOfBuy,
                                'humanReadableTimeOfBuy': self.humanReadableTimeofBuy,
                                'speculatedTotalBuyPrice': self.speculatedTotalBuyPrice,
                                'speculatedTotalSellPrice': self.speculatedTotalSellPrice,
                                'originalTotalBuyPrice': self.originalTotalBuyPrice,
                                'stopLossPercentage': self.stopLossPercentage,
                                'stopLossPrice': self.stopLossPrice,
                                'wazirXBuyOrderId': self.buyOrderDetails['id'],
                                'wazirXBuyPrice': float(self.buyOrderDetails['price']),
                                'wazirXBuyOriginalQty': self.buyOrderDetails['origQty'],
                                'wazirXBuyExecutedQty': self.buyOrderDetails['executedQty']
                            }
                        },
                        return_document=ReturnDocument.AFTER
                    )
                    print(self.mongoDbBuyOrderDetailsDoc)
                    break

                os.system('cls' if os.name == 'nt' else 'clear')
                print('\nTrying to Buy\n=============')
                print(kLineDataFrame)

            # Selling Condition
            # If Already Bought
            # Don't need kLine Data , because we are comparing price right ?.
            # So, we don't need to check if there is a trend or not. We just need more price of our asset than entryPrice
            # So taking look at order book again and again and see if there is bid that satisfies our needs.

            if self.position == 'long':
                while True:
                    time.sleep(3)

                    # kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.atrPeriod + 1)
                    # kLineDataFrame = kLineDataFrame[kLineDataFrame.Time > self.timeOfBuy]
                    # if kLineDataFrame is None or kLineDataFrame.empty:
                    #     continue
                    # kLineDataFrame = self.calculateATR(kLineDataFrame)
                    
                    # Getting the best Ask from the order book
                    latestOrderBookData = self.getOrderBookData(symbol, 5)
                    latestOrderBookData = latestOrderBookData.json()
                    bestBid = float(latestOrderBookData['bids'][0][0])

                    if (bestBid >= self.originalEntryPrice) or (bestBid <= self.stopLossPrice):
                        currentBuyOrderDetails = self.getOrderDetails(self.mongoDbBuyOrderDetailsDoc['wazirXBuyOrderId'])
                        currentBuyOrderDetails = currentBuyOrderDetails.json()

                        # Check If the buy Order is not yet fulfilled.
                        # Then cancel that order
                        # Remove document from database 
                        # Break out of loop.
                        
                        if currentBuyOrderDetails['status'] != 'done':
                            print(f"Cancelling the buying Order & deleting it from Database.")
                            cancelledOrderDetails = self.cancelOrder(self.mongoDbBuyOrderDetailsDoc['wazirXBuyOrderId'], symbol)
                            cancelledOrderDetails = cancelledOrderDetails.json()
                            self.collectionHandle.find_one_and_update(
                                {
                                    '_id': self.mongoDbBuyOrderDetailsDoc['_id']
                                }, {
                                    '$set': {
                                        'orderCancelled': True,
                                        'cancelledReason': 'BUY_ORDER_NOT_FULLFILLED',
                                        'isDeleted': True
                                    }
                                },
                                return_document=ReturnDocument.AFTER
                            )
                            break
                        
                        self.position = None
                        self.originalExitPrice = float(bestBid)
                        self.timeOfSell = kLineDataFrame.iloc[-1]['Time']
                        self.humanReadableTimeOfSell = kLineDataFrame.iloc[-1]['HumanReadableTime']
                        self.originalTotalSellPrice = float(self.originalExitPrice) * float(quantityToTrade)

                        # Imitiating the Market Order
                        self.sellOrderDetails = self.sendOrder(symbol, self.originalExitPrice, quantityToTrade, 'sell')
                        self.sellOrderDetails = self.sellOrderDetails.json()
                        isStopLossHit = (bestBid <= self.stopLossPrice)

                        self.mongoDbSellOrderDetailsDoc = self.collectionHandle.find_one_and_update(
                            {
                                'tradeId': self.uuidOfTrade
                            },
                            {
                                '$set': {
                                    'originalExitPrice': self.originalExitPrice,
                                    'assetSymbol': symbol,
                                    'quantity': quantityToTrade,
                                    'timeOfSell': self.timeOfSell,
                                    'humanReadableTimeOfSell': self.humanReadableTimeOfSell,
                                    'originalTotalSellPrice': self.originalTotalSellPrice,
                                    'wazirXSellOrderId': self.sellOrderDetails['id'],
                                    'wazirXSellPrice': float(self.sellOrderDetails['price']),
                                    'wazirXSellOriginalQty': self.sellOrderDetails['origQty'],
                                    'wazirXSellExecutedQty': self.sellOrderDetails['executedQty'],
                                    'isStopLossHit': isStopLossHit
                                }
                            },
                            return_document=ReturnDocument.AFTER
                        )
                        print('Sold the Asset')
                        print(self.mongoDbSellOrderDetailsDoc)
                        break

                    os.system('cls' if os.name == 'nt' else 'clear')
                    print('\nTrying to Sell\n=============')
                    print(self.mongoDbBuyOrderDetailsDoc)
                    print(f"Best bid currently is {bestBid}")

        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()
