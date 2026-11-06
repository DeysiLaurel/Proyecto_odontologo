from django.db import models


class Receta(models.Model):
    id = models.BigAutoField(primary_key=True)
    diagnostico = models.ForeignKey(
        "control.Diagnostico",
        on_delete=models.CASCADE,
        related_name="recetas",
    )
    medicamento = models.CharField(max_length=150)
    dosis = models.CharField(max_length=100)
    frecuencia = models.CharField(max_length=100)
    duracion = models.CharField(max_length=100)
    indicaciones = models.TextField(blank=True)
    fecha_emision = models.DateField()

    class Meta:
        db_table = "control_receta"
        verbose_name = "receta"
        verbose_name_plural = "recetas"

    def __str__(self):
        return f"Receta #{self.pk} - {self.medicamento}"
