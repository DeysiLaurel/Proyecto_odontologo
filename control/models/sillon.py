from django.db import models


class Sillon(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "control_sillon"
        ordering = ("nombre",)
        verbose_name = "sillón clínico"
        verbose_name_plural = "sillones clínicos"

    def __str__(self):
        return self.nombre

    def get_activo_display(self):
        return "Activo" if self.activo else "Inactivo"
