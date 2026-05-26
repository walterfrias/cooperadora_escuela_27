from django.http import JsonResponse
from .models import Cooperadora


EXEMPT_PREFIXES = ('/admin/',)


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in EXEMPT_PREFIXES):
            return self.get_response(request)

        slug = request.headers.get('X-Tenant-Slug', '').strip().lower()

        if not slug:
            return JsonResponse({'detail': 'Header X-Tenant-Slug requerido.'}, status=400)

        try:
            cooperadora = Cooperadora.objects.get(slug=slug)
        except Cooperadora.DoesNotExist:
            return JsonResponse({'detail': 'Cooperadora no encontrada.'}, status=404)

        if not cooperadora.tiene_acceso:
            return JsonResponse({'detail': 'Suscripción inactiva o vencida.'}, status=403)

        request.cooperadora = cooperadora
        return self.get_response(request)
