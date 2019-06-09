# -*- coding: utf-8 -*-
"""
Created on Fri Feb  2 09:41:58 2018

@author: aaroncgw
"""
#!/usr/bin/env python3

import threading
import time
import gdaxfixClient
import gdaxOrderbook
import setting


class GdaxTradingEngine(object):
    def __init__(self, market_data_feed, order_router):
        self.sem = threading.Semaphore(999)
        self.cancel = False
        self.order = None        
        
        self.market_data_feed = market_data_feed
        self.order_router = order_router        
        self.data_feed_thread = threading.Thread(target=self.market_data_feed.start, args=(self.sem,))
        self.order_router_thread = threading.Thread(target=self.order_router.start)
        self.newOrder_thread = None        
        
                
    def start(self):        
        self.data_feed_thread.start()
        self.order_router.connect()
        self.order_router_thread.start()
        
    def stop(self):               
        self.market_data_feed.close()
        self.order_router.stop()
        self.cancel_onStop_order()
        self.newOrder_thread.join()
        self.data_feed_thread.join()
        self.order_router_thread.join()
        self.order_router.disconnect()
        self.order_router.resetDB()
                
    def new_onStop_order(self, order):       
        self.newOrder_thread = threading.Thread(target=self.onStop_order)        
        self.order = order
        self.newOrder_thread.start()
            
    def onStop_order(self):
        print("new order is activated")
        self.cancel == False        
        while True:
            self.sem.acquire()
            if self.cancel == True:
                break
            new_level_one = self.market_data_feed.level_one_update 
            if len(new_level_one) != 0:            
                print(new_level_one)
                if new_level_one["product_id"] == self.order["product_id"]:
                    if self.order["side"] == "buy" and new_level_one["Bid"] > self.order["price"]:
                        print("order is executed")
                        break
                        self.order_router.sendOrder(symbol=self.order["product_id"], side="buy", ordType="limit", price = 1000, quantity=self.order["quantity"])                    
                    elif self.order["side"] == "sell" and new_level_one["Ask"] < self.order["price"]:
                        self.order_router.sendOrder(symbol=self.order["product_id"], side="sell", ordType="limit", price = 20000, quantity=self.order["quantity"])
                        print("order is executed")
                        break
    
            
    def cancel_onStop_order(self):
        self.cancel = True
        self.sem.release()
        self.newOrder_thread.join()
        print("order is cancelled")
        
    def modify_onStop_order(self, order):
        self.cancel_onStop_order()
        self.new_onStop_order(order)
        
        
        
        

if __name__ == "__main__":
    
    '''
    sandbox_auth = {
            "passphrase" : "",
            "api_key"    : "",
            "api_secret" : ""                        
       }
    '''
    sandbox_auth = setting.sandbox_auth
    wss_url = "wss://ws-feed.gdax.com"
    #products = ["BTC-USD", "ETH-USD", "ETH-BTC"]
    products = ["BTC-USD"]
    order_info = {"product_id" : "BTC-USD", "side" : "sell", "price" : 8539, "quantity" : 1}
    fixclient = gdaxfixClient.GdaxFixClient(sandbox_auth)
    data_feed = gdaxOrderbook.OrderBooks(product_ids=products, wss_url=wss_url)
    tradingEngine = GdaxTradingEngine(market_data_feed=data_feed, order_router=fixclient)    
    tradingEngine.start()
    #tradingEngine.new_onStop_order(order_info)
    #tradingEngine.cancel_onStop_order()
    #tradingEngine.stop()
    

    

