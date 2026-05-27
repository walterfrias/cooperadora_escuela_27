# back/core/serializers.py
from rest_framework import serializers
from rest_framework import serializers
from .models import Grado, Inscripcion, Pago, CuotaMensual, ConfiguracionAnual, Usuario, Publicacion, PublicacionImagen, MESES_CICLO, Cooperadora  # noqa: F401

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

class UsuarioSerializer(serializers.ModelSerializer):
    padre_email = serializers.SerializerMethodField()
    padre_dni = serializers.SerializerMethodField()
    padre_nombre = serializers.SerializerMethodField()
    padre_apellido = serializers.SerializerMethodField()
    dni_padre = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Usuario
        fields = ['uuid', 'email', 'dni', 'nombre', 'apellido',
                  'rol', 'telefono', 'activo', 'fecha_registro',
                  'padre_email', 'padre_dni', 'padre_nombre', 'padre_apellido', 'dni_padre',
                  'wallet_address', 'key_revealed']
        read_only_fields = ['uuid', 'fecha_registro', 'wallet_address', 'key_revealed']

    def get_padre_email(self, obj):
        return obj.padre.email if obj.padre else None

    def get_padre_dni(self, obj):
        return obj.padre.dni if obj.padre else None

    def get_padre_nombre(self, obj):
        return obj.padre.nombre if obj.padre else None

    def get_padre_apellido(self, obj):
        return obj.padre.apellido if obj.padre else None

    def update(self, instance, validated_data):
        dni_padre = validated_data.pop('dni_padre', None)
        instance = super().update(instance, validated_data)

        if 'dni_padre' in self.initial_data and instance.rol == 'SOC':
            if dni_padre:
                try:
                    padre = Usuario.objects.get(dni=dni_padre, rol='PAD')
                    instance.padre = padre
                except Usuario.DoesNotExist:
                    raise serializers.ValidationError(
                        {'dni_padre': f'No existe un padre/tutor con el DNI "{dni_padre}".'}
                    )
            else:
                instance.padre = None
            instance.save(update_fields=['padre'])

        return instance

class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    dni_padre = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    grado_id = serializers.PrimaryKeyRelatedField(
        queryset=Grado.objects.all(), required=False, allow_null=True, write_only=True
    )
    anio = serializers.IntegerField(required=False, write_only=True)
    modalidad = serializers.ChoiceField(
        choices=['mensual', 'anual'], required=False, default='mensual', write_only=True
    )

    class Meta:
        model = Usuario
        fields = ['email', 'password', 'dni', 'nombre', 'apellido', 'rol', 'telefono',
                  'dni_padre', 'grado_id', 'anio', 'modalidad']

    def validate(self, data):
        rol = data.get('rol', 'SOC')

        if rol == 'SOC':
            dni_padre = data.get('dni_padre')
            if dni_padre:
                # Filtramos por cooperadora para no cruzar datos entre tenants
                cooperadora = self.context.get('cooperadora')
                qs = Usuario.objects.filter(dni=dni_padre, rol='PAD')
                if cooperadora:
                    qs = qs.filter(cooperadora=cooperadora)
                try:
                    data['padre'] = qs.get()
                except Usuario.DoesNotExist:
                    raise serializers.ValidationError(
                        {'dni_padre': f'No existe un padre/tutor con el DNI "{dni_padre}".'}
                    )
            if not data.get('grado_id'):
                raise serializers.ValidationError({'grado_id': 'Debe asignar un grado al alumno.'})
            if not data.get('anio'):
                raise serializers.ValidationError({'anio': 'Debe indicar el año de inscripción.'})
        else:
            if not data.get('email'):
                raise serializers.ValidationError({'email': 'El email es obligatorio para este tipo de usuario.'})
            if not data.get('password'):
                raise serializers.ValidationError({'password': 'La contraseña es obligatoria.'})
            try:
                validate_password(data['password'])
            except DjangoValidationError as e:
                raise serializers.ValidationError({'password': list(e.messages)})

        return data

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        validated_data.pop('dni_padre', None)
        grado = validated_data.pop('grado_id', None)
        anio = validated_data.pop('anio', None)
        modalidad = validated_data.pop('modalidad', 'mensual')

        with transaction.atomic():
            user = super().create(validated_data)
            if password:
                user.set_password(password)
                user.save(update_fields=['password'])

            if grado and anio:
                Inscripcion.objects.create(
                    usuario=user,
                    grado=grado,
                    cooperadora=user.cooperadora,
                    anio=anio,
                    modalidad=modalidad,
                )

        return user
    
class UsuarioLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            # Autenticar usando el email (asumiendo que es el campo de identificación)
            user = authenticate(request=self.context.get('request'),
                                username=email, password=password)
            if not user:
                raise serializers.ValidationError('Credenciales inválidas.')
        else:
            raise serializers.ValidationError('Debe proporcionar email y contraseña.')

        data['user'] = user
        return data


class RegistroCooperadoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cooperadora
        fields = ('numero_escuela', 'nombre', 'nombre_contacto', 'email_contacto')

    def validate_numero_escuela(self, value):
        if Cooperadora.objects.filter(numero_escuela=value).exists():
            raise serializers.ValidationError('Ya existe una cooperadora registrada con ese número de escuela.')
        return value

    def create(self, validated_data):
        validated_data['slug'] = f"escuela{validated_data['numero_escuela']}"
        return super().create(validated_data)



class GradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grado
        fields = '__all__'

class InscripcionResumenSerializer(serializers.ModelSerializer):
    grado = serializers.StringRelatedField()

    class Meta:
        model = Inscripcion
        fields = ['id', 'grado', 'anio', 'modalidad', 'activa', 'fecha_inscripcion']


class UsuarioHijoSerializer(serializers.ModelSerializer):
    inscripciones = InscripcionResumenSerializer(many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = ['uuid', 'nombre', 'apellido', 'dni', 'rol', 'inscripciones']

class InscripcionSerializer(serializers.ModelSerializer):
    usuario = UsuarioHijoSerializer(read_only=True)
    usuario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        source='usuario',
        write_only=True
    )
    grado = serializers.PrimaryKeyRelatedField(queryset=Grado.objects.all())
    grado_detalle = GradoSerializer(source='grado', read_only=True)

    class Meta:
        model = Inscripcion
        fields = '__all__'
        read_only_fields = ['fecha_inscripcion']

    def validate(self, data):
        # Validar que el usuario sea socio (opcional, según tu lógica)
        usuario = data['usuario']
        if usuario.rol not in ['SOC', 'SOCIO']:  # ajusta según tu choice
            raise serializers.ValidationError("El usuario debe tener rol de socio.")
        # Validar que no exista otra inscripción para el mismo año
        if Inscripcion.objects.filter(usuario=usuario, anio=data['anio']).exists():
            raise serializers.ValidationError("El usuario ya tiene una inscripción para este año.")
        return data

class PagoSerializer(serializers.ModelSerializer):
    inscripcion_detalle = InscripcionSerializer(source='inscripcion', read_only=True)
    inscripcion_id = serializers.PrimaryKeyRelatedField(
        queryset=Inscripcion.objects.all(),
        source='inscripcion',
        write_only=True
    )

    class Meta:
        model = Pago
        fields = '__all__'
        read_only_fields = ['fecha_pago']

    def validate(self, data):
        # Validar que si es mensual, tenga mes; si no, que mes sea null
        if data['tipo'] == 'mensual' and data.get('mes') is None:
            raise serializers.ValidationError("El mes es obligatorio para pagos mensuales.")
        if data['tipo'] != 'mensual' and data.get('mes') is not None:
            raise serializers.ValidationError("El mes solo debe indicarse para pagos mensuales.")
        # Validar que el año coincida con la inscripción
        if data['inscripcion'].anio != data['anio']:
            raise serializers.ValidationError("El año del pago debe coincidir con el año de la inscripción.")
        # Si es anual, verificar modalidad y que no exista ya un pago anual
        if data['tipo'] == 'anual':
            if data['inscripcion'].modalidad != 'anual':
                raise serializers.ValidationError("No se puede registrar pago anual para una inscripción mensual.")
            if Pago.objects.filter(inscripcion=data['inscripcion'], tipo='anual').exists():
                raise serializers.ValidationError("Ya existe un pago anual para esta inscripción.")
        return data

