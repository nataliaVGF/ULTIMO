from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import RegistroClienteForm, RegistroVendedorForm
from .models import Perfil, Producto,Favorito
from django.db.models import Q ##busqueda potente

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
from django.db.models import Avg,Count
from .models import Resena

# 1. PANTALLA DE BIENVENIDA (Pública)
# Esta es la que tiene la frase y botones de "Registrar" o "Loguear"
def index(request):
    # Si el usuario ya está logueado, lo mandamos directo al Home
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/index.html')

# 2. PANTALLA PRINCIPAL DE VENTAS (Privada)
def home(request):
    query = request.GET.get('q')

    # --- 1. ESTA ES LA ÚNICA QUE SE FILTRA ---
    # Creamos una query base para las publicaciones generales
    publicaciones = Producto.objects.filter(estado='aprobado')
    
    if query:
        publicaciones = publicaciones.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query)
        )
    
    # Aplicamos el orden por fecha
    productos = publicaciones.order_by('-fecha_creacion')


    # --- 2. EL RESTO SE QUEDA IGUAL (SIN FILTRAR POR BÚSQUEDA) ---
    
    # Populares: siempre los mismos (basados en calificación global)
    productos_populares = Producto.objects.filter(
        estado='aprobado', 
        tipo='producto'
    ).annotate(
        promedio=Avg('resenas__calificacion')
    ).filter(
        promedio__gte=4
    ).order_by('-promedio')[:4]

    # Servicios: siempre los mismos (últimos 4 servicios aprobados)
    servicios = Producto.objects.filter(
        estado='aprobado', 
        tipo='servicio'
    ).order_by('-fecha_creacion')[:4]

    return render(request, 'core/home.html', {
        'productos': productos, # Esta es la que cambia al buscar
        'productos_populares': productos_populares,
        'servicios': servicios,
        'query': query
    })

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
            password = form.cleaned_data.get('password')

            user.username = correo
            user.email = correo
            user.is_active = False

            user.set_password(password)

            user.first_name = form.cleaned_data.get('nombre')
            user.last_name = form.cleaned_data.get('apellidos')

            try:
                user.save()

                Perfil.objects.create(
                    user=user,
                    rol='cliente',
                    foto=form.cleaned_data.get('foto'),
                    numero_control=form.cleaned_data.get('numero_control')
                )

                try:
                    enviar_correo_activacion(request, user)
                except Exception as e:
                    print(f"Error enviando correo: {e}")

                return render(request, 'core/confirmar_envio.html')

            except IntegrityError:
                form.add_error('email', "Este correo ya está registrado.")

        # 🔥 IMPORTANTE: mostrar errores en pantalla
        return render(request, 'core/registro_cliente.html', {'form': form})

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
        nuevo_correo = request.POST.get('email')
        
        # Guardamos nombres e información básica de inmediato
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save() 

        # Si el correo cambió, iniciamos verificación
        if nuevo_correo and nuevo_correo != user.email:
            codigo = str(random.randint(100000, 999999))
            request.session['temp_email'] = nuevo_correo
            request.session['verif_code'] = codigo
            
            send_mail(
                'Código de Verificación StuMarket',
                f'Tu código para cambiar de correo es: {codigo}',
                'noreply@stumarket.com',
                [nuevo_correo],
                fail_silently=False,
            )
            messages.info(request, "Nombres actualizados. Verifica tu nuevo correo para completar el cambio.")
            return render(request, 'core/verificar_codigo.html', {'email': nuevo_correo})

        messages.success(request, "Perfil actualizado correctamente.")
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
            user = request.user
            
            # --- EL CAMBIO CLAVE ---
            user.email = nuevo_email
            user.username = nuevo_email  # Actualizamos también el nombre de usuario
            user.save()
            # -----------------------
            
            request.session.pop('verif_code', None)
            request.session.pop('temp_email', None)
            
            messages.success(request, "¡Cuenta actualizada! Ahora tu nombre de usuario y correo son iguales.")
            return redirect('perfil')
        else:
            messages.error(request, "El código es incorrecto.")
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
        # 1. Recolección de datos
        nombre = request.POST.get('nombre')
        tipo = request.POST.get('tipo')
        precio_raw = request.POST.get('precio')
        descripcion = request.POST.get('descripcion', '')
        imagen = request.FILES.get('imagen')
        
        # 2. VALIDACIONES CRÍTICAS
        # A. Campos vacíos
        if not all([nombre, tipo, precio_raw, imagen]):
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'core/agregar_producto.html')

        # B. Validación de Precio (Evita el error Decimal de antes)
        try:
            precio_final = float(precio_raw)
            if precio_final <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Escribe un precio numérico válido (mayor a 0).")
            return render(request, 'core/agregar_producto.html')

        # 3. Guardado seguro
        try:
            nuevo_p = Producto(
                vendedor=request.user,
                nombre=nombre,
                tipo=tipo,
                precio=precio_final,
                descripcion=descripcion,
                imagen=imagen,
                estado='pendiente'
            )
            nuevo_p.save()
            
            messages.success(request, "¡Publicación enviada! El admin la revisará.")
            return redirect('mis_productos') 
            
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")
            return render(request, 'core/agregar_producto.html')

    return render(request, 'core/agregar_producto.html')


