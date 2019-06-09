import requests
import base64, hashlib, hmac, time
from requests.auth import AuthBase
from datetime import datetime

class GDAXRequestAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
    
    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + str(request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode('utf-8'), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode("utf-8")
        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

import json
    
API_KEY = '6777f39458390bbf84ed25060bddc72d'
API_SECRET = 'VKSPYLpnEiuRRi4pOzrpgfozzfQxaZh+wGpZlEqbSA9Uyys/KWY9BHwfb7vIltHiPklju0hgCUkv9jD7/4gGHQ=='
API_PASS = 'ximndivkdra'

api_url = 'https://api-public.sandbox.gdax.com'
auth = GDAXRequestAuth(API_KEY, API_SECRET, API_PASS)
order = {
    'size': 1.0,
    'price': 1000.0,
    'side': 'buy',
    'product_id': 'BTC-USD',
}

#r = requests.get(api_url + '/accounts', auth=auth)
print(datetime.now())
r = requests.post(api_url + '/orders', data=json.dumps(order), auth=auth)
print(datetime.now())
print (r.json())