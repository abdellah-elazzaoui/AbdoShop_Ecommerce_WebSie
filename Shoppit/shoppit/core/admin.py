from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Main fieldsets for editing existing users
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Information', {
            'fields': ('city', 'state', 'address', 'phone')
        }),
    )
    
    # Add fieldsets for creating new users
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'city', 'state', 'address', 'phone'),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)