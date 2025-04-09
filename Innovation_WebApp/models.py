from django.db import models
from django.utils import timezone
from tinymce.models import HTMLField
import uuid
from django.core.validators import EmailValidator,MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import hashlib
import uuid
from Club.models import Club, ExecutiveMember 
#from django.contrib.auth.models import User

class SubscribedUsers(models.Model):
    email = models.EmailField(unique=True, max_length=100)
    created_date = models.DateTimeField('Date created', default=timezone.now)

    def __str__(self):
        return self.email


class Events(models.Model):
    CATEGORY_CHOICE=[
        ('WEB','Web Development'),
        ('CYBERSEC','Cyber Security'),
        ('ANDROID','Android Development'),
        ('AI','Artificial Intelligence'),
        ('BLOCKCHAIN','Blockchain'),
        ('IoT','Internate of Things')
    ]
    name = models.CharField(max_length=100)
    category=models.CharField(max_length=50,choices=CATEGORY_CHOICE,null=False,default='Web Development')
    title = models.CharField(max_length=200 )
    description = models.TextField()
    image_url = models.URLField(default="event_images/default.png") # S3 image URL will be stored here
    date = models.DateTimeField()
    location = models.CharField(max_length=255)
    organizer = models.CharField(max_length=100)
    contact_email = models.EmailField(null=True, blank=True)
    is_virtual = models.BooleanField(default=False)
    #registration_link = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.title
    


class EventRegistration(models.Model):
    EDUCATION_LEVELS = [
        ('1', 'Year 1'),
        ('2', 'Year 2'),
        ('3', 'Year 3'),
        ('4', 'Year 4'),
        ('5', 'Year 5'),
    ]
    
   
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    event = models.ForeignKey('Events', on_delete=models.CASCADE, related_name='registrations')
    full_name = models.CharField(max_length=200)
    email = models.EmailField(validators=[EmailValidator()])
    course = models.CharField(max_length=200)
    educational_level = models.CharField(max_length=20, choices=EDUCATION_LEVELS)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    expectations = models.CharField(max_length=100, null=True)
    registration_timestamp = models.DateTimeField(auto_now_add=True)
    ticket_number = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return f"{self.full_name} - {self.event.name}"
    
    class Meta:
        unique_together = ['email', 'event']
    
class Social_media(models.Model):
    platform = models.CharField(max_length=50)
    url = models.URLField()

    def __str__(self):
        return f"{self.platform}"
    
    
class CommunityProfile(models.Model):
    MEETING_TYPES = [
        ('VIRTUAL', 'Virtual'),
        ('PHYSICAL', 'Physical'),
        ('HYBRID', 'Hybrid')
    ]
    name = models.CharField(max_length=200)
    club = models.ForeignKey('Club.Club',  related_name='communities', on_delete=models.CASCADE)
    community_lead = models.ForeignKey(
        'Club.ExecutiveMember', 
        related_name='communities',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    co_lead = models.ForeignKey(
       'Club.ExecutiveMember', 
        related_name='co_leads',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    secretary = models.ForeignKey(
        ExecutiveMember, 
        on_delete=models.SET_NULL, 
        related_name='secretary_communities',
        null=True,
        blank=True
    )
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    social_media = models.ManyToManyField(Social_media,related_name='communities')
    description = models.TextField()
    founding_date = models.DateField(blank=True, null=True)
    total_members = models.IntegerField(default=0)
    is_recruiting = models.BooleanField(default=False)
    tech_stack = models.JSONField(blank=True, null=True)

    def update_total_members(self):
        current_count = self.members.count()
        if self.total_members != current_count:
            CommunityProfile.objects.filter(id=self.id).update(total_members=current_count)

    def save(self, *args, **kwargs):
        if not self.pk:  # Only for new instances
            super().save(*args, **kwargs)
            self.update_total_members()
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def get_sessions(self):
        return self.sessions.all()
    
       # Convenience methods to get executive information
    def get_lead_email(self):
        return self.community_lead.email if self.community_lead else None
    
    def get_co_lead_email(self):
        return self.co_lead.email if self.co_lead else None
    
    def get_secretary_email(self):
        return self.secretary.email if self.secretary else None 
    
    @receiver([post_save, post_delete], sender='Innovation_WebApp.CommunityMember')
    def update_community_member_count(sender, instance, **kwargs):
        if instance.community:
            instance.community.update_total_members()
    
 
    
    
    
class CommunitySession(models.Model):
    DAYS_OF_WEEK = [
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday')
    ]
    community = models.ForeignKey(CommunityProfile, related_name='sessions', on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    meeting_type = models.CharField(max_length=10, choices=CommunityProfile.MEETING_TYPES)
    location = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.community.name} - {self.get_day_display()} Session"
    
    

class CommunityMember(models.Model):
    community = models.ForeignKey(CommunityProfile, related_name='members', on_delete=models.CASCADE,null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.community.name})"
    


class Community(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    total_members = models.IntegerField(default=0)

    def update_total_members(self):
        self.total_members = self.communitymember_set.count()
        self.save()

    def __str__(self):
        return self.name
