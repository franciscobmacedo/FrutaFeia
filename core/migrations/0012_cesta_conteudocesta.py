# Generated by Django 3.2.2 on 2021-06-22 16:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_produtor_estado'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConteudoCesta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade_pequena', models.FloatField(blank=True, null=True)),
                ('quantidade_grande', models.FloatField()),
                ('medida', models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Unidade'), (2, 'Kg')], null=True)),
                ('preco_unitario', models.FloatField()),
                ('produto_extra', models.BooleanField()),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.produto')),
                ('produtor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.produtor')),
            ],
        ),
        migrations.CreateModel(
            name='Cesta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField()),
                ('preco_pequena', models.FloatField()),
                ('peso_pequena', models.FloatField()),
                ('preco_grande', models.FloatField()),
                ('peso_grande', models.FloatField()),
                ('conteudo', models.ManyToManyField(to='core.ConteudoCesta')),
            ],
        ),
    ]
