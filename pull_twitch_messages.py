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


while True: # this loop never ends until user CTRL+C

    # reset chat
    if dt.datetime.now() - pull_twitch_messages_start_time > dt.timedelta(0,300,0):
        s = chat_connect.openSocket()
        s.setblocking(0)
        readbuffer = ""
        pull_twitch_messages_start_time = dt.datetime.now()

    if os.path.isfile('basetime.txt'): # keep looking for this file

        with open('basetime.txt') as f:
            basetime = dt.datetime.strptime(f.read(), '%Y-%m-%d %H:%M:%S.%f')

        # these checkpoints will be continuously reset to add 10 seconds each time
        c1 = basetime
        c2 = basetime + dt.timedelta(seconds = 10)

        user_messages = [[], []]

        while True:

            # add all messages to a running buffer (length 20s for now)
            # if current time hits a checkpoint, pack up all relevant messages and send it to file

            print(dt.datetime.now())

            if dt.datetime.now() - pull_twitch_messages_start_time > dt.timedelta(0,300,0):
                break # reset the check for a new basetime every 5 min

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
                        user_messages[0].append([user, message])
                    elif user in player_groups[2]:
                        user_messages[1].append([user, message])
                    else:
                        user_messages[0].append([user, message])


            for i, cp in enumerate([c1, c2]): # check each checkpoint

                if cp - dt.datetime.now() < dt.timedelta(0):
                    # save messages
                    cp += dt.timedelta(seconds = 20)
                    print('{}: messages for screen {} are: {}'.format(dt.datetime.now(), i+1, user_messages))
                    with open(['s1_messages.txt', 's2_messages.txt'][i], 'w') as f:
                        f.write(str(cp))
                        f.write('\n')
                        for user, message in user_messages:
                            f.write(user)
                            f.write(':::')
                            f.write(message)
                            f.write('\n')

    else:
        print('{}: Looking for baseline.txt...'.format(dt.datetime.now()))
        time.sleep(5)


'''
def dt_modulus(t1, t2, modulus_range, offset):
    # returns the modulus difference between t1 and t2
    # for example, t1 = 21:09:00 and t2 = 21:09:25,
    # modulus difference is 21:09:25 = 21:09:15 = 21:09:05 ==> 5 second diff
    while t2 - t1 + dt.timedelta(seconds = offset) > dt.timedelta(seconds = modulus_range):
        t1 += dt.timedelta(seconds = modulus_range)
    return t2 - t1

import time
time1 = dt.datetime.now()
for i in range(30):
    time2 = dt.datetime.now()
    print(dt_modulus(time1, time2, 10))
    time.sleep(1)
'''


##
