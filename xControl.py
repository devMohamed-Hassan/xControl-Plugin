from phBot import *
from threading import Timer
import phBotChat
import QtBind
import struct
import random
import json
import os
import sqlite3

pName = 'xControl'
pVersion = '1.8.2'
pUrl = 'https://github.com/devMohamed-Hassan/xControl-Plugin'

# ______________________________ Initializing ______________________________ #

# Globals
inGame = None
followActivated = False
followPlayer = ''
followDistance = 0
here = False

# Graphic user interface
gui = QtBind.init(__name__, pName)
QtBind.createLabel(gui,
                   'Control your party using in-game chat. Leader writes commands and your character will follow it.',
                   11, 11)

QtBind.createLabel(gui, '< COMMAND (uppercased) #Variable (required) #Variable? (optional) >', 11, 30)
QtBind.createLabel(gui,
                   '- START : Start bot\n- STOP : Stop bot\n- TR #Player? : Start trace to leader or another player\n- NOTRACE : Stop trace\n- RETURN : Use some "Return Scroll" from your inventory\n- TP #A #B : Use teleport from location A to B\n- RECALL #Town : Set recall on city portal\n- ZERK : Use berserker mode if is available\n- GETOUT : Left party\n- MOVEON #Radius? : Set a random movement\n- MOUNT #PetType? : Mount horse by default\n- DISMOUNT #PetType? : Dismount horse by default\n- SETPOS #PosX? #PosY? #Region? #PosZ? : Set training position\n- SETRADIUS #Radius? : Set training radius\n- SETSCRIPT #Path? : Change script path for training area\n- SETAREA #Name : Changes training area by config name\n- PROFILE #Name? : Loads a profile by his name\n- DC : Disconnect from game',
                   15, 45)
QtBind.createLabel(gui,
                   '- INJECT #Opcode #Encrypted? #Data? : Inject packet\n- CHAT #Type #Message : Send any message type\n- FOLLOW #Player? #Distance? : Trace a party player using distance\n- NOFOLLOW : Stop following\n- JUMP : Generate knockback visual effect\n- SIT : Sit or Stand up, depends\n- CAPE #Type? : Use PVP Cape\n- EQUIP #ItemName : Equips an item from inventory\n- UNEQUIP #ItemName : Unequips item from character\n- REVERSE #Type #Name?\n- GETPOS : Gets current position',
                   345, 80)

tbxLeaders = QtBind.createLineEdit(gui, "", 525, 11, 110, 20)
lstLeaders = QtBind.createList(gui, 525, 32, 110, 38)
lstHere = QtBind.createList(gui, 525, 200, 110, 38)
btnAddLeader = QtBind.createButton(gui, 'btnAddLeader_clicked', "    Add   ", 635, 10)
btnRemLeader = QtBind.createButton(gui, 'btnRemLeader_clicked', "     Remove     ", 635, 32)


# ______________________________ Methods ______________________________ #

# Return xControl folder path
def getPath():
    return get_config_dir() + pName + "\\"


# Return character configs path (JSON)
def getConfig():
    return getPath() + inGame['server'] + "_" + inGame['name'] + ".json"


# Check if character is ingame
def isJoined():
    global inGame
    inGame = get_character_data()
    if not (inGame and "name" in inGame and inGame["name"]):
        inGame = None
    return inGame


# Load default configs
def loadDefaultConfig():
    # Clear data
    QtBind.clear(gui, lstLeaders)


# Loads all config previously saved
def loadConfigs():
    loadDefaultConfig()
    if isJoined():
        # Check config exists to load
        if os.path.exists(getConfig()):
            data = {}
            with open(getConfig(), "r") as f:
                data = json.load(f)
            if "Leaders" in data:
                for nickname in data["Leaders"]:
                    QtBind.append(gui, lstLeaders, nickname)


def change_here(here):
    QtBind.clear(gui, lstHere)
    QtBind.append(gui, lstHere, here)


# Add leader to the list
def btnAddLeader_clicked():
    if inGame:
        player = QtBind.text(gui, tbxLeaders)
        # Player nickname it's not empty
        if player and not lstLeaders_exist(player):
            # Init dictionary
            data = {}
            # Load config if exist
            if os.path.exists(getConfig()):
                with open(getConfig(), 'r') as f:
                    data = json.load(f)
            # Add new leader
            if not "Leaders" in data:
                data['Leaders'] = []
            data['Leaders'].append(player)
            # Replace configs
            with open(getConfig(), "w") as f:
                f.write(json.dumps(data, indent=4, sort_keys=True))
            QtBind.append(gui, lstLeaders, player)
            QtBind.setText(gui, tbxLeaders, "")
            log('Plugin: Leader added [' + player + ']')


