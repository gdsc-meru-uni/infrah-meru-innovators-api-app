from django.contrib import admin
from .models import Events,SubscribedUsers,EventRegistration,CommunityProfile,CommunitySession,Community,CommunityMember,Social_media

# Register your models here.
admin.site.register(Events)
admin.site.register(SubscribedUsers)
admin.site.register(EventRegistration)
admin.site.register(CommunityProfile)
admin.site.register(CommunitySession)
admin.site.register(Community)
admin.site.register(CommunityMember)
admin.site.register(Social_media)





