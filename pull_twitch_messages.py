
import chat_connect
import select
import datetime
import string

# twitch IRC
s = chat_connect.openSocket()
s.setblocking(0)
#chat_connect.joinRoom(s)
readbuffer = ""

reset_chat = datetime.datetime.now()

decision_time = 17

while True:

    if datetime.datetime.now() - reset_chat > datetime.timedelta(0,300,0):
        s = chat_connect.openSocket()
        s.setblocking(0)
        readbuffer = ""
        reset_chat = datetime.datetime.now()

    user_messages = []

    timer_start = datetime.datetime.now()

    while datetime.datetime.now() - timer_start < datetime.timedelta(0, decision_time, 0):
        timeout = 1 #sec
        ready = select.select([s], [], [], timeout)

        print(datetime.datetime.now(), ready)

        #print ready
        if ready[0]:
            readbuffer = readbuffer + s.recv(1024)
            temp = string.split(readbuffer, '\n')
            readbuffer = temp.pop()
            for line in temp:
                if 'PING' in line:
                    s.send(line.replace('PING', 'PONG'))
                    break
                user = chat_connect.getUser(line)
                message = chat_connect.getMessage(line)
                print(user + ' typed:' + message)

                user_messages.append(message[:-1].lower())

    print('{}: messages are: {}'.format(datetime.datetime.now(), user_messages))

    with open('messages.txt', 'w') as f:
        f.write(str(datetime.datetime.now()))
        f.write('\n')
        for message in user_messages:
            f.write(message)
            f.write('\n')
