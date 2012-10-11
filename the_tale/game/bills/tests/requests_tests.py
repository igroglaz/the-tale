# coding: utf-8

from django.test import client
from django.core.urlresolvers import reverse

from common.utils.testcase import TestCase

from accounts.prototypes import AccountPrototype
from accounts.logic import register_user

from game.logic import create_test_map

from forum.models import Post

from game.bills.models import Bill, Vote, BILL_STATE
from game.bills.prototypes import BillPrototype, VotePrototype
from game.bills.bills import PlaceRenaming
from game.bills.conf import bills_settings
from game.map.places.storage import places_storage


class BaseTestRequests(TestCase):

    def setUp(self):
        self.place1, self.place2, self.place3 = create_test_map()

        result, account_id, bundle_id = register_user('test_user1', 'test_user1@test.com', '111111')
        self.account1 = AccountPrototype.get_by_id(account_id)

        result, account_id, bundle_id = register_user('test_user2', 'test_user2@test.com', '111111')
        self.account2 = AccountPrototype.get_by_id(account_id)

        self.client = client.Client()

        self.client.post(reverse('accounts:login'), {'email': 'test_user1@test.com', 'password': '111111'})

        from forum.models import Category, SubCategory

        forum_category = Category.objects.create(caption='category-1', slug='category-1')
        SubCategory.objects.create(caption=bills_settings.FORUM_CATEGORY_SLUG + '-caption',
                                   slug=bills_settings.FORUM_CATEGORY_SLUG,
                                   category=forum_category)

    def logout(self):
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 200)

    def create_bills(self, number, owner, caption_template, rationale_template, bill_data):
        for i in xrange(number):
            BillPrototype.create(owner.user, caption_template % i, rationale_template % i, bill_data)

    def check_bill_votes(self, bill_id, votes_for, votes_against):
        bill = Bill.objects.get(id=bill_id)
        self.assertEqual(bill.votes_for, votes_for)
        self.assertEqual(bill.votes_against, votes_against)

    def check_vote(self, vote, owner, value, bill_id):
        self.assertEqual(vote.owner, owner)
        self.assertEqual(vote.value, value)
        self.assertEqual(vote.model.bill.id, bill_id)



class TestIndexRequests(BaseTestRequests):

    def test_unlogined(self):
        self.logout()
        self.check_html_ok(self.client.get(reverse('game:bills:')), texts=(('bills.unlogined', 1),))

    def test_is_fast(self):
        self.account1.is_fast = True
        self.account1.save()
        self.check_html_ok(self.client.get(reverse('game:bills:')), texts=(('bills.is_fast', 1),))

    def test_no_bills(self):
        # print self.client.get(reverse('game:bills:'))
        self.check_html_ok(self.client.get(reverse('game:bills:')), texts=(('pgf-no-bills-message', 1),))

    def test_one_page(self):
        bill_data = PlaceRenaming(place_id=self.place1.id, base_name='new_name_1')
        self.create_bills(2, self.account1, 'caption-a1-%d', 'rationale-a1-%d', bill_data)
        bill_data = PlaceRenaming(place_id=self.place2.id, base_name='new_name_2')
        self.create_bills(3, self.account2, 'caption-a2-%d', 'rationale-a2-%d', bill_data)

        texts = [('pgf-no-bills-message', 0),
                 ('caption-a1-0', 1), ('rationale-a1-0', 0),
                 ('caption-a1-1', 1), ('rationale-a1-1', 0),
                 ('caption-a2-0', 1), ('rationale-a2-0', 0),
                 ('caption-a2-1', 1), ('rationale-a2-1', 0),
                 ('caption-a2-2', 1), ('rationale-a2-2', 0),
                 ('test_user1', 2),
                 ('test_user2', 3)]

        self.check_html_ok(self.client.get(reverse('game:bills:')), texts=texts)

    def test_two_pages(self):
        bill_data = PlaceRenaming(place_id=self.place1.id, base_name='new_name_1')
        self.create_bills(bills_settings.BILLS_ON_PAGE, self.account1, 'caption-a1-%d', 'rationale-a1-%d', bill_data)
        bill_data = PlaceRenaming(place_id=self.place2.id, base_name='new_name_2')
        self.create_bills(3, self.account2, 'caption-a2-%d', 'rationale-a2-%d', bill_data)

        texts = [('pgf-no-bills-message', 0),
                 ('caption-a1-0', 1), ('rationale-a1-0', 0),
                 ('caption-a1-1', 1), ('rationale-a1-1', 0),
                 ('caption-a1-2', 1), ('rationale-a1-2', 0),
                 ('caption-a1-3', 0), ('rationale-a1-3', 0),
                 ('caption-a2-0', 0), ('rationale-a2-0', 0),
                 ('caption-a2-2', 0), ('rationale-a2-2', 0),
                 ('test_user1', 3), ('test_user2', 0)]

        self.check_html_ok(self.client.get(reverse('game:bills:')+'?page=2'), texts=texts)


