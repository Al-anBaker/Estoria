#=======
#IMPORTS
#=======
import random
import os
import sys
import pygame

#====================
#Pygame Initalization
#====================
pygame.init()

TILE_SIZE = 16
MOVE_DELAY = 120
last_move_time = 0

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
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

pygame.display.set_caption("===ASCII DUNGEION===")


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
    wall: (200, 200, 200),
    empty: (40, 40, 40),
    water: (0, 0, 255),
    "@": (255, 255, 0), #Player
    "%": (255, 0, 255), #Legacy Foe
    "[": (0, 255, 0), #Leather Armour
    "/": (0, 255, 0), #Dagger
    "!": (0, 255, 0), #Health Potion
    ">": (0, 255, 255), #Door
    "g": (255, 0, 0), #Goblin
    "o": (255, 0, 0), #Orc
    "D": (255, 50, 50), #Demon
    "|": (255, 140, 0), #Torch
    grass: (20, 120, 20), #Grass
    tree: (0, 140, 0), #Tree
    stone: (120, 120, 120), #Stone
    town: (255, 255, 255), #Town
    "v": (140, 220, 140), #Villagers
    "S": (255, 215, 0), #Shop Clerk
    "l": (165, 42, 42) #Stick
}

def get_color(char):
    return color_map.get(char, (255, 255, 255))



#===============
#Global Varibles
#===============
command = ""
playerLastMove = True
dungeon_level = 0
inventory_open = False
inventory_selected = 0
message_log = []
MAX_LOG_LINES = 2
view_radius = 6
game_state = "menu"
player_name_input =""
OVERWORLD_WIDTH = 55
OVERWORLD_HEIGHT = 20
confirmation_window = False
FOREST_MOVE_DELAY = 220
shop_selected_index = 0
shop_panel = "shop" # "shop" or "player"
shop_open = False

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



class Character():
    #Character Vars
    def __init__(self, token, name, x, y, NPC, ATK, DEF, HP, GOLD, current_map=None):

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

        self.exp = 0
        self.level = 1

    #Adds an Item to the Inventory and Informs the Player
    def pickup_item(self, item):
        self.inventory.append(item)
        add_message(f"You have picked up a: {item.name}")

    #When in the inventory this add the Item from the Inventory to be a held item
    def equip_item(self, item):
        global view_radius
        if item.type == "weapon":
            if self.weapon:
                self.ATK -= self.weapon.atk
            self.weapon = item
            self.ATK += item.atk

        elif item.type == "armour":
            if self.armour:
                self.DEF -= self.armour.defn
            self.armour = item
            self.DEF += item.defn

        elif item.type == "misc":
            if self.misc:
                view_radius -= self.misc.vision
            self.misc = item
            view_radius += item.vision


    #Like the Equip Item but unequips instead
    def unequip_item(self, slot):
        global view_radius
        if slot == "weapon" and self.weapon:
            self.ATK -= self.weapon.atk
            self.weapon = None
        elif slot == "armour" and self.armour:
            self.DEF -= self.armour.defn
            self.armour = None

        elif slot == "equipment" and self.misc:
            view_radius -= self.misc.vision
            self.misc = None

    #For Consumables to give a temporary boot to the Player or Heal
    def use_potion(self, item):
        self.HP += item.hp
        add_message("Used Potion")
        if self.HP > 20:
            self.HP = 20

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
        
        item_count = random.randint(2, 5)

        for _ in range(item_count):
            room = random.choice(self.rooms)

            rx, ry, rw, rh = room

            x = random.randint(rx + 1, rx + rw - 2)
            y = random.randint(ry + 1, ry + rh - 2)

            if self.grid != empty:
                continue
        
        roll = random.random()

        if roll < 0.3:
            item = Item("!", "Health Potion", x, y, 10, item_type="potion", hp=5)
        elif roll < 0.7:
            item = Item("/", "Dagger", x, y, 5, item_type="weapon", atk=2)
        elif roll < 0.9:
            item = Item("|", "Torch", x, y, 10, item_type="misc", vision=2)
        else:
            item = Item("[", "Leather Armour", x, y, 5, item_type="armour", defn=2)

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
        
        base_count = random.randint(3, 6)

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

            roll = random.random()

            if roll < 0.6:
                foe = Character("g", "Goblin", x, y, True, 2, 1, 10, 5)
            elif roll < 0.9:
                foe = Character("o", "Orc", x, y, True, 3, 2, 15, 3)
            else:
                foe = Character("D", "Demon", x, y, True, 5, 3, 20, 5)

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
Player = Character("@", "Player", 7, 13, False, 3, 2, 20, 0)

