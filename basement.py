#
# written by Matt Takao
# started 2017-12-01
# last major update 2017-12-15
#

import random
import string
import datetime as dt
import sys
import time
import os
import numpy as np
import pygame
from pygame.locals import QUIT
import textwrap

from config import *

pygame.font.init()
#print(sorted(pygame.font.get_fonts()))

BASETIME = dt.datetime.now()

# conda install -c anaconda libpng # for interlace issue
# need 32 bit png
# https://pixlr.com/editor/

# for new puzzles:
#   add to self.components
#   add setup
#   add state update
#   add display update

# to do:
#
# new puzzles:
#  numbers on the wall for a code?
#  ice puzzles
#  spinning wheels ??
#
# highlight glow of new component:
#   add removal upon sight as well
#
# fix up multiple screens. known issues:
#   implement twitch timing for multiple screens
#   help function has issues
#   player control (via chat command)
#   highlight active screen
#
# add 'graphical delay' (ignore everything except update in if statement)
#
# trophies
#
# graphical inventory
#
# journal (log of in game events) (create screen for it)
#
# MULTIPLE TRACKS (CHAINS), each ending in a clue for a digit of the keypad
#
#

class Component(object):

    def __init__(self, description, image_placement, actions_to_state = {}, actions_to_inventory = {}, endpoints = [[], []]):
        self.description = description
        self.image_placement = image_placement  # 3-tuple: horizontal and vertical offset, and then depth (n/a:0, on wall:1, in front:2)
        self.actions_to_state = actions_to_state  # actions and consequences
        self.actions_to_inventory = actions_to_inventory
        self.endpoints = endpoints

        self.powered = True
        self.visible = True
        self.on_wall = ''

class Game:

