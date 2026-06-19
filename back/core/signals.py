import logging
import calendar
import urllib.request
from datetime import date
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='core.Cooperadora')
def _track_cooperadora_status(sender, instance, **kwargs):
    """Guarda el status anterior para que post_save pueda detectar la transición."""
    if not instance.pk:
        instance._prev_status = None
        return
    try:
        prev = sender.objects.get(pk=instance.pk)
        instance._prev_status = prev.subscription_status
    except sender.DoesNotExist:
        instance._prev_status = None


@receiver(post_save, sender='core.Cooperadora')
def provisionar_dao_clone(sender, instance, created, **kwargs):
    """
    Al activar una cooperadora (PENDING → TRIAL/ACTIVE) deploya un DAO clone via Factory
    y guarda el dao_address resultante. Solo actúa si dao_address todavía está vacío.
    """
    STATUS_CON_ACCESO = ('TRIAL', 'ACTIVE')
    prev = getattr(instance, '_prev_status', None)

    activando = (
        instance.subscription_status in STATUS_CON_ACCESO
        and prev not in STATUS_CON_ACCESO
        and not instance.dao_address
    )
    if not activando:
        return

    try:
        from core.web3_client import deploy_dao_clone
        ciclo_actual = date.today().year
        dao_address = deploy_dao_clone(instance.nombre, ciclo_actual)
        sender.objects.filter(pk=instance.pk).update(dao_address=dao_address)
        logger.info(
            "DAO clone deployado para cooperadora id=%s: %s",
            instance.pk, dao_address,
        )
    except Exception:
        logger.exception(
            "deploy_dao_clone falló para cooperadora id=%s — dao_address queda vacío",
            instance.pk,
        )


@receiver(post_save, sender='core.Usuario')
def generar_wallet_padre(sender, instance, created, **kwargs):
    if not created or instance.rol != 'PAD':
        return
    if instance.wallet_address:
        return
    if not instance.cooperadora or not instance.cooperadora.dao_address:
        logger.warning("No se puede registrar wallet: cooperadora sin dao_address para usuario id=%s", instance.pk)
        return
    try:
        from core.web3_client import generar_wallet, registrar_padre_en_dao
        address, encrypted_key = generar_wallet()
        sender.objects.filter(pk=instance.pk).update(
            wallet_address=address,
            wallet_private_key_encrypted=encrypted_key,
        )
        registrar_padre_en_dao(address, instance.cooperadora.dao_address)
    except Exception:
        logger.exception("generar_wallet/registrar_padre falló para usuario id=%s", instance.pk)


@receiver(post_save, sender='core.Pago')
def mint_token_on_pago(sender, instance, created, **kwargs):
    if not created or instance.token_minteado:
        return
    if instance.tipo == 'donacion':
        return
    try:
        from core.web3_client import mint_token_padre
        tx_hashes = mint_token_padre(instance)
        sender.objects.filter(pk=instance.pk).update(
            token_minteado=True,
            token_mint_tx=tx_hashes[0],  # guardamos el primer hash; los demás quedan en logs
        )
        if len(tx_hashes) > 1:
            logger.info("Pago anual id=%s: %d tokens minteados. Hashes: %s", instance.pk, len(tx_hashes), tx_hashes)
    except Exception:
        logger.exception("mint_token_padre falló para pago id=%s", instance.pk)


