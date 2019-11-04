from copy import deepcopy, copy


from pacman import Directions
from game import Agent
import api
import random
import game
import util


# class Point:
#     reward = {
#         'pacman': -0.04,
#         'space': -0.04,
#         'wall': '*',
#         'capsule': 2,
#         'food': 1,
#         'ghost': -1
#     }

#     def __init__(self, utility=0, type='space'):
#         self.utility = utility
#         self.type = type

#     def get_reward(self):
#         return Point.reward[self.type]

#     def __str__(self):
#         return 'p' if self.type == 'pacman' else str(self.utility)


# class Grid:
#     def __init__(self, fn, height, width):
#         # self.isPristine = True
#         self.__fn = fn
#         self.__height = height
#         self.__width = width
#         self.__grid = [
#             [fn() for _ in xrange(self.__width)] for _ in xrange(self.__height)
#         ]

#     def __getitem__(self, key):
#         return self.__grid[key]

#     def __getattr__(self, attr):
#         if attr == 'height':
#             return self.__height
#         if attr == 'width':
#             return self.__width

#     def __deepcopy__(self, memo):
#         grid = Grid(fn=self.__fn, height=self.__height, width=self.__width)
#         grid._Grid__grid = [[copy(item) for item in lst] for lst in self.__grid]
#         return grid

#     def update(self, state):
#         self.__grid = [
#             [self.__fn() for _ in xrange(self.__width)] for _ in xrange(self.__height)
#         ]

#         x, y = api.whereAmI(state)
#         self.__grid[x][y].type = 'pacman'

#         for x, y in api.walls(state):
#             self.__grid[x][y].type = 'wall'

#         for x, y in api.food(state):
#             self.__grid[x][y].type = 'food'
        
#         for x, y in api.capsules(state):
#             self.__grid[x][y].type = 'capsule'

#         for (x, y), timer in api.ghostStatesWithTimes(state):
#             x, y = int(x), int(y)
#             if timer < 2:
#                 self.__grid[x][y].type = 'ghost'
#                 if self.__grid[x][y+1].type != 'wall':self.__grid[x][y+1].type = 'ghost'
#                 if self.__grid[x][y-1].type != 'wall':self.__grid[x][y-1].type = 'ghost'
#                 if self.__grid[x+1][y].type != 'wall':self.__grid[x+1][y].type = 'ghost'
#                 if self.__grid[x-1][y].type != 'wall':self.__grid[x-1][y].type = 'ghost'
    
#     def __str__(self):
#         return '\n' +'\n'.join([''.join(['{:12}'.format(item) for item in row]) for row in self.__grid]) + '\n'


# class MDPAgent(Agent):
#     threshold = 0.001
#     gamma = 0.9

#     def __init__(self):
#         """
#         Initialize rewards, gamma and iterating threshold for the game
#         """
#         print "Starting up MDPAgent!"
#         name = "Pacman"

#     def registerInitialState(self, state):
#         foodGrid = state.getFood()
#         self.__grid = Grid(fn=Point, height=foodGrid.height,
#                            width=foodGrid.width)

#     def getAction(self, state):
#         """
#         Return the moving direction of pacman
#         """
#         self.__grid.update(state)
        
#         self.__value_iteration()
#         print self.__grid
#         x, y = api.whereAmI(state)

#         moves = {
#             Directions.NORTH: self.__grid[x][y+1].utility,
#             Directions.EAST: self.__grid[x+1][y].utility,
#             Directions.SOUTH: self.__grid[x][y-1].utility,
#             Directions.WEST: self.__grid[x-1][y].utility
#         }

#         move, _ = sorted(moves.items(), key=lambda kv: kv[1], reverse=True)[0]
#         print move
#         return api.makeMove(move, api.legalActions(state))

#     def __value_iteration(self):
#         """
#         value iteration for MDP
#         """
#         while True:
#             changes = False
#             grid_copy = deepcopy(self.__grid)

