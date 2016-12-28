#!/usr/bin/env python

import re
import sys
from collections import defaultdict

def histfile(mode):
    return file('cluedo.hist', mode)

re_comma_space = re.compile(', *')

WEAPONS = [
        ["knife"],
        ["candlestick"],
        ["pistol", "revolver", "gun"],
        ["poison"],
        ["trophy"],
        ["rope"],
        ["bat"],
        ["axe"],
        ["dumbbell"]
]

SUSPECTS = [
    ["scarlett", "red"],
    ["mustard", "yellow"],
    ["white"],
    ["green"],
    ["peacock", "blue"],
    ["plum", "purple"],
]

ROOMS = [
    "hall",
    "dining room",
    "kitchen",
    "patio",
    "observatory",
    "theatre",
    "living room",
    "spa",
    "guest house",
]

players = [] # Array<Player>
rumours = [] # Array<Rumour>
discovered_items = set() # Set<item>
pool_item = None
try:
    history = map(lambda l: l[:-1], histfile('r').readlines())
except IOError:
    history = []

def print_status():
    print "narrowed down to these items:"
    grouped_items = group_items(narrowed_down_items())
    for key in grouped_items:
        print "    {}: {}".format(key, ', '.join(grouped_items[key]))

    for player in players:
        print "{}:".format(player.name)
        print "    owns {}".format(', '.join(player.verified_items))
        print "    can't own {}".format(', '.join(player.unowned_items))

def raw_input_or_hist(pre = ''):
    global history
    if len(history):
        ret = history[0]
        history = history[1:]
        print '<canned: {}>'.format(ret)
        return ret

    while True:
        line = raw_input()
        if line == '/status':
            print_status()
            sys.stdout.write(pre)
        else:
            break

    histfile('a').write('{}\n'.format(line))
    return line

class Rumour():
    def __init__(self, weapon, suspect, room, asker):
        self.weapon = weapon
        self.suspect = suspect
        self.room = room

        self.asker = asker # Player
        self.answerer = None # Player?

        self.orig_weapon = weapon
        self.orig_suspect = suspect
        self.orig_room = room

    def items(self):
        return set(filter(
                lambda i: i is not None,
                [self.weapon, self.suspect, self.room]))

    def original_items(self):
        return set([self.orig_weapon, self.orig_suspect, self.orig_room])

    def discount(self, items):
        for item in items:
            if self.weapon == item:
                self.weapon = None
            elif self.suspect == item:
                self.suspect = None
            elif self.room == item:
                self.room = None

class Player():
    def __init__(self, name):
        self.name = name
        self.verified_items = set()
        self.unowned_items = set()

def prompt(s):
    pre = '{} '.format(s)
    sys.stdout.write(pre)
    return raw_input_or_hist(pre)

def yes_or_no(s):
    while True:
        yorn = prompt(s)
        if len(yorn) == 0:
            return True
        if yorn == 'y':
            return True
        if yorn == 'n':
            return False
        print "please enter y/n"

def substring_matches_in_array(substr, array):
    return filter(
            lambda p: p[:len(substr)] == substr,
            array)

def prompt_for(s, candidates, allow_empty = False):
    candidate = ''
    while True:
        candidate = prompt(s)

        if allow_empty and len(candidate) == 0:
            return None

        matches = substring_matches_in_array(candidate, candidates)

        if len(matches) == 1:
            return matches[0]
        if len(matches) == 0:
            print "'{}' not in candidates ({})".format(
                    candidate,
                    ', '.join(list(candidates)))
            continue
        print "too many candidates: {}".format(', '.join(matches))

def unreachable():
    assert False

def prompt_for_player(s, allow_empty = False):
    name = prompt_for(s, map(lambda p: p.name, players), allow_empty)

    if name is None:
        assert allow_empty
        return None

    for player in players:
        if player.name == name:
            return player
    unreachable()

def ALL_ITEMS_FLAT():
    items = set()
    for ar in WEAPONS: items.update(set(ar))
    for ar in SUSPECTS: items.update(set(ar))
    items.update(set(ROOMS))
    return items

