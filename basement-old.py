from PIL import Image



inventory = []

state = 'n-wall'

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

win = False
state = 's-wall'
print('The South wall. There\'s a bed.')

right_code = '423'

# basement
while win == False:
    action = raw_input('What is the action: ')

    always_actions = ['n-wall', 'e-wall', 'w-wall', 's-wall']

    if state == 'n-wall':
        possible_actions = ['turn-left', 'turn-right', 'chest']
    elif state == 'e-wall':
        possible_actions = ['turn-left', 'turn-right', 'painting']
    elif state == 's-wall':
        possible_actions = ['turn-left', 'turn-right', 'bed']
    elif state == 'w-wall':
        possible_actions = ['turn-left', 'turn-right', 'door']
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

    if action in possible_actions:
        if state == 'n-wall':
            if action == 'turn-left':
                state = 'w-wall'
            elif action == 'turn-right':
                state = 'e-wall'
            elif action == 'chest':
                state = 'chest'
        elif state == 'e-wall':
            if action == 'turn-left':
                state = 'n-wall'
            elif action == 'turn-right':
                state = 's-wall'
            elif action == 'painting':
                state = 'painting'
        elif state == 's-wall':
            if action == 'turn-left':
                state = 'e-wall'
            elif action == 'turn-right':
                state = 'w-wall'
            elif action == 'bed':
                state = 'bed'
        elif state == 'w-wall':
            if action == 'turn-left':
                state = 's-wall'
            elif action == 'turn-right':
                state = 'n-wall'
            elif action == 'door':
                state = 'door'
        elif state == 'bed':
            if action == 'back':
                state = 's-wall'
        elif state == 'door':
            if action == 'keypad':
                state = 'keypad'
            elif action == 'back':
                state = 'w-wall'
        elif state == 'painting':
            if action == 'back':
                state = 'e-wall'
        elif state == 'chest':
            if action == 'back':
                state = 'n-wall'
        elif state == 'keypad':
            if action == 'back':
                state = 'door'
            elif action == right_code:
                win = True

        print('action: {}'.format(action))

    if state == 'n-wall':
        image = Image.open('n-wall.jpg')
        image.show()
    elif state == 'e-wall':
        print('The East wall. There\'s a painting.')
    elif state == 's-wall':
        print('The South wall. There\'s a bed.')
    elif state == 'w-wall':
        print('The West wall. There\'s a door.')
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



print('\nYou\'re free yay!')
