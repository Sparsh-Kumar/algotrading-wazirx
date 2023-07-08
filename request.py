import requests


class Requests:
    def __init__(self, baseEndpoint=None, headers=None):
        self.baseEndpoint = baseEndpoint
        self.headers = headers

    def getURI(self, endpoint=None):
        return requests.get(self.baseEndpoint + endpoint, headers=self.headers)
    
    def postURI(self, endpoint=None, requestBody=None):
        return requests.post(self.baseEndpoint + endpoint, headers=self.headers, data=requestBody)

    def __del__(self):
        pass
