from pygame.locals import *

import threading

import random
import string
import datetime
import sys
import time

import pygame

import chat_connect

pygame.font.init()

RESOLUTION = (890, 503)

##COLORS##
#             R    G    B
WHITE    = (255, 255, 255)
BLUE     = (  0,   0, 255)
RED      = (255,   0,   0)
BLACK    = (  0,   0,   0)
GOLD     = (255, 215,   0)
HIGH     = (160, 190, 255)

class Component(object):

	def __init__(self, image_placement, actions):
		self.image_placement = image_placement  # 3-tuple: horizontal and vertical offset, and then layer placement (n/a:0, on wall:1, in front:2)
		self.actions = actions  # actions and consequences
		self.on_wall = ''

class Game:
	"""
	The main game control.
	"""

	def __init__(self):

		self.caption = "Twitch Escapes"

		self.fps = 60
		self.clock = pygame.time.Clock()

		self.screen = pygame.display.set_mode((890, 503))
		self.background = pygame.image.load('pics/n-wall.png')

		self.state = 's-wall'
		self.action = 'stay'

		self.text_surface_objs = []
		self.text_rect_objs = []

		self.timer_start = datetime.datetime.now()
		self.inventory = []
		self.walls = {'n-wall':[['', ''], ['', '', '']], 'e-wall':[['', ''], ['', '', '']], 's-wall':[['', ''], ['', '', '']],
			'w-wall':[['', ''], ['', '', '']]}
		self.win = False
		self.right_code = str(random.randint(100, 999))

		# twitch IRC
		self.s = chat_connect.openSocket()
		chat_connect.joinRoom(self.s)
		self.readbuffer = ""


	def map_components(self): # strings components together in a path to exit

		self.components_to_place = ['cipher-chest', 'cipher-painting', 'door', 'bed']

		if 'cipher-chest' in self.components_to_place:
			self.setup_cipher()

		# ensure there are enough spaces on walls when choosing components


	def place_components(self): # puts components on wall (for drawing)

		# define all components
		self.components = { 'n-wall': Component([0, 0, 0], {'left':'w-wall', 'right':'e-wall'}),
							'e-wall': Component([0, 0, 0], {'left':'n-wall', 'right':'s-wall'}),
							's-wall': Component([0, 0, 0], {'left':'e-wall', 'right':'w-wall'}),
							'w-wall': Component([0, 0, 0], {'left':'s-wall', 'right':'n-wall'}),
							'cipher-chest': Component([0, 0, 2], {}),
							'cipher-painting': Component([0, 0, 1], {}),
							'door': Component([0, 0, 1], {'keypad':'keypad'}),
							'bed': Component([0, 0, 2], {}),
							'keypad': Component([0, 0, 0], {'back': 'door', self.right_code: 'outside'}),
							'simon-says': Component([0, 0, 2], {})
						  }

		cnt = 0
		for component in self.components_to_place:
			not_done_placing_component = True
			while not_done_placing_component:
				random_wall = random.choice(['n-wall', 'e-wall', 's-wall', 'w-wall'])
				if self.components[component].image_placement[2] == 1: # if component is to be placed on wall
					self.walls[random_wall][0][random.choice([spot for spot in [0,1] if self.walls[random_wall][0][spot] == ''])] = component
					self.components[random_wall].actions[component] = component
					self.components[component].on_wall = random_wall
					not_done_placing_component = False
				if self.components[component].image_placement[2] == 2: # if component is to be placed in front of wall
					self.walls[random_wall][1][random.choice([spot for spot in [0,2] if self.walls[random_wall][1][spot] == ''])] = component
					self.components[random_wall].actions[component] = component
					self.components[component].on_wall = random_wall
					not_done_placing_component = False
				cnt += 1
				if cnt > 50: # in case of unexpected endless loop
					print('------------something unexpected: breaking!!')
					break
		print(self.walls)

		for component in self.components: # add the back option for components
			self.components[component].actions['back'] = self.components[component].on_wall



	def main(self):
		""""This executes the game and controls its flow."""

		# setup
		pygame.init()
		pygame.display.set_caption(self.caption)
		self.map_components()
		self.place_components()

		while True: # main game loop
			self.event_loop()
			self.update_display()


	def event_loop(self):
		"""
		The event loop. This is where events are triggered
		(like a mouse click) and then effect the game state.
		"""

		for event in pygame.event.get():

			t = threading.Thread(target = self.update_state)
			t.daemon = True
			t.start()

			if event.type == QUIT:
				pygame.quit()
				sys.exit


	def update_state(self):

		### Determine possible actions

		always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall']
		possible_actions = []
		for component in self.components:
			if self.state == component:
				possible_actions = self.components[component].actions.keys()
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
		#self.action = raw_input('next action? ') # for working offline
		self.action = self.parse_twitch_chat(possible_actions)

		### Update state based on action
		if self.action in possible_actions:
			for component in self.components:
				if self.state == component:
					print('attempting {} from {}'.format(self.action, self.state))
					print(self.components[component].actions)
					self.state = self.components[component].actions[self.action]
					print('moved to: {}'.format(self.state))
					break

		if self.state == 'outside':
			self.win = True


	def update_display(self):

		self.screen.blit(self.background, (0,0))

		time.sleep(0.15)

		for i, text_surface_obj in enumerate(self.text_surface_objs):
			self.screen.blit(self.text_surface_objs[i], self.text_rect_objs[i])

		if 'wall' in self.state:
			self.background = pygame.image.load('pics/{}.png'.format(self.state))
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
			for i, letter in enumerate(self.painting_text): # this needs to be more complicated for
				char = pygame.image.load('pics/letter-{}-medium.png'.format(letter))
				self.background.blit(char, (240.5 + i * 88, 125))

		elif self.state == 'simon-says':
			self.background = pygame.image.load('pics/simon-says-full.png')
			time.sleep(2)
			for color in self.simon_says_pattern:
				self.background = pygame.image.load('pics/simon-says-full-{}.png'.format(color))
				time.sleep(0.8)
			self.background = pygame.image.load('pics/simon-says-full.png')

		else:
			self.background = pygame.image.load('pics/{}-full.png'.format(self.state))

		self.draw_message('Action is: {}'.format(self.action), [400, 800])
		self.draw_message('Timer: {}'.format(datetime.datetime.now() - self.timer_start), [400, 20])

		pygame.display.update()
		self.clock.tick(self.fps)


	def draw_message(self, message, coord = [100, 100]):
		font_obj = pygame.font.Font('freesansbold.ttf', 24)
		self.text_surface_objs.append(font_obj.render(message, True, HIGH, BLACK))
		self.text_rect_objs.append(self.text_surface_objs[-1].get_rect())
		self.text_rect_objs[-1].center = (coord[0], coord[1])


	def get_twitch_chat(self): # returns ten seconds of twitch chat

		if datetime.datetime.now() - self.timer_start > datetime.timedelta(0, 15, 0):
			self.timer_start = datetime.datetime.now()

		messages = []

		while datetime.datetime.now() - self.timer_start < datetime.timedelta(0, 15, 0):
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
		#print(chat)

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


	def setup_cipher(self):

		self.cipher_number = random.randint(1, 24)

		self.chest_text = random.choice(['ghost', 'booms', 'tally', 'rando', 'night', 'sleep', 'santa', 'could', 'alone', 'happy'])
		self.chest_cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.chest_text])

		#self.painting_text = 'an investment in knowledge pays the best interest.' #benjamin franklin
		self.painting_text = 'test'
		self.painting_cipher_text = ''.join([chr((ord(x) - 96 + self.cipher_number) % 26 + 1 + 96) if x.isalpha() else x for x in self.painting_text])

		print('CIPHER: ',self.cipher_number, self.chest_cipher_text)


	def setup_simon_says(self):

		self.simon_says_pattern = [random.choice(['blue','red','green','yellow']) for _ in range(5)]
		print(self.simon_says_pattern)
		self.simon_says_current_pattern = []
		self.simon_says_user_guess = []


def main():
	game = Game()
	game.main()

if __name__ == "__main__":
	main()
