from django.db import models


class Diagnostico(models.Model):
    id = models.BigAutoField(primary_key=True)
    cita = models.ForeignKey(
        "control.Cita",
        on_delete=models.CASCADE,
        related_name="diagnosticos",
    )
    descripcion = models.TextField()
    recomendaciones = models.TextField(blank=True)
    fecha = models.DateField()

    class Meta:
        db_table = "control_diagnostico"
        verbose_name = "diagnóstico"
        verbose_name_plural = "diagnósticos"

    def __str__(self):
        return f"Diagnóstico #{self.pk} - {self.fecha}"
