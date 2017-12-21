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

import pygame

pygame.font.init()

RESOLUTION = (890, 503)

DECISIONTIME = 17

# conda install -c anaconda libpng # for interlace issue
# need 32 bit png
# https://pixlr.com/editor/

# to add:
#
# ice puzzles
# simon says
# spinning wheels

class Component(object):

    def __init__(self, description, image_placement, actions_to_state = {}, actions_to_inventory = {}, actions_to_event = {}):
        self.description = description
        self.image_placement = image_placement  # 3-tuple: horizontal and vertical offset, and then layer placement (n/a:0, on wall:1, in front:2)
        self.actions_to_state = actions_to_state  # actions and consequences
        self.actions_to_inventory = actions_to_inventory
        self.actions_to_event = actions_to_event
        self.visible = True
        self.on_wall = ''

class Game:

# ----------------------------------------------------------------------------------------------------------------------------------- PREP

    def __init__(self):

        self.caption = "Twitch Escapes"
        self.fps = 60
        self.clock = pygame.time.Clock()

        # just n-wall: 890, 503
        self.screen = pygame.display.set_mode((1090, 703))
        self.background = pygame.image.load('pics/n-wall.png')

        self.state = 's-wall'
        self.action = 'stay'

        self.screen_messages = []
        self.user_messages = []

        self.center_message = ['', (0,0), datetime.datetime.now(), datetime.timedelta(0,0,0)]

        self.help = False

        self.votes = {}
        self.visible_votes = {}

        self.timer_start = datetime.datetime.now()
        self.inventory = []
        self.walls = {'n-wall':[['', ''], ['', '', '']], 'e-wall':[['', ''], ['', '', '']], 's-wall':[['', ''], ['', '', '']], 'w-wall':[['', ''], ['', '', '']]}

        self.win = False
        self.keypad_code = str(random.randint(100, 999))


    def map_components(self): # strings components together in a path to exit

        # define all components
            self.components = { 'n-wall': Component('North wall', [0, 0, 0], {'left':'w-wall', 'right':'e-wall'}, {}, {}),
                                'e-wall': Component('East wall', [0, 0, 0], {'left':'n-wall', 'right':'s-wall'}, {}, {}),
                                's-wall': Component('South wall', [0, 0, 0], {'left':'e-wall', 'right':'w-wall'}, {}, {}),
                                'w-wall': Component('West wall', [0, 0, 0], {'left':'s-wall', 'right':'n-wall'}, {}, {}),
                                'cchest': Component('A cipher chest', [0, -45, 2], {}, {}, {}),
                                'cpainting': Component('A cipher painting', [0, 0, 1], {}, {}, {}),
                                'door': Component('The exit door', [0, -33, 1], {'keypad':'keypad'}, {}, {}),
                                'bed': Component('A bed', [0, -20, 2], {}, {}, {}),
                                'keypad': Component('A keypad', [0, 0, 0], {'back': 'door', self.keypad_code: 'outside'}, {}, {}),
                                'simon-says': Component('A simon says game', [0, -30, 2], {}, {}, {}),
                                'amidakuji': Component('Amidakuji', [0, 0, 1], {}, {}, {}),
                                'family': Component('The family game', [0, 0, 1], {}, {}, {})
                                }

            self.components_to_place = ['cchest', 'cpainting', 'door', 'bed', 'amidakuji', 'family']

            self.components['cpainting'].visible = False

            if 'cchest' in self.components_to_place:
                self.setup_cipher()

            if 'simon-says' in self.components_to_place:
                self.setup_simon_says()

            if 'amidakuji' in self.components_to_place:
                self.setup_amidakuji()

            if 'family' in self.components_to_place:
                self.setup_family()

            # ensure there are enough spaces on walls when choosing components


    def place_components(self): # puts components on wall (for drawing)

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
                            'what we think, we become.-Buddha', 'strive for greatness.-Lebron James', 'be so good they can\'t ignore you.-Steve Martin',
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

        self.components['cpainting'].visible = False # will show after complete

        self.correct_family_order = ' '.join([self.family_members_color_order_inv[self.amidakuji_map[x]] for x in self.amidakuji_map])
        print('correct family order', self.correct_family_order)
        self.components['family'].actions_to_event[self.correct_family_order] = 'show cpainting' # combine all actions?


# -------------------------------------------------------------------------------------------------------------------- EXECUTE

    def main(self):
        """"This executes the game and controls its flow."""

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

        #print('paint visible', self.components['cpainting'].visible)

        if datetime.datetime.now() - self.timer_start > datetime.timedelta(0, DECISIONTIME, 0):
            self.timer_start = datetime.datetime.now()

        always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall', 'help']

        possible_actions = ['stay']

        for component in self.components:
            if self.state == component:

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
        #self.action = raw_input('next action? ') # for working offline
        self.action = self.parse_twitch_chat_file(possible_actions)

        # Turn help on or off
        if self.action == 'help on' or (self.action == 'help' and self.help == False):
            self.help = True
        elif self.action == 'help off' or (self.action == 'help' and self.help == True):
            self.help = False

        ### Update state based on action
        if self.action in possible_actions:
            for component in self.components:
                if self.state == component:
                    if self.action in self.components[component].actions_to_state: # change of state
                        self.state = self.components[component].actions_to_state[self.action]
                        print('moved to: {}'.format(self.state))
                        break
                    elif self.action in self.components[component].actions_to_inventory: # change of inventory
                        if self.components[component].actions_to_inventory[self.action] not in self.inventory: # add only if you don't already have it
                            self.inventory.append(self.components[component].actions_to_inventory[self.action])
                            self.center_message = ['You got something in your inventory.', (150, 250), datetime.datetime.now(), datetime.timedelta(0,5,0)]
                            break
                    elif self.action in self.components[component].actions_to_event: # other change
                        if self.action == self.correct_family_order:
                            self.components['cpainting'].visible = True
                            self.center_message = ['You hear the sound of a painting materializing.', (150, 250), datetime.datetime.now(), datetime.timedelta(0,5,0)]
                    else:
                        pass
                        #print('did not do anything')

        if self.state == 'outside':
            self.win = True


