from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    email = models.EmailField(_("email_address"), blank=False, unique=True, error_messages=
    {
        'unique': _("A user with that email already exists."),
    })

    first_name = None
    last_name = None

    class Meta:
        verbose_name = _("CustomUser")
        verbose_name_plural = _("CustomUsers")


class FavoriteLocation(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    city = models.TextField()
    country = models.TextField()

    def __str__(self):
        return f"{self.id} - {self.user} - {self.city} - {self.country}"

    class Meta:
        verbose_name = _("Favorite Location")
        verbose_name_plural = _("Favorite Locations")
        unique_together = (("user", "city", "country"),)