# ----------------------------------------------------------------------------------------------------------------------------------- PREP

    def __init__(self):

        # window
        self.caption = "Twitch Escapes"
        self.fps = 60
        self.clock = pygame.time.Clock()
        if DEBUG:
            self.screen = pygame.display.set_mode((890, 717))
        else:
            self.screen = pygame.display.set_mode((1800, 717))  # (890, 503) , 214 vert for black, 20 margin
        self.background = pygame.image.load('pics/n-wall.png')
        self.one_off = True # toggler that ensures screen updates after state update?
        self.p_offset = [0, 0] # offset for multiple screens

        # game state
        self.s = 0 # player state to display or update
        if DEBUG:
            self.num_players = [1]
            self.state = ['n-wall']
            self.action = ['stay']
        else:
            self.num_players = [1, 2] # extremely powerful
            self.state = ['n-wall', 's-wall'] # THESE 3 NEED TO BE THE SAME SIZE
            self.action = ['stay', 'stay']
        #self.timer_start = [dt.datetime.now(), dt.datetime.now() - dt.timedelta(DECISIONTIME / 2)]
        self.timer_start = [dt.datetime.now(), dt.datetime.now() - dt.timedelta(seconds = 5)]
        self.win = False
        self.help = False
        self.center_message = ['', (0,0), dt.datetime.now(), dt.timedelta(0,0,0)]
        self.votes = {s:{} for s in self.num_players}
        self.inventory = []
        self.journal = ['Welcome to the Basement!']
        self.new_component_glow = [None, dt.datetime.now() + dt.timedelta(seconds = 0)]

        # game initialization reqs
        self.player_groups = {1:[], 2:[]} # which users are dedicated to which players
        self.components_order = []
        self.bridges = []
        self.walls = {'n-wall':[['', ''], ['', '', '']], 'e-wall':[['', ''], ['', '', '']], 's-wall':[['', ''], ['', '', '']], 'w-wall':[['', ''], ['', '', '']]}
        self.keypad_code = str(random.randint(100, 999))
        print('end:', self.keypad_code)


    def map_components(self): # strings components together in a path to exit

        # define all components: description, image_placement (n/a:0, on wall:1, in front:2), actions_to_state, actions_to_inventory, endpoints
            self.components = { 'n-wall': Component('North wall', [0, 0, 0], {'left':'w-wall', 'right':'e-wall'}, {}, [[], []]),
                                'e-wall': Component('East wall', [0, 0, 0], {'left':'n-wall', 'right':'s-wall'}, {}, [[], []]),
                                's-wall': Component('South wall', [0, 0, 0], {'left':'e-wall', 'right':'w-wall'}, {}, [[], []]),
                                'w-wall': Component('West wall', [0, 0, 0], {'left':'s-wall', 'right':'n-wall'}, {}, [[], []]),
                                'trophycase': Component('A trophy case', [0, 0, 1], {}, {}, [['knowledge'], ['inventory']]),
                                'door': Component('The exit door', [0, -33, 1], {'keypad':'keypad'}, {}, [[], []]),
                                'keypad': Component('A keypad', [0, 0, 0], {'back': 'door', self.keypad_code: 'outside'}, {}, [['inventory', 'knowledge-keypadcode'], []]),
                                'cpainting': Component('A cipher painting', [0, 0, 1], {}, {}, [['uncover', 'start'], ['cipherlink']]),
                                'cchest': Component('A cipher chest', [0, -45, 2], {}, {}, [['cipherlink'], ['inventory']]),
                                'bed': Component('A bed', [0, -20, 2], {}, {}, [[], []]),
                                'simonsays': Component('A simon says game', [0, -30, 2], {}, {}, [['start', 'power'], ['uncover', 'power', 'knowledge-keypadcode']]),
                                'amidakuji': Component('Amidakuji', [0, 0, 1], {}, {}, [['start', 'uncover'], ['knowledge-5colororder']]),
                                'family': Component('The family game', [0, 0, 1], {}, {}, [['knowledge-5colororder'], ['uncover', 'power']]),
                                'secretsafe': Component('A desk', [0, 0, 1], {}, {}, [['uncover'], ['inventory']]),
                                'keychest': Component('A chest with a keyhole', [0, 0, 2], {}, {}, [['inventory'], ['inventory']]),
                                'comchest': Component('A chest with a combination', [0, 0, 2], {}, {}, [['knowledge'], ['inventory']]),
                                'hangman': Component('A game of hangman', [0, 0, 1], {}, {}, [['start', 'uncover', 'power'], ['uncover', 'power']]),
                                'blockpush': Component('A game of push the block', [0, 0, 1], {}, {}, [['start', 'inventory', 'uncover', 'power'], ['uncover', 'power', 'knowledge-keypadcode']]),
                                'riddler': Component('A riddle game', [0, 0, 2], {}, {}, [['start', 'power'], ['uncover', 'power', 'knowledge-keypadcode']])
                                }

            self.generate_puzzle_chain()

    def generate_puzzle_chain(self):
        do_not_generate = ['n-wall', 'e-wall', 's-wall', 'w-wall', 'trophycase', 'door', 'bed', 'keypad']
        generate_components = [x for x in self.components if x not in do_not_generate]

        # determine starting puzzle
        while True:
            component = random.choice(generate_components)
            if 'start' in self.components[component].endpoints[0]:
                generate_components.remove(component)
                self.components_order.append(component)
                break

        # continue adding puzzles until the end
        cnt = 0
        while True:
            component = random.choice(generate_components)
            if len(self.components_order) > 4: # wrap it up
                if any([x in self.components[component].endpoints[0] for x in self.components[self.components_order[-1]].endpoints[1]]) and \
                        any([x in self.components['keypad'].endpoints[0] for x in self.components[component].endpoints[1]]):
                    self.components_order.append(component)
                    self.components_order.append('keypad')
                    break
            if any([x in self.components[component].endpoints[0] for x in self.components[self.components_order[-1]].endpoints[1]]):
                generate_components.remove(component)
                self.components_order.append(component)
            cnt += 1
            if cnt > 1000:
                print('breaking with excess')
                break

        # determine bridge between endpoints
        for i in range(len(self.components_order) - 1):
            current_end = self.components[self.components_order[i]].endpoints[1]
            next_begin = self.components[self.components_order[i+1]].endpoints[0]
            self.bridges.append(random.choice([x for x in current_end if x in next_begin]))

        # manual order and placement
        self.components_order = ['riddler', 'hangman', 'blockpush', 'amidakuji', 'family', 'cpainting', 'cchest', 'keypad']
        self.bridges = ['power', 'uncover', 'uncover', 'knowledge-5colororder', 'uncover', 'cipherlink', 'inventory']

        print(self.components_order, self.bridges)

        for i, c in enumerate(self.components_order):
            if c == 'cchest':
                self.setup_cipher()
            if c == 'simon-says':
                self.setup_simon_says()
            if c == 'amidakuji':
                self.setup_amidakuji()
            if c == 'family':
                self.setup_family()
            if c == 'blockpush':
                self.setup_blockpush()
            if c == 'hangman':
                self.setup_hangman()
            if c == 'riddler':
                self.setup_riddler()
            if i > 0:
                if self.bridges[i-1] == 'uncover':
                    self.components[c].visible = False
                if self.bridges[i-1] == 'power':
                    self.components[c].powered = False

    def place_components(self): # puts components on wall (for drawing)

        do_not_place = ['keypad']
        self.components_to_place = ['door', 'bed']
        self.components_to_place += [c for c in self.components_order if c not in do_not_place]

        cnt = 0
        for component in self.components_to_place:
            not_done_placing_component = True
            while not_done_placing_component:
                random_wall = random.choice(['n-wall', 'e-wall', 's-wall', 'w-wall'])
                if self.components[component].image_placement[2] == 1: # if component is to be placed on wall
                    available_spots = [spot for spot in [0,1] if self.walls[random_wall][0][spot] == '']
                    if available_spots:
                        self.walls[random_wall][0][random.choice(available_spots)] = component
                        self.components[random_wall].actions_to_state[component] = component
                        self.components[component].on_wall = random_wall
                        not_done_placing_component = False
                elif self.components[component].image_placement[2] == 2: # if component is to be placed in front of wall
                    available_spots = [spot for spot in [0,1,2] if self.walls[random_wall][1][spot] == '']
                    if available_spots:
                        self.walls[random_wall][1][random.choice(available_spots)] = component
                        self.components[random_wall].actions_to_state[component] = component
                        self.components[component].on_wall = random_wall
                        not_done_placing_component = False
                cnt += 1
                if cnt > 50: # in case of unexpected endless loop
                    print('------------something unexpected: breaking!!')
                    break

        for component in self.components: # add the back option for components
            if self.components[component].on_wall != '':
                self.components[component].actions_to_state['back'] = self.components[component].on_wall

        print(self.walls)


    def setup_cipher(self):

        self.cipher_number = random.randint(1, 24)
        self.chest_text = random.choice(['ghost', 'booms', 'tally', 'rando', 'night', 'sleep', 'santa', 'could', 'alone', 'happy'])
        self.chest_cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.chest_text])

        #self.painting_text = 'an investment in knowledge pays the best interest.' #benjamin franklin
        self.painting_text = '\"' + random.choice(['don\'t cry because it\'s over, smile because it happened.-Dr. Seuss', 'whatever you do, do it well.-Walt Disney',
                            'what we think, we become.-Buddha', 'be so good they can\'t ignore you.-Steve Martin',
                            'it hurts because it mattered.-John Green']) + '\"'
        self.painting_cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.painting_text])

        self.components['cchest'].actions_to_inventory[self.chest_cipher_text] = self.keypad_code

        print('CIPHER: ',self.cipher_number, self.chest_cipher_text)


    def setup_simon_says(self):

        self.simon_says_pattern = [random.choice(['blue','red','green','yellow']) for _ in range(5)]
        print(self.simon_says_pattern)
        self.simon_says_current_pattern = []
        self.simon_says_user_guess = []


    def setup_amidakuji(self):

        self.amidakuji_difficulty = 'easy'

        if self.amidakuji_difficulty == 'easy':
            self.amidakuji_choice = random.choice([1,2]) # selects painting 1 or 2
            numbers = [1, 2, 3, 4, 5, 6]
            self.amidakuji_numbers_order = random.sample(numbers, 6)
            if self.amidakuji_choice == 1:
                self.amidakuji_map = {1:1, 2:4, 3:3, 4:5, 5:6, 6:2}
            elif self.amidakuji_choice == 2:
                self.amidakuji_map = {1:4, 2:2, 3:1, 4:3, 5:5, 6:6}
            colors = ['yellow', 'red', 'orange', 'purple', 'pink', 'blue', 'green']
            self.amidakuji_colors_order = random.sample(colors, 6)
            self.amidakuji_map = {self.amidakuji_numbers_order[n-1]: self.amidakuji_colors_order[self.amidakuji_map[n] - 1] for n in range(1, 7)} # number to color by way of amidakuji


    def setup_family(self):

        family_members = ['daddy', 'mommy', 'lil-joe', 'janice', 'carter-iii', 'skip', 'bob-the-fish']
        self.family_members_order = random.sample(family_members, 6)
        self.family_members_color_order = {n:self.amidakuji_colors_order[i] for i, n in enumerate(self.family_members_order)}
        self.family_members_color_order_inv = {v: k for k, v in self.family_members_color_order.iteritems()}

        self.correct_family_order = [self.family_members_color_order_inv[self.amidakuji_map[x]] for x in self.amidakuji_map]
        self.correct_family_order = [' '.join(self.correct_family_order)] + [''.join([x[0] for x in self.correct_family_order])] + [' '.join([x[0] for x in self.correct_family_order])]

        print('correct family order', self.correct_family_order)


    def setup_blockpush(self):
        self.blockpush_grid = np.array([[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]])
        x1 = [random.randint(0,3), random.randint(0,3)]
        self.blockpush_grid[x1[0], x1[1]] = 1
        while True:
            x2 = [random.randint(0,3), random.randint(0,3)]
            if x2 != x1:
                self.blockpush_grid[x2[0], x2[1]] = 1
                break
        while True:
            x3 = [random.randint(0,3), random.randint(0,3)]
            if x3 != x1 and x3 != x2:
                self.blockpush_grid[x3[0], x3[1]] = 1
                break
        while True:
            start = [random.randint(0,3), random.randint(0,3)]
            safe = False
            if start != x1 and start != x2:
                if start[0] != 0:
                    if self.blockpush_grid[start[0] - 1][start[1]] == 0:
                        safe = True
                if start[0] != 3:
                    if self.blockpush_grid[start[0] + 1][start[1]] == 0:
                        safe = True
                if start[1] != 0:
                    if self.blockpush_grid[start[0]][start[1] - 1] == 0:
                        safe = True
                if start[1] != 3:
                    if self.blockpush_grid[start[0]][start[1] + 1] == 0:
                        safe = True
                if safe:
                    self.blockpush_grid[start[0], start[1]] = 2
                    break
        while True:
            end = [random.randint(0,3), random.randint(0,3)]
            safe = False
            if end != x1 and end != x2 and end != start:
                if end[0] != 0:
                    if self.blockpush_grid[end[0] - 1][end[1]] == 0:
                        safe = True
                if end[0] != 3:
                    if self.blockpush_grid[end[0] + 1][end[1]] == 0:
                        safe = True
                if end[1] != 0:
                    if self.blockpush_grid[end[0]][end[1] - 1] == 0:
                        safe = True
                if end[1] != 3:
                    if self.blockpush_grid[end[0]][end[1] + 1] == 0:
                        safe = True
                if safe:
                    self.blockpush_grid[end[0], end[1]] = 3
                    break

        self.blockpush_block = start
        self.blockpush_start = start
        self.blockpush_end = end

        print(self.blockpush_grid, self.blockpush_block)


    def setup_hangman(self):
        possible_qs = ['testing testing', 'the dog and the cat', 'geronimous']
        self.hangman_phrase = random.choice(possible_qs)
        self.hangman_guess = ['_' if c.isalpha() else ' ' for c in self.hangman_phrase]
        print(self.hangman_phrase, self.hangman_guess)
        self.hangmanstate = 0


    def setup_riddler(self):
        possible_riddles = [['I\'m tall when I\'m young and I\'m short when I die. What am I?', 'candle'],
                            ['A pants pocket is empty, but it still has something in it. What?', 'hole'],
                            ['Throw away the outside and cook the inside, then eat the outside and throw away the inside. What am I?', 'corn'],
                            ['What word becomes shorter when you add to letters to it?', 'short'],
                            ['What occurs once in a minute, twice in a moment, but never in ten thousand years?', 'm'],
                            ['What five letter word sounds the same if you take away the 1st, 3rd, and 5th letter?', 'empty'],
                            ['What is at the end of a rainbow?', 'w'],
                            ['What is so delicate that saying it\'s name breaks it?', 'silence'],
                            ['What is the center of gravity?', 'v'],
                            ['What is the next letter in the sequence JFMAMJJASON_?', 'd'],
                            ['When you need me, you throw me away. When you\'re done using me, you bring me back. What am I?', 'anchor'],
                            ['What is yours but is used almost exclusively by everyone else?', 'name'],
                            ['I\'m lighter than a feather, but the strongest man in the world cannot hold me for more than an hour. What am I?', 'breath']]
        riddle = random.choice(possible_riddles)
        self.riddler_riddle = riddle[0]
        self.riddler_answer = riddle[1]
        print(self.riddler_riddle, self.riddler_answer)


