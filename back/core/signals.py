import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


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
