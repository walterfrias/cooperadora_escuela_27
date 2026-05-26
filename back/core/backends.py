from .models import Usuario


class TenantAuthBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = Usuario.objects.get(email=username)
        except Usuario.DoesNotExist:
            return None

        if not user.check_password(password):
            return None

        if not user.activo:
            return None

        # Platform admin no tiene cooperadora — puede loguear desde /admin/ sin tenant
        if user.is_superuser and user.cooperadora is None:
            return user

        # Usuario regular: debe pertenecer a la cooperadora del request
        if not request or not hasattr(request, 'cooperadora'):
            return None

        if user.cooperadora != request.cooperadora:
            return None

        return user

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