# -------------------------------------------------------------------------------------------------------------------- EXECUTE

    def main(self):

        # setup
        pygame.init()
        pygame.display.set_caption(self.caption)
        self.map_components()
        self.place_components()
        if not DEBUG:
            self.create_vote_timing_commands()

        while True: # main game loop

            self.update_state()

            # update state of game continuously
            for event in pygame.event.get():

                if event.type == QUIT:
                    pygame.quit()
                    sys.exit

            self.update_display()


    def update_state(self):

        if self.one_off:

            s = self.s

            if not DEBUG:
                if dt.datetime.now() - self.timer_start[s] > dt.timedelta(0, DECISIONTIME, 0):
                    self.timer_start[s] = dt.datetime.now()

            always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall', 'help']

            possible_actions = ['stay']

            for component in self.components:
                if self.state[s] == component:

                    possible_actions += self.components[component].actions_to_state.keys()   \
                                    + self.components[component].actions_to_inventory.keys()

            possible_actions += always_actions

            for action in possible_actions:
                if action in self.components:
                    if not self.components[action].visible:
                        possible_actions.remove(action) # remove action if it is invisible

            #print('Possible actions: {}\n'.format(possible_actions))


            ### Decide action
            if DEBUG:
                self.action[s] = raw_input('next action for screen {}: '.format(s+1)).lower()
            else:
                self.parse_twitch_chat_file()

            # Turn help on or off
            if self.action[s] == 'help on' or (self.action[s] == 'help' and self.help == False):
                self.help = True
            elif self.action[s] == 'help off' or (self.action[s] == 'help' and self.help == True):
                self.help = False

            ### Update state based on action
            for component in self.components:
                if self.state[s] == component:

                    if self.action[s] in self.components[component].actions_to_state and self.action[s] in possible_actions: # change of state (moving the entire screen)
                        self.state[s] = self.components[component].actions_to_state[self.action[s]]
                        print('moved to: {}'.format(self.state[s]))
                        break

                    elif not self.components[component].powered: # check if component is powered
                        if 'not powered' not in self.journal[-1]:
                            self.jot('{} is not powered.'.format(component))
                        break

                    elif self.action[s] in self.components[component].actions_to_inventory: # change of inventory (adding something to inventory)
                        if self.components[component].actions_to_inventory[self.action[s]] not in self.inventory: # add only if you don't already have it
                            self.inventory.append(self.components[component].actions_to_inventory[self.action[s]])
                            self.jot('You got something in your inventory.')
                            break

                    elif self.state[s] == 'family' and self.action[s] in self.correct_family_order:
                        self.activate_next_puzzle('family')
                        break

                    elif self.state[s] == 'blockpush':
                        if self.action[s] in ['up', 'u'] and self.blockpush_block[0] > 0:
                            self.blockpush_block[0] -= 1
                        if self.action[s] in ['down', 'd'] and self.blockpush_block[0] < 3:
                            self.blockpush_block[0] += 1
                        if self.action[s] in ['right', 'r'] and self.blockpush_block[1] < 3:
                            self.blockpush_block[1] += 1
                        if self.action[s] in ['left', 'l'] and self.blockpush_block[1] > 0:
                            self.blockpush_block[1] -= 1
                        if self.blockpush_block == self.blockpush_end:
                            self.activate_next_puzzle('blockpush')
                        if self.blockpush_grid[self.blockpush_block[0], self.blockpush_block[1]] == 1:
                            self.setup_blockpush()
                        break

                    elif self.state[s] == 'hangman':
                        if self.action[s].isalpha() and len(self.action[s]) == 1:
                            next_guess = [self.action[s] if self.hangman_phrase[i] == self.action[s] else c for i, c in enumerate(self.hangman_guess)]
                            if self.action[s] in self.hangman_guess:
                                self.jot('You already guessed {}.'.format(self.action[s]))
                            elif next_guess == self.hangman_guess:
                                self.jot('{} is not in the phrase.'.format(self.action[s]))
                                self.hangmanstate += 1
                            else:
                                self.jot('{} is in the phrase!'.format(self.action[s]))
                                self.hangman_guess = next_guess
                            if all([x != '_' for x in self.hangman_guess]):
                                self.activate_next_puzzle('hangman')
                            if self.hangmanstate > 8:
                                self.setup_hangman()
                                self.jot('Hangman is resetting!')
                        break

                    elif self.state[s] == 'riddler':
                        if self.action[s] == self.riddler_answer:
                            self.activate_next_puzzle('riddler')
                        break

                    else:
                        pass

            if self.state[s] == 'outside':
                self.jot('{}: You are free!')
                self.win = True

            self.s += 1
            if self.s >= len(self.state):
                self.s = 0

        if self.one_off:
            self.one_off = False
        else:
            self.one_off = True


    def activate_next_puzzle(self, component):

        next_component = self.components_order[self.components_order.index(component) + 1]
        self.new_component_glow = [next_component, dt.datetime.now() + dt.timedelta(seconds = 20)]

        print('activating', component, self.bridges, self.components_order.index(component) + 1, self.components_order[self.components_order.index(component) + 1])

        if self.bridges[self.components_order.index(component)] == 'uncover':
            self.components[self.components_order[self.components_order.index(component) + 1]].visible = True
            self.jot('You hear the sound of {} appearing magically out of thin air.'.format(next_component))
        if self.bridges[self.components_order.index(component)] == 'power':
            self.components[self.components_order[self.components_order.index(component) + 1]].powered = True
            self.jot('You hear the sound of {} powering ON.'.format(next_component))


    def jot(self, message):
        if not self.journal[-1].endswith(message):
            self.journal.append('{}: {}'.format(dt.datetime.now(), message))


