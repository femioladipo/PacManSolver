from copy import deepcopy
from collections import defaultdict
from math import exp, sqrt, ceil
from re import sub

from pacman import Directions
from game import Agent, Actions
import api
import util


################## Fixing camel casing to comply with PEP8 ####################
def snake_to_camel(term):
    '''
    Converts a snake case string to a camel case version of the same string.

    Args:
        term (str): Word to camel case

    Returns:
        Camel cased version of term
    '''
    return ''.join(item if i == 0 else item.capitalize() for i, item in enumerate(term.split('_')))


def camel_to_snake(term):
    '''
    Converts a camel case string to a snake case version of the same string.

    Args:
        term (str): Word to snake case

    Returns:
        Snake cased version of term
    '''
    tmp = sub('(.)([A-Z][a-z]+)', r'\1_\2', term)
    return sub('([a-z0-9])([A-Z])', r'\1_\2', tmp).lower()


def camel_case(original):
    '''
    Used on a class to alias every method with a camel case version.
    '''
    for name, method_or_value in original.__dict__.copy().iteritems():
        setattr(original, snake_to_camel(name), method_or_value)
    return original


def snake_case(original):
    '''
    Used on a class to alias every method with a snake case version.
    '''
    for name, method_or_value in original.__dict__.copy().iteritems():
        setattr(original, camel_to_snake(name), method_or_value)
    return original


snake_case(util)
snake_case(api)
###############################################################################


class Coordinate(tuple):
    '''
    Tuple wrapper ensuring: size is 2, x & y are ints and enabling easy addition.
    For example: Tuple[int, int]
    '''
    def __new__(cls, x, y):
        return super(Coordinate, cls).__new__(cls, (int(x), int(y)))

    def __add__(self, other):
        return Coordinate(x=self[0]+other[0], y=self[1]+other[1])

    def __deepcopy__(self, memo):
        return Coordinate(x=self[0], y=self[1])


