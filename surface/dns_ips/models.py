import functools

from django.db import models
from django.utils import timezone

from bulk_update_or_create import BulkUpdateOrCreateQuerySet

from core_utils.fields import RangeModel


def default_source_unknown():
    # migrations won't support lru_cache wrapped callers, so wrap the wrapper!
    # TODO: add TTL to this?
    @functools.lru_cache
    def wrap():
        u, _ = Source.objects.get_or_create(
            name="UNKNOWN",
            defaults={
                "function": "",
                "owner": "",
            },
        )
        return u.pk

    return wrap()


class Tag(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "DNS & IPs Tag"
        verbose_name_plural = "DNS & IPs Tags"


class Source(models.Model):
    name = models.CharField(max_length=255, unique=True)
    function = models.CharField(max_length=255, null=False, blank=False, db_index=True)
    owner = models.CharField(max_length=255, null=False, blank=False, db_index=True)
    active = models.BooleanField(default=True, db_index=True)
    last_sync = models.DateTimeField(
        default=timezone.now, editable=False, db_index=True
    )
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Source"
        verbose_name_plural = "Sources"


class Organisation(models.Model):
    source = models.ForeignKey(
        "Source", blank=True, null=True, on_delete=models.CASCADE
    )
    source_key = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)

    name = models.CharField(max_length=255, null=False, blank=False)
    owned_by_us = models.BooleanField(default=False, db_index=True)
    whitelisted_to_be_scanned = models.BooleanField(default=False, db_index=True)
    point_of_contact = models.CharField(max_length=1024, null=True, blank=True)

    country = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    website = models.CharField(max_length=512, null=True, blank=True)
    owner = models.CharField(max_length=255, null=True, blank=True)
    key_supplier = models.CharField(max_length=255, null=True, blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    customer = models.CharField(max_length=255, null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"


class IPRange(RangeModel):
    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, default=default_source_unknown
    )
    active = models.BooleanField(default=True, db_index=True)
    last_seen = models.DateTimeField(
        default=timezone.now, editable=False, null=True, blank=True, db_index=True
    )

    vlan = models.CharField(max_length=255, null=True, blank=True)
    zone = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    datacenter = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.range

    def slack_display(self):
        return f"{self.range} (DC {self.datacenter}, vlan {self.vlan})"

    class Meta:
        verbose_name = "IP Range"
        verbose_name_plural = "IP Ranges"


class IPRangeThirdParty(models.Model):
    range = models.ForeignKey(
        "dns_ips.IPRange", blank=True, null=True, on_delete=models.CASCADE
    )
    organisation = models.ForeignKey(
        "Organisation", blank=True, null=True, on_delete=models.CASCADE
    )
    sn_ref = models.CharField(max_length=64, blank=True, null=True)
    expected_traffic = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    expected_ports = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    expected_protocol = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.sn_ref} ({self.expected_traffic})"

    class Meta:
        verbose_name = "IP Range - Third Party (SN)"
        verbose_name_plural = "IP Ranges - Third Parties (SN)"


class IPAddress(models.Model):
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    source = models.ForeignKey(
        "Source",
        related_name="dns_ips_source",
        on_delete=models.CASCADE,
        default=default_source_unknown,
    )
    active = models.BooleanField(default=True, db_index=True)
    last_seen = models.DateTimeField(
        default=timezone.now, editable=False, null=True, blank=True, db_index=True
    )

    name = models.GenericIPAddressField(db_index=True)
    organisation = models.ForeignKey(
        "Organisation", blank=True, null=True, on_delete=models.CASCADE
    )
    organisation_ip_owner = models.ForeignKey(
        "Organisation",
        blank=True,
        null=True,
        related_name="organisation_ip_owner",
        on_delete=models.CASCADE,
    )
    tags = models.ManyToManyField("dns_ips.Tag", blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.name) or ""

    def slack_display(self):
        if self.name is not None:
            return "{} ({}, {}, {})".format(
                str(self.name),
                str(self.location),
                str(self.organisation) or "",
                str(self.notes),
            )
        return ""

    class Meta:
        verbose_name = "IP Address"
        verbose_name_plural = "IP Addresses"
        unique_together = (("source", "name"),)


class DNSNameserver(models.Model):
    objects = BulkUpdateOrCreateQuerySet.as_manager()

    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, default=default_source_unknown
    )
    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(
        default=timezone.now, editable=False, null=True, blank=True
    )
    name = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "DNS Nameserver"
        verbose_name_plural = "DNS Nameservers"