class TestNewRequests(BaseTestRequests):

    def test_unlogined(self):
        self.logout()
        self.check_html_ok(self.client.get(reverse('game:bills:new') + ('?type=%s' % PlaceRenaming.type_str)), texts=(('bills.unlogined', 1),))

    def test_is_fast(self):
        self.account1.is_fast = True
        self.account1.save()
        self.check_html_ok(self.client.get(reverse('game:bills:new') + ('?type=%s' % PlaceRenaming.type_str)), texts=(('bills.is_fast', 1),))

    def test_wrong_type(self):
        self.check_html_ok(self.client.get(reverse('game:bills:new') + '?type=xxx'), texts=(('bills.new.wrong_type', 1),))

    def test_success(self):
        self.check_html_ok(self.client.get(reverse('game:bills:new') + ('?type=%s' % PlaceRenaming.type_str)))

    def test_new_place_renaming(self):
        texts = [('>'+place.name+'<', 1) for place in places_storage.all()]
        self.check_html_ok(self.client.get(reverse('game:bills:new') + ('?type=%s' % PlaceRenaming.type_str)), texts=texts)


class TestShowRequests(BaseTestRequests):

    def test_unlogined(self):
        bill_data = PlaceRenaming(place_id=self.place1.id, base_name='new_name_1')
        self.create_bills(1, self.account1, 'caption-a1-%d', 'rationale-a1-%d', bill_data)
        bill = Bill.objects.all()[0]

        self.logout()
        self.check_html_ok(self.client.get(reverse('game:bills:show', args=[bill.id])), texts=(('bills.unlogined', 1),))

    def test_is_fast(self):
        bill_data = PlaceRenaming(place_id=self.place1.id, base_name='new_name_1')
        self.create_bills(1, self.account1, 'caption-a1-%d', 'rationale-a1-%d', bill_data)
        bill = Bill.objects.all()[0]

        self.account1.is_fast = True
        self.account1.save()
        self.check_html_ok(self.client.get(reverse('game:bills:show', args=[bill.id])), texts=(('bills.is_fast', 1),))

    def test_unexsists(self):
        self.check_html_ok(self.client.get(reverse('game:bills:show', args=[0])), status_code=404)

    def test_show(self):
        bill_data = PlaceRenaming(place_id=self.place2.id, base_name='new_name_2')
        self.create_bills(1, self.account1, 'caption-a2-%d', 'rationale-a2-%d', bill_data)
        bill = Bill.objects.all()[0]

        texts = [('caption-a2-0', 2),
                 ('rationale-a2-0', 1),
                 ('test-voting-block', 0),
                 ('test-already-voted-block', 1),
                 (self.place2.name, 1)]

        self.check_html_ok(self.client.get(reverse('game:bills:show', args=[bill.id])), texts=texts)

    def test_show_after_voting(self):
        bill_data = PlaceRenaming(place_id=self.place2.id, base_name='new_name_2')
        self.create_bills(1, self.account1, 'caption-a2-%d', 'rationale-a2-%d', bill_data)
        bill = Bill.objects.all()[0]

        texts = [('test-voting-block', 1),
                 ('test-already-voted-block', 0),
                 (self.place2.name, 1)]

        self.logout()
        self.client.post(reverse('accounts:login'), {'email': 'test_user2@test.com', 'password': '111111'})

        self.check_html_ok(self.client.get(reverse('game:bills:show', args=[bill.id])), texts=texts)