# --------------------------------------------------------------------------------------------------------- DRAW

    def update_display(self):

        try:

            for s in range(len(self.state)): # iterate over players

                self.screen.blit(self.background, (self.p_offset[0], self.p_offset[1]))

                # offset two screens
                self.p_offset = [0, 0]
                if s == 1:
                    self.p_offset = [910, 0]

                if 'wall' in self.state[s]:
                    self.background = pygame.image.load('pics/{}.png'.format(self.state[s]))
                    layers = self.walls[self.state[s]]
                    for i, layer in enumerate(layers): # starting in the back
                        # i is [0,1]
                        for j, spot in enumerate(layer):
                            # j is [0,1] or [0,1,2] depending on layer
                            # i controls vertical placement, j controls horizontal placement
                            if spot in self.components:
                                if self.components[spot].visible: # only draw if visible
                                    component = spot
                                    c_image = pygame.image.load('pics/{}.png'.format(component))
                                    c_image_offset = [c_image.get_width()/2, c_image.get_height()/2]
                                    if i == 0:
                                        vert_plac = 186
                                        if j == 0:
                                            horz_plac = 324
                                        elif j == 1:
                                            horz_plac = 556
                                    elif i == 1:
                                        vert_plac = 312
                                        horz_plac = 220 * (j+1)
                                    horz_plac += self.components[component].image_placement[0]
                                    vert_plac -= self.components[component].image_placement[1]
                                    if self.new_component_glow[0] == spot and self.new_component_glow[1] - dt.datetime.now() > dt.timedelta(seconds=0):
                                        self.background.blit(pygame.image.load('pics/glow.png'), (horz_plac, vert_plac))
                                    self.background.blit(c_image, (horz_plac, vert_plac))
                                    if self.help:
                                        self.draw_message(component, (horz_plac + self.p_offset[0], vert_plac + self.p_offset[1]), preset = 'help')


                elif self.state[s] == 'cchest':
                    self.background = pygame.image.load('pics/cchest-full.png')
                    for i, letter in enumerate(self.chest_text):
                        char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
                        self.background.blit(char, (240.5 + i * 88, 125))

                elif self.state[s] == 'cpainting':
                    self.background = pygame.image.load('pics/cpainting-full.png')
                    quote = ''.join(string.lower(self.painting_cipher_text).split('-')[:-1])
                    quote_by = ' - ' + string.lower(self.painting_text).split('-')[-1][:-1]
                    rows = textwrap.TextWrapper(width = 30).wrap(text = quote)
                    for i, row in enumerate(rows):
                        self.background.blit(pygame.font.SysFont(FONT, FONTSIZE + 20).render(row, True, (0,0,0), (255,255,255)), (190, 80 + 50 * i))
                    self.background.blit(pygame.font.SysFont(FONT, FONTSIZE + 15).render(quote_by, True, (0,0,0), (255,255,255)), (420, 400))

                elif self.state[s] == 'simon-says':
                    self.background = pygame.image.load('pics/simon-says-full.png')
                    self.screen.blit(self.background, (0,0))
                    for color in self.simon_says_pattern:
                        self.background = pygame.image.load('pics/simon-says-full-{}.png'.format(color))
                        self.screen.blit(self.background, (0,0))
                        time.sleep(0.8)
                        self.background = pygame.image.load('pics/simon-says-full.png')

                elif self.state[s] == 'amidakuji':
                    self.background = pygame.image.load('pics/amidakuji-full-{}.png'.format(self.amidakuji_choice))
                    for i, amidakuji_number in enumerate(self.amidakuji_numbers_order):
                        number = pygame.image.load('pics/number-{}-medium.png'.format(amidakuji_number))
                        self.background.blit(number, (112 + i * 127, 3))
                    for i, amidakuji_color in enumerate(self.amidakuji_colors_order):
                        color = pygame.image.load('pics/{}-medium.png'.format(amidakuji_color))
                        self.background.blit(color, (111 + i * 128, 430))

                elif self.state[s] == 'family':
                    self.background = pygame.image.load('pics/family-full.png')
                    self.draw_message('In order of being the best, enter the names of the family!', (140 + self.p_offset[0], 100 + self.p_offset[1]), preset = 'help')
                    self.draw_message('For example: "daddy mommy lil-joe janice carter-III bob-the-fish"', (140 + self.p_offset[0], 120 + self.p_offset[1]), preset = 'help')
                    self.draw_message('Or: "d m l j c b"', (140 + self.p_offset[0], 140 + self.p_offset[1]), preset = 'help')
                    for i, member in enumerate(self.family_members_order):
                        member_to_draw = pygame.image.load('pics/{}.png'.format(member))
                        self.background.blit(member_to_draw, (111 + i * 108, 230))
                        member_dict = {'daddy':[124, 298, 'dot'], 'mommy':[127, 231, 'bow'], 'lil-joe':[151, 310, 'dot'], 'janice':[124, 266, 'bow'],
                                        'carter-iii':[142, 345, 'collar'], 'skip':[108, 229, 'hat'], 'bob-the-fish':[141, 333, 'fish']}
                        article = pygame.image.load('pics/{}-{}.png'.format(member_dict[member][2], self.family_members_color_order[member]))
                        self.background.blit(article, (member_dict[member][0] + i * 108, member_dict[member][1]))
                        if self.help:
                            self.draw_message(member, (111 + i * 108 + self.p_offset[0], 190 + self.p_offset[1]), preset = 'help')

                elif self.state[s] == 'blockpush':
                    self.background = pygame.image.load('pics/blockpush-full.png')
                    block = pygame.image.load('pics/blockpush-block.png')
                    x = pygame.image.load('pics/blockpush-x.png')
                    start = pygame.image.load('pics/blockpush-start.png')
                    end = pygame.image.load('pics/blockpush-end.png')
                    for i in range(4):
                        for j in range(4):
                            if self.blockpush_grid[i, j] == 1:
                                self.background.blit(x, (205 + j*115, 25 + i*115))
                            if self.blockpush_grid[i, j] == 2:
                                self.background.blit(start, (205 + j*115, 25 + i*115))
                            if self.blockpush_grid[i, j] == 3:
                                self.background.blit(end, (205 + j*115, 25 + i*115))
                            if i == self.blockpush_block[0] and j == self.blockpush_block[1]:
                                self.background.blit(block, (205 + j*115, 25 + i*115))
                    if self.help:
                        self.draw_message('up, down, left, right', (200, 500), preset = 'help')

                elif self.state[s] == 'hangman':
                    self.background = pygame.image.load('pics/hangman-full.png')
                    if self.hangmanstate > 0:
                        self.background.blit(pygame.image.load('pics/hangman-head.png'), (340, 65))
                    if self.hangmanstate > 1:
                        self.background.blit(pygame.image.load('pics/hangman-body.png'), (340, 125))
                    if self.hangmanstate > 2:
                        self.background.blit(pygame.image.load('pics/hangman-right-leg.png'), (320, 195))
                    if self.hangmanstate > 3:
                        self.background.blit(pygame.image.load('pics/hangman-left-leg.png'), (370, 195))
                    if self.hangmanstate > 4:
                        self.background.blit(pygame.image.load('pics/hangman-right-arm.png'), (310, 95))
                    if self.hangmanstate > 5:
                        self.background.blit(pygame.image.load('pics/hangman-left-arm.png'), (360, 95))
                    if self.hangmanstate > 6:
                        self.background.blit(pygame.image.load('pics/hangman-eye.png'), (347, 75))
                    if self.hangmanstate > 7:
                        self.background.blit(pygame.image.load('pics/hangman-eye.png'), (352, 75))
                    if self.hangmanstate > 8:
                        self.background.blit(pygame.image.load('pics/hangman-frown.png'), (340, 75))
                    h_row = 0 # need to add row wrapping on words
                    for i, c in enumerate(self.hangman_guess):
                        if c.isalpha():
                            char = pygame.image.load('pics/letter-{}-medium.png'.format(c))
                            self.background.blit(char, (70 + i * 45, 400))
                        elif c == '_':
                            char = pygame.image.load('pics/underscore-medium.png')
                            self.background.blit(char, (70 + i * 45, 400))

                elif self.state[s] == 'riddler':
                    self.background = pygame.image.load('pics/riddler-full.png')
                    rows = textwrap.TextWrapper(width = 30).wrap(text = self.riddler_riddle)
                    for i, row in enumerate(rows):
                        self.background.blit(pygame.font.SysFont(FONT, FONTSIZE + 10).render(row, True, (0,0,0), (255,255,255)), (240, 100 + 50 * i))

                else:
                    self.background = pygame.image.load('pics/{}-full.png'.format(self.state[s]))


                # other help items
                if self.help and 'wall' in self.state[s]:
                    self.draw_message('Left', (60 + self.p_offset[0], 450 + self.p_offset[1]), preset = 'help')
                    self.draw_message('Right', (800 + self.p_offset[0], 450 + self.p_offset[1]), preset = 'help')

                # bottom
                self.blackbottom = pygame.image.load('pics/clean-bottom.png')
                self.screen.blit(self.blackbottom, (0, 503))
                if not DEBUG:
                    self.screen.blit(self.blackbottom, (890, 503))


            # draw timer and actions/votes
            for s in range(len(self.state)):

                # offset two screens
                self.p_offset = [0, 0]
                if s == 1:
                    self.p_offset = [910, 0]

                if not DEBUG:
                    if (dt.datetime.now() - self.timer_start[s]).seconds < DECISIONTIME - 7:
                        self.draw_message('Vote! {}s'.format(DECISIONTIME - 7 - (dt.datetime.now() - self.timer_start[s]).seconds), (20 + self.p_offset[0], 20 + self.p_offset[1]), text_color = (0,0,0))
                    else:
                        self.draw_message('Wait! {}s'.format(DECISIONTIME - (dt.datetime.now() - self.timer_start[s]).seconds), (20 + self.p_offset[0], 20 + self.p_offset[1]), text_color = (0,0,0))
                    self.draw_message('Last votes were: {}'.format(self.visible_votes), (50, 580))

            # draw journal (last entry)
            rows = textwrap.TextWrapper(width = 60).wrap(text = ''.join(self.journal[-1].split(':')[3:])) # remove timestamp and wrap
            self.draw_message('Last journal entry:', (30, 520), preset = 'bottom')
            for i, row in enumerate(rows):
                self.draw_message(row, (250, 520 + 30 * i), preset = 'bottom')

            # draw inventory
            self.draw_message('Inventory: {}'.format(self.inventory), (30, 600), preset = 'bottom')

            pygame.display.update()
            self.clock.tick(self.fps)

        except BufferError:
        #except Exception:
            pass

    # blacksword.tff

    def draw_message(self, message, coord = (100, 100), preset = None, font = FONT, font_size = FONTSIZE, text_color = (160, 190, 255), background_color = None):
        if preset == 'help':
            background_color = (0, 0, 0)
            text_color = (255, 255, 255)
        if preset == 'bottom':
            background_color = None
        self.screen.blit(pygame.font.SysFont(font, font_size).render(message, True, text_color, background_color), coord)


