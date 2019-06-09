#
# gdax/order_book.py
# David Caseria
#
# Live order book updated from the gdax Websocket Feed

import logging
from datetime import datetime
from decimal import Decimal
from gdax_data_feed.order_book import OrderBook
from gdax_data_feed.websocket_client import WebsocketClient
from gdax_data_feed.authenticated_client import AuthenticatedClient



class OrderBooks(WebsocketClient):
    def __init__(self, rest_client, product_ids=['BTC-USD'], wss_url="wss://ws-feed-public.sandbox.gdax.com", log_to=None):
        super().__init__(products=product_ids, url=wss_url)
        
        self.logger = log_to
        self.auth_client = rest_client
        
        self.books = {}
        for product in self.products:
            book = OrderBook(product)
            self.books[product] = book
        
        self.edge = Decimal(2.0)
        self.inside_slobe = Decimal(0.5)
        self.outside_slobe = Decimal(0.0)
        
        self.bid_price = Decimal(0.0)
        self.ask_price = Decimal(0.0)
        self.bid_size = Decimal(0.0)
        self.ask_size = Decimal(0.0)
        
        self.btcusd_bid_hedgeratio = Decimal(0.05)
        self.btcusd_ask_hedgeratio = Decimal(0.05)       
             
        self.bid_order_id = None
        self.ask_order_id = None
        self.my_orders = set()
        self.pnls = {}
        
        self.message_count = 0
        
        self.trading_start = 0

    @property
    def product_ids(self):    
        return self.products

    def on_open(self):
        for product in self.products:
            self.books[product].on_open()
        print('Connected. Warming up...')

    def on_close(self):
        self.auth_client.cancel_all("ETH-USD")
        print("Strategy stops")
        self.logger.info("Strategy stopes")
    
    def calc_fills_stat(self):
        #profit calculation
        eth_usd_fill = self.auth_client.get_fills(product_id='ETH-USD')[0][0]
        btc_usd_fill = self.auth_client.get_fills(product_id='BTC-USD')[0][0]
        eth_btc_fill = self.auth_client.get_fills(product_id='ETH-BTC')[0][0]
        
        if eth_usd_fill['side'] == 'sell':
            fees = Decimal(eth_usd_fill['fee']) + Decimal(btc_usd_fill['fee']) + Decimal(eth_btc_fill['price'])
            pnl = Decimal(eth_usd_fill['price']) * Decimal(eth_usd_fill['size']) - Decimal(btc_usd_fill['price']) * Decimal(btc_usd_fill['size']) - Decimal(eth_btc_fill['price']) * Decimal(eth_btc_fill['size'])
        if eth_usd_fill['side'] == 'buy':
            fees = Decimal(eth_usd_fill['fee']) + Decimal(btc_usd_fill['fee']) + Decimal(eth_btc_fill['price'])
            pnl = -(Decimal(eth_usd_fill['price']) * Decimal(eth_usd_fill['size']) - Decimal(btc_usd_fill['price']) * Decimal(btc_usd_fill['size']) - Decimal(eth_btc_fill['price']) * Decimal(eth_btc_fill['size']))
        
        time = str(datetime.now())
        self.pnls[time] = pnl
        logger.info("eth_usd filled at: " + eth_usd_fill['price'] + " sdie: " + eth_usd_fill['side'] + " time: " + eth_usd_fill['created_at'])
        logger.info("btc_usd filled at: " + btc_usd_fill['price'] + " sdie: " + btc_usd_fill['side'] + " time: " + btc_usd_fill['created_at'])
        logger.info("eth_btc filled at: " + eth_btc_fill['price'] + " sdie: " + eth_btc_fill['side'] + " time: " + eth_btc_fill['created_at'])
        logger.info(time + ' pnl: ' + str(pnl) + ' fees: ' + str(fees))
        print(time + ' pnl: ' + str(pnl) + ' fees: ' + str(fees))


    def on_message(self, message):
        try:
            self.message_count = self.message_count + 1
            
            product_id = message['product_id']
            book = self.books[product_id]
            book.on_message(message)
           
            #warm up
            if self.message_count < 5000:
                return
                #update limit price for ETH-USD
            if self.message_count == 5000:
                print("Strategy starts")
                self.logger.info("Strategy starts")
                self.logger.info("edge: " + str(self.edge) + " inside: " + str(self.inside_slobe) + " outside: " + str(self.outside_slobe))
                
            if product_id in ['BTC-USD', 'ETH-BTC'] and self.trading_start == 1:
                                
                new_ask_price = round(self.books["BTC-USD"].get_ask() * self.books["ETH-BTC"].get_ask() + self.edge, 2)
                new_bid_price = round(self.books["BTC-USD"].get_bid() * self.books["ETH-BTC"].get_bid() - self.edge, 2)

                new_ask_size = round(min(self.books["BTC-USD"].get_ask_size()/self.btcusd_bid_hedgeratio, self.books["ETH-BTC"].get_ask_size(), Decimal(0.02)), 8)
                new_bid_size = round(min(self.books["BTC-USD"].get_bid_size()/self.btcusd_ask_hedgeratio, self.books["ETH-BTC"].get_bid_size(), Decimal(0.02)), 8)
                
                #update our bid ask when price or size change
                if new_bid_price != 0 and new_bid_size != 0 and ((new_bid_size != self.bid_size) or (new_bid_price - self.bid_price > self.inside_slobe) or (new_bid_price - self.bid_price < -self.outside_slobe)):
                    if self.bid_order_id:
                        self.auth_client.cancel_order(self.bid_order_id)
                        self.bid_order_id = None
                    if new_bid_size < Decimal(0.019999):
                        self.bid_size = 0
                        self.logger.info("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
                        print("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
                        return
                    bid_response = self.auth_client.buy(product_id="ETH-USD", size=str(new_bid_size), price=str(new_bid_price))
                    self.logger.info("eth_usd bid order created: " + str(bid_response))
                    self.bid_order_id = bid_response['id']
                    self.my_orders.add(self.bid_order_id)
                    self.bid_price = new_bid_price
                    self.bid_size = new_bid_size
                    self.btcusd_bid_hedgeratio =  self.bid_price / self.books["BTC-USD"].get_bid()
                    self.logger.info(product_id + " update" + ': ' + 'Bid: ' + str(book.get_bid()) + ' Ask: ' + str(book.get_ask()))                    
                    self.logger.info("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
                    print("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
    
                if new_ask_price !=0 and new_ask_size != 0 and ((new_ask_size != self.ask_size) or (self.ask_price - new_ask_price > self.inside_slobe) or (self.ask_price - new_ask_price < -self.outside_slobe)):
                    if self.ask_order_id:
                        self.auth_client.cancel_order(self.ask_order_id)
                        self.ask_order_id = None
                    if new_ask_size < Decimal(0.019999):
                        self.ask_size = 0
                        self.logger.info("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
                        print("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
                        return
                    ask_response = self.auth_client.sell(product_id="ETH-USD", size=str(new_ask_size), price=str(new_ask_price))
                    self.logger.info("eth_usd ask order created: " + str(ask_response))
                    self.ask_order_id = ask_response['id']
                    self.my_orders.add(self.ask_order_id)
                    self.ask_price = new_ask_price
                    self.ask_size = new_ask_size
                    self.btcusd_ask_hedgeratio = self.ask_price / self.books["BTC-USD"].get_ask()
                    self.logger.info(product_id + " update" + ': ' + 'Bid: ' + str(book.get_bid()) + ' Ask: ' + str(book.get_ask()))
                    self.logger.info("eth_usd ask order created: " + str(ask_response))
                    self.logger.info("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
                    print("our ethusd: " + " bid: " + str(self.bid_price) + " " + str(self.bid_size) + " ask:  " + str(self.ask_price) + " " + str(self.ask_size))
            
            #when get a fill of ETH-USD
            if product_id == 'ETH-USD' and message['type'] == 'match':
                if  (message['taker_order_id'] in self.my_orders and message['side'] == 'sell') or (message['maker_order_id'] in self.my_orders and message['side'] == 'buy'):
                    self.logger.info("eth_usd buy fill message receive at " + self.auth_client.get_time()['iso'])
                    self.auth_client.sell(product_id="BTC-USD", size=str(round(self.bid_size*self.btcusd_bid_hedgeratio, 8)), type='market')
                    self.logger.info("btc_usd order placed at " + self.auth_client.get_time()['iso'])
                    self.auth_client.sell(product_id="ETH-BTC", size=str(self.bid_size), type='market')
                    self.logger.info("eth_btc order placed at " + self.auth_client.get_time()['iso'])
                    print("ethusd bid hit " + str(self.bid_price))
                    print("btcusd sell " + str(-round(self.bid_size*self.btcusd_bid_hedgeratio, 8)) + " at " + str(self.books["BTC-USD"].get_bid()))
                    print("ethbtc sell " + str(self.bid_size) + " at " + str(self.books["ETH-USD"].get_bid()))
                    self.logger.info("ethusd bid hit " + str(self.bid_price))
                    self.logger.info("btcusd sell " + str(-round(self.bid_size*self.btcusd_bid_hedgeratio, 8)) + " at " + str(self.books["BTC-USD"].get_bid()))
                    self.logger.info("ethbtc sell " + str(self.bid_size) + " at " + str(self.books["ETH-BTC"].get_bid()))
                     #limit to one trade and cancel all open orders
                    self.auth_client.cancel_all("ETH-USD")
                    print("Trade limit reached! Open orders are cancelled")
                    self.trading_start = 0
                    self.calc_fills_stat()
                    
                elif (message['taker_order_id'] in self.my_orders and message['side'] == 'buy') or (message['maker_order_id'] in self.my_orders and message['side'] == 'sell'):
                    self.logger.info("eth_usd sell fill message receive at " + self.auth_client.get_time()['iso'])
                    self.auth_client.buy(product_id="BTC-USD", size=str(round(self.ask_size*self.btcusd_ask_hedgeratio, 8)), type='market')
                    self.logger.info("btc_usd order placed at " + self.auth_client.get_time()['iso'])
                    self.auth_client.buy(product_id="ETH-BTC", size=str(self.ask_size), type='market')
                    self.logger.info("eth_btc order placed at " + self.auth_client.get_time()['iso'])
                    print("ethusd ask hit " + str(self.ask_price))
                    print("btcusd buy " + str(round(self.ask_size*self.btcusd_ask_hedgeratio, 8)) + " at " + str(self.books["BTC-USD"].get_ask()))                        
                    print("ethbtc buy " + str(self.ask_size) + " at " + str(self.books["ETH-USD"].get_ask()))
                    self.logger.info("ethusd ask hit " + str(self.ask_price))
                    self.logger.info("btcusd buy " + str(round(self.ask_size*self.btcusd_ask_hedgeratio, 8)) + " at " + str(self.books["BTC-USD"].get_ask()))                        
                    self.logger.info("ethbtc buy " + str(self.ask_size) + " at " + str(self.books["ETH-BTC"].get_ask()))
                    
                    #limit to one trade and cancel all open orders
                    self.auth_client.cancel_all("ETH-USD")
                    print("Trade limit reached! Open orders are cancelled")
                    self.logger.info("Trade limit reached! Open orders are cancelled")
                    self.logger.info("Strategy stopes")
                    self.trading_start = 0
                    self.calc_fills_stat()
        except Exception as e:
            print(e)
            logger.info(e)
            self._disconnect()
            
        



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logfilename = datetime.now().strftime('gdax_arb_%Y_%m_%d_%H_%M_%S.log')
handler = logging.FileHandler(logfilename)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)06d %(message)s',datefmt='%Y-%m-%d,%H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)


sandbox_wss_url = "wss://ws-feed-public.sandbox.gdax.com"
sandbox_rest_api = "https://api-public.sandbox.gdax.com"
sandbox_key = "6777f39458390bbf84ed25060bddc72d"
sandbox_b64secret = "VKSPYLpnEiuRRi4pOzrpgfozzfQxaZh+wGpZlEqbSA9Uyys/KWY9BHwfb7vIltHiPklju0hgCUkv9jD7/4gGHQ=="
sandbox_passphrase = "ximndivkdra"
sandbox_client = AuthenticatedClient(sandbox_key, sandbox_b64secret, sandbox_passphrase, sandbox_rest_api)

wss_url = "wss://ws-feed.gdax.com"
'''
rest_api = "https://api.gdax.com/"
key = "9cd546c9dc4048ae824fc072d6a2b5a3"
b64secret = "fA6DMH5Rr9K54epp7pMV0kvOsLLIv9A8Kaw7gJM88vrwPckz1GjmwQOVsbQwQ/apVJyqfjdZgjmYclGTks8dmA=="
passphrase = "dk0dj9le2d"
auth_client = AuthenticatedClient(key, b64secret, passphrase, rest_api)
'''
if __name__ == '__main__':    
    products = ['BTC-USD', 'ETH-USD', 'ETH-BTC']
    order_books = OrderBooks(product_ids=products, log_to=logger, wss_url=wss_url, rest_client=sandbox_client)
    try:
        order_books.start()
    #time.sleep(10)
    except KeyboardInterrupt:
        order_books.close()

'''
start = datetime.now()
auth_client.get_time()
end = datetime.now()
latency = (end - start)
print(str(latency.microseconds / 1000000) + 's')
'''
        
