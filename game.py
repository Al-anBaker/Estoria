#=======
#IMPORTS
#=======
import random
import os
import sys
import pygame
import json

#====================
#Pygame Initalization
#====================
pygame.init()

TILE_SIZE = 16
MOVE_DELAY = 120
last_move_time = 0

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path) # type: ignore
    return os.path.join(os.path.abspath("."), relative_path)

font_path = resource_path("Perfect DOS VGA 437.ttf")
font = pygame.font.Font(font_path, TILE_SIZE)

clock = pygame.time.Clock()

MAP_PIXEL_WIDTH = 55 * TILE_SIZE
MAP_PIXEL_HEIGHT = 20 * TILE_SIZE
UI_HEIGHT = 80

screen = pygame.display.set_mode(
    (MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT + UI_HEIGHT)
)

pygame.display.set_caption("===ESTORIA===")

Legendary = (255, 128, 0)
Rare = (163, 53, 238)
Uncommon = (30, 255, 0)
Common = (255, 255, 255)


#Map Tile sets, these are the token for static Tiles on the map
water = "~"
empty = chr(176)
wall = chr(219)
door = ">"
grass = "."
tree = "T"
stone = "*"
town = "V"

#In Colour Map we asign colours to each of the Tiles using RGB Values this helps with making the game look better
color_map = {
    #STATIC TILES
    wall: (200, 200, 200),
    empty: (40, 40, 40),
    water: (0, 0, 255),
    grass: (20, 120, 20), #Grass
    tree: (0, 140, 0), #Tree
    stone: (120, 120, 120), #Stone
    town: (255, 255, 255), #Town
    door: (0, 255, 255), #Door
    

    #CHARACTERS
    "o": (255, 0, 0), #Orc
    "D": (255, 50, 50), #Demon
    "v": (140, 220, 140), #Villagers
    "S": (255, 215, 0), #Shop Clerk
    "g": (255, 0, 0), #Goblin
    "@": (255, 255, 0), #Player
    "%": (255, 0, 255), #Legacy Foe

    #ITEMS
        #LEGENDARY
    ")": Legendary,   # Runed Blade (T3 Sword)
    "]": Legendary, # Runed Plate (T3 Armour)
        #RARE
    "{": Rare,   # Chainmail (T2 Armour)
    "L": Rare,     # Iron Sword (T2 Sword)
        #UNCOMMON
    "[": Uncommon,  #Cloth Armour (T1 Armour)
    "/": Uncommon,  #Rusty Dagger (T1 Sword)
        #COMMON
    "l": Common,   #Stick (T0 Sword)
    "r": Common,   #Rags (T0 Armour)
    "!": Common,   #Health Potion
    "|": Common,   #Torch


}

def get_color(char):
    return color_map.get(char, (255, 255, 255))



#===============
#Global Varibles
#===============
playerLastMove = True
dungeon_level = 0 #Tracks what floor of a Dungeon the Player is on
inventory_selected = 0
message_log = []
MAX_LOG_LINES = 2
view_radius = 6
game_state = "menu" #"menu" or "game" or "shop" or "stats" or "inventory"
player_name_input =""
OVERWORLD_WIDTH = 55
OVERWORLD_HEIGHT = 20
confirmation_window = False
FOREST_MOVE_DELAY = 220
shop_selected_index = 0
shop_panel = "shop" # "shop" or "player"
shop_open = False
stats_selected_index = 0
exp_cap = 0
inv_limit = 5

#==============
#Object Classes
#==============
class Item():
    def __init__(self, token, name, x, y, value, item_type, atk=0, defn=0, hp=0, active=True, vision=0):

        #How the item look on the screen
        self.token = token

        #Its Name for use with the Message Log
        self.name = name

        #Spawn Coordinates
        self.x = x
        self.y = y

        self.value = value

        #What Type of Item is it (Weapon, Armour, Equipment)
        self.type = item_type

        #Item Stats these are added to Player Base stats 
        self.atk = atk
        self.defn = defn
        self.hp = hp
        self.vision = vision

        #If the Item is active or has been picked up (Deactive)
        self.active = active

        self.equipped = False



class Character():
    #Character Vars
    def __init__(self, token, name, x, y, NPC, ATK, DEF, HP, GOLD, EXP=0, current_map=None):

        #token is how the character looks on the Map
        self.token = token
        self.name = name

        #Characters Position Reletive to the Map
        self.x = x
        self.y = y

        #If the character is a Non Player Character
        self.NPC = NPC
        
        #Base Character Stats
        self.ATK = ATK
        self.DEF = DEF
        self.HP = HP
        self.GOLD = GOLD

        #To keep Track of what floor the Character is on
        self.current_map = current_map

        #Inventory and Equipped Items
        self.inventory = []
        self.weapon = None
        self.armour = None
        self.misc = None

        self.shopkeeper = False

        self.EXP = EXP
        self.level = 1

        self.upgrade_points = 0

        self.max_health = 20

    #Adds an Item to the Inventory and Informs the Player
    def pickup_item(self, item):
        if len(self.inventory) >= 5:
            add_message("Inventory Full")
            return False
        else:
            self.inventory.append(item)
            add_message(f"You have picked up a: {item.name}")
            return True

    #When in the inventory this add the Item from the Inventory to be a held item
    def equip_item(self, item):
        global view_radius
        if item.type == "weapon":
            if self.weapon:
                self.ATK -= self.weapon.atk
                self.DEF -= self.weapon.defn
                self.weapon.equipped = False
            self.weapon = item
            item.equipped = True
            self.ATK += item.atk
            self.DEF += item.defn

        elif item.type == "armour":
            if self.armour:
                self.DEF -= self.armour.defn
                self.ATK -= self.armour.atk
                self.armour.equipped = False
            self.armour = item
            item.equipped = True
            self.DEF += item.defn
            self.ATK += item.atk

        elif item.type == "misc":
            if self.misc:
                view_radius -= self.misc.vision
                self.misc.equipped = False
            self.misc = item
            item.equipped = True
            view_radius += item.vision


    #Like the Equip Item but unequips instead
    def unequip_item(self, item):
        global view_radius
        if item.type == "weapon" and self.weapon:
            self.ATK -= self.weapon.atk
            self.DEF -= self.weapon.defn
            self.weapon.equipped = False
            self.weapon = None

        elif item.type == "armour" and self.armour:
            self.DEF -= self.armour.defn
            self.ATK -= self.armour.atk
            self.armour.equipped = False
            self.armour = None
        elif item.type == "misc" and self.misc:
            view_radius -= self.misc.vision
            self.misc.equipped = False
            self.misc = None

    #For Consumables to give a temporary boot to the Player or Heal
    def use_potion(self, item):
        self.HP += item.hp
        add_message("Used Potion")
        if self.HP > self.max_health:
            self.HP = self.max_health

    def remove_item(self, item):
        self.inventory.remove(item)