def prompt_for_item(s, allow_empty = False):
    return prompt_for(s, ALL_ITEMS_FLAT(), allow_empty)

def init_players():
    global players
    print "input players (you first, in order), empty line to finish:"
    while True:
        name = raw_input_or_hist()
        if len(name) == 0:
            break
        if name in map(lambda p: p.name, players):
            print "already have {}".format(name)
            raise Exception()
        players.append(Player(name))

def ALL_ITEMS_OFFICIAL():
    def first_alias(aliases):
        return aliases[0]

    items = set(map(first_alias, WEAPONS))
    items.update(map(first_alias, SUSPECTS))
    items.update(ROOMS)

    return items

def narrowed_down_items():
    return ALL_ITEMS_OFFICIAL().difference(discovered_items)

def group_items(items):
    groups = defaultdict(list)
    for item in items:
        if subarray_find(item, WEAPONS): groups["weapons"].append(item)
        elif subarray_find(item, SUSPECTS): groups["suspects"].append(item)
        if item in ROOMS: groups["rooms"].append(item)
    return groups

def record_player_hasnt_item(player, item, recheck_rumours = True):
    assert item not in player.verified_items

    player.unowned_items.add(item)

    if recheck_rumours:
        # can see if there's any single-item rumours
        rumours_recheck()

def record_player_has_item(player, item, recheck_rumours = True):
    assert item not in player.unowned_items

    player.verified_items.add(item)

    # no one else has item
    for other in players:
        if other is not player:
            record_player_hasnt_item(other, item, recheck_rumours)

    # item can't be in the true rumour
    discount_discovered_item_owned_by(item, player)

def subarray_find(key, toplvl):
    for ar in toplvl:
        for ent in ar:
            if ent == key:
                return ar[0]
    return None

def item_resolve(item):
    resolved = subarray_find(item, WEAPONS)
    if resolved is not None: return resolved
    resolved = subarray_find(item, SUSPECTS)
    if resolved is not None: return resolved
    if item in ROOMS:
        return item
    return None

def init_from_my_cards():
    while True:
        raw_items = re.split(
                re_comma_space,
                prompt('your items?'))

        items = map(item_resolve, raw_items)

        if None in items:
            missing = []
            for i in range(len(items)):
                if items[i] is None:
                    missing.append(raw_items[i])
            print "these items aren't recognised: {}".format(', '.join(missing))
            continue

        items = set(items) # uniq

        correct = yes_or_no(
                "got {} items: {}, correct (Y/n)?"
                .format(
                    len(items),
                    ', '.join(items)))

        if correct:
            for item in items:
                record_player_has_item(players[0], item)
            break

def prompt_for_rumour(s, asker, allow_empty = True):
    while True:
        rumour = prompt(s)
        if allow_empty and len(rumour) == 0:
            return None

        rumour_entries = re.split(re_comma_space, rumour)
        if len(rumour_entries) != 3:
            print "got {} entries, need 3".format(len(rumour_entries))
            continue

        weapon, suspect, room = None, None, None

        for i in range(3):
            if subarray_find(rumour_entries[i], WEAPONS): weapon = rumour_entries[i]
            if subarray_find(rumour_entries[i], SUSPECTS): suspect = rumour_entries[i]
            if rumour_entries[i] in ROOMS: room = rumour_entries[i]

        need = []
        if weapon is None: need.append("weapon")
        if suspect is None: need.append("suspect")
        if room is None: need.append("room")

        if len(need) > 0:
            print "need {}".format(', '.join(need))
            continue

        return Rumour(weapon, suspect, room, asker)

