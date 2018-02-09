#
# written by Matt Takao
# started 2017-12-01
# last major update 2017-12-15
#

from pygame.locals import *

import random
import string
import datetime
import sys
import time
import os
import numpy as np

import pygame

pygame.font.init()

DECISIONTIME = 14 # +7 seconds for lag
DEBUG = True

# conda install -c anaconda libpng # for interlace issue
# need 32 bit png
# https://pixlr.com/editor/

# for new puzzles:
#   add to self.components
#   add setup
#   add state update
#   add display update

# to add:
#
# player control (via chat command)
#
# implement successful chain of puzzles:
#   add power inhibit
#
# better font for messages (from cristina)
#
# fix up multiple screens. known issues:
#   implement twitch timing for multiple screens
#   help function has issues
#
# numbers on the wall for a code?
#
# ice puzzles
# spinning wheels ??
#
# trophies
#
# graphical inventory
#
# journal (log of in game events)
#
# MULTIPLE TRACKS (CHAINS), each ending in a clue for a digit of the keypad
#

class Component(object):

    def __init__(self, description, image_placement, actions_to_state = {}, actions_to_inventory = {}, actions_to_event = {}, endpoints = [[], []]):
        self.description = description
        self.image_placement = image_placement  # 3-tuple: horizontal and vertical offset, and then depth (n/a:0, on wall:1, in front:2)
        self.actions_to_state = actions_to_state  # actions and consequences
        self.actions_to_inventory = actions_to_inventory
        self.actions_to_event = actions_to_event
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
        self.screen = pygame.display.set_mode((1800, 703))  # (890, 503) , 200 vert for black, 20 margin
        self.background = pygame.image.load('pics/n-wall.png')
        self.one_off = True # toggler that ensures screen updates after state update?
        self.p_offset = [0, 0] # offset for multiple screens

        # game state
        self.p = 0 # player state to display or update
        self.state = ['n-wall', 's-wall']
        self.action = ['stay', 'stay']
        self.win = False
        self.help = False
        self.center_message = ['', (0,0), datetime.datetime.now(), datetime.timedelta(0,0,0)]
        self.votes = {}
        self.visible_votes = {}
        self.inventory = []

        # game initialization reqs
        self.components_order = []
        self.bridges = []
        self.timer_start = datetime.datetime.now()
        self.walls = {'n-wall':[['', ''], ['', '', '']], 'e-wall':[['', ''], ['', '', '']], 's-wall':[['', ''], ['', '', '']], 'w-wall':[['', ''], ['', '', '']]}
        self.keypad_code = str(random.randint(100, 999))
        print('end:', self.keypad_code)


    def map_components(self): # strings components together in a path to exit

        # define all components: description, image_placement (n/a:0, on wall:1, in front:2), actions_to_state, actions_to_inventory, actions_to_event, endpoints
            self.components = { 'n-wall': Component('North wall', [0, 0, 0], {'left':'w-wall', 'right':'e-wall'}, {}, {}, [[], []]),
                                'e-wall': Component('East wall', [0, 0, 0], {'left':'n-wall', 'right':'s-wall'}, {}, {}, [[], []]),
                                's-wall': Component('South wall', [0, 0, 0], {'left':'e-wall', 'right':'w-wall'}, {}, {}, [[], []]),
                                'w-wall': Component('West wall', [0, 0, 0], {'left':'s-wall', 'right':'n-wall'}, {}, {}, [[], []]),
                                'trophycase': Component('A trophy case', [0, 0, 1], {}, {}, {}, [['knowledge'], ['inventory']]),
                                'door': Component('The exit door', [0, -33, 1], {'keypad':'keypad'}, {}, {}, [[], []]),
                                'keypad': Component('A keypad', [0, 0, 0], {'back': 'door', self.keypad_code: 'outside'}, {}, {}, [['inventory', 'knowledge-keypadcode'], []]),
                                'cpainting': Component('A cipher painting', [0, 0, 1], {}, {}, {}, [['uncover', 'start'], ['cipherlink']]),
                                'cchest': Component('A cipher chest', [0, -45, 2], {}, {}, {}, [['cipherlink'], ['inventory']]),
                                'bed': Component('A bed', [0, -20, 2], {}, {}, {}, [[], []]),
                                'simonsays': Component('A simon says game', [0, -30, 2], {}, {}, {}, [['inventory', 'power'], ['uncover', 'power', 'knowledge-keypadcode']]),
                                'amidakuji': Component('Amidakuji', [0, 0, 1], {}, {}, {}, [['start', 'uncover'], ['knowledge-5colororder']]),
                                'family': Component('The family game', [0, 0, 1], {}, {}, {}, [['knowledge-5colororder'], ['uncover', 'power']]),
                                'secretsafe': Component('A desk', [0, 0, 1], {}, {}, {}, [['uncover'], ['inventory']]),
                                'keychest': Component('A chest with a keyhole', [0, 0, 2], {}, {}, {}, [['inventory'], ['inventory']]),
                                'comchest': Component('A chest with a combination', [0, 0, 2], {}, {}, {}, [['knowledge'], ['inventory']]),
                                'hangman': Component('A game of hangman', [0, 0, 1], {}, {}, {}, [['start', 'uncover', 'power'], ['uncover', 'power']]),
                                'blockpush': Component('A game of push the block', [0, 0, 1], {}, {}, {}, [['start', 'inventory', 'uncover', 'power'], ['uncover', 'power', 'knowledge-keypadcode']])
                                }

            #self.components_to_place = self.generate_puzzle_chain()
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
        self.components_order = ['hangman', 'blockpush', 'amidakuji', 'family', 'cpainting', 'cchest', 'keypad']
        self.bridges = ['uncover', 'uncover', 'knowledge-5colororder', 'uncover', 'cipherlink', 'inventory']

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
        #print(self.simon_says_pattern)
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

        family_members = ['daddy', 'mommy', 'lil-joe', 'meghan', 'carter-iii', 'skip', 'bob-the-fish']
        self.family_members_order = random.sample(family_members, 6)
        self.family_members_color_order = {n:self.amidakuji_colors_order[i] for i, n in enumerate(self.family_members_order)}
        self.family_members_color_order_inv = {v: k for k, v in self.family_members_color_order.iteritems()}
        #print('family members color order:   {}'.format(self.family_members_color_order))

        self.correct_family_order = ' '.join([self.family_members_color_order_inv[self.amidakuji_map[x]] for x in self.amidakuji_map])
        print('correct family order', self.correct_family_order)
        self.components['family'].actions_to_event[self.correct_family_order] = 'complete' # combine all actions?


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

        self.components['blockpush'].actions_to_event['up'] = 'block-up'
        self.components['blockpush'].actions_to_event['down'] = 'block-down'
        self.components['blockpush'].actions_to_event['left'] = 'block-left'
        self.components['blockpush'].actions_to_event['right'] = 'block-right'

        print(self.blockpush_grid, self.blockpush_block)


    def setup_hangman(self):
        possible_qs = ['testing testing', 'the dog and the cat', 'geronimous']
        self.phrase = random.choice(possible_qs)
        self.hangman_guess = ['_' if c.isalpha() else ' ' for c in self.phrase]
        print(self.phrase, self.hangman_guess)
        self.hangmanstate = 0



