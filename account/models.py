from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import uuid
import json

def get_default_expires_at():
    return timezone.now() + timedelta(hours=1)

# Create your models here.
class PasswordResetRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    old_password = models.CharField(max_length=128,null=True)
    new_password = models.CharField(max_length=128,null=True)
    expires_at = models.DateTimeField(default=get_default_expires_at)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password change for {self.user.username} - {self.token}"
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    course = models.CharField(max_length=50)
    registration_no = models.CharField(max_length=50,blank=True,null=True)
    bio = models.CharField(null=True)
    tech_stacks = models.TextField(blank=True,null=True) # Will store as JSON string
    social_media = models.TextField(blank=True,null=True)
    photo = models.ImageField(upload_to='profile_photos/',blank=True,null=True)

    #  Additional student-specific fields
    graduation_year = models.PositiveIntegerField(blank=True,null=True)
    projects = models.TextField(blank=True,null=True)
    skills = models.TextField(blank=True,null=True)
    year_of_study = models.PositiveIntegerField(blank=True,null=True)

    def __str__(self):
        return self.user.username
    
    def set_tech_stacks(self, tech_stacks_list):
        """Set tech_stacks from a list of strings"""
        self.tech_stacks = json.dumps(tech_stacks_list)
    
    def get_tech_stacks(self):
        """Get tech_stacks as a list of strings"""
        return json.loads(self.tech_stacks) if self.tech_stacks else []
    
    def set_social_media(self, social_media_dict):
        """Set social_media from a dictionary"""
        self.social_media = json.dumps(social_media_dict)
    
    def get_social_media(self):
        """Get social_media as a dictionary"""
        return json.loads(self.social_media) if self.social_media else {}
    
    def set_projects(self, projects_list):
        """Set projects from a list"""
        self.projects = json.dumps(projects_list)
    
    def get_projects(self):
        """Get projects as a list"""
        return json.loads(self.projects) if self.projects else []
    
    def set_skills(self, skills_list):
        """Set skills from a list"""
        self.skills = json.dumps(skills_list)
    
    def get_skills(self):
        """Get skills as a list"""
        return json.loads(self.skills) if self.skills else []
    
    


# forgot password OTP
class OTP(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    def save(self,*args,**Kwargs):
        if not self.expires_at:
            # Set expiration time to 10 minutes from creation
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args,**Kwargs)
    
    def is_valid(self):
        return timezone.now() <= self.expires_at


# Sign up otp
    

class PasswordResetSession(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    otp = models.ForeignKey(OTP,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self,*args,**kwargs):
        if not self.expires_at:
            # Set expiration time to 10 minutes from creation
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)


    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at
