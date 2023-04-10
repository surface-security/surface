# Generated by Django 3.2.18 on 2023-04-10 15:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0001_initial_20211102'),
    ]

    operations = [
        migrations.CreateModel(
            name='Integration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('actions', models.JSONField()),
                ('enabled', models.BooleanField(default=True)),
            ],
        ),
    ]
