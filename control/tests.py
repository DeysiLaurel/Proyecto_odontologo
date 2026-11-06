from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import OdontologoForm, PacienteForm
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


class PacienteCrudTests(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            nombres="Ana",
            apellidos="Pérez",
            dni="12345678",
            fecha_nacimiento=date(1990, 5, 12),
            telefono="999123456",
            direccion="Av. Principal 123",
            correo="ana@example.com",
        )

    def test_list_searches_by_name_and_dni(self):
        response = self.client.get(reverse("control:paciente_list"), {"q": "12345678"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana")
        self.assertEqual(list(response.context["pacientes"]), [self.paciente])

    def test_create_patient(self):
        response = self.client.post(
            reverse("control:paciente_create"),
            {
                "nombres": "Luis",
                "apellidos": "García",
                "dni": "87654321",
                "fecha_nacimiento": "1988-03-10",
                "telefono": "988765432",
                "direccion": "Calle 2",
                "correo": "luis@example.com",
            },
        )

        self.assertRedirects(response, reverse("control:paciente_list"))
        self.assertTrue(Paciente.objects.filter(dni="87654321").exists())

    def test_update_patient(self):
        response = self.client.post(
            reverse("control:paciente_update", args=[self.paciente.pk]),
            {
                "nombres": "Ana María",
                "apellidos": "Pérez",
                "dni": "12345678",
                "fecha_nacimiento": "1990-05-12",
                "telefono": "999123456",
                "direccion": "Av. Principal 123",
                "correo": "ana@example.com",
            },
        )

        self.assertRedirects(response, reverse("control:paciente_list"))
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.nombres, "Ana María")

    def test_delete_requires_post_confirmation(self):
        response = self.client.get(
            reverse("control:paciente_delete", args=[self.paciente.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Paciente.objects.filter(pk=self.paciente.pk).exists())
        response = self.client.post(
            reverse("control:paciente_delete", args=[self.paciente.pk])
        )
        self.assertRedirects(response, reverse("control:paciente_list"))
        self.assertFalse(Paciente.objects.filter(pk=self.paciente.pk).exists())

    def test_form_rejects_non_numeric_or_wrong_length_dni(self):
        form = PacienteForm(
            data={
                "nombres": "Eva",
                "apellidos": "López",
                "dni": "1234abcd",
                "fecha_nacimiento": (date.today() - timedelta(days=365)).isoformat(),
                "telefono": "900000000",
                "direccion": "Calle 3",
                "correo": "eva@example.com",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("dni", form.errors)

    def test_patient_list_routes_and_home_redirect(self):
        for url in ("/pacientes/", "/clientes/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

        response = self.client.get("/")
        self.assertRedirects(
            response,
            f"{reverse('control:login')}?next=/",
            fetch_redirect_response=False,
        )


class ClinicalModulesTests(TestCase):
    def setUp(self):
        self.especialidad = Especialidad.objects.create(nombre="Ortodoncia")
        self.paciente = Paciente.objects.create(
            nombres="Elena",
            apellidos="Soto",
            dni="12345679",
            fecha_nacimiento=date(1985, 6, 10),
            telefono="900123456",
            direccion="Av. Salud 5",
            correo="elena@example.com",
        )
        self.odontologo = Odontologo.objects.create(
            nombres="Mario",
            apellidos="Reyes",
            numero_colegiatura="COL-001",
            telefono="900111222",
            correo="mario@example.com",
            especialidad=self.especialidad,
        )
        self.sillon = Sillon.objects.create(nombre="Sillón 1")
        self.cita = Cita.objects.create(
            paciente=self.paciente,
            odontologo=self.odontologo,
            sillon=self.sillon,
            fecha=date.today(),
            hora="10:00",
            motivo="Evaluación",
        )
        self.diagnostico = Diagnostico.objects.create(
            cita=self.cita,
            descripcion="Revisión inicial",
            fecha=date.today(),
        )
        self.tratamiento = Tratamiento.objects.create(
            diagnostico=self.diagnostico,
            nombre="Limpieza",
            descripcion="Limpieza dental",
            fecha_inicio=date.today(),
            costo="85.00",
        )
        self.receta = Receta.objects.create(
            diagnostico=self.diagnostico,
            medicamento="Analgésico",
            dosis="500 mg",
            frecuencia="Cada 8 horas",
            duracion="3 días",
            fecha_emision=date.today(),
        )

    def test_dashboard_and_module_lists_render(self):
        self.client.force_login(
            get_user_model().objects.create_user(
                username="test-clinician",
                password="SecurePass123!",
            )
        )
        route_names = (
            "control:dashboard",
            "control:especialidad_list",
            "control:odontologo_list",
            "control:sillon_list",
            "control:cita_list",
            "control:diagnostico_list",
            "control:tratamiento_list",
            "control:receta_list",
            "control:reporte_index",
        )
        for route_name in route_names:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_cita_agenda_filters_by_date_state_and_sillon(self):
        response = self.client.get(
            reverse("control:cita_list"),
            {
                "fecha": date.today().isoformat(),
                "estado": Cita.Estado.PENDIENTE,
                "sillon": self.sillon.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["objects"]), [self.cita])

    def test_invalid_cita_date_filter_returns_validation_errors(self):
        response = self.client.get(reverse("control:cita_list"), {"fecha": "fecha-invalida"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["objects"]), [])
        self.assertTrue(response.context["agenda_filter_form"]["fecha"].errors)

    def test_module_forms_render_and_specialty_crud(self):
        create_routes = (
            "control:especialidad_create",
            "control:odontologo_create",
            "control:sillon_create",
            "control:cita_create",
            "control:diagnostico_create",
            "control:tratamiento_create",
            "control:receta_create",
        )
        for route_name in create_routes:
            with self.subTest(route=route_name):
                self.assertEqual(self.client.get(reverse(route_name)).status_code, 200)

        create_response = self.client.post(
            reverse("control:especialidad_create"),
            {"nombre": "Endodoncia de prueba", "descripcion": "Tratamientos pulpares", "estado": "activa"},
        )
        self.assertEqual(create_response.status_code, 302)
        specialty = Especialidad.objects.get(nombre="Endodoncia de prueba")
        update_response = self.client.post(
            reverse("control:especialidad_update", args=[specialty.pk]),
            {"nombre": "Endodoncia avanzada", "descripcion": "", "estado": "activa"},
        )
        self.assertEqual(update_response.status_code, 302)
        specialty.refresh_from_db()
        self.assertEqual(specialty.nombre, "Endodoncia avanzada")
        delete_response = self.client.post(
            reverse("control:especialidad_delete", args=[specialty.pk])
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Especialidad.objects.filter(pk=specialty.pk).exists())

    def test_odontologo_form_lists_professional_active_specialties(self):
        expected = {
            "Ortodoncia y Ortopedia Maxilar",
            "Endodoncia",
            "Periodoncia",
            "Rehabilitación Oral",
            "Cirugía Maxilofacial",
            "Odontopediatría",
            "Estética Dental",
        }
        form = OdontologoForm()
        offered = set(form.fields["especialidad"].queryset.values_list("nombre", flat=True))

        self.assertTrue(expected.issubset(offered))

    def test_odontologo_registration_uses_seeded_specialty_options(self):
        response = self.client.get(reverse("control:odontologo_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alt="Logo Odontología"')
        self.assertContains(response, "/static/images/odontologia.png")
        for specialty in (
            "Ortodoncia y Ortopedia Maxilar",
            "Endodoncia",
            "Periodoncia",
            "Rehabilitación Oral",
            "Cirugía Maxilofacial",
            "Odontopediatría",
            "Estética Dental",
        ):
            with self.subTest(specialty=specialty):
                self.assertContains(response, specialty)

    def test_reports_filter_and_export_pdf(self):
        report_url = reverse("control:reporte_citas")
        response = self.client.get(
            report_url,
            {"fecha_desde": date.today().isoformat(), "estado": Cita.Estado.PENDIENTE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Elena")

        pdf_response = self.client.get(
            reverse("control:reporte_citas_pdf"),
            {"fecha_desde": date.today().isoformat(), "estado": Cita.Estado.PENDIENTE},
        )
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

        for report_type in ("diagnosticos", "tratamientos", "recetas"):
            with self.subTest(report=report_type):
                report_page = self.client.get(reverse(f"control:reporte_{report_type}"))
                self.assertEqual(report_page.status_code, 200)
                report_pdf = self.client.get(
                    reverse(f"control:reporte_{report_type}_pdf")
                )
                self.assertEqual(report_pdf.status_code, 200)
                self.assertTrue(report_pdf.content.startswith(b"%PDF"))

        invalid_response = self.client.get(
            reverse("control:reporte_citas_pdf"),
            {"fecha_desde": "not-a-date"},
        )
        self.assertEqual(invalid_response.status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="doctora",
            email="doctora@example.com",
            password="SecurePass123!",
        )

    def test_login_page_has_branding_and_fields(self):
        response = self.client.get(reverse("control:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¡Bienvenido a")
        self.assertContains(response, "Usuario o correo")
        self.assertContains(response, "Contraseña")
        self.assertContains(response, "/static/images/odontologia.png")

    def test_login_accepts_username_and_remember_session(self):
        response = self.client.post(
            reverse("control:login"),
            {
                "username": "doctora",
                "password": "SecurePass123!",
                "remember_me": "on",
            },
        )

        self.assertRedirects(response, reverse("control:dashboard"))
        self.assertEqual(int(self.client.session.get_expiry_age()), 60 * 60 * 24 * 14)

    def test_login_accepts_unique_email(self):
        response = self.client.post(
            reverse("control:login"),
            {
                "username": "doctora@example.com",
                "password": "SecurePass123!",
                "remember_me": "on",
            },
        )

        self.assertRedirects(response, reverse("control:dashboard"))

    def test_login_honors_safe_internal_next_url(self):
        response = self.client.post(
            reverse("control:login"),
            {
                "username": "doctora",
                "password": "SecurePass123!",
                "remember_me": "on",
                "next": reverse("control:paciente_list"),
            },
        )

        self.assertRedirects(response, reverse("control:paciente_list"))

    def test_login_defaults_to_browser_session_when_not_remembered(self):
        response = self.client.post(
            reverse("control:login"),
            {"username": "doctora", "password": "SecurePass123!"},
        )

        self.assertRedirects(response, reverse("control:dashboard"))
        self.assertEqual(self.client.session.get_expire_at_browser_close(), True)

    def test_login_rejects_bad_credentials_and_external_next_url(self):
        response = self.client.post(
            reverse("control:login"),
            {
                "username": "doctora",
                "password": "incorrecta",
                "next": "https://example.invalid/",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("control:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('control:login')}?next={reverse('control:dashboard')}",
            fetch_redirect_response=False,
        )

    def test_authenticated_header_shows_profile_role_and_post_logout(self):
        self.user.is_staff = True
        self.user.first_name = "Deysi"
        self.user.last_name = "Admin"
        self.user.save()
        self.client.force_login(self.user)

        dashboard_response = self.client.get(reverse("control:dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Deysi Admin")
        self.assertContains(dashboard_response, "Personal administrativo")
        self.assertContains(dashboard_response, 'action="/logout/"')
        self.assertContains(dashboard_response, 'name="csrfmiddlewaretoken"')

        logout_response = self.client.post(reverse("control:logout"))
        self.assertRedirects(logout_response, reverse("control:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_does_not_accept_get(self):
        response = self.client.get(reverse("control:logout"))

        self.assertEqual(response.status_code, 405)

    def test_password_reset_flow_pages_are_available(self):
        for route in (
            "control:password_reset",
            "control:password_reset_done",
            "control:password_reset_complete",
        ):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_email_using_custom_templates(self):
        response = self.client.post(
            reverse("control:password_reset"),
            {"email": self.user.email},
        )

        self.assertRedirects(response, reverse("control:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/password-reset/", mail.outbox[0].body)
