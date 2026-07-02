# core/permissions.py
from rest_framework import permissions

class EsTesoreroOAdmin(permissions.BasePermission):
    """
    Permiso que solo concede acceso a usuarios con rol 'TES' (Tesorero) o 'ADMIN' (Administrador).
    """
    def has_permission(self, request, view):
        # Verificar que el usuario esté autenticado
        if not request.user.is_authenticated:
            return False
        # Verificar el rol
        return request.user.rol in ['TES', 'ADMIN']


class EsTesoreroAdminOPresidente(permissions.BasePermission):
    """
    Como EsTesoreroOAdmin, pero además habilita al Presidente ('PRES').
    El Presidente tiene el mismo acceso que el Tesorero salvo para registrar pagos
    (esa acción sigue usando EsTesoreroOAdmin).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.rol in ['TES', 'ADMIN', 'PRES']


class EsSecretarioOAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.rol in ['SEC', 'ADMIN']