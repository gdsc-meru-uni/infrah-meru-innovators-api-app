from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from partners.views import PartnerViewSet
from Innovation_WebApp.views import (
    CommunityMembersView, 
    EventRegistrationViewSet,
    CommunityProfileViewSet,
    EventViewSet,
    SessionCreateView,
    JoinCommunityView,
)
# from AboutUs import urls
from Feedback import urls
from testimonials.views import TestimonialViewSet
# Main router
router = DefaultRouter()
router.register(r'event-registrations', EventRegistrationViewSet, basename='events_registration')
router.register(r'events', EventViewSet, basename='events')
router.register(r'communities', CommunityProfileViewSet)
router.register(r'testimonials', TestimonialViewSet)
router.register(r'partners', PartnerViewSet)
#router.register(r'community-members', CommunityMembersView, basename='community-members')



community_viewset = CommunityProfileViewSet.as_view({
    'post':'create',  # for /add-community/
    'get':'list',     # for /list-communities/
})

detail_viewset = CommunityProfileViewSet.as_view({
    'get':'retrieve',       # For /retrieve-community/<pk>/
    'put':'update',         # For /update-community/<pk>/
    'patch':'update',       # Partial update for /update-community/<pk>/
})

search_viewset = CommunityProfileViewSet.as_view({
    'get':'search_by_name',     # For /search-community/?name=<name>
})

# Nested router for event registrations
event_router = routers.NestedDefaultRouter(router, r'events', lookup='event')
event_router.register(r'registrations', EventRegistrationViewSet, basename='event-registrations')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Innovation_WebApp.urls')),
    path('api/', include('Api.urls')),
    path('comments/', include('comments.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    

    path('add-community/', community_viewset, name='add-community'),
    path('list-communities/', community_viewset, name='list-communities'),
    path('retrieve-community/<int:pk>/', detail_viewset, name='retrieve-community'),
    path('update-community/<int:pk>/', detail_viewset, name='update-community'),
    path('search-community/', search_viewset, name='search-community'),
    path('communities/<int:pk>/join/', JoinCommunityView.as_view(), name='join-community'),
    path('communities/<int:pk>/members/', CommunityMembersView.as_view(), name='community_members'),


    
    path('', include(router.urls)),
    path('', include(event_router.urls)),

    path('testimonies/', include('testimonials.urls')),


    path('', include('Feedback.urls')),
    path('comments/', include('comments.urls')),


    path('api/', include('Club.urls')),

    # path('api/',include('fcm_django.urls')),
]

