# Generated by Django 4.2.16 on 2024-12-04 12:00

import django_migration_linter as linter
from django.db import migrations

import common.migrations.remove_field


class Migration(migrations.Migration):
    dependencies = [
        ("slack", "0009_drop_orphaned_messages_and_fill_in_missing_team_identity_values"),
    ]

    operations = [
        linter.IgnoreMigration(),
        common.migrations.remove_field.RemoveFieldDB(
            model_name="SlackMessage",
            name="active_update_task_id",
            remove_state_migration=("slack", "0008_remove_slackmessage_active_update_task_id_state"),
        ),
    ]