from django.db import models
from django.contrib.auth.models import AbstractUser

from profiles.models import OsuUser

class User(AbstractUser):
    """
    Custom user model
    """
    
    is_beta_tester = models.BooleanField(default=False)

    # Relations
    osu_user = models.OneToOneField(OsuUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        if self.osu_user:
            return "{} ({})".format(self.username, self.osu_user.username)
        else:
            return self.username
