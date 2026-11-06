from django.db import models


class Cita(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"
        ATENDIDA = "atendida", "Atendida"
        CANCELADA = "cancelada", "Cancelada"

    id = models.BigAutoField(primary_key=True)
    paciente = models.ForeignKey(
        "control.Paciente",
        on_delete=models.CASCADE,
        related_name="citas",
    )
    odontologo = models.ForeignKey(
        "control.Odontologo",
        on_delete=models.CASCADE,
        related_name="citas",
    )
    sillon = models.ForeignKey(
        "control.Sillon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="citas",
    )
    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.CharField(max_length=255)
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "control_cita"
        verbose_name = "cita"
        verbose_name_plural = "citas"

    def __str__(self):
        return f"Cita #{self.pk} - {self.fecha} {self.hora}"