#             for i in xrange(self.__grid.width):
#                 for j in xrange(self.__grid.height):
#                     if (self.__grid[i][j].type != 'wall'):
#                         utility = self.__grid[i][j].get_reward() + \
#                             MDPAgent.gamma * self.__calculate_MEU(i, j)

#                         grid_copy[i][j].utility = utility

#                         if abs(self.__grid[i][j].utility - grid_copy[i][j].utility) > MDPAgent.threshold:
#                             changes = True

#                     self.__grid = grid_copy

#             if not changes:
#                 break

#     def __calculate_MEU(self, x, y):
#         """
#         Calculate maximum expected utility for given state(x, y)
#         """
#         north = sum([
#             0.8 * self.__grid[x][y + 1].utility if self.__grid[x][y +
#                                                                   1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x+1][y].utility if self.__grid[x +
#                                                              1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x-1][y].utility if self.__grid[x -
#                                                              1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility
#         ])

#         east = sum([
#             0.8 * self.__grid[x+1][y].utility if self.__grid[x +
#                                                              1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x][y+1].utility if self.__grid[x][y +
#                                                                 1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x][y-1].utility if self.__grid[x][y -
#                                                                 1].utility != Point.reward['wall'] else self.__grid[x][y].utility
#         ])

#         south = sum([
#             0.8 * self.__grid[x][y - 1].utility if self.__grid[x][y -
#                                                                   1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x+1][y].utility if self.__grid[x +
#                                                              1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x-1][y].utility if self.__grid[x -
#                                                              1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility
#         ])

#         west = sum([
#             0.8 * self.__grid[x - 1][y].utility if self.__grid[x -
#                                                                1][y].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x][y+1].utility if self.__grid[x][y +
#                                                                 1].utility != Point.reward['wall'] else self.__grid[x][y].utility,
#             0.1 * self.__grid[x][y-1].utility if self.__grid[x][y -
#                                                                 1].utility != Point.reward['wall'] else self.__grid[x][y].utility
#         ])

#         return max(north, east, south, west)

#     def final(self, state):
#         print "Let's try again!"
#         self.registerInitialState(state)
class Grid:
    """
    Build 2D grid of cells as a map for pacman
    """
    
    def __init__(self, grid_width, grid_height, initial_grid = None):
        """
        Initialize every cell in the map as 0
        """
        self.grid_height = grid_height
        self.grid_width = grid_width
        self.grid = [[0 for x in range(self.grid_width)] for y in range(self.grid_height)]
        
        # initial_grid is used to make a copy of the map
        if initial_grid != None:
            for i in range(self.grid_height):
                for j in range(self.grid_width):
                    self.grid[i][j] = initial_grid[i][j]
        
    def set_value(self, x, y, value):
        """
        Set value for the given cell(x,y)
        """
        self.grid[y][x] = value
        
    def get_value(self, x, y):
        """
        Return value for the given cell(x,y)
        """
        return self.grid[y][x]
    
    def copy_grid(self):
        """
        Return a copy of the map
        """
        new_map = Grid(self.grid_width, self.grid_height, self.grid)
        return new_map

