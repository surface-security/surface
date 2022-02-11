from django.test import TestCase

from dns_ips.models import DNSRecord, DNSRecordValue, IPAddress
from core_utils.db.models import GroupConcat


class Test(TestCase):
    def test_values(self):
        d1 = DNSRecord.objects.create(name='a.com')
        d2 = DNSRecord.objects.create(name='b.com')
        self.assertEqual(DNSRecord.objects.count(), 2)
        DNSRecordValue.objects.bulk_create(
            [
                DNSRecordValue(record=d1, rtype=DNSRecordValue.RecordType.A, value='1.1.1.1'),
                DNSRecordValue(record=d1, rtype=DNSRecordValue.RecordType.A, value='8.8.8.8'),
                DNSRecordValue(record=d2, rtype=DNSRecordValue.RecordType.A, value='1.1.1.1'),
                DNSRecordValue(record=d2, rtype=DNSRecordValue.RecordType.CNAME, value='b.b.com'),
            ]
        )

        # returns duplicate values (and not even cached to be useful...)
        with self.assertNumQueries(1):
            self.assertEqual(
                list(DNSRecord.objects.filter(dnsrecordvalue__rtype=DNSRecordValue.RecordType.A)), [d1, d1, d2]
            )
        # distinct solves though...
        with self.assertNumQueries(1):
            self.assertEqual(
                list(DNSRecord.objects.filter(dnsrecordvalue__rtype=DNSRecordValue.RecordType.A).distinct()), [d1, d2]
            )
        # avoids distinct and duplicates, but looks quite weird...
        with self.assertNumQueries(1):
            self.assertEqual(
                list(
                    DNSRecord.objects.filter(
                        pk__in=DNSRecordValue.objects.filter(rtype=DNSRecordValue.RecordType.A).values('record')
                    )
                ),
                [d1, d2],
            )

        # prefetch_related works
        with self.assertNumQueries(3):
            # main query (1) + 1 value query per record (2) = 3
            l = list(DNSRecord.objects.filter(dnsrecordvalue__rtype=DNSRecordValue.RecordType.A).distinct())
            self.assertEqual(len(l), 2)
            for r in l:
                list(r.dnsrecordvalue_set.all())
        with self.assertNumQueries(2):
            # main query (1) + prefetch query (1) = 2
            l = list(
                DNSRecord.objects.filter(dnsrecordvalue__rtype=DNSRecordValue.RecordType.A)
                .distinct()
                .prefetch_related('dnsrecordvalue_set')
            )
            self.assertEqual(len(l), 2)
            for r in l:
                list(r.dnsrecordvalue_set.all())

    def test_concat(self):
        # test GROUP_CONCAT fetch list of IP PKs related to record value in single query (without prefetch overhead)
        d1 = DNSRecord.objects.create(name='a.com')
        d2 = DNSRecord.objects.create(name='b.com')
        dv11 = DNSRecordValue.objects.create(record=d1, rtype=DNSRecordValue.RecordType.A, value='1.1.1.1')
        dv12 = DNSRecordValue.objects.create(record=d1, rtype=DNSRecordValue.RecordType.CNAME, value='b.b.com')
        dv21 = DNSRecordValue.objects.create(record=d2, rtype=DNSRecordValue.RecordType.CNAME, value='b.b.com')
        dv11.ips.add(IPAddress.objects.create(name='1.1.1.1'))
        dv12.ips.add(IPAddress.objects.create(name='1.1.1.2'))
        dv12.ips.add(IPAddress.objects.create(name='1.1.1.3'))
        dv21.ips.add(IPAddress.objects.create(name='8.8.8.8'))

        with self.assertNumQueries(1):
            for rv in DNSRecordValue.objects.all().annotate(ip_pk_list=GroupConcat('ips', separator=',')):
                if rv.pk in (dv11.pk, dv21.pk):
                    self.assertNotIn(',', rv.ip_pk_list)
                if rv.pk == dv12.pk:
                    self.assertIn(',', rv.ip_pk_list)

        with self.assertNumQueries(2):
            list(DNSRecordValue.objects.all().prefetch_related('ips'))
