from pygame.locals import *

import threading

import random
import string
import datetime
import sys
import time

import select

import pygame

import chat_connect

pygame.font.init()

RESOLUTION = (890, 503)

DECISIONTIME = 10

##COLORS##
#             R    G    B
WHITE    = (255, 255, 255)
BLUE     = (  0,   0, 255)
RED      = (255,   0,   0)
BLACK    = (  0,   0,   0)
GOLD     = (255, 215,   0)
HIGH     = (160, 190, 255)

class Component(object):

	def __init__(self, image_placement, actions_to_state = {}, actions_to_inventory = {}):
		self.image_placement = image_placement  # 3-tuple: horizontal and vertical offset, and then layer placement (n/a:0, on wall:1, in front:2)
		self.actions_to_state = actions_to_state  # actions and consequences
		self.actions_to_inventory = actions_to_inventory
		self.on_wall = ''

class Game:
	"""
	The main game control.
	"""

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

		self.timer_start = datetime.datetime.now()
		self.inventory = []
		self.walls = {'n-wall':[['', ''], ['', '', '']], 'e-wall':[['', ''], ['', '', '']], 's-wall':[['', ''], ['', '', '']],
			'w-wall':[['', ''], ['', '', '']]}
		self.win = False
		self.keypad_code = str(random.randint(100, 999))

		# twitch IRC
		self.s = chat_connect.openSocket()
		#self.s.setblocking(0)
		try:
			chat_connect.joinRoom(self.s)
		except Exception:
			pass
		self.readbuffer = ""


	def map_components(self): # strings components together in a path to exit

		# define all components
		self.components = { 'n-wall': Component([0, 0, 0], {'left':'w-wall', 'right':'e-wall'}, {}),
							'e-wall': Component([0, 0, 0], {'left':'n-wall', 'right':'s-wall'}, {}),
							's-wall': Component([0, 0, 0], {'left':'e-wall', 'right':'w-wall'}, {}),
							'w-wall': Component([0, 0, 0], {'left':'s-wall', 'right':'n-wall'}, {}),
							'cipher-chest': Component([0, 0, 2], {}, {}),
							'cipher-painting': Component([0, 0, 1], {}, {}),
							'door': Component([0, 0, 1], {'keypad':'keypad'}, {}),
							'bed': Component([0, 0, 2], {}, {}),
							'keypad': Component([0, 0, 0], {'back': 'door', self.keypad_code: 'outside'}, {}),
							'simon-says': Component([0, 0, 2], {}, {})
						  }

		self.components_to_place = ['cipher-chest', 'cipher-painting', 'door', 'bed', 'simon-says']

		if 'cipher-chest' in self.components_to_place:
			self.setup_cipher()

		if 'simon-says' in self.components_to_place:
			self.setup_simon_says()

		# ensure there are enough spaces on walls when choosing components


	def place_components(self): # puts components on wall (for drawing)

		cnt = 0
		for component in self.components_to_place:
			not_done_placing_component = True
			while not_done_placing_component:
				random_wall = random.choice(['n-wall', 'e-wall', 's-wall', 'w-wall'])
				if self.components[component].image_placement[2] == 1: # if component is to be placed on wall
					self.walls[random_wall][0][random.choice([spot for spot in [0,1] if self.walls[random_wall][0][spot] == ''])] = component
					self.components[random_wall].actions_to_state[component] = component
					self.components[component].on_wall = random_wall
					not_done_placing_component = False
				if self.components[component].image_placement[2] == 2: # if component is to be placed in front of wall
					self.walls[random_wall][1][random.choice([spot for spot in [0,2] if self.walls[random_wall][1][spot] == ''])] = component
					self.components[random_wall].actions_to_state[component] = component
					self.components[component].on_wall = random_wall
					not_done_placing_component = False
				cnt += 1
				if cnt > 50: # in case of unexpected endless loop
					print('------------something unexpected: breaking!!')
					break
		print(self.walls)

		for component in self.components: # add the back option for components
			if self.components[component].on_wall != '':
				self.components[component].actions_to_state['back'] = self.components[component].on_wall


	def setup_cipher(self):

		self.cipher_number = random.randint(1, 24)

		self.chest_text = random.choice(['ghost', 'booms', 'tally', 'rando', 'night', 'sleep', 'santa', 'could', 'alone', 'happy'])
		self.chest_cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.chest_text])

		#self.painting_text = 'an investment in knowledge pays the best interest.' #benjamin franklin
		self.painting_text = random.choice(['Don\'t cry because it\'s over, smile because it happened.-Dr. Seuss', 'Whatever you do, do it well.-Walt Disney',
											'What we think, we become.-Buddha', 'Strive for greatness.-Lebron James'])
		self.painting_cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.painting_text])

		self.components['cipher-chest'].actions_to_inventory[self.chest_cipher_text] = self.keypad_code

		print('CIPHER: ',self.cipher_number, self.chest_cipher_text)


	def setup_simon_says(self):

		self.simon_says_pattern = [random.choice(['blue','red','green','yellow']) for _ in range(5)]
		print(self.simon_says_pattern)
		self.simon_says_current_pattern = []
		self.simon_says_user_guess = []


