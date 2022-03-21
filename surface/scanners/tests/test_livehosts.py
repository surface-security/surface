from django.test import TestCase

from django.contrib.contenttypes import models as ct_models
from dns_ips import models as dns_models
from scanners import models


class Test(TestCase):
    def test_generic_foreign_key_prefetch_related(self):
        i1 = dns_models.IPAddress.objects.create(name='8.8.8.8')
        i2 = dns_models.IPAddress.objects.create(name='4.4.4.4')
        d1 = dns_models.DNSRecord.objects.create(name='a.com')
        lh1 = models.LiveHost.objects.create(host=i1)
        models.LiveHost.objects.create(host=i2)
        models.LiveHost.objects.create(host=d1)

        self.assertEqual(lh1.host.name, '8.8.8.8')

        # old:
        # models.LiveHost.objects.filter(ip__name=X)
        # new:
        x = models.LiveHost.objects.filter(
            host_content_type=ct_models.ContentType.objects.get_for_model(dns_models.IPAddress),
            host_object_id__in=dns_models.IPAddress.objects.filter(name='8.8.8.8'),
        )
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh1)

        with self.assertNumQueries(3):
            # 1 query for LiveHosts + 1 query for each content_type found (IPAddress + DNSRecord = 2 extra queries)
            list(models.LiveHost.objects.prefetch_related('host').all())

        with self.assertNumQueries(3):
            l = list(models.LiveHost.objects.prefetch_related('host').all())
            # as `host` was prefeteched, no extra queries
            [str(ll) for ll in l]

        with self.assertNumQueries(4):
            # without prefetch, 1 extra query for each record instead (3 livehosts = 3 extra queries)
            l = list(models.LiveHost.objects.all())
            [str(ll) for ll in l]

    def test_content_type_limit(self):
        # WTF!! only IPAddress and DNSRecord in limit_choices
        # save() shouldn't allow this even if there is no DB constraint...
        # left test to reflect HOW IT IS NOT SUPPOSED TO WORK
        # IF IT STARTS FAILING -> AWESOME!
        # TODO: implement constraints in migrations in some way
        cc = dns_models.DNSDomain.objects.create()
        models.LiveHost.objects.create(host=cc)
        # THIS SHOULD BE 0!!!
        self.assertEqual(models.LiveHost.objects.count(), 1)

    def test_manager_helper(self):
        i1 = dns_models.IPAddress.objects.create(name='8.8.8.8')
        i2 = dns_models.IPAddress.objects.create(name='4.4.4.4')
        d1 = dns_models.DNSRecord.objects.create(name='a.com')
        lh1 = models.LiveHost.objects.create(host=i1)
        models.LiveHost.objects.create(host=i2)
        models.LiveHost.objects.create(host=d1)

        self.assertEqual(lh1.host.name, '8.8.8.8')

        # old:
        # models.LiveHost.objects.filter(ip__name=X)
        # new:
        x = models.LiveHost.objects.filter(host__ip__name='8.8.8.8')
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh1)

    def test_manager_helper_filter_any(self):
        i1 = dns_models.IPAddress.objects.create(name='8.8.8.8')
        i2 = dns_models.IPAddress.objects.create(name='4.4.4.4')
        d1 = dns_models.DNSRecord.objects.create(name='a.com')
        lh1 = models.LiveHost.objects.create(host=i1)
        lh2 = models.LiveHost.objects.create(host=i2)
        lh3 = models.LiveHost.objects.create(host=d1)
        # nonsense DNSRecord but just to test any
        d2 = dns_models.DNSRecord.objects.create(name='8.8.8.8')
        lh4 = models.LiveHost.objects.create(host=d2, port=8443)

        # filter _any_
        x = models.LiveHost.objects.filter(host__any__name='4.4.4.4')
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh2)
        x = models.LiveHost.objects.filter(host__any__name='a.com')
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh3)
        x = models.LiveHost.objects.filter(host__any__name='8.8.8.8')
        self.assertEqual(x.count(), 2)
        self.assertEqual({xx.pk for xx in x}, {lh1.pk, lh4.pk})
        x = models.LiveHost.objects.filter(host__any__name='8.8.8.8', port=443)
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh1)

    def test_get_or_create(self):
        i1 = dns_models.IPAddress.objects.create(name='8.8.8.8')
        lh, c = models.LiveHost.objects.get_or_create(host=i1)
        self.assertTrue(c)
        self.assertEqual(lh.host.name, '8.8.8.8')

        lh1, c = models.LiveHost.objects.get_or_create(host=i1)
        self.assertFalse(c)
        self.assertEqual(lh, lh1)

    def test_q_function(self):
        i1 = dns_models.IPAddress.objects.create(name='8.8.8.8')
        i2 = dns_models.IPAddress.objects.create(name='4.4.4.4')
        d1 = dns_models.DNSRecord.objects.create(name='a.com')
        lh1 = models.LiveHost.objects.create(host=i1)
        models.LiveHost.objects.create(host=i2)
        models.LiveHost.objects.create(host=d1)
        x = models.LiveHost.objects.filter(models.Q(host__ip__name='8.8.8.8'))
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh1)

    def test_valid_ip_re(self):
        self.assertTrue(models.LiveHostQS.valid_ip('127.0.0.1'))
        self.assertTrue(models.LiveHostQS.valid_ip('127.0.0.1'))
        self.assertTrue(models.LiveHostQS.valid_ip('127.0.0.1'))
        self.assertTrue(models.LiveHostQS.valid_ip('127.0.0.1/24'))

        self.assertFalse(models.LiveHostQS.valid_ip('x'))
        self.assertFalse(models.LiveHostQS.valid_ip('127.0.0.1/244'))

        # TODO: these should be false but is it worth making the regex more complex (and expensive)?
        # using something like: re.compile(r'^[0-2]{0,1}[0-5]{0,1}\d\.[0-2]{0,1}[0-5]{0,1}\d\.[0-2]{0,1}[0-5]{0,1}\d\.[0-2]{0,1}[0-5]{0,1}\d(\/\d{1,2})?$')
        # costs 50% more and it's not even complete yet..
        # self.assertFalse(models.LiveHostQS.valid_ip('527.0.0.1/244'))
        # self.assertFalse(models.LiveHostQS.valid_ip('277.0.0.1/244'))

    def test_another(self):
        i1 = dns_models.IPAddress.objects.create(name='8.8.8.8')
        lh1 = models.LiveHost.objects.create(host=i1)

        x = models.LiveHost.objects.filter(host__ip__name='8.8.8.8')
        self.assertEqual(x.count(), 1)
        self.assertEqual(x[0], lh1)

        x = models.LiveHost.objects.filter(host__any__name='a.com')
        self.assertEqual(x.count(), 0)

        x = models.LiveHost.objects.filter(host__ip__name='a.com')
        self.assertEqual(x.count(), 0)