def find_safe_spawn(grid):
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            if grid[y][x] == grass:
                return x, y
    return 1, 1  # fallback


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
stick = Item("l", "Stick", 2, 2, 1, item_type="weapon", atk=2)
current_map = Overworld
current_map.add_entity(stick)

shop_inventory = [
    Item("}", "Platemail", 0, 0, 25, item_type="armour", defn=6),
    Item(">", "Spear", 0, 0, 20, item_type="weapon", atk=5),
    Item("!!", "Greater Health Potion", 0, 0, 10, item_type="potion", hp=10)
]


#Draw_Game prints the Map onto the window, we do this by interating through both the x axis and y axis 
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

    if inventory_open:
        overlay = pygame.Surface((MAP_PIXEL_WIDTH - 200, MAP_PIXEL_HEIGHT - 100))
        overlay.set_alpha(220)
        overlay.fill((20, 20, 20))

        screen.blit(overlay, (100, 50))

        title = font.render("===INVENTORY===", True, (255,255,255))
        screen.blit(title, (120, 60))

        weapon_text = font.render(f"Weapon: {Player.weapon.name if Player.weapon else 'None'}", True, (200,200,200))
        armour_text = font.render(f"Armour: {Player.armour.name if Player.armour else 'None'}", True, (200,200,200))
        misc_text = font.render(f"Equipment: {Player.misc.name if Player.misc else 'None'}", True, (200, 200, 200))

        screen.blit(weapon_text, (120, 90))
        screen.blit(armour_text, (120, 110))
        screen.blit(misc_text, (120, 130))

        for i, item in enumerate(Player.inventory):
            color = (255,255,0) if i == inventory_selected else (200,200,200)
            text = font.render(item.name, True, color)
            screen.blit(text, (120, 180 + i * 25))

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

    stats_text = f"{Player.name} | LEVEL: {Player.level} | ATK: {Player.ATK} | DEF: {Player.DEF} | HP: {Player.HP} | GOLD: {Player.GOLD} | XP: {Player.exp}| Current Level: {current_map.name}"
    stats_surface = font.render(stats_text, True, (255, 255, 255))
    screen.blit(stats_surface, (10, MAP_PIXEL_HEIGHT + 5))


    log_x = 10
    log_y = MAP_PIXEL_HEIGHT + 30

    for i, msg in enumerate(message_log):
        text_surface = font.render(msg, True, (180, 180, 180))
        screen.blit(text_surface, (log_x, log_y + i * 20))

    pygame.display.flip()

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
                current_map.entities.remove(entity)
                add_message(f"{entity.name} Defeated You have earned {entity.GOLD} Gold!")

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
                Player.pickup_item(entity)
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

            town_grid = generate_town()


            town_map = GameMap("Town", town_grid)
            
            town_map.fog_enabled = False

            for _ in range(random.randint(4, 7)):
                
                while True:
                    x = random.randint(1, town_map.width - 2)
                    y = random.randint(1, town_map.height - 2)

                    if town_grid[y][x] in [grass, stone]:
                        villager = Character("v", "Villager", x, y, True, 0, 0, 5, 0)
                        town_map.add_entity(villager)
                        break

            shopkeeper = Character("S", "Shopkeeper", 27, 10, True, 1, 1, 5, 1)
            shopkeeper.shopkeeper = True

            town_map.add_entity(shopkeeper)

            town_map.enter_map(Player, 0, 10)
            
            current_map = town_map

            add_message("You have arrived in a village")


#This is to move the NPC
def Foe_Move():

    for entity in current_map.entities:

        if isinstance(entity, Character) and entity.NPC:

            if not entity.shopkeeper:
                move = random.choice([(0, -1),(0, 1), (-1, 0), (1,0)])
                Try_Move(entity, *move)
            else:
                continue

