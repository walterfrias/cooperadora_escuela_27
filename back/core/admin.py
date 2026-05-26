# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from datetime import timedelta
from .models import Usuario, Grado, Inscripcion, CuotaMensual, ConfiguracionAnual, Pago, Cooperadora, SubscriptionStatus

@admin.register(Cooperadora)
class CooperadoraAdmin(admin.ModelAdmin):
    list_display = ('numero_escuela', 'nombre', 'slug', 'subscription_status', 'trial_until', 'subscription_expiry', 'acceso_activo', 'creada_en')
    list_filter = ('subscription_status',)
    search_fields = ('nombre', 'numero_escuela', 'slug')
    readonly_fields = ('slug', 'creada_en')
    fieldsets = (
        (None, {'fields': ('numero_escuela', 'nombre', 'slug', 'dao_address')}),
        ('Suscripción', {'fields': ('subscription_status', 'trial_until', 'subscription_expiry')}),
        ('Info', {'fields': ('creada_en',)}),
    )
    actions = ['habilitar_trial_30_dias', 'activar_anualidad', 'suspender', 'marcar_pendiente']

    @admin.display(boolean=True, description='Acceso activo')
    def acceso_activo(self, obj):
        return obj.tiene_acceso

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = f"escuela{obj.numero_escuela}"
        super().save_model(request, obj, form, change)

    @admin.action(description='Habilitar trial de 30 días')
    def habilitar_trial_30_dias(self, request, queryset):
        hoy = timezone.now().date()
        queryset.update(
            subscription_status=SubscriptionStatus.TRIAL,
            trial_until=hoy + timedelta(days=30),
        )

    @admin.action(description='Activar suscripción anual (1 año desde hoy)')
    def activar_anualidad(self, request, queryset):
        hoy = timezone.now().date()
        queryset.update(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expiry=hoy + timedelta(days=365),
        )

    @admin.action(description='Suspender')
    def suspender(self, request, queryset):
        queryset.update(subscription_status=SubscriptionStatus.SUSPENDED)

    @admin.action(description='Marcar como pendiente')
    def marcar_pendiente(self, request, queryset):
        queryset.update(subscription_status=SubscriptionStatus.PENDING)


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
        ('Información personal', {'fields': ('nombre', 'apellido', 'dni', 'telefono', 'rol', 'cooperadora')}),
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