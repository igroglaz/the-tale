
import smart_imports

smart_imports.all()


class TEST_RELATION(rels_django.DjangoEnum):
    records = (('REC_1', 0, 'rec_1'),
               ('REC_3', 1, 'rec_2'),
               ('REC_5', 2, 'rec_3'))


class WRONG_TEST_RELATION(rels_django.DjangoEnum):
    records = (('WREC_1', 0, 'wrec_1'),
               ('WREC_3', 1, 'wrec_2'),
               ('WREC_5', 2, 'wrec_3'))


class TestPermanentRelationStorage(permanent_storage.PermanentRelationsStorage):
    RELATION = TEST_RELATION
    VALUE_COLUMN = 'value'


class PermanentStorageTests(testcase.TestCase):

    def setUp(self):
        super(PermanentStorageTests, self).setUp()
        self.storage = permanent_storage.PermanentStorage()
        self.storage.insert(1)
        self.storage.insert(3)
        self.storage.insert(5)

    def test_serialization(self):
        self.assertEqual(set(self.storage.serialize()), set((1, 3, 5)))

    def test_deserialization(self):
        self.assertEqual(permanent_storage.PermanentStorage.deserialize(self.storage.serialize())._data, set((1, 3, 5)))

    def test_insert(self):
        self.storage.insert(4)
        self.assertEqual(self.storage._data, set((1, 3, 4, 5)))

    def test_insert_duplicate(self):
        self.assertRaises(permanent_storage.DuplicateInsertError, self.storage.insert, 3)

    def test_is_contain(self):
        self.assertTrue(1 in self.storage)
        self.assertFalse(2 in self.storage)
        self.assertTrue(3 in self.storage)
        self.assertFalse(4 in self.storage)


class PermanentRelationsStorageTests(testcase.TestCase):

    def setUp(self):
        super(PermanentRelationsStorageTests, self).setUp()
        self.storage = TestPermanentRelationStorage()
        self.storage.insert(TEST_RELATION.REC_1)
        self.storage.insert(TEST_RELATION.REC_5)

    def test_serialization(self):
        self.assertEqual(set(self.storage.serialize()), set((TEST_RELATION.REC_1.value, TEST_RELATION.REC_5.value)))

    def test_deserialization(self):
        self.assertEqual(TestPermanentRelationStorage.deserialize(self.storage.serialize())._data, set((TEST_RELATION.REC_1, TEST_RELATION.REC_5)))

    def test_insert(self):
        self.storage.insert(TEST_RELATION.REC_3)
        self.assertEqual(self.storage._data, set((TEST_RELATION.REC_1, TEST_RELATION.REC_3, TEST_RELATION.REC_5)))

    def test_insert_duplicate(self):
        self.assertRaises(permanent_storage.DuplicateInsertError, self.storage.insert, TEST_RELATION.REC_1)

    def test_insert_wrong_relation(self):
        self.assertRaises(permanent_storage.WrongRelationError, self.storage.insert, WRONG_TEST_RELATION.WREC_1)

    def test_is_contain(self):
        self.assertTrue(TEST_RELATION.REC_1 in self.storage)
        self.assertFalse(TEST_RELATION.REC_3 in self.storage)
        self.assertTrue(TEST_RELATION.REC_5 in self.storage)
        self.assertFalse(4 in self.storage)
