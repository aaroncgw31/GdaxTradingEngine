#import sqlite3
import pickle
from message import MessageDirection
from session import FIXSession
import MySQLdb



class DuplicateSeqNoError(Exception):
    pass

class Journaler(object):
    def __init__(self, filename = None):
        
        self.conn = MySQLdb.connect(host="localhost", user="root", passwd="1234", db="TICKPREDICT")
        

        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS message("
                               "seqNo INTEGER NOT NULL,"
                               "session VARCHAR(512) NOT NULL ,"
                               "direction INTEGER NOT NULL,"
                               "msg TEXT,"
                               "PRIMARY KEY (seqNo, session, direction))")

        self.cursor.execute("CREATE TABLE IF NOT EXISTS session("
                               "sessionId INTEGER PRIMARY KEY AUTO_INCREMENT,"
                               "targetCompId VARCHAR(256) NOT NULL,"
                               "senderCompId VARCHAR(256) NOT NULL,"
                               "outboundSeqNo INTEGER DEFAULT 0,"
                               "inboundSeqNo INTEGER DEFAULT 0,"
                               "UNIQUE (targetCompId, senderCompId))")

    def sessions(self):
        sessions = []
        self.cursor.execute("SELECT sessionId, targetCompId, senderCompId, outboundSeqNo, inboundSeqNo FROM session")
        for sessionInfo in self.cursor:
            session = FIXSession(sessionInfo[0], sessionInfo[1], sessionInfo[2])
            session.sndSeqNum = sessionInfo[3]
            session.nextExpectedMsgSeqNum = sessionInfo[4] + 1
            sessions.append(session)

        return sessions

    def createSession(self, targetCompId, senderCompId):
        session = None
        try:
            self.cursor.execute("INSERT INTO session(targetCompId, senderCompId) VALUES('%s', '%s')" % (targetCompId, senderCompId))
            sessionId = self.cursor.lastrowid
            self.conn.commit()
            session = FIXSession(sessionId, targetCompId, senderCompId)
        except MySQLdb.IntegrityError:
            raise RuntimeError("Session already exists for TargetCompId: %s SenderCompId: %s" % (targetCompId, senderCompId))

        return session

    def persistMsg(self, msg, session, direction):
        msgStr = pickle.dumps(msg)
        seqNo = msg["34"]
        try:
            self.cursor.execute("INSERT INTO message VALUES('%s', '%s', '%s', '%s')" % (seqNo, session.key, direction.value, msg))
            if direction == MessageDirection.OUTBOUND:
                self.cursor.execute("UPDATE session SET outboundSeqNo={}".format(seqNo,))
            elif direction == MessageDirection.INBOUND:
                self.cursor.execute("UPDATE session SET inboundSeqNo={}".format(seqNo,))

            self.conn.commit()
        except MySQLdb.IntegrityError as e:
            raise DuplicateSeqNoError("%s is a duplicate" % (seqNo, ))

    def recoverMsg(self, session, direction, seqNo):
        try:
            msgs = self.recoverMsgs(session, direction, seqNo, seqNo)
            return msgs[0]
        except IndexError:
            return None

    def recoverMsgs(self, session, direction, startSeqNo, endSeqNo):
        self.cursor.execute("SELECT msg FROM message WHERE session = {} AND direction = {} AND seqNo >= {} AND seqNo <= {} ORDER BY seqNo".format(session.key, direction.value, startSeqNo, endSeqNo))
        msgs = []
        for msg in self.cursor:
            #msgs.append(pickle.loads(msg[0]))
            msgs.append(dict([item.split("=") for item in msg[0].split("|")]))
        return msgs

    def getAllMsgs(self, sessions = [], direction = None):
        sql = "SELECT seqNo, msg, direction, session FROM message"
        clauses = []
        args = []
        if sessions is not None and len(sessions) != 0:
            clauses.append("session in (" + ','.join('{}'*len(sessions)) + ")")
            args.extend(sessions)
        if direction is not None:
            clauses.append("direction = {}")
            args.append(direction.value)

        if clauses:
            sql = sql + " WHERE " + " AND ".join(clauses)

        sql = sql + " ORDER BY rowid"

        self.cursor.execute(sql, tuple(args))
        msgs = []
        for msg in self.cursor:
            msgs.append((msg[0], pickle.loads(msg[1]), msg[2], msg[3]))

        return msgs
        
    def resetDB(self):
        sql = "DROP table message"
        self.cursor.execute(sql)
        sql = "DROP table session"
        self.cursor.execute(sql)