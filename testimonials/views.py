from rest_framework import viewsets,permissions,filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Testimonial
from django.db import models
from .serializers import TestimonialSerializer
from .permissions import IsAdminOrReadOnly,IsOwnerOrReadOnly

class TestimonialViewSet(viewsets.ModelViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    filter_backends = [filters.OrderingFilter]    
    ordering_fields = ['created_at', 'rating']
  


    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrReadOnly]
        elif self.action in ['approve', 'reject']:
            permission_classes = [permissions.IsAdminUser]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'list':
            permission_classes = []
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = Testimonial.objects.all()

        if self.request.user.is_staff:
            return queryset
        else:
            return queryset .filter(status=Testimonial.APPROVED)
        
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        testimonial = self.get_object()
        testimonial.status = Testimonial.APPROVED
        testimonial.save()
        return Response({'status': 'testimonial approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        testimonial = self.get_object()
        testimonial.status = Testimonial.REJECTED
        testimonial.save()
        return Response({'status': 'testimonial rejected'})
    


