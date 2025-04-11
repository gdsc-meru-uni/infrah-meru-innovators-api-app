from django.db import models
from django.utils.timezone import now
from django.contrib.auth import get_user_model
User = get_user_model()

# Create your models here.
class Club(models.Model):
    name = models.CharField(max_length=200)
    about_us = models.TextField()
    vision = models.CharField(max_length=500)
    mission = models.CharField(max_length=500)
    social_media = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return self.name

class ExecutiveMember(models.Model):
    POSITIONS = [
        ('LEAD', 'Community Lead'),
        ('CO_LEAD', 'Co-Lead'),
        ('SECRETARY', 'Secretary')
    ]
    
    user = models.ForeignKey(User, related_name='executive_positions', on_delete=models.CASCADE)
    community = models.ForeignKey('Innovation_WebApp.CommunityProfile', related_name='executive_members', on_delete=models.CASCADE)
    position = models.CharField(max_length=10, choices=POSITIONS)
    joined_date = models.DateField(default=now)
    
    class Meta:
        unique_together = ('user', 'community')
        
    def __str__(self):
        return f"{self.user.username} - {self.get_position_display()} of {self.community.name}"
    