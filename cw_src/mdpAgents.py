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
    GHOST_NEIGHBOUR = 'GHOST_NEIGHBOUR'
    GHOST_EDIBLE = 'GHOST_EDIBLE'
    GHOST_HOSTILE = 'GHOST_HOSTILE'


class Point:
    '''
    A single point on the board.

    Attributes:
        type (States): Current type, discribing the state of the point.
        reward (float): Current reward value of this point dependent on current type.
        utility (float): Current utility value of this point.
    '''

    # Reward value for each state
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

    def __init__(self, utility=None, type=States.SPACE):
        '''
        Args:
            utility (int): Initial utility.
            type (States): Initial type.
        '''
        self.__utility = utility
        self.type = type

    def __getattr__(self, key):
        if key == 'reward':
            return Point.REWARDS[self.type]
        if key == 'utility':
            if self.__utility is None:
                return Point.REWARDS[self.type]
            else:
                return self.__utility

    def __copy__(self):
        return Point(utility=self.utility, type=self.type)

    def __str__(self):
        if self.type == States.PACMAN:
            return 'p - ' + str(self.utility)
        elif self.type == States.GHOST_HOSTILE:
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
        self.__grid = {
            (x, y): fn() for y in xrange(self.__HEIGHT) for x in xrange(self.__WIDTH)
        }

    def __getitem__(self, (x, y)):
        return self.__grid[x, y]

    def __getattr__(self, attr):
        if attr == 'height':
            return self.__HEIGHT
        if attr == 'width':
            return self.__WIDTH

    def __deepcopy__(self, memo):
        grid = Grid(fn=self.__FN, height=self.__HEIGHT, width=self.__WIDTH)
        grid._Grid__grid = {
            (x, y): copy(self[x, y]) for y in xrange(self.__HEIGHT) for x in xrange(self.__WIDTH)
        }
        return grid

    def __str__(self):
        res = ''

        sorted_grid = sorted(self.__grid)

        for i in range(self.__WIDTH):
            res += '\n' + ''.join(['{:20}'.format(
                str(self[pos])) for pos in sorted_grid[i*self.__HEIGHT:(i+1)*self.__HEIGHT]]
            )

        return '\n' + res + '\n'

    def is_valid_position(self, x, y):
        '''
        Checks if position (x, y) is contained within the limits of the grid.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.

        Returns:
            True if (x,y) is within the grid, or False otherwise.
        '''
        try:
            self[x, y]
        except KeyError:
            return False
        return True

    def update(self, state):
        '''
        Repaints the grid according to the passed in state. Updating the position of pacman,
        the ghosts, the food, the capsules, and the blank spaces.

        Args:
            state: Current game state.
        '''
        self.__grid = {
            (x, y): self.__FN() for y in xrange(self.__HEIGHT) for x in xrange(self.__WIDTH)
        }

        x, y = api.whereAmI(state)
        self[x, y].type = States.PACMAN

        for x, y in api.walls(state):
            self[x, y].type = States.WALL

        for x, y in api.food(state):
            self[x, y].type = States.FOOD

        for x, y in api.capsules(state):
            self[x, y].type = States.CAPSULE

        for (x, y), timer in api.ghostStatesWithTimes(state):
            x, y = int(x), int(y)
            if timer < 2:
                self[x, y].type = States.GHOST_HOSTILE
                for dx in xrange(-1, 2):
                    for dy in xrange(-1, 2):
                        if dx == dy == 0:
                            continue
                        if self.__grid[x+dx, y+dy].type != States.WALL:
                            self.__grid[x+dx, y +
                                        dy].type = States.GHOST_NEIGHBOUR
                        # else:
                        #     new_x, new_y = x+(dx*2),y+(dy*2)
                        #     if self.__is_valid_position(new_x, new_y) and self.__grid[new_x, new_y].type != States.WALL:
                        #         self.__grid[new_x, new_y].type = States.GHOST_NEIGHBOUR
            else:
                self[x, y].type = States.GHOST_EDIBLE


