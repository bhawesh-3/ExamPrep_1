from django import forms
from .models import Syllabus
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re

class SyllabusForm(forms.ModelForm):
    class Meta:
        model = Syllabus
        fields = ['content', 'file']

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=True,
        help_text='Required. Enter a valid email address.',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 6:
            raise ValidationError("Username must be at least 6 characters long.")
        return username
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        # Check for minimum length (Django default is 8)
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        # Check for at least one letter
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError("Password must contain at least one letter.")
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number.")
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character (like !@#$%^&*(),.?\":{}|<>).")
        
        return password

# Custom authentication form that accepts email or username
class EmailOrUsernameAuthenticationForm(forms.Form):
    username_or_email = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )