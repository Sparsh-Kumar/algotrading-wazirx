from datetime import datetime, timedelta
import sys
import time
import hashlib
import hmac

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

    # typeOfOrder can be buy / sell
    def sendOrder(self, symbol = None, price = None, quantity = None, side = None, typeOfOrder = 'limit'):
        try:
            timestamp = datetime.now().timestamp()
            timestamp = int(timestamp * 1000)
            apiSecretKey = self.creds['SecretKey']
            preHashString = f"{apiSecretKey}&price={price}&quantity={quantity}&recvWindow=60000&side={side}&symbol={symbol}&timestamp={timestamp}&type={typeOfOrder}"
            signature = hmac.new(apiSecretKey.encode(), preHashString.encode(), hashlib.sha256).hexdigest()

            # Sending the POST request
            orderResponse = self.requestInstance.postURI('/order', { 'price': price,'quantity': quantity,'recvWindow': 1000,'side': side,'symbol': symbol,'timestamp': timestamp,'type': typeOfOrder,'signature': signature })
            return orderResponse

        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def __del__(self):
        pass
