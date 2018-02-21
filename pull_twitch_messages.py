import chat_connect
import select
import datetime as dt
import string
import time

from config import *

# twitch IRC
s = chat_connect.openSocket()
s.setblocking(0)
#chat_connect.joinRoom(s)
readbuffer = ""

pull_twitch_messages_start_time = dt.datetime.now()
player_groups = {1:[], 2:[]}

try:
    os.remove('vtc.txt')
except:
    pass

while True: # this loop never ends until user CTRL+C

    if os.path.isfile('vtc.txt'): # keep looking for vote timing command

        with open('vtc.txt') as f:
            basetime = dt.datetime.strptime(f.read(), '%Y-%m-%d %H:%M:%S.%f')
        os.remove('vtc.txt')

        # these checkpoints will be continuously reset to add 10 seconds each time
        c1 = basetime
        c2 = basetime + dt.timedelta(seconds = 10)
        cp = [c1, c2]

        print()

        user_messages = [[], []]

        while True:

            # reset chat
            if dt.datetime.now() - pull_twitch_messages_start_time > dt.timedelta(0,300,0):
                s = chat_connect.openSocket()
                s.setblocking(0)
                readbuffer = ""
                pull_twitch_messages_start_time = dt.datetime.now()

            if os.path.isfile('vtc.txt'): # if a new one pop ups, restart
                with open('vtc.txt') as f:
                    basetime = dt.datetime.strptime(f.read(), '%Y-%m-%d %H:%M:%S.%f')
                os.remove('vtc.txt')
                print('starting with new providing VTC')
                c1 = basetime
                c2 = basetime + dt.timedelta(seconds = 10)
                cp = [c1, c2]

            # add all messages to a running buffer (length 20s for now)
            # if current time hits a checkpoint, pack up all relevant messages and send it to file

            timeout = 1 #sec
            ready = select.select([s], [], [], timeout)

            #print ready
            if ready[0]:

                readbuffer = readbuffer + s.recv(1024)
                temp = string.split(readbuffer, '\n')
                readbuffer = temp.pop()

                for line in temp:

                    # respond to twitch
                    if 'PING' in line:
                        s.send(line.replace('PING', 'PONG'))
                        break

                    # get users and messages
                    user = chat_connect.getUser(line)
                    message = chat_connect.getMessage(line).lower()[:-1] # -1 removes /r char
                    print(user + ' typed:' + message)

                    # put users in a specific group if they ask
                    if message == 'p1' and user not in player_groups[1]:
                        player_groups[1].append(user)
                    elif message == 'p2' and user not in player_groups[2]:
                        player_groups[2].append(user)

                    # add messages from temp commands
                    elif 'p1' in message:
                        user_messages[0].append([user, ' '.join(message.split(' ')[1:])])
                    elif 'p2' in message:
                        user_messages[1].append([user, ' '.join(message.split(' ')[1:])])

                    # and of course add messages from dedicated users
                    elif user in player_groups[1]:
                        user_messages[0].append([user, message])
                    elif user in player_groups[2]:
                        user_messages[1].append([user, message])
                    else:
                        user_messages[0].append([user, message])


            for i, c in enumerate(cp): # check each checkpoint

                if c - dt.datetime.now() < dt.timedelta(0) or c - dt.datetime.now() < dt.timedelta(0) > dt.timedelta(seconds = 86000):
                    # save messages
                    cp[i] += dt.timedelta(seconds = 20)
                    print('{} messages are: {}'.format(i+1, user_messages[i]))
                    print(cp)
                    with open(['s1_messages.txt', 's2_messages.txt'][i], 'w') as f:
                        f.write(str(cp[i]))
                        f.write('\n')
                        for user, message in user_messages[i]:
                            f.write(user)
                            f.write(':::')
                            f.write(message)
                            f.write('\n')
                    user_messages[i] = [] # reset group messages

    else:
        print('{}: Looking for vtc.txt...'.format(dt.datetime.now()))
        time.sleep(5)




##
