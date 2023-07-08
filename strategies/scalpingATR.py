import sys
import time
import json
import pandas as pd
from datetime import datetime
from wazirxHelper import WazirXHelper


class ScalpingATR(WazirXHelper):
    def getDataWith30MinTimeFrame(self, symbol=None):
        try:
            if not symbol:
                raise Exception('symbol is required.')
            kLineDataBefore30MinsJSONData = json.loads(
                self.kLineDataBeforeXMin(symbol, None, 30).content)
            kLineDataFrameBefore30Mins = pd.DataFrame(
                kLineDataBefore30MinsJSONData)
            kLineDataFrameBefore30Mins.columns = [
                'Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            '''
              We can make Time as an index column using the line below.
              kLineDataFrameBefore30Mins.set_index('Time', inplace=True, drop=True)
              Converting values to floating
            '''
            kLineDataFrameBefore30Mins = kLineDataFrameBefore30Mins.astype(
                float)
            kLineDataFrameBefore30Mins['HumanReadableTime'] = pd.to_datetime(
                kLineDataFrameBefore30Mins['Time'], unit='s')
            return kLineDataFrameBefore30Mins
        except Exception as e:
            self.loggerInstance.logError(str(e))
            sys.exit()

    def executeStrategy(self, symbol=None, quantityToTrade=1):
        pass
