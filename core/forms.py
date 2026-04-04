from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class RegistroClienteForm(forms.ModelForm):
    # Campos adicionales que no están en el modelo User por defecto
    nombre = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    numero_control = forms.CharField(max_length=20)
    foto = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['nombre', 'apellidos', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data
    
# Agrega esto a core/forms.py
class RegistroVendedorForm(forms.ModelForm):
    nombre = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    telefono = forms.CharField(max_length=15)
    numero_control = forms.CharField(max_length=20)
    grupo = forms.CharField(max_length=10)
    
    EDIFICIOS = (
        ('Edificio A', 'Edificio A'),
        ('Edificio D', 'Edificio D'),
        ('Edificio F', 'Edificio F'),
    )
    edificio = forms.ChoiceField(choices=EDIFICIOS, widget=forms.RadioSelect)
    casillero = forms.CharField(max_length=10)
    direccion = forms.CharField(widget=forms.TextInput())
    foto = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['nombre', 'apellidos', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data   