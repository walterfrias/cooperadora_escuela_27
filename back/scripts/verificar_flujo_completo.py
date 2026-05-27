"""
Verificación end-to-end del flujo multi-tenant con Clone Factory.

Pasos que ejecuta este script:
  1. Activa una cooperadora (PENDING → TRIAL) y verifica que el signal
     despliega un DAO clone y guarda el dao_address.
  2. Crea un usuario PAD en esa cooperadora y verifica que se genera
     una wallet y se registra en el clone correcto.
  3. Crea un pago mensual para ese padre y verifica que se mintea
     1 token COOP en Base Sepolia.
  4. Limpia los datos de prueba creados.

Uso (desde back/):
    python scripts/verificar_flujo_completo.py

Requiere que .env.saas tenga FACTORY_CONTRACT_ADDRESS y PRESIDENTE_PLATFORM_ADDRESS.
"""

import os
import sys
import django
from pathlib import Path

# ── Setup Django ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from datetime import timedelta, date
from core.models import Cooperadora, Usuario, Grado, Inscripcion, Pago, SubscriptionStatus
from core.web3_client import _get_factory, FACTORY_ADDRESS, PRESIDENTE_PLATFORM


# ── Helpers visuales ────────────────────────────────────────────────────────

def ok(msg):
    print(f"  ✓ {msg}")

def fail(msg):
    print(f"  ✗ {msg}")
    sys.exit(1)

def step(n, msg):
    print(f"\n[{n}] {msg}")


# ── Precondiciones ──────────────────────────────────────────────────────────

def verificar_configuracion():
    step("0", "Verificando configuración web3")

    if not FACTORY_ADDRESS:
        fail("FACTORY_CONTRACT_ADDRESS no está en .env.saas")
    ok(f"Factory: {FACTORY_ADDRESS}")

    if not PRESIDENTE_PLATFORM:
        fail("PRESIDENTE_PLATFORM_ADDRESS no está en .env.saas")
    ok(f"Presidente platform: {PRESIDENTE_PLATFORM}")

    w3, factory = _get_factory()
    chain_id = w3.eth.chain_id
    if chain_id != 84532:
        fail(f"chainId inesperado: {chain_id} (esperado 84532 = Base Sepolia)")
    ok(f"Conectado a Base Sepolia (chainId {chain_id})")

    owner = factory.functions.owner().call()
    ok(f"Factory owner: {owner}")


# ── Paso 1: Activar cooperadora y provisionar DAO clone ────────────────────

def paso1_activar_cooperadora():
    step("1", "Activar cooperadora → signal despliega DAO clone")

    NOMBRE = "Cooperadora Verificacion Test"
    SLUG   = "verificacion-test-script"

    # Limpiar si quedó de una ejecución anterior
    Cooperadora.objects.filter(slug=SLUG).delete()

    # Crear en PENDING (sin acceso, sin DAO)
    coop = Cooperadora.objects.create(
        numero_escuela=9999,
        nombre=NOMBRE,
        slug=SLUG,
        subscription_status=SubscriptionStatus.PENDING,
    )
    ok(f"Cooperadora creada id={coop.pk}, status=PENDING, dao_address='{coop.dao_address}'")

    # Activar: PENDING → TRIAL dispara el signal provisionar_dao_clone
    coop.subscription_status = SubscriptionStatus.TRIAL
    coop.trial_until = date.today() + timedelta(days=30)
    print("    Guardando (esto hace un deploy en Base Sepolia, ~15 seg)...")
    coop.save()

    coop.refresh_from_db()
    if not coop.dao_address:
        fail("dao_address vacío después de activar. Revisar logs de Django.")
    ok(f"DAO clone deployado: {coop.dao_address}")

    return coop


# ── Paso 2: Crear PAD → wallet generada y registrada en el clone ────────────

def paso2_crear_padre(coop):
    step("2", "Crear PAD → wallet generada y registrada en clone DAO")

    EMAIL = "padre_verificacion_script@test.local"
    Usuario.objects.filter(email=EMAIL).delete()

    print("    Creando usuario PAD (genera wallet y la registra en DAO, ~10 seg)...")
    padre = Usuario.objects.create_user(
        email=EMAIL,
        password="test1234",
        nombre="Padre",
        apellido="Script",
        dni="00000001",
        rol="PAD",
        cooperadora=coop,
    )

    padre.refresh_from_db()

    if not padre.wallet_address:
        fail("wallet_address vacío después de crear PAD.")
    ok(f"Wallet generada: {padre.wallet_address}")

    if not padre.wallet_private_key_encrypted:
        fail("wallet_private_key_encrypted vacío.")
    ok("Private key encriptada guardada en DB")

    return padre


# ── Paso 3: Registrar pago → mintear 1 token COOP ──────────────────────────

def paso3_registrar_pago(coop, padre):
    step("3", "Registrar pago mensual → mintear 1 token COOP")

    # Necesitamos un Grado y una Inscripcion para poder crear un Pago
    grado, _ = Grado.objects.get_or_create(numero=1, letra="A")

    Inscripcion.objects.filter(usuario=padre, anio=2026).delete()
    inscripcion = Inscripcion.objects.create(
        usuario=padre,
        grado=grado,
        anio=2026,
        modalidad="mensual",
        activa=True,
    )
    ok(f"Inscripcion creada id={inscripcion.pk}")

    print("    Creando pago (mintea token en Base Sepolia, ~15 seg)...")
    pago = Pago.objects.create(
        inscripcion=inscripcion,
        cooperadora=coop,
        tipo="mensual",
        mes=5,
        anio=2026,
        monto=500,
        fecha_pago=date.today(),
    )

    pago.refresh_from_db()

    if not pago.token_minteado:
        fail("token_minteado=False después de crear el pago. Revisar logs.")
    ok(f"Token minteado. TX hash: {pago.token_mint_tx}")

    return pago


# ── Paso 4: Limpieza ────────────────────────────────────────────────────────

def paso4_limpiar(coop, padre, pago):
    step("4", "Limpieza de datos de prueba")

    Pago.objects.filter(pk=pago.pk).delete()
    ok("Pago eliminado")

    Inscripcion.objects.filter(usuario=padre).delete()
    ok("Inscripcion eliminada")

    Usuario.objects.filter(pk=padre.pk).delete()
    ok("Usuario PAD eliminado")

    # La cooperadora la dejamos para poder inspeccionar el dao_address en admin
    print(f"\n  La cooperadora '{coop.nombre}' (slug={coop.slug}) queda en DB")
    print(f"  dao_address: {coop.dao_address}")
    print("  Podés eliminarla desde el admin si querés.")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("\n══════════════════════════════════════════")
    print("  Verificación end-to-end Clone Factory")
    print("══════════════════════════════════════════")

    verificar_configuracion()
    coop  = paso1_activar_cooperadora()
    padre = paso2_crear_padre(coop)
    pago  = paso3_registrar_pago(coop, padre)
    paso4_limpiar(coop, padre, pago)

    print("\n══════════════════════════════════════════")
    print("  Todo OK — flujo verificado end-to-end")
    print("══════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
