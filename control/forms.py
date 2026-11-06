from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Cita,
    Diagnostico,
    Especialidad,
    Odontologo,
    Paciente,
    Receta,
    Sillon,
    Tratamiento,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "h-4 w-4 rounded border-slate-300 text-cyan-700"
            else:
                css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-input"
            field.widget.attrs["class"] = (
                f"{field.widget.attrs.get('class', '')} {css_class} "
                "transition-all duration-300 hover:scale-[1.01] "
                "focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500".strip()
            )


class ClinicAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        label="Recordarme",
    )

    username = forms.CharField(
        label="Usuario o correo",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "Tu usuario o correo",
                "class": "login-input",
            }
        ),
    )

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Ingresa tu contraseña",
                "class": "login-input",
            }
        ),
    )

    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        if "@" in identifier:
            user_model = get_user_model()
            username_field = user_model.USERNAME_FIELD
            email_matches = list(
                user_model._default_manager.filter(email__iexact=identifier)
                .values_list(username_field, flat=True)[:2]
            )
            if len(email_matches) == 1:
                self.cleaned_data["username"] = email_matches[0]
        return super().clean()


class PacienteForm(StyledModelForm):
    class Meta:
        model = Paciente
        fields = (
            "nombres",
            "apellidos",
            "dni",
            "fecha_nacimiento",
            "telefono",
            "direccion",
            "correo",
        )
        widgets = {
            "nombres": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "apellidos": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "dni": forms.TextInput(
                attrs={
                    "inputmode": "numeric",
                    "maxlength": "8",
                    "autocomplete": "off",
                }
            ),
            "fecha_nacimiento": forms.DateInput(
                attrs={"type": "date", "autocomplete": "bday"}
            ),
            "telefono": forms.TextInput(attrs={"autocomplete": "tel"}),
            "direccion": forms.TextInput(
                attrs={"autocomplete": "street-address"}
            ),
            "correo": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_dni(self):
        dni = self.cleaned_data["dni"].strip()
        if len(dni) != 8 or not dni.isascii() or not dni.isdigit():
            raise ValidationError("El DNI debe contener exactamente 8 dígitos.")
        return dni

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data["fecha_nacimiento"]
        if fecha_nacimiento > timezone.localdate():
            raise ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha_nacimiento


class EspecialidadForm(StyledModelForm):
    class Meta:
        model = Especialidad
        fields = ("nombre", "descripcion", "estado")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class OdontologoForm(StyledModelForm):
    class Meta:
        model = Odontologo
        fields = (
            "nombres",
            "apellidos",
            "numero_colegiatura",
            "telefono",
            "correo",
            "especialidad",
            "estado",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["especialidad"].queryset = Especialidad.objects.filter(
            estado=Especialidad.Estado.ACTIVA
        ).order_by("nombre")


class SillonForm(StyledModelForm):
    class Meta:
        model = Sillon
        fields = ("nombre", "activo")


class CitaForm(StyledModelForm):
    class Meta:
        model = Cita
        fields = (
            "paciente",
            "odontologo",
            "sillon",
            "fecha",
            "hora",
            "motivo",
            "estado",
            "observaciones",
        )
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "hora": forms.TimeInput(attrs={"type": "time"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paciente"].queryset = Paciente.objects.order_by("apellidos", "nombres")
        odontologos = Odontologo.objects.filter(estado=Odontologo.Estado.ACTIVO)
        sillones = Sillon.objects.filter(activo=True)
        if self.instance.pk:
            odontologos = odontologos | Odontologo.objects.filter(
                pk=self.instance.odontologo_id
            )
            if self.instance.sillon_id:
                sillones = sillones | Sillon.objects.filter(pk=self.instance.sillon_id)
        self.fields["odontologo"].queryset = odontologos.select_related("especialidad")
        self.fields["sillon"].queryset = sillones
        self.fields["sillon"].required = False


class DiagnosticoForm(StyledModelForm):
    class Meta:
        model = Diagnostico
        fields = ("cita", "descripcion", "recomendaciones", "fecha")
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "recomendaciones": forms.Textarea(attrs={"rows": 3}),
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cita"].queryset = Cita.objects.select_related(
            "paciente", "odontologo"
        ).order_by("-fecha", "-hora")


class TratamientoForm(StyledModelForm):
    class Meta:
        model = Tratamiento
        fields = (
            "diagnostico",
            "nombre",
            "descripcion",
            "fecha_inicio",
            "fecha_fin",
            "costo",
            "estado",
        )
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
            "costo": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def clean_costo(self):
        costo = self.cleaned_data["costo"]
        if costo < 0:
            raise ValidationError("El costo no puede ser negativo.")
        return costo

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_inicio")
        fin = cleaned_data.get("fecha_fin")
        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin", "La fecha final no puede ser anterior a la inicial.")
        return cleaned_data


class RecetaForm(StyledModelForm):
    class Meta:
        model = Receta
        fields = (
            "diagnostico",
            "medicamento",
            "dosis",
            "frecuencia",
            "duracion",
            "indicaciones",
            "fecha_emision",
        )
        widgets = {
            "indicaciones": forms.Textarea(attrs={"rows": 3}),
            "fecha_emision": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["diagnostico"].queryset = Diagnostico.objects.select_related(
            "cita", "cita__paciente"
        ).order_by("-fecha")


class CitaAgendaFilterForm(forms.Form):
    fecha = forms.DateField(
        required=False,
        label="Fecha",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}),
    )
    estado = forms.ChoiceField(
        required=False,
        label="Estado",
        choices=[("", "Todos")] + list(Cita.Estado.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sillon = forms.ModelChoiceField(
        required=False,
        label="Sillón",
        queryset=Sillon.objects.filter(activo=True),
        empty_label="Todos",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
