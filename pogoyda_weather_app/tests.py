import re
from datetime import datetime, timedelta
from unittest.mock import patch

import jwt
from django.test import TestCase

from pogoyda_weather import settings
from pogoyda_weather_app.models import CustomUser, FavoriteLocation
from django.core.cache import cache


class IndexTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_index_returns_200_for_authenticated_user(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Favorites')

    def test_index_returns_200_for_anonymous_user(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'register')

    def test_search_returns_weather_data(self):
        response_en = self.client.post('/', {'city': 'Moscow'})

        self.assertEqual(response_en.status_code, 200)
        self.assertContains(response_en, 'Moscow')
        self.assertContains(response_en, '°C')
        self.assertContains(response_en, 'km/h')

    def test_invalid_city_shows_error(self):
        response = self.client.post('/', {'city': 'NonExistCity123'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/incorrect_city/NonExistCity123')

    # Pymorphy3 locative prepositional test
    def test_russian_language_prepositional_city_names(self):
        response = self.client.post('/', {'city': 'Москва'}, HTTP_ACCEPT_LANGUAGE='ru')
        self.assertContains(response, 'Москве')

    def test_rate_limiting_on_index(self):

        try:
            for i in range(30):
                self.client.get('/')

            response = self.client.get('/')

            self.assertEqual(response.status_code, 429)
            self.assertTemplateUsed(response, 'too_many_requests.html')
        finally:
            cache.clear() # ratelimit keep count of requests in cache, that's why we clear cache to avoid errors.


class CustomLoginTest(TestCase):

    @classmethod
    def setUp(cls):
        cls.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_login_page_loads(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Password')

    def test_successful_login_and_redirect_to_index_page(self):
        response = self.client.post('/login/', {'username': 'testuser', 'password': 'testpass123'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')

    def test_successful_login(self):
        self.client.post('/login/', {'username': 'testuser', 'password': 'testpass123'})
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_invalid_login_and_stay_at_login_page(self):
        response = self.client.post('/login/', {'username': 'testuser', 'password': '<PASSWORD>'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username')

    def test_rate_limiting_on_login(self):

        try:
            for i in range(20):
                self.client.get('/login/')

            response = self.client.get('/login/')

            self.assertEqual(response.status_code, 429)
            self.assertTemplateUsed(response, 'too_many_requests.html')
        finally:
            cache.clear() # ratelimit keep count of requests in cache, that's why we clear cache to avoid errors.


class TestCustomRegister(TestCase):

    def test_registration_page_loads(self):
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register')
        self.assertContains(response, 'email')


    def test_successful_registration_sends_confirmation_email(self):

        with patch('pogoyda_weather_app.views.send_mail') as mock_send_mail:

            response = self.client.post('/register/', {
                'username': 'user1',
                'email': 'test@mail.com',
                'password1': 'testpass1',
                'password2': 'testpass1'
            })

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Check Your Email')

            mock_send_mail.assert_called_once()
            args = mock_send_mail.call_args[0]

            self.assertEqual(args[0], 'Registration confirmation')
            self.assertIn('confirm', args[1])

            self.assertFalse(CustomUser.objects.filter(username='user1').exists())

    def test_registration_with_already_existing_email(self):

        CustomUser.objects.create_user(username='user1', password='testpass1', email='test@mail.com')

        with patch('pogoyda_weather_app.views.send_mail') as mock_send_mail:

            response = self.client.post('/register/', {
                'username': 'user2',
                'email': 'test@mail.com',
                'password1': 'testpass1',
                'password2': 'testpass1'
            })

            self.assertEqual(response.status_code, 200)

            mock_send_mail.assert_not_called()

            self.assertContains(response, 'email already exists')
            self.assertFalse(CustomUser.objects.filter(username='user2').exists())

    def test_passwords_not_match(self):

        with patch('pogoyda_weather_app.views.send_mail') as mock_send_mail:

            response = self.client.post('/register/', {
                'username': 'user1',
                'email': 'test@mail.com',
                'password1': 'testpass1',
                'password2': '123123123'
            })

            self.assertEqual(response.status_code, 200)

            mock_send_mail.assert_not_called()

            self.assertContains(response, 'not match')
            self.assertFalse(CustomUser.objects.filter(username='user1').exists())

    def test_rate_limiting_on_registration(self):

        try:
            for i in range(10):
                self.client.get('/register/')

            response = self.client.get('/register/')

            self.assertEqual(response.status_code, 429)
            self.assertTemplateUsed(response, 'too_many_requests.html')
        finally:
            cache.clear() # ratelimit keep count of requests in cache, that's why we clear cache to avoid errors.



class TestCustomConfirmRegistration(TestCase):

    def test_successful_confirm_registration(self):
        with patch('pogoyda_weather_app.views.send_mail') as mock_send_mail:

            response = self.client.post('/register/', {
                'username': 'user1',
                'email': 'test@mail.com',
                'password1': 'testpass1',
                'password2': 'testpass1'
            })

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Check Your Email')

            mock_send_mail.assert_called_once()

            args = mock_send_mail.call_args[0]
            confirmation_link = re.search(r'(https?://\S+)', args[1]).group(0)

            self.assertFalse(CustomUser.objects.filter(username='user1').exists())
            self.client.get(confirmation_link)
            self.assertTrue(CustomUser.objects.filter(username='user1').exists())

    def test_expired_token_confirm_registration(self):

        expired_payload = {
            'email': 'test@mail.com',
            'username': 'user1',
            'password': 'testpass1',
            'exp': datetime.utcnow() - timedelta(hours=1)
        }

        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(f'/confirm/{expired_token}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Token expired')
        self.assertFalse(CustomUser.objects.filter(username='user1').exists())

    def test_invalid_token_confirm_registration(self):
        response = self.client.get('/confirm/invalid-token/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid token')

class TestPasswordRecovery(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@mail.com',
            password='testpass123'
        )

    def test_recovery_password_page_loads(self):
        response = self.client.get('/password_reset/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recovery')

    def test_recovery_email_send_to_existing_user(self):
        with patch('pogoyda_weather_app.views.send_mail') as mock_send_mail:
            response = self.client.post('/password_reset/', {'email': 'test@mail.com'})

            mock_send_mail.assert_called_once()
            args = mock_send_mail.call_args[0]

            self.assertIn('Account access recovery', args[0])
            self.assertEqual(['test@mail.com'], args[3])

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'recovery_notify.html')

    def test_recovery_email_send_to_not_existing_user(self):

        response = self.client.post('/password_reset/', {'email': 'not_exist@mail.com'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'email not exists')

    def test_success_password_reset(self):

        payload = {
            'email': 'test@mail.com',
            'username': 'testuser',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }

        reset_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.post(f'/recovery_account/{reset_token}/', {
            'password1': 'newpass',
            'password2': 'newpass'
        })

        self.assertRedirects(response, '/')
        user = CustomUser.objects.get(username='testuser')
        self.assertTrue(user.check_password('newpass'))

    def test_expired_token_for_reset_password(self):

        payload = {
            'email': 'test@mail.com',
            'username': 'testuser',
            'exp': datetime.utcnow() - timedelta(hours=1)
        }

        reset_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(f'/recovery_account/{reset_token}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Token expired')

    def test_invalid_token_for_reset_password(self):
        response = self.client.get('/recovery_account/invalid-token/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid token')


class TestLogout(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@mail.com',
            password='testpass123'
        )

    def test_successful_logout(self):
        self.client.login(username='testuser', password='testpass123')
        self.assertIn('_auth_user_id', self.client.session)
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_rate_limiting_on_logout(self):

        try:
            for i in range(10):
                self.client.get('/logout/')

            response = self.client.get('/logout/')

            self.assertEqual(response.status_code, 429)
            self.assertTemplateUsed(response, 'too_many_requests.html')
        finally:
            cache.clear() # ratelimit keep count of requests in cache, that's why we clear cache to avoid errors.

class TestCreateFavoriteLocations(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@mail.com',
            password='testpass123'
        )

    def test_successful_create_favorite_location(self):
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post('/', {'city': 'moscow'})
        response = self.client.get('/create_fav/')

        self.assertRedirects(response,'/')

        response = self.client.get('/')
        self.assertContains(response, 'Moscow - Russia')
        self.assertTrue(FavoriteLocation.objects.filter(city='Moscow', country='Russia').exists())

    def test_unauthorized_user_try_create_favorite_location_redirects_to_index(self):
        response = self.client.get('/create_fav/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')

    def test_create_duplicate_favorite_location_not_created(self):
        self.client.login(username='testuser', password='testpass123')

        self.client.post('/', {'city': 'moscow'})
        self.client.get('/create_fav/')
        self.client.get('/create_fav/')

        self.assertTrue(FavoriteLocation.objects.filter(city='Moscow', country='Russia').exists())
        count = (FavoriteLocation.objects.filter(city='Moscow', country='Russia').count())
        self.assertEqual(count, 1)

    def test_no_city_and_country_in_session_redirects_to_index(self):
        self.client.login(username='testuser', password='testpass123')

        self.client.post('/', {'city': 'moscow'})

        session = self.client.session
        session.pop('city', None)
        session.pop('country', None)
        session.save()

        response = self.client.get('/create_fav/')

        self.assertRedirects(response, '/')
        self.assertEqual(FavoriteLocation.objects.count(), 0)

