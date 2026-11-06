from django.db import models


class Odontologo(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    id = models.BigAutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    numero_colegiatura = models.CharField(max_length=30, unique=True)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField()
    especialidad = models.ForeignKey(
        "control.Especialidad",
        on_delete=models.CASCADE,
        related_name="odontologos",
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )

    class Meta:
        db_table = "control_odontologo"
        verbose_name = "odontólogo"
        verbose_name_plural = "odontólogos"

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
