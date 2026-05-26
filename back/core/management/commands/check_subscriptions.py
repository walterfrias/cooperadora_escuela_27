from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from core.models import Cooperadora, SubscriptionStatus


AVISOS_DIAS = [30, 15, 7]


class Command(BaseCommand):
    help = 'Verifica suscripciones: notifica vencimientos próximos y marca vencidas las que expiraron.'

    def handle(self, *args, **options):
        hoy = timezone.now().date()

        # Marcar como EXPIRED las que vencieron
        expiradas = Cooperadora.objects.filter(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_expiry__lt=hoy,
        )
        count = expiradas.update(subscription_status=SubscriptionStatus.EXPIRED)
        if count:
            self.stdout.write(self.style.WARNING(f'{count} suscripción(es) marcada(s) como EXPIRED.'))

        expiradas_trial = Cooperadora.objects.filter(
            subscription_status=SubscriptionStatus.TRIAL,
            trial_until__lt=hoy,
        )
        count_trial = expiradas_trial.update(subscription_status=SubscriptionStatus.EXPIRED)
        if count_trial:
            self.stdout.write(self.style.WARNING(f'{count_trial} trial(s) marcado(s) como EXPIRED.'))

        # Notificar vencimientos próximos
        for dias in AVISOS_DIAS:
            fecha_objetivo = hoy + timedelta(days=dias)

            proximas_active = Cooperadora.objects.filter(
                subscription_status=SubscriptionStatus.ACTIVE,
                subscription_expiry=fecha_objetivo,
                email_contacto__gt='',
            )
            for coop in proximas_active:
                self._enviar_aviso(coop, dias, coop.subscription_expiry)

            proximas_trial = Cooperadora.objects.filter(
                subscription_status=SubscriptionStatus.TRIAL,
                trial_until=fecha_objetivo,
                email_contacto__gt='',
            )
            for coop in proximas_trial:
                self._enviar_aviso(coop, dias, coop.trial_until, es_trial=True)

        self.stdout.write(self.style.SUCCESS('check_subscriptions completado.'))

    def _enviar_aviso(self, coop, dias, fecha, es_trial=False):
        tipo = 'período de prueba' if es_trial else 'suscripción'
        send_mail(
            subject=f'[CooperaApp] Tu {tipo} vence en {dias} días',
            message=(
                f'Hola {coop.nombre_contacto},\n\n'
                f'Tu {tipo} en CooperaApp vence el {fecha.strftime("%d/%m/%Y")} '
                f'({dias} días).\n\n'
                f'Para renovar o consultar, respondé este email.\n\n'
                f'Saludos,\nEl equipo de CooperaApp'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[coop.email_contacto],
            fail_silently=True,
        )
        self.stdout.write(f'Aviso enviado a {coop.email_contacto} ({coop}) — vence en {dias} días.')
