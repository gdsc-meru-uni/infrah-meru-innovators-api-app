from grpc import Status
from requests import Response, Session
from rest_framework import serializers


from Innovation_WebApp.Email import send_ticket_email
from .models import CommunityMember, SubscribedUsers, Events,EventRegistration,CommunityProfile,CommunitySession,Social_media
from .models import CommunityProfile, Social_media, CommunitySession
import boto3
from django.conf import settings
import uuid
from django.db import IntegrityError, DatabaseError, OperationalError
from Club.models import Club,ExecutiveMember
from Club.serializers import ExecutiveMemberSerializer,ClubSerializer
from django.db import transaction
from account.models import User
from Club.models import ExecutiveMember


import logging

logger = logging.getLogger(__name__)

class SubscribedUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscribedUsers
        fields = ['id', 'email', 'created_date']


class EventsSerializer(serializers.ModelSerializer):
    image_field = serializers.ImageField(write_only=True, required=False)  # Handle image upload
    image_url = serializers.SerializerMethodField()  # Return the S3 URL

    class Meta:
        model = Events
        fields = ['id', 'name', 'category', 'description',
                  'image_url', 'image_field', 'date', 'location',
                  'organizer', 'contact_email', 'is_virtual']
        extra_kwargs = {
            'image_url': {'read_only': True}  # Read-only field for S3 URL
        }

    def get_image_url(self, obj):
        """Return the full S3 URL for the image."""
        if obj.image_url:
            # Debug: Print what we're working with
            print(f"get_image_url processing: {obj.image_url}")
            
            if obj.image_url.startswith('http'):
                print(f"Using existing URL: {obj.image_url}")
                return obj.image_url  # Already a full URL
            
            full_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.image_url}"
            print(f"Converted to full URL: {full_url}")
            return full_url
        return None

    def create(self, validated_data):
        # Extract image_field from the validated data
        image_file = validated_data.pop('image_field', None)
        print("Starting creating process....")
        print(f"Image file is in validated_data:{image_file}")
        # Create the event instance
        event_instance = Events.objects.create(**validated_data)
        print(f"Event instance created with ID: {event_instance.id}")


        # Handle S3 upload if an image is provided
        if image_file:
            try:
                print(f"Attempting S3 upload for file: {image_file.name}")
        
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )

                # Generate a unique file name
                filename = f"event_images/{uuid.uuid4()}_{image_file.name}"
                print(f"Generated filename: {filename}")

                # Reset file pointer
                image_file.seek(0)

                # Upload the file to S3
                print("Starting S3 upload...")
                s3_client.upload_fileobj(
                    image_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    filename,
                    ExtraArgs={
                        'ContentType': image_file.content_type
                    }
                )
                print("S3 upload completed")

               
                # store just the path,the SerializerMethodField will construct the full url
                event_instance.image_url = filename
                event_instance.save()


                # Set the public S3 URL in the image field
                #event_instance.image = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{filename}"
                #event_instance.save()
            except Exception as e:
                    print(f"Error uploading to S3: {str(e)}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    raise serializers.ValidationError(f"Failed to upload image to S3: {str(e)}")
        return event_instance
        
   

    def update(self, instance, validated_data):
        image_file = validated_data.pop('image_field', None)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image_file:
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )

                # Delete old image if it exists and isn't the default
                if instance.image_url and 'default.png' not in instance.image_url:
                    # Handle both path-only and full URL formats
                    old_key = instance.image_url
                    if instance.image_url.startswith('http'):
                        old_key = instance.image_url.split('.com/')[-1]
                    
                    try:
                        s3_client.delete_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=old_key
                        )
                    except Exception as e:
                        print(f"Warning: Failed to delete old image: {str(e)}")

                # Generate unique filename
                filename = f"event_images/{uuid.uuid4()}_{image_file.name}"
                image_file.seek(0)

                # Upload new image
                s3_client.upload_fileobj(
                    image_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    filename,
                    ExtraArgs={'ContentType': image_file.content_type}
                )

                # Store just the path, not the full URL (consistent with create method)
                instance.image_url = filename

            except Exception as e:
                print(f"Error uploading to S3: {str(e)}")
                raise serializers.ValidationError(f"Failed to upload image to S3: {str(e)}")

        instance.save()
        return instance


class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = ['uid', 'event', 'full_name', 'email', 'course', 'educational_level', 
                 'phone_number', 'expectations', 'registration_timestamp', 'ticket_number']
        read_only_fields = ['uid','registration_timestamp', 'ticket_number']

    def create(self, validated_data):
        registration = super().create(validated_data)
        
        # Send ticket email
        send_ticket_email(registration)

        
        return registration
    
class EventDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Events
        fields = ['name', 'description', 'location', 'date', 'category', 'organizer']

