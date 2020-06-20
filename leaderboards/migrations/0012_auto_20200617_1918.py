# Generated by Django 3.0.7 on 2020-06-17 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leaderboards', '0011_leaderboard_score_set'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='invite',
            constraint=models.UniqueConstraint(fields=('leaderboard_id', 'user_id'), name='unique_invites'),
        ),
    ]