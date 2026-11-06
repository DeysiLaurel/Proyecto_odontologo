from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import (
    CitaAgendaFilterForm,
    CitaForm,
    ClinicAuthenticationForm,
    DiagnosticoForm,
    EspecialidadForm,
    OdontologoForm,
    PacienteForm,
    RecetaForm,
    SillonForm,
    TratamientoForm,
)
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
from .reporting import REPORTS, ReportFilterForm, get_report_queryset, make_report_pdf


def login_view(request):
    if request.user.is_authenticated:
        return redirect("control:dashboard")

    next_url = request.POST.get("next") or request.GET.get("next", "")
    form = ClinicAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if form.cleaned_data["remember_me"]:
            request.session.set_expiry(60 * 60 * 24 * 14)
        else:
            request.session.set_expiry(0)

        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("control:dashboard")

    return render(
        request,
        "control/login.html",
        {"form": form, "next": next_url},
    )


def _column_value(instance, path):
    value = instance
    for part in path.split("."):
        value = getattr(value, part)
        if callable(value):
            value = value()
    return value


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "control/dashboard.html"
    login_url = reverse_lazy("control:login")
    redirect_field_name = "next"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        context.update(
            total_pacientes=Paciente.objects.count(),
            citas_hoy=Cita.objects.filter(fecha=hoy).exclude(
                estado=Cita.Estado.CANCELADA
            ).count(),
            tratamientos_activos=Tratamiento.objects.filter(
                estado__in=(
                    Tratamiento.Estado.PENDIENTE,
                    Tratamiento.Estado.EN_PROCESO,
                )
            ).count(),
            total_diagnosticos=Diagnostico.objects.count(),
            proximas_citas=Cita.objects.filter(fecha__gte=hoy)
            .exclude(estado=Cita.Estado.CANCELADA)
            .select_related("paciente", "odontologo", "sillon")
            .order_by("fecha", "hora")[:8],
        )
        return context


