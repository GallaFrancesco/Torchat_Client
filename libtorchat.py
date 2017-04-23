import json,socket
from time import strftime, localtime, ctime, sleep
# this is used for async send/recv on socket
from asyncore import dispatcher

class Torchat:
    def __init__ (self, host, port):
        self.host = host
        self.port = port
        # self.open_socket() # used to communicate with the daemon
        self.onion = self.get_hostname()

    def create_json (self, cmd='', msg='', id='localhost', portno=None):
        # create a dictionary and populate it, ready to be converted to a json string
        t = localtime()
        if portno == None:
            portno = self.port
        if cmd == '':
            raise ValueError ("NullCommand")
        else:
            j = dict ()
            j['id'] = id
            j['portno'] = int (portno)
            j['date'] = ctime ()[-13:]
            j['msg'] = msg
            j['cmd'] = cmd
            return j

    def open_socket(self):
        # opens a socket, sets its timeout to 2 mins
        try:
            sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
            sock.connect ((self.host, int (self.port)))
            sock.settimeout(120)
            return sock
        except ConnectionRefusedError:
            print("Unable to connect to the daemon. Is it running? [ConnectionRefusedError]")
        except:
            pass

    def format_message_length(self, buf):
        strLen = str(len(buf))
        if len(strLen) == 1:
            retLen = '000'+ strLen
        if len(strLen) == 2:
            retLen = '00' + strLen
        elif len(strLen) == 3:
            retLen = '0' + strLen
        # elif len(strLen) == 4:
        else:   
            retLen = strLen
        with open("line.txt", 'wb') as fp:
            fp.write(retLen.encode('utf-8'))
            fp.write(str(len(retLen)).encode('utf-8'))
        return retLen

    def send_to_daemon (self, j, wait=False):
        # send to the TORchat daemon
        # here we send, if unsuccessful, retry, and reset the connection if needed
        # try:
        lengthJson = self.format_message_length(json.dumps(j))
        sock = self.open_socket()
        msg = bytes (lengthJson, 'utf-8') + bytes(json.dumps(j), 'utf-8')
        sock.send (msg)
        if wait:
            recvSt = sock.recv (5000).decode ('utf-8')
            with open("line.txt", 'w') as fp:
                fp.write(recvSt)
                sock.close()
            resp = json.loads (recvSt[4:]) # a dictionary; skip first 4 chars that are the dimensionhead
            return resp
        else:
            sock.close()
        # except:
            # resp = dict()
            # resp['cmd'] = 'ERR'
            # resp['msg'] = "The client couldn't send the message. [ConnectionResetError]"
            # return resp

    def get_peers(self):        # returns a list
        # ask for a list of peers with pending messages
        j = self.create_json (cmd='GET_PEERS')
        resp = self.send_to_daemon (j, wait=True) 
        with open("tmp", 'w') as fp:
            fp.write('ciao')
        if resp != None:
            peerList = resp['msg'].split (',')
            return peerList
        else:
            return None

    def get_hostname(self):
        resp = self.send_message(command="HOST", line="", currentId="localhost", wait=True)
        return resp["msg"]

    def close_server (self):
        j = self.create_json(cmd='EXIT', msg='')
        self.send_to_daemon(j, wait=False)

    def send_message (self, command, line, currentId, sendPort="", wait=False): # added cmd for fileup needs
        # portno is the one used by the other server, usually 80
        if sendPort == "":
            sendPort = self.port
        j = self.create_json(cmd=command, msg=line, id=currentId, portno = sendPort)
        return self.send_to_daemon(j, wait)

    def check_error (self, j):
        if j['cmd'] == 'ERR':
            return j['msg']
        else:
            return False

    def check_new_messages (self, currId):
        # return List of tuples date, msg
        # could have used an iterator
        msgs = list ()
        while True:
            j = self.create_json (cmd='UPDATE', msg=currId)
            resp = self.send_to_daemon (j, wait=True)
            if resp['cmd'] == 'END':
                if msgs:
                    return msgs
                else:
                    return None
            else:
                msgs.append (resp)

    def check_new_messages_single (self, currId):
        j = self.create_json (cmd='UPDATE', msg=currId)
        resp = self.send_to_daemon (j, wait=True)
        if resp['cmd'] == 'END':
                return None
        else:
            return resp
