# coding: utf-8
import mock

from the_tale.common.utils import testcase

from the_tale.accounts.prototypes import AccountPrototype
from the_tale.accounts.logic import register_user

from the_tale.game.bundles import BundlePrototype
from the_tale.game.models import Bundle
from the_tale.game.logic import remove_game_data, create_test_map, form_game_info
from the_tale.game.prototypes import TimePrototype

from the_tale.game.pvp.tests.helpers import PvPTestsMixin
from the_tale.game.pvp.models import BATTLE_1X1_STATE

from the_tale.game.heroes.prototypes import HeroPrototype


class LogicTests(testcase.TestCase):

    def setUp(self):
        super(LogicTests, self).setUp()
        create_test_map()

        result, account_id, bundle_id = register_user('test_user')

        self.account_id = account_id
        self.bundle = BundlePrototype.get_by_id(bundle_id)

    def test_remove_game_data(self):

        self.assertEqual(Bundle.objects.all().count(), 1)
        self.assertEqual(HeroPrototype._db_count(), 1)

        remove_game_data(AccountPrototype.get_by_id(self.account_id))

        self.assertEqual(Bundle.objects.all().count(), 0)
        self.assertEqual(HeroPrototype._db_count(), 0)



class FormGameInfoTests(testcase.TestCase, PvPTestsMixin):

    def setUp(self):
        super(FormGameInfoTests, self).setUp()
        create_test_map()

        result, account_id, bundle_id = register_user('test_user_1')
        self.account_1 = AccountPrototype.get_by_id(account_id)

        result, account_id, bundle_id = register_user('test_user_2')
        self.account_2 = AccountPrototype.get_by_id(account_id)

    def test_no_account(self):
        data = form_game_info()
        self.assertEqual(data['mode'], 'pve')
        self.assertEqual(data['account'], None)
        self.assertEqual(data['enemy'], None)

    def test_account(self):
        data = form_game_info(self.account_1, is_own=True)
        self.assertEqual(data['mode'], 'pve')
        self.assertFalse(data['account']['in_pvp_queue'])
        self.assertEqual(data['account']['id'], self.account_1.id)
        self.assertEqual(data['enemy'], None)

    def test_account__other(self):
        data = form_game_info(self.account_2, is_own=True)
        self.assertEqual(data['mode'], 'pve')
        self.assertFalse(data['account']['in_pvp_queue'])
        self.assertEqual(data['account']['id'], self.account_2.id)
        self.assertEqual(data['enemy'], None)

    def test_pvp_in_queue(self):
        self.pvp_create_battle(self.account_1, None)
        self.pvp_create_battle(self.account_2, None)

        data = form_game_info(self.account_1)
        self.assertEqual(data['mode'], 'pve')
        self.assertTrue(data['account']['in_pvp_queue'])
        self.assertEqual(data['enemy'], None)

    def test_pvp_prepairing(self):
        self.pvp_create_battle(self.account_1, self.account_2, state=BATTLE_1X1_STATE.PREPAIRING)
        self.pvp_create_battle(self.account_2, self.account_1, state=BATTLE_1X1_STATE.PREPAIRING)

        data = form_game_info(self.account_1)
        self.assertEqual(data['mode'], 'pvp')
        self.assertFalse(data['account']['in_pvp_queue'])
        self.assertNotEqual(data['enemy'], None)

    def test_pvp_processing(self):
        self.pvp_create_battle(self.account_1, self.account_2, state=BATTLE_1X1_STATE.PROCESSING)
        self.pvp_create_battle(self.account_2, self.account_1, state=BATTLE_1X1_STATE.PROCESSING)

        data = form_game_info(self.account_1)
        self.assertEqual(data['mode'], 'pvp')
        self.assertFalse(data['account']['in_pvp_queue'])
        self.assertFalse(data['enemy']['in_pvp_queue'])

        self.assertEqual(data['account']['id'], self.account_1.id)
        self.assertEqual(data['enemy']['id'], self.account_2.id)

    def test_own_hero_get_cached_data(self):
        hero = HeroPrototype.get_by_account_id(self.account_1.id)

        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.cached_ui_info_for_hero',
                        mock.Mock(return_value={'actual_on_turn': hero.saved_at_turn,
                                                'pvp__actual':'actual',
                                                'pvp__last_turn':'last_turn',
                                                'ui_caching_started_at': 0})) as cached_ui_info_for_hero:
            with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info') as ui_info:
                data = form_game_info(self.account_1, is_own=True)

        self.assertEqual(data['account']['hero']['pvp'], 'actual')
        self.assertEqual(data['enemy'], None)

        self.assertFalse('pvp__actual' in data['account']['hero']['pvp'])
        self.assertFalse('pvp__last_turn' in data['account']['hero']['pvp'])

        self.assertEqual(cached_ui_info_for_hero.call_count, 1)
        self.assertEqual(cached_ui_info_for_hero.call_args, mock.call(self.account_1.id))
        self.assertEqual(ui_info.call_count, 0)

    def test_not_own_hero_get_cached_data(self):
        hero = HeroPrototype.get_by_account_id(self.account_1.id)

        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info',
                        mock.Mock(return_value={'actual_on_turn': hero.saved_at_turn,
                                                'pvp__actual':'actual',
                                                'pvp__last_turn':'last_turn',
                                                'ui_caching_started_at': 0})) as ui_info:
            data = form_game_info(self.account_1, is_own=False)

        self.assertEqual(data['account']['hero']['pvp'], 'last_turn')
        self.assertEqual(data['enemy'], None)

        self.assertFalse('pvp__actual' in data['account']['hero']['pvp'])
        self.assertFalse('pvp__last_turn' in data['account']['hero']['pvp'])

        self.assertEqual(ui_info.call_count, 1)
        self.assertEqual(ui_info.call_args, mock.call(actual_guaranteed=False))

    def test_is_old(self):
        self.assertFalse(form_game_info(self.account_1, is_own=True)['account']['is_old'])

        TimePrototype(turn_number=666).save()
        self.assertTrue(form_game_info(self.account_1, is_own=True)['account']['is_old'])

        HeroPrototype.get_by_account_id(self.account_1.id).save()
        self.assertFalse(form_game_info(self.account_1, is_own=True)['account']['is_old'])

    def test_is_old__not_own_hero(self):
        self.assertFalse(form_game_info(self.account_1, is_own=False)['account']['is_old'])

        TimePrototype(turn_number=666).save()
        self.assertTrue(form_game_info(self.account_1, is_own=False)['account']['is_old'])

        HeroPrototype.get_by_account_id(self.account_1.id).save()
        self.assertFalse(form_game_info(self.account_1, is_own=False)['account']['is_old'])


    def test_is_old__pvp(self):
        self.pvp_create_battle(self.account_1, self.account_2, BATTLE_1X1_STATE.PROCESSING)
        self.pvp_create_battle(self.account_2, self.account_1, BATTLE_1X1_STATE.PROCESSING)

        hero_1 = HeroPrototype.get_by_account_id(self.account_1.id)
        hero_2 = HeroPrototype.get_by_account_id(self.account_2.id)

        self.assertFalse(form_game_info(self.account_1)['account']['is_old'])
        self.assertFalse(form_game_info(self.account_1)['enemy']['is_old'])

        TimePrototype(turn_number=666).save()
        self.assertTrue(form_game_info(self.account_1)['account']['is_old'])
        self.assertTrue(form_game_info(self.account_1)['enemy']['is_old'])

        hero_1.save()
        hero_2.save()

        self.assertFalse(form_game_info(self.account_1)['account']['is_old'])
        self.assertFalse(form_game_info(self.account_1)['enemy']['is_old'])


    def test_game_info_data_hidding(self):
        '''
        player hero always must show actual data
        enemy hero always must show data on statrt of the turn
        '''
        self.pvp_create_battle(self.account_1, self.account_2, BATTLE_1X1_STATE.PROCESSING)
        self.pvp_create_battle(self.account_2, self.account_1, BATTLE_1X1_STATE.PROCESSING)

        hero_1 = HeroPrototype.get_by_account_id(self.account_1.id)
        hero_2 = HeroPrototype.get_by_account_id(self.account_2.id)

        hero_1.pvp.set_energy(1)
        hero_1.save()

        hero_2.pvp.set_energy(2)
        hero_2.save()

        data = form_game_info(self.account_1, is_own=True)

        self.assertEqual(data['account']['hero']['pvp']['energy'], 1)
        self.assertEqual(data['enemy']['hero']['pvp']['energy'], 0)

        hero_2.pvp.store_turn_data()
        hero_2.save()

        data = form_game_info(self.account_1, is_own=True)

        self.assertEqual(data['enemy']['hero']['pvp']['energy'], 2)

    def test_game_info_caching(self):
        self.pvp_create_battle(self.account_1, self.account_2, BATTLE_1X1_STATE.PROCESSING)
        self.pvp_create_battle(self.account_2, self.account_1, BATTLE_1X1_STATE.PROCESSING)

        hero_1 = HeroPrototype.get_by_account_id(self.account_1.id)
        hero_2 = HeroPrototype.get_by_account_id(self.account_2.id)

        def get_ui_info(self, **kwargs):
            if self.id == hero_1.id:
                return {'actual_on_turn': hero_1.saved_at_turn,
                        'pvp__actual':'actual',
                        'pvp__last_turn':'last_turn',
                        'ui_caching_started_at': 0}
            else:
                return {'actual_on_turn': hero_2.saved_at_turn,
                        'pvp__actual':'actual',
                        'pvp__last_turn':'last_turn',
                        'ui_caching_started_at': 0}

        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info', get_ui_info):
            data = form_game_info(self.account_1, is_own=True)

        self.assertEqual(data['account']['hero']['pvp'], 'actual')
        self.assertEqual(data['enemy']['hero']['pvp'], 'last_turn')

        self.assertFalse('pvp__actual' in data['account']['hero']['pvp'])
        self.assertFalse('pvp__last_turn' in data['account']['hero']['pvp'])
        self.assertFalse('pvp__actual' in data['enemy']['hero']['pvp'])
        self.assertFalse('pvp__last_turn' in data['enemy']['hero']['pvp'])