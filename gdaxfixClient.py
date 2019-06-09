"""
Created on Wed Jan 31 11:05:23 2018
@author: aaroncgw
"""

from enum import Enum
import logging
import uuid
import threading
import time
#import random
from datetime import datetime
from connection import ConnectionState, MessageDirection
from client_connection import FIXClient
from engine import FIXEngine
from message import FIXMessage
import setting
#from event import TimerEventRegistration


class Side(Enum):
    buy = 1
    sell = 2

class GdaxFixClient(FIXEngine):
    def __init__(self, auth):
        FIXEngine.__init__(self, "client_example.store")
        self.clOrdID = 0
        self.heartbeat_count = 0
        self.Stop = False
        self.orderTypeDict = {"market" : 1, "limit" : 2, "stop" : 3}
        self.orderSideDict = {"buy" : 1, "sell" : 2}
        #self.msgGenerator = None

        # create a FIX Client using the FIX 4.4 standard
        self.client = FIXClient(self, "FIX42", "Coinbase", "6777f39458390bbf84ed25060bddc72d", auth=auth)
        self.connectionHandler = None

    def connect(self):
        print("Connecting...")        
        # we register some listeners since we want to know when the connection goes up or down        
        self.client.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.client.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)

        # start our event listener indefinitely
        self.client.start('127.0.0.1', int("4197"))
        
    def start(self):          
        while True:
            self.eventManager.waitForEventWithTimeout(10.0)
            if self.Stop == True:
                break
            
    def stop(self):
        self.Stop = True
            
    def disconnect(self):
        print("Disconnecting...")        
        self.client.stop()

    def current_datetime(self):
        return datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")
        
    def onConnect(self, session):
        logging.info("Established connection to %s" % (session.address(), ))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON)
        session.addMessageHandler(self.onHeartBeat, MessageDirection.INBOUND, self.client.protocol.msgtype.HEARTBEAT)
        session.addMessageHandler(self.onExecutionReport, MessageDirection.INBOUND, self.client.protocol.msgtype.EXECUTIONREPORT)

    def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(), ))
        print("%s has disconnected" % (session.address(), ))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON)
        session.removeMessageHandler(self.onHeartBeat, MessageDirection.INBOUND, self.client.protocol.msgtype.HEARTBEAT)        
        session.removeMessageHandler(self.onExecutionReport, MessageDirection.INBOUND, self.client.protocol.msgtype.EXECUTIONREPORT)
        
        # some clean up before we shut down
        self.client.removeConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.client.removeConnectionListener(self.onConnect, ConnectionState.DISCONNECTED)

        #if self.msgGenerator:
            #self.eventManager.unregisterHandler(self.msgGenerator)

    def sendOrder(self, symbol, side, ordType, quantity, price=None, connectionHandler=None):
        if not connectionHandler:
           connectionHandler = self.connectionHandler 
        self.clOrdID = str(uuid.uuid4())
        codec = connectionHandler.codec
        msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
        if price and ordType == "limit":        
            msg.setField(codec.protocol.fixtags.Price, price)
        msg.setField(codec.protocol.fixtags.OrderQty, quantity)
        msg.setField(codec.protocol.fixtags.OrdType, self.orderTypeDict[ordType])
        msg.setField(codec.protocol.fixtags.TimeInForce, "1")
        msg.setField(codec.protocol.fixtags.Symbol, symbol)
        msg.setField(codec.protocol.fixtags.HandlInst, "1")
        msg.setField(codec.protocol.fixtags.Side, self.orderSideDict[side])
        msg.setField(codec.protocol.fixtags.ClOrdID, self.clOrdID)

        connectionHandler.sendMsg(msg)
        print("Send order at: " + str(self.current_datetime()))
        #side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
        #logging.debug("---> [%s] %s: %s %s %s@%s" % (codec.protocol.msgtype.msgTypeToName(msg.msgType), msg.getField(codec.protocol.fixtags.ClOrdID), msg.getField(codec.protocol.fixtags.Symbol), side.name, msg.getField(codec.protocol.fixtags.OrderQty), msg.getField(codec.protocol.fixtags.Price)))


    def onLogin(self, connectionHandler, msg):
        logging.info("Logged in")
        print("Logged in")
        self.connectionHandler = connectionHandler
        #self.sendOrder(connectionHandler)
        # lets do something like send and order every 3 seconds
        #self.msgGenerator = TimerEventRegistration(lambda type, closure: self.sendOrder(closure), 0.5, connectionHandler)
        #self.eventManager.registerHandler(self.msgGenerator)
        
    def onHeartBeat(self, connectionHandler, msg):
        codec = connectionHandler.codec
        msgType = codec.protocol.msgtype.msgTypeToName(msg.msgType)      
        time = msg.getField(codec.protocol.fixtags.SendingTime)        
        self.heartbeat_count = self.heartbeat_count + 1    
        print("%s: %s" % (msgType, time))
        #self.sendOrder()

    def onExecutionReport(self, connectionHandler, msg):
        print("Receive confirmation at: " + str(self.current_datetime()))
        print(msg)
        codec = connectionHandler.codec
        if codec.protocol.fixtags.ExecType in msg:
            if msg.getField(codec.protocol.fixtags.ExecType) == "0":
                side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
                logging.debug("<--- [%s] %s: %s %s %s@%s" % (codec.protocol.msgtype.msgTypeToName(msg.getField(codec.protocol.fixtags.MsgType)), msg.getField(codec.protocol.fixtags.ClOrdID), msg.getField(codec.protocol.fixtags.Symbol), side.name, msg.getField(codec.protocol.fixtags.OrderQty), msg.getField(codec.protocol.fixtags.Price)))                
                #print("New order sending time: %s" % msg.getField(codec.protocol.fixtags.SendingTime))
                #print("New order transact time : %s" % msg.getField(codec.protocol.fixtags.TransactTime))
            elif msg.getField(codec.protocol.fixtags.ExecType) == "4":
                reason = "Unknown" if codec.protocol.fixtags.Text not in msg else msg.getField(codec.protocol.fixtags.Text)
                logging.info("Order Rejected '%s'" % (reason,))
        else:
            logging.error("Received execution report without ExecType")
            
    def resetDB(self):
        self.journaller.resetDB()
        print("Database is reset")

def main():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    client = GdaxFixClient()
    client.connect()    
    client.start()
    #time.sleep(10)
    #client.sendOrder()
    #client.stop()
    logging.info("All done... shutting down")
    
auth = setting.sandbox_auth

if __name__ == "__main__":
    fixclient = GdaxFixClient(auth)
    fixclient.connect()
    fixManager = threading.Thread(target=fixclient.start)
    #orderManager = threading.Thread(target=trade, args=(msgEvents, fixclient))
    fixManager.start()
    '''
    while True:        
        #warm up a little bit
        if fixclient.heartbeat_count > 2:
            fixclient.sendOrder(symbol="BTC-USD", side="buy", ordType="limit", quantity=1, price=999)
            break        
        time.sleep(20)
    
    fixclient.stop()
    fixManager.join()
    fixclient.disconnect()
    fixclient.resetDB()
    '''
