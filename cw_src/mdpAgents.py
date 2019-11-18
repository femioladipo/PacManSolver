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
        min_ghost_distance (int): Minimum manhattan distance from point to a ghost.
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

    def __init__(self, utility=None, type=States.EMPTY):
        '''
        Args:
            utility (int): Initial utility.
            type (States): Initial type.
        '''
        self.__utility = utility
        self.type = type
        self.min_ghost_distance = Grid.MAX_DISTANCE

    def __copy__(self):
        return Point(utility=self.utility, type=self.type)

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
        if self.type == States.WALL:
            return Point.REWARDS[self.type]

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

    Attributes:
        height (int): Height of the grid.
        width (int): Width of the grid.
    '''

    # Height of grid
    HEIGHT = 0
    # Width of grid
    WIDTH = 0
    # Maximum distance between any two points the board
    MAX_DISTANCE = 0
    # Number of filled spaces on the board
    FILL_COUNT = 0

    def __init__(self):
        '''
        Instantiates a grid of size Grid.Height * Grid.Width, or size 0 if either Grid.Height or
        Grid.Width doesn't exist.
        '''
        self.__grid = {
            (x, y): Point() for y in xrange(Grid.HEIGHT) for x in xrange(Grid.WIDTH)
        }

    @staticmethod
    def size():
        '''
        Returns:
            Integer value representing number points on the grid.
        '''
        return Grid.HEIGHT * Grid.WIDTH

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
        Grid.FILL_COUNT = 0

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
            States.GHOST_HOSTILE: [ghost for ghost, time in ghosts_with_times if time <= Grid.GHOST_RADIUS],
            States.GHOST_EDIBLE: [ghost for ghost, time in ghosts_with_times if time > Grid.GHOST_RADIUS],
        }

        for type, coords in points.items():
            for x, y in coords:
                Grid.FILL_COUNT += 1
                self[x, y].type = type
                if type != States.WALL:
                    self[x, y].min_ghost_distance = Point.min_distance(
                        x, y, ghosts
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
        Uses Richard's Curve to distribute x over the open interval (0.7, 1) in a sigmoid curve.
        Then set's gamma to this value.
        '''
        K = 0.9  # upper asymptote
        A = 0.7  # lower asymptote
        B = -0.1  # growth rate
        M = 5  # growth area midpoint
        cls.GAMMA = A + (K-A) / (1 + exp(-B*(x-M)))

    @staticmethod
    def registerInitialState(state):
        '''
        Sets Grid and Points classes static constants dependant on state.

        Args:
            state: Current game state.
        '''
        Grid.HEIGHT = max([h for _, h in api.corners(state)]) + 1
        Grid.WIDTH = max([w for w, _ in api.corners(state)]) + 1
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
        grid = Grid.from_state(state)

        grid = cls.value_iteration(grid)

        x, y = api.whereAmI(state)

        legal = api.legalActions(state)

        return api.makeMove(direction=cls.policy(x, y, grid, legal), legal=legal)

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
        iterations = 0
        while iterations < MDPAgent.ITERATION_LIMIT:
            grid_copy = deepcopy(grid)

            for x in xrange(grid.WIDTH):
                for y in xrange(grid.HEIGHT):
                    if grid[x, y].type != States.WALL and \
                            grid[x, y].type != States.GHOST_HOSTILE and \
                            grid[x, y].type != States.GHOST_NEIGHBOUR:
                        grid_copy[x, y].utility = grid[x, y].reward + \
                            cls.GAMMA * \
                            cls.maximum_expected_utility(x, y, grid)

            grid = grid_copy

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
                new_position = grid[x+dx, y+dy]
                EU_values[main_direction] += prob * (
                    new_position.utility if new_position.type != States.WALL else position.utility
                )

        return EU_values
