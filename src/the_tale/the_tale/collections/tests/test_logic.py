
import smart_imports

smart_imports.all()


class LogicTests(utils_testcase.TestCase):

    def setUp(self):
        super(LogicTests, self).setUp()

        game_logic.create_test_map()

        self.account_1 = self.accounts_factory.create_account()

        self.account_1_items = prototypes.AccountItemsPrototype.get_by_account_id(self.account_1.id)

        self.collection_1 = prototypes.CollectionPrototype.create(caption='collection_1', description='description_1')
        self.collection_2 = prototypes.CollectionPrototype.create(caption='collection_2', description='description_2', approved=True)

        self.kit_1 = prototypes.KitPrototype.create(collection=self.collection_1, caption='kit_1', description='description_1')
        self.kit_2 = prototypes.KitPrototype.create(collection=self.collection_2, caption='kit_2', description='description_2', approved=True)
        self.kit_3 = prototypes.KitPrototype.create(collection=self.collection_2, caption='kit_3', description='description_3', approved=True)

        self.item_1_1 = prototypes.ItemPrototype.create(kit=self.kit_1, caption='item_1_1', text='text_1_1', approved=False)
        self.item_1_2 = prototypes.ItemPrototype.create(kit=self.kit_1, caption='item_1_2', text='text_1_2', approved=True)
        self.item_2_1 = prototypes.ItemPrototype.create(kit=self.kit_2, caption='item_2_1', text='text_2_1', approved=True)
        self.item_2_2 = prototypes.ItemPrototype.create(kit=self.kit_2, caption='item_2_2', text='text_2_2', approved=False)
        self.item_3_1 = prototypes.ItemPrototype.create(kit=self.kit_3, caption='item_3_1', text='text_3_1', approved=True)

    def test_get_items_count(self):
        self.assertEqual(logic.get_items_count(prototypes.ItemPrototype._db_all()),
                         (collections.Counter({self.kit_2.id: 1, self.kit_3.id: 1}), {self.collection_2.id: 2}))

    def test_get_items_count__with_account(self):
        self.account_1_items.add_item(self.item_3_1)
        self.account_1_items.save()

        self.assertEqual(logic.get_items_count(prototypes.ItemPrototype._db_filter(id__in=self.account_1_items.items_ids())),
                         (collections.Counter({self.kit_3.id: 1}), {self.collection_2.id: 1}))

    def test_get_collections_statistics__no_account(self):
        self.assertEqual(logic.get_collections_statistics(None),
                         {'total_items_in_collections': {self.collection_2.id: 2},
                          'total_items_in_kits': collections.Counter({self.kit_2.id: 1, self.kit_3.id: 1}),
                          'account_items_in_collections': {},
                          'account_items_in_kits': {},
                          'total_items': 2,
                          'account_items': 0})

    def test_get_collections_statistics__with_account(self):

        self.account_1_items.add_item(self.item_3_1)
        self.account_1_items.save()

        self.assertEqual(logic.get_collections_statistics(self.account_1_items),
                         {'total_items_in_collections': {self.collection_2.id: 2},
                          'total_items_in_kits': collections.Counter({self.kit_2.id: 1, self.kit_3.id: 1}),
                          'account_items_in_collections': {self.collection_2.id: 1},
                          'account_items_in_kits': collections.Counter({self.kit_3.id: 1}),
                          'total_items': 2,
                          'account_items': 1})
