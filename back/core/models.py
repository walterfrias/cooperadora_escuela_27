# back/core/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid
from datetime import date


class SubscriptionStatus(models.TextChoices):
    PENDING   = 'PENDING',   'Pendiente'
    TRIAL     = 'TRIAL',     'Período de prueba'
    ACTIVE    = 'ACTIVE',    'Activa'
    EXPIRED   = 'EXPIRED',   'Vencida'
    SUSPENDED = 'SUSPENDED', 'Suspendida'


class Cooperadora(models.Model):
    numero_escuela      = models.PositiveIntegerField(unique=True)
    nombre              = models.CharField(max_length=200)
    slug                = models.SlugField(unique=True)
    dao_address         = models.CharField(max_length=42, blank=True)
    subscription_status = models.CharField(
        max_length=10,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING
    )
    trial_until         = models.DateField(null=True, blank=True)
    subscription_expiry = models.DateField(null=True, blank=True)
    email_contacto      = models.EmailField(blank=True)
    nombre_contacto     = models.CharField(max_length=100, blank=True)
    activation_token    = models.UUIDField(null=True, blank=True)
    creada_en           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cooperadoras'
        verbose_name = 'Cooperadora'
        verbose_name_plural = 'Cooperadoras'

    def __str__(self):
        return f"Escuela N°{self.numero_escuela} — {self.nombre}"

    @property
    def tiene_acceso(self):
        if self.subscription_status == SubscriptionStatus.TRIAL:
            return bool(self.trial_until and self.trial_until >= date.today())
        if self.subscription_status == SubscriptionStatus.ACTIVE:
            return bool(self.subscription_expiry and self.subscription_expiry >= date.today())
        return False


