# Generated by Django 4.2.5 on 2023-10-07 18:20

import django.contrib.auth.password_validation
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backend", "0003_rename_shops_category_shop_category_id_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="client",
            name="password",
            field=models.CharField(
                blank=True,
                max_length=100,
                validators=[
                    django.contrib.auth.password_validation.MinimumLengthValidator,
                    django.contrib.auth.password_validation.UserAttributeSimilarityValidator,
                    django.contrib.auth.password_validation.CommonPasswordValidator,
                    django.contrib.auth.password_validation.NumericPasswordValidator,
                ],
                verbose_name="password",
            ),
        ),
    ]