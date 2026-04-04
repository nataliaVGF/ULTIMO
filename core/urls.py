from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings 

urlpatterns = [
    # 1. Pantalla de Bienvenida (Pública - Frase de bienvenida)
    path('', views.index, name='index'), 
    
    # 2. Pantalla Principal de Ventas (Privada - Solo con login)
    path('home/', views.home, name='home'),
    
    # 3. Registros y Login
    path('registro/', views.registro_seleccion, name='registro_seleccion'),
    path('registro/cliente/', views.registro_cliente, name='registro_cliente'),
    path('registro/vendedor/', views.registro_vendedor, name='registro_vendedor'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    
    # 4. Logout (Asegúrate de que esta ruta exista para el botón de cerrar sesión)
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('perfil/eliminar/', views.eliminar_cuenta, name='eliminar_cuenta'),
    
# 5. Recuperación de contraseña (AÑADE LA PRIMERA LÍNEA)
    path('reset_password/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html',
        email_template_name='core/password_reset_email.html',
        success_url='/reset_password_sent/'
    ), name='reset_password'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_sent.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'), name='password_reset_complete'),
    
    # 6. Activación de cuenta (Si decides implementar esta funcionalidad)
    path('activar/<uidb64>/<token>/', views.activar, name='activar'),
    
    # 7. Perfil de Usuario (Privada - Solo con login)
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/foto/', views.cambiar_foto, name='cambiar_foto'),
    path('perfil/password/', views.change_password, name='change_password'),
    path('perfil/vendedor/', views.solicitar_vendedor, name='solicitar_vendedor'),
    path('perfil/confirmar-email/', views.confirmar_email, name='confirmar_email'),
    path('perfil/mis-productos/', views.mis_productos, name='mis_productos'),
    path('mis-productos/agregar/', views.agregar_producto, name='agregar_producto'),
    
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)