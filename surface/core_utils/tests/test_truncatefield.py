from django.test import TestCase

from core_utils.tests.models import TruncateFieldModel


class Test(TestCase):
    def test_truncatefield_create(self):
        name = 'x' * 10
        o = TruncateFieldModel.objects.create(name=name, name_trunc=name)
        o.refresh_from_db()
        self.assertEqual(o.name, name)
        self.assertEqual(o.name_trunc, name)

        name = 'x' * 20
        o = TruncateFieldModel.objects.create(name=name, name_trunc=name)
        o.refresh_from_db()
        self.assertEqual(o.name, name)
        # _trunc truncated
        self.assertEqual(o.name_trunc, name[:7] + '...')

    def test_truncatefield_filter(self):
        name = 'x' * 20
        o = TruncateFieldModel.objects.create(name=name, name_trunc=name)
        o.refresh_from_db()
        self.assertEqual(o.name_trunc, name[:7] + '...')

        self.assertEqual(TruncateFieldModel.objects.count(), 1)
        o = TruncateFieldModel.objects.filter(name_trunc=name).first()
        self.assertIsNotNone(o)
        self.assertEqual(o.name_trunc, name[:7] + '...')

    def test_truncate_field_get_or_create(self):
        name = 'x' * 20
        o, c = TruncateFieldModel.objects.get_or_create(name_trunc=name, defaults={'name': name})
        o.refresh_from_db()
        self.assertEqual(TruncateFieldModel.objects.count(), 1)
        self.assertTrue(c)
        self.assertEqual(o.name_trunc, name[:7] + '...')
        self.assertEqual(o.name, name)

        # should be using filter() behind the scenes
        o, c = TruncateFieldModel.objects.get_or_create(name_trunc=name, defaults={'name': 'nope'})
        self.assertEqual(TruncateFieldModel.objects.count(), 1)
        self.assertFalse(c)
        self.assertEqual(o.name_trunc, name[:7] + '...')
        # name unchanged as it was not new
        self.assertEqual(o.name, name)

        # should be using filter() behind the scenes
        o, c = TruncateFieldModel.objects.update_or_create(name_trunc=name, defaults={'name': 'nope'})
        self.assertEqual(TruncateFieldModel.objects.count(), 1)
        self.assertFalse(c)
        self.assertEqual(o.name_trunc, name[:7] + '...')
        # name changed
        self.assertEqual(o.name, 'nope')

    def test_truncate_field_create(self):
        name = 'x' * 20
        o, c = TruncateFieldModel.objects.get_or_create(name_trunc=name, defaults={'name': name})
        self.assertEqual(TruncateFieldModel.objects.count(), 1)
        self.assertTrue(c)
        # must have been truncated by the custom Model.save() method
        # TODO: find some solution that can be contained in the Field class...
        # clean method would be nice but only used by django-admin (or explicitly called)
        self.assertEqual(o.name_trunc, name[:7] + '...')
        self.assertEqual(o.name, name)
