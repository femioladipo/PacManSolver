from copy import deepcopy, copy


from pacman import Directions
from game import Agent
import api
import random
import game
import util


class States:
    PACMAN = 'PACMAN'
    SPACE = 'SPACE'
    WALL = 'WALL'
    CAPSULE = 'CAPSULE'
    FOOD = 'FOOD'
    GHOST = 'GHOST'
    GHOST_NEIGHBOUR = 'GHOST_NEIGHBOUR'


class Point:
    reward = {
        States.PACMAN: -0.04,
        States.SPACE: -0.04,
        States.WALL: '*',
        States.CAPSULE: 2,
        States.FOOD: 1,
        States.GHOST: -1,
        States.GHOST_NEIGHBOUR: -1
    }

    def __init__(self, utility=0, type=States.SPACE):
        self.utility = utility
        self.type = type

    def get_reward(self):
        return Point.reward[self.type]

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
    def __init__(self, fn, height, width):
        # self.isPristine = True
        self.__fn = fn
        self.__height = height
        self.__width = width
        self.__grid = [
            [fn() for _ in xrange(self.__width)] for _ in xrange(self.__height)
        ]

    def __getitem__(self, key):
        return self.__grid[key]

    def __getattr__(self, attr):
        if attr == 'height':
            return self.__height
        if attr == 'width':
            return self.__width

    def __deepcopy__(self, memo):
        grid = Grid(fn=self.__fn, height=self.__height, width=self.__width)
        grid._Grid__grid = [[copy(item) for item in lst]
                            for lst in self.__grid]
        return grid

    def update(self, state):
        self.__grid = [
            [self.__fn() for _ in xrange(self.__height)] for _ in xrange(self.__width)
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
                self.__grid[x][y].type = States.GHOST
                if self.__grid[x][y+1].type != States.WALL:
                    self.__grid[x][y+1].type = States.GHOST_NEIGHBOUR
                if self.__grid[x][y-1].type != States.WALL:
                    self.__grid[x][y-1].type = States.GHOST_NEIGHBOUR
                if self.__grid[x+1][y].type != States.WALL:
                    self.__grid[x+1][y].type = States.GHOST_NEIGHBOUR
                if self.__grid[x-1][y].type != States.WALL:
                    self.__grid[x-1][y].type = States.GHOST_NEIGHBOUR

    def __str__(self):
        return '\n' + '\n'.join([''.join(['{:20}'.format(item) for item in row]) for row in self.__grid]) + '\n'


class MDPAgent(Agent):
    threshold = 0.001
    gamma = 0.9

    def __init__(self):
        """
        Initialize rewards, gamma and iterating threshold for the game
        """
        print "Starting up MDPAgent!"
        name = "Pacman"

    def registerInitialState(self, state):
        height = max([h for w, h in api.corners(state)]) + 1
        width = max([w for w, h in api.corners(state)]) + 1
        self.__grid = Grid(fn=Point, height=height, width=width)

    def getAction(self, state):
        """
        Return the moving direction of pacman
        """
        self.__grid.update(state)

        self.__value_iteration()
        # print self.__grid
        x, y = api.whereAmI(state)

        moves = {
            Directions.NORTH: self.__grid[x][y+1].utility,
            Directions.EAST: self.__grid[x+1][y].utility,
            Directions.SOUTH: self.__grid[x][y-1].utility,
            Directions.WEST: self.__grid[x-1][y].utility
        }

        move, _ = sorted(moves.items(), key=lambda kv: kv[1], reverse=True)[0]
        # print move
        return api.makeMove(move, api.legalActions(state))

    def __value_iteration(self):
        """
        value iteration for MDP
        """
        while True:
            changes = False
            grid_copy = deepcopy(self.__grid)

            for i in xrange(self.__grid.width):
                for j in xrange(self.__grid.height):
                    if (self.__grid[i][j].type != States.WALL):
                        utility = self.__grid[i][j].get_reward() + \
                            MDPAgent.gamma * self.__calculate_MEU(i, j)

                        grid_copy[i][j].utility = utility

                        if abs(self.__grid[i][j].utility - grid_copy[i][j].utility) > MDPAgent.threshold:
                            changes = True

            self.__grid = grid_copy

            if not changes:
                break

    def __calculate_MEU(self, x, y):
        """
        Calculate maximum expected utility for given state(x, y)
        """
        north = sum([
            0.8 * self.__grid[x][y + 1].utility if self.__grid[x][y +
                                                                  1].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x+1][y].utility if self.__grid[x +
                                                             1][y].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x-1][y].utility if self.__grid[x -
                                                             1][y].type != States.WALL else self.__grid[x][y].utility
        ])

        east = sum([
            0.8 * self.__grid[x+1][y].utility if self.__grid[x +
                                                             1][y].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y+1].utility if self.__grid[x][y +
                                                                1].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y-1].utility if self.__grid[x][y -
                                                                1].type != States.WALL else self.__grid[x][y].utility
        ])

        south = sum([
            0.8 * self.__grid[x][y - 1].utility if self.__grid[x][y -
                                                                  1].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x+1][y].utility if self.__grid[x +
                                                             1][y].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x-1][y].utility if self.__grid[x -
                                                             1][y].type != States.WALL else self.__grid[x][y].utility
        ])

        west = sum([
            0.8 * self.__grid[x - 1][y].utility if self.__grid[x -
                                                               1][y].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y+1].utility if self.__grid[x][y +
                                                                1].type != States.WALL else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y-1].utility if self.__grid[x][y -
                                                                1].type != States.WALL else self.__grid[x][y].utility
        ])

        return max(north, east, south, west)

    def final(self, state):
        print "Let's try again!"
        self.registerInitialState(state)