class MyRegistrationSerializer(serializers.ModelSerializer):
    # Include the event details
    eventName = serializers.CharField(source='event.name')
    eventDescription = serializers.CharField(source='event.description')
    eventLocation = serializers.CharField(source='event.location')
    eventDate = serializers.DateTimeField(source='event.date')
    
    class Meta:
        model = EventRegistration
        fields = [
            'eventName', 'eventDescription', 'eventLocation', 'eventDate',
            'uid', 'event', 'full_name', 'email', 'course', 'educational_level', 
            'phone_number', 'expectations', 'registration_timestamp', 'ticket_number'
        ]
    
class CommunitySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunitySession
        fields = ['day', 'start_time', 'end_time', 'meeting_type', 'location']
        extra_kwargs = {'community':{'reequired':False}}

class CommunityMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityMember
        fields = ['id', 'name', 'email', 'joined_at']

class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Social_media
        fields = ['id','platform','url']

class CommunityMemberListSerializer(serializers.ModelSerializer):
    joined_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    
    class Meta:
        model = CommunityMember
        fields = ['id', 'name', 'email', 'joined_date']
        read_only_fields = ['id', 'joined_date']



DEFAULT_CLUB_ID = 1
class CommunityProfileSerializer(serializers.ModelSerializer):
    community_lead = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )
    co_lead = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )
    secretary = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )

    community_lead_details = serializers.SerializerMethodField()
    co_lead_details = serializers.SerializerMethodField()
    secretary_details = serializers.SerializerMethodField()

    club = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )

    social_media = SocialMediaSerializer(many=True, required=False)
    sessions = CommunitySessionSerializer(many=True, required=False)
    members = CommunityMemberListSerializer(many=True, read_only=True)


    class Meta:
        model = CommunityProfile
        fields = [
            'id', 'name', 'club', 'community_lead', 'co_lead', 'secretary',
            'community_lead_details', 'co_lead_details', 'secretary_details',
            'email', 'phone_number', 'social_media', 'description',
            'founding_date', 'total_members','members', 'is_recruiting', 'tech_stack',
            'sessions'
        ]
        read_only_fields = ['id', 'total_members', 'community_lead_details', 
                           'co_lead_details', 'secretary_details','members']

    def to_internal_value(self, data):
        raw_data = data.copy()
        validated_data = super().to_internal_value(data)
        for field in ['community_lead', 'co_lead', 'secretary']:
            if field in raw_data:
                value = raw_data[field]
                if value is not None:
                    try:
                        User.objects.get(id=value)
                        validated_data[field] = value
                    except User.DoesNotExist:
                        raise serializers.ValidationError({field: f"Invalid pk '{value}' - object does not exist."})
                else:
                    validated_data[field] = None
        return validated_data

    def get_community_lead_details(self, obj):
        if obj.community_lead:
            return {
                'id': obj.community_lead.id,
                'username': obj.community_lead.username,
                'email': obj.community_lead.email,
                'first_name': obj.community_lead.first_name,
                'last_name': obj.community_lead.last_name
            }
        return None

    def get_co_lead_details(self, obj):
        if obj.co_lead:
            return {
                'id': obj.co_lead.id,
                'username': obj.co_lead.username,
                'email': obj.co_lead.email,
                'first_name': obj.co_lead.first_name,
                'last_name': obj.co_lead.last_name
            }
        return None

    def get_secretary_details(self, obj):
        if obj.secretary:
            return {
                'id': obj.secretary.id,
                'username': obj.secretary.username,
                'email': obj.secretary.email,
                'first_name': obj.secretary.first_name,
                'last_name': obj.secretary.last_name
            }
        return None

    def validate(self, data):
        community_lead_id = data.get('community_lead')
        co_lead_id = data.get('co_lead')
        secretary_id = data.get('secretary')

        if not any([community_lead_id, co_lead_id, secretary_id]):
            raise serializers.ValidationError(
                "At least one executive position (community_lead, co_lead, or secretary) must be assigned."
            )

        executives = [id for id in [community_lead_id, co_lead_id, secretary_id] if id is not None]
        if len(executives) != len(set(executives)):
            raise serializers.ValidationError(
                "A user cannot hold multiple executive positions in the same community."
            )

        return data

    def validate_name(self, value):
        club = self.initial_data.get('club', DEFAULT_CLUB_ID)
        if self.instance is None:
            if CommunityProfile.objects.filter(name=value, club_id=club).exists():
                raise serializers.ValidationError("A community with this name already exists in this club.")
        return value

    def validate_email(self, value):
        if value and CommunityProfile.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This email is already used by another community.")
        return value

    def validate_phone_number(self, value):
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits, +, -, or spaces.")
        return value

    def create(self, validated_data):
        social_media_data = validated_data.pop('social_media', [])
        sessions_data = validated_data.pop('sessions', [])
        
        # Convert IDs to User instances for ForeignKey fields
        community_lead = None
        co_lead = None
        secretary = None
        
        if 'community_lead' in validated_data and validated_data['community_lead'] is not None:
            community_lead = User.objects.get(id=validated_data['community_lead'])
            validated_data['community_lead'] = community_lead
        
        if 'co_lead' in validated_data and validated_data['co_lead'] is not None:
            co_lead = User.objects.get(id=validated_data['co_lead'])
            validated_data['co_lead'] = co_lead
        
        if 'secretary' in validated_data and validated_data['secretary'] is not None:
            secretary = User.objects.get(id=validated_data['secretary'])
            validated_data['secretary'] = secretary
        
        # Set default club if not provided
        if 'club' not in validated_data or validated_data['club'] is None:
            validated_data['club'] = Club.objects.get(id=DEFAULT_CLUB_ID)
        
        # Create the CommunityProfile instance
        community = CommunityProfile.objects.create(**validated_data)
        
        # Create executive entries
        if community_lead:
            ExecutiveMember.objects.create(user=community_lead, community=community, position='LEAD')
        
        if co_lead:
            ExecutiveMember.objects.create(user=co_lead, community=community, position='CO_LEAD')
        
        if secretary:
            ExecutiveMember.objects.create(user=secretary, community=community, position='SECRETARY')
        
        # Handle social media
        social_media_instances = [
            Social_media.objects.get_or_create(**sm_data)[0] for sm_data in social_media_data
        ]
        community.social_media.set(social_media_instances)
        
        # Handle sessions
        for session_data in sessions_data:
            session_serializer = CommunitySessionSerializer(data=session_data)
            if session_serializer.is_valid():
                session_serializer.save(community=community)
            else:
                raise serializers.ValidationError(f"Session validation errors: {session_serializer.errors}")
        
        community.update_total_members()
        
        return community

    def update(self, instance, validated_data):
        social_media_data = validated_data.pop('social_media', None)
        sessions_data = validated_data.pop('sessions', None)
        
        # Keep track of original executives
        old_community_lead = instance.community_lead
        old_co_lead = instance.co_lead
        old_secretary = instance.secretary
        
        # Convert IDs to User instances for ForeignKey fields
        new_community_lead = None
        new_co_lead = None
        new_secretary = None
        
        if 'community_lead' in validated_data and validated_data['community_lead'] is not None:
            new_community_lead = User.objects.get(id=validated_data['community_lead'])
            validated_data['community_lead'] = new_community_lead
        
        if 'co_lead' in validated_data and validated_data['co_lead'] is not None:
            new_co_lead = User.objects.get(id=validated_data['co_lead'])
            validated_data['co_lead'] = new_co_lead
        
        if 'secretary' in validated_data and validated_data['secretary'] is not None:
            new_secretary = User.objects.get(id=validated_data['secretary'])
            validated_data['secretary'] = new_secretary
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update executives
        if old_community_lead != new_community_lead:
            if old_community_lead:
                ExecutiveMember.objects.filter(user=old_community_lead, community=instance, position='LEAD').delete()
            if new_community_lead:
                ExecutiveMember.objects.create(user=new_community_lead, community=instance, position='LEAD')
        
        if old_co_lead != new_co_lead:
            if old_co_lead:
                ExecutiveMember.objects.filter(user=old_co_lead, community=instance, position='CO_LEAD').delete()
            if new_co_lead:
                ExecutiveMember.objects.create(user=new_co_lead, community=instance, position='CO_LEAD')
        
        if old_secretary != new_secretary:
            if old_secretary:
                ExecutiveMember.objects.filter(user=old_secretary, community=instance, position='SECRETARY').delete()
            if new_secretary:
                ExecutiveMember.objects.create(user=new_secretary, community=instance, position='SECRETARY')
        
        # Handle social media and sessions (existing code remains the same)
        if social_media_data is not None:
            instance.social_media.clear()
            social_media_instances = [
                Social_media.objects.get_or_create(**sm_data)[0] for sm_data in social_media_data
            ]
            instance.social_media.set(social_media_instances)

        if sessions_data is not None:
            instance.sessions.all().delete()
            for session_data in sessions_data:
                session_serializer = CommunitySessionSerializer(data=session_data)
                if session_serializer.is_valid():
                    session_serializer.save(community=instance)
                else:
                    raise serializers.ValidationError(f"Session validation errors: {session_serializer.errors}")

        instance.update_total_members()
        
        return instance
    
class CommunityJoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityMember
        fields = ['community', 'name', 'email']