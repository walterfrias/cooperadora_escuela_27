# core/admin.py
import uuid
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings as django_settings
from datetime import timedelta
from .models import Usuario, Grado, Inscripcion, CuotaMensual, ConfiguracionAnual, Pago, Cooperadora, SubscriptionStatus

@admin.register(Cooperadora)
class CooperadoraAdmin(admin.ModelAdmin):
    list_display = ('numero_escuela', 'nombre', 'slug', 'subscription_status', 'trial_until', 'subscription_expiry', 'acceso_activo', 'creada_en')
    list_filter = ('subscription_status',)
    search_fields = ('nombre', 'numero_escuela', 'slug')
    readonly_fields = ('slug', 'dao_address', 'activation_token', 'creada_en')
    fieldsets = (
        (None, {'fields': ('numero_escuela', 'nombre', 'slug', 'dao_address')}),
        ('Suscripción', {'fields': ('subscription_status', 'trial_until', 'subscription_expiry')}),
        ('AFIP', {'fields': ('cuit', 'afip_punto_venta')}),
        ('Info', {'fields': ('creada_en',)}),
    )
    actions = ['habilitar_trial_30_dias', 'activar_anualidad', 'suspender', 'marcar_pendiente', 'enviar_bienvenida']

    @admin.display(boolean=True, description='Acceso activo')
    def acceso_activo(self, obj):
        return obj.tiene_acceso

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = f"escuela{obj.numero_escuela}"
        super().save_model(request, obj, form, change)

    def _enviar_link_activacion(self, cooperadora, token, es_trial=False):
        if not cooperadora.email_contacto:
            return
        link = f'{django_settings.FRONTEND_URL}/{cooperadora.slug}/activar?token={token}'
        periodo = 'Tenés 30 días de prueba gratuita.' if es_trial else 'Tu suscripción anual ya está activa.'
        send_mail(
            subject='[CooperaApp] Activá tu cuenta',
            message=(
                f'Hola {cooperadora.nombre_contacto},\n\n'
                f'Tu cooperadora "{cooperadora.nombre}" fue aprobada. '
                f'{periodo}\n\n'
                f'Para crear tu usuario administrador hacé clic en el siguiente enlace:\n\n'
                f'{link}\n\n'
                f'El enlace es de un solo uso.\n\n'
                f'Saludos,\nEl equipo de CooperaApp'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cooperadora.email_contacto],
            fail_silently=True,
        )

    def _necesita_activacion(self, cooperadora):
        """True si la cooperadora aún no tiene usuario ADMIN creado."""
        return not cooperadora.usuarios.filter(rol='ADMIN').exists()

    @admin.action(description='Habilitar trial de 30 días')
    def habilitar_trial_30_dias(self, request, queryset):
        hoy = timezone.now().date()
        for cooperadora in queryset:
            token = uuid.uuid4()
            cooperadora.subscription_status = SubscriptionStatus.TRIAL
            cooperadora.trial_until = hoy + timedelta(days=30)
            cooperadora.activation_token = token
            cooperadora.save(update_fields=['subscription_status', 'trial_until', 'activation_token'])
            if self._necesita_activacion(cooperadora):
                self._enviar_link_activacion(cooperadora, token, es_trial=True)

    @admin.action(description='Activar suscripción anual (1 año desde hoy)')
    def activar_anualidad(self, request, queryset):
        hoy = timezone.now().date()
        for cooperadora in queryset:
            token = uuid.uuid4()
            cooperadora.subscription_status = SubscriptionStatus.ACTIVE
            cooperadora.subscription_expiry = hoy + timedelta(days=365)
            cooperadora.activation_token = token
            cooperadora.save(update_fields=['subscription_status', 'subscription_expiry', 'activation_token'])
            if self._necesita_activacion(cooperadora):
                self._enviar_link_activacion(cooperadora, token, es_trial=False)

    @admin.action(description='Suspender')
    def suspender(self, request, queryset):
        queryset.update(subscription_status=SubscriptionStatus.SUSPENDED)

    @admin.action(description='Marcar como pendiente')
    def marcar_pendiente(self, request, queryset):
        queryset.update(subscription_status=SubscriptionStatus.PENDING)

    @admin.action(description='Enviar email de bienvenida al contacto')
    def enviar_bienvenida(self, request, queryset):
        for cooperadora in queryset:
            if not cooperadora.email_contacto:
                continue
            send_mail(
                subject='¡Bienvenida a CooperaApp!',
                message=(
                    f'Hola {cooperadora.nombre_contacto},\n\n'
                    f'Tu cooperadora "{cooperadora.nombre}" ya tiene acceso a CooperaApp.\n\n'
                    f'Podés ingresar en: cooperadoras.org/{cooperadora.slug}\n\n'
                    f'Saludos,\nEl equipo de CooperaApp'
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cooperadora.email_contacto],
                fail_silently=True,
            )


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Configuración personalizada para el modelo Usuario
    """
    # Campos que se mostrarán en la lista de usuarios
    list_display = ('email', 'nombre', 'apellido', 'dni', 'rol', 'cooperadora', 'is_staff', 'is_active')
    search_fields = ('email', 'nombre', 'apellido', 'dni')
    list_filter = ('rol', 'cooperadora', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre', 'apellido', 'dni', 'cuil', 'telefono', 'rol', 'cooperadora')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'apellido', 'dni', 'password1', 'password2', 'rol', 'cooperadora'),
        }),
    )
    
    # Ordenamiento por defecto
    ordering = ('email',)

@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'letra')
    ordering = ('numero', 'letra')

@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'grado', 'anio', 'modalidad', 'activa')
    list_filter = ('anio', 'modalidad', 'activa')
    search_fields = ('usuario__nombre', 'usuario__apellido', 'usuario__dni')

@admin.register(CuotaMensual)
class CuotaMensualAdmin(admin.ModelAdmin):
    list_display = ('anio', 'mes', 'monto', 'activa')
    list_filter = ('anio', 'activa')
    ordering = ('-anio', 'mes')

@admin.register(ConfiguracionAnual)
class ConfiguracionAnualAdmin(admin.ModelAdmin):
    list_display = ('anio', 'monto', 'activa')

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'tipo', 'mes', 'anio', 'monto', 'fecha_pago')
    list_filter = ('tipo', 'anio')
    search_fields = ('inscripcion__usuario__nombre', 'inscripcion__usuario__apellido')
    date_hierarchy = 'fecha_pago'