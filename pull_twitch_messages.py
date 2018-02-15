import chat_connect
import select
import datetime as dt
import string

from config import *

# twitch IRC
s = chat_connect.openSocket()
s.setblocking(0)
#chat_connect.joinRoom(s)
readbuffer = ""

pull_twitch_messages_start_time = dt.datetime.now()
player_groups = {1:[], 2:[]}

def is_in_range_modulus(t1, t2, range, subrange):


while True:

    # reset chat
    if dt.datetime.now() - pull_twitch_messages_start_time > dt.timedelta(0,300,0):
        s = chat_connect.openSocket()
        s.setblocking(0)
        readbuffer = ""
        reset_chat = dt.datetime.now()

    if os.path.isfile('VTC.txt'): # keep looking for this file

        with open('VTC.txt') as f:
            contents = f.read().split('\n')

        screen_basetimes = []
        for row in contents:
            screen_basetimes.append(row)

        # run a check for all screens to see which needs to be written, then check for a new VTC (unlikely)
        for i, screen_basetime in emuerate(screen_basetimes):

            user_messages[i] = []

            # record messages if we are in a certain timezone of a screen
            while is_in_range_modulus(dt.datetime.now(), screen_basetime, 10, [0, 5]):

                print(dt.datetime.now())

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
                        message = chat_connect.getMessage(line).lower()
                        print(user + ' typed:' + message)

                        # put users in a specific group if they ask
                        if message == 'p1' and user not in player_groups[1]:
                            player_groups[1].append(user)
                        if message == 'p2' and user not in player_groups[2]:
                            player_groups[2].append(user)

                        # and of course add messages from dedicated users
                        if user in player_groups[1]:
                            messages_by_screen[1].append(message)
                        if user in player_groups[2]:
                            messages_by_screen[2].append(message)

                        user_messages.append([user, message])

            # exit recording and save messages
            print('{}: messages are: {}'.format(dt.datetime.now(), user_messages))

            with open(['s1_messages.txt', 's2_messages.txt'][i], 'w') as f:
                f.write(str(dt.datetime.now()))
                f.write('\n')
                for user, message in user_messages:
                    f.write(user)
                    f.write(':::')
                    f.write(message)
                    f.write('\n')
