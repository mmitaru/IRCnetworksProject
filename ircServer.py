#!/usr/bin/env python

# FROM: http://code.activestate.com/recipes/531824-chat-server-client-using-selectselect/
# FROM: http://stackoverflow.com/questions/960733/python-creating-a-dictionary-of-lists
# Matei Mitaru Networks Project CS494 Fall 2014 Portland State University
# Simple TCP socket server/client IRC protocol implementation using the python select module

import select
import socket
import sys
import signal
from collections import defaultdict

BUFSIZ = 1024

class ChatServer():

    def __init__(self, port=6667, backlog=5):
        self.clients = 0
        # Client map
        self.clientmap = {}
        # Room map
        self.roommap = defaultdict(list)
        # client-room-map
        self.clientroommap = defaultdict(list)
        # Command list: 1 arg commands
        self.dispatch1 = {
            'NICK': self.do_nick,
            'CREATE': self.do_create,
            'JOIN': self.do_join,
            'LEAVE': self.do_leave,
            'QUIT': self.do_quit,
            'PING': self.do_ping,
            'PONG': self.do_pong
        }
        # Command list: 0 arg commands
        self.dispatch0 = {
            'LISTROOMS': self.do_listrooms,
            'LISTALLROOMS': self.do_listallrooms
        }
        # Output socket list
        self.outputs = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('',port))
        print 'Listening to port',port,'...'
        self.server.listen(backlog)
        # Trap keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)

    def sighandler(self, signum, frame):
        # Close the server
        print 'Shutting down server...'
        # Close existing client sockets
        for o in self.outputs:
            o.close()

        self.server.close()

    def getname(self, client):
        info = self.clientmap[client]
        return info[1] + '@'


    def connectclient(self, inputs):
        # handle the server socket
        client, address = self.server.accept()
        print 'chatserver: got connection %d from %s' % (client.fileno(), address)
        # Read the login name
        cname = client.recv(BUFSIZ).split('NAME: ')[1]

        # Compute client name and send back
        self.clients += 1
        client.send('CLIENT: ' + str(address[0]))
        inputs.append(client)
        self.roommap['Lobby'].append(client)
        self.clientroommap[client].append('Lobby')

        self.clientmap[client] = (address, cname)
        # Send joining information to other clients
        msg = '\n(Connected: New client (%d) from %s)' % (self.clients, self.getname(client))
        for o in self.outputs:
            o.send(msg)

        self.outputs.append(client)

    def do_nick(self, client, arg):
        self.clientmap[client] = (self.clientmap[client][0], arg)

    def do_create(self, client, arg):
        if not self.roommap.has_key(arg):
            self.roommap[arg].append(client)
            self.clientroommap[client].append(arg)
            client.send("ok")
        else:
            client.send("error")

    def do_join(self, client, arg):
        if self.roommap.has_key(arg):
            if not arg in self.clientroommap[client]:
                self.clientroommap[client].append(arg)
                self.roommap[arg].append(client)
                client.send('ok')
            else:
                client.send("error")
        else:
            client.send("error")

    def do_leave(self, client, arg):
        if self.roommap.has_key(arg) and arg in self.clientroommap[client]:
            self.roommap[arg].remove(client)
            self.clientroommap[client].remove(arg)
            client.send("ok")
        else:
            client.send("error")

    def do_quit(self, client, arg):pass

    def do_listrooms(self, client):
        for r in self.clientroommap[client]:
            client.send("\n" + r)

    def do_listallrooms(self, client):
        for r in self.roommap:
            client.send("\n" + r)

    def do_ping(self, client, arg):pass

    def do_pong(self, client, arg):pass

    def processcommand(self, client, command, arg):
        command = self.dispatch1[command]
        command(client, arg)

    def processnoargcommand(self, client, command):
        command = self.dispatch0[command]
        command(client)

    def handleclients(self, inputs, s):
        # handle all other sockets
        try:
            data = s.recv(BUFSIZ)
            # data = receive(s)
            if data:

                temp = data.split()
                if temp[0] in self.dispatch1.keys():
                    if len(temp) == 1:
                        print temp[0] + " requires at least one argument"
                    else:
                        self.processcommand(s, temp[0], temp[1])
                elif temp[0] in self.dispatch0.keys():
                    self.processnoargcommand(s, temp[0])
                else:
                    # Send as new client's message...
                    #msg = '\n#[' + self.getname(s) + ']>> ' + data
                    # Send data to all except ourselves
                    #for o in self.outputs:
                    #    if o != s:
                    #        o.send(msg)
                    # send data to clients in our rooms
                    for r in self.clientroommap[s]:
                        for o in self.roommap[r]:
                            if o != s:
                                msg = '\n#[' + self.getname(s) + r + ']>> ' + data
                                o.send(msg)
            else:
                print 'chatserver: %d hung up' % s.fileno()
                self.clients -= 1
                s.close()
                inputs.remove(s)
                self.outputs.remove(s)

                # Send client leaving information to others
                msg = '\n(Hung up: Client from %s)' % self.getname(s)
                for o in self.outputs:
                    o.send(msg)

        except socket.error, e:
            # Remove
            inputs.remove(s)
            self.outputs.remove(s)

    def serve(self):

        inputs = [self.server,sys.stdin]
        self.outputs = []

        running = 1

        while running:

            try:
                inputready,outputready,exceptready = select.select(inputs, self.outputs, [])
            except select.error, e:
                break
            except socket.error, e:
                break

            for s in inputready:

                if s == self.server:
                    # handle the server socket
                    self.connectclient(inputs)

                elif s == sys.stdin:
                    # handle standard input (ie exit)
                    junk = sys.stdin.readline()
                    running = 0
                else:
                    # handle all other sockets
                    self.handleclients(inputs, s)

        self.server.close()

if __name__ == "__main__":
    ChatServer().serve()