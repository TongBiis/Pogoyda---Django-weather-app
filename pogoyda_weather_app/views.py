from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import requests
import pymorphy3
from datetime import datetime
import time

from jwt import ExpiredSignatureError, InvalidTokenError

from .forms import *
from django.contrib.auth import login, logout
from django.contrib import messages
from django.core.mail import send_mail
from .models import FavoriteLocation
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
import jwt

morph = pymorphy3.MorphAnalyzer()

def is_russian(text): # Check if text contains only Russian letters, hyphens and spaces
    return bool(re.match(r'^[а-яА-ЯёЁ\s-]+$', text))


def get_city_in_locative(city_name): # Convert city name to locative case, e.g. Moscow --> in Moscow
    parsed_word = morph.parse(city_name)[0]
    city_in_prepositional = parsed_word.inflect({'loct'}).word
    if city_in_prepositional is None:
        return city_name
    return city_in_prepositional

def generate_registration_token(email, username, password): # Generate token for registration confirmation
    payload = {
        'email': email,
        'username': username,
        'password': password,
        'exp': int(time.time()) + 4 * 3600,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256',)
    return token

def generate_account_recovery_token(email, username): # Generate token for password reset and account recovery
    payload = {
        'email': email.lower(),
        'username': username,
        'exp': int(time.time()) + 4 * 3600,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token


def extract_forecast_data(data):
    forecast_by_days = [] # Create list for forecast data to use later

    for day_data in data['forecast']['forecastday']: # Process each day's general information
        day_entry = { # Store day data
            'date': day_data['date'], # Date in API format
            'date_formatted': datetime.strptime(day_data['date'], '%Y-%m-%d').strftime('%d.%m.%Y'), # Date in website format
            'hours': [] # Store weather information for each hour
        }

        for hour_data in day_data['hour']: # Process each hour's forecast
            hour = int(hour_data['time'][11:13]) # Extract hour from time string
            if hour % 3 == 1:  # Get data every 3 hours starting from 01:00
                day_entry['hours'].append({ # Add data to hourly forecast
                    'time': hour_data['time'][11:16], # Keep only hours and minutes
                    'temp_c': hour_data['temp_c'], # Temperature in Celsius
                    'wind_kph': hour_data['wind_kph'], # Wind speed in km/h
                    'humidity': hour_data['humidity'], # Humidity
                    'condition_icon': hour_data['condition']['icon'], # Weather icon
                    'condition_text': hour_data['condition']['text'] # Weather condition
                })

        forecast_by_days.append(day_entry) # Update forecast data list

    location = { # Location data
        'city': data['location']['name'],
        'region': data['location']['region'],
        'country': data['location']['country'],
    }

    current = { # Current weather data, separated from forecast to avoid confusion
        'localtime': data['location']['localtime'],
        'temp_c': data['current']['temp_c'],
        'wind_kph': data['current']['wind_kph'],
        'humidity': data['current']['humidity'],
        'condition_icon': data['current']['condition']['icon'],
        'condition_text': data['current']['condition']['text'],
    }

    return {
        'forecast_by_days': forecast_by_days[1:],
        'location': location,
        'current': current,
    }


def get_user_ip(request): # Get user's IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_user_city(request): # Get user's city using IP via external API
    ip = get_user_ip(request)
    if not ip or ip in ['127.0.0.1', 'localhost']:
        ip = '8.8.8.8'


    response = requests.get(f'https://ipinfo.io/{ip}/json').json()
    if 'bogon' in response: # If a non-routable IP is used, then send a repeat request
        response = requests.get(f'https://ipinfo.io/8.8.8.8/json').json()


    city = response['city']

    return city


def get_weather_data(city): # Get weather data
    try:
        key = settings.WEATHERAPI_KEY
        url_forecast = settings.WEATHERAPI_REQUESTS_LINK
        params = {'key': key, 'q': city, 'days': 3}  # Parameters for weather API request

        response = requests.get(url_forecast, params=params, timeout=10) # Send request to get weather data
        data = response.json()

        if 'error' in data and data['error']['code'] == 1006: # User entered invalid city
            return {'error_type': 'City_not_found', 'city': city}

        if 'error' in data: # Any other error is considered API error
            return {'error_type': 'API_error'}

    except requests.exceptions.Timeout:
        return {'error_type': 'API_timeout'}
    except Exception as e: # Catch all other exceptions as API errors
        return {'error_type': 'API_error', 'message': str(e)}

    return data


def create_and_get_weather_from_cache(city): # Get weather data, create cache, return weather data
    weather_data = get_weather_data(city)

    if 'error_type' in weather_data: # If response contains error
        error_type = weather_data['error_type'] # Store error type

        if error_type == 'City_not_found':
            cache.set(city, 'City_not_found', 3600)

        elif error_type in ['API_timeout', 'API_error']:
            cache.set(city, error_type, 300)

        return cache.get(city)

    cache.set(city, weather_data, 60) # Store cache for 60 seconds because data updates every minute
    return weather_data


def get_weather_from_cache(city): # Get weather data from cache

    weather_data = cache.get(city)

    if weather_data:
        return weather_data

    if weather_data is None: # if no data, use another function
        return create_and_get_weather_from_cache(city)


def get_search_city(request): # Get city for weather search

    if 'city' in request.POST: # If user manually entered city for search, use this value
        form = SearchForm(request.POST)
        if form.is_valid():
            return form.cleaned_data['city']

    if request.session.get('city'): # If user didn't enter, get from session last searched city
        return request.session.get('city')

    return get_user_city(request)

@login_required(login_url='/', redirect_field_name=None)
def add_to_history(request, location): # Add to search history

    if 'search_history' not in request.session:  # If no search history list in session, create it
        request.session['search_history'] = []

    new_entry = f"{location['city']} - {location['country']}"

    if not request.session['search_history'] or request.session['search_history'][0] != new_entry:  # If list is empty, or if previous item is not equal to new one
        request.session['search_history'].insert(0, new_entry)  # Insert city and country to session
        request.session['search_history'] = request.session['search_history'][:10]  # Limit list size to 10 elements


@ratelimit(key='ip', rate='30/m')
def index(request): # Main function
    city = get_search_city(request)

    browser_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')[:2] # Detect language from browser settings
    supported_langs = ['en', 'ru'] # Supported languages
    lang = browser_lang if browser_lang in supported_langs else 'en' # If browser language is supported, use it, otherwise default to English

    weather_data = get_weather_from_cache(city)

    if weather_data == 'City_not_found': # If city not found, notify user
        return redirect('incorrect_city', city)
    elif weather_data in ['API_timeout', 'API_error']: # Other errors are considered API errors, notify user
        return redirect('redirect_to_api_error')

    forecast = extract_forecast_data(weather_data) # Extract weather forecast from weather data
    location = forecast['location'] # Location data (city, region, country)
    request.session['country'] = location['country'] # Add to session so after page reload user sees the city they entered
    request.session['city'] = location['city']

    add_to_history(request, location) # Add to user's search history

    if lang == 'ru' and is_russian(location['city']): # If language is Russian and search was in Russian, show city in Russian locative case
        location['city'] = get_city_in_locative(location['city'])

    current_weather = forecast['current'] # Current weather data (not forecast)
    localtime = datetime.strptime(current_weather['localtime'], '%Y-%m-%d %H:%M') # Specify time format from API to work with time data
    day, month_en, time = localtime.strftime('%d %B %H:%M').split() # Format time conveniently
    time_list = (day, month_en, time)

    context = {'current_weather': current_weather, 'location': location, 'localtime': localtime, 'time_list': time_list,
               'forecast': forecast['forecast_by_days'], 'incorrect_city': incorrect_city}

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    return render(request, 'index.html', context=context)


@ratelimit(key='ip', rate='10/m')
def custom_register(request): # Registration function

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            registration_token_coded = generate_registration_token( # Create token for confirmation link, embed user info in token, decode later
                email=form.cleaned_data['email'],
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1']
            )
            send_mail(
                'Registration confirmation', # Email subject
                f'To confirm registration, follow this link {request.build_absolute_uri(f"/confirm/{registration_token_coded}/")}', # Email content
                'noreplytest@gmail.com', # From email
                [form.cleaned_data['email'], ], # Recipients list
                fail_silently=False, # Don't ignore errors
            )
            return render(request, 'email_notify.html')
    else:
        form = CustomUserCreationForm()

    context = {'form': form}

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    return render(request, 'register_page.html', context=context)


def email_notify(request): # Function to show that registration email was sent
    return render(request, 'email_notify.html')


@ratelimit(key='ip', rate='20/m')
def custom_login(request): # Login function

    if request.method == 'POST':
        form = CustomUserLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                return redirect('index_url')
    else:
        form = CustomUserLoginForm()

    context = {'form': form}

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    return render(request, 'login_page.html', context=context)


def custom_password_reset(request):
    context = {}

    if 'email' in request.POST:  # If account recovery request was sent
        email_form = EmailValidateForm(request.POST)
        if email_form.is_valid():
            email_for_recovery = email_form.cleaned_data['email']  # Get email user entered
            account_exist = CustomUser.objects.filter(
                email=email_for_recovery.lower()).exists()  # Check if account exists with this email
            if account_exist:  # If account exists
                user = CustomUser.objects.get(email=email_for_recovery.lower())
                username = user.username
                recovery_token_coded = generate_account_recovery_token(
                    email=email_for_recovery,
                    username=username,
                )
                send_mail(
                    'Account access recovery',
                    f'To confirm account access recovery, follow this link {request.build_absolute_uri(f"/recovery_account/{recovery_token_coded}/")}',
                    # Email content
                    'noreplytest@gmail.com',
                    [email_for_recovery, ],
                    fail_silently=False,
                )
                context['email_form'] = email_form
                return render(request, 'recovery_notify.html', context=context)  # Redirect to recovery page
    else:
        email_form = EmailValidateForm()

    context['email_form'] = email_form

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    return render(request, 'password_recovery.html', context=context)


@ratelimit(key='ip', rate='10/m')
def custom_logout(request): # Logout function
    logout(request)
    return redirect('index_url')


def custom_confirm(request, token): # User registration confirmation function
    context = {}

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    try:
        registration_token_decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256']) # Decode token with account creation info from link
        hashed_password = make_password(registration_token_decoded['password']) # Hash password
        user = CustomUser(
            email=registration_token_decoded['email'].lower(),
            username=registration_token_decoded['username'],
            password=hashed_password,
        )
        user.save()
        login(request, user)
        return render(request, 'confirm_register.html', context=context)
    except ExpiredSignatureError:
        return render(request, 'expired_token.html')
    except InvalidTokenError:
        return render(request, 'invalid_token.html')


@ratelimit(key='ip', rate='10/m')
def custom_recovery_account(request, token): # Password change and account access recovery

    try:
        form = CustomUserRestorePasswordForm(request.POST)
        recovery_token_decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        username = recovery_token_decoded['username']


        if request.method == 'POST':
            if form.is_valid():
                user = CustomUser.objects.get(username=username)
                user.set_password(form.cleaned_data['password1'])
                user.save()
                login(request, user)
                messages.success(request, 'Password successfully changed!')
                return redirect('index_url')
        else:
            form = CustomUserRestorePasswordForm()

        context = {'form': form, 'username': username}

        if request.user.is_authenticated:
            favorites = FavoriteLocation.objects.filter(user=request.user)
            context['favorites'] = favorites

        return render(request, 'restore_account_page.html', context=context)
    except ExpiredSignatureError:
        return render(request, 'expired_token.html')
    except InvalidTokenError:
        return render(request, 'invalid_token.html')



@login_required(login_url='/', redirect_field_name=None)
@ratelimit(key='ip', rate='10/m')
def create_favorites(request): # Function to add city to favorites
    if request.user.is_authenticated:
        city = request.session.get('city')  # When searching city, location data is saved to session immediately, so we get data from there
        country = request.session.get('country')

        if FavoriteLocation.objects.filter(user=request.user, city=city, country=country).exists():
            return redirect('index_url')
        if city and country:
            FavoriteLocation.objects.create(
                user=request.user,
                city=city,
                country=country
            )
        return redirect('index_url')
    return redirect('index_url')


@ratelimit(key='ip', rate='20/m')
def show_favorites(request): # Function to show user's favorite cities
    city = request.GET.get('city') # Get value from input in index.html
    request.session['city'] = city # Save to session because in index city is primarily taken from session
    return redirect('index_url')


@ratelimit(key='ip', rate='20/m')
def show_history(request):
    city = request.GET.get('city')
    request.session['city'] = city
    return redirect('index_url')


def incorrect_city(request, city): # Function to show notification that specified city was not found
    context = {'city': city}

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    return render(request, 'incorrect_city.html', context=context)

def redirect_too_many_requests(request, exception):
    response = render(request, 'too_many_requests.html')
    response.status_code = 429
    return response

def redirect_to_api_error(request): # Redirect to page showing notification about temporary API issues
    context = {}

    if request.user.is_authenticated:
        favorites = FavoriteLocation.objects.filter(user=request.user)
        context['favorites'] = favorites

    return render(request, 'api_error.html', context=context)
