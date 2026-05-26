from django.db import migrations


def seed_cooperadora_27(apps, schema_editor):
    Cooperadora = apps.get_model('core', 'Cooperadora')
    Cooperadora.objects.get_or_create(
        numero_escuela=27,
        defaults={
            'nombre': 'Escuela N°27',
            'slug': 'escuela27',
            'dao_address': '0x77c6740a2031fa0684ea88edc9c6019fa0e7bd2b',
            'subscription_status': 'TRIAL',
        }
    )


def undo_seed(apps, schema_editor):
    Cooperadora = apps.get_model('core', 'Cooperadora')
    Cooperadora.objects.filter(numero_escuela=27).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_cooperadora_alter_configuracionanual_anio_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_cooperadora_27, undo_seed),
    ]
