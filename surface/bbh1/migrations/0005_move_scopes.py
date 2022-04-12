# Generated by Django 3.2.12 on 2022-04-12 10:12

from django.db import migrations


def datafix(app, schema):
    S = app.get_model('bbh1', 'Scope')
    NS = app.get_model('bbh1', 'TEMPScope')
    for s in S.objects.all():
        NS.objects.create(
            tla=f'BBH1_{s.name.upper()}',
            name=s.name,
            description=s.description,
            link=s.link,
            monitor=s.monitor,
            torify=s.torify,
            disabled=s.disabled,
            big_scope=s.big_scope,
            scope_domains_in=s.scope_domains_in,
            scope_domains_out=s.scope_domains_out,
            ignore_domains=s.ignore_domains,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('bbh1', '0004_historicaltempscope_tempscope'),
    ]

    operations = [
        migrations.RunPython(datafix, reverse_code=migrations.RunPython.noop)
    ]