class DNSDomain(models.Model):
    source = models.ForeignKey(
        "Source",
        related_name="domain_source",
        on_delete=models.CASCADE,
        default=default_source_unknown,
    )
    active = models.BooleanField(default=True, db_index=True)
    last_seen = models.DateTimeField(
        default=timezone.now, editable=False, null=True, blank=True, db_index=True
    )

    name = models.CharField(max_length=255, db_index=True, null=True)
    notes = models.TextField(null=True, blank=True)
    registration_date = models.DateTimeField(null=True, blank=True, db_index=True)
    expire_date = models.DateTimeField(null=True, blank=True, db_index=True)
    raw_whois = models.TextField(null=True, blank=True)
    # Options for Domain
    register_management_status = models.BooleanField(default=False, db_index=True)
    register_dns_managed = models.BooleanField(default=False, db_index=True)
    register_csc_lock = models.BooleanField(default=False, db_index=True)
    register_masking = models.BooleanField(default=False, db_index=True)
    # Registrant
    register_registrant_name = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    register_registrant_organisation = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    register_registrant_address = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_registrant_postcode = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_registrant_city = models.CharField(max_length=255, null=True, blank=True)
    register_registrant_state = models.CharField(max_length=255, null=True, blank=True)
    register_registrant_country = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_registrant_phone = models.CharField(max_length=255, null=True, blank=True)
    register_registrant_fax = models.CharField(max_length=255, null=True, blank=True)
    register_registrant_email = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    # Admin
    register_admin_name = models.CharField(max_length=255, null=True, blank=True)
    register_admin_organisation = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_admin_address = models.CharField(max_length=255, null=True, blank=True)
    register_admin_postcode = models.CharField(max_length=255, null=True, blank=True)
    register_admin_city = models.CharField(max_length=255, null=True, blank=True)
    register_admin_state = models.CharField(max_length=255, null=True, blank=True)
    register_admin_country = models.CharField(max_length=255, null=True, blank=True)
    register_admin_phone = models.CharField(max_length=255, null=True, blank=True)
    register_admin_fax = models.CharField(max_length=255, null=True, blank=True)
    register_admin_email = models.CharField(max_length=255, null=True, blank=True)
    # Technical
    register_technical_name = models.CharField(max_length=255, null=True, blank=True)
    register_technical_organisation = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_technical_address = models.CharField(max_length=255, null=True, blank=True)
    register_technical_postcode = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_technical_city = models.CharField(max_length=255, null=True, blank=True)
    register_technical_state = models.CharField(max_length=255, null=True, blank=True)
    register_technical_country = models.CharField(max_length=255, null=True, blank=True)
    register_technical_phone = models.CharField(max_length=255, null=True, blank=True)
    register_technical_fax = models.CharField(max_length=255, null=True, blank=True)
    register_technical_email = models.CharField(max_length=255, null=True, blank=True)
    # Other
    register_portfolio_sections = models.CharField(
        max_length=255, null=True, blank=True
    )
    register_account_name = models.CharField(max_length=255, null=True, blank=True)
    register_nameservers = models.ManyToManyField(
        "dns_ips.DNSNameserver", blank=True, related_name="register_nameservers"
    )
    dns_nameservers = models.ManyToManyField(
        "dns_ips.DNSNameserver", blank=True, related_name="dns_nameservers"
    )
    register_tld_region = models.CharField(max_length=255, null=True, blank=True)
    register_tld_country = models.CharField(max_length=255, null=True, blank=True)
    register_email = models.CharField(max_length=255, null=True, blank=True)
    register_puny_code = models.CharField(max_length=255, null=True, blank=True)
    register_comment = models.TextField(null=True, blank=True)
    register_registrar = models.CharField(max_length=255, null=True, blank=True)
    register_cost_center = models.CharField(max_length=255, null=True, blank=True)
    register_website = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

    def slack_display(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "DNS Domain"
        verbose_name_plural = "DNS Domains"


class DNSRecord(models.Model):
    source = models.ForeignKey(
        "Source",
        related_name="dnsrecord_source",
        on_delete=models.CASCADE,
        default=default_source_unknown,
    )
    active = models.BooleanField(default=True, db_index=True)
    last_seen = models.DateTimeField(
        default=timezone.now, editable=False, null=True, blank=True, db_index=True
    )

    name = models.CharField(max_length=255, db_index=True, null=True)
    domain = models.ForeignKey(
        "dns_ips.DNSDomain", null=True, blank=True, on_delete=models.CASCADE
    )

    tla = models.ForeignKey(
        "inventory.Application",
        blank=True,
        null=True,
        related_name="dns",
        on_delete=models.SET_NULL,
        verbose_name="Application",
    )

    tags = models.ManyToManyField("dns_ips.Tag", blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.name)

    def slack_display(self):
        # FIXME: is this really required? get from DNSRecordValues now that rtype and value moved to different model=
        # return f'{self.name} IN {self.rtype} "{self.value}"'
        return self.name

    class Meta:
        verbose_name = "DNS Record"


class DNSRecordValue(models.Model):
    class RecordType(models.TextChoices):
        A = "A"
        CNAME = "CNAME"
        TXT = "TXT"
        SPF = "SPF"
        MX = "MX"
        DKIM = "DKIM"
        DMARC = "DMARC"
        SRV = "SRV"
        SOA = "SOA"
        PTR = "PTR"
        NS = "NS"
        AAAA = "AAAA"
        APEXALIAS = "APEXALIAS"
        LB = "LB"
        CAA = "CAA"

    record = models.ForeignKey(DNSRecord, on_delete=models.CASCADE)
    rtype = models.CharField(
        max_length=10,
        choices=RecordType.choices,
        verbose_name="Record Type",
        db_index=True,
    )
    ttl = models.IntegerField(null=True, default=None, verbose_name="TTL")
    # Value is used for cname,txt,spf,mx only
    value = models.TextField(null=True, blank=True)
    ips = models.ManyToManyField(
        "dns_ips.IPAddress",
        blank=True,
        verbose_name="IPs",
        related_name="dnsrecordvalue_ips",
    )

    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=["active", "last_seen"]),
        ]
        verbose_name = "DNS Record Value"

    def __str__(self):
        return f"{self.pk} {self.record.name} {self.rtype}"
