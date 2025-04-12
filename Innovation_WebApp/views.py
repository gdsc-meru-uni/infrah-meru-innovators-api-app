import csv
import traceback
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from rest_framework import viewsets, views, status,permissions
from rest_framework.response import Response
from .serializers import CommunityJoinSerializer, CommunityMemberListSerializer, CommunityMemberSerializer, CommunitySessionSerializer, MyRegistrationSerializer, SubscribedUsersSerializer, EventsSerializer,EventRegistrationSerializer,CommunityProfileSerializer
from .models import CommunityMember, SubscribedUsers, Events,EventRegistration,CommunityProfile
from django.core.mail import send_mail, EmailMessage
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.files import File
import base64
from rest_framework.decorators import action
import pandas as pd
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework.views import APIView

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.pagination import PageNumberPagination
import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
import pandas as pd
from rest_framework.parsers import MultiPartParser, FormParser
import logging
logger = logging.getLogger(__name__)
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.uploadedfile import InMemoryUploadedFile
import boto3
from django.db.models import Q 
from Club.models import ExecutiveMember

from .models import Events  # Assuming Events model is imported
from .serializers import EventsSerializer  # Assuming EventsSerializer is imported
from django.conf import settings
from django.shortcuts import get_object_or_404
s3_client = boto3.client('s3')
from Club.models import Club
from django.db import transaction
from account.models import User
from django.db import transaction, models

class EventPagination(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'message':'Events retrieved successfuly',
            'status':'success',
            'data':{
                'count':self.page.paginator.count,
                'next':self.get_next_link(),
                'previous':self.get_previous_link(),
                'results':data
            }
        })

def generate_s3_image_url(bucket_name, object_key):
    return f"https://{bucket_name}.s3.ap-southeast-2.amazonaws.com/{object_key}"



