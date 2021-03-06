
import smart_imports

smart_imports.all()


class PAYMENT_GROUPS(rels_django.DjangoEnum):
    top_border = rels.Column()

    records = (('INT_1', 0, '0 … 600', 500),
               ('INT_2', 1, '600 … 1100', 1100),
               ('INT_3', 2, '1100 … 2600', 2600),
               ('INT_4', 3, '2600 … 10100', 10000),
               ('INT_5', 4, '10100 … 9999999', 9999999))
