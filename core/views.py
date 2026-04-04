from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import RegistroClienteForm, RegistroVendedorForm
from .models import Perfil, Producto

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib.auth.tokens import default_token_generator

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError # Importante para capturar duplicados

from django.contrib.auth import update_session_auth_hash
import random # Para generar un código de 6 dígitos
from django.core.mail import send_mail

from django.contrib.auth import logout

from django.shortcuts import get_object_or_404
from django.db.models import Avg
from .models import Resena

# 1. PANTALLA DE BIENVENIDA (Pública)
# Esta es la que tiene la frase y botones de "Registrar" o "Loguear"
def index(request):
    # Si el usuario ya está logueado, lo mandamos directo al Home
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/index.html')

# 2. PANTALLA PRINCIPAL DE VENTAS (Privada)
# Solo accesible tras hacer login
def home(request):
    # Usamos fecha_creacion que es el nombre real en tu modelo
    productos = Producto.objects.filter(estado='aprobado').order_by('-fecha_creacion')
    return render(request, 'core/home.html', {'productos': productos})

def registro_seleccion(request):
    return render(request, 'core/registro_seleccion.html')

def login_view(request):
    if request.method == 'POST':
        nombre_usuario = request.POST.get('username')
        clave = request.POST.get('password')
        
        # 1. Autenticamos al usuario
        user = authenticate(request, username=nombre_usuario, password=clave)
        
        if user is not None:
            if user.is_active:
                # Si es válido y está activo, entra al sistema
                login(request, user)
                return redirect('home')
            else:
                # Si existe pero NO está activo
                messages.warning(request, "Tu cuenta aún no ha sido activada. Por favor, revisa tu correo electrónico.")
        else:
            # Si las credenciales son incorrectas
            messages.error(request, "Usuario o contraseña incorrectos.")
            
    return render(request, 'core/login.html')


def registro_cliente(request):
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            correo = form.cleaned_data.get('email')
            user.username = correo 
            user.email = correo
            
            # --- OBLIGATORIO PARA FLUJO DE ACTIVACIÓN ---
            user.is_active = False 
            
            user.set_password(form.cleaned_data['password'])
            user.first_name = form.cleaned_data['nombre']
            user.last_name = form.cleaned_data['apellidos']
            
            try:
                user.save()
                Perfil.objects.create(
                    user=user,
                    rol='cliente',
                    foto=form.cleaned_data.get('foto'),
                    numero_control=form.cleaned_data.get('numero_control')
                )

                # Intentamos enviar el correo
                try:
                    enviar_correo_activacion(request, user)
                except Exception as e:
                    print(f"Error enviando correo: {e}") 
                    # Aún si falla el correo, redirigimos para que el usuario sepa qué pasó
                
                # ESTA LÍNEA ES LA QUE LANZA LA PANTALLA DE "REVISA TU CORREO"
                return render(request, 'core/confirmar_envio.html')

            except IntegrityError:
                form.add_error('email', "Este correo ya está registrado.")
        else:
            # Si el formulario no es válido (ej. contraseña corta), imprimimos en consola
            print(form.errors) 
    else:
        form = RegistroClienteForm()

    return render(request, 'core/registro_cliente.html', {'form': form})