class TestCreateRequests(BaseTestRequests):

    def get_post_data(self):
        return {'caption': 'bill-caption',
                'rationale': 'bill-rationale',
                'place': self.place1.id,
                'new_name': 'new-name'}

    def test_unlogined(self):
        self.logout()
        self.check_ajax_error(self.client.post(reverse('game:bills:create'), self.get_post_data()), 'bills.unlogined')

    def test_is_fast(self):
        self.account1.is_fast = True
        self.account1.save()
        self.check_ajax_error(self.client.post(reverse('game:bills:create'), self.get_post_data()), 'bills.is_fast')

    def test_type_not_exist(self):
        self.check_ajax_error(self.client.post(reverse('game:bills:create') + '?type=xxx', self.get_post_data()), 'bills.create.wrong_type')

    def test_success(self):
        response = self.client.post(reverse('game:bills:create') + ('?type=%s' % PlaceRenaming.type_str), self.get_post_data())

        bill = BillPrototype(Bill.objects.all()[0])
        self.assertEqual(bill.caption, 'bill-caption')
        self.assertEqual(bill.rationale, 'bill-rationale')
        self.assertEqual(bill.data.place.id, self.place1.id)
        self.assertEqual(bill.data.base_name, 'new-name')
        self.assertEqual(bill.votes_for, 1)
        self.assertEqual(bill.votes_against, 0)

        vote = VotePrototype(Vote.objects.all()[0])
        self.check_vote(vote, self.account1.user, True, bill.id)

        self.check_ajax_ok(response, data={'next_url': reverse('game:bills:show', args=[bill.id])})



class TestVoteRequests(BaseTestRequests):

    def setUp(self):
        super(TestVoteRequests, self).setUp()

        self.client.post(reverse('game:bills:create') + ('?type=%s' % PlaceRenaming.type_str), {'caption': 'bill-caption',
                                                                                                'rationale': 'bill-rationale',
                                                                                                'place': self.place1.id,
                                                                                                'new_name': 'new-name'})
        self.bill = BillPrototype(Bill.objects.all()[0])

        self.logout()
        self.client.post(reverse('accounts:login'), {'email': 'test_user2@test.com', 'password': '111111'})

    def test_unlogined(self):
        self.logout()
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}), 'bills.unlogined')

    def test_is_fast(self):
        self.account2.is_fast = True
        self.account2.save()
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}), 'bills.is_fast')
        self.check_bill_votes(self.bill.id, 1, 0)

    def test_bill_not_exists(self):
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[666]) + '?value=for', {}), 'bills.wrong_bill_id')

    def test_wrong_value(self):
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=xxx', {}), 'bills.vote.wrong_value')
        self.check_bill_votes(self.bill.id, 1, 0)

    def test_bill_accepted(self):
        self.bill.state = BILL_STATE.ACCEPTED
        self.bill.save()
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}), 'bills.vote.wrong_bill_state')
        self.check_bill_votes(self.bill.id, 1, 0)

    def test_bill_rejected(self):
        self.bill.state = BILL_STATE.REJECTED
        self.bill.save()
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}), 'bills.vote.wrong_bill_state')
        self.check_bill_votes(self.bill.id, 1, 0)

    def test_success_for(self):
        self.check_ajax_ok(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}))
        vote = VotePrototype(Vote.objects.all()[1])
        self.check_vote(vote, self.account2.user, True, self.bill.id)
        self.check_bill_votes(self.bill.id, 2, 0)

    def test_success_agains(self):
        self.check_ajax_ok(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=against', {}))
        vote = VotePrototype(Vote.objects.all()[1])
        self.check_vote(vote, self.account2.user, False, self.bill.id)
        self.check_bill_votes(self.bill.id, 1, 1)

    def test_already_exists(self):
        self.check_ajax_ok(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}))
        self.check_ajax_error(self.client.post(reverse('game:bills:vote', args=[self.bill.id]) + '?value=for', {}), 'bills.vote.vote_exists')
        self.check_bill_votes(self.bill.id, 2, 0)