class Rol(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
    PRESIDENTE = 'PRES', 'Presidente'
    TESORERO = 'TES', 'Tesorero'
    SECRETARIO = 'SEC', 'Secretario'
    REVISOR = 'REV', 'Revisor de Cuentas'
    DOCENTE = 'DOC', 'Docente'
    SOCIO = 'SOC', 'Socio'
    PADRE = 'PAD', 'Padre'
    MIEMBRO = 'MIE', 'Miembro Cooperadora'

class UsuarioManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        if email:
            email = self.normalize_email(email)
        extra_fields.setdefault('activo', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('activo', True)
        extra_fields.setdefault('rol', Rol.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractUser):
    """
    Extiende el User model de Django
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='usuarios'
    )
    dni = models.CharField(max_length=20)
    rol = models.CharField(
        max_length=5,
        choices=Rol.choices,
        default=Rol.SOCIO
    )
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Deshabilitamos campos que no usamos
    first_name = None
    last_name = None
    username = None

    # Campos personalizados
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    padre = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='hijos',
        limit_choices_to={'rol': Rol.PADRE}
    )
    wallet_address = models.CharField(max_length=42, null=True, blank=True)
    wallet_private_key_encrypted = models.TextField(null=True, blank=True)
    key_revealed = models.BooleanField(default=False)

    # Configuración
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['dni', 'nombre', 'apellido']

    # Manager personalizado
    objects = UsuarioManager()

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        constraints = [
            models.UniqueConstraint(fields=['cooperadora', 'dni'], name='unique_usuario_dni_por_cooperadora'),
        ]
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.dni}"
    
    def save(self, *args, **kwargs):
        # Aseguramos que is_active sincronice con activo
        self.is_active = self.activo
        super().save(*args, **kwargs)


# Choices para meses del ciclo escolar (ejemplo: marzo a diciembre)
MESES_CICLO = [
    (3, 'Marzo'),
    (4, 'Abril'),
    (5, 'Mayo'),
    (6, 'Junio'),
    (7, 'Julio'),
    (8, 'Agosto'),
    (9, 'Septiembre'),
    (10, 'Octubre'),
    (11, 'Noviembre'),
    (12, 'Diciembre'),
]

class Grado(models.Model):
    """Tabla de grados escolares: 1° a 7°, con división A, B, C opcional."""
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        on_delete=models.CASCADE,
        related_name='grados'
    )
    numero = models.PositiveSmallIntegerField(choices=[(i, f'{i}°') for i in range(1, 8)])
    letra = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C')],
        blank=True,
        help_text="Opcional, ej: A, B, C"
    )

    class Meta:
        unique_together = ('cooperadora', 'numero', 'letra')
        ordering = ['numero', 'letra']
        verbose_name = "Grado"
        verbose_name_plural = "Grados"

    def __str__(self):
        if self.letra:
            return f"{self.numero}° {self.letra}"
        return f"{self.numero}°"

class Inscripcion(models.Model):
    """Vincula un alumno (Usuario con rol SOCIO) a un grado en un año determinado."""
    MODALIDAD_CHOICES = [
        ('mensual', 'Mensual'),
        ('anual', 'Anual'),
    ]
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        on_delete=models.CASCADE,
        related_name='inscripciones'
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='inscripciones')
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name='inscripciones')
    anio = models.PositiveIntegerField()
    activa = models.BooleanField(default=True, help_text="Indica si es la inscripción actual del alumno")
    modalidad = models.CharField(max_length=10, choices=MODALIDAD_CHOICES, default='mensual')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        unique_together = ('usuario', 'anio')  # Un alumno solo una inscripción por año
        ordering = ['-anio', 'usuario__apellido', 'usuario__nombre']
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def __str__(self):
        return f"{self.usuario} - {self.grado} - {self.anio}"

    def clean(self):
        # Validar que el usuario tenga rol SOCIO (opcional, depende de la lógica de negocio)
        if self.usuario.rol != 'SOC':  # Ajustar si el código del rol es 'SOCIO' o 'SOC'
            raise ValidationError({'usuario': 'El usuario debe tener rol SOCIO para inscribirse.'})
        # Si la modalidad es anual, verificar que no existan pagos mensuales previos
        if self.modalidad == 'anual' and self.pk:  # Si ya existe, verificar pagos
            if self.pagos.filter(tipo='mensual').exists():
                raise ValidationError({'modalidad': 'No se puede cambiar a anual porque ya existen pagos mensuales.'})
        # Si es nueva inscripción y modalidad anual, no hay problema

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Publicacion(models.Model):
    TIPO_CHOICES = [
        ('noticia', 'Noticia'),
        ('agenda', 'Agenda'),
        ('novedad', 'Novedad'),
    ]
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        on_delete=models.CASCADE,
        related_name='publicaciones'
    )
    titulo = models.CharField(max_length=200)
    encabezado = models.CharField(max_length=300, blank=True, null=True)
    contenido = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='noticia')
    imagen_portada = models.ImageField(upload_to='publicaciones/portadas/', blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='publicaciones'
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Publicación"
        verbose_name_plural = "Publicaciones"

    def __str__(self):
        return self.titulo


class PublicacionImagen(models.Model):
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='publicaciones/galeria/')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Imagen de publicación"
        verbose_name_plural = "Imágenes de publicaciones"

    def __str__(self):
        return f"Imagen de {self.publicacion.titulo}"

class CuotaMensual(models.Model):
    """Define el monto de la cuota para un mes y año específicos (global para todos los grados)."""
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        on_delete=models.CASCADE,
        related_name='cuotas_mensuales'
    )
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField(choices=MESES_CICLO)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    activa = models.BooleanField(default=True, help_text="Permite deshabilitar una cuota sin eliminarla")

    class Meta:
        unique_together = ('cooperadora', 'anio', 'mes')
        ordering = ['anio', 'mes']
        verbose_name = "Cuota mensual"
        verbose_name_plural = "Cuotas mensuales"

    def __str__(self):
        return f"{self.get_mes_display()} {self.anio}: ${self.monto}"

class ConfiguracionAnual(models.Model):
    """Monto fijo del pago anual por año."""
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        on_delete=models.CASCADE,
        related_name='configuraciones_anuales'
    )
    anio = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('cooperadora', 'anio')
        ordering = ['-anio']
        verbose_name = "Configuración anual"
        verbose_name_plural = "Configuraciones anuales"

    def __str__(self):
        return f"Pago anual {self.anio}: ${self.monto}"

class Pago(models.Model):
    """Registro de pagos: puede ser cuota mensual, pago anual o donación."""
    TIPO_CHOICES = [
        ('mensual', 'Cuota mensual'),
        ('anual', 'Pago anual'),
        ('donacion', 'Donación'),
    ]
    cooperadora = models.ForeignKey(
        Cooperadora,
        null=True,
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    inscripcion = models.ForeignKey(Inscripcion, on_delete=models.CASCADE, related_name='pagos')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    mes = models.PositiveSmallIntegerField(
        choices=MESES_CICLO,
        null=True,
        blank=True,
        help_text="Obligatorio si tipo es 'mensual'"
    )
    anio = models.PositiveIntegerField()  # Año del pago (debe coincidir con inscripción)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)
    token_minteado = models.BooleanField(default=False)
    token_mint_tx = models.CharField(max_length=66, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['inscripcion', 'tipo', 'mes', 'anio'],
                name='unique_pago_mensual',
                condition=models.Q(tipo='mensual')
            ),
            # No permitir más de un pago anual por inscripción
            models.UniqueConstraint(
                fields=['inscripcion'],
                name='unique_pago_anual',
                condition=models.Q(tipo='anual')
            ),
        ]
        ordering = ['-fecha_pago']
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        if self.tipo == 'mensual':
            return f"{self.inscripcion} - {self.get_mes_display()} {self.anio}: ${self.monto}"
        elif self.tipo == 'anual':
            return f"{self.inscripcion} - Pago anual {self.anio}: ${self.monto}"
        else:
            return f"{self.inscripcion} - Donación ${self.monto} ({self.fecha_pago.date()})"

    def clean(self):
        # Validaciones específicas
        if self.tipo == 'mensual' and self.mes is None:
            raise ValidationError({'mes': 'El mes es obligatorio para pagos mensuales.'})
        if self.tipo == 'anual' and self.mes is not None:
            raise ValidationError({'mes': 'El mes no debe indicarse para pagos anuales.'})
        # El año del pago debe coincidir con el año de la inscripción
        if self.anio != self.inscripcion.anio:
            raise ValidationError({'anio': f'El año del pago debe ser {self.inscripcion.anio} (año de la inscripción).'})
        # Si es pago anual, verificar que la inscripción sea de modalidad anual
        if self.tipo == 'anual' and self.inscripcion.modalidad != 'anual':
            raise ValidationError({'tipo': 'No se puede registrar un pago anual para una inscripción mensual.'})
        # Si es pago anual, verificar que exista configuración para ese año (opcional)
        if self.tipo == 'anual':
            if not ConfiguracionAnual.objects.filter(anio=self.anio, activa=True).exists():
                raise ValidationError({'anio': f'No hay configuración de pago anual para el año {self.anio}.'})
        # Si es pago mensual, verificar que la inscripción sea mensual
        if self.tipo == 'mensual' and self.inscripcion.modalidad != 'mensual':
            raise ValidationError({'tipo': 'No se puede registrar un pago mensual para una inscripción anual.'})
        # Verificar que no se pague dos veces el mismo mes (ya cubierto por UniqueConstraint)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