# Serializer para pago simple (un mes) con lógica cuota + donación
class PagoSimpleSerializer(serializers.Serializer):
    inscripcion_id = serializers.IntegerField()
    mes = serializers.IntegerField(min_value=1, max_value=12)
    anio = serializers.IntegerField()
    monto_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        cooperadora = self.context['request'].cooperadora

        try:
            inscripcion = Inscripcion.objects.get(
                id=data['inscripcion_id'], anio=data['anio'], cooperadora=cooperadora
            )
        except Inscripcion.DoesNotExist:
            raise serializers.ValidationError("Inscripción no encontrada para ese año.")

        if inscripcion.modalidad != 'mensual':
            raise serializers.ValidationError("La inscripción no es de modalidad mensual.")

        if Pago.objects.filter(inscripcion=inscripcion, tipo='mensual', mes=data['mes'], anio=data['anio']).exists():
            raise serializers.ValidationError("Ya existe un pago registrado para ese mes.")

        try:
            cuota = CuotaMensual.objects.get(
                anio=data['anio'], mes=data['mes'], activa=True, cooperadora=cooperadora
            )
        except CuotaMensual.DoesNotExist:
            raise serializers.ValidationError("No hay cuota definida para ese mes y año.")

        self.context['inscripcion'] = inscripcion
        self.context['cuota'] = cuota
        return data


# Serializer para el pago múltiple (varios meses)
class PagoMultipleSerializer(serializers.Serializer):
    inscripcion_id = serializers.IntegerField()
    meses = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=12))
    anio = serializers.IntegerField()
    monto_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_inscripcion_id(self, value):
        try:
            inscripcion = Inscripcion.objects.get(id=value)
        except Inscripcion.DoesNotExist:
            raise serializers.ValidationError("Inscripción no encontrada.")
        # Guardamos la inscripción en el contexto para usarla después
        self.context['inscripcion'] = inscripcion
        return value

    def validate(self, data):
        inscripcion = self.context.get('inscripcion')
        if not inscripcion:
            # Si no vino del validate_inscripcion_id, lo buscamos
            try:
                inscripcion = Inscripcion.objects.get(id=data['inscripcion_id'])
            except Inscripcion.DoesNotExist:
                raise serializers.ValidationError("Inscripción no encontrada.")

        # Validar que la inscripción sea del año indicado
        if inscripcion.anio != data['anio']:
            raise serializers.ValidationError("El año del pago debe coincidir con el año de la inscripción.")

        # Validar que la modalidad sea mensual
        if inscripcion.modalidad != 'mensual':
            raise serializers.ValidationError("La inscripción no es de modalidad mensual, no se pueden pagar meses sueltos.")

        # Validar que los meses tengan cuota definida (filtrado por cooperadora)
        cooperadora = self.context['request'].cooperadora
        cuotas = CuotaMensual.objects.filter(
            anio=data['anio'], mes__in=data['meses'], activa=True, cooperadora=cooperadora
        )
        if cuotas.count() != len(data['meses']):
            meses_faltantes = set(data['meses']) - set(cuotas.values_list('mes', flat=True))
            raise serializers.ValidationError(f"No hay cuota definida para los meses: {meses_faltantes}")

        # Guardar las cuotas en el contexto para no volver a consultar
        self.context['cuotas'] = cuotas
        self.context['inscripcion'] = inscripcion
        return data

class CuotaMensualSerializer(serializers.ModelSerializer):
    nombre_mes = serializers.SerializerMethodField()

    class Meta:
        model = CuotaMensual
        fields = ['id', 'anio', 'mes', 'nombre_mes', 'monto', 'activa']

    def get_nombre_mes(self, obj):
        return obj.get_mes_display()


class PublicacionImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicacionImagen
        fields = ['id', 'imagen', 'orden']


class PublicacionSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    imagenes = serializers.SerializerMethodField()

    class Meta:
        model = Publicacion
        fields = ['id', 'titulo', 'encabezado', 'contenido', 'tipo', 'imagen_portada', 'fecha', 'autor', 'autor_nombre', 'imagenes']
        read_only_fields = ['fecha', 'autor']

    def get_imagenes(self, obj):
        return PublicacionImagenSerializer(obj.imagenes.all(), many=True, context=self.context).data

    def get_autor_nombre(self, obj):
        if obj.autor:
            return f"{obj.autor.nombre} {obj.autor.apellido}"
        return None

    def create(self, validated_data):
        validated_data['autor'] = self.context['request'].user
        return super().create(validated_data)


class EstadoCuentaHijoSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    nombre = serializers.CharField()
    apellido = serializers.CharField()
    dni = serializers.CharField()
    inscripcion = serializers.SerializerMethodField()
    cuotas_pagas = serializers.SerializerMethodField()
    cuotas_pendientes = serializers.SerializerMethodField()
    donaciones = serializers.SerializerMethodField()

    def _get_inscripcion(self, obj):
        anio = self.context.get('anio')
        return obj.inscripciones.filter(anio=anio).first()

    def get_inscripcion(self, obj):
        ins = self._get_inscripcion(obj)
        if not ins:
            return None
        return {
            'id': ins.id,
            'grado': str(ins.grado),
            'anio': ins.anio,
            'modalidad': ins.modalidad,
        }

    def get_cuotas_pagas(self, obj):
        ins = self._get_inscripcion(obj)
        if not ins:
            return []
        pagos = ins.pagos.filter(tipo='mensual').order_by('mes')
        return [{'mes': p.mes, 'nombre_mes': p.get_mes_display(), 'monto': str(p.monto), 'fecha_pago': p.fecha_pago} for p in pagos]

    def get_cuotas_pendientes(self, obj):
        ins = self._get_inscripcion(obj)
        if not ins or ins.modalidad != 'mensual':
            return []
        anio = self.context.get('anio')
        meses_pagados = set(ins.pagos.filter(tipo='mensual', anio=anio).values_list('mes', flat=True))
        cuotas = CuotaMensual.objects.filter(anio=anio, activa=True).exclude(mes__in=meses_pagados).order_by('mes')
        meses_dict = dict(MESES_CICLO)
        return [{'mes': c.mes, 'nombre_mes': meses_dict.get(c.mes, ''), 'monto': str(c.monto)} for c in cuotas]

    def get_donaciones(self, obj):
        ins = self._get_inscripcion(obj)
        if not ins:
            return []
        pagos = ins.pagos.filter(tipo='donacion').order_by('-fecha_pago')
        return [{'monto': str(p.monto), 'fecha_pago': p.fecha_pago, 'observaciones': p.observaciones} for p in pagos]


# Serializer para pago anual (simple, con validación)
class PagoAnualSerializer(serializers.Serializer):
    inscripcion_id = serializers.IntegerField()
    anio = serializers.IntegerField()
    monto = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, data):
        try:
            inscripcion = Inscripcion.objects.get(id=data['inscripcion_id'], anio=data['anio'])
        except Inscripcion.DoesNotExist:
            raise serializers.ValidationError("Inscripción no encontrada para ese año.")

        if inscripcion.modalidad != 'anual':
            raise serializers.ValidationError("La inscripción no es de modalidad anual.")

        if Pago.objects.filter(inscripcion=inscripcion, tipo='anual').exists():
            raise serializers.ValidationError("Ya existe un pago anual para esta inscripción.")

        # Si no se envía monto, se busca en ConfiguracionAnual
        if 'monto' not in data or data['monto'] is None:
            try:
                config = ConfiguracionAnual.objects.get(anio=data['anio'], activa=True)
                data['monto'] = config.monto
            except ConfiguracionAnual.DoesNotExist:
                raise serializers.ValidationError("No hay configuración de pago anual para este año. Debe enviar el monto.")
        self.context['inscripcion'] = inscripcion
        return data