#this is the event with s3 functionality   
@method_decorator(csrf_exempt, name='dispatch') 
class EventViewSet(viewsets.ModelViewSet):
    queryset = Events.objects.all()
    serializer_class = EventsSerializer
    pagination_class = EventPagination
    parser_classes = (MultiPartParser, FormParser)

    @action(methods=['post'], detail=False, url_path='add', url_name='add-event')
    def create_event(self, request, *args, **kwargs):
        # Debugging output
        print("Files in request:", request.FILES)
        print("Data in request:", request.data)
        print("Content-Type:", request.content_type)

        # Extract form data and handle the file upload
        file = request.FILES.get('image')
        if not file:
            return JsonResponse({
                "message": "No image provided",
                "status": "error"
                }, status=400)
        
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        object_key = f"event_images/{file.name}"

        # Upload image to S3
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=file.read(),
                ContentType=file.content_type
            )
        except Exception as e:
            return JsonResponse({
                "message": f"Failed to upload image to S3: {str(e)}", 
                "status": "error"
                }, status=500)

        # Create event
        event_data = request.data
        event = Events.objects.create(
            name=event_data['name'],
            category=event_data['category'],
            title=event_data['title'],
            description=event_data['description'],
            date=event_data['date'],
            location=event_data['location'],
            organizer=event_data['organizer'],
            contact_email=event_data['contact_email'],
            is_virtual=event_data['is_virtual'],
            image_url=f"event_images/{file.name}"  # Store the image path in the event
        )

        # Construct the image URL
        image_url = generate_s3_image_url(bucket_name, object_key)

        response_data = {
            'message': 'Event Created successfully',
            'status': 'success',
            "data": {
                "id": event.id,
                "image_url": image_url,
                "name": event.name,
                "category": event.category,
                "title": event.title,
                "description": event.description,
                "date": event.date,
                "location": event.location,
                "organizer": event.organizer,
                "contact_email": event.contact_email,
                "is_virtual": event.is_virtual,
            }
        }

        return JsonResponse(response_data)

    
    @action(methods=['put', 'patch'], detail=True, url_path='update', url_name='update-event')
    def update_event(self, request, *args, **kwargs):
        partial = kwargs.get('partial', request.method == 'PATCH')
        instance = self.get_object()
        
        # Handle file upload if image is in the request
        file = request.FILES.get('image')
        if file:
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            object_key = f"event_images/{file.name}"

            try:
                # Upload image to S3
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=object_key,
                    Body=file.read(),
                    ContentType=file.content_type
                )
                
                # Update image_url field in the data
                mutable_data = request.data.copy()
                mutable_data['image_url'] = f"event_images/{file.name}"
                
                # Use modified data for serializer
                serializer = self.get_serializer(instance, data=mutable_data, partial=partial)
            except Exception as e:
                return Response({
                    "message": f"Failed to upload image to S3: {str(e)}", 
                    "status": "error",
                    "data": None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # No new image, just update other fields
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            event_instance = serializer.save()
            
            # If image was updated, include the full URL in response
            if file:
                image_url = generate_s3_image_url(bucket_name, object_key)
                response_data = EventsSerializer(event_instance).data
                response_data['image_url'] = image_url
            else:
                response_data = EventsSerializer(event_instance).data
                
            return Response({
                'message': 'Event Updated Successfully',
                'status': 'success',
                'data': response_data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'message': 'Event update failed',
            'status': 'error',
            'errors': serializer.errors,
            'data': None
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='list', url_name='list-events')
    def list_events(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Debug: Print raw image_url values from database
        for event in queryset:
            print(f"Event {event.id} has image_url in DB: {event.image_url}")
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            
            # Debug: Print serialized data before returning
            for item in serializer.data:
                print(f"Serialized event {item['id']} has image_url: {item.get('image_url')}")
            
            return self.get_paginated_response(serializer.data)
            
        # Fallback in case pagination fails or is disabled
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'Events retrieved successfully',
            'status': 'success',
            'data': {
                'count': queryset.count(),
                'next': None,
                'previous': None,
                'results': serializer.data
            }
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], url_path='delete', url_name='delete-event')
    def destroy_event(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
            return Response({
                'message':'Event deleted successfully',
                'status':'success',
                'data':None
            },status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                'message':'Error deleting the event',
                'status':'failed',
                'data':None
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='view', url_name='view-event')
    def retrieve_event(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return Response({
                'message':'Event details fetched successfully',
                'status':'success',
                'data':serializer.data
            },status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'message':'Event not found',
                'status':'failed',
                'data':None
            },status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'message':f'Error fetching thr event:{str(e)}',
                'status':'failed',
                'data':None
            },status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='by-name', url_name='event-by-name')
    def get_event_by_name(self, request):
        try:
            event_name = request.query_params.get('name')
            print(f"Searching for event with name: {event_name}")  # Debug print
            
            if not event_name:
                return Response({
                    'message': 'Name parameter is required',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            instance = Events.objects.filter(
                Q(name__iexact=event_name) |
                Q(name__icontains=event_name)
            ).first()
            
            if not instance:
                return Response({
                    'message': f'Event with name "{event_name}" not found',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(instance)
            
            return Response({
                'message': 'Event details fetched successfully',
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error in get_event_by_name: {str(e)}")  # Debug print
            return Response({
                'message': f'Error fetching the event: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    


class NewsletterSendView(views.APIView):
    def post(self, request):
        subject = request.data.get('subject')
        message = request.data.get('message')

        # Retrieve all subscribed email addresses
        subscribed_emails = list(SubscribedUsers.objects.values_list('email', flat=True))

        user_email = request.user.email if request.user.is_authenticated and request.user.email else 'default@example.com'
        mail = EmailMessage(subject, message, f"Meru University Science Innovators Club <{user_email}>", bcc=subscribed_emails)
        mail.content_subtype = 'html'

        if mail.send():
            return Response({'message': 'Email sent successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'There was an error sending the email'}, status=status.HTTP_400_BAD_REQUEST)

class SubscribeView(views.APIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({'message': 'Please enter a valid email address to subscribe to our Newsletters!'}, status=status.HTTP_400_BAD_REQUEST)

        if SubscribedUsers.objects.filter(email=email).exists():
            return Response({'message': f'{email} email address is already a subscriber'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email(email)
        except ValidationError as e:
            return Response({'message': e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

        subscribe_model_instance = SubscribedUsers(email=email)
        subscribe_model_instance.save()

        return Response({'message': f'{email} email was successfully subscribed to our newsletter!'}, status=status.HTTP_201_CREATED)

class ContactView(views.APIView):
    def post(self, request):
        message_name = request.data.get('name')
        message_email = request.data.get('email')
        message = request.data.get('message')

        send_mail(
            message_name,
            message,
            message_email,
            ['ondeyostephen0@gmail.com']
        )

        return Response({'message_name': message_name}, status=status.HTTP_200_OK)
    

class EventRegistrationViewSet(viewsets.ModelViewSet):
    queryset = EventRegistration.objects.all()
    serializer_class = EventRegistrationSerializer

    def create(self,request,*args,**kwargs):
        event_pk = self.kwargs.get('event_pk')
        if not event_pk:
            return Response({
                "message":"Event ID missing in the request URL",
                "status":"failed",
                "data":None
            },status=status.HTTP_400_BAD_REQUEST)
        
        # Get email from request data
        email = request.data.get('email')
        if not email:
            return Response({
                "message":"Email is required for registration",
                "status":"failed",
                "data":None
            },status=status.HTTP_400_BAD_REQUEST)

        mutable_data = request.data.copy()
        mutable_data['event'] = event_pk

        serializer = self.get_serializer(data=mutable_data)

        if serializer.is_valid():
            try:
                if request.user.is_authenticated:
                    registration = serializer.save(user=request.user)
                else:
                    registration = serializer.save()

                event = registration.event

               

                return Response({
                    "message":"successfully registered for the event",
                    "status":"success",
                    "data":{
                    "eventName": event.name,
                    "eventDescription": event.description,
                    "eventLocation": event.location,
                    "eventDate": event.date.isoformat(),
                    "course": registration.course,
                    "educational_level": registration.educational_level,
                    "email": registration.email,
                    "event": event.id,
                    "expectations": registration.expectations,
                    "full_name": registration.full_name,
                    "phone_number": registration.phone_number,
                    "registration_timestamp": registration.registration_timestamp.isoformat(),
                    "ticket_number": str(registration.ticket_number),
                    "uid": str(registration.uid)
                    }
                },status=status.HTTP_201_CREATED)  
            except Exception as e:
                traceback.print_exc()
                print(f'Error during registration process:{str(e)}')
                return Response({
                    "message":f'An error occured registration:{str(e)}',
                    "status":"failed",
                    "data":None
                },status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        error_messages = "\n".join(
            f"{field}: {', '.join(errors)}" for field, errors in serializer.errors.items()
        )
        return Response({
            'message': f'Event registration failed: {error_messages}',
            'status': 'failed',
            'data': None
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='user-registrations')
    def get_user_registered_events(self, request):
        try:
            # Get email from query params
            email = request.query_params.get('email')
            if not email:
                return Response({
                    'message': 'Email parameter is required',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get all registrations for this email
            registrations = EventRegistration.objects.filter(email=email)

            if not registrations.exists():
                return Response({
                    'message': 'No registered events found for this email',
                    'status': 'success',
                    'data': []
                }, status=status.HTTP_200_OK)

            # Serialize the registrations
            serializer = EventRegistrationSerializer(registrations, many=True)
            return Response({
                'message': 'Registered events retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'message': f'Error retrieving events: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
    
    @action(detail=False, methods=['get'], url_path='user-events/(?P<user_id>\d+)')
    def get_events_by_user_id(self, request, user_id=None, *args, **kwargs):
        try:
            # Validate user_id is provided
            if not user_id:
                return Response({
                    'message': 'User ID is required',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            # First, get the user's email based on their ID
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                user_email = user.email
            except User.DoesNotExist:
                return Response({
                    'message': 'User not found',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Now use the email to find all registrations
            registrations = EventRegistration.objects.filter(email=user_email)

            if not registrations.exists():
                return Response({
                    'message': 'No registrations found for this user',
                    'status': 'success',
                    'data': []
                }, status=status.HTTP_200_OK)

            # Serialize the registrations
            serializer = self.get_serializer(registrations, many=True)
            
            return Response({
                'message': 'User registrations retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'message': f'Error retrieving registrations: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
    @action(detail=False, methods=['get'], url_path='my-registrations')
    def get_my_registrations(self, request, *args, **kwargs):
        try:
            # Ensure user is authenticated
            if not request.user.is_authenticated:
                return Response({
                    'message': 'Authentication required',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Only filter by user, not by email
            registrations = EventRegistration.objects.filter(user=request.user).select_related('event')
            
            if not registrations.exists():
                return Response({
                    'message': 'You have no registered events',
                    'status': 'success',
                    'data': []
                }, status=status.HTTP_200_OK)
            
            # Serialize all registrations
            serializer = MyRegistrationSerializer(registrations, many=True)
            
            return Response({
                'message': 'Your registered events retrieved successfully',
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'message': f'Error retrieving your registrations: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_queryset(self):
        event_pk = self.kwargs.get('event_pk')
        if event_pk:
            return EventRegistration.objects.filter(event_id=event_pk)
        return super().get_queryset()
    
    
    def list(self,request,*args,**kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page,many=True)
                paginated_data = self.paginator.get_paginated_response(serializer.data)

                return Response({
                    'message':'Event registrations retrieved successfully',
                    'status':'success',
                    'data':{
                        'count':paginated_data.data['count'],
                        'next':paginated_data.data['next'],
                        'previous':paginated_data.data['previous'],
                        'results':paginated_data.data['results']
                    }
                },status=status.HTTP_200_OK)
            serializer = self.get_serializer(queryset,many=True)
            return Response({
                'message':'Event registrations retrieved successfully',
                'status':'success',
                'data':{
                    'count':len(serializer.data),
                    'next':None,
                    'previous':None,
                    'data':serializer.data
                }
            },status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'message':f'Error retreiving registrations:{str(e)}',
                'status':'failed',
                'data':None
            },status=status.HTTP_400_BAD_REQUEST)
        

    
    

    
    @action(detail=False, methods=['get'], url_path='export')
    def export_registrations(self, request, event_pk=None):
        if not event_pk:
            return Response({"error": "Event ID is required"}, status=400)
        
        registrations = EventRegistration.objects.filter(event_id=event_pk)
    
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="event_{event_pk}_registrations.csv"'
    
        writer = csv.writer(response)
        writer.writerow((
            'UID', 
            'Full Name', 
            'Email', 
            'Course',
            'Educational Level',
            'Phone Number',
            'Expectations',
            'Registration Date',
            'Ticket Number'
        ))
    
        for registration in registrations:
            writer.writerow((
                registration.uid, 
                registration.full_name, 
                registration.email, 
                registration.course,
                registration.educational_level,
                registration.phone_number,
                registration.expectations,
                registration.registration_timestamp,
                registration.ticket_number
            ))
    
        return response

DEFAULT_CLUB_ID = 1
class CommunityProfileViewSet(viewsets.ModelViewSet):
    queryset = CommunityProfile.objects.all().order_by('id')
    serializer_class = CommunityProfileSerializer

    def create(self, request, *args, **kwargs):
        print(f"View - Request data: {request.data}")
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                print(f"View - Initial data: {serializer.initial_data}")
                if serializer.is_valid():
                    print(f"View - Validated data: {serializer.validated_data}")

                    # Validate executive conflicts using IDs
                    community_lead_id = serializer.validated_data.get('community_lead')
                    co_lead_id = serializer.validated_data.get('co_lead')
                    secretary_id = serializer.validated_data.get('secretary')

                    # Check if any of the users are already executives
                    if community_lead_id:
                        community_lead = get_object_or_404(User, id=community_lead_id)
                        if ExecutiveMember.objects.filter(user=community_lead).exists():
                            return Response({
                                'message': f'User {community_lead.email} is already an executive in another community',
                                'status': 'failed',
                                'data': None
                            }, status=status.HTTP_400_BAD_REQUEST)

                    if co_lead_id:
                        co_lead = get_object_or_404(User, id=co_lead_id)
                        if ExecutiveMember.objects.filter(user=co_lead).exists():
                            return Response({
                                'message': f'User {co_lead.email} is already an executive in another community',
                                'status': 'failed',
                                'data': None
                            }, status=status.HTTP_400_BAD_REQUEST)

                    if secretary_id:
                        secretary = get_object_or_404(User, id=secretary_id)
                        if ExecutiveMember.objects.filter(user=secretary).exists():
                            return Response({
                                'message': f'User {secretary.email} is already an executive in another community',
                                'status': 'failed',
                                'data': None
                            }, status=status.HTTP_400_BAD_REQUEST)

                    community = serializer.save()
                    print(f"View - Community created: {community}")

                    return Response({
                        'message': 'Community created successfully',
                        'status': 'success',
                        'data': self.get_serializer(community).data
                    }, status=status.HTTP_201_CREATED)

                error_messages = "\n".join(
                    f"{field}: {', '.join(errors)}" for field, errors in serializer.errors.items()
                )
                print(f"View - Validation errors: {serializer.errors}")
                return Response({
                    'message': f'Community creation failed: {error_messages}',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"View - Exception: {str(e)}")
            return Response({
                'message': f'Error creating community: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=True)
                
                if serializer.is_valid():
                    # Validate executive conflicts using IDs
                    community_lead_id = serializer.validated_data.get('community_lead')
                    co_lead_id = serializer.validated_data.get('co_lead')
                    secretary_id = serializer.validated_data.get('secretary')

                    # Check if any new executives are already executives in other communities
                    if community_lead_id and community_lead_id != instance.community_lead_id:
                        community_lead = get_object_or_404(User, id=community_lead_id)
                        if ExecutiveMember.objects.filter(user=community_lead).exclude(community=instance).exists():
                            return Response({
                                'message': f'User {community_lead.email} is already an executive in another community',
                                'status': 'failed',
                                'data': None
                            }, status=status.HTTP_400_BAD_REQUEST)

                    if co_lead_id and co_lead_id != instance.co_lead_id:
                        co_lead = get_object_or_404(User, id=co_lead_id)
                        if ExecutiveMember.objects.filter(user=co_lead).exclude(community=instance).exists():
                            return Response({
                                'message': f'User {co_lead.email} is already an executive in another community',
                                'status': 'failed',
                                'data': None
                            }, status=status.HTTP_400_BAD_REQUEST)

                    if secretary_id and secretary_id != instance.secretary_id:
                        secretary = get_object_or_404(User, id=secretary_id)
                        if ExecutiveMember.objects.filter(user=secretary).exclude(community=instance).exists():
                            return Response({
                                'message': f'User {secretary.email} is already an executive in another community',
                                'status': 'failed',
                                'data': None
                            }, status=status.HTTP_400_BAD_REQUEST)

                    updated_community = serializer.save()
                    
                    return Response({
                        'message': 'Community updated successfully',
                        'status': 'success',
                        'data': self.get_serializer(updated_community).data
                    }, status=status.HTTP_200_OK)

                error_messages = "\n".join(
                    f"{field}: {', '.join(errors)}" for field, errors in serializer.errors.items()
                )
                return Response({
                    'message': f'Community update failed: {error_messages}',
                    'status': 'failed',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'message': f'Error updating community: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self,request,*args,**kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page,many=True)
                paginated_data = self.paginator.get_paginated_response(serializer.data)

                return Response({
                    'message':'Communities retrieved successfully',
                    'status':'success',
                    'data':{
                        'count':paginated_data.data['count'],
                        'next':paginated_data.data['next'],
                        'previous':paginated_data.data['previous'],
                        'results':paginated_data.data['results']
                    }
                },status=status.HTTP_200_OK)
            serializer = self.get_serializer(queryset,many=True)
            return Response({
                'message':'Communities retrieved successfully',
                'status':'success',
                'data':serializer.data
            },status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'message':f'Error retrieving communities',
                'status':'failed',
                'data':None
            },status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return Response({
                'message':'Community retrieved successfully',
                'status':'success',
                'data':serializer.data
            },status=status.HTTP_200_OK)
        except CommunityProfile.DoesNotExist:
            return Response({
                'message':'Community not found',
                'status':'failed',
                'data':None
            },status=status.HTTP_400_BAD_REQUEST)
        
    
    def perfom_update(self,request,*args,**kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data,partial=True)
            if serializer.is_valid():
                self.perfom_update(serializer)
                return Response({
                    "message":"Community updated successfully",
                    "status":"success",
                    "data":serializer.data
                },status=status.HTTP_200_OK)
            
            error_messages = "\n".join(
                f"{field}:{', '.join(errors)}" for field, errors in serializer.errors.item()
            )
            return Response({
                "message":f'community update failed:{error_messages}',
                "status":"failed",
                "data":None
            },status=status.HTTP_400_BAD_REQUEST)
        except CommunityProfile.DoesNotExist:
            return Response({
                "message":f'Community not found',
                "status":"failed",
                "data":None
            },status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "message":f'Error updating community: {str(e)}',
                "status":"failed",
                "data":None
            },status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['get'], url_path='search-community')
    def search_by_name(self,request,name=None):
        try:
            name = request.query_params.get('name',None)
            if not name:
                return Response({
                    "message":"Pleasee provide a community name too search",
                    "status":"failed",
                    "data":None
                },status=status.HTTP_400_BAD_REQUEST)
            community = CommunityProfile.objects.get(name__iexact=name)
            serializer = self.get_serializer(community)
            return Response({
                "name":"Community retrieved successfully",
                "status":"success",
                "data":serializer.data
            },status=status.HTTP_200_OK)
        except CommunityProfile.DoesNotExist:
            return Response({
                "message":f'community with name "{name}" not found',
                "status":"failed",
                "data":None
            },status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "message":f'Error retrieving community:{str(e)}',
                "status":"failed",
                "data":None
            },status=status.HTTP_400_BAD_REQUEST)
        
    
class SessionCreateView(APIView):
    def post(self, request, community_id):
        try:
            # Retrieve the community by its ID
            community = CommunityProfile.objects.get(id=community_id)
            
            # Serialize the session data
            session_serializer = CommunityProfileSerializer(data=request.data, context={'request': request})
            if session_serializer.is_valid():
                # Save the session and associate it with the community
                session_serializer.save(community=community)
                #return Response(session_serializer.data, status=status.HTTP_201_CREATED)
                return Response({
                    'message':'Session Updated Successfully',
                    'status':'success',
                    'data':session_serializer.data
                },status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'message':session_serializer.errors,
                    'status':'failed',
                    'data':None
                })
            

        except CommunityProfile.DoesNotExist:
            return Response({
                'message':'Commmunity not found',
                'status':'failed',
                'data':None
            },status=status.HTTP_400_BAD_REQUEST)
            
        

    

class CommunityMembersView(APIView):
    def get(self, request, pk):
        try:
            community = CommunityProfile.objects.get(pk=pk)
        except CommunityProfile.DoesNotExist:
            return Response({"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND)

        members = community.members.all()  # Fetch related members
        serializer = CommunityMemberSerializer(members, many=True)
        return Response({
            'message':'Members retrieved successfully',
            'status':'success',
            'data':serializer.data
        },status=status.HTTP_200_OK)
        
    

class JoinCommunityView(APIView):
    def post(self, request, *args, **kwargs):
        community_id = kwargs.get('pk')
        user_email = request.data.get('email')
        
        try:
            community = CommunityProfile.objects.get(id=community_id)
        except CommunityProfile.DoesNotExist:
            return Response(
                {"error": "Community not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        # count the number of communities the user has joined
        user_community_count = CommunityMember.objects.filter(email=user_email).count()

        if user_community_count >= 3:
            return Response({
                "message": "You cannot join more than 3 communities."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CommunityJoinSerializer(data={
            'community': community.id,
            'name': request.data.get('name'),
            'email': request.data.get('email')
        })
        
        if serializer.is_valid():
            member = serializer.save(community=community)
            community.update_total_members()
            
            # Get updated community with members list
            community_serializer = CommunityProfileSerializer(community)
            
            return Response({
                "message": "Successfully joined the community!",
                'status': 'success',
                'data': community_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'message': f'There was an error please try again: {serializer.errors}',
            'status': 'failed',
            'data': None
        }, status=status.HTTP_400_BAD_REQUEST)
    
class CommunityMembersView(APIView):
    def get(self, request, pk=None):
        try:
            community = CommunityProfile.objects.get(id=pk)
            members = community.members.all()
            serializer = CommunityMemberListSerializer(members, many=True)
            
            return Response({
                'status': 'success',
                'total_members': members.count(),
                'data': serializer.data
            })
            
        except CommunityProfile.DoesNotExist:
            return Response({
                'status': 'failed',
                'message': 'Community not found'
            }, status=status.HTTP_404_NOT_FOUND)


