from cryptography.fernet import Fernet
import os
from rest_framework import generics, permissions
from django.core.mail import send_mail
from django.conf import settings as django_settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import Usuario, Publicacion, PublicacionImagen, Cooperadora
from django.shortcuts import get_object_or_404
from .permissions import EsTesoreroOAdmin, EsSecretarioOAdmin
from .throttles import LoginRateThrottle
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Grado, Inscripcion, Pago, CuotaMensual
from .serializers import (
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioHijoSerializer,
    UsuarioLoginSerializer,
    GradoSerializer,
    InscripcionSerializer,
    PagoSerializer,
    PagoMultipleSerializer,
    PagoAnualSerializer,
    PagoSimpleSerializer,
    PublicacionSerializer,
    EstadoCuentaHijoSerializer,
    CuotaMensualSerializer,
    RegistroCooperadoraSerializer,
)


class TenantQuerysetMixin:
    """Filtra el queryset base por la cooperadora del request."""
    def get_queryset(self):
        return super().get_queryset().filter(cooperadora=self.request.cooperadora)

    def perform_create(self, serializer):
        serializer.save(cooperadora=self.request.cooperadora)

class CrearUsuarioView(TenantQuerysetMixin, generics.CreateAPIView):
    """
    Crea un nuevo usuario (PAD o SOC).
    Solo accesible para Tesorero y Admin.
    - rol=PAD: requiere email, nombre, apellido, dni
    - rol=SOC: requiere email_padre (debe existir un PAD con ese email)
    """
    queryset = Usuario.objects.all()
    serializer_class = UsuarioCreateSerializer
    permission_classes = [IsAuthenticated, EsTesoreroOAdmin]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['cooperadora'] = self.request.cooperadora
        return ctx

class UsuarioDetailView(TenantQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated, EsTesoreroOAdmin]

class UsuarioListView(TenantQuerysetMixin, generics.ListAPIView):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated, EsTesoreroOAdmin]

class UsuarioLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = UsuarioLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generar tokens JWT
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        # Opcional: incluir datos del usuario
        user_data = UsuarioSerializer(user).data
        return Response({**tokens, 'user': user_data}, status=status.HTTP_200_OK)
    

class MisHijosView(generics.ListAPIView):
    serializer_class = UsuarioHijoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Usuario.objects.filter(
            cooperadora=self.request.cooperadora,
            padre=self.request.user,
        )


class EstadoCuentaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        anio = int(request.query_params.get('anio', timezone.now().year))
        hijos = Usuario.objects.filter(
            cooperadora=request.cooperadora,
            padre=request.user,
        )
        serializer = EstadoCuentaHijoSerializer(hijos, many=True, context={'anio': anio})
        return Response(serializer.data)


class PublicacionViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = Publicacion.objects.all()
    serializer_class = PublicacionSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), EsSecretarioOAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        publicacion = serializer.save(cooperadora=self.request.cooperadora)
        for img in self.request.FILES.getlist('imagenes'):
            PublicacionImagen.objects.create(publicacion=publicacion, imagen=img)

    def perform_update(self, serializer):
        publicacion = serializer.save()
        for img in self.request.FILES.getlist('imagenes'):
            PublicacionImagen.objects.create(publicacion=publicacion, imagen=img)
        ids_eliminar = self.request.data.getlist('eliminar_imagenes')
        if ids_eliminar:
            PublicacionImagen.objects.filter(id__in=ids_eliminar, publicacion=publicacion).delete()