# Remove leader selected from list
def btnRemLeader_clicked():
    if inGame:
        selectedItem = QtBind.text(gui, lstLeaders)
        if selectedItem:
            if os.path.exists(getConfig()):
                data = {"Leaders": []}
                with open(getConfig(), 'r') as f:
                    data = json.load(f)
                try:
                    # remove leader nickname from file if exists
                    data["Leaders"].remove(selectedItem)
                    with open(getConfig(), "w") as f:
                        f.write(json.dumps(data, indent=4, sort_keys=True))
                except:
                    pass  # just ignore file if doesn't exist
            QtBind.remove(gui, lstLeaders, selectedItem)
            log('Plugin: Leader removed [' + selectedItem + ']')


# Return True if nickname exist at the leader list
def lstLeaders_exist(nickname):
    nickname = nickname.lower()
    players = QtBind.getItems(gui, lstLeaders)
    for i in range(len(players)):
        if players[i].lower() == nickname:
            return True
    return False


# Inject teleport packet, using the source and destination name
def inject_teleport(source, destination):
    t = get_teleport_data(source, destination)
    if t:
        npcs = get_npcs()
        for key, npc in npcs.items():
            if npc['name'] == source or npc['servername'] == source:
                log("Plugin: Selecting teleporter [" + source + "]")
                # Teleport found, select it
                inject_joymax(0x7045, struct.pack('<I', key), False)
                # Start a timer to teleport in 2.0 seconds
                Timer(2.0, inject_joymax, (0x705A, struct.pack('<IBI', key, 2, t[1]), False)).start()
                Timer(2.0, log, ("Plugin: Teleporting to [" + destination + "]")).start()
                return
        log('Plugin: NPC not found. Wrong NPC name or servername')
    else:
        log('Plugin: Teleport data not found. Wrong teleport name or servername')


# Send message, Ex. "All Hello World!" or "private Kapalo Hi!"
def handleChatCommand(msg):
    # Try to split message
    args = msg.split(' ', 1)
    # Check if the format is correct and is not empty
    if len(args) != 2 or not args[0] or not args[1]:
        return
    # Split correctly the message
    t = args[0].lower()
    if t == 'private' or t == 'note':
        # then check message is not empty
        argsExtra = args[1].split(' ', 1)
        if len(argsExtra) != 2 or not argsExtra[0] or not argsExtra[1]:
            return
        args.pop(1)
        args += argsExtra
    # Check message type
    sent = False
    if t == "all":
        sent = phBotChat.All(args[1])
    elif t == "private":
        sent = phBotChat.Private(args[1], args[2])
    elif t == "party":
        sent = phBotChat.Party(args[1])
    elif t == "guild":
        sent = phBotChat.Guild(args[1])
    elif t == "union":
        sent = phBotChat.Union(args[1])
    elif t == "note":
        sent = phBotChat.Note(args[1], args[2])
    elif t == "stall":
        sent = phBotChat.Stall(args[1])
    elif t == "global":
        sent = phBotChat.Global(args[1])
    if sent:
        log('Plugin: Message "' + t + '" sent successfully!')


# Move to a random position from the actual position using a maximum radius
def randomMovement(radiusMax=10):
    # Generating a random new point
    pX = random.uniform(-radiusMax, radiusMax)
    pY = random.uniform(-radiusMax, radiusMax)
    # Mixing with the actual position
    p = get_position()
    pX = pX + p["x"]
    pY = pY + p["y"]
    # Moving to new position
    move_to(pX, pY, p["z"])
    log("Plugin: Random movement to (X:%.1f,Y:%.1f)" % (pX, pY))


# Follow a player using distance. Return success
def start_follow(player, distance):
    if party_player(player):
        global followActivated, followPlayer, followDistance
        followPlayer = player
        followDistance = distance
        followActivated = True
        return True
    return False


# Return True if the player is in the party
def party_player(player):
    players = get_party()
    if players:
        for p in players:
            if players[p]['name'] == player:
                return True
    return False


# Return point [X,Y] if player is in the party and near, otherwise return None
def near_party_player(player):
    players = get_party()
    if players:
        for p in players:
            if players[p]['name'] == player and players[p]['player_id'] > 0:
                return players[p]
    return None


# Calc the distance from point A to B
def GetDistance(ax, ay, bx, by):
    return ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5


# Stop follow player
def stop_follow():
    global followActivated, followPlayer, followDistance
    result = followActivated
    # stop
    followActivated = False
    followPlayer = ""
    followDistance = 0
    return result


# Try to summon a vehicle
def MountHorse():
    items = get_inventory()['items']
    for slot, item in enumerate(items):
        if item:
            sn = item['servername']
            # Search some kind vehicle by servername
            if '_C_' in sn:
                packet = struct.pack('B', slot)
                packet += struct.pack('H', 4588 + (1 if sn.endswith('_SCROLL') else 0))  # Silk scroll
                inject_joymax(0x704C, packet, True)
                return True
    log('Plugin: Horse not found at your inventory')
    return False


# Try to mount pet by type, return success
def MountPet(petType):
    # just in case
    if petType == 'pick':
        return False
    elif petType == 'horse':
        return MountHorse()
    # get all summoned pets
    pets = get_pets()
    if pets:
        for uid, pet in pets.items():
            if pet['type'] == petType:
                p = b'\x01'  # mount flag
                p += struct.pack('I', uid)
                inject_joymax(0x70CB, p, False)
                return True
    return False