def discount_discovered_item_owned_by(item, owner):
    # - update discovered_items list
    # - check discovered_items against count of all items - if exactly 3 less, done
    # - go through rumours discounting the item from each one
    #   and if said rumour only has one item:
    #   - add item to rumour.answerer's verified_items,
    #     which means no one else has it
    #   - recurse with that item to discount
    if item not in owner.verified_items:
        print "discounting {}, owned by {}".format(item, owner.name)

    discovered_items.add(item)

    possibles = narrowed_down_items()
    if len(possibles) == 3:
        print "COMPLETE: {}".format(', '.join(possibles))

    for rumour in rumours:
        if len(rumour.items()) == 1:
            continue # nothing important to find

        if rumour.answerer != owner:
            # the answerer can't possibly have the item, so:
            rumour.discount(set([item]))
            if len(rumour.items()) == 1 and rumour.answerer is not None:
                owned_item = rumour.items().pop()
                record_player_has_item(rumour.answerer, owned_item)

def check_if_no_one_owns_items():
    ret = False
    if pool_item is None:
        return ret

    items_to_unowners = defaultdict(list) # Dict<item, Set<Player>>
    for player in players:
        for item in player.unowned_items:
            items_to_unowners[item].append(player)

    for item in items_to_unowners:
        if len(items_to_unowners[item]) == len(players):
            # no one owns 'item' - not in the pool because
            # pool_item is not None / we own the pool item
            print "no one owns {}".format(item)
            # we know 'item' is a murder item, so we can discount
            # all other items in its category:

            for player in players:
                if item not in player.unowned_items:
                    record_player_hasnt_item(player, item, False)
                    ret = True

    return ret

def rumours_recheck():
    # - remove from [a, b, c] those items we know the answerer doesn't have
    #   (assert len([a,b,c]) > 0)
    # - if len([a, b, c]) == 1 then we know that player has the item
    # - for each item, if no one has the item (and it's not in the pool),
    #   then it's a murder item

    recheck = False

    for rumour in filter(lambda r: r.answerer is not None and len(r.items()) > 1, rumours):
        rumour.discount(rumour.answerer.unowned_items)
        assert len(rumour.items()) > 0

        if len(rumour.items()) == 1:
            record_player_has_item(rumour.answerer, rumour.items().pop(), False)
            recheck = True

    recheck |= check_if_no_one_owns_items()

    if recheck:
        rumours_recheck()

def completed_rumour(rumour):
    # new rumour: rumour.answerer? has a, b or c
    # - iterate through all people between player
    #   and answerer: all those people don't have a, b nor c
    # - recheck rumours against new non-presents

    if rumour.answerer is not None:
        i = players.index(rumour.asker) + 1
        n = len(players)

        while players[i % n] != rumour.answerer:
            for item in rumour.original_items():
                print "player {} can't have {}".format(
                        players[i%n].name, item)

                record_player_hasnt_item(players[i % n], item, False)
            i += 1
    else:
        for player in filter(lambda p: p is not rumour.asker, players):
            for item in rumour.original_items():
                record_player_hasnt_item(player, item, False)

    rumours_recheck()

init_players()
init_from_my_cards()

player = prompt_for_player("whose turn first?")
turn = players.index(player)
assert turn >= 0

while True:
    correct_turn = yes_or_no("is it {}'s turn (Y/n)?".format(players[turn].name))
    assert correct_turn
    current_player = players[turn]
    turn = (turn + 1) % len(players)

    if current_player is players[0]:
        if pool_item is None:
            pool_item = prompt_for_item(
                    "what's the pool item (empty for undiscovered)?",
                    True)
            if pool_item is not None:
                # act as if we own it:
                players[0].unowned_items.discard(pool_item)
                record_player_has_item(players[0], pool_item)
        # TODO: ideal rumour to ask

    rumour = prompt_for_rumour(
            "rumour (a, b, c) (empty for no rumour)?",
            current_player)

    if rumour is None:
        continue

    answerer = prompt_for_player('who answered (nothing = no one)?', True)

    rumour.answerer = answerer
    assert rumour.answerer is not rumour.asker
    rumours.append(rumour)

    completed_rumour(rumour)

    if answerer is not None and current_player is players[0]:
        item = prompt_for_item('what was the answer?')
        record_player_has_item(rumour.answerer, item)
