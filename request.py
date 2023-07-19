import requests


class Requests:
    def __init__(self, baseEndpoint=None, currentPriceInfoEndpoint = None, headers=None):
        self.baseEndpoint = baseEndpoint
        self.currentPriceInfoEndpoint = currentPriceInfoEndpoint
        self.headers = headers

    def getCurrentPriceInfoURI(self):
        return requests.get(self.currentPriceInfoEndpoint)

    def getURI(self, endpoint=None, queryParams={}):
        return requests.get(self.baseEndpoint + endpoint, headers=self.headers, params=queryParams)
    
    def postURI(self, endpoint=None, requestBody=None):
        return requests.post(self.baseEndpoint + endpoint, headers=self.headers, data=requestBody)

    def deleteURI(self, endpoint=None, requestBody=None):
        return requests.delete(self.baseEndpoint + endpoint, headers=self.headers, data=requestBody)

    def __del__(self):
        pass