def enviar_correo_activacion(request, user):
    current_site = get_current_site(request)
    subject = 'Activa tu cuenta en StuMarket'
    
    # Renderizamos el HTML que me pasaste
    message = render_to_string('core/email_activacion.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    
    email = EmailMessage(
        subject,
        message,
        to=[user.email],
    )
    
    # Si esto falla, te mostrará el error real de Gmail en la terminal
    email.send(fail_silently=False)

def registro_vendedor(request):
    if request.method == 'POST':
        form = RegistroVendedorForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            
            # --- CRUCIAL: Asignar identificadores ---
            correo = form.cleaned_data.get('email')
            user.username = correo  # Sin esto, fallará el UNIQUE constraint
            user.email = correo
            
            user.is_active = False  # Activo para pruebas en la UTNG
            
            # --- ENCRIPTACIÓN ---
            user.set_password(form.cleaned_data['password'])
            
            user.first_name = form.cleaned_data['nombre']
            user.last_name = form.cleaned_data['apellidos']
            
            try:
                user.save()
                
                # Guardamos los datos del perfil del vendedor con sus campos específicos
                Perfil.objects.create(
                    user=user,
                    rol='vendedor',
                    foto=form.cleaned_data.get('foto'),
                    numero_control=form.cleaned_data.get('numero_control'),
                    grupo=form.cleaned_data.get('grupo'),
                    contacto=form.cleaned_data.get('telefono'), # Asegúrate que el modelo tenga 'contacto'
                    edificio=form.cleaned_data.get('edificio'),
                    casillero=form.cleaned_data.get('casillero')
                )
                
                # Intento de envío de correo (si falla el SMTP, el registro sigue vivo)
                try:
                    enviar_correo_activacion(request, user)
                except Exception:
                    pass 
                
                return render(request, 'core/confirmar_envio.html')

            except IntegrityError:
                # Manejo de error si el correo ya existe en la base de datos
                form.add_error('email', "Este correo electrónico ya está registrado como vendedor o cliente.")
            except Exception as e:
                form.add_error(None, f"Error inesperado: {e}")
    else:
        form = RegistroVendedorForm()
        
    return render(request, 'core/registro_vendedor.html', {'form': form})


def activar(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('login') # Ahora ya puede loguearse
    else:
        return render(request, 'core/activacion_invalida.html')
    
@login_required
def perfil_view(request):
    return render(request, 'core/perfil.html')

def editar_perfil(request):
    return redirect('perfil')

def cambiar_foto(request):
    return redirect('perfil')

def change_password(request):
    return redirect('perfil')

def solicitar_vendedor(request):
    return redirect('perfil')

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        user = request.user
        nuevo_nombre = request.POST.get('first_name')
        nuevo_apellido = request.POST.get('last_name')
        nuevo_correo = request.POST.get('email')

        # 1. Lógica del Correo (Verificación)
        if nuevo_correo and nuevo_correo != user.email:
            # Aquí podrías enviar un correo real con un token
            user.email = nuevo_correo
            user.perfil.email_verificado = False
            user.perfil.save()
            messages.warning(request, "Correo actualizado. Por favor, verifica tu bandeja de entrada.")
        
        # 2. Actualizar nombres
        user.first_name = nuevo_nombre
        user.last_name = nuevo_apellido
        user.save()
        
        messages.success(request, "Datos actualizados correctamente.")
    return redirect('perfil')

@login_required
def cambiar_foto(request):
    if request.method == 'POST' and request.FILES.get('foto'):
        perfil = request.user.perfil
        perfil.foto = request.FILES['foto']
        perfil.save()
        messages.success(request, "Foto de perfil actualizada.")
    return redirect('perfil')

@login_required
def change_password(request):
    if request.method == 'POST':
        old_pass = request.POST.get('old_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')

        if request.user.check_password(old_pass):
            if new_pass == confirm_pass:
                request.user.set_password(new_pass)
                request.user.save()
                # Importante para que no se cierre la sesión al cambiar pass
                update_session_auth_hash(request, request.user)
                messages.success(request, "Contraseña cambiada con éxito.")
            else:
                messages.error(request, "Las nuevas contraseñas no coinciden.")
        else:
            messages.error(request, "La contraseña actual es incorrecta.")
    return redirect('perfil')

@login_required
def perfil_view(request):
    # Aseguramos que el usuario tenga un perfil (por si acaso no se creó en el registro)
    perfil, created = Perfil.objects.get_or_create(user=request.user)
    return render(request, 'core/perfil.html')

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        user = request.user
        nuevo_correo = request.POST.get('email')
        
        # SI EL CORREO ES DIFERENTE AL ACTUAL
        if nuevo_correo and nuevo_correo != user.email:
            # 1. Generamos un código aleatorio
            codigo = str(random.randint(100000, 999999))
            
            # 2. Guardamos los datos temporalmente en la SESIÓN (no en la BD aún)
            request.session['temp_email'] = nuevo_correo
            request.session['verif_code'] = codigo
            
            # 3. Enviamos el correo (Configura tu SMTP en settings.py)
            send_mail(
                'Código de Verificación StuMarket',
                f'Tu código para cambiar de correo es: {codigo}',
                'noreply@stumarket.com',
                [nuevo_correo],
                fail_silently=False,
            )
            
            # 4. EN LUGAR DE REDIRECT A PERFIL, VAMOS A LA PANTALLA DE CÓDIGO
            return render(request, 'core/verificar_codigo.html', {'email': nuevo_correo})

        # Si el correo no cambió, solo actualizamos nombres
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()
        messages.success(request, "Datos actualizados.")
        
    return redirect('perfil')

@login_required
def cambiar_foto(request):
    if request.method == 'POST' and request.FILES.get('foto'):
        perfil = request.user.perfil
        perfil.foto = request.FILES['foto']
        perfil.save()
        messages.success(request, "¡Foto de perfil actualizada con éxito!")
    return redirect('perfil')

@login_required
def change_password(request):
    if request.method == 'POST':
        old_pass = request.POST.get('old_password')
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')

        # Validar contraseña actual
        if not request.user.check_password(old_pass):
            messages.error(request, "La contraseña actual es incorrecta.")
            return redirect('perfil')

        # Validar coincidencia
        if new_pass != confirm_pass:
            messages.error(request, "Las nuevas contraseñas no coinciden.")
            return redirect('perfil')
        
        # Validar longitud mínima (opcional pero recomendado)
        if len(new_pass) < 8:
            messages.error(request, "La nueva contraseña debe tener al menos 8 caracteres.")
            return redirect('perfil')

        # Guardar nueva contraseña
        request.user.set_password(new_pass)
        request.user.save()
        
        # MANTENER LA SESIÓN ACTIVA: Evita que Django desloguee al usuario
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Contraseña actualizada correctamente.")
    
    return redirect('perfil')

@login_required
def solicitar_vendedor(request):
    if request.method == 'POST':
        perfil = request.user.perfil
        
        # Capturamos los datos del formulario
        perfil.contacto = request.POST.get('telefono')
        perfil.numero_control = request.POST.get('numero_control')
        perfil.grupo = request.POST.get('grupo')
        perfil.edificio = request.POST.get('edificio')
        perfil.casillero = request.POST.get('casillero')
        # Si decides añadir un campo 'direccion' al modelo Perfil:
        # perfil.direccion = request.POST.get('direccion') 
        
        # Cambiamos el rol y guardamos
        perfil.rol = 'vendedor'
        perfil.save()
        
        messages.success(request, "¡Felicidades! Ya eres vendedor. Ahora puedes gestionar tus productos.")
        return redirect('home') # Redirigimos al home para que vea el nuevo menú
    
    return redirect('perfil')

@login_required
def confirmar_email(request):
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo_ingresado')
        codigo_real = request.session.get('verif_code')
        nuevo_email = request.session.get('temp_email')
        
        if codigo_ingresado == codigo_real:
            # SI EL CÓDIGO COINCIDE, AHORA SÍ ACTUALIZAMOS LA BD
            user = request.user
            user.email = nuevo_email
            user.save()
            
            # Limpiamos la sesión
            del request.session['verif_code']
            del request.session['temp_email']
            
            messages.success(request, "¡Correo verificado y actualizado con éxito!")
            return redirect('perfil')
        else:
            messages.error(request, "El código es incorrecto. Inténtalo de nuevo.")
            return render(request, 'core/verificar_codigo.html', {'email': nuevo_email})
            
    return redirect('perfil')

# core/views.py

@login_required
def mis_productos(request):
    # Obtenemos solo los productos que pertenecen al usuario actual
    productos = request.user.productos.all() 
    return render(request, 'core/mis_productos.html', {'productos': productos})

@login_required
def mis_productos(request):
    # Filtrar solo los productos del usuario actual
    productos_vendedor = Producto.objects.filter(vendedor=request.user)
    return render(request, 'core/mis_productos.html', {
        'productos': productos_vendedor
    })

@login_required
def agregar_producto(request):
    if request.method == 'POST':
        # Procesar teléfono
        opcion_tel = request.POST.get('phone_option')
        telefono_final = request.POST.get('otro_telefono') if opcion_tel == 'otro' else opcion_tel
        
        # Crear producto pero NO publicar (estado pendiente por defecto)
        nuevo_p = Producto(
            vendedor=request.user,
            nombre=request.POST.get('nombre'),
            tipo=request.POST.get('tipo'),
            precio=request.POST.get('precio'),
            descripcion=request.POST.get('descripcion', ''),
            imagen=request.FILES.get('imagen'),
            ubicacion_externa=request.POST.get('ubicacion_url'),
            telefono_contacto=telefono_final,
            estado='pendiente' # Importante
        )
        nuevo_p.save()
        
        messages.success(request, "Publicación enviada. Un administrador la revisará pronto.")
        return redirect('mis_productos')
        
    return render(request, 'core/agregar_producto.html')


@login_required
def eliminar_cuenta(request):
    if request.method == 'POST':
        user = request.user
        password_confirm = request.POST.get('password_confirm')
        
        # Verificamos que la contraseña sea correcta
        if user.check_password(password_confirm):
            # Opcional: Aquí podrías eliminar imágenes de la carpeta media si quisieras
            user.delete() 
            logout(request)
            messages.success(request, "Tu cuenta ha sido eliminada. Lamentamos verte partir.")
            return redirect('home')
        else:
            messages.error(request, "La contraseña es incorrecta. No se pudo eliminar la cuenta.")
            return redirect('perfil')
            
    return redirect('perfil')

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    resenas = producto.resenas.all()
    
    # Promedio del producto
    promedio_producto = resenas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    
    # Promedio del vendedor (de todos sus productos)
    promedio_vendedor = Resena.objects.filter(producto__vendedor=producto.vendedor).aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    
    context = {
        'producto': producto,
        'resenas': resenas,
        'promedio_producto': promedio_producto,
        'promedio_vendedor': promedio_vendedor,
        'total_resenas': resenas.count(),
    }
    return render(request, 'core/detalle_producto.html', context)