#GameMap is an Object that holds the current Maps name, grid and its dimensions, it is also respoonsible in adding doors and entities
class GameMap:
    def __init__(self, name, grid=None, width=None, height=None):
        self.name = name
        self.entities = []
        self.fog_enabled = True

        # Case 1: Static map passed in
        if isinstance(grid, list):
            self.grid = grid
            self.height = len(grid)
            self.width = len(grid[0])

        # Case 2: Procedural map requested
        elif width is not None and height is not None:
            self.width = width
            self.height = height
            self.grid = self.generate_procedural_map()
            self.spawn_random_items()
            self.spawn_foes()

        else:
            raise ValueError("Invalid GameMap initialization")

        self.visible = [[False for _ in range(self.width)]
                        for _ in range(self.height)]
        self.discovered = [[False for _ in range(self.width)]
                           for _ in range(self.height)]

    def __getitem__(self, index):
        return self.grid[index]

    #Here we add an Entity to the selected map
    def add_entity(self, entity):
        self.entities.append(entity)
        entity.current_map = self

    #Spawn Random Items scatters loot around the map for Players to Pickup
    def spawn_random_items(self):
        if not hasattr(self, "rooms"):
            return
        
        item_count = random.randint(1, 3)

        for _ in range(item_count):
            room = random.choice(self.rooms)

            rx, ry, rw, rh = room

            x = random.randint(rx + 1, rx + rw - 2)
            y = random.randint(ry + 1, ry + rh - 2)

            if self.grid[y][x] != empty:
                continue
            
            tier = get_loot_tier()
            roll = random.random()

            if roll < 0.3:
                item = Item("!", "Health Potion", x, y, 10, item_type="potion", hp=5)
            elif roll < 0.4:
                item = Item("|", "Torch", x, y, 5, item_type="misc", vision=2)

            elif roll < 0.65:
                w = weapon_tiers[tier]
                item = Item(
                    w["token"],
                    w["name"],
                    x, y,
                    w["value"],
                    item_type="weapon",
                    atk=w["atk"],
                    defn=w["defn"],
                    active=True
                )
            else:
                a = armour_tiers[tier]
                item = Item(
                    a["token"],
                    a["name"],
                    x, y,
                    a["value"],
                    item_type="armour",
                    defn=a["defn"],
                    atk=a["atk"],
                    active=True
                )
            self.entities.append(item)

    #Here we handle Map Transition for the Player and make sure they spawn in a safe area
    def enter_map(self, player, x, y):
        global current_map
        if hasattr(self, "spawn_point") and self.spawn_point:
            player.x, player.y = self.spawn_point
        else:
            player.x = x
            player.y = y
        self.add_entity(player)

    #This handles Monster Spawning in the Proecedually generated levels
    def spawn_foes(self):

        if not hasattr(self, "rooms"):
            return
        
        base_count = random.randint(1, 3)

        for _ in range(base_count):
            room = random.choice(self.rooms)

            spawn_room = self.rooms[0]
            if room == spawn_room:
                continue

            rx, ry, rw, rh = room

            x = random.randint(rx + 1, rx + rw - 2)
            y = random.randint(ry + 1, ry + rh - 2)

            if self.grid[y][x] != empty:
                continue
            if any(e.x == x and e.y == y for e in self.entities):
                continue

            level_scale = max(1, dungeon_level)

            atk_bonus = level_scale // 2
            def_bonus = level_scale // 2
            hp_bonus = level_scale * 2
            gold_bonus = level_scale * 2
            exp_reward = level_scale * 5

            roll = random.random()

            if roll < 0.6:
                foe = Character(
                    "g", "Goblin", x, y, True,
                    2 + atk_bonus,
                    1 + def_bonus,
                    10 + hp_bonus,
                    5 + gold_bonus,
                    EXP=exp_reward
                )
            elif roll < 0.9:
                foe = Character(
                    "o", "Orc", x, y, True,
                    3 + atk_bonus,
                    2 + def_bonus,
                    15 + hp_bonus,
                    3 + gold_bonus,
                    EXP=exp_reward + 5
                )
            else:
                foe = Character(
                    "D", "Demon", x, y, True,
                    5 + atk_bonus,
                    3 + def_bonus,
                    20 + hp_bonus,
                    5 + gold_bonus,
                    EXP=exp_reward + 10
                )

            self.add_entity(foe)
    
    #Basic Method to add a door to a map
    def add_door(self, x, y):
        self.grid[y][x] = door

    #Update Visibility handles the Players Fog of War, this works by Raycasting until it hits a wall tile
    def update_visibility(self, player, radius):
        # Clear current visibility
        global view_radius
        radius = view_radius
        for y in range(self.height):
            for x in range(self.width):
                self.visible[y][x] = False

        px, py = player.x, player.y

        # Bresenham line algorithm
        def line(x0, y0, x1, y1):
            points = []
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            x, y = x0, y0
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1

            if dx > dy:
                err = dx / 2.0
                while x != x1:
                    points.append((x, y))
                    err -= dy
                    if err < 0:
                        y += sy
                        err += dx
                    x += sx
            else:
                err = dy / 2.0
                while y != y1:
                    points.append((x, y))
                    err -= dx
                    if err < 0:
                        x += sx
                        err += dy
                    y += sy

            points.append((x1, y1))
            return points

        # Cast rays to every tile in square around player
        for y in range(py - radius, py + radius + 1):
            for x in range(px - radius, px + radius + 1):

                if not (0 <= x < self.width and 0 <= y < self.height):
                    continue

                if abs(x - px) + abs(y - py) > radius:
                    continue

                for lx, ly in line(px, py, x, y):

                    if not (0 <= lx < self.width and 0 <= ly < self.height):
                        break

                    self.visible[ly][lx] = True
                    self.discovered[ly][lx] = True

                    # Stop ray if wall hit (but wall itself is visible)
                    if self.grid[ly][lx] == wall and (lx, ly) != (px, py):
                        break

    #Here we are drawing the fog for the Player, to make Discovered but not visible tiles Dim
    def draw(self):

        self.update_visibility(Player, view_radius)

        for y in range(self.height):
            for x in range(self.width):

                # Skip if never discovered
                if self.fog_enabled and not self.discovered[y][x]:
                    continue

                char = self.grid[y][x]

                # Draw entities if visible OR fog disabled
                if self.visible[y][x] or not self.fog_enabled:
                    for entity in self.entities:
                        if entity.x == x and entity.y == y:
                            char = entity.token
                            break

                # --- COLOR HANDLING ---
                normal_color = get_color(char)
                dim_color = (
                    normal_color[0] // 3,
                    normal_color[1] // 3,
                    normal_color[2] // 3
                )

                # Fog handling
                if not self.fog_enabled:
                    color = normal_color
                else:
                    if self.visible[y][x]:
                        color = normal_color
                    else:
                        color = dim_color

                text = font.render(char, True, color)
                screen.blit(text, (x * TILE_SIZE, y * TILE_SIZE))

    #This Method focuses on generating the Provedural Maps, for the Player
    def generate_procedural_map(self):
        grid = [[wall for _ in range(self.width)]
                for _ in range(self.height)]

        rooms = []
        max_rooms = 9
        max_attempts = 50
        attempts = 0
        min_size = 3
        max_size = 9
        self.spawn_point = None

        while len(rooms) < max_rooms and attempts < max_attempts:
            attempts += 1

            w = random.randint(min_size, max_size)
            h = random.randint(min_size, max_size)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)

            new_room = (x, y, w, h)

            failed = False
            for other in rooms:
                if (x < other[0] + other[2] and
                    x + w > other[0] and
                    y < other[1] + other[3] and
                    y + h > other[1]):
                    failed = True
                    break

            if failed:
                continue

            # Carve room
            for i in range(x, x + w):
                for j in range(y, y + h):
                    grid[j][i] = empty

            # Connect to previous room
            if rooms:
                prev_x = rooms[-1][0] + rooms[-1][2] // 2
                prev_y = rooms[-1][1] + rooms[-1][3] // 2
                new_x_center = x + w // 2
                new_y_center = y + h // 2

                if random.choice([True, False]):
                    for i in range(min(prev_x, new_x_center),
                                max(prev_x, new_x_center) + 1):
                        grid[prev_y][i] = empty

                    for j in range(min(prev_y, new_y_center),
                                max(prev_y, new_y_center) + 1):
                        grid[j][new_x_center] = empty
                else:
                    for j in range(min(prev_y, new_y_center),
                                max(prev_y, new_y_center) + 1):
                        grid[j][prev_x] = empty

                    for i in range(min(prev_x, new_x_center),
                                max(prev_x, new_x_center) + 1):
                        grid[new_y_center][i] = empty

            rooms.append(new_room)


        if not rooms:
            # emergency fallback room
            x = self.width // 2 - 3
            y = self.height // 2 - 3
            for i in range(x, x + 6):
                for j in range(y, y + 6):
                    grid[j][i] = empty
            rooms.append((x, y, 6, 6))

        # Spawn in first room
        first = rooms[0]
        spawn_x = first[0] + first[2] // 2
        spawn_y = first[1] + first[3] // 2
        self.spawn_point = (spawn_x, spawn_y)

        # Door in last room
        last = rooms[-1]
        door_x = last[0] + last[2] // 2
        door_y = last[1] + last[3] // 2

        # Prevent spawn and door overlap
        if (door_x, door_y) == self.spawn_point:
            door_x += 1

        grid[door_y][door_x] = door
        self.rooms = rooms
        return grid
    
    def add_forest_patches(self, count=8, min_size=3, max_size=4):
        for _ in range(count):
            width = random.randint(min_size, max_size)
            height = random.randint(min_size, max_size)

            start_x = random.randint(1, self.width - width - 1)
            start_y = random.randint(1, self.height - height - 1)

            for y in range(start_y, start_y + height):
                for x in range(start_x, start_x + width):
                    if self.grid[y][x] == grass:
                        self.grid[y][x] = tree

    def surround_doors_with_stone(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == door:

                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:

                            nx = x + dx
                            ny = y + dy

                            if 0 <= nx < self.width and 0 <= ny < self.height:

                                # Don't overwrite door itself
                                if self.grid[ny][nx] == grass:
                                    self.grid[ny][nx] = stone

#Generates a tile map for the overworld
def generate_overworld():
    grid = [[grass for _ in range(OVERWORLD_WIDTH)]
            for _ in range(OVERWORLD_HEIGHT)]
    

    for _ in range(5):
        wx = random.randint(5, OVERWORLD_WIDTH-6)
        wy = random.randint(5, OVERWORLD_HEIGHT-6)

        for y in range(wy-2, wy+3):
            for x in range(wx-3, wx+4):
                if random.random() < 0.4:
                    grid[y][x] = water
    return grid

#Generates a tile map for the Village
def generate_town(width=55, height=20):

    grid = [[grass for _ in range(width)] for _ in range(height)]

    road_y = height // 2
    for y in range(road_y - 1, road_y + 2):
        for x in range(width):
            grid[y][x] = stone

    road_x = width // 2 
    for x in range(road_x - 1, road_x + 2):
        for y in range(height):
            grid[y][x] = stone

    house_count = random.randint(5, 8)
    placed = 0
    attempts = 0

    while placed < house_count and attempts < 100:
        attempts += 1

        w = random.randint(4, 8)
        h = random.randint(4, 6)

        x = random.randint(2, width - w - 2)
        y = random.randint(2, height - h - 2)

        # Check if house touches road
        intersects_road = False
        for i in range(x - 1, x + w + 1):
            for j in range(y - 1, y + h + 1):
                if grid[j][i] == stone:
                    intersects_road = True

        if intersects_road:
            continue

        # Build house
        for i in range(x, x + w):
            for j in range(y, y + h):

                if i == x or i == x + w - 1 or j == y or j == y + h - 1:
                    grid[j][i] = wall
                else:
                    grid[j][i] = empty

        # Door
        door_x = x + w // 2
        grid[y + h - 1][door_x] = empty

        placed += 1

    for _ in range(40):

        x = random.randint(1, width - 2)
        y = random.randint(1, height - 2)

        if grid[y][x] == grass:
            grid[y][x] = tree

    return grid

#Here we initilise the Player with their attrbutes
Player = Character("@", "Player", 7, 13, False, 3, 2, 20, 0, 0)

#Finds a space spawn, used for Over World
def find_safe_spawn(grid):
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            if grid[y][x] == grass:
                return x, y
    return 1, 1  # fallback

#Checks if the player is able to level up
def check_level_up():
    global exp_cap
    exp_cap = int(Player.level * 20 * 1.25)
    if Player.EXP >= exp_cap:
        Player.level += 1
        Player.upgrade_points = Player.level + 1
        Player.EXP -= exp_cap
        add_message(f"You are now Level: {Player.level}")

def check_inv_full():
    if len(Player.inventory) >= 5:
        return True
    else:
        return False
    


#==================
#Generate Overworld
#==================
overworld_grid = generate_overworld()
Overworld = GameMap("Overworld", overworld_grid)
Overworld.fog_enabled = False
Overworld.add_forest_patches()
spawn_x, spawn_y = find_safe_spawn(overworld_grid)
Overworld.enter_map(Player, spawn_x, spawn_y)
Overworld.add_door(10, 10)
Overworld.add_door(40, 8)
Overworld.add_door(25, 15)
Overworld.surround_doors_with_stone()
Overworld.grid[5][20] = town
Overworld.grid[14][35] = town
current_map = Overworld



#Player Stats and Stat Names are for the Stats screen 
Player_Stats = [
    Player.ATK, Player.DEF, Player.max_health
]
Stat_names = [
    "Attack", "Defence", "Max Health"
]

#Makes sure that the Player has their correct EXP cap
check_level_up()

#Global shop inventory, 
shop_inventory = [
    Item("}", "Platemail", 0, 0, 25, item_type="armour", defn=6),
    Item(">", "Spear", 0, 0, 20, item_type="weapon", atk=5),
    Item("!!", "Greater Health Potion", 0, 0, 10, item_type="potion", hp=10)
]

weapon_tiers = {
    1: {"name": "Stick", "token": "l", "atk": 2, "defn": 0, "value": 5},
    2: {"name": "Rusty Dagger", "token": "/", "atk": 4, "defn": 2, "value": 5},
    3: {"name": "Iron Sword", "token": "L", "atk": 7, "defn": 4, "value": 12},
    4: {"name": "Runed Blade", "token": ")", "atk": 10, "defn": 7, "value": 25},
}

armour_tiers = {
    1: {"name": "Rags", "token": "r", "defn": 2, "atk": 0, "value": 1},
    2: {"name": "Cloth Armour", "token": "[", "defn": 4, "atk": 2, "value": 5},
    3: {"name": "Chainmail", "token": "{", "defn": 7, "atk": 4, "value": 12},
    4: {"name": "Runed Plate", "token": "]", "defn": 10, "atk": 7, "value": 25},
}

def get_loot_tier():
    if dungeon_level < 3:
        return 1
    elif dungeon_level < 6:
        return 2
    elif dungeon_level < 10:
        return 3
    else:
        return 4

def full_towngen():
            global current_map

            town_grid = generate_town()

            town_map = GameMap("Town", town_grid)
            
            town_map.fog_enabled = False

            for _ in range(random.randint(4, 7)):
                
                while True:
                    x = random.randint(1, town_map.width - 2)
                    y = random.randint(1, town_map.height - 2)

                    if town_grid[y][x] in [grass, stone]:
                        villager = Character("v", "Villager", x, y, True, 0, 0, 5, 0, 0)
                        town_map.add_entity(villager)
                        break

            shopkeeper = Character("S", "Shopkeeper", 27, 10, True, 1, 1, 5, 1, 0)
            shopkeeper.shopkeeper = True

            town_map.add_entity(shopkeeper)

            town_map.enter_map(Player, 0, 10)
            
            current_map = town_map

            add_message("You have arrived in a village")

def buy_item(index):
    
    item = shop_inventory[index]

    if Player.GOLD >= item.value:
        Player.GOLD -= item.value
        Player.pickup_item(item)
        add_message(f"Brought {item.name}")

    else:
        add_message("Not enough gold")

def sell_item(index):
    item = Player.inventory[index]

    Player.GOLD += item.value
    shop_inventory.append(item)
    Player.remove_item(item)

    add_message(f"Sold: {item.name}")

#We use this method to add messages to the Message Log on the screen
def add_message(text):
    global message_log

    message_log.append(text)

    if len(message_log) > MAX_LOG_LINES:
        message_log.pop(0)


#This Deals with PVE combat
def Combat():
    global game_state
    for entity in current_map.entities[:]:

        # Only process Characters
        if not isinstance(entity, Character):
            continue

        # Only process enemies
        if not entity.NPC or entity.name == "Villager" or entity.name == "Shopkeeper":
            continue

        if entity.HP <= 0:
            continue

        # Check if adjacent to player
        if abs(Player.x - entity.x) + abs(Player.y - entity.y) == 1:

            if Player.ATK > entity.DEF:
                damage = Player.ATK - entity.DEF
                entity.HP -= damage
                add_message(f"You have attacked {entity.name} for {damage} Damage!")

            if entity.ATK > Player.DEF:
                damage = entity.ATK - Player.DEF
                Player.HP -= damage
                add_message(f"Attacked for {damage} by {entity.name}!")

            if entity.HP <= 0:
                Player.GOLD += entity.GOLD
                Player.EXP += entity.EXP
                current_map.entities.remove(entity)
                add_message(f"{entity.name} Defeated You have earned {entity.GOLD} Gold!")
                add_message(f"You have gained: {entity.EXP} XP!")

            if Player.HP <= 0:
                game_state = "gameover"

#Try_Move is responisble for moving the Player and handling Player and Entity Interaction
def Try_Move(character, dx, dy):
    global dungeon_level, current_map
    new_x = character.x + dx
    new_y = character.y + dy

    if not (0 <= new_y < len(current_map.grid) and 0 <= new_x < len(current_map.grid[0])):
        return False

    tile = current_map.grid[new_y][new_x]

    if tile in [wall, water]:
        return False
    
    # Block walking into enemies
    for entity in current_map.entities:
        if isinstance(entity, Character) and entity.NPC:
            if entity.NPC and entity.x == new_x and entity.y == new_y:
                return False

    character.x = new_x
    character.y = new_y

    #Here if the Player encounters an Active Chest they will pick it up and have their stats improved
    for entity in current_map.entities[:]:
        if isinstance(entity, Item):
            if entity.x == Player.x and entity.y == Player.y:
                if Player.pickup_item(entity):
                    current_map.entities.remove(entity)


    #This handles Player and Door Interation allowing for Players to move between Levels, and if needed Generate New Levels
    if character == Player:
        if tile == door:

            if current_map.name == "Overworld":

                dungeon_level = 1

                new_floor = GameMap(
                    f"Dungeon {dungeon_level}",
                    width=55,
                    height=20
                )

                new_floor.enter_map(Player, 1, 1)
                current_map = new_floor
                add_message(f"{Player.name} decends into darkness...")

            elif current_map.name.startswith("Dungeon"):

                dungeon_level += 1

                new_floor = GameMap(
                    f"Dungeon {dungeon_level}",
                    width = 55,
                    height=20
                )

                new_floor.enter_map(Player, 1, 1)
                current_map = new_floor
                add_message(f"{Player.name} decends deeper...")

        elif tile == town:
            full_towngen()

def save_game():
    data = {
        "player": {
            "name": Player.name,
            "x": Player.x,
            "y": Player.y,
            "HP": Player.HP,
            "ATK": Player.ATK,
            "DEF": Player.DEF,
            "GOLD": Player.GOLD,
            "inventory": [
                {
                    "name": item.name,
                    "token": item.token,
                    "value": item.value,
                    "type": item.type,
                    "atk": item.atk,
                    "defn": item.defn,
                    "hp": item.hp,
                    "vision": item.vision
                }
                for item in Player.inventory
            ],
            "weapon": Player.weapon.name if Player.weapon else None,
            "armour": Player.armour.name if Player.armour else None,
            "misc": Player.misc.name if Player.misc else None
        },
        "world": {
            "map": current_map.name,
            "dungeon_level": dungeon_level
        }
    }

    with open("savegame.json", "w") as f:
        json.dump(data, f, indent=4)

    add_message("Game Saved!")

def load_game():
    global dungeon_level, current_map

    try:
        with open("savegame.json", "r") as f:
            data = json.load(f)

    except:
        add_message("No save file found!")
        return False
    
    p = data["player"]

    Player.name = p["name"]
    Player.x = p["x"]
    Player.y = p["y"]
    Player.HP = p["HP"]
    Player.ATK = p["ATK"]
    Player.DEF = p["DEF"]
    Player.GOLD = p["GOLD"]

    Player.inventory.clear()

    for item_data in p["inventory"]:
        item = Item(
            item_data["token"],
            item_data["name"],
            Player.x,
            Player.y,
            item_data["value"],
            item_data["type"],
            atk=item_data["atk"],
            defn=item_data["defn"],
            hp=item_data["hp"],
            vision=item_data["vision"]
        )
        Player.inventory.append(item)

    Player.weapon = None
    Player.armour = None
    Player.misc = None

    for item in Player.inventory:
        if item.name == p["weapon"]:
            Player.equip_item(item)
        elif item.name == p["armour"]:
            Player.equip_item(item)
        elif item.name == p["misc"]:
            Player.equip_item(item)

    dungeon_level = data["world"]["dungeon_level"]

    map_name = data["world"]["map"]

    if map_name == "Overworld":
        current_map = Overworld
    elif map_name == "Town":
        full_towngen()
    elif map_name.startswith("Dungeon"):
        current_map(map_name, width=55, height=20)

    current_map.enter_map(Player, Player.x, Player.y)

    add_message("Game Loaded!")
    return True


#This is to move the NPC's
def Foe_Move():
    for entity in current_map.entities:

        if isinstance(entity, Character) and entity.NPC:

            if not entity.shopkeeper:
                move = random.choice([(0, -1),(0, 1), (-1, 0), (1,0)])
                Try_Move(entity, *move)
            else:
                continue

#Draw_Game is responible for the Main game screen and if there are any overlays such as the Confimation window or the Inventory
#Its also responsible for the UI elements such as the Stats lower portion
#And Resposible for Fog
def Draw_Game():
    screen.fill((0, 0, 0))

    current_map.update_visibility(Player, view_radius)

    current_map.draw()

    if confirmation_window:
        overlay = pygame.Surface((MAP_PIXEL_WIDTH - 230, MAP_PIXEL_HEIGHT - 130))
        overlay.set_alpha(230)
        overlay.fill((20, 20, 20))

        screen.blit(overlay, (100, 50))

        title = font.render("Return to the surface?", True, (255, 255, 255))
        screen.blit(title, (120, 70))

        yes_text = font.render("[Y] Yes", True, (0, 255, 0))
        no_text = font.render("[N] No", True, (255, 0, 0))

        screen.blit(yes_text, (120, 110))
        screen.blit(no_text, (120, 135))

    footer_rect = pygame.Rect(
        0,
        MAP_PIXEL_HEIGHT,
        MAP_PIXEL_WIDTH,
        UI_HEIGHT
    )

    pygame.draw.rect(screen, (25, 25, 25), footer_rect)
    pygame.draw.line(
        screen,
        (80, 80, 80),
        (0, MAP_PIXEL_HEIGHT),
        (MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT),
        2
    )

    stats_text = f"{Player.name} | LEVEL: {Player.level} | ATK: {Player.ATK} | DEF: {Player.DEF} | HP: {Player.HP} | GOLD: {Player.GOLD} | XP: {Player.EXP} | Current Level: {current_map.name}"
    stats_surface = font.render(stats_text, True, (255, 255, 255))
    screen.blit(stats_surface, (10, MAP_PIXEL_HEIGHT + 5))


    log_x = 10
    log_y = MAP_PIXEL_HEIGHT + 30

    for i, msg in enumerate(message_log):
        text_surface = font.render(msg, True, (180, 180, 180))
        screen.blit(text_surface, (log_x, log_y + i * 20))

    pygame.display.flip()

#This handles the Main Menu allowing for Player Name Imput
def Draw_Main_Menu():
    screen.fill((0, 0, 0))

    # Title
    title = font.render("===ESTORIA===", True, (255,255,0))
    title_rect = title.get_rect(center=(MAP_PIXEL_WIDTH // 2, 80))
    screen.blit(title, title_rect)

    # Prompt
    prompt = font.render("Enter The Hero's Name:", True, (200,200,200))
    prompt_rect = prompt.get_rect(center=(MAP_PIXEL_WIDTH // 2, 150))
    screen.blit(prompt, prompt_rect)

    # Name input (aligned perfectly with prompt)
    name_surface = font.render(player_name_input + "_", True, (255,255,0))
    name_rect = name_surface.get_rect(center=(MAP_PIXEL_WIDTH // 2, 180))
    screen.blit(name_surface, name_rect)

    # Info
    info = font.render("Enter = New Game | F6 = Load Game | ESC = Exit", True, (150,150,150))
    info_rect = info.get_rect(center=(MAP_PIXEL_WIDTH // 2, 240))
    screen.blit(info, info_rect)

    pygame.display.flip()

#Here we handle The Game Over Screen
def Draw_Game_Over():
    screen.fill((0, 0, 0))

    title = font.render("====GAME OVER====", True, (255, 0, 0))
    screen.blit(title, (MAP_PIXEL_WIDTH // 2 - 80, 100))

    name_text = font.render(f"Rest in Peace: {Player.name}", True, (200, 200, 200))
    screen.blit(name_text, (MAP_PIXEL_WIDTH // 2 - 100, 150))

    info = font.render("Press R to Restart", True, (150, 150, 150))
    screen.blit(info, (MAP_PIXEL_WIDTH // 2 - 100, 200))

    pygame.display.flip()

#Tis is the Shop's Menu
def Draw_Shop():

    screen.fill((0, 0, 0))

    # Titles
    title = font.render("==SHOP KEEPER==", True, (255,255,255))
    title_rect = title.get_rect(center=(MAP_PIXEL_WIDTH // 2, 20))
    screen.blit(title, title_rect)

    gold_text = font.render(f"Gold: {Player.GOLD}", True, (255, 215, 0))
    screen.blit(gold_text, (10,30))

    left_x = 20
    right_x = MAP_PIXEL_WIDTH // 2 + 20
    y_start = 90

    shop_title_color = (255, 255, 255) if shop_panel == "shop" else (180, 180, 180)
    shop_title = font.render("SHOP", True, shop_title_color)
    screen.blit(shop_title, (left_x, 50))

    for i, item in enumerate(shop_inventory):
        color = (255, 255, 0) if (shop_panel == "shop" and i == shop_selected_index) else (200, 200, 200)
        text = f"{item.name} - {item.value}g"
        line = font.render(text, True, color)
        screen.blit(line, (left_x, y_start + i * 20))

    player_title_color = (255, 255, 255) if shop_panel == "player" else (180, 180, 180)
    player_title = font.render("INVENTORY", True, player_title_color)
    screen.blit(player_title, (right_x, 50))

    for i, item in enumerate(Player.inventory):
        color = (255, 255, 0) if (shop_panel == "player" and i == shop_selected_index) else (200, 200, 200)
        if item.equipped:
            text = f"{item.name} (+{item.value}g) (equipped)"
        else:
            text = f"{item.name} (+{item.value}g)"
        line = font.render(text, True, color)
        screen.blit(line, (right_x, y_start + i * 20))

    log_y = MAP_PIXEL_HEIGHT - 60
    for i, msg in enumerate(message_log):
        text_surface = font.render(msg, True, (180, 180, 180))
        screen.blit(text_surface, (10, log_y + i * 20))

    help_text = font.render("(Left and Right): Switch Menus | (Up and Down): Select items | ENTER: Buy/Sell | Q: Exit", True, (150, 150, 150))
    screen.blit(help_text, (10, MAP_PIXEL_HEIGHT - 20))

    pygame.display.flip()

def Draw_Inventory():
    screen.fill((0, 0, 0))

    title = font.render("===INVENTORY===", True, (255,255,255))
    title_rect = title.get_rect(center=(MAP_PIXEL_WIDTH // 2, 40))
    screen.blit(title, title_rect)

    left_x = 20
    full_meter = inv_limit - len(Player.inventory)

    if check_inv_full():
        invcolour = (255, 0, 0)
        text = f"Free Slots: {full_meter}/5 (Full: walking speed Reduced!)"
    else:
        invcolour = (200, 200, 200)
        text = f"Free Slots: {full_meter}/5"
    inventory_cap_text = font.render(text, True, invcolour)
    screen.blit(inventory_cap_text, (left_x, 60))

    weapon_text = font.render(f"Weapon: {Player.weapon.name if Player.weapon else 'None'}", True, (200,200,200))
    screen.blit(weapon_text, (left_x, 80))

    armour_text = font.render(f"Armour: {Player.armour.name if Player.armour else 'None'}", True, (200,200,200))
    screen.blit(armour_text, (left_x, 100))

    misc_text = font.render(f"Equipment: {Player.misc.name if Player.misc else 'None'}", True, (200, 200, 200))
    screen.blit(misc_text, (left_x, 120))

    for i, item in enumerate(Player.inventory):
        color = (255,255,0) if i == inventory_selected else (200,200,200)
        if item.equipped:
            text = font.render(f"{item.name} (ATK: +{item.atk} | DEF: +{item.defn} | HP: +{item.hp}) (equipped)", True, color)
        else:
            text = font.render(f"{item.name} (ATK: +{item.atk} | DEF: +{item.defn} | HP: +{item.hp})", True, color)
        screen.blit(text, (left_x + 20, 160 + i * 25))



    help_text = font.render("(Up and Down): Select items | ENTER: Equip/Unequip | U: Unequip All | Q: Exit | T: Trash", True, (150, 150, 150))
    screen.blit(help_text, (10, MAP_PIXEL_HEIGHT - 40))

    msg = message_log[-1]
    log_y = MAP_PIXEL_HEIGHT - 20
    text_surface = font.render(msg, True, (180, 180, 180))
    screen.blit(text_surface, (10, log_y))

    pygame.display.flip()

#Player Stats Screen
def Draw_Player_stats():
    screen.fill((0, 0, 0))

    title = font.render(f"==={Player.name}'s STATS===", True, (255,255,255))
    title_rect = title.get_rect(center=(MAP_PIXEL_WIDTH // 2, 40))
    screen.blit(title, title_rect)

    left_x = 20

    player_name = font.render(f"Name: {Player.name}", True, (255, 255, 255))
    screen.blit(player_name, (left_x, 100))

    player_gold = font.render(f"Gold: {Player.GOLD}", True, (255, 215, 0))
    screen.blit(player_gold, (left_x, 120))

    player_level = font.render(f"Level: {Player.level}", True, (200, 200, 200))
    screen.blit(player_level, (left_x, 140))

    xpcap = font.render(f"XP needed to Level Up: {exp_cap - Player.EXP}", True, (200, 200, 200))
    screen.blit(xpcap, (left_x, 160))

    player_exp = font.render(f"XP: {Player.EXP}", True, (200, 200, 200))
    screen.blit(player_exp, (left_x, 180))

    upgrade_points = font.render(f"Upgrade Points: {Player.upgrade_points}", True, (200, 200, 200))
    screen.blit(upgrade_points, (left_x, 200))

    for i, stat in enumerate(Player_Stats):
        color = (255, 255, 0) if (i == stats_selected_index) else (200, 200, 200)
        text = f"{Stat_names[i]}: {stat}"
        line = font.render(text, True, color)
        screen.blit(line, (left_x + 20, 220 + i * 20))


    help_text = font.render("(Up and Down): Select items | ENTER: Upgrade | Q: Exit", True, (150, 150, 150))
    screen.blit(help_text, (10, MAP_PIXEL_HEIGHT - 30))

    msg = message_log[-1]
    log_y = MAP_PIXEL_HEIGHT - 10
    text_surface = font.render(msg, True, (180, 180, 180))
    screen.blit(text_surface, (10, log_y))

    pygame.display.flip()

#Here we have the main Game Loop
def Game_Loop():
    global playerLastMove, last_move_time
    global inventory_selected
    global game_state, player_name_input, Player
    global confirmation_window, dungeon_level
    global shop_selected_index, shop_panel
    global shop_open, current_map, stats_selected_index

    running = True

    while running:
        clock.tick(60)

        # =====================
        # MENU STATE
        # =====================
        if game_state == "menu":

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_RETURN:
                        if player_name_input.strip() == "":
                            player_name_input = "Hero"

                        Player.name = player_name_input
                        Player.HP = 20
                        spawn_x, spawn_y = find_safe_spawn(overworld_grid)
                        Overworld.enter_map(Player, spawn_x, spawn_y)
                        current_map = Overworld
                        game_state = "game"
                        add_message("Welcome to Estroria!")

                    elif event.key == pygame.K_BACKSPACE:
                        player_name_input = player_name_input[:-1]
                    elif event.key == pygame.K_F6:
                        if load_game():
                            game_state = "game"

                    else:
                        if len(player_name_input) < 12 and event.unicode.isprintable():
                            player_name_input += event.unicode

            Draw_Main_Menu()
            continue

        # =====================
        # GAME OVER STATE
        # =====================
        if game_state == "gameover":

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:

                        # Reset player
                        Player.HP = 20
                        Player.GOLD = 0
                        Player.inventory.clear()
                        Player.weapon = None
                        Player.armour = None
                        Player.misc = None
                        Player.ATK = 3
                        Player.DEF = 2
                        Player.EXP = 0
                        Player.level = 1
                        Player.max_health = 20

                        game_state = "menu"

            Draw_Game_Over()
            continue
 
        if game_state == "shop":

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        shop_open = False
                        game_state = "game"
                            
                    elif event.key == pygame.K_LEFT:
                        shop_panel = "shop"
                        shop_selected_index = 0

                    elif event.key == pygame.K_RIGHT:
                        shop_panel = "player"
                        shop_selected_index = 0

                    elif event.key == pygame.K_UP:
                        shop_selected_index = max(0, shop_selected_index - 1)

                    elif event.key == pygame.K_DOWN:
                        if shop_panel == "shop":
                            shop_selected_index = min(len(shop_inventory) - 1, shop_selected_index + 1)
                        else:
                            shop_selected_index = min(len(Player.inventory) - 1, shop_selected_index + 1)

                    elif event.key == pygame.K_RETURN:
                                
                        if shop_panel == "shop":
                            if shop_inventory:
                                buy_item(shop_selected_index)
                                
                        elif shop_panel == "player":
                            if Player.inventory:
                                item = Player.inventory[shop_selected_index]

                                if item.equipped:
                                    add_message("Unequip item first!")
                                else:
                                    sell_item(shop_selected_index)
                                    shop_selected_index = max(0, shop_selected_index - 1)
            Draw_Shop()
            continue

        if game_state == "stats":

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_q or event.key == pygame.K_l:
                        game_state = "game"

                    elif event.key == pygame.K_UP:
                        stats_selected_index = max(0, stats_selected_index -1)

                    elif event.key == pygame.K_DOWN:
                        stats_selected_index = min(len(Player_Stats) - 1, stats_selected_index + 1)

                    elif event.key == pygame.K_RETURN:
                        if Player.upgrade_points > 0:
                            Player_Stats[stats_selected_index] += 1
                            Player.upgrade_points -= 1
            
            Draw_Player_stats()
            continue

        if game_state == "inventory":

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_q or event.key == pygame.K_e:
                        game_state = "game"
                    
                    elif event.key == pygame.K_UP:
                        inventory_selected = max(0, inventory_selected - 1)
                    
                    elif event.key == pygame.K_DOWN:
                        inventory_selected = min(len(Player.inventory) - 1, inventory_selected + 1)

                    elif event.key == pygame.K_RETURN:
                        item = Player.inventory[inventory_selected]

                        if item.type == "potion":
                            Player.use_potion(item)
                            Player.inventory.remove(item)

                        else:
                            if item.equipped:
                                Player.unequip_item(item)
                            else:
                                Player.equip_item(item)
                    
                    elif event.key == pygame.K_u:
                        if Player.weapon:
                            Player.weapon.equipped = False
                        if Player.armour:
                            Player.armour.equipped = False
                        if Player.misc:
                            Player.misc.equipped = False
                        Player.armour = None
                        Player.weapon = None
                        Player.misc = None

                    elif event.key == pygame.K_t:
                        item = Player.inventory[inventory_selected]

                        if item.equipped:
                            add_message("Unable to Trash Equipped Item!")
                        else:
                            Player.inventory.remove(item)
                            add_message("Item Trashed!")

            Draw_Inventory()
            continue

        # =====================
        # GAME STATE
        # =====================
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:

                if confirmation_window:

                    if event.key == pygame.K_y:
                        spawn_x, spawn_y = find_safe_spawn(overworld_grid)
                        Overworld.enter_map(Player, spawn_x, spawn_y)
                        current_map = Overworld
                        dungeon_level = 0
                        confirmation_window = False
                        add_message("You return to the surface.")

                    elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                        confirmation_window = False

                else:
                    if event.key == pygame.K_RETURN:
                        for entity in current_map.entities:
                            if isinstance(entity, Character) and entity.shopkeeper:
                                if max(abs(Player.x - entity.x), abs(Player.y - entity.y)) <= 1:
                                    game_state = "shop"
                                    shop_open = True
                                    break
                    elif event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_e:
                        game_state = "inventory"
                    elif event.key == pygame.K_r:
                        confirmation_window = True
                    elif event.key == pygame.K_l:
                        game_state = "stats"      
                    elif event.key == pygame.K_F5:
                        save_game()

        if not game_state == "inventory" and not confirmation_window and not shop_open and not game_state == "stats":
            keys = pygame.key.get_pressed()

            move_x = 0
            move_y = 0

            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move_y = -1
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move_y = 1
            elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move_x = -1
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move_x = 1
            
            current_time = pygame.time.get_ticks()

            if move_x != 0 or move_y != 0:
                # Determine current tile movement delay
                current_tile = current_map.grid[Player.y][Player.x]

                if current_tile == tree:
                    delay = FOREST_MOVE_DELAY
                elif check_inv_full():
                    delay = FOREST_MOVE_DELAY
                else:
                    delay = MOVE_DELAY

                if current_time - last_move_time > delay:
                    Try_Move(Player, move_x, move_y)
                    check_level_up()
                    Combat()
                    Foe_Move()
                    last_move_time = current_time

        if Player.HP <= 0:
            game_state = "gameover"

        Draw_Game()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    Game_Loop()