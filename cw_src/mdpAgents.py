from copy import deepcopy, copy
from collections import defaultdict
from math import exp, sqrt, tanh

from pacman import Directions
from game import Agent
import api
import random
import game
import util


class States(object):
    '''
    Enum of possible board point states.
    '''
    PACMAN = 'PACMAN'
    EMPTY = 'EMPTY'
    WALL = 'WALL'
    CAPSULE = 'CAPSULE'
    FOOD = 'FOOD'
    GHOST_NEIGHBOUR = 'GHOST_NEIGHBOUR'
    GHOST_EDIBLE = 'GHOST_EDIBLE'
    GHOST_HOSTILE = 'GHOST_HOSTILE'


class Point(object):
    '''
    A single point on the board.

    Attributes:
        type (States): Current type, discribing the state of the point.
        reward (float): Current reward value of this point dependent on current type.
        utility (float): Current utility value of this point.
        min_ghost_distance (int): 
    '''

    # Reward value for each state
    REWARDS = {
        # Neutral rewards
        States.WALL: 0,
        # Negative rewards
        States.EMPTY: -0.04,
        States.PACMAN: -0.04,
        States.GHOST_HOSTILE: -5,
        States.GHOST_EDIBLE: -2,
        States.GHOST_NEIGHBOUR: -2,
        # Positive rewards
        States.CAPSULE: 5,
        States.FOOD: 2,
    }
    # # Number of filled spaces on the board
    # FILL_COUNT = 0
    # # Scaling factor in reward function
    # GRID_SIZE = 1
    # # Maximum distance between any two points the board
    # MAX_DISTANCE = 0
    # # Radius around a ghost pacman should avoid
    # GHOST_RADIUS = 1

    def __init__(self, utility=None, type=States.EMPTY):
        '''
        Args:
            utility (int): Initial utility.
            type (States): Initial type.
        '''
        self.__utility = utility
        self.__type = type
        # self.min_ghost_distance = Point.MAX_DISTANCE

    def __copy__(self):
        return Point(utility=self.utility, type=self.__type)

    @property
    def utility(self):
        '''
        Returns:
            Floating point number representing the points current utility
            if set,  otherwise  returns the  default reward.
        '''
        if self.__utility is None:
            return self.reward
        else:
            return self.__utility

    @utility.setter
    def utility(self, value):
        self.__utility = value

    @property
    def type(self):
        '''
        Returns:
            String at out States enum, representing current state.  However, if
            the  point is less than the ghost radius units away from any ghost,
            the state  is overridden with States.GHOST_NEIGHBOUR.
        '''
        # if self.__type != States.WALL and \
        #         self.__type != States.GHOST_HOSTILE and \
        #         self.min_ghost_distance <= Point.GHOST_RADIUS:
        #     return States.GHOST_NEIGHBOUR

        return self.__type

    @type.setter
    def type(self, value):
        self.__type = value

    @property
    def reward(self):
        '''
        Will calculate the dynamic reward value if type is food, otherwise will return the default
        reward value (defined statically on the class) for all other types.

            Dynamic Reward - FOOD
            reward(f, gd) = d * e^(s - f / s) * e^(gd / md)
            where:
                d = default reward value
                f = number of filled spaces
                s = height * width
                gd = minimum distance to a ghost
                md = maximum distance of two board points

            Dynamic Reward - NOT FOOD
            reward(gd) = d / e^(gd / md)
            where:
                d = default reward value
                gd = minimum distance to a ghost
                md = maximum distance of two board points

        Returns:
            Float representing the points current reward value.
        '''
        # if self.type == States.WALL:
        #     return Point.REWARDS[States.WALL]

        # if self.type == States.FOOD:
        #     return Point.REWARDS[States.FOOD] * exp((Point.GRID_SIZE - Point.FILL_COUNT) / Point.GRID_SIZE) * exp(self.min_ghost_distance / Point.MAX_DISTANCE)

        # return Point.REWARDS[self.type] / exp(self.min_ghost_distance / Point.MAX_DISTANCE)
        return Point.REWARDS[self.type]

    # @staticmethod
    # def min_distance(x, y, items):
    #     '''
    #     Finds which item in the list of items is closest to (x, y), according
    #     to manhattan distance. Then returns the  distance between the closest
    #     item and (x, y).

    #     Args:
    #         x (int): X-coordinate of point
    #         y (int): Y-coordinate of point
    #         items (list): List of coordinates

    #     Returns:
    #         An integer representing the distance between closest item and (x, y).
    #     '''
    #     return min([util.manhattanDistance((x, y), item) for item in items])