# -------------------------------------------------------------------------------------------------------------------- EXECUTE

	def main(self):
		""""This executes the game and controls its flow."""

		# setup
		pygame.init()
		pygame.display.set_caption(self.caption)
		self.map_components()
		self.place_components()

		while True: # main game loop

			if threading.active_count() < 2:
				t = threading.Thread(target = self.update_state)
				t.daemon = True
				t.start()

			#print(threading.active_count())

			# update state of game continuously
			for event in pygame.event.get():

				if event.type == QUIT:
					pygame.quit()
					sys.exit

			# update display continuously
			self.update_display()


	def update_state(self):

		### Determine possible actions

		always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall']
		possible_actions = []
		for component in self.components:
			if self.state == component:
				possible_actions = self.components[component].actions_to_state.keys() + self.components[component].actions_to_inventory.keys()
		# move these to place_components eventually
		# add possible actions from wall to component
		if self.state == 'n-wall':
			possible_actions += [x for x in self.components if self.components[x].on_wall == 'n-wall']
		elif self.state == 'e-wall':
			possible_actions += [x for x in self.components if self.components[x].on_wall == 'e-wall']
		elif self.state == 's-wall':
			possible_actions += [x for x in self.components if self.components[x].on_wall == 's-wall']
		elif self.state == 'w-wall':
			possible_actions += [x for x in self.components if self.components[x].on_wall == 'w-wall']

		#print('Possible actions: {}\n'.format(possible_actions))


		### Decide action
		self.action = raw_input('next action? ') # for working offline
		#self.action = self.parse_twitch_chat(possible_actions)

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

		if self.state == 'outside':
			self.win = True