def Draw_Main_Menu():
    screen.fill((0, 0, 0))

    # Title
    title = font.render("===ASCII DUNGEON===", True, (255,255,255))
    title_rect = title.get_rect(center=(MAP_PIXEL_WIDTH // 2, 80))
    screen.blit(title, title_rect)

    # Prompt
    prompt = font.render("Enter Your Hero's Name:", True, (200,200,200))
    prompt_rect = prompt.get_rect(center=(MAP_PIXEL_WIDTH // 2, 150))
    screen.blit(prompt, prompt_rect)

    # Name input (aligned perfectly with prompt)
    name_surface = font.render(player_name_input + "_", True, (255,255,0))
    name_rect = name_surface.get_rect(center=(MAP_PIXEL_WIDTH // 2, 180))
    screen.blit(name_surface, name_rect)

    # Info
    info = font.render("Press ENTER to Start", True, (150,150,150))
    info_rect = info.get_rect(center=(MAP_PIXEL_WIDTH // 2, 240))
    screen.blit(info, info_rect)

    pygame.display.flip()

def Draw_Game_Over():
    screen.fill((0, 0, 0))

    title = font.render("====GAME OVER====", True, (255, 0, 0))
    screen.blit(title, (MAP_PIXEL_WIDTH // 2 - 80, 100))

    name_text = font.render(f"Rest in Peace: {Player.name}", True, (200, 200, 200))
    screen.blit(name_text, (MAP_PIXEL_WIDTH // 2 - 100, 150))

    info = font.render("Press R to Restart", True, (150, 150, 150))
    screen.blit(info, (MAP_PIXEL_WIDTH // 2 - 100, 200))

    pygame.display.flip()

def Draw_Shop():

    screen.fill((0, 0, 0))

    # Titles
    title = font.render("==SHOP==", True, (255, 255, 255))
    screen.blit(title, (10, 10))

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

#Here we have the main Game Loop
def Game_Loop():
    global playerLastMove, last_move_time
    global inventory_open, inventory_selected
    global game_state, player_name_input, Player
    global confirmation_window, dungeon_level
    global shop_selected_index, shop_panel
    global shop_open, current_map

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

                    if event.key == pygame.K_RETURN:
                        if player_name_input.strip() == "":
                            player_name_input = "Hero"

                        Player.name = player_name_input
                        Player.HP = 20
                        spawn_x, spawn_y = find_safe_spawn(overworld_grid)
                        Overworld.enter_map(Player, spawn_x, spawn_y)
                        current_map = Overworld
                        game_state = "game"

                    elif event.key == pygame.K_BACKSPACE:
                        player_name_input = player_name_input[:-1]

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
                        Player.exp = 0
                        Player.level = 1

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

                                if item in [Player.weapon, Player.armour, Player.misc]:
                                    add_message("Unequip item first!")
                                else:
                                    sell_item(shop_selected_index)
                                    shop_selected_index = max(0, shop_selected_index - 1)
            Draw_Shop()
            continue

        # =====================
        # GAME STATE
        # =====================
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:

                if inventory_open:

                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_e:
                        inventory_open = False

                    elif event.key == pygame.K_UP:
                        inventory_selected = max(0, inventory_selected - 1)

                    elif event.key == pygame.K_DOWN:
                        inventory_selected = min(len(Player.inventory)-1, inventory_selected + 1)

                    elif event.key == pygame.K_RETURN:
                        if Player.inventory:
                            item = Player.inventory[inventory_selected]

                            if item.type == "potion":
                                Player.use_potion(item)
                                Player.inventory.remove(item)
                            else:
                                if item in [Player.armour, Player.weapon, Player.misc]:
                                    Player.unequip_item(item)
                                else:
                                    Player.equip_item(item)

                elif confirmation_window:

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
                                print("Shopkeepers position: ", entity.x, entity.y)
                                if max(abs(Player.x - entity.x), abs(Player.y - entity.y)) <= 1:
                                    print("Player next to Shopkeeper")
                                    game_state = "shop"
                                    shop_open = True
                                    break
                    elif event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_e:
                        inventory_open = True
                    elif event.key == pygame.K_r:
                        confirmation_window = True

                                    

        if not inventory_open and not confirmation_window and not shop_open:
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
                else:
                    delay = MOVE_DELAY

                if current_time - last_move_time > delay:
                    Try_Move(Player, move_x, move_y)
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