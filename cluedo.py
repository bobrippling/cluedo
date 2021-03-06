#!/usr/bin/env python

import re
import sys
from collections import defaultdict

def usage():
    print >>sys.stderr, "Usage: {} [histfile]".format(sys.argv[0])
    sys.exit(2)

histfilepath = 'cluedo.hist'

if len(sys.argv) == 2:
    histfilepath = sys.argv[1]
elif len(sys.argv) != 1:
    usage()

def histfile(mode):
    return file(histfilepath, mode)

re_comma_space = re.compile(', *')
re_give = re.compile('/give ([^,]+), *(.*)$')

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
discovered_items = set() # Set<item> (may contain items found through deduction)
murder_items = set() # Set<item>
#pool_item = None
try:
    history = map(lambda l: l[:-1], histfile('r').readlines())
except IOError:
    history = []

def print_status():
    print "narrowed down to these items (all items minus discovered items):"
    grouped_items = group_items(narrowed_down_items())
    for key in grouped_items:
        print "    {}: {}".format(key, ', '.join(grouped_items[key]))

    print "known murder items (no one owns these):"
    print "    {}".format(', '.join(murder_items))

    for player in players:
        print "{}:".format(player.name)
        print "    owns weapons: {}".format(      ', '.join(player.verified_items.intersection(map(first_alias, WEAPONS))))
        print "    owns suspects: {}".format(     ', '.join(player.verified_items.intersection(map(first_alias, SUSPECTS))))
        print "    owns rooms: {}".format(        ', '.join(player.verified_items.intersection(ROOMS)))
        print "    can't own weapons: {}".format( ', '.join(player.unowned_items.intersection(map(first_alias, WEAPONS))))
        print "    can't own suspects: {}".format(', '.join(player.unowned_items.intersection(map(first_alias, SUSPECTS))))
        print "    can't own rooms: {}".format(   ', '.join(player.unowned_items.intersection(ROOMS)))

def raw_input_or_hist(pre = ''):
    global history
    if len(history):
        ret = history[0]
        history = history[1:]
        print '<canned: {}>'.format(ret)
        return ret

    while True:
        line = raw_input()
        give_match = re_give.match(line)
        if line == '/status':
            print_status()
            sys.stdout.write(pre)
        elif give_match:
            item = give_match.group(1)
            name = give_match.group(2)

            founds = filter(lambda p: p.name == name, players)
            if len(founds) != 1:
                print "invalid player {}".format(name)
                continue
            player = founds[0]

            item = item_or_none(item)
            if item is None:
                print "invalid item"
                continue

            record_player_has_item(player, item)
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
    item = prompt_for(s, ALL_ITEMS_FLAT(), allow_empty)
    if item is None:
        assert allow_empty
        return None
    return item_or_none(item) # canonicalise item

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
        if ',' in name:
            print "comma in {}".format(name)
            raise Exception()
        players.append(Player(name))

def first_alias(aliases):
    return aliases[0]

def ALL_ITEMS_OFFICIAL():
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
    owner_assertion = item not in player.verified_items #or player is players[0] and item is pool_item
    if not owner_assertion:
        print "!!! player {} is lying - they already own {}".format(player.name, item)
        return

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

def item_or_none(item):
    resolved = subarray_find(item, WEAPONS)
    if resolved is not None: return resolved
    resolved = subarray_find(item, SUSPECTS)
    if resolved is not None: return resolved
    if item in ROOMS:
        return item
    return None

def item_lookup(item):
    matches = substring_matches_in_array(item, ALL_ITEMS_FLAT())

    if len(matches) == 1:
        return item_or_none(matches[0])
    print "too many matches for '{}': {}".format(item, ', '.join(matches))
    return None

def init_from_my_cards():
    while True:
        raw_items = re.split(
                re_comma_space,
                prompt('your items?'))

        items = map(item_or_none, raw_items)

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

        rumour_entries_raw = re.split(re_comma_space, rumour)
        if len(rumour_entries_raw) != 3:
            print "got {} entries, need 3".format(len(rumour_entries_raw))
            continue
        rumour_entries = map(item_lookup, rumour_entries_raw)

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
            print "need {} - only resolved {}".format(
                    ', '.join(need),
                    ', '.join(filter(lambda p: p is not None, rumour_entries)))
            continue

        return Rumour(weapon, suspect, room, asker)

def complete(items):
    print "I KNOW WHO IT IS"
    #print "COMPLETE: {}".format(', '.join(items))
    #print_status()