class Grid(object):
    '''
    Abstraction of a 2D array, used the store all the positions in the game.

    Attributes:
        height (int): Height of the grid.
        width (int): Width of the grid.
    '''

    # Height of grid
    HEIGHT = 0
    # Width of grid
    WIDTH = 0

    def __init__(self):
        '''
        Instantiates a grid of size Grid.Height * Grid.Width, or size 0 if either Grid.Height or
        Grid.Width doesn't exist.
        '''
        self.__grid = {
            (x, y): Point() for y in xrange(Grid.HEIGHT) for x in xrange(Grid.WIDTH)
        }

    def __deepcopy(self, memo):
        grid_copy = Grid()
        grid_copy._Grid__grid = {
            key: copy(point) for key, point in self.__grid.items()
        }
        return grid_copy

    @classmethod
    def from_state(cls, state):
        '''
        Instantiates a new grid from a game state, setting the relevant board elements.
        '''
        grid = cls()
        grid._Grid__update_positions(state)
        return grid

    def __getitem__(self, pos):
        return self.__grid[pos]

    def __update_positions(self, state):
        '''
        Repaints the grid according to the passed in state. Updating the position of pacman,
        the ghosts, the food, the capsules, and the blank spaces.

        In addition calculates the number of filled spaces and stores this value statically
        on Point, for later use in the reward function.

        Args:
            state: Current game state.
        '''
        # Point.FILL_COUNT = 0

        ghosts_with_times = [
            ((int(x), int(y)), time) for (x, y), time in api.ghostStatesWithTimes(state)
        ]
        ghosts = [ghost for ghost, _ in ghosts_with_times]
        ghost_times = [time for _, time in ghosts_with_times]

        points = {
            States.PACMAN: [api.whereAmI(state)],
            States.WALL: api.walls(state),
            States.FOOD: api.food(state),
            States.CAPSULE: api.capsules(state),
            States.GHOST_HOSTILE: ghosts,
            # States.GHOST_HOSTILE: [ghost for ghost, time in ghosts_with_times if time <= Point.GHOST_RADIUS],
            # States.GHOST_EDIBLE: [ghost for ghost, time in ghosts_with_times if time > Point.GHOST_RADIUS],
        }

        for type, coords in points.items():
            for x, y in coords:
                self[x, y].type = type
                if type != States.WALL:
                    pass
                    # self[x, y].min_ghost_distance = Point.min_distance(
                    #     x, y, ghosts
                    # )

                    # Point.FILL_COUNT += 1

                    # MDPAgent.GAMMA = tanh(Point.FOOD_COUNT) / 2


class MDPAgent(Agent):
    '''
    The MDPAgent the calculates the new utility values, using value interation
    on every game step. In addition, pick the best next move dependent on the
    resulting utility values.
    '''

    # Convergence threshold
    THRESHOLD = 0.01
    # Convergence iteration limit
    # ITERATION_LIMIT = 15
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

    @staticmethod
    def registerInitialState(state):
        '''
        Sets Grid and Points classes static constants dependant on state.

        Args:
            state: Current game state.
        '''
        Grid.HEIGHT = max([h for _, h in api.corners(state)]) + 1
        Grid.WIDTH = max([w for w, _ in api.corners(state)]) + 1
        # Point.GRID_SIZE = Grid.HEIGHT * Grid.WIDTH
        # Point.MAX_DISTANCE = Grid.HEIGHT + Grid.WIDTH - 4
        # MDPAgent.ITERATION_LIMIT = sqrt(Grid.HEIGHT * Grid.WIDTH)

    @classmethod
    def getAction(cls, state):
        '''
        Picks the best next move dependent on state.

        Args:
            state: Current game state.

        Returns:
            A direction representing where pacman should move next.
        '''
        grid = Grid.from_state(state)

        grid = cls.value_iteration(grid)

        x, y = api.whereAmI(state)

        legal = api.legalActions(state)

        move = cls.calculate_MEU(x, y, grid, legal, value=False)

        return api.makeMove(move, legal)

    @classmethod
    def value_iteration(cls, grid):
        '''
        Calculates a sets new utility values for every point on the grid, repeating
        until new utility values converge within MDPAgent.Threshold.

        Args:
            grid (Grid): Grid representing the game state.

        Returns:
            A new grid containting updated utility values by performing value iteration
            on each point.
        '''
        # threshold_break = False
        # iterations = 0
        while True:
            changes = False
            grid_copy = deepcopy(grid)

            for x in xrange(grid.WIDTH):
                for y in xrange(grid.HEIGHT):
                    if grid[x, y].type != States.WALL and \
                        grid[x, y].type != States.GHOST_HOSTILE and \
                            grid[x, y].type != States.GHOST_NEIGHBOUR:
                        #         grid[x, y].type != States.FOOD:
                        utility = grid[x, y].reward + \
                            cls.GAMMA * cls.calculate_MEU(x, y, grid)

                        grid_copy[x, y].utility = utility

                        if abs(grid[x, y].utility - grid_copy[x, y].utility) > cls.THRESHOLD:
                            changes = True

            grid = grid_copy

            if not changes:
                # threshold_break = True
                break
            # else:
            #     iterations += 1

        # print 'threshold break at: ' + \
        #     str(iterations) if threshold_break else 'iteration break'
        return grid

    @classmethod
    def calculate_MEU(cls, x, y, grid, legal=[], value=True):
        '''
        Calculates and returns the maximum expected utility at (x, y).

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            grid (Grid): Grid representing the game state.
            legal (list): List of legal moves from current position
            value (bool): Boolean value True if returning MEU value, False if
                returning the corresponding move.

        Returns:
            Floating point number representing maximum expected utility.
        '''
        EU_values = defaultdict(int)
        position = grid[x, y]

        for main_direction, displacement in cls.DIRECTIONS.items():
            if not legal or main_direction in legal:
                main_direction_prob = [(displacement, api.directionProb)]
                non_deterministic_directions_prob = [
                    (cls.DIRECTIONS[direction], (1-api.directionProb)/2) for direction in cls.NON_DETERMINISTIC_DIRECTIONS[main_direction]
                ]
                for (dx, dy), prob in main_direction_prob + non_deterministic_directions_prob:
                    new_position = grid[x+dx, y+dy]
                    EU_values[main_direction] += prob * (
                        new_position.utility if new_position.type != States.WALL else position.utility
                    )

        if value:
            return max(*EU_values.values())
        else:
            return max(EU_values.items(), key=lambda kv: kv[1])[0]

    def final(self, state):
        pass
