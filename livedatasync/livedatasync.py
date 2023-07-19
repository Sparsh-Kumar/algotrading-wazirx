from functools import total_ordering
import sys
import time
import json
import os
import pandas as pd
import numpy as np
import uuid
from datetime import datetime
from datetime import timedelta
from wazirxHelper import WazirXHelper
from pymongo import MongoClient
from pymongo import ReturnDocument
from pymongo import ASCENDING

class LiveDataSync(WazirXHelper):
    def __init__ (self, creds, requestInstance, loggerInstance):
        super().__init__(creds, requestInstance, loggerInstance)
        self.assets = ['xrpinr', 'dogeinr', 'shibinr', 'ethinr']
        self.sleepTime = 10 # In seconds
        self.databaseHandle = None
        self.collectionHandle = None
        self.syncDataFor = 5 # In Days
        self.dbConnect()

    def dbConnect(self):
        try:
            self.dbClient = MongoClient(self.creds['databaseURI'])
            self.databaseHandle = self.dbClient.get_database(self.creds['syncDatabaseName'])
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def liveDataSync(self):
        try:
            totalDocsToSync = (self.syncDataFor * 24 * 60 * 60) / (self.sleepTime)
            while True:
                livePriceData = self.getCurrentPriceInfo().json()
                for key in livePriceData:
                    if key not in self.assets:
                        continue
                    dt = datetime.utcfromtimestamp(livePriceData[key]['at'])
                    ist = dt + timedelta(hours=5, minutes=30)
                    priceInfo = {
                        'open': livePriceData[key]['open'],
                        'high': livePriceData[key]['high'],
                        'low': livePriceData[key]['low'],
                        'close': livePriceData[key]['last'],
                        'volume': livePriceData[key]['volume'],
                        'at': livePriceData[key]['at'],
                        'name': livePriceData[key]['name'],
                        'bestAsk': livePriceData[key]['sell'],
                        'bestBid': livePriceData[key]['buy'],
                        'ist': ist,
                    }
                    self.collectionHandle = self.databaseHandle[key]
                    sortedRecords = list(self.collectionHandle.find({}).sort('_id', ASCENDING))
                    sortedRecordsLen = len(sortedRecords)
                    if sortedRecordsLen > totalDocsToSync:
                        recordsToDelete = sortedRecords[: (sortedRecordsLen - totalDocsToSync)]
                        recordsToDeleteIds = [record['_id'] for record in recordsToDelete]
                        self.collectionHandle.delete_many({ '_id': { '$in': recordsToDeleteIds } })
                    insertedRecord = self.collectionHandle.insert_one(priceInfo)
                    print(insertedRecord.inserted_id)
                time.sleep(self.sleepTime)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def __del__ (self):
        pass

