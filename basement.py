#
# written by Matt Takao
# started 2017-12-01
# last major update 2018-02-19
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

os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (20,20)

pygame.font.init()
#print(sorted(pygame.font.get_fonts()))

BASETIME = dt.datetime.now()

# conda install -c anaconda libpng # for interlace issue
# need 32 bit png
# https://pixlr.com/editor/
#
# resize
# http://resizeimage.net/


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
        self.screen = pygame.display.set_mode((1780, 1020))  # (850, 400)
        self.background = pygame.image.load('pics/walls/n-wall.png')
        self.one_off = True # toggler that ensures screen updates after state update?
        self.p_offset = [30, 10] # offset for multiple screens

        # game state
        self.s = 0 # player state to display or update
        self.state = ['n-wall', 'e-wall', 's-wall', 'w-wall']
        self.action = ['stay', 'stay', 'stay', 'stay']
        self.win = False
        self.help = False
        self.votes = {s:{} for s in self.state}
        self.ready_time = [dt.datetime.now() for s in self.state]
        self.inventory = []
        self.journal = ['0:0:0: Welcome to the Basement!']
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
                            'journal': Component('The journal', [0, 0, 0], {}, {}, [[], []]),
                            'trophycase': Component('A trophy case', [0, 0, 1], {}, {}, [['knowledge'], ['inventory']]),
                            'door': Component('The exit door', [0, -33, 1], {'keypad':'keypad'}, {}, [[], []]),
                            'keypad': Component('A keypad', [0, 0, 0], {'back': 'door', self.keypad_code: 'outside'}, {}, [['inventory', 'knowledge-keypadcode'], []]),
                            'cpainting': Component('A cipher painting', [-40, 0, 1], {}, {}, [['uncover', 'start'], ['cipherlink']]),
                            'cchest': Component('A cipher chest', [-40, -45, 2], {}, {}, [['cipherlink'], ['inventory']]),
                            'bed': Component('A bed', [0, -20, 2], {}, {}, [[], []]),
                            'simonsays': Component('A simon says game', [0, -30, 2], {}, {}, [['start', 'power'], ['uncover', 'power', 'knowledge-keypadcode']]),
                            'amidakuji': Component('Amidakuji', [0, 0, 1], {}, {}, [['start', 'uncover'], ['knowledge-5colororder']]),
                            'family': Component('The family game', [0, 0, 1], {}, {}, [['knowledge-5colororder'], ['uncover', 'power']]),
                            'secretsafe': Component('A desk', [0, 0, 1], {}, {}, [['uncover'], ['inventory']]),
                            'keychest': Component('A chest with a keyhole', [0, 0, 2], {}, {}, [['inventory'], ['inventory']]),
                            'comchest': Component('A chest with a combination', [0, 0, 2], {}, {}, [['knowledge'], ['inventory']]),
                            'hangman': Component('A game of hangman', [0, 0, 1], {}, {}, [['start', 'uncover', 'power'], ['uncover', 'power']]),
                            'blockpush': Component('A game of push the block', [0, 0, 1], {}, {}, [['start', 'inventory', 'uncover', 'power'], ['uncover', 'power', 'knowledge-keypadcode']]),
                            'riddler': Component('A riddle game', [0, 0, 2], {}, {}, [['start', 'power'], ['uncover', 'power', 'knowledge-keypadcode']]),
                            'truculent': Component('A strange puzzle game', [0, 0, 2], {}, {}, [['start', 'power'], ['knowledge', 'power']])
                            }

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
                self.setup_cipher() # covers cpainting
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

        # debug section
        self.components['cpainting'].visible = True
        self.help = True


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
        possible_qs = ['this is a blizzard, seriously', 'the beekeeper and the bagpipes', 'there are thirty nine letters in this sentence',
                       'i love rocky road', 'the gypsy is inherent', 'do you play jazz?']
        possible_qs = ['test']
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
            self.create_basetime()

        while True: # main game loop

            self.update_display()
            self.update_state()

            # update state of game continuously
            for event in pygame.event.get():

                if event.type == QUIT:
                    pygame.quit()
                    sys.exit


    def update_state(self):

        ### Decide action
        if DEBUG:
            temp_action = raw_input('next action: ').lower()
            self.action[0] = temp_action
        else:
            self.action[self.s] = self.parse_twitch_chat_file()
            for i in range(len(self.action)):
                if i != self.s:
                    self.action[i] = 'stay'

        # move onto next screen for next update
        self.s += 1
        if self.s >= len(self.state):
            self.s = 0

        print(self.action)

        for s in range(len(self.action)):

            # possible actions section
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

            # Turn help on or off
            if self.action[s] == 'help on' or (self.action[s] == 'help' and self.help == False):
                self.help = True
            elif self.action[s] == 'help off' or (self.action[s] == 'help' and self.help == True):
                self.help = False

            # moving in and out of journal
            if self.action[s] == 'journal' and self.state[s] != 'journal': # consider journal only from wall?
                self.previous_state = self.state[s]
                self.state[s] = 'journal'
                self.journal_page = 0
            elif self.state[s] == 'journal':
                if self.action[s] == 'left':
                    pass
                if self.action[s] == 'right':
                    pass
                if self.action[s] == 'back':
                    self.state[s] = self.previous_state

            else:
                ### Update state based on action
                for component in self.components:
                    if self.state[s] == component:

                        # change of state (moving the entire screen)
                        if self.action[s] in self.components[component].actions_to_state and self.action[s] in possible_actions:
                            self.state[s] = self.components[component].actions_to_state[self.action[s]]
                            print('moved to: {}'.format(self.state[s]))
                            break

                        # check if component is powered
                        elif not self.components[component].powered:
                            if 'not powered' not in self.journal[-1]:
                                self.jot('{} is not powered.'.format(component))
                            break

                        # change of inventory (adding something to inventory)
                        elif self.action[s] in self.components[component].actions_to_inventory:
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

                #self.screen.blit(self.background, (self.p_offset[0], self.p_offset[1]))

                # offset two screens
                if s == 0:
                    self.p_offset = [30, 10]
                if s == 1:
                    self.p_offset = [890, 10]
                if s == 2:
                    self.p_offset = [30, 560]
                if s == 3:
                    self.p_offset = [890, 560]

                if 'wall' in self.state[s]:
                    self.background = pygame.image.load('pics/walls/{}.png'.format(self.state[s]))
                    layers = self.walls[self.state[s]]
                    for i, layer in enumerate(layers): # starting in the back
                        # i is [0,1]
                        for j, spot in enumerate(layer):
                            # j is [0,1] or [0,1,2] depending on layer
                            # i controls vertical placement, j controls horizontal placement
                            if spot in self.components:
                                if self.components[spot].visible: # only draw if visible
                                    component = spot
                                    c_image = pygame.image.load('pics/{}/{}.png'.format(component, component))
                                    c_image_offset = [c_image.get_width()/2, c_image.get_height()/2]
                                    if i == 0: # in front
                                        vert_plac = 136
                                        if j == 0:
                                            horz_plac = 324
                                        elif j == 1:
                                            horz_plac = 556
                                    elif i == 1: # in back
                                        vert_plac = 252
                                        horz_plac = 220 * (j+1)
                                    horz_plac += self.components[component].image_placement[0]
                                    vert_plac -= self.components[component].image_placement[1]
                                    if self.new_component_glow[0] == spot and self.new_component_glow[1] - dt.datetime.now() > dt.timedelta(seconds=0):
                                        self.background.blit(pygame.image.load('pics/accs/glow.png'), (horz_plac, vert_plac))
                                    self.background.blit(c_image, (horz_plac, vert_plac))
                                    if self.help:
                                        self.draw_message(component, (horz_plac, vert_plac), preset = 'help')

                elif self.state[s] == 'journal':
                    self.background = pygame.image.load('pics/accs/journal-full.png')
                    journal_pages = [[]]
                    cnt = 0
                    for entry in self.journal: # create journal pages
                        if cnt == 32:
                            journal_pages.append([])
                            cnt = 0
                        journal_pages[-1].append(''.join(entry.split(':')[3:]))
                        cnt += 1
                    for i, row in enumerate(journal_pages[self.journal_page]):
                        if len(row) > 35:
                            text = ' '.join(row.split(' ')[:-1]) + '...'
                        else:
                            text = row
                        if i <= 16:
                            self.draw_message(text, (60, 30 + 21 * i), preset = 'journal')
                        if i > 16:
                            self.draw_message(text, (484, 30 + 21 * (i - 17)), preset = 'journal')

                elif self.state[s] == 'cchest':
                    self.background = pygame.image.load('pics/cchest/cchest-full.png')
                    for i, letter in enumerate(self.chest_text):
                        char = pygame.image.load('pics/text/letter-{}-medium.png'.format(letter))
                        self.background.blit(char, (240.5 + i * 88, 125))

                elif self.state[s] == 'cpainting':
                    self.background = pygame.image.load('pics/cpainting/cpainting-full.png')
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
                        self.background = pygame.image.load('pics/simon-says/simon-says-full-{}.png'.format(color))
                        self.screen.blit(self.background, (0,0))
                        time.sleep(0.8)
                        self.background = pygame.image.load('pics/simon-says/simon-says-full.png')

                elif self.state[s] == 'amidakuji':
                    self.background = pygame.image.load('pics/amidakuji/amidakuji-full-{}.png'.format(self.amidakuji_choice))
                    for i, amidakuji_number in enumerate(self.amidakuji_numbers_order):
                        number = pygame.image.load('pics/text/number-{}-medium.png'.format(amidakuji_number))
                        self.background.blit(number, (112 + i * 127, 3))
                    for i, amidakuji_color in enumerate(self.amidakuji_colors_order):
                        color = pygame.image.load('pics/amidakuji/{}-medium.png'.format(amidakuji_color))
                        self.background.blit(color, (111 + i * 128, 430))

                elif self.state[s] == 'family':
                    self.background = pygame.image.load('pics/family/family-full.png')
                    self.draw_message('In order of being the best, enter the names of the family!', (70 + self.p_offset[0], 30 + self.p_offset[1]), preset = 'help')
                    self.draw_message('For example: "daddy mommy lil-joe janice carter-III bob-the-fish"', (70 + self.p_offset[0], 60 + self.p_offset[1]), preset = 'help')
                    self.draw_message('Or: "d m l j c b", or "dmljcb" because I\'m cool like that', (70 + self.p_offset[0], 90 + self.p_offset[1]), preset = 'help')
                    inverse = -1
                    for i, member in enumerate(self.family_members_order):
                        inverse = -inverse
                        member_to_draw = pygame.image.load('pics/family/{}.png'.format(member))
                        self.background.blit(member_to_draw, (111 + i * 108, 180))
                        member_dict = {'daddy':[124, 298-50, 'dot'], 'mommy':[127, 231-50, 'bow'], 'lil-joe':[151, 310-50, 'dot'], 'janice':[124, 266-50, 'bow'],
                                        'carter-iii':[142, 345-50, 'collar'], 'skip':[108, 229-50, 'hat'], 'bob-the-fish':[141, 333-50, 'fish']}
                        article = pygame.image.load('pics/family/{}-{}.png'.format(member_dict[member][2], self.family_members_color_order[member]))
                        self.background.blit(article, (member_dict[member][0] + i * 108, member_dict[member][1]))
                        if self.help:
                            self.draw_message(member, (111 + i * 108 + self.p_offset[0], 260 + self.p_offset[1] + inverse * 90), preset = 'help')

                elif self.state[s] == 'blockpush':
                    self.background = pygame.image.load('pics/blockpush/blockpush-full.png')
                    block = pygame.image.load('pics/blockpush/blockpush-block.png')
                    x = pygame.image.load('pics/blockpush/blockpush-x.png')
                    start = pygame.image.load('pics/blockpush/blockpush-start.png')
                    end = pygame.image.load('pics/blockpush/blockpush-end.png')
                    for i in range(4):
                        for j in range(4):
                            if self.blockpush_grid[i, j] == 1:
                                self.background.blit(x, (200 + j*110, 20 + i*100))
                            if self.blockpush_grid[i, j] == 2:
                                self.background.blit(start, (200 + j*110, 20 + i*100))
                            if self.blockpush_grid[i, j] == 3:
                                self.background.blit(end, (200 + j*110, 20 + i*100))
                            if i == self.blockpush_block[0] and j == self.blockpush_block[1]:
                                self.background.blit(block, (200 + j*110, 20 + i*100))
                    if self.help:
                        self.draw_message('up, down, left, right', (200, 500), preset = 'help')

                elif self.state[s] == 'hangman':
                    self.background = pygame.image.load('pics/hangman/hangman-full.png')
                    if self.hangmanstate > 0:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-head.png'), (340, 65))
                    if self.hangmanstate > 1:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-body.png'), (340, 125))
                    if self.hangmanstate > 2:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-right-leg.png'), (320, 195))
                    if self.hangmanstate > 3:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-left-leg.png'), (370, 195))
                    if self.hangmanstate > 4:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-right-arm.png'), (310, 95))
                    if self.hangmanstate > 5:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-left-arm.png'), (360, 95))
                    if self.hangmanstate > 6:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-eye.png'), (347, 75))
                    if self.hangmanstate > 7:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-eye.png'), (352, 75))
                    if self.hangmanstate > 8:
                        self.background.blit(pygame.image.load('pics/hangman/hangman-frown.png'), (340, 75))
                    h_row = 0 # need to add row wrapping on words
                    rows = textwrap.TextWrapper(width = 28).wrap(text = ''.join(self.hangman_guess))
                    for j, row in enumerate(rows):
                        for i, c in enumerate(row):
                            self.draw_message(c, (170 + i*20, 300 + j*35), font_size = FONTSIZE + 30, text_color = (50,50,50))

                elif self.state[s] == 'riddler':
                    self.background = pygame.image.load('pics/riddler/riddler-full.png')
                    rows = textwrap.TextWrapper(width = 30).wrap(text = self.riddler_riddle)
                    for i, row in enumerate(rows):
                        self.background.blit(pygame.font.SysFont(FONT, FONTSIZE + 10).render(row, True, (0,0,0), (255,255,255)), (200, 100 + 50 * i))

                else:
                    self.background = pygame.image.load('pics/{}/{}-full.png'.format(self.state[s], self.state[s]))


                # other help items
                if self.help and 'wall' in self.state[s]:
                    self.draw_message('Left', (60 + self.p_offset[0], 450 + self.p_offset[1]), preset = 'help')
                    self.draw_message('Right', (800 + self.p_offset[0], 450 + self.p_offset[1]), preset = 'help')

                self.screen.blit(self.background, (self.p_offset[0], self.p_offset[1]))

            # bottom
            statusbar = pygame.image.load('pics/accs/clean-bottom.png')
            self.screen.blit(statusbar, (0, 420))

            # draw journal (last entry)
            rows = textwrap.TextWrapper(width = 50).wrap(text = ''.join(self.journal[-1].split(':')[3:])) # remove timestamp and wrap
            self.draw_message('Last journal entry:', (40, 440), preset = 'bottom')
            for i, row in enumerate(rows):
                self.draw_message(row, (70, 470 + 20 * i), preset = 'bottom')

            # draw inventory
            self.draw_message('Inventory: {}'.format(self.inventory), (640, 440), preset = 'bottom')

            # draw votes/actions
            if not DEBUG:
                s1_seconds = (self.ready_time[0] - dt.datetime.now()).seconds - STREAM_DELAY_OFFSET
                s2_seconds = (self.ready_time[1] - dt.datetime.now()).seconds - STREAM_DELAY_OFFSET
                banner = pygame.image.load('pics/accs/vote.png')
                if 0 < s1_seconds < 10:
                    self.draw_message('Vote! {}'.format(s1_seconds), (130, 80), preset = 'timer')
                    #self.screen.blit(banner, (0, 20))
                    #self.screen.blit(banner, (0, 474))
                if 0 < s2_seconds < 10:
                    self.draw_message('Vote! {}'.format(s2_seconds), (1030, 80), preset = 'timer')
                    #self.screen.blit(banner, (910, 20))
                    #self.screen.blit(banner, (910, 474))

            self.draw_message('now: {}'.format(dt.datetime.now()), (1230, 440), preset = 'status')
            if not DEBUG:
                self.draw_message('s1_ready: {}, s2_ready: {}'.format((self.ready_time[0] - dt.datetime.now()).seconds, \
                                                    (self.ready_time[1] - dt.datetime.now()).seconds), (1230, 470), preset = 'status')
                self.draw_message('s1: {}'.format(self.ready_time[0]), (1230, 500), preset = 'status')
                self.draw_message('s2: {}'.format(self.ready_time[1]), (1230, 530), preset = 'status')

            pygame.display.update()
            self.clock.tick(self.fps)

        except BufferError:
        #except Exception:
            pass

    # blacksword.tff

    def draw_message(self, message, coord = (100, 100), preset = None, font = FONT, font_size = FONTSIZE, text_color = (160, 190, 255), background_color = None, alpha = 255):
        message = message.upper()
        screen_or_background = 'screen'
        if preset == 'journal':
            text_color = (0, 0, 0)
            font_size = FONTSIZE - 5
        if preset == 'help':
            screen_or_background = 'background'
            background_color = (0, 0, 0)
            text_color = (255, 255, 255)
            alpha = 200
            message = ' {} '.format(message)
        elif preset == 'bottom':
            background_color = None
        elif preset == 'timer':
            text_color = (0,0,0)
        font_object = pygame.font.SysFont(font, font_size).render(message, True, text_color, background_color)
        font_object.set_alpha(alpha)
        if screen_or_background == 'screen':
            self.screen.blit(font_object, coord)
        else:
            self.background.blit(font_object, coord)


