# coding: utf-8
import random
import time
import datetime

from the_tale.game.balance import constants as c, formulas as f

from the_tale.game.heroes.conf import heroes_settings

from the_tale.game.heroes.habilities.relations import ABILITY_TYPE, ABILITY_AVAILABILITY, ABILITY_ACTIVATION_TYPE, ABILITY_LOGIC_TYPE
from the_tale.game.heroes.habilities.battle import ABILITIES as BATTLE_ABILITIES
from the_tale.game.heroes.habilities.attributes import ABILITIES as ATTRIBUTES_ABILITIES
from the_tale.game.heroes.habilities.modifiers import ABILITIES as MODIFIERS_ABILITIES
from the_tale.game.heroes.habilities.nonbattle import ABILITIES as NONBATTLE_ABILITIES


ABILITIES = dict(**BATTLE_ABILITIES)
ABILITIES.update(**ATTRIBUTES_ABILITIES)
ABILITIES.update(**MODIFIERS_ABILITIES)
ABILITIES.update(**NONBATTLE_ABILITIES)

__all__ = ['ABILITIES', 'ABILITY_LOGIC_TYPE', 'ABILITY_TYPE', 'ABILITY_AVAILABILITY', 'ABILITY_ACTIVATION_TYPE']

class AbilitiesPrototype(object):

    __slots__ = ('abilities', 'reseted_at', 'destiny_points_spend', 'updated', 'hero')

    def __init__(self):
        self.abilities = {}
        self.reseted_at = datetime.datetime.now()
        self.destiny_points_spend = 0
        self.updated = False
        self.hero = None

    def set_reseted_at(self, reseted_at):
        self.reseted_at = reseted_at

    def serialize(self):
        data = {'abilities': {},
                'reseted_at': time.mktime(self.reseted_at.timetuple()),
                'destiny_points_spend': self.destiny_points_spend}
        for ability_id, ability in self.abilities.items():
            data['abilities'][ability_id] = ability.serialize()

        return data

    @classmethod
    def deserialize(cls, hero, data):
        abilities = cls()

        for ability_id, ability_data in data['abilities'].items():
            ability = ABILITIES[ability_id].deserialize(ability_data)
            abilities.abilities[ability_id] = ability

        abilities.reseted_at = datetime.datetime.fromtimestamp(data.get('reseted_at', 0))
        abilities.destiny_points_spend = data.get('destiny_points_spend', 0)
        abilities.hero = hero

        return abilities

    @property
    def can_reset(self):
        return self.reseted_at + heroes_settings.ABILITIES_RESET_TIMEOUT < datetime.datetime.now()

    def reset(self):
        self.destiny_points_spend += 1
        self.reseted_at = datetime.datetime.now()
        self.initialize()
        self.updated = True

    @property
    def time_before_reset(self):
        return max(datetime.timedelta(seconds=0), (self.reseted_at + heroes_settings.ABILITIES_RESET_TIMEOUT - datetime.datetime.now()))

    def initialize(self):
        ability = ABILITIES['hit'](level=1)
        self.abilities = {ability.get_id(): ability}

    @classmethod
    def create(cls):
        abilities = cls()
        abilities.initialize()
        return abilities

    @property
    def all(self): return self.abilities.values()

    @property
    def active_abilities(self): return [ability for ability in self.abilities.values() if ability.activation_type._is_ACTIVE]

    @property
    def passive_abilities(self): return [ability for ability in self.abilities.values() if ability.activation_type._is_PASSIVE]

    def has(self, ability_id): return ability_id in self.abilities

    def get(self, ability_id): return self.abilities[ability_id]

    def add(self, ability_id, level=1):
        self.updated = True
        self.abilities[ability_id] = ABILITIES[ability_id](level=level)
        self.destiny_points_spend += 1

    def increment_level(self, ability_id):
        self.updated = True
        self.abilities[ability_id].level += 1
        self.destiny_points_spend += 1

    def _get_candidates(self):

        ability_type=self.next_ability_type

        max_active_abilities, max_passive_abilities = self.ability_types_limitations[ability_type]

        # filter by type (battle, nonbattle, etc...)
        ability_classes = filter(lambda a: a.TYPE==ability_type, ABILITIES.values()) # pylint: disable=W0110
        choosen_abilities = filter(lambda a: a.TYPE==ability_type, self.abilities.values()) # pylint: disable=W0110

        # filter by availability for players
        ability_classes = filter(lambda a: a.AVAILABILITY.value & ABILITY_AVAILABILITY.FOR_PLAYERS.value, ability_classes) # pylint: disable=W0110

        # filter abilities with max level
        ability_classes = filter(lambda a: not (self.has(a.get_id()) and self.get(a.get_id()).has_max_level), ability_classes) # pylint: disable=W0110

        # filter unchoosen abilities if there are no free slots
        free_active_slots = max_active_abilities - len(filter(lambda a: a.ACTIVATION_TYPE==ABILITY_ACTIVATION_TYPE.ACTIVE, choosen_abilities)) # pylint: disable=W0110
        free_passive_slots = max_passive_abilities - len(filter(lambda a: a.ACTIVATION_TYPE==ABILITY_ACTIVATION_TYPE.PASSIVE, choosen_abilities)) # pylint: disable=W0110

        candidates = [a(level=1 if not self.has(a.get_id()) else self.get(a.get_id()).level+1)
                      for a in ability_classes]

        if free_active_slots <= 0:
            candidates = filter(lambda a: not a.activation_type._is_ACTIVE or self.has(a.get_id()), candidates) # pylint: disable=W0110

        if free_passive_slots <= 0:
            candidates = filter(lambda a: not a.activation_type._is_PASSIVE or self.has(a.get_id()), candidates) # pylint: disable=W0110

        return candidates


    def _get_for_choose(self, candidates, max_old_abilities_for_choose, max_abilities_for_choose):
        old_candidates = filter(lambda a: self.has(a.get_id()), candidates) # pylint: disable=W0110
        new_candidates = filter(lambda a: not self.has(a.get_id()), candidates) # pylint: disable=W0110

        first_old_candidates = random.sample(old_candidates, min(max_old_abilities_for_choose, len(old_candidates)))
        # second_old_candidates = filter(lambda a: a not in first_old_candidates, old_candidates)
        new_candidates = random.sample(new_candidates, min(max_abilities_for_choose - len(first_old_candidates), len(new_candidates)))

        candidates = first_old_candidates + new_candidates

        random.shuffle(candidates)

        return candidates

    def modify_attribute(self, name, value):
        for ability in self.abilities.values():
            value = ability.modify_attribute(name, value)
        return value

    def update_context(self, actor, enemy):
        for ability in self.abilities.values():
            ability.update_context(actor, enemy)

    def update_quest_reward(self, hero, money):
        for ability in self.abilities.values():
            money = ability.update_quest_reward(hero, money)
        return money

    def update_buy_price(self, hero, money):
        for ability in self.abilities.values():
            money = ability.update_buy_price(hero, money)
        return money

    def update_sell_price(self, hero, money):
        for ability in self.abilities.values():
            money = ability.update_sell_price(hero, money)
        return money

    def update_items_of_expenditure_priorities(self, hero, priorities):
        for ability in self.abilities.values():
            priorities = ability.update_items_of_expenditure_priorities(hero, priorities)
        return priorities

    def can_get_artifact_for_quest(self, hero):
        for ability in self.abilities.values():
            if ability.can_get_artifact_for_quest(hero):
                return True
        return False

    def can_buy_better_artifact(self, hero):
        for ability in self.abilities.values():
            if ability.can_buy_better_artifact(hero):
                return True
        return False

    def randomized_level_up(self, levels):

        for i in xrange(levels):

            candidates = []

            for ability in self.abilities.values():
                if not ability.has_max_level:
                    candidates.append(ability)

            if not candidates: return levels - i

            ability = random.choice(candidates)
            ability.level += 1
            self.updated = True

        return 0

    @property
    def ability_types_limitations(self):
        return {ABILITY_TYPE.BATTLE: (c.ABILITIES_ACTIVE_MAXIMUM, c.ABILITIES_PASSIVE_MAXIMUM),
                ABILITY_TYPE.NONBATTLE: (c.ABILITIES_NONBATTLE_MAXUMUM, c.ABILITIES_NONBATTLE_MAXUMUM)}

    def get_for_choose(self):

        random_state = random.getstate()
        random.seed(self.hero.id + self.destiny_points_spend)

        candidates = self._get_candidates()


        abilities = self._get_for_choose(candidates,
                                         max_old_abilities_for_choose=c.ABILITIES_OLD_ABILITIES_FOR_CHOOSE_MAXIMUM,
                                         max_abilities_for_choose=c.ABILITIES_FOR_CHOOSE_MAXIMUM)

        random.setstate(random_state)

        return abilities

    def can_rechoose_abilities_choices(self):
        candidates = self._get_candidates()

        return not (all(self.has(ability.get_id()) for ability in candidates) and
                    len(candidates) <= c.ABILITIES_OLD_ABILITIES_FOR_CHOOSE_MAXIMUM)

    def rechooce_choices(self):
        if not self.can_rechoose_abilities_choices():
            return False

        old_choices = set(ability.get_id() for ability in self.get_for_choose())
        new_choices = old_choices

        while old_choices == new_choices:
            self.destiny_points_spend += 1
            new_choices = set(ability.get_id() for ability in self.get_for_choose())

        self.updated = True

        return True


    @property
    def max_ability_points_number(self):
        return f.max_ability_points_number(self.hero.level)

    @property
    def current_ability_points_number(self):
        return sum(ability.level for ability in self.abilities.values())

    @property
    def can_choose_new_ability(self):
        return self.current_ability_points_number < self.max_ability_points_number

    @property
    def destiny_points(self):
        return self.max_ability_points_number - self.current_ability_points_number

    @property
    def next_ability_type(self):
        return {1: ABILITY_TYPE.BATTLE,
                2: ABILITY_TYPE.BATTLE,
                0: ABILITY_TYPE.NONBATTLE}[self.current_ability_points_number % 3]

    @property
    def next_battle_ability_point_lvl(self):
        delta = self.hero.level % 6
        return {0: 1,
                1: 2,
                2: 1,
                3: 4,
                4: 3,
                5: 2}[delta] + self.hero.level

    @property
    def next_nonbattle_ability_point_lvl(self):
        delta = self.hero.level % 6
        return {0: 5,
                1: 4,
                2: 3,
                3: 2,
                4: 1,
                5: 6}[delta] + self.hero.level


    def __eq__(self, other):
        return set(self.abilities.keys()) == set(other.abilities.keys())