class Dispositions(object):
    '''
    Enum of possible board point states.
    '''
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
        disposition (Dispositions): Current disposition, discribing the state of the point.
        reward (float): Current reward value of this point dependent on current disposition.
        utility (float): Current utility value of this point.
        min_ghost_distance (int): Minimum manhattan distance from point to a ghost.
    '''

    # Reward value for each state
    REWARDS = {
        # Negative rewards
        Dispositions.EMPTY: -0.04,
        Dispositions.GHOST_HOSTILE: -5,
        Dispositions.GHOST_EDIBLE: -2,
        Dispositions.GHOST_NEIGHBOUR: -2,
        # Positive rewards
        Dispositions.CAPSULE: 5,
        Dispositions.FOOD: 2,
    }

    def __init__(
            self,
            utility=None,
            disposition=Dispositions.EMPTY,
            min_ghost_distance=None,
        ):
        '''
        Args:
            utility (int): Initial utility.
            disposition (Dispositions): Initial disposition.
            min_ghost_distance (int): Manhattan distance to closest ghost
        '''
        self.__utility = utility
        self.__disposition = disposition
        self.__min_ghost_distance = min_ghost_distance

    def __copy__(self):
        return Point(
            utility=self.__utility,
            disposition=self.__disposition,
            min_ghost_distance=self.__min_ghost_distance,
        )

    @property
    def min_ghost_distance(self):
        '''
        Returns:
            Integer representing manhattan distance to closest ghost, or max 
            grid distance if not set.
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
    def disposition(self):
        '''
        Returns:
            String at out Dispositions enum, representing current state.  However, if
            the point is less than the ghost radius units away from any ghost,
            the state  is overridden with Dispositions.GHOST_NEIGHBOUR.
        '''
        if self.__disposition not in {Dispositions.GHOST_EDIBLE, Dispositions.GHOST_HOSTILE} and \
                self.min_ghost_distance <= Grid.GHOST_RADIUS:
            return Dispositions.GHOST_NEIGHBOUR

        return self.__disposition

    @disposition.setter
    def disposition(self, value):
        self.__disposition = value

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
        if self.disposition in {Dispositions.FOOD, Dispositions.CAPSULE}:
            return Point.REWARDS[self.disposition] * self.f_phi() / self.f_delta()

        return Point.REWARDS[self.disposition] * self.f_delta()

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
    def min_distance(coordinate, items):
        '''
        Finds which item in the list of items is closest to (x, y), according
        to manhattan distance. Then returns the  distance between the closest
        item and (x, y).

        Args:
            coordinate (Coordinate): (x, y) coordinate of the point
            items (list): List of coordinates

        Returns:
            An integer representing the distance between closest item and the coordinate.
        '''
        return min([util.manhattan_distance(coordinate, item) for item in items])


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
    GHOST_RADIUS = 1
    # Walls for the current grid
    WALLS = set()

    def __init__(self, state):
        '''
        Instantiates a grid of size Grid.Height * Grid.Width, or size 0 if
        either Grid.Height or Grid.Width doesn't exist. Setting the relevant 
        board points from the game state, 
        '''
        self.__grid = {
            Coordinate(x, y): Point()
            for y in range(Grid.HEIGHT) for x in range(Grid.WIDTH)
            if (x, y) not in Grid.WALLS
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
        '''
        Allows iteration through the coordinates and points of the grid,
        using the 'for coordinate, point in Grid' syntax.
        '''
        return self.__grid.iteritems()

    def __contains__(self, coordinate):
        '''
        Checks if coordinate is in the grid.

        Args:
            coordinate (Coordinate): (x,y) coordinates of position to check for.

        Returns:
            Bool that is true if coordinate is in the grid, or false otherwise.
        '''
        return coordinate in self.__grid

    def __update_positions(self, state):
        '''
        Repaints the grid according to the passed in state. Updating the 
        position of pacman, the ghosts, the food, the capsules, and the blank
        spaces.

        In addition calculates the number of filled spaces and stores this value
        statically on Point, for later use in the reward function.

        Args:
            state: Current game state.
        '''
        Grid.FILL_COUNT = 0

        points = {
            Dispositions.FOOD: api.food(state),
            Dispositions.CAPSULE: api.capsules(state),
            Dispositions.GHOST_HOSTILE: [
                ghost
                for ghost, time in api.ghost_states_with_times(state)
                if time <= Grid.GHOST_SAFE_TIME
            ],
            Dispositions.GHOST_EDIBLE: [
                ghost
                for ghost, time in api.ghost_states_with_times(state)
                if time > Grid.GHOST_SAFE_TIME
            ],
        }

        for disposition, coordinates in points.items():
            for x, y in coordinates:
                Grid.FILL_COUNT += 1
                coordinate = Coordinate(x, y)  # because ghost x, y are floats
                self[coordinate].disposition = disposition
                self[coordinate].min_ghost_distance = Point.min_distance(
                    coordinate, api.ghosts(state)
                )

        MDPAgent.set_gamma(len(api.food(state) + api.capsules(state)))


@camel_case
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
    # Probability for each displacement for each direction
    DIRECTION_PROBABILITIES = {
        direction: [(Actions._directions[direction], api.direction_prob)] +
        [(Actions._directions[Directions.LEFT[direction]], (1-api.direction_prob)/2)] +
        [(Actions._directions[Directions.RIGHT[direction]], (1-api.direction_prob)/2)]
        for direction in Actions._directions.iterkeys()
    }

    @classmethod
    def set_gamma(cls, x):
        '''
        Uses Richard's Curve to distribute x over the open interval (0.6, 1) in
        a sigmoid curve. Then set's gamma to this value.
        '''
        K = 1  # upper asymptote
        A = 0.6  # lower asymptote
        B = -0.1  # growth rate
        M = 5  # growth area midpoint
        cls.GAMMA = A + (K-A) / (1 + exp(-B*(x-M)))

    @staticmethod
    def register_initial_state(state):
        '''
        Sets Grid and Point classes' static constants dependant on state, and
        MDPAgent.ITERATION_LIMIT.

        Args:
            state: Current game state.
        '''
        Grid.HEIGHT = max([h for _, h in api.corners(state)]) + 1
        Grid.WIDTH = max([w for w, _ in api.corners(state)]) + 1
        if Grid.WIDTH > 7 and Grid.HEIGHT > 7:  # mediumClassic or bigger
            Grid.GHOST_RADIUS = 3
        Grid.MAX_DISTANCE = Grid.HEIGHT + Grid.WIDTH - 4
        Grid.WALLS = set(api.walls(state))
        MDPAgent.ITERATION_LIMIT = int(
            ceil(sqrt(Grid.HEIGHT * Grid.WIDTH)) * 2
        )

    @classmethod
    def get_action(cls, state):
        '''
        Picks the best next move dependent on state.

        Args:
            state: Current game state.

        Returns:
            A direction representing where pacman should move next.
        '''
        grid = Grid(state)

        grid = cls.__value_iteration(grid)

        coordinate = Coordinate(*api.where_am_i(state))

        legal = api.legal_actions(state)

        return api.make_move(direction=cls.__policy(grid, coordinate, legal), legal=legal)

    @classmethod
    def __value_iteration(cls, grid):
        '''
        Calculates and sets new utility values for every point on the grid,
        repeating until MDPAgent.ITERATION_LIMIT is reached.

        Args:
            grid (Grid): Grid representing the game state.

        Returns:
            A new grid containting updated utility values by performing value
            iteration on each point.
        '''
        for _ in range(MDPAgent.ITERATION_LIMIT):
            grid_copy = deepcopy(grid)

            for coordinate, point in grid:
                if point.disposition != Dispositions.GHOST_HOSTILE:
                    point.utility = point.reward + \
                        cls.GAMMA * \
                        cls.__maximum_expected_utility(grid_copy, coordinate)

        return grid

    @classmethod
    def __policy(cls, grid, coordinate, legal):
        '''
        Finds the best policy from position (x, y), that's also included in 
        legal moves.

        Args:
            coordinate (Coordinate): (x, y) coordinate of the point
            grid (Grid): Grid representing the game state.
            legal (list): List of legal moves from current position

        Returns:
            Direction representing the optimum policy from (x, y)
        '''
        return max([
            (utility, direction)
            for direction, utility in cls.__expected_utilities(grid, coordinate).iteritems()
            if direction in legal
        ])[1]

    @classmethod
    def __maximum_expected_utility(cls, grid, coordinate):
        '''
        Calculates and returns the maximum expected utility at (x, y).

        Args:
            coordinate (Coordinate): (x, y) coordinate of the point
            grid (Grid): Grid representing the game state.

        Returns:
            Floating point number representing maximum expected utility.
        '''
        return max(cls.__expected_utilities(grid, coordinate).values())

    @classmethod
    def __expected_utilities(cls, grid, coordinate):
        '''
        Calculates the expected utility for moving in each direction from (x, y).

        Args:
            coordinate (Coordinate): (x, y) coordinate of the point
            grid (Grid): Grid representing the game state.

        Returns:
            Dictionary mapping directions to their utility values.
        '''
        expected_utilities = defaultdict(int)

        for direction, probabilities in MDPAgent.DIRECTION_PROBABILITIES.iteritems():
            for displacement, probability in probabilities:
                if coordinate+displacement in grid:
                    expected_utilities[direction] += probability * \
                        grid[coordinate+displacement].utility
                else:
                    expected_utilities[direction] += probability * \
                        grid[coordinate].utility

        return expected_utilities