# ------------------------------------------------------------------------------------------------------------------- TWITCH

    def create_vote_timing_commands(self):
        f = open('VTC.txt', 'w')
        for i, s in enumerate(self.num_players):
            pass

    def parse_twitch_chat_file(self):

        for s, f in enumerate(['s1_messages.txt', 's2_messages.txt']):

            if os.path.isfile(f):

                with open(f) as fn:
                    contents = fn.read().split('\n')
                os.remove(f)

                ready_time = contents[0] # need to format datetime to read

                # don't do anything until the timestamp expires
                if dt.datetime.now() - ready_time > dt.timedelta(seconds=0):

                    # reset votes for this screen
                    self.votes[s] = []

                    # partition content into messages and users, might want to use users later
                    for content in contents[1:]: # user:message, user2:message2, etc.
                        users = [x.split[':'][0] for x in content]
                        messages = [''.join(x.split[':'][1:]) for x in content]

                    # do votes
                    for i, message_group in enumerate(messages_by_screen):
                        for message in message_group:
                            if message == '':
                                pass
                            elif message not in self.votes[s]:
                                self.votes[s][message] = 1
                            else:
                                self.votes[s][message] += 1

                    # default action is to stay if there are no votes
                    if all([self.votes[s][v] == 0 for v in self.votes]):
                        self.votes['stay'] += 1

                    # choose max vote per screen
                    mv = max(self.votes[s].values())
                    self.action = random.choice([k for (k, v) in self.votes[s].items() if v == mv])

            else: # if file isn't there, don't do anything
                self.action = 'stay'




def main():
    game = Game()
    game.main()

if __name__ == "__main__":
    main()
