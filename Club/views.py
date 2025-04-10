from django.shortcuts import get_object_or_404
from rest_framework import generics,status,viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Club,ExecutiveMember
from .serializers import ClubSerializer, ExecutiveMemberSerializer
from rest_framework.decorators import action
# Create your views here.

# Default club ID (Meru University Science Innovators Club)
DEFAULT_CLUB_ID = 1

class ClubDetailView(APIView):

    def post(self,request):
    # Create a neww club
        serializer = ClubSerializer(data=request.data)
        if serializer.is_valid():
            club = serializer.save()
            return Response({
                'messsage':'Club created succssfully',
                'status':'succcess',
                'data':serializer.data
            },status=status.HTTP_201_CREATED)
        return Response({
            'message':f'Club Creation failed:{serializer.errors}',
            'status':'failed',
            'data':None
        },status=status.HTTP_400_BAD_REQUEST)
    """
    Vieww to retrieve, update , or delete club details
    Since we're only dealing with one club, we'll always use the default ID.
    """

    def get(self, request):
        club = get_object_or_404(
            Club.objects.prefetch_related(
                'communities',
                'communities__community_lead',
                'communities__co_lead',
                'communities__secretary',
                'communities__social_media',
                'communities__members',
                'communities__sessions'
            ), 
        id=DEFAULT_CLUB_ID
    )
        serializer = ClubSerializer(club)
        return Response({
            'message': 'Club retrieved successfully',
            'status': 'success',
            'data': serializer.data
        })

    def put(self, request):
        club = get_object_or_404(Club, id=DEFAULT_CLUB_ID)
        serializer = ClubSerializer(club, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Club updated successfully',
                'status': 'success',
                'data': serializer.data
            })
        return Response({
            'message': f'Club update failed: {serializer.errors}',
            'status': 'failed',
            'data': None
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        club = get_object_or_404(Club, id=DEFAULT_CLUB_ID)
        club.delete()
        return Response({
            'message': 'Club deleted successfully',
            'status': 'success',
            'data': None
        }, status=status.HTTP_204_NO_CONTENT)

class ExecutiveMemberViewSet(viewsets.ModelViewSet):
    queryset = ExecutiveMember.objects.all()
    serializer_class = ExecutiveMemberSerializer
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                self.perform_create(serializer)
                return Response({
                    'message': 'Executive member created successfully',
                    'status': 'success',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            error_messages = "\n".join(
                f"{field}: {', '.join(errors)}" for field, errors in serializer.errors.items()
            )
            return Response({
                'message': f'Executive member creation failed: {error_messages}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'message': f'Error creating executive member: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
            
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Executive members retrieved successfully',
            'status': 'success',
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'message': 'Executive member retrieved successfully',
            'status': 'success',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response({
                    'message': 'Executive member updated successfully',
                    'status': 'success',
                    'data': serializer.data
                })
            
            error_messages = "\n".join(
                f"{field}: {', '.join(errors)}" for field, errors in serializer.errors.items()
            )
            return Response({
                'message': f'Executive member update failed: {error_messages}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'message': f'Error updating executive member: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
            
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({
                'message': 'Executive member deleted successfully',
                'status': 'success',
                'data': None
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({
                'message': f'Error deleting executive member: {str(e)}',
                'status': 'failed',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['post'], url_path='check-email')
    def check_email(self,request):
        try:
            email = request.data.get('email')

            if not email:
                return Response({
                    "message":"Email if required",
                    "status":"failed",
                    "data":None
                },status=status.HTTP_400_BAD_REQUEST)
            
            executive = ExecutiveMember.objects.filter(email=email).first()

            if executive:
                serializer = self.get_serializer(executive)
                return Response({
                    "message":"User is an executive member",
                    "status":"success",
                    "data":serializer.data,
                    "is_executive":True
                })
            else:
                return Response({
                    "message":"User is not an executive member",
                    "status":"success",
                    "data":None,
                    "is_executive":False
                })
        except Exception as e:
            return Response({
                "message":f'Error checking executive status',
                "status":"failed",
                "data":None,
            }, status=status.HTTP_400_BAD_REQUEST)
        