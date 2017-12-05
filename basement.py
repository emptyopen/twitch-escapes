# -*- coding: utf-8 -*-
"""
Created on Mon Dec 04 10:53:22 2017

@author: wc803e
"""


import random
import string
import datetime

from PIL import Image

import chat_connect



# states are:
# n-wall (has chest)
# e-wall (has painting)
# w-wall (has door)
# s-wall (has bed)
# chest
# door
# bed
# painting
# keypad


class Basement(object):

    def __init__(self):

        self.walls = {'n-wall':[], 'e-wall':[], 's-wall':[], 'w-wall':[]}
        self.spawning_components = ['cipher-chest', 'cipher-painting', 'bed', 'door']


    def string_components(self): # strings components together in a path to exit

        pass


    def place_components(self): # puts components on wall (for drawing)

        for component in self.spawning_components:
            random_wall = random.choice(['n-wall', 'e-wall', 's-wall', 'w-wall'])
            self.walls[random_wall].append(component)
        print(self.walls)


    def update_image(self):

        pass


    def get_twitch_chat(self): # returns ten seconds of twitch chat

        s = chat_connect.openSocket()
        chat_connect.joinRoom(s)
        readbuffer = ""

        timer_start = datetime.datetime.now()
        thing = 0

        while datetime.datetime.now() - timer_start < datetime.timedelta(0,10,0):
            readbuffer = readbuffer + s.recv(1024)
            temp = string.split(readbuffer, '\n')
            readbuffer = temp.pop()
            for line in temp:
                print(line)
                if 'PING' in line:
                    s.send(line.replace('PING', 'PONG'))
                    break
                user = chat_connect.getUser(line)
                message = chat_connect.getMessage(line)
                print(user + 'typed:' + message)

                if 'thinga' in line:
                    thing += 1

        return thing


    def parse_twitch_chat(self, possible_actions):

        chat = self.get_twitch_chat()

        if len(chat) > 0:
            votes = {action:0 for action in possible_actions}

            for line in chat:
                if line in possible_actions:
                    votes[line] += 1

            mv = max(votes.values())
            rc = random.choice([k for (k, v) in votes.items() if v == mv])

            print(votes, rc)

        else:
            rc = 'stay'

        return rc


    def basic_cipher(self):
        self.quote_text = 'an investment in knowledge pays the best interest.' #benjamin franklin
        self.cipher_number = random.randint(1, 24)
        self.cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.quote_text])
        print(self.cipher_number, self.cipher_text)


    def play_game(self):

        # initial setting
        win = False
        state = 's-wall'
        inventory = []
        right_code = '423'

        self.generate_components()

        #self.walls = {'n-wall':['chest'], 'e-wall':['painting'], 's-wall':['bed'], 'w-wall':['door']}

        # basement
        while win == False:

            if state == 'n-wall':
                #image = Image.open('n-wall.jpg')
                #image.show()
                print('The North wall. There\'s {}.'.format(self.walls['n-wall']))
            elif state == 'e-wall':
                print('The East wall. There\'s {}.'.format(self.walls['e-wall']))
            elif state == 's-wall':
                print('The South wall. There\'s {}.'.format(self.walls['s-wall']))
            elif state == 'w-wall':
                print('The West wall. There\'s {}.'.format(self.walls['w-wall']))
            elif state == 'bed':
                print('A bed.')
            elif state == 'door':
                print('A door. There\'s a keypad.')
            elif state == 'painting':
                print('A painting.')
            elif state == 'chest':
                print('A chest.')
            elif state == 'keypad':
                print('A keypad.')


            always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall']

            if state == 'n-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['n-wall']]
            elif state == 'e-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['e-wall']]
            elif state == 's-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['s-wall']]
            elif state == 'w-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['w-wall']]

            elif state == 'bed':
                possible_actions = ['back']
            elif state == 'door':
                possible_actions = ['keypad', 'back']
            elif state == 'painting':
                possible_actions = ['back']
            elif state == 'chest':
                possible_actions = ['back']
            elif state == 'keypad':
                possible_actions = [right_code, 'back']

            print('Possible actions: {}\n'.format(possible_actions))

            action = self.parse_twitch_chat(possible_actions)
            #action = raw_input('next action? ')


            if action in possible_actions:
                if state == 'n-wall':
                    if action == 'left':
                        state = 'w-wall'
                    elif action == 'right':
                        state = 'e-wall'
                elif state == 'e-wall':
                    if action == 'left':
                        state = 'n-wall'
                    elif action == 'right':
                        state = 's-wall'
                elif state == 's-wall':
                    if action == 'left':
                        state = 'e-wall'
                    elif action == 'right':
                        state = 'w-wall'
                elif state == 'w-wall':
                    if action == 'left':
                        state = 's-wall'
                    elif action == 'right':
                        state = 'n-wall'
                elif state == 'bed':
                    if action == 'back':
                        state = [x for x in self.walls if 'bed' in self.walls[x]][0]
                elif state == 'door':
                    if action == 'keypad':
                        state = 'keypad'
                    elif action == 'back':
                        state = [x for x in self.walls if 'door' in self.walls[x]][0]
                elif state == 'painting':
                    if action == 'back':
                        state = [x for x in self.walls if 'painting' in self.walls[x]][0]
                elif state == 'chest':
                    if action == 'back':
                        state = [x for x in self.walls if 'chest' in self.walls[x]][0]
                elif state == 'keypad':
                    if action == 'back':
                        state = 'door'
                    elif action == right_code:
                        state == 'outside'
                        win = True

                for component in self.spawning_components:          # moving from wall to component
                    if action == component and [x for x in self.walls if component in self.walls[x]][0] == state:
                        state = component


                print('moved to: {}'.format(state))





        print('\nYou\'re free yay!')




B = Basement()
#B.play_game()
#B.basic_cipher()

print(B.get_twitch_chat())
#B.parse_twitch_chat(['left','right','bed'])


##