class GradoViewSet(TenantQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Grado.objects.all()
    serializer_class = GradoSerializer
    permission_classes = [IsAuthenticated]

class InscripcionViewSet(viewsets.ModelViewSet):
    serializer_class = InscripcionSerializer

    def get_queryset(self):
        coop = self.request.cooperadora
        user = self.request.user
        if user.rol in ['TES', 'ADMIN', 'PRES']:
            return Inscripcion.objects.filter(cooperadora=coop)
        if user.rol == 'PAD':
            return Inscripcion.objects.filter(cooperadora=coop, usuario__padre=user)
        if user.rol == 'SOC':
            return Inscripcion.objects.filter(cooperadora=coop, usuario=user)
        return Inscripcion.objects.none()

    def perform_create(self, serializer):
        serializer.save(cooperadora=self.request.cooperadora)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, EsTesoreroOAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class PagoViewSet(viewsets.ModelViewSet):
    serializer_class = PagoSerializer

    def get_queryset(self):
        from django.db.models import Q
        coop = self.request.cooperadora
        user = self.request.user
        if user.rol in ['TES', 'ADMIN', 'PRES']:
            queryset = Pago.objects.filter(cooperadora=coop)
        elif user.rol == 'PAD':
            queryset = Pago.objects.filter(cooperadora=coop, inscripcion__usuario__padre=user)
        elif user.rol == 'SOC':
            queryset = Pago.objects.filter(cooperadora=coop, inscripcion__usuario=user)
        else:
            return Pago.objects.none()
        mes = self.request.query_params.get('mes')
        anio = self.request.query_params.get('anio')
        tipo = self.request.query_params.get('tipo')
        grado = self.request.query_params.get('grado')
        busqueda = self.request.query_params.get('busqueda')
        if mes:
            queryset = queryset.filter(mes=mes)
        if anio:
            queryset = queryset.filter(anio=anio)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if grado:
            queryset = queryset.filter(inscripcion__grado_id=grado)
        if busqueda:
            queryset = queryset.filter(
                Q(inscripcion__usuario__apellido__icontains=busqueda) |
                Q(inscripcion__usuario__nombre__icontains=busqueda) |
                Q(inscripcion__usuario__dni__icontains=busqueda)
            )
        return queryset

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'pago_multiple', 'pago_anual', 'pago_simple']:
            permission_classes = [IsAuthenticated, EsTesoreroOAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='pago-simple')
    def pago_simple(self, request):
        serializer = PagoSimpleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        inscripcion = serializer.context['inscripcion']
        cuota = serializer.context['cuota']
        mes = serializer.validated_data['mes']
        anio = serializer.validated_data['anio']
        monto_total = serializer.validated_data['monto_total']

        coop = request.cooperadora
        with transaction.atomic():
            if monto_total >= cuota.monto:
                Pago.objects.create(
                    cooperadora=coop,
                    inscripcion=inscripcion,
                    tipo='mensual',
                    mes=mes,
                    anio=anio,
                    monto=cuota.monto,
                    observaciones=f"Pago cuota {cuota.get_mes_display()} {anio}"
                )
                mensaje = f"Cuota de {cuota.get_mes_display()} registrada (${cuota.monto})."
                if monto_total > cuota.monto:
                    excedente = monto_total - cuota.monto
                    Pago.objects.create(
                        cooperadora=coop,
                        inscripcion=inscripcion,
                        tipo='donacion',
                        mes=mes,
                        anio=anio,
                        monto=excedente,
                        observaciones=f"Excedente pago {cuota.get_mes_display()} {anio}"
                    )
                    mensaje += f" Excedente de ${excedente} registrado como donación."
            else:
                Pago.objects.create(
                    cooperadora=coop,
                    inscripcion=inscripcion,
                    tipo='donacion',
                    mes=mes,
                    anio=anio,
                    monto=monto_total,
                    observaciones=f"Pago insuficiente para cuota {cuota.get_mes_display()} {anio} (cuota: ${cuota.monto})"
                )
                mensaje = f"El monto no cubre la cuota (${cuota.monto}). Se registró como donación."

        return Response({"mensaje": mensaje}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='pago-multiple')
    def pago_multiple(self, request):
        serializer = PagoMultipleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        inscripcion = serializer.context['inscripcion']
        meses = serializer.validated_data['meses']
        anio = serializer.validated_data['anio']
        monto_total = serializer.validated_data['monto_total']
        cuotas = serializer.context['cuotas']  # ya están validadas

        coop = request.cooperadora
        monto_esperado = sum(cuota.monto for cuota in cuotas)

        with transaction.atomic():
            if monto_total >= monto_esperado:
                for cuota in cuotas:
                    Pago.objects.create(
                        cooperadora=coop,
                        inscripcion=inscripcion,
                        tipo='mensual',
                        mes=cuota.mes,
                        anio=anio,
                        monto=cuota.monto,
                        observaciones=f"Pago mes {cuota.get_mes_display()}"
                    )
                if monto_total > monto_esperado:
                    excedente = monto_total - monto_esperado
                    Pago.objects.create(
                        cooperadora=coop,
                        inscripcion=inscripcion,
                        tipo='donacion',
                        mes=None,
                        anio=anio,
                        monto=excedente,
                        observaciones="Excedente de pago de cuotas"
                    )
                mensaje = "Pago de cuotas registrado."
                if monto_total > monto_esperado:
                    mensaje += f" Se generó una donación de ${excedente}."
            else:
                Pago.objects.create(
                    cooperadora=coop,
                    inscripcion=inscripcion,
                    tipo='donacion',
                    mes=None,
                    anio=anio,
                    monto=monto_total,
                    observaciones="Pago insuficiente para cuotas"
                )
                mensaje = f"El monto no cubre ninguna cuota. Se registró como donación de ${monto_total}."

        return Response({"mensaje": mensaje}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='pago-anual')
    def pago_anual(self, request):
        serializer = PagoAnualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inscripcion = serializer.context['inscripcion']
        anio = serializer.validated_data['anio']
        monto = serializer.validated_data['monto']

        with transaction.atomic():
            pago = Pago.objects.create(
                cooperadora=request.cooperadora,
                inscripcion=inscripcion,
                tipo='anual',
                mes=None,
                anio=anio,
                monto=monto,
                observaciones="Pago anual"
            )

        response_serializer = PagoSerializer(pago)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        allowed = {k: v for k, v in request.data.items() if k in ('nombre', 'apellido', 'telefono')}
        serializer = UsuarioSerializer(request.user, data=allowed, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CambiarPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password_actual = request.data.get('password_actual', '')
        password_nuevo = request.data.get('password_nuevo', '')

        if not request.user.check_password(password_actual):
            return Response({'password_actual': 'La contraseña actual es incorrecta.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password_nuevo, user=request.user)
        except DjangoValidationError as e:
            return Response({'password_nuevo': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(password_nuevo)
        request.user.save()
        return Response({'detail': 'Contraseña actualizada correctamente.'})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Se requiere el refresh token.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({'detail': 'Token inválido o ya expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Sesión cerrada correctamente.'}, status=status.HTTP_200_OK)


class CuotaMensualViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    queryset = CuotaMensual.objects.all()
    serializer_class = CuotaMensualSerializer
    permission_classes = [IsAuthenticated, EsTesoreroOAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        anio = self.request.query_params.get('anio')
        if anio:
            queryset = queryset.filter(anio=anio)
        return queryset


class RegistroCooperadoraView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroCooperadoraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cooperadora = serializer.save()

        self._notificar_admin(cooperadora)
        self._confirmar_registrante(cooperadora)

        return Response(
            {'detail': 'Solicitud recibida. Te contactaremos cuando tu acceso esté habilitado.'},
            status=status.HTTP_201_CREATED,
        )

    def _confirmar_registrante(self, cooperadora):
        try:
            send_mail(
                subject='[CooperaApp] Recibimos tu solicitud',
                message=(
                    f'Hola {cooperadora.nombre_contacto},\n\n'
                    f'Recibimos tu solicitud para registrar la cooperadora "{cooperadora.nombre}" '
                    f'(Escuela N°{cooperadora.numero_escuela}).\n\n'
                    f'Estamos revisando los datos. Te escribiremos a este email cuando tu acceso esté habilitado.\n\n'
                    f'Saludos,\nEl equipo de CooperaApp'
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cooperadora.email_contacto],
                fail_silently=True,
            )
        except Exception:
            pass

    def _notificar_admin(self, cooperadora):
        try:
            send_mail(
                subject=f'[CooperaApp] Nueva solicitud: Escuela N°{cooperadora.numero_escuela}',
                message=(
                    f'Nueva cooperadora registrada.\n\n'
                    f'Escuela: {cooperadora.nombre}\n'
                    f'Número: {cooperadora.numero_escuela}\n'
                    f'Contacto: {cooperadora.nombre_contacto}\n'
                    f'Email: {cooperadora.email_contacto}\n\n'
                    f'Aprobá el acceso desde el panel: /admin/core/cooperadora/{cooperadora.pk}/change/'
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[django_settings.PLATFORM_ADMIN_EMAIL],
                fail_silently=True,
            )
        except Exception:
            pass


class CooperadoraInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        c = get_object_or_404(Cooperadora, slug=slug)
        return Response({'nombre': c.nombre, 'numero_escuela': c.numero_escuela})


class ActivarCooperadoraView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            c = Cooperadora.objects.get(activation_token=token)
        except Cooperadora.DoesNotExist:
            return Response({'detail': 'Token inválido o ya utilizado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'nombre': c.nombre,
            'email_contacto': c.email_contacto,
            'slug': c.slug,
        })

    def post(self, request, token):
        try:
            c = Cooperadora.objects.get(activation_token=token)
        except Cooperadora.DoesNotExist:
            return Response({'detail': 'Token inválido o ya utilizado.'}, status=status.HTTP_404_NOT_FOUND)

        nombre = request.data.get('nombre', '').strip()
        apellido = request.data.get('apellido', '').strip()
        dni = request.data.get('dni', '').strip()
        password = request.data.get('password', '')

        errors = {}
        if not nombre:
            errors['nombre'] = ['Este campo es requerido.']
        if not apellido:
            errors['apellido'] = ['Este campo es requerido.']
        if not dni:
            errors['dni'] = ['Este campo es requerido.']
        if not password:
            errors['password'] = ['Este campo es requerido.']

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password)
        except DjangoValidationError as e:
            return Response({'password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        if Usuario.objects.filter(email=c.email_contacto).exists():
            return Response(
                {'detail': 'Ya existe un usuario con ese email. Iniciá sesión directamente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            Usuario.objects.create_user(
                email=c.email_contacto,
                password=password,
                nombre=nombre,
                apellido=apellido,
                dni=dni,
                rol='ADMIN',
                cooperadora=c,
                activo=True,
            )
            c.activation_token = None
            c.save(update_fields=['activation_token'])

        return Response({'detail': 'Usuario creado correctamente. Ya podés iniciar sesión.'})


class MiWalletView(APIView):
    """
    GET /mi-wallet/
    Solo para PAD autenticado.
    - Primera llamada: devuelve address + private_key desencriptada y marca key_revealed=True.
    - Llamadas siguientes: devuelve solo address (key_revealed=True → key omitida).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.rol != 'PAD':
            return Response(
                {'detail': 'Solo los padres tienen wallet.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.wallet_address:
            return Response(
                {'detail': 'Wallet aún no generada. Intentá en unos segundos.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            'address': user.wallet_address,
            'revealed': user.key_revealed,
            'private_key': None,
        }

        if not user.key_revealed:
            encryption_key = os.environ.get('WALLET_ENCRYPTION_KEY', '')
            fernet = Fernet(encryption_key.encode())
            data['private_key'] = fernet.decrypt(
                user.wallet_private_key_encrypted.encode()
            ).decode()
            Usuario.objects.filter(pk=user.pk).update(key_revealed=True)

        return Response(data)