# -------------------------------------------------------------------------------------------------------------------- EXECUTE

    def main(self):

        # setup
        pygame.init()
        pygame.display.set_caption(self.caption)
        self.map_components()
        self.place_components()

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

            p = self.p

            if True: # disable for cycling players
                p = 1

            if datetime.datetime.now() - self.timer_start > datetime.timedelta(0, DECISIONTIME, 0):
                self.timer_start = datetime.datetime.now()

            always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall', 'help']

            possible_actions = ['stay']

            for component in self.components:
                if self.state[p] == component:

                    possible_actions += self.components[component].actions_to_state.keys()   \
                                    + self.components[component].actions_to_inventory.keys()  \
                                    + self.components[component].actions_to_event.keys()

            possible_actions += always_actions

            for action in possible_actions:
                if action in self.components:
                    if not self.components[action].visible:
                        possible_actions.remove(action) # remove action if it is invisible

            #print('Possible actions: {}\n'.format(possible_actions))


            ### Decide action
            if DEBUG:
                self.action[p] = raw_input('next action for player{}: '.format(p+1))
            else:
                self.action[p] = self.parse_twitch_chat_file(possible_actions)

            # Turn help on or off
            if self.action[p] == 'help on' or (self.action[p] == 'help' and self.help == False):
                self.help = True
            elif self.action[p] == 'help off' or (self.action[p] == 'help' and self.help == True):
                self.help = False

            ### Update state based on action
            if self.action[p] in possible_actions:
                for component in self.components:
                    if self.state[p] == component:
                        if self.action[p] in self.components[component].actions_to_state: # change of state
                            self.state[p] = self.components[component].actions_to_state[self.action[p]]
                            print('moved to: {}'.format(self.state[p]))
                            break
                        elif self.action[p] in self.components[component].actions_to_inventory: # change of inventory
                            if self.components[component].actions_to_inventory[self.action[p]] not in self.inventory: # add only if you don't already have it
                                self.inventory.append(self.components[component].actions_to_inventory[self.action[p]])
                                self.center_message = ['You got something in your inventory.', (150, 250), datetime.datetime.now(), datetime.timedelta(0,5,0)]
                                break
                        elif self.action[p] in self.components[component].actions_to_event: # other change
                            # action to event, complete
                            if self.components[component].actions_to_event[self.action[p]] == 'complete':
                                self.activate_next_puzzle(component)
                            # blockpush
                            if self.state[p] == 'blockpush':
                                if self.components[component].actions_to_event[self.action[p]] == 'block-up' and self.blockpush_block[0] > 0:
                                    self.blockpush_block[0] -= 1
                                if self.components[component].actions_to_event[self.action[p]] == 'block-down' and self.blockpush_block[0] < 3:
                                    self.blockpush_block[0] += 1
                                if self.components[component].actions_to_event[self.action[p]] == 'block-right' and self.blockpush_block[1] < 3:
                                    self.blockpush_block[1] += 1
                                if self.components[component].actions_to_event[self.action[p]] == 'block-left' and self.blockpush_block[1] > 0:
                                    self.blockpush_block[1] -= 1
                                if self.blockpush_block == self.blockpush_end:
                                    self.activate_next_puzzle('blockpush')
                                if self.blockpush_grid[self.blockpush_block[0], self.blockpush_block[1]] == 1:
                                    self.setup_blockpush()
                            if self.state[p] == 'hangman':
                                if self.action[p].isalpha():
                                    next_guess = [self.action[p] if self.hangman_phrase[i] == self.action[p] else c for i, c in enumerate(self.hangman_guess)]
                                    if next_guess == self.hangman_guess:
                                        self.hangmanstate += 1
                                    else:
                                        self.hangman_guess = next_guess
                                    if all([x != '_' for x in self.hangman_guess]):
                                        print('win')
                                        self.activate_next_puzzle('hangman')
                                    if self.hangmanstate > 5:
                                        print('lose')
                                        self.setup_hangman()
                                    print(self.hangman_guess)

                        else:
                            pass

            if self.state[p] == 'outside':
                self.win = True

            self.p += 1
            if self.p >= len(self.state):
                self.p = 0

        if self.one_off:
            self.one_off = False
        else:
            self.one_off = True


    def activate_next_puzzle(self, component):

        print('activating {}'.format(self.components_order[self.components_order.index(component) + 1]))
        self.center_message = ['You hear the sound of something activating.', (150, 250), datetime.datetime.now(), datetime.timedelta(0,5,0)]
        self.components[self.components_order[self.components_order.index(component) + 1]].powered = True
        self.components[self.components_order[self.components_order.index(component) + 1]].visible = True


