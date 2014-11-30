#! /usr/bin/env python

# FROM: http://code.activestate.com/recipes/531824-chat-server-client-using-selectselect/
# FROM: http://stackoverflow.com/questions/960733/python-creating-a-dictionary-of-lists
# Matei Mitaru Networks Project CS494 Fall 2014 Portland State University
# Simple TCP socket server/client IRC protocol implementation using the python select module

import socket
import sys
import select
import time

BUFSIZ = 1024

class ChatClient():
    """ A simple command line chat client using select """

    def __init__(self):
        self.name = 'GUEST'
        # Quit flag
        self.flag = False
        self.port = 6667
        self.host = 'localhost'
        self.rooms = []
        self.rooms.append('Lobby')
        # Initial prompt
        self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        # Command list
        self.dispatch1 = {
            'NICK': self.do_nick,
            'CREATE': self.do_create,
            'JOIN': self.do_join,
            'LEAVE': self.do_leave,
            'QUIT': self.do_quit,
            'PING': self.do_ping,
            'PONG': self.do_pong
        }
        self.dispatch0 = {
            'LISTROOMS': self.do_listrooms,
            'LISTALLROOMS': self.do_listallrooms
        }
        # Connect to server at port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print 'Connected to chat server@%d' % self.port
            # Send my name...
            # send(self.sock,'NAME: ' + self.name)
            self.sock.send('NAME: ' + self.name)
            data = self.sock.recv(BUFSIZ)
            # Contains client address, set it
            #addr = data.split('CLIENT: ')[1]
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        except socket.error, e:
            print 'Could not connect to chat server @%d' % self.port
            sys.exit(1)

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

    def do_join(self, arg):
        # need to handle received "error"!
        temp = self.sock.recv(BUFSIZ).split()
        if (not arg in self.rooms) and temp[0] != "error":
            self.rooms.append(arg)
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        else: print self.prompt + "client error"

    def do_leave(self, arg):
        temp = self.sock.recv(BUFSIZ).split()
        if (arg in self.rooms) and temp[0] != "error":
            self.rooms.remove(arg)
            self.prompt='[' + '@'.join((self.name, '#' + '#'.join(self.rooms))) + ']> '
        else: print self.prompt + "client error"

    def do_quit(self, arg):pass

    def do_listrooms(self):
        time.sleep(.01)

    def do_listallrooms(self):
        time.sleep(.01)

    def do_ping(self, arg):
        print "PING command received"

    def do_pong(self, arg):pass

    def processcommand(self, command, arg):
        command = self.dispatch1[command]
        command(arg)

    def processnoargcommand(self, command):
        command = self.dispatch0[command]
        command()

    def control(self):

        while not self.flag:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                # Wait for input from stdin & socket
                inputready, outputready,exceptready = select.select([0, self.sock], [],[])

                for i in inputready:
                    if i == 0:
                        # send data from stdin to socket (server)
                        data = sys.stdin.readline().strip()
                        temp = data.split()
                        if data:
                            self.sock.send(data)
                            if temp[0] in self.dispatch1.keys() and len(temp) > 1:
                                self.processcommand(temp[0], temp[1])
                            elif temp[0] in self.dispatch0.keys():
                                self.processnoargcommand(temp[0])
                    elif i == self.sock:
                        # data = receive(self.sock)
                        data = self.sock.recv(BUFSIZ)
                        # handle broken connection
                        if not data:
                            print 'Shutting down.'
                            self.flag = True
                            break
                        else:
                            # print received messages
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()

            except KeyboardInterrupt:
                print 'Interrupted.'
                self.sock.close()
                break


if __name__ == "__main__":
    client = ChatClient()
    client.control()