from django.urls import path
from . import views

# Namespace: API endpoints are reachable as `{% url 'api:track-list' %}` etc.
# This prevents collisions with the frontend URL names that use the same labels
# (e.g. 'track-list' for the HTML page in soundai/urls.py).
app_name = 'api'

urlpatterns = [
    # Users
    path('users/',              views.user_list,    name='user-list'),
    path('users/<uuid:pk>/',    views.user_detail,  name='user-detail'),

    # Generation Requests
    path('requests/',           views.request_list,   name='request-list'),
    path('requests/<uuid:pk>/', views.request_detail, name='request-detail'),

    # Tracks
    path('tracks/',             views.track_list,   name='track-list'),
    path('tracks/<uuid:pk>/',   views.track_detail, name='track-detail'),

    # Generation (triggers active strategy: mock or suno)
    path('requests/<uuid:pk>/generate/', views.generate_track, name='generate-track'),

    # Share Links
    path('share-links/',              views.sharelink_list,   name='sharelink-list'),
    path('share-links/<uuid:pk>/',    views.sharelink_detail, name='sharelink-detail'),
    path('share-links/<uuid:pk>/revoke/', views.sharelink_revoke, name='sharelink-revoke'),
    # Public share endpoint (no auth required)
    path('s/<str:token>/',      views.public_share,  name='public-share'),
]