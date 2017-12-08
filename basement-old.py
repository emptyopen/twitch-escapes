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

class Component(object):

    def __init__(self, text, actions):
        self.text = text  # to be changed into images?
        self.actions = actions  # actions and consequences

class Basement(object):

    def __init__(self):

        self.walls = {'n-wall':[], 'e-wall':[], 's-wall':[], 'w-wall':[]}
        self.win = False
        self.right_code = '423'
        self.spawning_components = ['cipher-chest', 'cipher-painting', 'bed', 'door']

        # twitch IRC
        self.s = chat_connect.openSocket()
        chat_connect.joinRoom(self.s)
        self.readbuffer = ""


    def string_components(self): # strings components together in a path to exit

        pass


    def place_components(self): # puts components on wall (for drawing)

        for component in self.spawning_components:
            random_wall = random.choice(['n-wall', 'e-wall', 's-wall', 'w-wall'])
            self.walls[random_wall].append(component)
        print(self.walls)


    def finalize_components(self): # needs to be run after place_components

        self.components = { 'cipher-chest': Component( 'A chest.', {'back': [x for x in self.walls if 'cipher-chest' in self.walls[x]][0]}),
                        'cipher-painting': Component('A painting.', {'back': [x for x in self.walls if 'cipher-painting' in self.walls[x]][0]}),
                        'door': Component('A door. There\'s a keypad.', {'back': [x for x in self.walls if 'door' in self.walls[x]][0], 'keypad':'keypad'}),
                        'bed': Component('A bed.', {'back': [x for x in self.walls if 'bed' in self.walls[x]][0]}),
                        'keypad': Component('A keypad.', {'back': 'door', self.right_code: 'outside'})
                      }


    def update_image(self):

        pass


    def get_twitch_chat(self): # returns ten seconds of twitch chat

        timer_start = datetime.datetime.now()
        thing = 0

        messages = []

        while datetime.datetime.now() - timer_start < datetime.timedelta(0, 30, 0):
            self.readbuffer = self.readbuffer + self.s.recv(1024)
            temp = string.split(self.readbuffer, '\n')
            self.readbuffer = temp.pop()
            for line in temp:
                #print(line)
                if 'PING' in line:
                    self.s.send(line.replace('PING', 'PONG'))
                    break
                user = chat_connect.getUser(line)
                message = chat_connect.getMessage(line)
                print(user + ' typed:' + message)

                messages.append(message)

        return messages


    def parse_twitch_chat(self, possible_actions):

        chat = [x[:-1] for x in self.get_twitch_chat()]
        print(chat)

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
        state = 's-wall'
        inventory = []

        self.place_components()
        self.finalize_components()

        #self.walls = {'n-wall':['chest'], 'e-wall':['painting'], 's-wall':['bed'], 'w-wall':['door']}

        # basement
        while self.win == False:

            ### Update graphics / text

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

            for component in self.components:
                if state == component:
                    print(self.components[component].text)

            ### Determine possible actions

            always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall']

            possible_actions = []

            if state == 'n-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['n-wall']]
            elif state == 'e-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['e-wall']]
            elif state == 's-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['s-wall']]
            elif state == 'w-wall':
                possible_actions = ['left', 'right'] + [x for x in self.walls['w-wall']]

            for component in self.components:
                if state == component:
                    possible_actions = self.components[component].actions.keys()

            print('Possible actions: {}\n'.format(possible_actions))


            ### Decide action

            #action = self.parse_twitch_chat(possible_actions)
            action = raw_input('next action? ') # for working offline


            ### Update state based on action

            if 'wall' in state: # from wall
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
                else:
                    for component in self.spawning_components:          # moving from wall to component
                        if action == component and [x for x in self.walls if component in self.walls[x]][0] == state:
                            state = component

            else: # from component
                for component in self.components:
                    if state == component:
                        state = self.components[component].actions[action]


            print('moved to: {}'.format(state))
            if state == 'outside':
                self.win = True



        print('\nYou\'re free yay!')





B = Basement()
B.play_game()

#B.basic_cipher()

#print(B.get_twitch_chat())
#B.parse_twitch_chat(['left','right','bed'])


##
