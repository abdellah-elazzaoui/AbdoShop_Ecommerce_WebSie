from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class CustomUser(AbstractUser):
    city = models.CharField(max_length=100,blank=True,null=True)
    state = models.CharField(max_length=100,blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    phone = models.CharField(max_length=15,blank=True,null=True)
    country = models.CharField(max_length=100, blank=True, null=True,default="Agadir")
    image = models.ImageField(upload_to="img",default="profil.jpg")

    def __str__(self):
        return self.username