# ------------------------------------------------------------------------------------------------------------------- TWITCH

    def create_basetime(self):
        with open('vtc.txt', 'w') as f:
            f.write(str(BASETIME))

    def parse_twitch_chat_file(self):

        for s, f in enumerate(['s1_messages.txt', 's2_messages.txt']):

            if os.path.isfile(f):

                with open(f) as fn:
                    contents = fn.read().split('\n')
                os.remove(f)

                print('contents: {}'.format(contents))

                self.ready_time[s] = dt.datetime.strptime(contents[0], '%Y-%m-%d %H:%M:%S.%f')

                # reset votes for this screen
                self.votes[s] = {}

                # partition content into messages and users, might want to use users later
                users = [x.split(':::')[0] for x in contents[1:]]
                messages = [':::'.join(x.split(':::')[1:]) for x in contents[1:]]

                # do votes
                for message in messages:
                    if message == '':
                        pass
                    elif message not in self.votes[s]:
                        self.votes[s][message] = 1
                    else:
                        self.votes[s][message] += 1

                # default action is to stay if there are no votes
                if all([self.votes[s][v] == 0 for v in self.votes[s]]):
                    if 'stay' in self.votes[s]:
                        self.votes[s]['stay'] += 1
                    else:
                        self.votes[s]['stay'] = 1

                # choose max vote per screen
                mv = max(self.votes[s].values())
                action = random.choice([k for (k, v) in self.votes[s].items() if v == mv])
                return action

            else: # if file isn't there, don't do anything
                return 'stay'




def main():
    game = Game()
    game.main()

if __name__ == "__main__":
    main()




# (890, 503) , 214 vert for black, 20 margin






#
