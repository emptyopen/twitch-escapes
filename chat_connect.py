import string
import socket
import datetime
import os

HOST = "irc.twitch.tv"
PORT = 6667

with open(os.pardir + '/auth/oauth.txt') as f:
	PASS = f.read()

IDENT = 'escape_bot'
CHANNEL = 'twitch_escapes'

def openSocket():
	s = socket.socket()
	s.connect((HOST, PORT))
	s.send("PASS " + PASS + "\r\n")
	s.send("NICK " + IDENT + "\r\n")
	s.send("JOIN #" + CHANNEL + "\r\n")
	return s

def sendMessage(s, message):
	messageTemp = "PRIVMSG #" + CHANNEL + " :" + message
	s.send(messageTemp + "\r\n")
	print("Sent: " + messageTemp)

def getUser(line):
	separate = line.split(":", 2)
	user = separate[1].split("!", 1)[0]
	return user

def getMessage(line):
	if ':' in line:
		separate = line.split(":", 2)
		if len(separate) > 2:
			return separate[2]
		else:
			return separate[-1]
	else:
		return line

def joinRoom(s):
	readbuffer = ""
	Loading = True
	while Loading:
		readbuffer = readbuffer + s.recv(1024)
		temp = string.split(readbuffer, "\n")
		readbuffer = temp.pop()

		for line in temp:
			###print(line)
			Loading = loadingComplete(line)
	sendMessage(s, "Successfully joined chat")

def loadingComplete(line):
	if("End of /NAMES list" in line):
		return False
	else:
		return True




###