# Try to dismount pet by type, return success
def DismountPet(petType):
    petType = petType.lower()
    # just in case
    if petType == 'pick':
        return False
    # get all summoned pets
    pets = get_pets()
    if pets:
        for uid, pet in pets.items():
            if pet['type'] == petType:
                p = b'\x00'
                p += struct.pack('I', uid)
                inject_joymax(0x70CB, p, False)
                return True
    return False


# Gets the NPC unique ID if the specified name is found near
def GetNPCUniqueID(name):
    NPCs = get_npcs()
    if NPCs:
        name = name.lower()
        for UniqueID, NPC in NPCs.items():
            NPCName = NPC['name'].lower()
            if name == NPCName:
                return UniqueID
    return 0


# Search an item by name or servername through lambda expression and return his information
def GetItemByExpression(_lambda, start=0, end=0):
    inventory = get_inventory()
    items = inventory['items']
    if end == 0:
        end = inventory['size']
    # check items between intervals
    for slot, item in enumerate(items):
        if start <= slot and slot <= end:
            if item:
                # Search by lambda
                if _lambda(item['name'], item['servername']):
                    # Save slot location
                    item['slot'] = slot
                    return item
    return None


# Finds an empty slot, returns -1 if inventory is full
def GetEmptySlot():
    items = get_inventory()['items']
    # check the first empty
    for slot, item in enumerate(items):
        if slot >= 13:
            if not item:
                return slot
    return -1


# Injects item movement on inventory
def Inject_InventoryMovement(movementType, slotInitial, slotFinal, logItemName, quantity=0):
    p = struct.pack('<B', movementType)
    p += struct.pack('<B', slotInitial)
    p += struct.pack('<B', slotFinal)
    p += struct.pack('<H', quantity)
    log('Plugin: Moving item "' + logItemName + '"...')
    # CLIENT_INVENTORY_ITEM_MOVEMENT
    inject_joymax(0x7034, p, False)


# Try to equip item
def EquipItem(item):
    itemData = get_item(item['model'])
    # Check equipables only
    if itemData['tid1'] != 1:
        log('Plugin: ' + item['name'] + ' cannot be equiped!')
        return
    # Check equipable type
    t = itemData['tid2']
    # garment, protector, armor, robe, light, heavy
    if t == 1 or t == 2 or t == 3 or t == 9 or t == 10 or t == 11:
        t = itemData['tid3']
        # head
        if t == 1:
            Inject_InventoryMovement(0, item['slot'], 0, item['name'])
        # shoulders
        elif t == 2:
            Inject_InventoryMovement(0, item['slot'], 2, item['name'])
        # chest
        elif t == 3:
            Inject_InventoryMovement(0, item['slot'], 1, item['name'])
        # pants
        elif t == 4:
            Inject_InventoryMovement(0, item['slot'], 4, item['name'])
        # gloves
        elif t == 5:
            Inject_InventoryMovement(0, item['slot'], 3, item['name'])
        # boots
        elif t == 6:
            Inject_InventoryMovement(0, item['slot'], 5, item['name'])
    # shields
    elif t == 4:
        Inject_InventoryMovement(0, item['slot'], 7, item['name'])
    # accesories ch/eu
    elif t == 5 or t == 12:
        t = itemData['tid3']
        # earring
        if t == 1:
            Inject_InventoryMovement(0, item['slot'], 9, item['name'])
        # necklace
        elif t == 2:
            Inject_InventoryMovement(0, item['slot'], 10, item['name'])
        # ring
        elif t == 3:
            # Check if second ring slot is empty
            if not GetItemByExpression(lambda s, n: True, 11):
                Inject_InventoryMovement(0, item['slot'], 12, item['name'])
            else:
                Inject_InventoryMovement(0, item['slot'], 11, item['name'])
    # weapon ch/eu
    elif t == 6:
        Inject_InventoryMovement(0, item['slot'], 6, item['name'])
    # job
    elif t == 7:
        Inject_InventoryMovement(0, item['slot'], 8, item['name'])
    # avatar
    elif t == 13:
        t = itemData['tid3']
        # hat
        if t == 1:
            Inject_InventoryMovement(36, item['slot'], 0, item['name'])
        # dress
        elif t == 2:
            Inject_InventoryMovement(36, item['slot'], 1, item['name'])
        # accesory
        elif t == 3:
            Inject_InventoryMovement(36, item['slot'], 2, item['name'])
        # flag
        elif t == 4:
            Inject_InventoryMovement(36, item['slot'], 3, item['name'])
    # devil spirit
    elif t == 14:
        Inject_InventoryMovement(36, item['slot'], 4, item['name'])


# Try to unequip item
def UnequipItem(item):
    # find an empty slot
    slot = GetEmptySlot()
    if slot != -1:
        Inject_InventoryMovement(0, item['slot'], slot, item['name'])


