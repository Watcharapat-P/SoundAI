"""
URL configuration for soundai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from myapp.views.frontend_views import (
    home,
    track_list_view,
    track_detail_view,
    request_list_view,
    request_detail_view,
    user_list_view,
    user_detail_view,
    sharelink_list_view,
    sharelink_detail_view,
    sharelink_revoke_view,
    public_share_view,
)
from myapp.views.auth_views import (
    login_view,
    google_login,
    google_callback,
    logout_view,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('login/', login_view, name='login'),
    path('auth/google/', google_login, name='google-login'),
    path('auth/google/callback/', google_callback, name='google-callback'),
    path('logout/', logout_view, name='logout'),

    # Frontend views
    path('', home, name='home'),
    path('tracks/', track_list_view, name='track-list'),
    path('tracks/<uuid:pk>/', track_detail_view, name='track-detail'),
    path('requests/', request_list_view, name='request-list'),
    path('requests/<uuid:pk>/', request_detail_view, name='request-detail'),
    path('users/', user_list_view, name='user-list'),
    path('users/<uuid:pk>/', user_detail_view, name='user-detail'),
    path('share-links/', sharelink_list_view, name='sharelink-list'),
    path('share-links/<uuid:pk>/', sharelink_detail_view, name='sharelink-detail'),
    path('share-links/<uuid:pk>/revoke/', sharelink_revoke_view, name='sharelink-revoke'),
    path('s/<str:token>/', public_share_view, name='public-share'),
    
    # API endpoints
    path('api/', include('myapp.urls')),
]
