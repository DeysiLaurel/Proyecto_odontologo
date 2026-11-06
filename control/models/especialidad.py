from django.db import models


class Especialidad(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        INACTIVA = "inactiva", "Inactiva"

    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVA,
    )

    class Meta:
        db_table = "control_especialidad"
        verbose_name = "especialidad"
        verbose_name_plural = "especialidades"

    def __str__(self):
        return self.nombre