class MDPAgent(Agent):
    '''
    The MDPAgent the calculates the new utility values, using value interation
    on every game step. In addition, pick the best next move dependent on the
    resulting utility values.
    '''

    # Convergence threshold
    THRESHOLD = 0.001
    # Gamma value in bellman equation
    GAMMA = 0.9
    # Directions mapped to displacement
    DIRECTIONS = {
        Directions.NORTH: (0, 1),
        Directions.EAST: (1, 0),
        Directions.SOUTH: (0, -1),
        Directions.WEST: (-1, 0)
    }
    # Directions mapped to list of left and right directions
    NON_DETERMINISTIC_DIRECTIONS = {
        Directions.NORTH: [Directions.EAST, Directions.WEST],
        Directions.EAST: [Directions.NORTH, Directions.SOUTH],
        Directions.SOUTH: [Directions.EAST, Directions.WEST],
        Directions.WEST: [Directions.NORTH, Directions.SOUTH]
    }

    def registerInitialState(self, state):
        '''
        Instantiates initial grid based on game state.

        Args:
            state: Current game state.
        '''
        height = max([h for _, h in api.corners(state)]) + 1
        width = max([w for w, _ in api.corners(state)]) + 1
        self.__grid = Grid(fn=Point, height=height, width=width)
        # MDPAgent.gamma = 0.7 if (11, 20) == (height, width) else 0.9

    def getAction(self, state):
        '''
        Picks the best next move dependent on state.

        Args:
            state: Current game state.

        Returns:
            A direction representing where pacman should move next.
        '''
        self.__grid.update(state)

        self.__value_iteration()

        x, y = api.whereAmI(state)

        legal = api.legalActions(state)

        moves = [
            (direction, self.__grid[x+dx, y+dy].utility)
            for direction, (dx, dy) in MDPAgent.DIRECTIONS.items() if direction in legal
        ]

        move = max(moves, key=lambda kv: kv[1])[0]

        return api.makeMove(move, legal)

    def __value_iteration(self):
        '''
        Calculates a sets new utility values for every point on the grid, repeating
        until new utility values converge within MDPAgent.Threshold.
        '''
        while True:
            changes = False
            grid_copy = deepcopy(self.__grid)

            for x in xrange(self.__grid.width):
                for y in xrange(self.__grid.height):
                    if self.__grid[x, y].type != States.WALL and \
                            self.__grid[x, y].type != States.GHOST_HOSTILE and \
                            self.__grid[x, y].type != States.GHOST_NEIGHBOUR:
                        utility = self.__grid[x, y].reward + \
                            MDPAgent.GAMMA * self.__calculate_MEU(x, y)

                        grid_copy[x, y].utility = utility

                        if abs(self.__grid[x, y].utility - grid_copy[x, y].utility) > MDPAgent.THRESHOLD:
                            changes = True

            self.__grid = grid_copy

            if not changes:
                break

    def __calculate_MEU(self, x, y):
        '''
        Calculates and returns the maximum expected utility at (x, y).

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.

        Returns:
            Floating point number representing maximum expected utility.
        '''
        EU_values = defaultdict(int)
        position = self.__grid[x, y]

        for main_direction, displacement in MDPAgent.DIRECTIONS.items():
            main_direction_prob = [(displacement, api.directionProb)]
            non_deterministic_directions_prob = [
                (MDPAgent.DIRECTIONS[direction], (1-api.directionProb)/2) for direction in MDPAgent.NON_DETERMINISTIC_DIRECTIONS[main_direction]
            ]
            for (dx, dy), prob in main_direction_prob + non_deterministic_directions_prob:
                new_position = self.__grid[x+dx, y+dy]
                EU_values[main_direction] += prob * (
                    new_position.utility if new_position.type != States.WALL else position.utility)

        return max(*EU_values.values())

    def final(self, state):
        pass