class PacienteListView(ListView):
    model = Paciente
    template_name = "control/pacientes.html"
    context_object_name = "pacientes"
    paginate_by = 10
    ordering = ("apellidos", "nombres")

    def get_queryset(self):
        queryset = Paciente.objects.all().order_by(*self.ordering)
        self.search_query = self.request.GET.get("q", "").strip()
        if self.search_query:
            queryset = queryset.filter(
                Q(nombres__icontains=self.search_query)
                | Q(apellidos__icontains=self.search_query)
                | Q(dni__icontains=self.search_query)
                | Q(correo__icontains=self.search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.search_query
        return context


class PacienteCreateView(CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "control/paciente_form.html"
    success_url = reverse_lazy("control:paciente_list")

    def form_valid(self, form):
        messages.success(self.request, "El paciente se registró correctamente.")
        return super().form_valid(form)


class PacienteUpdateView(UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "control/paciente_form.html"
    success_url = reverse_lazy("control:paciente_list")

    def form_valid(self, form):
        messages.success(self.request, "Los datos del paciente se actualizaron correctamente.")
        return super().form_valid(form)


class PacienteDeleteView(DeleteView):
    model = Paciente
    template_name = "control/paciente_confirm_delete.html"
    success_url = reverse_lazy("control:paciente_list")

    def form_valid(self, form):
        messages.success(self.request, "El paciente se eliminó correctamente.")
        return super().form_valid(form)


class EntityListView(ListView):
    template_name = "control/crud_list.html"
    context_object_name = "objects"
    paginate_by = 12
    ordering = ("pk",)
    columns = ()
    search_fields = ()
    related_fields = ()
    entity_name = ""
    route_prefix = ""
    entity_labels = {
        "Especialidad": ("Especialidades", "Nueva especialidad"),
        "Odontólogo": ("Odontólogos", "Nuevo odontólogo"),
        "Sillón clínico": ("Sillones clínicos", "Nuevo sillón"),
        "Cita": ("Citas", "Nueva cita"),
        "Diagnóstico": ("Diagnósticos", "Nuevo diagnóstico"),
        "Tratamiento": ("Tratamientos", "Nuevo tratamiento"),
        "Receta": ("Recetas", "Nueva receta"),
    }

    def get_queryset(self):
        queryset = self.model.objects.all().order_by(*self.ordering)
        if self.related_fields:
            queryset = queryset.select_related(*self.related_fields)
        self.search_query = self.request.GET.get("q", "").strip()
        if self.search_query and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": self.search_query})
            queryset = queryset.filter(query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = context["page_obj"]
        rows = []
        for obj in page.object_list:
            values = [_column_value(obj, field) for _, field in self.columns]
            rows.append(
                {
                    "values": values,
                    "edit_url": reverse(
                        f"control:{self.route_prefix}_update", kwargs={"pk": obj.pk}
                    ),
                    "delete_url": reverse(
                        f"control:{self.route_prefix}_delete", kwargs={"pk": obj.pk}
                    ),
                }
            )
        context.update(
            entity_name=self.entity_name,
            entity_name_plural=self.entity_labels[self.entity_name][0],
            columns=[label for label, _ in self.columns],
            rows=rows,
            search_query=self.search_query,
            create_url=reverse(f"control:{self.route_prefix}_create"),
            create_label=self.entity_labels[self.entity_name][1],
        )
        return context


class EntityCreateView(CreateView):
    template_name = "control/crud_form.html"
    entity_name = ""
    route_prefix = ""

    def get_success_url(self):
        return reverse_lazy(f"control:{self.route_prefix}_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            entity_name=self.entity_name,
            page_title=f"Registrar {self.entity_name.lower()}",
            cancel_url=reverse(f"control:{self.route_prefix}_list"),
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, f"{self.entity_name} registrado correctamente.")
        return super().form_valid(form)


class EntityUpdateView(UpdateView):
    template_name = "control/crud_form.html"
    entity_name = ""
    route_prefix = ""

    def get_success_url(self):
        return reverse_lazy(f"control:{self.route_prefix}_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            entity_name=self.entity_name,
            page_title=f"Editar {self.entity_name.lower()}",
            cancel_url=reverse(f"control:{self.route_prefix}_list"),
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, f"{self.entity_name} actualizado correctamente.")
        return super().form_valid(form)


class EntityDeleteView(DeleteView):
    template_name = "control/crud_confirm_delete.html"
    entity_name = ""
    route_prefix = ""

    def get_success_url(self):
        return reverse_lazy(f"control:{self.route_prefix}_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            entity_name=self.entity_name,
            cancel_url=reverse(f"control:{self.route_prefix}_list"),
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, f"{self.entity_name} eliminado correctamente.")
        return super().form_valid(form)


class EspecialidadListView(EntityListView):
    model = Especialidad
    entity_name = "Especialidad"
    route_prefix = "especialidad"
    columns = (("Nombre", "nombre"), ("Estado", "get_estado_display"))
    search_fields = ("nombre", "descripcion")


class EspecialidadCreateView(EntityCreateView):
    model = Especialidad
    form_class = EspecialidadForm
    entity_name = "Especialidad"
    route_prefix = "especialidad"


class EspecialidadUpdateView(EntityUpdateView):
    model = Especialidad
    form_class = EspecialidadForm
    entity_name = "Especialidad"
    route_prefix = "especialidad"


class EspecialidadDeleteView(EntityDeleteView):
    model = Especialidad
    entity_name = "Especialidad"
    route_prefix = "especialidad"


class OdontologoListView(EntityListView):
    model = Odontologo
    entity_name = "Odontólogo"
    route_prefix = "odontologo"
    columns = (
        ("Nombres", "nombres"),
        ("Apellidos", "apellidos"),
        ("Colegiatura", "numero_colegiatura"),
        ("Especialidad", "especialidad"),
        ("Estado", "get_estado_display"),
    )
    search_fields = ("nombres", "apellidos", "numero_colegiatura", "correo")
    related_fields = ("especialidad",)


class OdontologoCreateView(EntityCreateView):
    model = Odontologo
    form_class = OdontologoForm
    entity_name = "Odontólogo"
    route_prefix = "odontologo"


class OdontologoUpdateView(EntityUpdateView):
    model = Odontologo
    form_class = OdontologoForm
    entity_name = "Odontólogo"
    route_prefix = "odontologo"


class OdontologoDeleteView(EntityDeleteView):
    model = Odontologo
    entity_name = "Odontólogo"
    route_prefix = "odontologo"


class SillonListView(EntityListView):
    model = Sillon
    entity_name = "Sillón clínico"
    route_prefix = "sillon"
    columns = (("Nombre", "nombre"), ("Estado", "get_activo_display"))
    search_fields = ("nombre",)


class SillonCreateView(EntityCreateView):
    model = Sillon
    form_class = SillonForm
    entity_name = "Sillón clínico"
    route_prefix = "sillon"


class SillonUpdateView(EntityUpdateView):
    model = Sillon
    form_class = SillonForm
    entity_name = "Sillón clínico"
    route_prefix = "sillon"


class SillonDeleteView(EntityDeleteView):
    model = Sillon
    entity_name = "Sillón clínico"
    route_prefix = "sillon"


class CitaListView(EntityListView):
    model = Cita
    entity_name = "Cita"
    route_prefix = "cita"
    columns = (
        ("Fecha", "fecha"),
        ("Hora", "hora"),
        ("Paciente", "paciente"),
        ("Odontólogo", "odontologo"),
        ("Sillón", "sillon"),
        ("Estado", "get_estado_display"),
    )
    search_fields = ("paciente__nombres", "paciente__apellidos", "motivo")
    related_fields = ("paciente", "odontologo", "sillon")

    def get_queryset(self):
        queryset = super().get_queryset()
        self.agenda_filter_form = CitaAgendaFilterForm(self.request.GET or None)
        if self.agenda_filter_form.is_bound:
            if not self.agenda_filter_form.is_valid():
                return queryset.none()
            filters = self.agenda_filter_form.cleaned_data
            if filters["fecha"]:
                queryset = queryset.filter(fecha=filters["fecha"])
            if filters["estado"]:
                queryset = queryset.filter(estado=filters["estado"])
            if filters["sillon"]:
                queryset = queryset.filter(sillon=filters["sillon"])
        return queryset.order_by("-fecha", "-hora")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            agenda_filter_form=self.agenda_filter_form,
        )
        return context


class CitaCreateView(EntityCreateView):
    model = Cita
    form_class = CitaForm
    entity_name = "Cita"
    route_prefix = "cita"


class CitaUpdateView(EntityUpdateView):
    model = Cita
    form_class = CitaForm
    entity_name = "Cita"
    route_prefix = "cita"


class CitaDeleteView(EntityDeleteView):
    model = Cita
    entity_name = "Cita"
    route_prefix = "cita"


class DiagnosticoListView(EntityListView):
    model = Diagnostico
    entity_name = "Diagnóstico"
    route_prefix = "diagnostico"
    columns = (
        ("Fecha", "fecha"),
        ("Paciente", "cita.paciente"),
        ("Cita", "cita"),
        ("Descripción", "descripcion"),
    )
    search_fields = ("descripcion", "cita__paciente__nombres", "cita__paciente__apellidos")
    related_fields = ("cita", "cita__paciente")


class DiagnosticoCreateView(EntityCreateView):
    model = Diagnostico
    form_class = DiagnosticoForm
    entity_name = "Diagnóstico"
    route_prefix = "diagnostico"


class DiagnosticoUpdateView(EntityUpdateView):
    model = Diagnostico
    form_class = DiagnosticoForm
    entity_name = "Diagnóstico"
    route_prefix = "diagnostico"


class DiagnosticoDeleteView(EntityDeleteView):
    model = Diagnostico
    entity_name = "Diagnóstico"
    route_prefix = "diagnostico"


class TratamientoListView(EntityListView):
    model = Tratamiento
    entity_name = "Tratamiento"
    route_prefix = "tratamiento"
    columns = (
        ("Nombre", "nombre"),
        ("Paciente", "diagnostico.cita.paciente"),
        ("Costo", "costo"),
        ("Estado", "get_estado_display"),
    )
    search_fields = ("nombre", "descripcion", "diagnostico__cita__paciente__nombres")
    related_fields = ("diagnostico", "diagnostico__cita", "diagnostico__cita__paciente")


class TratamientoCreateView(EntityCreateView):
    model = Tratamiento
    form_class = TratamientoForm
    entity_name = "Tratamiento"
    route_prefix = "tratamiento"


class TratamientoUpdateView(EntityUpdateView):
    model = Tratamiento
    form_class = TratamientoForm
    entity_name = "Tratamiento"
    route_prefix = "tratamiento"


class TratamientoDeleteView(EntityDeleteView):
    model = Tratamiento
    entity_name = "Tratamiento"
    route_prefix = "tratamiento"


class RecetaListView(EntityListView):
    model = Receta
    entity_name = "Receta"
    route_prefix = "receta"
    columns = (
        ("Fecha", "fecha_emision"),
        ("Paciente", "diagnostico.cita.paciente"),
        ("Medicamento", "medicamento"),
        ("Dosis", "dosis"),
    )
    search_fields = (
        "medicamento",
        "diagnostico__cita__paciente__nombres",
        "diagnostico__cita__paciente__apellidos",
    )
    related_fields = ("diagnostico", "diagnostico__cita", "diagnostico__cita__paciente")


class RecetaCreateView(EntityCreateView):
    model = Receta
    form_class = RecetaForm
    entity_name = "Receta"
    route_prefix = "receta"


class RecetaUpdateView(EntityUpdateView):
    model = Receta
    form_class = RecetaForm
    entity_name = "Receta"
    route_prefix = "receta"


class RecetaDeleteView(EntityDeleteView):
    model = Receta
    entity_name = "Receta"
    route_prefix = "receta"


class ReportListView(TemplateView):
    template_name = "control/report_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_type = self.kwargs["report_type"]
        report = REPORTS[report_type]
        filter_form = ReportFilterForm(self.request.GET or None, report_type=report_type)
        queryset = get_report_queryset(report_type, filter_form)
        rows = [
            {
                "values": [_column_value(obj, field) for _, field in report["columns"]],
            }
            for obj in queryset[:500]
        ] if filter_form.is_valid() or not self.request.GET else []
        context.update(
            report_type=report_type,
            report_title=report["title"],
            columns=[label for label, _ in report["columns"]],
            rows=rows,
            filter_form=filter_form,
            pdf_url=reverse(f"control:reporte_{report_type}"),
        )
        return context


class ReportIndexView(TemplateView):
    template_name = "control/report_index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = [
            {
                "title": config["title"],
                "url": reverse(f"control:reporte_{report_type}"),
                "description": {
                    "citas": "Agenda, paciente, profesional, sillón y estado.",
                    "diagnosticos": "Hallazgos y recomendaciones clínicas.",
                    "tratamientos": "Procedimientos, fechas, costos y estado.",
                    "recetas": "Medicamentos, dosis e indicaciones prescritas.",
                }[report_type],
            }
            for report_type, config in REPORTS.items()
        ]
        return context


class ReportPdfView(TemplateView):
    def get(self, request, report_type):
        filter_form = ReportFilterForm(request.GET or None, report_type=report_type)
        if request.GET and not filter_form.is_valid():
            return render(
                request,
                "control/report_list.html",
                {
                    "report_type": report_type,
                    "report_title": REPORTS[report_type]["title"],
                    "columns": [label for label, _ in REPORTS[report_type]["columns"]],
                    "rows": [],
                    "filter_form": filter_form,
                    "pdf_url": reverse(f"control:reporte_{report_type}"),
                },
                status=400,
            )
        queryset = get_report_queryset(report_type, filter_form)[:5000]
        pdf = make_report_pdf(report_type, queryset)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="reporte-{report_type}-{date.today().isoformat()}.pdf"'
        )
        return response
