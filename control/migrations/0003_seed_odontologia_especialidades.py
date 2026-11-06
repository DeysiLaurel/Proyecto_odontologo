from django.db import migrations


ESPECIALIDADES = (
    ("Ortodoncia y Ortopedia Maxilar", "Corrección de la posición dental y maxilar."),
    ("Endodoncia", "Diagnóstico y tratamiento de enfermedades de la pulpa dental."),
    ("Periodoncia", "Prevención y tratamiento de enfermedades de las encías y tejidos de soporte."),
    ("Rehabilitación Oral", "Restauración de la función y estética del sistema oral."),
    ("Cirugía Maxilofacial", "Tratamiento quirúrgico de afecciones maxilofaciales."),
    ("Odontopediatría", "Atención odontológica integral de niñas, niños y adolescentes."),
    ("Estética Dental", "Procedimientos odontológicos orientados a la armonía de la sonrisa."),
)


def crear_especialidades(apps, schema_editor):
    Especialidad = apps.get_model("control", "Especialidad")
    database = schema_editor.connection.alias
    for nombre, descripcion in ESPECIALIDADES:
        Especialidad.objects.using(database).get_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion, "estado": "activa"},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("control", "0002_sillon_cita_sillon"),
    ]

    operations = [
        migrations.RunPython(crear_especialidades, migrations.RunPython.noop),
    ]
