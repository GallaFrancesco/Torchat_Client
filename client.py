import readline
import rlcompleter
from curses import wrapper
import curses
from time import sleep
from threading import Thread, Lock
import threading

from libtorchat import Torchat
from cursesUI import ChatUI
# many thanks to https://github.com/calzoneman/python-chatui.git
# for this curses implementation of a chat UI


class Completer(object):
    # this is a completer that works on the input buffer
    'The completer class for gnu readline'

    def __init__(self, options):
        self.options = sorted(options)

    def update (self, options):
        # use this method to add options to the completer
        self.options.extend (options)

    def complete(self, text, state=0):
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]

        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = ''
        return response

class Client:
    # main class for the client
    # args are the UI class and the Torchat class
    # (initialized in main)
    def __init__(self, ui, torchat):
        self.ui = ui;
        self.torchat = torchat;
        self.currId = ""
        self.peerList, i = self.get_peers()
        self.currId = self.peerList[i]
        self.printBuf = list()
        self.exitFlag = False
        self.filePath = None
        self.fileName = None

    def print_line_cur (self, line, color):
        # append sent messages and received messages to the buffer
        # then send them to the ui and pop them one by one
        # global printBuf
        self.printBuf.append (line)
        for l in self.printBuf:
            self.ui.chatbuffer_add(l, color)
            self.printBuf.pop()

    def send_input_message (self, msg):
        # this sends the message to the peer
        # does not deal with commands to the client
        # send_message is multithread because socket recv is blocking
        resp = self.torchat.send_message(command="SEND", line=msg, currentId=self.currId, sendPort=80, wait=True)
        if resp['cmd'] == 'ERR':
            self.print_line_cur(resp['msg'], 1)

    def elaborate_command (self, line):
        # this processes the commands received from the input buffer (the ones with "/")
        # global exitFlag
        # global currId
        if line == '/exit':
        # this sends an exit to the client AND to the server
            # self.torchat.send_message(command='EXIT', line='', currentId="localhost", wait=False)
            self.exitFlag = True
            self.torchat.close_server()
            exit ()
        elif line == '/quit':
            # only the client exits here
            self.exitFlag = True
            exit()
        elif line == '/peer':
            # update peers list, possibly select a new one
            self.peerList, i = self.get_peers()
            currId = self.peerList[i]
            self.ui.chatbuffer = []
            self.ui.linebuffer = []
            self.ui.redraw_ui(i)
        elif '/fileup' in line:
            data = line.split(' ')
            if len(data) != 3:
                self.print_line_cur("/fileup [filePath] [fileName]", 1)
                return
            self.filePath = data[1]
            self.fileName = data[2]
            msg = self.filePath + " " + self.fileName + " " + self.currId
            # upload files: start by requiring an handshake to the peer
            self.torchat.send_message(command='FILEALLOC', line=msg, currentId=self.currId, wait=False)

    def send_file_info (self, port):
        fileInfo = self.filePath + " " + self.fileName + " " + port + " " + self.currId
        self.torchat.send_message('FILEINFO', fileInfo, "localhost", wait=False)

    def get_peers(self):
        # ask for a list of peers with pending messages
        peerList = self.torchat.get_peers()
        if peerList[0] == "ERR":
            self.ui.chatbuffer_add(peerList[1])
            self.exitFlag = True
            exit()
        rightId = False

        # this part is the peer list UI management
        if peerList[0] == '' and not self.ui.userlist: # no peers have written you, previous list is empty
            i = 0
            peerList[0] = self.ui.wait_input("Onion Address: ")
            if not peerList[0] in self.ui.userlist:
                self.ui.userlist.append(peerList[0])
            self.ui.redraw_userlist(i, self.torchat.onion) # this redraws only the user panel
            if self.currId != "":
                self.ui.userlist.append(self.currId)
        else:
            for userid in peerList: # print them all with an integer id associated
                if userid != "" and not userid in self.ui.userlist:
                    self.ui.userlist.append(userid)
            # if self.currId != "" and not self.currId in peerList:
                # self.ui.userlist.append(self.currId)
            i = self.ui.scroll_userlist(self.currId, self.torchat.onion)
            peerList = self.ui.userlist
        return peerList, i

def update_routine(cli):
    # this function queries the server for unread messages
    # it runs until no messages from the given peer are left
    # then waits half a second and queries again
    while True:
        if cli.exitFlag:
            cli.ui.close_ui()
            exit()
        resp = cli.torchat.send_message (command="UPDATE", line=cli.currId, currentId="localhost", sendPort=8000, wait=True)
            # fp.write('\n')
        # the json is not printed if no messages are received
        if resp['cmd'] == 'END':
            sleep(0.5)
        # elif resp['cmd'] == 'FILEPORT':
            # cli.send_file_info(resp['msg'])
        else:
            try:
                cli.print_line_cur ('[' + resp['date'] + '] ' + resp['msg'], 3) 
            except:
                pass

def input_routine (cli):
    # processes the input buffer each return
    c = Completer (['/help', '/exit', '/quit', '/peer', '/fileup'])
    while True:
        # the input is taken from the bottom window in the ui
        # and printed directly (it is actually sent below)
        line = cli.ui.wait_input(completer = c)
        if len (line) > 0 and line[0] != '/':
            # here we send to mongoose / tor
            # if the user does not input a command send the message (done on a separate thread)
            cli.print_line_cur (line, 2)
            td = Thread(target=cli.send_input_message, args=(line,))
            td.start ()
            c.update ([line])
        elif line != "":
            # the user inputs a command,
            # they start with "/"
            cli.elaborate_command(line)

def main (stdscr, t):
    global currId

    # initialize UI class
    stdscr.clear()
    ui = ChatUI(stdscr)

    # initialize client
    cli = Client(ui, t)
    # here we use one thread to update unread messages in background,
    # the foreground one gets the input
    # they both work on the same buffer (printBuf) and thus a
    # semaphore is needed to prevent race conditions
    t1 = Thread(target=update_routine, args=(cli,))
    t1.start()
    input_routine (cli)

# the wrapper is a curses function which performs a standard init process
# the ui init is then continued by the call to the ChatUi class (see main)
if __name__ == '__main__':
    from sys import argv
    # here since it must check connection before starting the curses wrapper
    # initialize Torchat class
    t = Torchat(argv[1], argv[2])
    wrapper(main, t)
