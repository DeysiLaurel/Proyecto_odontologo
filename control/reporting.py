from datetime import date
from html import escape
from io import BytesIO

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Cita, Diagnostico, Receta, Tratamiento


REPORTS = {
    "citas": {
        "title": "Reporte de citas",
        "model": Cita,
        "date_field": "fecha",
        "related": ("paciente", "odontologo", "sillon"),
        "columns": (
            ("Fecha", "fecha"),
            ("Hora", "hora"),
            ("Paciente", "paciente"),
            ("Odontólogo", "odontologo"),
            ("Sillón", "sillon"),
            ("Estado", "get_estado_display"),
            ("Motivo", "motivo"),
        ),
    },
    "diagnosticos": {
        "title": "Reporte de diagnósticos",
        "model": Diagnostico,
        "date_field": "fecha",
        "related": ("cita", "cita__paciente", "cita__odontologo"),
        "columns": (
            ("Fecha", "fecha"),
            ("Paciente", "cita.paciente"),
            ("Odontólogo", "cita.odontologo"),
            ("Descripción", "descripcion"),
            ("Recomendaciones", "recomendaciones"),
        ),
    },
    "tratamientos": {
        "title": "Reporte de tratamientos",
        "model": Tratamiento,
        "date_field": "fecha_inicio",
        "related": ("diagnostico", "diagnostico__cita", "diagnostico__cita__paciente"),
        "columns": (
            ("Inicio", "fecha_inicio"),
            ("Fin", "fecha_fin"),
            ("Paciente", "diagnostico.cita.paciente"),
            ("Tratamiento", "nombre"),
            ("Costo", "costo"),
            ("Estado", "get_estado_display"),
        ),
    },
    "recetas": {
        "title": "Reporte de recetas",
        "model": Receta,
        "date_field": "fecha_emision",
        "related": ("diagnostico", "diagnostico__cita", "diagnostico__cita__paciente"),
        "columns": (
            ("Emisión", "fecha_emision"),
            ("Paciente", "diagnostico.cita.paciente"),
            ("Medicamento", "medicamento"),
            ("Dosis", "dosis"),
            ("Frecuencia", "frecuencia"),
            ("Duración", "duracion"),
        ),
    },
}


class ReportFilterForm(forms.Form):
    fecha_desde = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )

    def __init__(self, *args, report_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.report_type = report_type
        if report_type == "citas":
            self.fields["estado"] = forms.ChoiceField(
                required=False,
                label="Estado",
                choices=[("", "Todos")] + list(Cita.Estado.choices),
                widget=forms.Select(attrs={"class": "form-select"}),
            )

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_desde")
        fin = cleaned_data.get("fecha_hasta")
        if inicio and fin and fin < inicio:
            raise ValidationError("La fecha final debe ser igual o posterior a la inicial.")
        return cleaned_data


def get_report_queryset(report_type, filter_form):
    config = REPORTS[report_type]
    queryset = config["model"].objects.all().select_related(*config["related"])
    if not filter_form.is_bound:
        return queryset.order_by(f"-{config['date_field']}")
    if not filter_form.is_valid():
        return queryset.none()
    filters = filter_form.cleaned_data
    date_field = config["date_field"]
    if filters.get("fecha_desde"):
        queryset = queryset.filter(**{f"{date_field}__gte": filters["fecha_desde"]})
    if filters.get("fecha_hasta"):
        queryset = queryset.filter(**{f"{date_field}__lte": filters["fecha_hasta"]})
    if report_type == "citas" and filters.get("estado"):
        queryset = queryset.filter(estado=filters["estado"])
    return queryset.order_by(f"-{date_field}")


def _column_value(instance, path):
    value = instance
    for part in path.split("."):
        value = getattr(value, part)
        if callable(value):
            value = value()
    if value is None:
        return "—"
    if isinstance(value, date):
        return timezone.template_localtime(value).strftime("%d/%m/%Y")
    return str(value)


def make_report_pdf(report_type, queryset):
    config = REPORTS[report_type]
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=config["title"],
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Sonrisa Perfecta", styles["Title"]),
        Paragraph(config["title"], styles["Heading2"]),
        Paragraph(f"Generado: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]),
        Spacer(1, 0.2 * inch),
    ]
    headers = [label for label, _ in config["columns"]]
    table_data = [[Paragraph(escape(str(label)), styles["BodyText"]) for label in headers]]
    for obj in queryset:
        table_data.append(
            [
                Paragraph(escape(_column_value(obj, field)), styles["BodyText"])
                for _, field in config["columns"]
            ]
        )
    if len(table_data) == 1:
        table_data.append([Paragraph("Sin registros para los filtros seleccionados.", styles["BodyText"])] + [""] * (len(headers) - 1))
    table = Table(table_data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#155e75")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(table)
    document.build(elements)
    return buffer.getvalue()