# Create a connection to database
def GetDatabaseConnection():
    bot_path = os.getcwd()
    # Load the server info
    data = {}
    locale = get_locale()
    character_data = get_character_data()
    # vSRO
    if locale == 22:
        with open(bot_path + "/vSRO.json", "r") as f:
            data = json.load(f)
        # Match data with the current server name
        server = character_data['server']
        for k in data:
            servers = data[k]['servers']
            # Check if servers is in list
            if server in servers:
                # Scan data folder
                for path in os.scandir(bot_path + "/Data"):
                    # Check databases only
                    if path.is_file() and path.name.endswith(".db3"):
                        # Connect to check if the data matches
                        conn = sqlite3.connect(bot_path + "/Data/" + path.name)
                        c = conn.cursor()
                        c.execute('SELECT * FROM data WHERE k="path" AND v=?', (data[k]['path'],))
                        if c.fetchone():
                            # match found
                            return conn
                        else:
                            conn.close()
    # iSRO
    elif locale == 18:
        return sqlite3.connect(bot_path + "/Data/iSRO.db3")
    # TrSRO
    elif locale == 56:
        return sqlite3.connect(bot_path + "/Data/TRSRO.db3")
    return None


# __________________________


# Get Type ID from item
def GetTIDFromItem(itemId):
    conn = GetDatabaseConnection()
    c = conn.cursor()
    c.execute('SELECT cash_item, tid1, tid2, tid3 FROM items WHERE id=?', (itemId,))
    result = c.fetchone()
    # calculate TID
    result = result[0] + (3 * 4) + (result[1] * 32) + (result[2] * 128) + (result[3] * 2048)
    conn.close()
    return result


# Try to use the item specified
def UseItem(item):
    # Create packet and inject it
    p = struct.pack('<B', item['slot'])
    loc = get_locale()

    tid = GetTIDFromItem(item['model'])
    if loc == 22:  # vsro
        p += struct.pack('<H', tid)
    else:
        p += struct.pack('<I', tid)

    log('Plugin: Using item "' + item['name'] + '"...')
    # CLIENT_INVENTORY_ITEM_USE
    inject_joymax(0x704C, p, True)


def CanCast(name):
    skills = get_skills()
    for ID, skill in skills.items():
        if skill['name'] == name:
            return skill['can_cast']
    return False


def GetSkillID(name):
    skills = get_skills()
    for ID, skill in skills.items():
        if skill['name'] == name:
            return ID


def HasSkill(name):
    skills = get_skills()
    for ID, skill in skills.items():
        if skill['name'] == name:
            return True
    return False


def CastSkill(name):
    ID = GetSkillID(name)
    p = b'\x01\x04'
    p += struct.pack('<I', ID)
    p += b'\x00'
    inject_joymax(0x7074, p, False)
    log("Plugin: Casting [%s]" % name)


# ______________________________ Events ______________________________ #

# Called when the bot successfully connects to the game server
def connected():
    global inGame
    inGame = None


# Called when the character enters the game world
def joined_game():
    loadConfigs()


