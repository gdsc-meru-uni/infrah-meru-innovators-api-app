from django.contrib import admin
from .models import PasswordResetRequest,UserProfile,OTP,PasswordResetSession

# Register your models here.
admin.site.register(PasswordResetRequest)
admin.site.register(UserProfile)
admin.site.register(OTP)
admin.site.register(PasswordResetSession)