def discount_discovered_item_owned_by(item, owner):
    # ^ owner may be None
    #
    # - update discovered_items list
    # - check discovered_items against count of all items - if exactly 3 less, done
    # - go through rumours discounting the item from each one
    #   and if said rumour only has one item:
    #   - add item to rumour.answerer's verified_items,
    #     which means no one else has it
    #   - recurse with that item to discount
    if item not in discovered_items:
        pass
        #print "discounting {}, owned by {}".format(
        #        item,
        #        owner.name if owner else '<no one - deduced>')

    already_have_3 = len(narrowed_down_items()) == 3

    discovered_items.add(item)

    possibles = narrowed_down_items()
    if len(possibles) == 3 and not already_have_3:
        complete(possibles)

    if owner is None:
        # - we've deduced an item isn't owned by anyone
        # - if we don't know the pool_item then we can't prove anything
        # - once we know the pool item we can use this list of unowned items
        #   to prove further
        # FIXME: delay this until later
        return

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
    #if pool_item is None:
    #    return ret

    items_to_unowners = defaultdict(list) # Dict<item, Set<Player>>
    for player in players:
        for item in player.unowned_items:
            items_to_unowners[item].append(player)

    for item in items_to_unowners:
        #if item is pool_item:
        #    continue

        if item in murder_items:
            continue # already done this one

        if len(items_to_unowners[item]) == len(players):
            # no one owns 'item' - it's either a murder item or pool item
            # can't be a pool item because of the above if-statement
            #print "no one owns {} - murder item".format(item)

            for player in players:
                assert item in player.unowned_items

            if item not in murder_items:
                murder_items.add(item)
                if len(murder_items) == 3:
                    complete(murder_items)

            # discount all other items in category - must be the murder item
            if subarray_find(item, WEAPONS):
                for weapon in filter(lambda w: w != item, map(first_alias, WEAPONS)):
                    discount_discovered_item_owned_by(weapon, None)
            elif subarray_find(item, SUSPECTS):
                for suspect in filter(lambda s: s != item, map(first_alias, SUSPECTS)):
                    discount_discovered_item_owned_by(suspect, None)
            elif item in ROOMS:
                for room in filter(lambda r: r != item, ROOMS):
                    discount_discovered_item_owned_by(room, None)
            else:
                unreachable()


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
                if item not in players[i % n].unowned_items:
                    pass
                    #print "player {} can't have {}".format(
                    #        players[i%n].name, item)

                record_player_hasnt_item(players[i % n], item, False)
            i += 1
    else:
        for player in filter(lambda p: p is not rumour.asker, players):
            for item in rumour.original_items():
                record_player_hasnt_item(player, item, False)

    rumours_recheck()

def expected_rumour_stop_player(rumour, turn):
    n = len(players)
    i = turn + 1
    while i != turn:
        next_p = players[i % n]

        for item in rumour.items():
            if item in next_p.verified_items:
                return next_p
        i = (i + 1) % n

    return None

def print_ideal_rumour():
    pass

init_players()
init_from_my_cards()

player = prompt_for_player("whose turn first?")
turn = players.index(player)
assert turn >= 0

while True:
    # FIXME: people can have multiple turns
    current_player = players[turn]
    turn = (turn + 1) % len(players)

    if current_player is players[0]:
        #if pool_item is None:
        #    pool_item = prompt_for_item(
        #            "what's the pool item (empty for undiscovered)?",
        #            True)
        #    if pool_item is not None:
        #        # act as if we own it:
        #        players[0].unowned_items.discard(pool_item)
        #        record_player_has_item(players[0], pool_item)
        print_ideal_rumour()

    rumour = prompt_for_rumour(
            "{}'s rumour (a, b, c) (empty for no rumour)?".format(current_player.name),
            current_player)

    if rumour is None:
        continue

    stop_player = expected_rumour_stop_player(rumour, turn - 1)

    # FIXME: intrigue prevents rumour being answered - can say people don't have something but can't add a rumour
    answerer = prompt_for_player(
            'who answered{} (nothing = no one, STOP <name> = stopped)?'.format(
                " - should stop at {}".format(stop_player.name) if stop_player else ''),
            True)

    rumour.answerer = answerer
    assert rumour.answerer is not rumour.asker
    rumours.append(rumour)

    completed_rumour(rumour)

    if answerer is not None and current_player is players[0]:
        item = prompt_for_item('what was the answer?')
        record_player_has_item(rumour.answerer, item)
