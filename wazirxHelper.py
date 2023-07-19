from datetime import datetime, timedelta
import sys
import time
import hashlib
import hmac
from urllib import request
import urllib.parse

class WazirXHelper:
    def __init__(self, creds, requestInstance, loggerInstance):
        self.creds = creds
        self.requestInstance = requestInstance
        self.loggerInstance = loggerInstance
        self.totalAmount = 0

    def checkSystemHealth(self):
        try:
            return self.requestInstance.getURI('/systemStatus')
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit(1)

    def priceChangeStatistics24Hr(self, symbol=None):
        try:
            tickerPriceChangeEndpoint = '/tickers/24hr'
            if symbol:
                tickerPriceChangeEndpoint = '/ticker/24hr?symbol=' + symbol
            return self.requestInstance.getURI(tickerPriceChangeEndpoint)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def kLineData(self, symbol=None, limit=None, interval=None, startTime=None, endTime=None):
        try:
            if not symbol:
                raise Exception('symbol is required.')
            if not interval:
                raise Exception('interval is required.')
            kLineDataEndpoint = '/klines?symbol='+symbol+'&interval='+interval
            if startTime:
                kLineDataEndpoint += '&startTime='+str(int(startTime))
            if endTime:
                kLineDataEndpoint += '&endTime='+str(int(endTime))
            if limit:
                kLineDataEndpoint += '&limit='+str(limit)
            return self.requestInstance.getURI(kLineDataEndpoint)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def kLineDataBeforeXMin(self, symbol=None, limit=None, minutes=30):
        try:
            if not symbol:
                raise Exception('symbol is required.')
            interval = 1
            utcTimeNow = datetime.utcnow()
            utcTime30MinsBefore = utcTimeNow - \
                timedelta(minutes=minutes)
            epochTime = datetime(1970, 1, 1)
            totalSeconds30MinsBefore = (
                utcTime30MinsBefore - epochTime).total_seconds()
            return self.kLineData(symbol, limit, str(interval)+'m', totalSeconds30MinsBefore)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    # Calculate signature
    def calculateSignature(self, requestPayload = None):
        try:
            timestamp = datetime.now().timestamp()
            timestamp = int(timestamp * 1000)
            apiSecretKey = self.creds['SecretKey']
            requestPayload['timestamp'] = timestamp
            requestPayload['recvWindow'] = 60000
            signedPayload = urllib.parse.urlencode(requestPayload)
            requestPayload['signature'] = hmac.new(apiSecretKey.encode('latin-1'), msg = signedPayload.encode('latin-1'), digestmod=hashlib.sha256).hexdigest()
            return requestPayload
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    # side can be buy / sell
    def sendOrder(self, symbol = None, price = None, quantity = None, side = None, typeOfOrder = 'limit'):
        try:
            requestPayload = { 'price': price,'quantity': quantity,'side': side,'symbol': symbol,'type': typeOfOrder }
            requestPayload = self.calculateSignature(requestPayload)
            return self.requestInstance.postURI('/order', requestPayload)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()
    
    # Get Order Details
    def getOrderDetails(self, orderId = None):
        try:
            requestPayload = { 'orderId': orderId }
            requestPayload = self.calculateSignature(requestPayload)
            return self.requestInstance.getURI('/order', requestPayload)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    # Cancel Particular Order
    def cancelOrder(self, orderId = None, symbol = None):
        try:
            requestPayload = { 'orderId': orderId, 'symbol': symbol }
            requestPayload = self.calculateSignature(requestPayload)
            return self.requestInstance.deleteURI('/order', requestPayload)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    # Get Order Book Data
    def getOrderBookData(self, symbol = None, limit = None):
        try:
            requestPayload = { 'symbol': symbol, 'limit': limit }
            requestPayload = self.calculateSignature(requestPayload)
            return self.requestInstance.getURI('/depth', requestPayload)
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    # Get Current Data
    def getCurrentPriceInfo(self):
        try:
            return self.requestInstance.getCurrentPriceInfoURI()
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def __del__(self):
        pass