# --------------------------------------------------------------------------------------------------------- DRAW

    def update_display(self):

        try:

            self.screen.blit(self.background, (0,0))

            if 'wall' in self.state:
                self.background = pygame.image.load('pics/{}.png'.format(self.state))

                layers = self.walls[self.state]
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
                                #print(c_image_offset)

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
                                    self.draw_message(component, (horz_plac, vert_plac))

            elif self.state == 'cchest':
                self.background = pygame.image.load('pics/cchest-full.png')
                for i, letter in enumerate(self.chest_text):
                    char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
                    self.background.blit(char, (240.5 + i * 88, 125))

            elif self.state == 'cpainting':
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

            elif self.state == 'simon-says':
                self.background = pygame.image.load('pics/simon-says-full.png')
                self.screen.blit(self.background, (0,0))
                for color in self.simon_says_pattern:
                    self.background = pygame.image.load('pics/simon-says-full-{}.png'.format(color))
                    self.screen.blit(self.background, (0,0))
                    time.sleep(0.8)
                    self.background = pygame.image.load('pics/simon-says-full.png')

            elif self.state == 'amidakuji':
                self.background = pygame.image.load('pics/amidakuji-full-{}.png'.format(self.amidakuji_choice))
                for i, amidakuji_number in enumerate(self.amidakuji_numbers_order):
                    number = pygame.image.load('pics/number-{}-medium.png'.format(amidakuji_number))
                    self.background.blit(number, (112 + i * 127, 3))
                for i, amidakuji_color in enumerate(self.amidakuji_colors_order):
                    color = pygame.image.load('pics/{}-medium.png'.format(amidakuji_color))
                    self.background.blit(color, (111 + i * 128, 430))

            elif self.state == 'family':
                self.background = pygame.image.load('pics/family-full.png')

                self.draw_message('In order of being the best, enter the names of the family!', (140, 100))
                self.draw_message('For example: "daddy mommy lil-joe meghan carter-III bob-the-fish"', (140, 130))

                for i, member in enumerate(self.family_members_order):
                    member_to_draw = pygame.image.load('pics/{}.png'.format(member))
                    self.background.blit(member_to_draw, (111 + i * 108, 230))

                    if member == 'daddy':
                        article_to_draw = pygame.image.load('pics/dot-{}.png'.format(self.family_members_color_order['daddy']))
                        self.background.blit(article_to_draw, (124 + i * 108, 298))

                    if member == 'mommy':
                        article_to_draw = pygame.image.load('pics/bow-{}.png'.format(self.family_members_color_order['mommy']))
                        self.background.blit(article_to_draw, (127 + i * 108, 231))

                    if member == 'lil-joe':
                        article_to_draw = pygame.image.load('pics/dot-{}.png'.format(self.family_members_color_order['lil-joe']))
                        self.background.blit(article_to_draw, (151 + i * 108, 310))

                    if member == 'meghan':
                        article_to_draw = pygame.image.load('pics/bow-{}.png'.format(self.family_members_color_order['meghan']))
                        self.background.blit(article_to_draw, (124 + i * 108, 266))

                    if member == 'carter-iii':
                        article_to_draw = pygame.image.load('pics/collar-{}.png'.format(self.family_members_color_order['carter-iii']))
                        self.background.blit(article_to_draw, (142 + i * 108, 345))

                    if member == 'skip':
                        article_to_draw = pygame.image.load('pics/hat-{}.png'.format(self.family_members_color_order['skip']))
                        self.background.blit(article_to_draw, (108 + i * 108, 229))

                    if member == 'bob-the-fish':
                        article_to_draw = pygame.image.load('pics/fish-{}.png'.format(self.family_members_color_order['bob-the-fish']))
                        self.background.blit(article_to_draw, (141 + i * 108, 333))

                    if self.help:
                        self.draw_message(member, (111 + i * 108, 190))

            else:
                self.background = pygame.image.load('pics/{}-full.png'.format(self.state))


            # draw center message if applicable
            if self.center_message[3].seconds > 0:
                if datetime.datetime.now() - self.center_message[2] > self.center_message[3]:
                    self.center_message[3] = datetime.timedelta(0,0,0)
                self.draw_message(self.center_message[0], self.center_message[1], font_size = 38, text_color = (255, 255, 255))

            # other help items
            if self.help and 'wall' in self.state:
                self.draw_message('Left', (60, 450))
                self.draw_message('Right', (800, 450))

            # draw timer and actions/votes

            self.blackbottom = pygame.image.load('pics/black-bottom.png')
            self.screen.blit(self.blackbottom, (0, 503))

            if (datetime.datetime.now() - self.timer_start).seconds < DECISIONTIME - 7:
                self.draw_message('Timer: {}'.format(DECISIONTIME - 7 - (datetime.datetime.now() - self.timer_start).seconds), (50, 550))
            else:
                self.draw_message('Hold on until next round to vote!   ({})'.format(DECISIONTIME - (datetime.datetime.now() - self.timer_start).seconds), (50, 550))
            self.draw_message('Last votes were: {}'.format(self.visible_votes), (50, 580))

            pygame.display.update()
            self.clock.tick(self.fps)

            # draw inventory
            self.draw_message('Inventory: {}'.format(self.inventory), (900, 150))

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
                #print('message: {}'.format(message))
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
