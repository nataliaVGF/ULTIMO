from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

# Extendemos la información del usuario
class Perfil(models.Model):
    ROLES = (
        ('cliente', 'Cliente'),
        ('vendedor', 'Vendedor'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=10, choices=ROLES, null=True, blank=True)
    foto = models.ImageField(upload_to='perfiles/', null=True, blank=True)
    numero_control = models.CharField(max_length=20, unique=True, null=True, blank=True)
    grupo = models.CharField(max_length=10, null=True, blank=True)
    contacto = models.CharField(max_length=15, unique=True, null=True, blank=True)
    edificio = models.CharField(max_length=20, null=True, blank=True)
    casillero = models.CharField(max_length=10, null=True, blank=True)
    email_verificado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.rol}"

# Modelo del Producto
class Producto(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente de aprobación'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    )
    TIPO = (
        ('producto', 'Producto'),
        ('servicio', 'Servicio'),
    )

    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=10, choices=TIPO, default='producto')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    ubicacion_externa = models.CharField(max_length=255, null=True, blank=True)
    telefono_contacto = models.CharField(max_length=15)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Corregido: Usamos self.resenas directamente
    @property
    def promedio_calificacion(self):
        promedio = self.resenas.aggregate(Avg('calificacion'))['calificacion__avg']
        return round(promedio, 1) if promedio else 0

    def __str__(self):
        return f"{self.nombre} ({self.vendedor.username})"

class Resena(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    calificacion = models.IntegerField(default=5) # 1 a 5
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre} ({self.calificacion}★)"

class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mis_favoritos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)                                                                                                                                                                                                                         