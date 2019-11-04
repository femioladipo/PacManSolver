from copy import deepcopy, copy


from pacman import Directions
from game import Agent
import api
import random
import game
import util


class Point:
    reward = {
        'space': -0.04,
        'wall': '*',
        'capsule': 2,
        'food': 1,
        'ghost': -1
    }

    def __init__(self, utility=0, type='space'):
        self.utility = utility
        self.type = type

    def get_reward(self):
        return Point.reward[self.type]


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

    # def __deepcopy__(self, memo):
    #     grid = Grid(fn=self.__fn, height=self.__height, width=self.__width)
    #     grid._Grid__grid = copy(self.__grid)
    #     return grid

    def update(self, state):
        self.__grid = [
            [self.__fn() for _ in xrange(self.__width)] for _ in xrange(self.__height)
        ]

        for x, y in api.walls(state):
            self.__grid[x][y].type = 'wall'

        for x, y in api.food(state):
            self.__grid[x][y].type = 'food'

        for (x, y), timer in api.ghostStatesWithTimes(state):
            if timer < 2:
                self.__grid[int(x)][int(y)].type = 'ghost'

    def ghost_update(self, state):
        """
        Update ghosts to the map
        """
        pass
        # # for safety, also assign ghost_reward to cells next to ghosts
        # ghost_neighbors = self.four_neighbors(ghost_x, ghost_y)
        # for neighbor in ghost_neighbors:
        #     # if not wall
        #     if neighbor not in api.walls(state):
        #         self.map.set_value(
        #             neighbor[0], neighbor[1], self.ghost_reward)


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
        foodGrid = state.getFood()
        self.__grid = Grid(fn=Point, height=foodGrid.height,
                           width=foodGrid.width)

    def getAction(self, state):
        """
        Return the moving direction of pacman
        """
        self.__grid.update(state)

        self.__value_iteration()

        x, y = api.whereAmI(state)

        moves = {
            Directions.NORTH: self.__grid[x][y+1].utility,
            Directions.EAST: self.__grid[x+1][y].utility,
            Directions.SOUTH: self.__grid[x][y-1].utility,
            Directions.WEST: self.__grid[x-1][y].utility
        }

        move, _ = sorted(moves.items(), key=lambda kv: kv[1], reverse=True)[0]

        return api.makeMove(move, api.legalActions(state))

    def __value_iteration(self):
        """
        value iteration for MDP
        """
        while True:
            changes = False
            # map_copy = deepcopy(self.__map)
            grid_copy = self.__grid

            for i in xrange(self.__grid.width):
                for j in xrange(self.__grid.height):
                    if (self.__grid[i][j].type != 'wall'):
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
                                                                  1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x+1][y].utility if self.__grid[x +
                                                             1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x-1][y].utility if self.__grid[x -
                                                             1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility
        ])

        east = sum([
            0.8 * self.__grid[x+1][y].utility if self.__grid[x +
                                                             1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y+1].utility if self.__grid[x][y +
                                                                1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y-1].utility if self.__grid[x][y -
                                                                1].utility != Point.reward['wall'] else self.__grid[x][y].utility
        ])

        south = sum([
            0.8 * self.__grid[x][y - 1].utility if self.__grid[x][y -
                                                                  1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x+1][y].utility if self.__grid[x +
                                                             1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x-1][y].utility if self.__grid[x -
                                                             1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility
        ])

        west = sum([
            0.8 * self.__grid[x - 1][y].utility if self.__grid[x -
                                                               1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y+1].utility if self.__grid[x][y +
                                                                1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
            0.1 * self.__grid[x][y-1].utility if self.__grid[x][y -
                                                                1].utility != Point.reward['wall'] else self.__grid[x][y].utility
        ])

        return max(north, east, south, west)

    def final(self, state):
        print "Let's try again!"
        self.registerInitialState(state)
