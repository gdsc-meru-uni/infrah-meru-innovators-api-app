
from rest_framework import serializers
from .models import Club, ExecutiveMember


class ClubSerializer(serializers.ModelSerializer):
    communities = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = ['id', 'name', 'about_us', 'vision', 'mission', 'social_media', 'communities']
    
    def get_communities(self, obj):
        communities = obj.communities.all()
        result = []
        
        for community in communities:
            # Get community lead details
            community_lead_details = None
            if community.community_lead:
                community_lead_details = {
                    'id': community.community_lead.id,
                    'name': str(community.community_lead),
                    'email': community.community_lead.email if hasattr(community.community_lead, 'email') else None
                }
            
            # Get co-lead details
            co_lead_details = None
            if community.co_lead:
                co_lead_details = {
                    'id': community.co_lead.id,
                    'name': str(community.co_lead),
                    'email': community.co_lead.email if hasattr(community.co_lead, 'email') else None
                }
            
            # Get secretary details
            secretary_details = None
            if community.secretary:
                secretary_details = {
                    'id': community.secretary.id,
                    'name': str(community.secretary),
                    'email': community.secretary.email if hasattr(community.secretary, 'email') else None
                }
            
            # Get social media
            social_media = []
            if hasattr(community, 'social_media'):
                for sm in community.social_media.all():
                    social_media.append({
                        'id': sm.id,
                        'platform': sm.platform,
                        'url': sm.url
                    })
            
            # Get sessions
            sessions = []
            if hasattr(community, 'get_sessions'):
                for session in community.get_sessions():
                    sessions.append({
                        'day': session.day,
                        'start_time': str(session.start_time),
                        'end_time': str(session.end_time),
                        'meeting_type': session.meeting_type,
                        'location': session.location
                    })
            
            # Get members
            members = []
            if hasattr(community, 'members'):
                for member in community.members.all():
                    members.append({
                        'id': member.id,
                        'name': str(member)
                    })
            
            community_data = {
                'id': community.id,
                'name': community.name,
                'community_lead_details': community_lead_details,
                'co_lead_details': co_lead_details,
                'secretary_details': secretary_details,
                'email': community.email,
                'phone_number': community.phone_number,
                'description': community.description,
                'founding_date': community.founding_date,
                'is_recruiting': community.is_recruiting,
                'social_media': social_media,
                'tech_stack': community.tech_stack,
                'members': members,
                'total_members': community.total_members,
                'sessions': sessions
            }
            
            result.append(community_data)
        
        return result
    
class ExecutiveMemberSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    community_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ExecutiveMember
        fields = ['id', 'user', 'community', 'position', 'joined_date', 'user_details', 'community_details']
        read_only_fields = ['joined_date']
    
    def get_user_details(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name
        }
    
    def get_community_details(self, obj):
        return {
            'id': obj.community.id,
            'name': obj.community.name
        }
    
    def validate(self, data):
        # Check if user is already an executive in another community
        user = data.get('user')
        community = data.get('community')
        
        if self.instance:
            # For update operations, exclude the current instance
            is_executive = ExecutiveMember.objects.filter(
                user=user
            ).exclude(id=self.instance.id).exists()
        else:
            # For create operations
            is_executive = ExecutiveMember.objects.filter(user=user).exists()
        
        if is_executive:
            raise serializers.ValidationError(f"User {user.email} is already an executive in another community")
        
        return data