@receiver(post_save, sender='core.Pago')
def emitir_factura_on_pago(sender, instance, created, **kwargs):
    if not created or instance.factura_emitida:
        return
    cooperadora = instance.inscripcion.cooperadora
    if not cooperadora or not cooperadora.cuit or not cooperadora.afip_punto_venta:
        logger.warning(
            "Factura omitida para pago id=%s: cooperadora sin CUIT o punto_venta configurado",
            instance.pk,
        )
        return
    padre = instance.inscripcion.usuario.padre
    if not padre or not padre.cuil:
        logger.warning(
            "Factura omitida para pago id=%s: padre sin CUIL registrado",
            instance.pk,
        )
        return
    try:
        from core.facturacion import emitir_factura

        if instance.tipo == 'mensual' and instance.mes and instance.anio:
            serv_desde = date(instance.anio, instance.mes, 1)
            serv_hasta = date(instance.anio, instance.mes, calendar.monthrange(instance.anio, instance.mes)[1])
        elif instance.tipo == 'anual' and instance.anio:
            serv_desde = date(instance.anio, 1, 1)
            serv_hasta = date(instance.anio, 12, 31)
        else:
            serv_desde = serv_hasta = None

        if instance.tipo == 'mensual':
            descripcion = f"Cuota mensual — {instance.get_mes_display()} {instance.anio}"
        elif instance.tipo == 'anual':
            descripcion = f"Pago anual {instance.anio}"
        else:
            descripcion = "Donación cooperadora escolar"

        resultado = emitir_factura(
            cuit_emisor=cooperadora.cuit,
            punto_venta=cooperadora.afip_punto_venta,
            cuil_receptor=padre.cuil,
            monto=float(instance.monto),
            fecha_serv_desde=serv_desde,
            fecha_serv_hasta=serv_hasta,
            emisor_nombre=cooperadora.nombre,
            receptor_nombre=f"{padre.nombre} {padre.apellido}",
            descripcion=descripcion,
            email_receptor=padre.email or None,
        )
        sender.objects.filter(pk=instance.pk).update(
            factura_emitida=True,
            factura_numero=resultado["numero"],
            factura_cae=resultado["cae"],
            factura_vencimiento_cae=resultado["vencimiento_cae"],
        )
        # Compartir pdf_url con notificar_pago_padre via atributo temporal
        instance._pdf_url = resultado.get("pdf_url")
        instance._factura_numero = resultado["numero"]
        instance._factura_cae = resultado["cae"]
        logger.info(
            "Factura emitida para pago id=%s: N°%s CAE=%s",
            instance.pk, resultado["numero"], resultado["cae"],
        )
    except Exception:
        logger.exception("emitir_factura falló para pago id=%s", instance.pk)


@receiver(post_save, sender='core.Pago')
def notificar_pago_padre(sender, instance, created, **kwargs):
    if not created:
        return
    padre = instance.inscripcion.usuario.padre
    if not padre or not padre.email:
        return

    alumno = instance.inscripcion.usuario
    cooperadora = instance.inscripcion.cooperadora

    if instance.tipo == 'mensual':
        detalle = f"Cuota mensual — {instance.get_mes_display()} {instance.anio}"
    elif instance.tipo == 'anual':
        detalle = f"Pago anual {instance.anio}"
    else:
        detalle = f"Donación"

    try:
        pdf_url      = getattr(instance, '_pdf_url', None)
        nro_factura  = getattr(instance, '_factura_numero', None)
        cae          = getattr(instance, '_factura_cae', None)

        cuerpo = (
            f'Hola {padre.nombre},\n\n'
            f'Se registró un pago para {alumno.nombre} {alumno.apellido}:\n\n'
            f'  Concepto: {detalle}\n'
            f'  Monto: ${instance.monto}\n'
            f'  Fecha: {instance.fecha_pago.strftime("%d/%m/%Y")}\n'
        )
        if nro_factura and cae:
            cuerpo += f'  Factura C N°{nro_factura} — CAE: {cae}\n'

        cuerpo += f'\nGracias por tu pago.\n\n{cooperadora.nombre}'

        email = EmailMessage(
            subject=f'[{cooperadora.nombre}] Pago registrado',
            body=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[padre.email],
        )

        if pdf_url:
            try:
                with urllib.request.urlopen(pdf_url) as resp:
                    pdf_bytes = resp.read()
                nombre_archivo = f'factura_c_{nro_factura}.pdf'
                email.attach(nombre_archivo, pdf_bytes, 'application/pdf')
            except Exception:
                logger.warning("No se pudo adjuntar el PDF para pago id=%s", instance.pk)

        email.send(fail_silently=True)
    except Exception:
        logger.exception("notificar_pago_padre falló para pago id=%s", instance.pk)
