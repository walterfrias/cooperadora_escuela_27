"""
Integración con AFIP via AFIPSDK (afip.py).
Requiere en .env: AFIPSDK_ACCESS_TOKEN
En test (sin certificado) usa el CUIT de prueba 20-40937847-2 automáticamente.
En producción, pasar AFIPSDK_CERT_PATH y AFIPSDK_KEY_PATH por cooperadora.
"""

import calendar
import datetime
from django.conf import settings
from afip import Afip

TIPO_FACTURA_C         = 11  # Monotributistas / cooperadoras escolares
CONCEPTO_SERVICIO      = 2   # Servicios
DOC_TIPO_DNI           = 96
CONDICION_IVA_CONS_FIN = 5   # Consumidor Final (RG 5616)


def _get_client(cuit_emisor: str) -> Afip:
    cuit_num = int(cuit_emisor.replace("-", ""))
    config = {
        "CUIT": cuit_num,
        "access_token": settings.AFIPSDK_ACCESS_TOKEN,
    }
    cert_path = getattr(settings, "AFIPSDK_CERT_PATH", None)
    key_path  = getattr(settings, "AFIPSDK_KEY_PATH",  None)
    if cert_path and key_path:
        with open(cert_path) as f:
            config["cert"] = f.read()
        with open(key_path) as f:
            config["key"] = f.read()
    return Afip(config)


def _fmt_afip(d: datetime.date) -> int:
    return int(d.strftime("%Y%m%d"))


def _fmt_pdf(d: datetime.date) -> str:
    return d.strftime("%d/%m/%Y")


def emitir_factura(
    cuit_emisor: str,
    punto_venta: int,
    cuil_receptor: str,
    monto: float,
    fecha_serv_desde: datetime.date = None,
    fecha_serv_hasta: datetime.date = None,
    emisor_nombre: str = "",
    receptor_nombre: str = "",
    descripcion: str = "Cuota cooperadora escolar",
    email_receptor: str = None,
) -> dict:
    """
    Emite una Factura C en AFIP, genera el PDF y lo envía al padre por email.
    Devuelve {'numero', 'cae', 'vencimiento_cae', 'pdf_url'}.
    """
    afip = _get_client(cuit_emisor)

    last   = afip.ElectronicBilling.getLastVoucher(punto_venta, TIPO_FACTURA_C)
    next_n = last + 1
    hoy    = datetime.date.today()

    if fecha_serv_desde is None:
        fecha_serv_desde = hoy.replace(day=1)
    if fecha_serv_hasta is None:
        fecha_serv_hasta = hoy.replace(day=calendar.monthrange(hoy.year, hoy.month)[1])

    cuit_num = int(cuit_emisor.replace("-", ""))

    # ── Emitir comprobante ────────────────────────────────────────────────────
    voucher_data = {
        "CantReg":              1,
        "PtoVta":               punto_venta,
        "CbteTipo":             TIPO_FACTURA_C,
        "Concepto":             CONCEPTO_SERVICIO,
        "DocTipo":              DOC_TIPO_DNI,
        "DocNro":               int(cuil_receptor.replace("-", "")),
        "CbteDesde":            next_n,
        "CbteHasta":            next_n,
        "CbteFch":              _fmt_afip(hoy),
        "FchServDesde":         _fmt_afip(fecha_serv_desde),
        "FchServHasta":         _fmt_afip(fecha_serv_hasta),
        "FchVtoPago":           _fmt_afip(hoy),
        "ImpTotal":             round(monto, 2),
        "ImpTotConc":           0,
        "ImpNeto":              round(monto, 2),
        "ImpOpEx":              0,
        "ImpIVA":               0,
        "ImpTrib":              0,
        "MonId":                "PES",
        "MonCotiz":             1,
        "CondicionIVAReceptorId": CONDICION_IVA_CONS_FIN,
    }

    res         = afip.ElectronicBilling.createVoucher(voucher_data, False)
    cae         = res["CAE"]
    vencimiento = datetime.date.fromisoformat(str(res["CAEFchVto"]))

    # ── Generar PDF y enviarlo al padre ───────────────────────────────────────
    pdf_url = None
    try:
        pdf_data = {
            "file_name": f"factura_c_{punto_venta:05d}_{next_n:08d}.pdf",
            "template": {
                "name": "invoice-c",
                "params": {
                    "voucher_number":           next_n,
                    "sales_point":              punto_venta,
                    "issue_date":               _fmt_pdf(hoy),
                    "cae":                      cae,
                    "cae_due_date":             _fmt_pdf(vencimiento),
                    "issuer_cuit":              cuit_num,
                    "issuer_business_name":     emisor_nombre or cuit_emisor,
                    "issuer_address":           "-",
                    "issuer_iva_condition":     "Monotributista",
                    "issuer_gross_income":      "-",
                    "issuer_activity_start_date": "01/01/2024",
                    "receiver_name":            receptor_nombre or "Consumidor Final",
                    "receiver_address":         "-",
                    "receiver_document_type":   DOC_TIPO_DNI,
                    "receiver_document_number": int(cuil_receptor.replace("-", "")),
                    "receiver_iva_condition":   "Consumidor Final",
                    "sale_condition":           "Contado",
                    "concept":                  CONCEPTO_SERVICIO,
                    "currency_id":              "ARS",
                    "currency_rate":            1,
                    "items": [{
                        "code":       "001",
                        "description": descripcion,
                        "quantity":   1,
                        "unit_price": round(monto, 2),
                        "subtotal":   round(monto, 2),
                    }],
                    "net_amount_taxed":   round(monto, 2),
                    "net_amount_untaxed": 0,
                    "exempt_amount":      0,
                    "vat_amount":         0,
                    "tributes_amount":    0,
                    "total_amount":       round(monto, 2),
                    "billing_from":       _fmt_pdf(fecha_serv_desde),
                    "billing_to":         _fmt_pdf(fecha_serv_hasta),
                    "payment_due_date":   _fmt_pdf(hoy),
                },
            },
        }

        if email_receptor:
            pdf_data["send_to"] = email_receptor

        pdf_res = afip.ElectronicBilling.createPDF(pdf_data)
        pdf_url = pdf_res.get("file")
    except Exception:
        import logging
        logging.getLogger(__name__).exception("createPDF falló para factura N°%s", next_n)

    return {
        "numero":          next_n,
        "cae":             cae,
        "vencimiento_cae": vencimiento,
        "pdf_url":         pdf_url,
    }