class MDPAgent(Agent):

    def __init__(self):
        """
        Initialize rewards, gamma and iterating threshold for the game
        """
        print "Starting up MDPAgent!"
        name = "Pacman"
        self.initial_utility = 0
        self.space_reward = -0.04
        self.food_reward = 1
        self.ghost_reward = -1
        self.gamma = 0.9
        self.threshold = 0.001
        
    def registerInitialState(self, state):
        """
        Build a map and update necessary rewards into the map
        """
        print "Running registerInitialState!"
        
        # Make a map of the right size
        self.map_size(state)
        self.make_map()         
        
        # update wall, space, food and ghosts
        self.wall_update(state)
        self.space_update(state)
        self.food_update(state)
        self.ghost_update(state)

    def final(self, state):
        """
        Reset the field when run games in a row
        """
        print "Let's try again!"
        self.registerInitialState(state)

    def map_size(self, state):
        """
        Calculate the height and width of map
        """
        # use corner function to find the size of the map
        corner_list = api.corners(state)
        corner_x_list = []
        corner_y_list = []
        for corner in corner_list:
            corner_x_list.append(corner[0])
            corner_y_list.append(corner[1])
        self.grid_width = max(corner_x_list) + 1
        self.grid_height = max(corner_y_list) + 1

    def make_map(self):
        """
        Conduct the map
        """
        self.map = Grid(self.grid_width, self.grid_height)
        
    def wall_update(self, state):
        """
        Add walls to the map
        """
        walls = api.walls(state)
        for wall in walls:
            self.map.set_value(wall[0], wall[1], "*")
            
    def space_update(self, state):
        """
        Find space in the map
        """
        for i in range(self.grid_width):
            for j in range(self.grid_height):
                if self.map.get_value(i, j) != "*":
                    self.map.set_value(i, j, self.initial_utility)
            
    def food_update(self, state):
        """
        Update food to the map
        """
        foods = api.food(state)
        for food in foods:
            self.map.set_value(food[0], food[1], self.food_reward)
 
    def ghost_update(self, state):
        """
        Update ghosts to the map
        """
        ghosts = api.ghostStatesWithTimes(state)
        for ghost in ghosts:
            # if ghosts are scared and the time of remaining scared
            # is longer than 2 (set 2 for safety)
            if ghost[1] > 2:
                # ignore the ghosts
                continue
            else:
                # if ghosts are not scared or the time of being scared 
                # is less than 2
                ghost_x = int(ghost[0][0])
                ghost_y = int(ghost[0][1])
                # set ghost reward to ghost
                self.map.set_value(ghost_x, ghost_y, self.ghost_reward)
                
                # for safety, also assign ghost_reward to cells next to ghosts
                ghost_neighbors = self.four_neighbors(ghost_x, ghost_y)
                for neighbor in ghost_neighbors:
                    # if not wall
                    if neighbor not in api.walls(state):
                        self.map.set_value(neighbor[0], neighbor[1], self.ghost_reward)
                
    def four_neighbors(self, x, y):
        """
        Returns horizontal and vertical neighbors of cell (x, y)
        """        
        ans = []
        if x > 1:
            ans.append((x - 1, y))
        if x < self.grid_width - 1:
            ans.append((x + 1, y))
        if y > 1:
            ans.append((x, y - 1))
        if y < self.grid_height - 1:
            ans.append((x, y + 1))
        return ans
        
    def calculate_MEU(self, x, y, return_dir = False):
        """
        Calculate maximum expected utility for given state(x, y)
        """
        
        # Calculate for Directions.NORTH       
        if self.map.get_value(x, y + 1) != "*":
            north_n = 0.8 * self.map.get_value(x, y + 1)
        else:
            north_n = 0.8 * self.map.get_value(x, y)
            
        if self.map.get_value(x - 1, y) != "*":
            north_w = 0.1 * self.map.get_value(x - 1, y)
        else:
            north_w = 0.1 * self.map.get_value(x, y)
        
        if self.map.get_value(x + 1, y) != "*":
            north_e = 0.1 * self.map.get_value(x + 1, y)
        else:
            north_e = 0.1 * self.map.get_value(x, y)
        
        north_u = north_n + north_w + north_e
        
        # Calculate for Directions.WEST       
        if self.map.get_value(x - 1, y) != "*":
            west_w = 0.8 * self.map.get_value(x - 1, y)
        else:
            west_w = 0.8 * self.map.get_value(x, y)
            
        if self.map.get_value(x, y + 1) != "*":
            west_n = 0.1 * self.map.get_value(x, y + 1)
        else:
            west_n = 0.1 * self.map.get_value(x, y)
        
        if self.map.get_value(x, y - 1) != "*":
            west_s = 0.1 * self.map.get_value(x, y - 1)
        else:
            west_s = 0.1 * self.map.get_value(x, y)
            
        west_u = west_w + west_n + west_s    
        
        # Calculate for Directions.SOUTH       
        if self.map.get_value(x, y - 1) != "*":
            south_s = 0.8 * self.map.get_value(x, y - 1)
        else:
            south_s = 0.8 * self.map.get_value(x, y)
            
        if self.map.get_value(x - 1, y) != "*":
            south_w = 0.1 * self.map.get_value(x - 1, y)
        else:
            south_w = 0.1 * self.map.get_value(x, y)
        
        if self.map.get_value(x + 1, y) != "*":
            south_e = 0.1 * self.map.get_value(x + 1, y)
        else:
            south_e = 0.1 * self.map.get_value(x, y)
            
        south_u = south_s + south_w + south_e    
        
      # Calculate for Directions.EAST       
        if self.map.get_value(x + 1, y) != "*":
            east_e = 0.8 * self.map.get_value(x + 1, y)
        else:
            east_e = 0.8 * self.map.get_value(x, y)
            
        if self.map.get_value(x, y - 1) != "*":
            east_s = 0.1 * self.map.get_value(x, y - 1)
        else:
            east_s = 0.1 * self.map.get_value(x, y)
        
        if self.map.get_value(x, y + 1) != "*":
            east_n = 0.1 * self.map.get_value(x, y + 1)
        else:
            east_n = 0.1 * self.map.get_value(x, y)
            
        east_u = east_e + east_s + east_n
        
        EU_dict = {Directions.NORTH : north_u,
                   Directions.WEST : west_u,
                   Directions.SOUTH : south_u,
                   Directions.EAST : east_u}
        
        max_value = max(EU_dict.values())
        
        # return MEU for iterating value, return direction for makeing a move
        if return_dir == True:
            direction = max(EU_dict, key = EU_dict.get)
            return direction
        else:
            return max_value
    
    def calculate_utility(self, x, y):
        """
        Calculate utility for given state(x, y)
        """
        utility = self.space_reward + self.gamma * self.calculate_MEU(x, y)
        return utility
        
    def value_iteration(self):
        """
        value iteration for MDP
        """
        iterate = True       
        while iterate == True:
            delta = 0
            # make 2 copies of the map before iteration
            self.new_map = self.map.copy_grid()
            self.old_map = self.map.copy_grid()
            for i in range(self.grid_width):
                for j in range(self.grid_height):
                    # only calculate U for blank space
                    if (self.map.get_value(i, j) != "*" and 
                        self.map.get_value(i, j) != self.food_reward and 
                        self.map.get_value(i, j) != self.ghost_reward):
                        utility = self.calculate_utility(i, j)
                        # update U to the new map
                        self.new_map.set_value(i, j, utility)
                        # calculate the difference after iteration
                        difference = self.new_map.get_value(i, j) - self.old_map.get_value(i, j)                       
                        # check whether the difference is smaller than threshold
                        if abs(difference) > self.threshold:
                            delta = difference
            # copy U back to self.map              
            self.map = self.new_map.copy_grid()
            
            # if for all grids, the difference after iteration is smaller 
            # than threshold, then stop iteration
            if delta == 0:
                iterate = False
                
    def getAction(self, state):
        """
        Return the moving direction of pacman
        """            
        self.space_update(state)
        self.food_update(state)
        self.ghost_update(state)
        self.value_iteration()
        pacman = api.whereAmI(state)
        x = pacman[0]
        y = pacman[1]
        # Get the actions we can try, and remove "STOP" if that is one of them.
        legal = api.legalActions(state)
        if Directions.STOP in legal:
            legal.remove(Directions.STOP)
        # use MEU to decide the next move
        return api.makeMove(self.calculate_MEU(x, y, True), legal