# All chat messages received are sent to this function
def handle_chat(t, player, msg):
    # Remove guild name from union chat messages
    if t == 11:
        msg = msg.split(': ', 1)[1]

    # Check player at leader list or a Discord message
    if player and lstLeaders_exist(player) or t == 100:
        # Parsing message command
        if msg == "ST":
            start_bot()
            log("Plugin: Bot started")
        elif msg == "SP":
            stop_bot()
            log("Plugin: Bot stopped")
        elif msg.startswith("TR"):
            # deletes empty spaces on right
            msg = msg.rstrip()
            if msg == "TR":
                if start_trace(player):
                    log("Plugin: Starting trace to [" + player + "]")
            else:
                msg = msg[5:].split()[0]
                if start_trace(msg):
                    log("Plugin: Starting trace to [" + msg + "]")
        elif msg == "RT":
            stop_trace()
            change_here('no_go')
            log("Plugin: Trace stopped")
        elif msg.startswith("SETPOS"):
            # deletes empty spaces on right
            msg = msg.rstrip()
            if msg == "SETPOS":
                p = get_position()
                set_training_position(p['region'], p['x'], p['y'], p['z'])
                log("Plugin: Training area set to current position (X:%.1f,Y:%.1f)" % (p['x'], p['y']))
            else:
                try:
                    # check arguments
                    p = msg[6:].split()
                    x = float(p[0])
                    y = float(p[1])
                    # auto calculated if is not specified
                    region = int(p[2]) if len(p) >= 3 else 0
                    z = float(p[3]) if len(p) >= 4 else 0
                    set_training_position(region, x, y, z)
                    log("Plugin: Training area set to (X:%.1f,Y:%.1f)" % (x, y))
                except:
                    log("Plugin: Wrong training area coordinates!")
        elif msg == 'GETPOS':
            # Check current position
            pos = get_position()
            phBotChat.Private(player, 'My position is (X:%.1f,Y:%.1f,Z:%1f,Region:%d)' % (pos['x'], pos['y'], pos['z'],
                                                                                          pos['region']))
        elif msg.startswith("SET"):
            # deletes empty spaces on right
            msg = msg.rstrip()
            if msg == "SETRADIUS":
                # set default radius
                radius = 50
                set_training_radius(radius)
                log("Plugin: Training radius reseted to " + str(radius) + " m.")
            else:
                try:
                    # split and parse movement radius
                    radius = int(float(msg[9:].split()[0]))
                    # to absolute
                    radius = (radius if radius > 0 else radius * -1)
                    set_training_radius(radius)
                    log("Plugin: Training radius set to " + str(radius) + " m.")
                except:
                    log("Plugin: Wrong training radius value!")
        elif msg.startswith('SETSCRIPT'):
            # deletes empty spaces on right
            msg = msg.rstrip()
            if msg == 'SETSCRIPT':
                # reset script
                set_training_script('')
                log('Plugin: Training script path has been reseted')
            else:
                # change script to the path specified
                set_training_script(msg[9:])
                log('Plugin: Training script path has been changed')
        elif msg.startswith('SETAREA '):
            # deletes empty spaces on right
            msg = msg[8:]
            if msg:
                # try to change to specified area name
                if set_training_area(msg):
                    log('Plugin: Training area has been changed to [' + msg + ']')
                else:
                    log('Plugin: Training area [' + msg + '] not found in the list')
        elif msg == "SIT":
            log("Plugin: Sit/Stand")
            inject_joymax(0x704F, b'\x04', False)
        elif msg.startswith("HWT1"):
            inject_joymax(0x705A, b'\x02\x00\x00\x00\x02\xA5\x00\x00\x00', False)
        elif msg.startswith("HWT2"):
            inject_joymax(0x705A, b'\x02\x00\x00\x00\x02\xA6\x00\x00\x00', False)
        elif msg.startswith("HWT3"):
            inject_joymax(0x705A, b'\x02\x00\x00\x00\x02\xA7\x00\x00\x00', False)
        elif msg == "OPS":
            log("Plugin: zerktest")
            inject_joymax(0x715F, b'\x8b]\x00\x00\x81]\x00\x00', False)
        elif msg == "JUMP":
            # Just a funny emote lol
            log("Plugin: Jumping!")
            inject_joymax(0x3091, b'\x0c', False)
        elif msg == "HOT":
            log("Plugin: LAVA TRAP)")
            inject_joymax(0x7074, b'\x01\x04\x43\x28\x00\x00\x00', False)
        elif msg == "FOR":
            log("Plugin: Earth FENCE)")
            inject_joymax(0x7074, b'\x01\x04\x5e\x27\x00\x00\x00', False)
        elif msg == "RCON":
            log("Plugin: TELEPORT CONST)")
            inject_joymax(0x705A, b'\xA4\x06\x00\x00\x02\x28\x00\x00\x00', False)
        elif msg == "CON":
            log("Plugin: TELEPORT CONST)")
            inject_joymax(0x705A, b'\xA6\x06\x00\x00\x02\x29\x00\x00\x00', False)
        elif msg == "GOO":
            log("Plugin: DEVIL IGNORE)")
            inject_joymax(0x7074, b'\x01\x04\xB0\x79\x00\x00\x00', False)
        elif msg == "PET":
            log("Plugin: Spawned PET")
            inject_joymax(0x704C, b'\x25\xCD\x08', False)
        elif msg.startswith("SH"):
            inject_joymax(0x705A, b'\x19\x00\x00\x00\x02\x05\x00\x00\x00', False)
        elif msg.startswith("JA"):
            inject_joymax(0x705A, b'\x15\x00\x00\x00\x02\xb0\x00\x00\x00', False)
        elif msg.startswith("SC"):
            inject_joymax(0x705A, b'\x19\x00\x00\x00\x02\x14\x00\x00\x00', False)
        elif msg.startswith("HD"):
            inject_joymax(0x705A, b'\x0c\x00\x00\x00\x02\x02\x00\x00\x00', False)
        elif msg.startswith("DJ"):
            inject_joymax(0x705A, b'\x17\x00\x00\x00\x02\x01\x00\x00\x00', False)
        elif msg.startswith("AH"):
            inject_joymax(0x705A, b'\x0a\x00\x00\x00\x02\x05\x00\x00\x00', False)
        elif msg.startswith("CS"):
            inject_joymax(0x705A, b'\x18\x00\x00\x00\x02\x19\x00\x00\x00', False)
        elif msg.startswith("AJ"):
            inject_joymax(0x705A, b'\x0a\x00\x00\x00\x02\x01\x00\x00\x00', False)
        elif msg.startswith("HS"):
            inject_joymax(0x705A, b'\x0c\x00\x00\x00\x02\x19\x00\x00\x00', False)
        elif msg.startswith("DH"):
            inject_joymax(0x705A, b'\x17\x00\x00\x00\x02\x05\x00\x00\x00', False)
        elif msg.startswith("HA"):
            inject_joymax(0x705A, b'\x0c\x00\x00\x00\x02\xb0\x00\x00\x00', False)
        elif msg.startswith("JD"):
            inject_joymax(0x705A, b'\x15\x00\x00\x00\x02\x02\x00\x00\x00', False)
        elif msg.startswith("TP1"):
            inject_joymax(0x705A, b'\x02\x00\x00\x00\x02\xA5\x00\x00\x00', False)
        elif msg.startswith("TP2"):
            inject_joymax(0x705A, b'\x02\x00\x00\x00\x02\xA6\x00\x00\x00', False)
        elif msg.startswith("FH1"):
            inject_joymax(0x705A, b'\x13\x00\x00\x00\x02\x99\x00\x00\x00\x00', False)
        elif msg.startswith("FH2"):
            inject_joymax(0x705A, b'\x13\x00\x00\x00\x02\x9a\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FH3"):
            inject_joymax(0x705A, b'\x13\x00\x00\x00\x02\x9b\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FH4"):
            inject_joymax(0x705A, b'\x13\x00\x00\x00\x02\x9c\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FJ1"):
            inject_joymax(0x705A, b'\x10\x00\x00\x00\x02\x31\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FJ2"):
            inject_joymax(0x705A, b'\x10\x00\x00\x00\x02\x32\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FJ3"):
            inject_joymax(0x705A, b'\x10\x00\x00\x00\x02\x33\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FB1"):
            inject_joymax(0x705A, b'\x09\x00\x00\x00\x02\x90\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FB2"):
            inject_joymax(0x705A, b'\x09\x00\x00\x00\x02\x91\x00\x00\x00\x00\x00', False)
        elif msg.startswith("FB3"):
            inject_joymax(0x705A, b'\x09\x00\x00\x00\x02\x92\x00\x00\x00\x00\x00', False)

        elif msg.startswith("CAPE"):
            # deletes empty spaces on right
            msg = msg.rstrip()
            if msg == "CAPE":
                log("Plugin: Using PVP Cape by default (Yellow)")
                inject_joymax(0x7516, b'\x05', False)
            else:
                # get cape type normalized
                cape = msg[4:].split()[0].lower()
                if cape == "off":
                    log("Plugin: Removing PVP Cape")
                    inject_joymax(0x7516, b'\x00', False)
                elif cape == "red":
                    log("Plugin: Using PVP Cape (Red)")
                    inject_joymax(0x7516, b'\x01', False)
                elif cape == "gray":
                    log("Plugin: Using PVP Cape (Gray)")
                    inject_joymax(0x7516, b'\x02', False)
                elif cape == "blue":
                    log("Plugin: Using PVP Cape (Blue)")
                    inject_joymax(0x7516, b'\x03', False)
                elif cape == "white":
                    log("Plugin: Using PVP Cape (White)")
                    inject_joymax(0x7516, b'\x04', False)
                elif cape == "yellow":
                    log("Plugin: Using PVP Cape (Yellow)")
                    inject_joymax(0x7516, b'\x05', False)
                else:
                    log("Plugin: Wrong PVP Cape color!")

        elif msg == "NAM":
            # Just a funny emote lol
            log("Plugin: (Praying!")
            inject_joymax(0x3091, b'\x0999', False)
        elif msg == "Z":
            log("Plugin: Using Berserker mode")
            inject_joymax(0x70A7, b'\x01', False)
        elif msg == "UNS":
            pets = get_pets()
            if pets:
                for uid, pet in pets.items():
                    if pet['type'] == 'wolf':
                        inject_joymax(0x7116, struct.pack('I', uid), False)
        elif msg == "R":
            # Quickly check if is dead
            character = get_character_data()
            if character['hp'] == 0:
                # RIP
                log('Plugin: Resurrecting at town...')
                inject_joymax(0x3053, b'\x01', False)
            else:
                log('Plugin: Trying to use return scroll...')
                # Avoid high CPU usage with too many chars at the same time
                Timer(random.uniform(0.5, 2), use_return_scroll).start()
        elif msg.startswith("QW"):
            # deletes command header and whatever used as separator
            msg = msg[3:]
            if not msg:
                return
            # select split char
            split = ',' if ',' in msg else ' '
            # extract arguments
            source_dest = msg.split(split)
            # needs to be at least two name points to try teleporting
            if len(source_dest) >= 2:
                source = source_dest[0].strip()
                dest = source_dest[1].strip()
                source_dest_dict = {
                    'J': 'Jangan',
                    'S': 'Samarkand',
                    'AN': 'Alexandria (North)',
                    'AS': 'Alexandria (South)',
                    'C': 'Constantinople',
                    'H': 'Hotan',
                    'D': 'Donwhang'
                }
                if source in source_dest_dict:
                    source = source_dest_dict[source]
                if dest in source_dest_dict:
                    dest = source_dest_dict[dest]

                inject_teleport(source, dest)
        elif msg.startswith("INT "):
            msgPacket = msg[7:].split()
            msgPacketLen = len(msgPacket)
            if msgPacketLen == 0:
                log("Plugin: Incorrect structure to inject packet")
                return
            # Check packet structure
            opcode = int(msgPacket[0], 16)
            data = bytearray()
            encrypted = False
            dataIndex = 1
            if msgPacketLen >= 2:
                enc = msgPacket[1].lower()
                if enc == 'true' or enc == 'false':
                    encrypted = enc == "true"
                    dataIndex += 1
            # Create packet data and inject it
            for i in range(dataIndex, msgPacketLen):
                data.append(int(msgPacket[i], 16))
            inject_joymax(opcode, data, encrypted)
            # Log the info
            log("Plugin: Injecting packet...\nOpcode: 0x" + '{:02X}'.format(opcode) + " - Encrypted: " + (
                "Yes" if encrypted else "No") + "\nData: " + (
                    ' '.join('{:02X}'.format(int(msgPacket[x], 16)) for x in range(dataIndex, msgPacketLen)) if len(
                        data) else 'None'))
        elif msg.startswith("CHAT "):
            handleChatCommand(msg[5:])
        elif msg.startswith("M"):
            if msg == "M":
                randomMovement()
            else:
                try:
                    # split and parse movement radius
                    radius = int(float(msg[6:].split()[0]))
                    # to positive
                    radius = (radius if radius > 0 else radius * -1)
                    randomMovement(radius)
                except:
                    log("Plugin: Movement maximum radius incorrect")
        elif msg.startswith("F"):
            # default values
            charName = player
            distance = 0
            if msg != "FO1":
                # Check params
                msg = msg[6:].split()
                try:
                    if len(msg) >= 1:
                        charName = msg[0]
                    if len(msg) >= 2:
                        distance = float(msg[1])
                except:
                    log("Plugin: Follow distance incorrect")
                    return
            # Start following
            if start_follow(charName, distance):
                log("Plugin: Starting to follow to [" + charName + "] using [" + str(distance) + "] as distance")
        elif msg == "BB":
            if stop_follow():
                log("Plugin: Following stopped")
        elif msg.startswith("ASH"):
            if msg == "PROFILE":
                if set_profile('Default'):
                    log("Plugin: Setting Default profile")
            else:
                msg = msg[3:]
                if set_profile(msg):
                    log("Plugin: Setting " + msg + "ASH")
        elif msg == "DC":
            log("Plugin: Disconnecting...")
            disconnect()
        elif msg.startswith("SS"):
            # default value
            pet = "wolf"
            if msg != "SS":
                msg = msg[2:].split()
                if msg:
                    pet = msg[0]
            # Try mount pet
            if MountPet(pet):
                log("Plugin: Mounting pet [" + pet + "]")
        elif msg.startswith("DMT"):
            # default value
            pet = "wolf"
            if msg != "DMT":
                msg = msg[3:].split()
                if msg:
                    pet = msg[0]
            # Try dismount pet
            if DismountPet(pet):
                log("Plugin: Dismounting pet [" + pet + "]")
        elif msg == "GG":
            # Check if has party
            if get_party():
                # Left it
                log("Plugin: Leaving the party..")
                inject_joymax(0x7061, b'', False)
        elif msg.startswith("RECALL "):
            msg = msg[7:]
            if msg:
                npcUID = GetNPCUniqueID(msg)
                if npcUID > 0:
                    log("Plugin: Designating recall to \"" + msg.title() + "\"...")
                    inject_joymax(0x7059, struct.pack('I', npcUID), False)
        elif msg.startswith("EQUIP "):
            msg = msg[6:]
            if msg:
                # search item with similar name or exact server name
                item = GetItemByExpression(lambda n, s: msg in n or msg == s, 13)
                if item:
                    EquipItem(item)
        elif msg.startswith("UNEQUIP "):
            msg = msg[8:]
            if msg:
                # search item with similar name or exact server name
                item = GetItemByExpression(lambda n, s: msg in n or msg == s, 0, 12)
                if item:
                    UnequipItem(item)
        elif msg == "USE PET":
            pets_to_try = ['Bear', 'Rengar Summon Scroll', 'Night Fury Summon Scroll', 'Achatles Summon Scroll',
                           'Nacrasena Summon Scroll', 'Night Fang Summon Scroll', ]
            end = 0
            start = 13
            inventory = get_inventory()
            items = inventory['items']
            if end == 0:
                end = inventory['size']
            # check items between intervals
            for slot, item in enumerate(items):
                if start <= slot and slot <= end:
                    if item['name'] in pets_to_try:
                        item['slot'] = slot
                        UseItem(item)
                        break
        elif msg == 'DD':
            end = 0
            start = 0
            inventory = get_inventory()
            items = inventory['items']
            if end == 0:
                end = inventory['size']
            # check items between intervals
            for slot, item in enumerate(items):
                if start <= slot and slot <= end:
                    log(str(item))
        elif msg.startswith("USE "):
            # remove command
            msg = msg[4:]
            if msg:
                # search item with similar name or exact server name
                use_dict = {
                    'zerk': 'Energy of life 4th degree',
                    'rs': 'Special Return Scroll',
                    'SEX': 'Bear',
                    'SEX': 'Bird',
                    'SEX': 'Nacrasena Summon Scroll',
                    'SEX': 'Night Fang Summon Scroll',
                    'Falcon': 'Falcon Summon Scroll',
                    'RED': 'Berserker Regeneration Potion',
                }

                if msg in use_dict:
                    if msg == 'zerk':
                        zerks = [
                            'Energy of life 1st degree',
                            'Energy of life 2nd degree',
                            'Energy of life 3th degree',
                            'Energy of life 4th degree'
                        ]
                        for zrk in zerks:
                            log(zrk)
                            item = GetItemByExpression(lambda n, s: zrk in n or zrk == s, 13)
                            if item:
                                UseItem(item)
                                break
                    else:
                        msg = use_dict[msg]

                        item = GetItemByExpression(lambda n, s: msg in n or msg == s, 13)
                        if item:
                            UseItem(item)
                else:
                    log('Unkown command')

        elif msg.startswith("222"):
            if CanCast("Vallainous Devil Skill"):
                CastSkill("Vallainous Devil Skill")
            elif CanCast("Vallainous Spirit of Asura"):
                CastSkill("Vallainous Spirit of Asura")
            elif CanCast("Divine skill of omnipotence"):
                CastSkill("Divine skill of omnipotence")
            if CanCast("Wicked Devil Skill"):
                CastSkill("Wicked Devil Skill")
            if CanCast("Malicious Devil Skill"):
                CastSkill("Malicious Devil Skill")

        elif msg.startswith("ASD "):
            # remove command
            msg = msg[4:]
            if msg:
                # check params
                msg = msg.split(' ', 1)
                # param type
                if msg[0] == 'G':
                    # try to use it
                    if reverse_return(0, ''):
                        log('Plugin: Using reverse to the last return scroll location')
                elif msg[0] == 'D':
                    # try to use it
                    if reverse_return(1, ''):
                        log('Plugin: Using reverse to the last death location')
                elif msg[0] == 'player':
                    # Check existing name
                    if len(msg) >= 2:
                        # try to use it
                        if reverse_return(2, msg[1]):
                            log('Plugin: Using reverse to player "' + msg[1] + '" location')
                elif msg[0] == 'Z':
                    # Check existing zone
                    if len(msg) >= 2:
                        # try to use it
                        if msg[1] == "B":
                            zone = "Bandit's Mountain Stronghold"
                        if msg[1] == "S":
                            zone = "Shepherd Town"
                        if msg[1] == "J":
                            zone = "Grassland"
                        if msg[1] == "R":
                            zone = "Grassland Road"
                        if msg[1] == "G":
                            zone = "Garden of Gods"
                        if msg[1] == "A":
                            zone = "Ancient Remains"
                        if msg[1] == "H":
                            zone = "Huns Garrison"
                        if msg[1] == "P":
                            zone = "Pond Ruins"
                        if msg[1] == "JJ":
                            zone = "Jangan"
                        if msg[1] == "SAM":
                            zone = "Samarkand"
                        if msg[1] == "ALEX":
                            zone = "Alexandria (North)"
                        if msg[1] == "CON":
                            zone = "Constantinople"
                        if msg[1] == "TEP":
                            zone = "Salt Desert"
                        if msg[1] == "HE":
                            zone = "Heart Peak"
                        if msg[1] == "B4":
                            zone = "Tomb of Qin-Shi Emperor lv.4"
                        if msg[1] == "B3":
                            zone = "Tomb of Qin-Shi Emperor lv.3"
                        if msg[1] == "B2":
                            zone = "Tomb of Qin-Shi Emperor lv.2"
                        if msg[1] == "LORD":
                            zone = "Niya Remains"
                        if msg[1] == "ROC":
                            zone = "Roc Mountain"
                        if msg[1] == "LOST":
                            zone = "Lost Town"
                        if msg[1] == "WIND":
                            zone = "Wind Town"
                        if msg[1] == "RED":
                            zone = "Red ground"
                        if reverse_return(3, zone):
                            log('Plugin: Using reverse to zone "' + zone + '" location')


# Called every 500ms
def event_loop():
    if inGame and followActivated:
        player = near_party_player(followPlayer)
        # check if is near
        if not player:
            return
        # check distance to the player
        if followDistance > 0:
            p = get_position()
            playerDistance = round(GetDistance(p['x'], p['y'], player['x'], player['y']), 2)
            # check if has to move
            if followDistance < playerDistance:
                # generate vector unit
                x_unit = (player['x'] - p['x']) / playerDistance
                y_unit = (player['y'] - p['y']) / playerDistance
                # distance to move
                movementDistance = playerDistance - followDistance
                log("Following " + followPlayer + "...")
                move_to(movementDistance * x_unit + p['x'], movementDistance * y_unit + p['y'], 0)
        else:
            # Avoid negative numbers
            log("Following " + followPlayer + "...")
            move_to(player['x'], player['y'], 0)


# Plugin loaded
log("Plugin: " + pName + " v" + pVersion + " successfully loaded")

if os.path.exists(getPath()):
    # Adding RELOAD plugin support
    loadConfigs()
else:
    # Creating configs folder
    os.makedirs(getPath())
    log('Plugin: ' + pName + ' folder has been created')
