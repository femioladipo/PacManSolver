from copy import deepcopy
from collections import defaultdict
from math import exp, sqrt, ceil

from pacman import Directions
from game import Agent
import api
import util


class States(object):
    '''
    Enum of possible board point states.
    '''
    PACMAN = 'PACMAN'
    EMPTY = 'EMPTY'
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
        min_ghost_distance (int): Minimum manhattan distance from point to a ghost.
    '''

    # Reward value for each state
    REWARDS = {
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

    def __init__(self, utility=None, type=States.EMPTY, min_ghost_distance=None):
        '''
        Args:
            utility (int): Initial utility.
            type (States): Initial type.
            min_ghost_distance (int): Manhattan distance to closest ghost
        '''
        self.__utility = utility
        self.__type = type
        self.__min_ghost_distance = min_ghost_distance

    def __copy__(self):
        return Point(utility=self.__utility, type=self.__type, min_ghost_distance=self.__min_ghost_distance)

    @property
    def min_ghost_distance(self):
        '''
        Returns:
            Integer representing manhattan distance to closest ghost, or max grid distance
            if not set.
        '''
        if self.__min_ghost_distance is None:
            return Grid.MAX_DISTANCE
        else:
            return self.__min_ghost_distance

    @min_ghost_distance.setter
    def min_ghost_distance(self, value):
        self.__min_ghost_distance = value

    @property
    def utility(self):
        '''
        Returns:
            Floating point number representing the points current utility if
            set, otherwise returns the default reward.
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
            the point is less than the ghost radius units away from any ghost,
            the state  is overridden with States.GHOST_NEIGHBOUR.
        '''
        if self.__type not in {States.GHOST_EDIBLE, States.GHOST_HOSTILE} and \
                self.min_ghost_distance <= Grid.GHOST_RADIUS:
            return States.GHOST_NEIGHBOUR

        return self.__type

    @type.setter
    def type(self, value):
        self.__type = value

    @property
    def reward(self):
        '''
        Calculates and returns the shaped reward depending on the current state.

            Dynamic Reward - Positive
            reward(s) = d * f_phi / f_delta
            where:
                d = default reward value

            Dynamic Reward - Negative
            reward(s) = d * f_delta
            where:
                d = default reward value

        Returns:
            Float representing the points current reward value.
        '''
        if self.type in {States.FOOD, States.CAPSULE}:
            return Point.REWARDS[self.type] * self.f_phi() / self.f_delta()

        return Point.REWARDS[self.type] * self.f_delta()

    def f_delta(self):
        '''
        Returns:
            Value between 1 and e representing closeness to a ghost.
        '''
        return exp((Grid.MAX_DISTANCE - self.min_ghost_distance) / Grid.MAX_DISTANCE)

    @staticmethod
    def f_phi():
        '''
        Returns:
            Value between 1 and e representing ratio of empty space to filled space.
        '''
        return exp((Grid.size() - Grid.FILL_COUNT) / Grid.size())

    @staticmethod
    def min_distance(x, y, items):
        '''
        Finds which item in the list of items is closest to (x, y), according
        to manhattan distance. Then returns the  distance between the closest
        item and (x, y).

        Args:
            x (int): X-coordinate of point
            y (int): Y-coordinate of point
            items (list): List of coordinates

        Returns:
            An integer representing the distance between closest item and (x, y).
        '''
        return min([util.manhattanDistance((x, y), item) for item in items])


class Grid(object):
    '''
    Abstraction of a 2D array, used the store all the positions in the game.
    '''

    # Height of grid
    HEIGHT = 0
    # Width of grid
    WIDTH = 0
    # Maximum distance between any two points on the board
    MAX_DISTANCE = 0
    # Number of filled spaces on the board
    FILL_COUNT = 0
    # Amount of time remaining in edible mode, where ghosts are still considered safe
    GHOST_SAFE_TIME = 3
    # Radius around ghosts pacman should avoid
    GHOST_RADIUS = 0
    # Walls for the current grid
    WALLS = set()

    def __init__(self, state):
        '''
        Instantiates a grid of size Grid.Height * Grid.Width, or size 0 if either Grid.Height or
        Grid.Width doesn't exist.

        Instantiates a new grid from a game state, setting the relevant board elements.
        '''
        self.__grid = {
            (x, y): Point() for y in xrange(Grid.HEIGHT) for x in xrange(Grid.WIDTH) if (x, y) not in Grid.WALLS
        }
        self.__update_positions(state)

    @staticmethod
    def size():
        '''
        Returns:
            Integer value representing number points on the grid.
        '''
        return (Grid.HEIGHT * Grid.WIDTH) - len(Grid.WALLS)

    def __getitem__(self, coordinate):
        return self.__grid[coordinate]

    def __iter__(self):
        return self.__grid.iterkeys()

    def __contains__(self, coordinate):
        return coordinate in self.__grid

    def __update_positions(self, state):
        '''
        Repaints the grid according to the passed in state. Updating the position of pacman,
        the ghosts, the food, the capsules, and the blank spaces.

        In addition calculates the number of filled spaces and stores this value statically
        on Point, for later use in the reward function.

        Args:
            state: Current game state.
        '''
        Grid.FILL_COUNT = 0

        points = {
            States.PACMAN: [api.whereAmI(state)],
            States.FOOD: api.food(state),
            States.CAPSULE: api.capsules(state),
            States.GHOST_HOSTILE: [ghost for ghost, time in api.ghostStatesWithTimes(state) if time <= Grid.GHOST_SAFE_TIME],
            States.GHOST_EDIBLE: [ghost for ghost, time in api.ghostStatesWithTimes(state) if time > Grid.GHOST_SAFE_TIME],
        }

        for type, coords in points.items():
            for x, y in coords:
                x, y = map(int, [x, y])
                Grid.FILL_COUNT += 1
                self[x, y].type = type
                self[x, y].min_ghost_distance = Point.min_distance(
                    x, y, api.ghosts(state)
                )

        MDPAgent.set_gamma(len(api.food(state)) + len(api.capsules(state)))


class MDPAgent(Agent):
    '''
    The MDPAgent the calculates the new utility values, using value interation
    on every game step. In addition, pick the best next move dependent on the
    resulting utility values.
    '''

    # Convergence iteration limit
    ITERATION_LIMIT = 15
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

    @classmethod
    def set_gamma(cls, x):
        '''
        Uses Richard's Curve to distribute x over the open interval (0.6, 1) in a sigmoid curve.
        Then set's gamma to this value.
        '''
        K = 1  # upper asymptote
        A = 0.6  # lower asymptote
        B = -0.1  # growth rate
        M = 5  # growth area midpoint
        cls.GAMMA = A + (K-A) / (1 + exp(-B*(x-M)))

    @staticmethod
    def registerInitialState(state):
        '''
        Sets Grid and Point classes' static constants dependant on state, and
        MDPAgent.ITERATION_LIMIT.

        Args:
            state: Current game state.
        '''
        Grid.HEIGHT = max([h for _, h in api.corners(state)]) + 1
        Grid.WIDTH = max([w for w, _ in api.corners(state)]) + 1
        if Grid.WIDTH > 7 and Grid.HEIGHT > 7:
            Grid.GHOST_RADIUS = 3
        Grid.WALLS = set(api.walls(state))
        Grid.MAX_DISTANCE = Grid.HEIGHT + Grid.WIDTH - 4
        MDPAgent.ITERATION_LIMIT = ceil(sqrt(Grid.HEIGHT * Grid.WIDTH)) * 2

    @classmethod
    def getAction(cls, state):
        '''
        Picks the best next move dependent on state.

        Args:
            state: Current game state.

        Returns:
            A direction representing where pacman should move next.
        '''
        grid = Grid(state)

        grid = cls.value_iteration(grid)

        x, y = api.whereAmI(state)

        legal = api.legalActions(state)

        return api.makeMove(direction=cls.policy(x, y, grid, legal), legal=legal)

    @classmethod
    def value_iteration(cls, grid):
        '''
        Calculates and sets new utility values for every point on the grid, repeating
        until MDPAgent.ITERATION_LIMIT is reached.

        Args:
            grid (Grid): Grid representing the game state.

        Returns:
            A new grid containting updated utility values by performing value iteration
            on each point.
        '''
        iterations = 0

        while iterations < MDPAgent.ITERATION_LIMIT:
            grid_copy = deepcopy(grid)

            for (x, y) in grid:
                if grid[x, y].type != States.GHOST_HOSTILE:
                    grid[x, y].utility = grid[x, y].reward + \
                        cls.GAMMA * \
                        cls.maximum_expected_utility(x, y, grid_copy)

            iterations += 1

        return grid

    @classmethod
    def policy(cls, x, y, grid, legal):
        '''
        Finds the best policy from position (x, y), that's also included in legal moves.

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            grid (Grid): Grid representing the game state.
            legal (list): List of legal moves from current position

        Returns:
            Direction representing the optimum policy from (x, y)
        '''
        return max([
            (utility, direction) for (direction, utility) in cls.expected_utilities(x, y, grid).items() if direction in legal
        ])[1]

    @classmethod
    def maximum_expected_utility(cls, x, y, grid):
        '''
        Calculates and returns the maximum expected utility at (x, y).

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            grid (Grid): Grid representing the game state.

        Returns:
            Floating point number representing maximum expected utility.
        '''
        return max(cls.expected_utilities(x, y, grid).values())

    @classmethod
    def expected_utilities(cls, x, y, grid):
        '''
        Calculates the expected utility for moving in each direction from (x, y).

        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            grid (Grid): Grid representing the game state.

        Returns:
            Dictionary mapping directions to their utility values.
        '''
        EU_values = defaultdict(int)
        position = grid[x, y]

        for main_direction, displacement in cls.DIRECTIONS.items():
            main_direction_prob = [(displacement, api.directionProb)]
            non_deterministic_directions_prob = [
                (cls.DIRECTIONS[direction], (1-api.directionProb)/2) for direction in cls.NON_DETERMINISTIC_DIRECTIONS[main_direction]
            ]
            for (dx, dy), prob in main_direction_prob + non_deterministic_directions_prob:
                if (x+dx, y+dy) in Grid.WALLS:
                    EU_values[main_direction] += prob * position.utility
                else:
                    EU_values[main_direction] += prob * \
                        grid[x+dx, y+dy].utility

        return EU_values
