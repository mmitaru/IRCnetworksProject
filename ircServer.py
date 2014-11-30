#!/usr/bin/env python


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


import select
import socket
import sys
import signal
from collections import defaultdict

BUFSIZ = 1024

class ChatServer(object):

    def __init__(self, port=6667, backlog=5):
        # keeps count of connected clients
        self.clients = 0
        # maps clients to nicknames
        self.clientmap = {}
        # maps rooms to [clients]
        self.roommap = defaultdict(list)
        # maps clients to [rooms]
        self.clientroommap = defaultdict(list)
        # command list: 1 arg commands - maps command literals to class methods
        self.dispatch1 = {
            'NICK': self.do_nick,
            'CREATE': self.do_create,
            'JOIN': self.do_join,
            'PART': self.do_leave,
            '#': self.do_broadcasttoroom
        }
        # command list: 0 arg commands - maps command literals to class methods
        self.dispatch0 = {
            'LISTROOMS': self.do_listrooms,
            'LISTALLROOMS': self.do_listallrooms,
            'QUIT': self.do_quit,
            'NAMES': self.do_names
        }
        # Output socket list
        self.outputs = []
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('', port))
        print "Listening on port", port, "..."
        self.server.listen(backlog)
        # catch interrupts, pass in our own handler
        signal.signal(signal.SIGINT, self.signalhandler)

    # 'signum' and 'frame' are required params for the signal handler passed to signal()
    def signalhandler(self, signum, frame):
        print "Shutting down server..."
        # close existing client sockets
        for o in self.outputs:
            o.close()
        self.server.close()

    # return the nickname of a client connection
    def getname(self, client):
        info = self.clientmap[client]
        return info[1] + '@'

    # accept a connection from a client
    def connectclient(self, inputs):
        # handle the server socket
        client, address = self.server.accept()
        print "New client connected..."
        # register new user, place in 'Lobby'
        cname = client.recv(BUFSIZ).split('NAME: ')[1]
        self.clients += 1
        inputs.append(client)
        self.roommap['Lobby'].append(client)
        self.clientroommap[client].append('Lobby')
        self.clientmap[client] = (address, cname)
        # let other clients know there is a new user
        msg = "Connected: New client- " + self.getname(client)
        for o in self.outputs:
            o.send(msg)
        self.outputs.append(client)

    # update nickname
    def do_nick(self, client, arg):
        self.clientmap[client] = (self.clientmap[client][0], arg)

    # create room
    def do_create(self, client, arg):
        if not self.roommap.has_key(arg):
            self.roommap[arg].append(client)
            self.clientroommap[client].append(arg)
            client.send("ok")
        else:
            client.send("error")

    # join room
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

    # leave room ('PART')
    def do_leave(self, client, arg):
        if self.roommap.has_key(arg) and arg in self.clientroommap[client]:
            self.roommap[arg].remove(client)
            self.clientroommap[client].remove(arg)
            client.send("ok")
        else:
            client.send("error")

    # quit chat
    def do_quit(self, client):
        for r in self.roommap:
            if client in self.roommap[r]:
                self.roommap[r].remove(client)
        self.clientroommap.pop(client)
        self.clients -= 1

    # list rooms client belongs to
    def do_listrooms(self, client):
        for r in self.clientroommap[client]:
            client.send("\n" + r)

    # list all rooms
    def do_listallrooms(self, client):
        for r in self.roommap:
            client.send("\n" + r)

    # list names of users who share rooms with client
    def do_names(self, client):
        for r in self.clientroommap[client]:
            for c in self.roommap[r]:
                if self.getname(c) != self.getname(client):
                    client.send("\n" + self.getname(c) + r)

    # broadcast message to specified room ('#roomname')
    def do_broadcasttoroom(self, client, arg):
        data = arg.split()
        room = data[0].strip('#')
        data.pop(0)
        message = ""
        for i in data:
            message += i + " "
        if room in self.roommap.keys():
            for c in self.roommap[room]:
                if c != client:
                    msg = '\n#[' + self.getname(client) + room + ']>> ' + message
                    c.send(msg)

    # execute command with arg
    def processcommand(self, client, command, arg):
        command = self.dispatch1[command]
        command(client, arg)

    # execute command without arg
    def processnoargcommand(self, client, command):
        command = self.dispatch0[command]
        command(client)

    # process incoming data, send out appropriate responses
    def handleclients(self, inputs, s):
        try:
            # examine the data
            data = s.recv(BUFSIZ)
            if data:
                temp = data.split()
                # commands that take an argument
                if temp[0] in self.dispatch1.keys():
                    if len(temp) == 1:
                        print temp[0] + " requires at least one argument."
                    else:
                        self.processcommand(s, temp[0], temp[1])
                # broadcast to specific room only
                elif temp[0].startswith('#'):
                    temp[0].strip('#')
                    message = ""
                    for i in temp:
                        message += i + " "
                    self.processcommand(s, '#', message)
                # no arg commands
                elif temp[0] in self.dispatch0.keys():
                    self.processnoargcommand(s, temp[0])
                else:
                    # send data to clients in our rooms
                    for r in self.clientroommap[s]:
                        for o in self.roommap[r]:
                            if o != s:
                                msg = '\n#[' + self.getname(s) + r + ']>> ' + data
                                o.send(msg)
            else:
                print "Client hung up"
                self.clients -= 1
                s.close()
                inputs.remove(s)
                self.outputs.remove(s)
                # send client leaving information to others
                msg = self.getname(s) + " has left chat."
                for o in self.outputs:
                    o.send(msg)

        except socket.error, e:
            # remove lost client
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