class TestEditRequests(BaseTestRequests):

    def setUp(self):
        super(TestEditRequests, self).setUp()

        self.client.post(reverse('game:bills:create') + ('?type=%s' % PlaceRenaming.type_str), {'caption': 'bill-caption',
                                                                                                'rationale': 'bill-rationale',
                                                                                                'place': self.place1.id,
                                                                                                'new_name': 'new-name'})
        self.bill = BillPrototype(Bill.objects.all()[0])


    def test_unlogined(self):
        self.logout()
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[self.bill.id])), texts=(('bills.unlogined', 1),))

    def test_is_fast(self):
        self.account1.is_fast = True
        self.account1.save()
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[self.bill.id])), texts=(('bills.is_fast', 1),))

    def test_unexsists(self):
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[666])), status_code=404)

    def test_no_permissions(self):
        self.logout()
        self.client.post(reverse('accounts:login'), {'email': 'test_user2@test.com', 'password': '111111'})
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[self.bill.id])), texts=(('bills.edit.no_permissions', 1),))

    def test_wrong_state(self):
        self.bill.state = BILL_STATE.ACCEPTED
        self.bill.save()
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[self.bill.id])), texts=(('bills.edit.wrong_state', 1),))

    def test_success(self):
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[self.bill.id])))

    def test_edit_place_renaming(self):
        texts = [('>'+place.name+'<', 1) for place in places_storage.all()]
        self.check_html_ok(self.client.get(reverse('game:bills:edit', args=[self.bill.id])), texts=texts)


class TestUpdateRequests(BaseTestRequests):

    def setUp(self):
        super(TestUpdateRequests, self).setUp()

        self.client.post(reverse('game:bills:create') + ('?type=%s' % PlaceRenaming.type_str), {'caption': 'bill-caption',
                                                                                                'rationale': 'bill-rationale',
                                                                                                'place': self.place1.id,
                                                                                                'new_name': 'new-name'})
        self.bill = BillPrototype(Bill.objects.all()[0])

    def get_post_data(self):
        return {'caption': 'new-caption',
                'rationale': 'new-rationale',
                'place': self.place2.id,
                'new_name': 'new-new-name'}



    def test_unlogined(self):
        self.logout()
        self.check_ajax_error(self.client.post(reverse('game:bills:update', args=[self.bill.id]), self.get_post_data()), 'bills.unlogined')

    def test_is_fast(self):
        self.account1.is_fast = True
        self.account1.save()
        self.check_ajax_error(self.client.post(reverse('game:bills:update', args=[self.bill.id]), self.get_post_data()), 'bills.is_fast')

    def test_type_not_exist(self):
        self.check_ajax_error(self.client.post(reverse('game:bills:update', args=[666]), self.get_post_data()), 'bills.wrong_bill_id')

    def test_no_permissions(self):
        self.logout()
        self.client.post(reverse('accounts:login'), {'email': 'test_user2@test.com', 'password': '111111'})
        self.check_ajax_error(self.client.post(reverse('game:bills:update', args=[self.bill.id]), self.get_post_data()), 'bills.update.no_permissions')

    def test_wrong_state(self):
        self.bill.state = BILL_STATE.ACCEPTED
        self.bill.save()
        self.check_ajax_error(self.client.post(reverse('game:bills:update', args=[self.bill.id]), self.get_post_data()), 'bills.update.wrong_state')

    def test_form_errors(self):
        self.check_ajax_error(self.client.post(reverse('game:bills:update', args=[self.bill.id]), {}), 'bills.update.form_errors')

    def test_update_success(self):
        old_updated_at = self.bill.updated_at

        self.assertEqual(Post.objects.all().count(), 1)

        self.check_ajax_ok(self.client.post(reverse('game:bills:update', args=[self.bill.id]), self.get_post_data()))

        self.bill = BillPrototype.get_by_id(self.bill.id)
        self.assertTrue(old_updated_at < self.bill.updated_at)

        self.assertEqual(Post.objects.all().count(), 2)