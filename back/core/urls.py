from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import RegistroCooperadoraView, ActivarCooperadoraView, CooperadoraInfoView

# Router para los ViewSets
router = DefaultRouter()
router.register(r'grados', views.GradoViewSet, basename='grado')
router.register(r'inscripciones', views.InscripcionViewSet, basename='inscripcion')
router.register(r'pagos', views.PagoViewSet, basename='pago')
router.register(r'publicaciones', views.PublicacionViewSet, basename='publicacion')
router.register(r'cuotas', views.CuotaMensualViewSet, basename='cuota')

urlpatterns = [
    path('register/', RegistroCooperadoraView.as_view(), name='registro-cooperadora'),
    path('activar/<uuid:token>/', ActivarCooperadoraView.as_view(), name='activar-cooperadora'),
    path('cooperadora-info/<slug:slug>/', CooperadoraInfoView.as_view(), name='cooperadora-info'),
    path('usuarios/crear/', views.CrearUsuarioView.as_view(), name='crear-usuario'),
    path('login/', views.UsuarioLoginView.as_view(), name='login'),
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario-list'),
    path('usuarios/<uuid:uuid>/', views.UsuarioDetailView.as_view(), name='usuario-detail'),
    path('mis-hijos/', views.MisHijosView.as_view(), name='mis-hijos'),
    path('estado-cuenta/', views.EstadoCuentaView.as_view(), name='estado-cuenta'),
    path('me/', views.MeView.as_view(), name='me'),
    path('mi-wallet/', views.MiWalletView.as_view(), name='mi-wallet'),
    path('cambiar-password/', views.CambiarPasswordView.as_view(), name='cambiar-password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]

# Agregamos las rutas del router
urlpatterns += router.urls