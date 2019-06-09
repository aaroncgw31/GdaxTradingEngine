# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 14:56:56 2018

@author: aaroncgw
"""

#import gdax_data_feed as gdaxDataFeed


#
# gdax/order_book.py
# David Caseria
#
# Live order book updated from the gdax Websocket Feed

import logging
from datetime import datetime
from threading import Thread
import time
#from decimal import Decimal
from gdax_data_feed.order_book import OrderBook
from gdax_data_feed.websocket_client import WebsocketClient
 
#from gdax_data_feed.authenticated_client import AuthenticatedClient



class OrderBooks(WebsocketClient):
    def __init__(self, wss_url, product_ids=['BTC-USD'], log_to=None):
        super().__init__(products=product_ids, url=wss_url)
        
        self.semaphore = None        
        self.logger = log_to
        self.message_count = 0
        self.product_ids = product_ids
        
        self.books = {}
        self.level_ones = {}
        self.level_one_update = {}
        for product in self.product_ids:
            book = OrderBook(product)
            self.books[product] = book
            self.level_ones[product] = (0, 0)
         

    def on_open(self):
        for product in self.products:
            self.books[product].on_open()
        print('Data feed connected. Warming up...')

    def on_close(self):
        print("data feed stops")
        if self.logger:
            self.logger.info("data feed stops")
    

    def on_message(self, message):
        try:
            self.message_count = self.message_count + 1
            if self.message_count < 10000:
                return
            product_id = message['product_id']
            book = self.books[product_id]
            book.on_message(message)
            newBestBid = book.get_bid()
            newBestAsk = book.get_ask()
            if self.level_ones[product_id] != (newBestBid, newBestAsk):
               self.level_ones[product_id] = (newBestBid, newBestAsk)
               self.level_one_update = {"time" : message['time'], "product_id" : product_id, "Bid" : newBestBid, "Ask" : newBestAsk}
               if self.semaphore:
                   self.semaphore.release()
               #print(self.level_one_update)    
            
            
            #print(message)
            #print("%s: TIme: %s Bid: %.2f Ask: %.2f" % (book.product_id, message['time'], book.get_bid(), book.get_ask()))
           
        except Exception as e:
            print(e)
            if self.logger:
                self.logger.info(e)
            self._disconnect()
            
        

'''
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logfilename = datetime.now().strftime('gdax_arb_%Y_%m_%d_%H_%M_%S.log')
handler = logging.FileHandler(logfilename)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)06d %(message)s',datefmt='%Y-%m-%d,%H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
sandbox_wss_url = "wss://ws-feed-public.sandbox.gdax.com"
'''
wss_url = "wss://ws-feed.gdax.com"
#sandbox_rest_api = "https://api-public.sandbox.gdax.com"
#sandbox_key = "6777f39458390bbf84ed25060bddc72d"
#sandbox_b64secret = "VKSPYLpnEiuRRi4pOzrpgfozzfQxaZh+wGpZlEqbSA9Uyys/KWY9BHwfb7vIltHiPklju0hgCUkv9jD7/4gGHQ=="
#sandbox_passphrase = "ximndivkdra"
#sandbox_client = AuthenticatedClient(sandbox_key, sandbox_b64secret, sandbox_passphrase, sandbox_rest_api)


if __name__ == '__main__':    
    products = ['BTC-USD', 'ETH-USD', 'ETH-BTC']
    gdaxOrderbook = OrderBooks(product_ids=products, wss_url=wss_url)
    gdaxOrderbook.start()
    '''    
    try:
        orderbook_thread = Thread(target=gdaxOrderbook.start)        
        orderbook_thread.start()
    #time.sleep(10)
    except KeyboardInterrupt:
        gdaxOrderbook.close()
        orderbook_thread.join()
    '''