@login_required
def eliminar_cuenta(request):
    if request.method == 'POST':
        user = request.user
        password_confirm = request.POST.get('password_confirm')
        
        # Verificamos que la contraseña sea correcta
        if user.check_password(password_confirm):
            # Opcional: Aquí podrías eliminar imágenes de la carpeta media si quisieras
            logout(request)
            user.delete() 
            messages.success(request, "Tu cuenta ha sido eliminada. Lamentamos verte partir.")
            return redirect('login')
        else:
            messages.error(request, "La contraseña es incorrecta. No se pudo eliminar la cuenta.")
            return redirect('perfil')
            
    return redirect('perfil')

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Lógica de reseñas (Se queda igual)
    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        comentario = request.POST.get('comentario')
        
        Resena.objects.create(
            producto=producto,
            usuario=request.user,
            calificacion=calificacion,
            comentario=comentario
        )
        return redirect('detalle_producto', producto_id=producto.id)
    
    resenas = producto.resenas.all().order_by('-fecha')
    promedio_producto = resenas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    promedio_vendedor = Resena.objects.filter(producto__vendedor=producto.vendedor).aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    
    # --- ESTO ES LO NUEVO Y SEGURO ---
    es_favorito = False
    if request.user.is_authenticated:
        es_favorito = Favorito.objects.filter(usuario=request.user, producto=producto).exists()
    # --------------------------------
    
    context = {
        'producto': producto,
        'resenas': resenas,
        'promedio_producto': promedio_producto,
        'promedio_vendedor': promedio_vendedor,
        'total_resenas': resenas.count(),
        'es_favorito': es_favorito,  # Enviamos la respuesta al HTML
    }
    return render(request, 'core/detalle_producto.html', context)

# --- VISTA PARA ELIMINAR PRODUCTO ---
@login_required
def eliminar_producto(request, producto_id):
    # Buscamos el producto asegurándonos que el vendedor sea quien solicita borrarlo
    producto = get_object_or_404(Producto, id=producto_id, vendedor=request.user)
    
    if request.method == 'POST':
        producto.delete()
        messages.success(request, "El producto ha sido eliminado permanentemente.")
        # El redirect funciona como "limpieza de caché" forzando una nueva carga de datos
        return redirect('mis_productos')
    
    return redirect('mis_productos')

# ---EDITAR PRODUCTO ---
@login_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, vendedor=request.user)

    if request.method == 'POST':
        # Capturamos datos del formulario manual
        nombre = request.POST.get('nombre')
        tipo = request.POST.get('tipo')
        precio = request.POST.get('precio')
        descripcion = request.POST.get('descripcion')
        nueva_imagen = request.FILES.get('imagen')

        # Validaciones básicas
        if not all([nombre, precio]):
            messages.error(request, "El nombre y el precio son obligatorios.")
            return render(request, 'core/editar_producto.html', {'producto': producto})

        # Actualizamos los campos
        producto.nombre = nombre
        producto.tipo = tipo
        producto.precio = precio
        producto.descripcion = descripcion
        
        if nueva_imagen:
            producto.imagen = nueva_imagen
            
        # IMPORTANTE: Al editar, el estado vuelve a 'pendiente' para que el admin lo revise de nuevo
        producto.estado = 'pendiente'
        producto.save()

        messages.success(request, "Producto actualizado. Esperando nueva revisión del administrador.")
        return redirect('mis_productos')

    return render(request, 'core/editar_producto.html', {'producto': producto})

##Apartado Hamburguesa bootstrap
##vista terminos y condiciones 
def terminos_view(request):
    return render(request, 'core/terminos.html')

##Apartado favoritos
@login_required
def agregar_favorito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Buscamos si ya existe, si no lo crea
    favorito, created = Favorito.objects.get_or_create(
        usuario=request.user, 
        producto=producto
    )
    
    if not created:
        # Si ya existía y le dio click de nuevo, lo quitamos (Efecto On/Off)
        favorito.delete()
        messages.info(request, "Eliminado de tus favoritos.")
    else:
        messages.success(request, "¡Agregado a tus favoritos!")
    
    # Te regresa a la misma página donde estabas
    return redirect('detalle_producto', producto_id=producto.id)

@login_required
def favoritos_view(request):
    # Aquí es donde cargamos tu archivo favoritos.html
    mis_favoritos = Favorito.objects.filter(usuario=request.user).select_related('producto')
    
    return render(request, 'core/favoritos.html', {
        'favoritos': mis_favoritos
    })

@login_required
def eliminar_favorito(request, favorito_id):
    if request.method == 'POST':
        # Borramos usando el ID de la tabla core_favorito
        fav = get_object_or_404(Favorito, id=favorito_id, usuario=request.user)
        fav.delete()
        messages.success(request, "Se quitó de la lista.")
    
    return redirect('favoritos') # Nombre de la URL de tu lista