# --------------------------------------------------------------------------------------------------------- DRAW

	def update_display(self):

		self.screen.blit(self.background, (0,0))

		if datetime.datetime.now() - self.timer_start > datetime.timedelta(0, DECISIONTIME + 0.8, 0):
			self.timer_start = datetime.datetime.now()
			self.user_messages = []

		time.sleep(0.15)

		if 'wall' in self.state:
			self.background = pygame.image.load('pics/{}.png'.format(self.state))
			#print('\nstate is!! {} \nwalls are: {}'.format(self.state, self.walls))
			layers = self.walls[self.state]
			#print(layers)

			for i, layer in enumerate(layers): # starting in the back
				# i is [0,1]
				for j, spot in enumerate(layer):
					# j is [0,1] or [0,1,2] depending on layer
					# i controls vertical placement, j controls horizontal placement
					if spot in self.components:
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
							horz_plac = 220 * (i+1)

						self.background.blit(c_image, (horz_plac, vert_plac))

		elif self.state == 'cipher-chest':
			self.background = pygame.image.load('pics/cipher-chest-full.png')
			for i, letter in enumerate(self.chest_text):
				char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
				self.background.blit(char, (240.5 + i * 88, 125))

		elif self.state == 'cipher-painting':
			self.background = pygame.image.load('pics/cipher-painting-full.png')
			row = 0
			quote = ''.join(string.lower(self.painting_cipher_text).split('-')[:-1])
			quote_by = string.lower(self.painting_text).split('-')[-1]
			for i, letter in enumerate(quote): # this needs to be more complicated for
				if letter.isalpha():
					char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
				elif letter == '.':
					char = pygame.image.load('pics/period-medium.png'.format(letter))
				elif letter == ',':
					char = pygame.image.load('pics/comma-medium.png'.format(letter))
				elif letter == '\'':
					char = pygame.image.load('pics/apostrophe-medium.png'.format(letter))
				elif letter == '-':
					char = pygame.image.load('pics/hyphen-medium.png'.format(letter))
				else:
					char = 'none'
				if char != 'none':
					char = pygame.transform.scale(char, (40,40))
					self.background.blit(char, (190 + i % 12 * 45, 80 + (i / 12) * 45))
			for i, letter in enumerate(quote_by): # this needs to be more complicated for
				if letter.isalpha():
					char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
				elif letter == '.':
					char = pygame.image.load('pics/period-medium.png'.format(letter))
				elif letter == '-':
					char = pygame.image.load('pics/hyphen-medium.png'.format(letter))
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

		else:
			self.background = pygame.image.load('pics/{}-full.png'.format(self.state))

		# draw timer and actions/votes

		self.blackbottom = pygame.image.load('pics/black-bottom.png')
		self.screen.blit(self.blackbottom, (0, 503))

		self.screen.blit(pygame.font.Font('freesansbold.ttf', 18).render('Timer: {}'.format((datetime.datetime.now() - self.timer_start).seconds), True, HIGH, BLACK), (200, 550))
		self.screen.blit(pygame.font.Font('freesansbold.ttf', 18).render('Previous action: {}'.format(self.action), True, HIGH, BLACK), (600, 550))
		self.screen.blit(pygame.font.Font('freesansbold.ttf', 18).render('Votes are: {}'.format(self.user_messages), True, HIGH, BLACK), (400, 580))

		pygame.display.update()
		self.clock.tick(self.fps)

		# draw inventory
		self.screen.blit(pygame.font.Font('freesansbold.ttf', 18).render('Inventory: \n{}'.format(self.inventory), True, HIGH, BLACK), (900, 150))


	def draw_message(self, message, coord = [100, 100]):

		font_obj = pygame.font.Font('freesansbold.ttf', 18)
		text_surface_obj = font_obj.render(message, True, HIGH, BLACK)
		text_rect_obj = text_surface_obj.get_rect()
		text_rect_obj.center = (coord[0], coord[1])
		return [text_surface_obj, text_rect_obj]


# ------------------------------------------------------------------------------------------------------------------- TWITCH

	def get_twitch_chat(self): # returns xx seconds of twitch chat

		while datetime.datetime.now() - self.timer_start < datetime.timedelta(0, DECISIONTIME, 0):
			timeout = 1 #sec
			try:
				ready = select.select([self.s], [], [], timeout)
			except Exception:
				pass
			#print ready
			if ready[0]:
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

				self.user_messages.append(message[:-1])

		return self.user_messages


	def parse_twitch_chat(self, possible_actions):

		self.user_messages = []
		messages = self.get_twitch_chat() # this should take xx seconds
		#print('{}: got: {}'.format(datetime.datetime.now(), messages))

		if len(messages) > 0:
			votes = {action:0 for action in possible_actions}

			for line in messages:
				if line in possible_actions:
					votes[line] += 1

			mv = max(votes.values())
			rc = random.choice([k for (k, v) in votes.items() if v == mv])

			print(votes, rc)

		else:
			rc = 'stay'

		return rc



def main():
	game = Game()
	game.main()

if __name__ == "__main__":
	main()
