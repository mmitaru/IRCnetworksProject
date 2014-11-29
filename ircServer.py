# import SocketServer
# from collections import defaultdict
# import Queue
# import threading
# import thread
# import select

# FROM: http://code.activestate.com/recipes/531824-chat-server-client-using-selectselect/


# First the server

#!/usr/bin/env python

"""
A basic, multiclient 'chat server' using Python's select module
with interrupt handling.

Entering any line of input at the terminal will exit the server.
"""

import select
import socket
import sys
import signal
# from communication import send, receive

BUFSIZ = 1024


class ChatServer(object):
    """ Simple chat server using select """

    def __init__(self, port=6667, backlog=5):
        self.clients = 0
        # Client map
        self.clientmap = {}
        # Room map
        self.roommap = {}
        # Command list
        self.dispatch = {
            'NICK': self.do_nick,
            'CREATE': self.do_create,
            'JOIN': self.do_join,
            'QUIT': self.do_quit,
            'LISTROOMS': self.do_listrooms,
            'LISTALLROOMS': self.do_listallrooms,
            'PING': self.do_ping,
            'PONG': self.do_pong
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

        # Return the printable name of the
        # client, given its socket...
        info = self.clientmap[client]
        host, name = info[0][0], info[1]
        return '@'.join((name, host))

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

        self.clientmap[client] = (address, cname)
        # Send joining information to other clients
        msg = '\n(Connected: New client (%d) from %s)' % (self.clients, self.getname(client))
        for o in self.outputs:
            o.send(msg)

        self.outputs.append(client)

    def do_nick(self, client, arg):
        self.clientmap[client] = (self.clientmap[client][0], arg)
        print "NICK command received"
    def do_create(self, client, arg):pass
    def do_join(self, client, arg):pass
    def do_quit(self, client, arg):pass
    def do_listrooms(self, client, arg):pass
    def do_listallrooms(self, client, arg):pass
    def do_ping(self, client, arg):
        print "PING command received"
    def do_pong(self, client, arg):pass

    def processcommand(self, client, command, arg):
        command = self.dispatch[command]
        command(client, arg)

    def handleclients(self, inputs, s):
        # handle all other sockets
        try:
            data = s.recv(BUFSIZ)
            # data = receive(s)
            if data:

                temp = data.split()
                if temp[0] in self.dispatch.keys():
                    if len(temp) == 1:
                        print temp[0] + " requires at least one argument"
                    else:
                        self.processcommand(s, temp[0], temp[1])
                else:
                    # Send as new client's message...
                    msg = '\n#[' + self.getname(s) + ']>> ' + data
                    # Send data to all except ourselves
                    for o in self.outputs:
                        if o != s:
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