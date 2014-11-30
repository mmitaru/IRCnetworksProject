#! /usr/bin/env python


# Matei Mitaru, Networks Project, CS494, Fall 2014, Portland State University.
# Simple TCP socket server/client IRC protocol implementation using the python select module.
# 3 data structures are used to track client info: clients-nickname map, rooms-[clients] map, and clients-[rooms] map.
# 2 dispatch dictionaries mapping command literals to class methods.
# Using the select module, the control loop examines inputs stdin and socket connections to the server.
# Input data is examined and processed accordingly, and client messages are delivered when needed.

# SOURCES:
# http://code.activestate.com/recipes/578591-primitive-peer-to-peer-chat/
# http://code.activestate.com/recipes/531824-chat-server-client-using-selectselect/
# http://stackoverflow.com/questions/960733/python-creating-a-dictionary-of-lists
# https://docs.python.org/2/library/select.html
# https://docs.python.org/2/library/socket.html
# https://docs.python.org/2/library/signal.html


import socket
import sys
import select
import time

BUFSIZ = 1024
CHILL = .01

class ChatClient(object):

    def __init__(self):
        self.name = 'GUEST'
        # quit flag
        self.flag = False
        self.port = 6667
        self.host = 'localhost'
        self.rooms = []
        self.rooms.append('Lobby')
        # prompt
        self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        # command list (1 arg)- dictionary mapping command literals to class methods
        self.dispatch1 = {
            'NICK': self.do_nick,
            'CREATE': self.do_create,
            'JOIN': self.do_join,
            'PART': self.do_leave,
            'QUIT': self.do_quit
        }
        # command list (0 arg)- dictionary mapping command literals to class methods
        self.dispatch0 = {
            'LISTROOMS': self.do_listrooms,
            'LISTALLROOMS': self.do_listallrooms,
            'QUIT': self.do_quit,
            'NAMES':self.do_names
        }
        # register first time user
        print "\nPlease enter your nickname >"
        self.name = sys.stdin.readline().strip()
        # connect to server at port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print "Connected to chat server"
            self.sock.send('NAME: ' + self.name)
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        except socket.error, e:
            print "Could not connect to chat server"
            sys.exit(1)

    # update nickname
    def do_nick(self, arg):
        self.name = arg
        self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '

    # create room
    def do_create(self,arg):
        # need to handle received "error"!
        temp = self.sock.recv(BUFSIZ).split()
        if not arg in self.rooms and temp[0] != "error":
            self.rooms.append(arg)
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        else: print self.prompt + "client error"

    # join room
    def do_join(self, arg):
        # need to handle received "error"!
        temp = self.sock.recv(BUFSIZ).split()
        if (not arg in self.rooms) and temp[0] != "error":
            self.rooms.append(arg)
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        else: print self.prompt + "client error"

    # leave a room ('PART')
    def do_leave(self, arg):
        temp = self.sock.recv(BUFSIZ).split()
        if (arg in self.rooms) and temp[0] != "error":
            self.rooms.remove(arg)
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        else: print self.prompt + "client error"

    # leave chat
    def do_quit(self):
        time.sleep(CHILL)
        print "\nclosing connection..."
        self.flag = True
        self.sock.close()

    # list rooms that this client belongs to
    def do_listrooms(self):
        time.sleep(CHILL)

    # list all available rooms
    def do_listallrooms(self):
        time.sleep(CHILL)

    # list names of all users that share at least one room with this client
    def do_names(self):
        time.sleep(CHILL)

    # execute command (1 arg)
    def processcommand(self, command, arg):
        command = self.dispatch1[command]
        command(arg)

    # execute command (no args)
    def processnoargcommand(self, command):
        command = self.dispatch0[command]
        command()

    def control(self):
        # control loop
        while not self.flag:
            try:
                # display prompt
                sys.stdout.write(self.prompt)
                sys.stdout.flush()
                # check for input from stdin and socket
                inputready, outputready,exceptready = select.select([0, self.sock], [],[])
                for i in inputready:
                    if i == 0:
                        # read input from stdin
                        data = sys.stdin.readline().strip()
                        temp = data.split()
                        if data:
                            # send input data to the server
                            self.sock.send(data)
                            # if client user issued a command, process it
                            if temp[0] in self.dispatch1.keys() and len(temp) > 1:
                                self.processcommand(temp[0], temp[1])
                            elif temp[0] in self.dispatch0.keys():
                                self.processnoargcommand(temp[0])
                    elif i == self.sock:
                        # read input from socket
                        data = self.sock.recv(BUFSIZ)
                        # handle broken connection
                        if not data:
                            print 'Shutting down...'
                            self.flag = True
                            break
                        else:
                            # print received messages
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()
            except KeyboardInterrupt:
                print "Closing connection..."
                self.sock.close()
                break

if __name__ == "__main__":
    client = ChatClient()
    client.control()