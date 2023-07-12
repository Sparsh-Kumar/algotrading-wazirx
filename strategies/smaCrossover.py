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


class SMACrossover(WazirXHelper):
    def __init__ (self, creds, requestInstance, loggerInstance):
        super().__init__(creds, requestInstance, loggerInstance)
        self.shortSMALookup = 20
        self.longSMALookup = 50
        self.position = None
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
        self.buyOrderDetails = None
        self.sellOrderDetails = None
        self.mongoDbBuyOrderDetailsDoc = None
        self.mongoDbSellOrderDetailsDoc = None
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
                kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.longSMALookup + 5)
                kLineDataFrame = kLineDataFrame.dropna()
                kLineDataFrame['SMA-Short'] = kLineDataFrame['Close'].rolling(self.shortSMALookup).mean()
                kLineDataFrame['SMA-Long'] = kLineDataFrame['Close'].rolling(self.longSMALookup).mean()

                if self.position is None and (kLineDataFrame.iloc[-1]['SMA-Short'] > kLineDataFrame.iloc[-1]['SMA-Long']) and (kLineDataFrame.iloc[-2]['SMA-Short'] < kLineDataFrame.iloc[-2]['SMA-Long']):
                    self.position = 'long'
                    self.buyAssetPrice = kLineDataFrame.iloc[-1]['Close']
                    self.totalAssetBuyPrice = self.buyAssetPrice * quantityToTrade
                    self.timeOfBuy = kLineDataFrame.iloc[-1]['Time']
                    self.humanReadableTimeofBuy = kLineDataFrame.iloc[-1]['HumanReadableTime']

                    ## Make Actual Order
                    self.buyOrderDetails = self.sendOrder(symbol, self.buyAssetPrice, quantityToTrade, 'buy')
                    self.buyOrderDetails = self.buyOrderDetails.json()

                    ## Do Database Operations.
                    self.mongoDbBuyOrderDetailsDoc = self.collectionHandle.find_one_and_update(
                        {
                            'tradeId': self.uuidOfTrade
                        },
                        {
                            '$set': {
                                'buyAssetPrice': self.buyAssetPrice,
                                'quantity': quantityToTrade,
                                'totalAssetBuyPrice': self.totalAssetBuyPrice,
                                'timeOfBuy': self.humanReadableTimeOfBuy,
                                'buyOrderDetails': self.buyOrderDetails,
                            }
                        },
                        return_document=ReturnDocument.AFTER
                    )
                    print(f"Bought the asset {self.mongoDbBuyOrderDetailsDoc}")
                    break

                # Displaying the information
                os.system('cls' if os.name == 'nt' else 'clear')
                print('\nTrying to Buy\n=============')
                print(kLineDataFrame)

            # Selling Loop
            while True:
                time.sleep(3)
                kLineDataFrame = self.getDataWithXMinTimeFrame(symbol, self.longSMALookup + 5)
                kLineDataFrame = kLineDataFrame.dropna()
                kLineDataFrame['SMA-Short'] = kLineDataFrame['Close'].rolling(self.shortSMALookup).mean()
                kLineDataFrame['SMA-Long'] = kLineDataFrame['Close'].rolling(self.longSMALookup).mean()

                if self.position == 'long' and (kLineDataFrame.iloc[-1]['SMA-Long'] > kLineDataFrame.iloc[-1]['SMA-Short']) and (kLineDataFrame.iloc[-2]['SMA-Long'] < kLineDataFrame.iloc[-2]['SMA-Short']):

                    ## Checking the limit order status
                    currentBuyOrderDetails = self.getOrderDetails(self.mongoDbBuyOrderDetailsDoc['wazirXBuyOrderId'])
                    currentBuyOrderDetails = currentBuyOrderDetails.json()

                    # Check If the buy Order is not yet fulfilled.
                    # Then cancel that order
                    # Remove document from database 
                    # Break out of loop.

                    if currentBuyOrderDetails['status'] != 'done':
                        print(f"Cancelling the buying Order & soft deleting it from Database.")
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

                    ## Perform computations
                    self.position = None
                    self.sellAssetPrice = kLineDataFrame.iloc[-1]['Close']
                    self.totalAssetSellPrice = self.sellAssetPrice * quantityToTrade
                    self.timeOfSell = kLineDataFrame.iloc[-1]['Time']
                    self.humanReadableTimeOfSell = kLineDataFrame.iloc[-1]['HumanReadableTime']

                    ## Make Actual Order
                    self.sellOrderDetails = self.sendOrder(symbol, self.sellAssetPrice, quantityToTrade, 'sell')
                    self.sellOrderDetails = self.sellOrderDetails.json()

                    ## Do Database Operations.
                    self.mongoDbSellOrderDetailsDoc = self.collectionHandle.find_one_and_update(
                        {
                            'tradeId': self.uuidOfTrade
                        },
                        {
                            '$set': {
                                'sellAssetPrice': self.sellAssetPrice,
                                'quantity': quantityToTrade,
                                'totalAssetSellPrice': self.totalAssetSellPrice,
                                'timeOfSell': self.humanReadableTimeOfSell,
                                'sellOrderDetails': self.sellOrderDetails,
                            }
                        },
                        return_document=ReturnDocument.AFTER
                    )
                    print(f"Sold the asset {self.mongoDbSellOrderDetailsDoc}")
                    break

                os.system('cls' if os.name == 'nt' else 'clear')
                print('\nTrying to Sell\n=============')
                print(self.mongoDbBuyOrderDetailsDoc)
                print(kLineDataFrame)

        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def __del__(self):
        pass
