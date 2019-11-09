from copy import deepcopy, copy
from collections import defaultdict

from pacman import Directions
from game import Agent
import api
import random
import game
import util


class States:
    '''
    Enum of possible board point states.
    '''
    PACMAN = 'PACMAN'
    SPACE = 'SPACE'
    WALL = 'WALL'
    CAPSULE = 'CAPSULE'
    FOOD = 'FOOD'
    GHOST = 'GHOST'
    GHOST_NEIGHBOUR = 'GHOST_NEIGHBOUR'
    GHOST_EDIBLE = 'GHOST_EDIBLE'
    GHOST_HOSTILE = 'GHOST_HOSTILE'


class Point:
    '''
    A single point on the board.

    Attributes:
        type (States): Current type, discribing the state of the point.
        reward (float): Current reward value of this point depedant on current type.
        utility (float): Current utility value of this point.
    '''

    REWARDS = {
        States.PACMAN: -0.04,
        States.SPACE: -0.04,
        States.WALL: 0,
        States.CAPSULE: 2,
        States.FOOD: 1,
        States.GHOST_EDIBLE: -2,
        States.GHOST_HOSTILE: -5,
        States.GHOST_NEIGHBOUR: -0.09
    }

    def __init__(self, utility=0, type=States.SPACE):
        '''
        Args:
            utility (int): Initial utility.
            type (States): Initial type.
        '''
        self.utility = utility
        self.type = type

    def __getattr__(self, key):
        if key == 'reward':
            return Point.REWARDS[self.type]
    
    def __copy__(self):
        return Point(utility=self.utility, type=self.type)

    def __str__(self):
        if self.type == States.PACMAN:
            return 'p - ' + str(self.utility)
        elif self.type == States.GHOST:
            return 'g - ' + str(self.utility)
        elif self.type == States.WALL:
            return '* - ' + str(self.utility)
        else:
            return str(self.utility)


class Grid:
    '''
    Abstraction of a 2D array, used the store all the positions in the game.

    Attributes:
        height (int): Height of the grid.
        width (int): Width of the grid.
    '''

    def __init__(self, fn, height, width):
        '''
        Args:
            fn: function that returns an object
            height (int): Final height of the grid.
            width (int): Final width of the grid.
        '''
        self.__FN = fn
        self.__HEIGHT = height
        self.__WIDTH = width
        self.__grid = [
            [fn() for _ in xrange(self.__HEIGHT)] for _ in xrange(self.__WIDTH)
        ]
    
    def __getitem__(self, key):
        return self.__grid[key]

    def __getattr__(self, attr):
        if attr == 'height':
            return self.__HEIGHT
        if attr == 'width':
            return self.__WIDTH

    def __deepcopy__(self, memo):
        grid = Grid(fn=self.__FN, height=self.__HEIGHT, width=self.__WIDTH)
        grid._Grid__grid = [
            [copy(point) for point in row] for row in self.__grid
        ]
        return grid

    def __str__(self):
        return '\n' + '\n'.join([''.join(['{:20}'.format(item) for item in row]) for row in self.__grid]) + '\n'

    def __is_valid_position(self, x, y):
        '''
        Checks if position (x, y) is contained within the limits of the grid.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.

        Returns:
            True if (x,y) is within the grid, or False otherwise.
        '''
        try:
            self.__grid[x][y]
        except IndexError:
            return False
        return True

    def update(self, state):
        '''
        Repaints the grid according to the passed in state. Updating the position of pacman,
        the ghosts, the food, the capsules, and the blank spaces.

        Args:
            state: Current game state.
        '''
        self.__grid = [
            [self.__FN() for _ in row] for row in self.__grid
        ]

        x, y = api.whereAmI(state)
        self.__grid[x][y].type = States.PACMAN

        for x, y in api.walls(state):
            self.__grid[x][y].type = States.WALL

        for x, y in api.food(state):
            self.__grid[x][y].type = States.FOOD

        for x, y in api.capsules(state):
            self.__grid[x][y].type = States.CAPSULE

        for (x, y), timer in api.ghostStatesWithTimes(state):
            x, y = int(x), int(y)
            if timer < 2:
                self.__grid[x][y].type = States.GHOST_HOSTILE
                # for dx in xrange(-1, 2):
                #     for dy in xrange(-1, 2):
                #         if self.__grid[x+dx][y+dy].type == States.WALL:
                #             new_x, new_y = x+(dx*2),y+(dy*2)
                #             if self.__is_valid_position(new_x, new_y) and self.__grid[new_x][new_y].type != States.WALL:
                #                 self.__grid[new_x][new_y].type = States.GHOST_NEIGHBOUR
            else:
                self.__grid[x][y].type = States.GHOST_EDIBLE

