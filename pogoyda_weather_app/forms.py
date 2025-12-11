import re
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator


class SearchForm(forms.Form):
    city = forms.CharField(max_length=254, widget=forms.TextInput(attrs={'class': 'form-group'}), required=True)

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()

        if not city:
            raise forms.ValidationError(_('Please, enter a city.'))

        if re.search(r'[!@#$%^&*()_+=<>?/\\|{}[\]`~]', city):
            raise forms.ValidationError(_('The city name cannot have special characters.'))

        return city


class CustomUserCreationForm(forms.Form):
    email = forms.EmailField(max_length=254,
                             widget=forms.EmailInput(
                                 attrs={'id': 'id_email', 'class': 'form-input', 'placeholder': _('Enter email')}), )
    username = forms.CharField(max_length=150,
                               widget=forms.TextInput(attrs={'id': 'id_username', 'class': 'form-input',
                                                             'placeholder': _('Enter username')}),
                               validators=[UnicodeUsernameValidator()])
    password1 = forms.CharField(min_length=6, max_length=128, widget=forms.PasswordInput(
        attrs={'id': 'id_password1', 'class': 'form-input', 'placeholder': _('Enter password')}), )
    password2 = forms.CharField(min_length=6, max_length=128, widget=forms.PasswordInput(
        attrs={'id': 'id_password2', 'class': 'form-input', 'placeholder': _('Confirm password')}))

    def clean_username(self):
        cleaned_name = self.cleaned_data['username']
        if CustomUser.objects.filter(username=cleaned_name).exists():
            raise forms.ValidationError(_('A user with that username already exists.'))
        return cleaned_name

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()

        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(_('A user with that email already exists.'))
        return email

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_('Passwords do not match.'))

        return cleaned_data


class CustomUserLoginForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None

    username = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={'class': 'form-input', 'placeholder': _('Enter your username'), }))
    password = forms.CharField(max_length=128, widget=forms.PasswordInput(
        attrs={'class': 'form-input', 'placeholder': _('Enter your password'), }))

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_('Invalid username or password.'))

        return cleaned_data

    def get_user(self):
        return self.user_cache


class CustomUserRestorePasswordForm(forms.Form):
    password1 = forms.CharField(
        min_length=6,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'id': 'new_password1',
            'class': 'form-input',
            'placeholder': _('Enter new password')
        })
    )

    password2 = forms.CharField(
        min_length=6,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'id': 'new_password2',
            'class': 'form-input',
            'placeholder': _('Confirm new password')
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_('Password do not match.'))

        return cleaned_data


class EmailValidateForm(forms.Form):
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(
        attrs={'id': 'id_email', 'class': 'form-input',
               'placeholder': _('Please enter the email address you used to register')}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()

        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(_('A user with that email not exists.'))
        return email