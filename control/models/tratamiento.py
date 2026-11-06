from django.db import models


class Tratamiento(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        FINALIZADO = "finalizado", "Finalizado"

    id = models.BigAutoField(primary_key=True)
    diagnostico = models.ForeignKey(
        "control.Diagnostico",
        on_delete=models.CASCADE,
        related_name="tratamientos",
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    class Meta:
        db_table = "control_tratamiento"
        verbose_name = "tratamiento"
        verbose_name_plural = "tratamientos"

    def __str__(self):
        return self.nombre
