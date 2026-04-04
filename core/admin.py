from django.contrib import admin
from .models import Perfil
from .models import Producto

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    # Usamos 'get_user' para mostrar el nombre completo en lugar de solo el objeto
    list_display = ('get_user', 'rol', 'numero_control', 'contacto')
    list_filter = ('rol', 'edificio')
    search_fields = ('user__username', 'numero_control', 'user__first_name')

    # Función personalizada para que en la lista aparezca el nombre del alumno
    def get_user(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"
    
    get_user.short_description = 'Estudiante' # Título de la columna
    
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Columnas que verás en la lista
    list_display = ('nombre', 'vendedor', 'tipo', 'precio', 'estado', 'fecha_creacion')
    
    # Filtros laterales para encontrar rápido lo pendiente
    list_filter = ('estado', 'tipo', 'fecha_creacion')
    
    # Permitir editar el estado directamente desde la lista
    list_editable = ('estado',)
    
    # Buscador por nombre de producto o nombre del vendedor
    search_fields = ('nombre', 'vendedor__username')    
    
    
    