class MDPAgent(Agent):
    '''
    The MDPAgent the calculates the new utility values, using value interation
    on every game step. In addition, pick the best next move depedant on the
    resulting utility values.
    '''

    threshold = 0.00001
    gamma = 0.9
    DIRECTIONS = {
        Directions.NORTH: (0, 1),
        Directions.EAST: (1, 0),
        Directions.SOUTH: (0,-1),
        Directions.WEST: (-1, 0)
    }
    NON_DETERMINISTIC_DIRECTIONS = {
        Directions.NORTH: [Directions.EAST, Directions.WEST],
        Directions.EAST: [Directions.NORTH, Directions.SOUTH],
        Directions.SOUTH: [Directions.EAST, Directions.WEST],
        Directions.WEST: [Directions.NORTH, Directions.SOUTH]
    }

    def registerInitialState(self, state):
        '''
        Instatiates initial grid based on game state.

        Args:
            state: Current game state.
        '''
        height = max([h for w, h in api.corners(state)]) + 1
        width = max([w for w, h in api.corners(state)]) + 1
        self.__grid = Grid(fn=Point, height=height, width=width)
        # MDPAgent.gamma = 0.7 if (11, 20) == (height, width) else 0.9

    def getAction(self, state):
        '''
        Picks the best next move depedant on state.

        Args:
            state: Current game state.
        '''
        self.__grid.update(state)

        self.__value_iteration()
        
        x, y = api.whereAmI(state)

        legal = api.legalActions(state)

        moves = [
            (direction, self.__grid[x+dx][y+dy].utility)
            for direction, (dx, dy) in MDPAgent.DIRECTIONS.items() if direction in legal
        ]

        move = max(moves, key=lambda kv: kv[1])[0]

        return api.makeMove(move, legal)

    def __value_iteration(self):
        '''
        Calculates a sets new utlity values for every point on the grid, repeating
        until new utility values converge within MDPAgent.Threshold.
        '''
        while True:
            changes = False
            grid_copy = deepcopy(self.__grid)

            for x in xrange(self.__grid.width):
                for y in xrange(self.__grid.height):
                    if (self.__grid[x][y].type != States.WALL):
                        utility = self.__grid[x][y].reward + \
                            MDPAgent.gamma * self.__calculate_MEU(x, y)
            
                        grid_copy[x][y].utility = utility

                        if abs(self.__grid[x][y].utility - grid_copy[x][y].utility) > MDPAgent.threshold:
                            changes = True

            self.__grid = grid_copy

            if not changes:
                break

    def __calculate_MEU(self, x, y):
        '''
        Calcualtes the maximum expected utility at (x, y).

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
        '''
        EU_values = defaultdict(int)
        position = self.__grid[x][y]
        
        for main_direction, displacement in MDPAgent.DIRECTIONS.items():
            main_direction_prob = [(displacement, api.directionProb)]
            non_deterministic_directions_prob = [
                (MDPAgent.DIRECTIONS[direction], (1-api.directionProb)/2) for direction in MDPAgent.NON_DETERMINISTIC_DIRECTIONS[main_direction]
            ]
            for (dx, dy), prob in main_direction_prob + non_deterministic_directions_prob:
                new_position = self.__grid[x+dx][y+dy]
                EU_values[main_direction] += prob * (new_position.utility if new_position.type != States.WALL else position.utility)

        return max(*EU_values.values())

    def final(self, state):
        pass