# --------------------------------------------------------------------------------------------------------- DRAW

    def update_display(self):

        try:

            for p in range(len(self.state)): # iterate over players

                self.screen.blit(self.background, (self.p_offset[0], self.p_offset[1]))

                # offset two screens
                self.p_offset = [0, 0]
                if p == 1:
                    self.p_offset = [910, 0]

                if 'wall' in self.state[p]:
                    self.background = pygame.image.load('pics/{}.png'.format(self.state[p]))
                    layers = self.walls[self.state[p]]
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
                                    self.background.blit(c_image, (horz_plac, vert_plac))
                                    if self.help:
                                        self.draw_message(component, (horz_plac + self.p_offset[0], vert_plac + self.p_offset[1]))

                elif self.state[p] == 'cchest':
                    self.background = pygame.image.load('pics/cchest-full.png')
                    for i, letter in enumerate(self.chest_text):
                        char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
                        self.background.blit(char, (240.5 + i * 88, 125))

                elif self.state[p] == 'cpainting':
                    self.background = pygame.image.load('pics/cpainting-full.png')
                    quote = ''.join(string.lower(self.painting_cipher_text).split('-')[:-1])
                    quote_by = string.lower(self.painting_text).split('-')[-1]
                    for i, letter in enumerate(quote): # this needs to be more complicated for
                        if letter.isalpha():
                            char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
                        elif letter == '.':
                            char = pygame.image.load('pics/period-medium.png')
                        elif letter == ',':
                            char = pygame.image.load('pics/comma-medium.png')
                        elif letter == '\'':
                            char = pygame.image.load('pics/apostrophe-medium.png')
                        elif letter == '-':
                            char = pygame.image.load('pics/hyphen-medium.png')
                        elif letter == '\"':
                            char = pygame.image.load('pics/quote-medium.png')
                        else:
                            char = 'none'
                        if char != 'none':
                            char = pygame.transform.scale(char, (40,40))
                            self.background.blit(char, (190 + i % 12 * 45, 80 + (i / 12) * 45))
                        for i, letter in enumerate(quote_by): # this needs to be more complicated for
                            if letter.isalpha():
                                char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
                            elif letter == '.':
                                char = pygame.image.load('pics/period-medium.png')
                            elif letter == '-':
                                char = pygame.image.load('pics/hyphen-medium.png')
                            else:
                                char = 'none'
                            if char != 'none':
                                char = pygame.transform.scale(char, (40,40))
                                self.background.blit(char, (220 + i * 45, 400))

                elif self.state[p] == 'simon-says':
                    self.background = pygame.image.load('pics/simon-says-full.png')
                    self.screen.blit(self.background, (0,0))
                    for color in self.simon_says_pattern:
                        self.background = pygame.image.load('pics/simon-says-full-{}.png'.format(color))
                        self.screen.blit(self.background, (0,0))
                        time.sleep(0.8)
                        self.background = pygame.image.load('pics/simon-says-full.png')

                elif self.state[p] == 'amidakuji':
                    self.background = pygame.image.load('pics/amidakuji-full-{}.png'.format(self.amidakuji_choice))
                    for i, amidakuji_number in enumerate(self.amidakuji_numbers_order):
                        number = pygame.image.load('pics/number-{}-medium.png'.format(amidakuji_number))
                        self.background.blit(number, (112 + i * 127, 3))
                    for i, amidakuji_color in enumerate(self.amidakuji_colors_order):
                        color = pygame.image.load('pics/{}-medium.png'.format(amidakuji_color))
                        self.background.blit(color, (111 + i * 128, 430))

                elif self.state[p] == 'family':
                    self.background = pygame.image.load('pics/family-full.png')
                    self.draw_message('In order of being the best, enter the names of the family!', (140 + self.p_offset[0], 100 + self.p_offset[1]))
                    self.draw_message('For example: "daddy mommy lil-joe meghan carter-III bob-the-fish"', (140 + self.p_offset[0], 130 + self.p_offset[1]))
                    for i, member in enumerate(self.family_members_order):
                        member_to_draw = pygame.image.load('pics/{}.png'.format(member))
                        self.background.blit(member_to_draw, (111 + i * 108, 230))
                        member_dict = {'daddy':[124, 298, 'dot'], 'mommy':[127, 231, 'bow'], 'lil-joe':[151, 310, 'dot'], 'meghan':[124, 266, 'bow'],
                                        'carter-iii':[142, 345, 'collar'], 'skip':[108, 229, 'hat'], 'bob-the-fish':[141, 333, 'fish']}
                        article = pygame.image.load('pics/{}-{}.png'.format(member_dict[member][2], self.family_members_color_order[member]))
                        self.background.blit(article, (member_dict[member][0] + i * 108, member_dict[member][1]))
                        if self.help:
                            self.draw_message(member, (111 + i * 108 + self.p_offset[0], 190 + self.p_offset[1]))

                elif self.state[p] == 'blockpush':
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

                elif self.state[p] == 'hangman':
                    self.background = pygame.image.load('pics/hangman-full.png')
                    for i, c in enumerate(self.hangman_guess):
                        if c.isalpha():
                            char = pygame.image.load('pics/letter-{}-medium.png'.format(c))
                            self.background.blit(char, (220 + i * 45, 400))
                        elif c == '_':
                            char = pygame.image.load('pics/underscore-medium.png')
                            self.background.blit(char, (220 + i * 45, 400))


                else:
                    self.background = pygame.image.load('pics/{}-full.png'.format(self.state[p]))


                # draw center message if applicable
                if self.center_message[3].seconds > 0:
                    if datetime.datetime.now() - self.center_message[2] > self.center_message[3]:
                        self.center_message[3] = datetime.timedelta(0,0,0)
                    self.draw_message(self.center_message[0], self.center_message[1], font_size = 38, text_color = (255, 255, 255))

                # other help items
                if self.help and 'wall' in self.state[p]:
                    self.draw_message('Left', (60 + self.p_offset[0], 450 + self.p_offset[1]))
                    self.draw_message('Right', (800 + self.p_offset[0], 450 + self.p_offset[1]))

            # draw timer and actions/votes

            if DEBUG:
                pass
            else:
                if (datetime.datetime.now() - self.timer_start).seconds < DECISIONTIME - 7:
                    self.draw_message('Timer: {}'.format(DECISIONTIME - 7 - (datetime.datetime.now() - self.timer_start).seconds), (50, 550))
                else:
                    self.draw_message('Hold on until next round to vote!   ({})'.format(DECISIONTIME - (datetime.datetime.now() - self.timer_start).seconds), (50, 550))
                self.draw_message('Last votes were: {}'.format(self.visible_votes), (50, 580))

            #self.blackbottom = pygame.image.load('pics/black-bottom.png')
            #self.screen.blit(self.blackbottom, (0, 503))

            # draw inventory
            self.draw_message('Inventory: {}'.format(self.inventory), (50, 630))

            pygame.display.update()
            self.clock.tick(self.fps)

        except BufferError:
        #except Exception:
            pass

    def draw_message(self, message, coord = (100, 100), font = 'blacksword.ttf', font_size = 28, text_color = (160, 190, 255), background_color = (  0,   0,   0)):
        self.screen.blit(pygame.font.SysFont(font, font_size).render(message, True, text_color, background_color), coord)



# ------------------------------------------------------------------------------------------------------------------- TWITCH

    def parse_twitch_chat_file(self, possible_actions):

        if os.path.isfile('messages.txt'):

            with open('messages.txt') as f:
                contents = f.read().split('\n')

            self.twitch_timer = contents[0]
            self.timer_start = datetime.datetime.strptime(self.twitch_timer, '%Y-%m-%d %H:%M:%S.%f')

            self.votes = {n:0 for n in possible_actions}
            self.visible_votes = {}

            for message in contents[1:]:
                if message == '':
                    pass
                elif message not in self.visible_votes:
                    self.visible_votes[message] = 1
                else:
                    self.visible_votes[message] += 1
                if message in possible_actions:
                    self.votes[message] += 1

            if all([self.votes[x] == 0 for x in self.votes]):
                self.votes['stay'] += 1

            mv = max(self.votes.values())
            action = random.choice([k for (k, v) in self.votes.items() if v == mv])

            os.remove('messages.txt')

            return action



def main():
    game = Game()
    game.main()

if __name__ == "__main__":
    main()
