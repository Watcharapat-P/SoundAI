from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.exceptions import ValidationError

from myapp.models import User, GenerationRequest, Track, ShareLink
from myapp.services.generation_service import generate_track_from_request
from myapp.strategies.exceptions import (
    SunoOfflineError,
    SunoInsufficientCreditsError,
)


def _is_admin(request) -> bool:
    """True if the current session user's email is in settings.ADMIN_EMAILS."""
    email = (request.session.get('user_email') or '').strip().lower()
    return bool(email) and email in getattr(settings, 'ADMIN_EMAILS', [])


@require_http_methods(["GET", "POST"])
def home(request):
    """Render the home page with recent tracks and handle form submission"""
    # Scope tracks to the signed-in user when available; otherwise show recent
    user_id = request.session.get('user_id')
    if user_id:
        tracks = (Track.objects
                  .filter(owner_id=user_id)
                  .select_related('owner', 'generation_request')
                  .order_by('-created_at')[:10])
    else:
        tracks = (Track.objects
                  .select_related('owner', 'generation_request')
                  .order_by('-created_at')[:10])

    if request.method == 'POST':
        # Require login to generate
        if not user_id:
            messages.error(request, 'Please sign in to generate music.')
            return redirect('login')

        try:
            user = User.objects.get(pk=user_id)

            # Step 1: create the GenerationRequest (the AI parameters)
            gen_req = GenerationRequest(
                owner=user,
                song_title=request.POST.get('song_title', ''),
                occasion=request.POST.get('occasion'),
                mood=request.POST.get('mood'),
                genre=request.POST.get('genre'),
                requested_duration_seconds=int(request.POST.get('requested_duration_seconds', 180))
            )
            gen_req.full_clean()
            gen_req.save()

            # Step 2: hand the request off to the active strategy
            # (mock or suno — selected centrally by GENERATOR_STRATEGY).
            # This is what actually creates the Track.
            try:
                track = generate_track_from_request(gen_req)
            except SunoOfflineError as e:
                messages.error(request, f'Suno service unavailable: {e}')
                return redirect('home')
            except SunoInsufficientCreditsError as e:
                messages.error(request, f'Suno credits exhausted: {e}')
                return redirect('home')
            except Exception as e:
                # Surface unexpected strategy errors instead of silently swallowing them
                messages.error(request, f'Generation failed: {e}')
                return redirect('home')

            if track.status == 'pending':
                messages.success(
                    request,
                    f'Track "{track.title}" is generating (Suno taskId: {track.task_id}). '
                    'Refresh in a few minutes to see the finished audio.'
                )
            else:
                messages.success(
                    request,
                    f'Track "{track.title}" generated successfully!'
                )
            return redirect('track-detail', pk=track.id)
        except User.DoesNotExist:
            request.session.flush()
            messages.error(request, 'Your session expired. Please sign in again.')
            return redirect('login')
        except ValidationError as e:
            messages.error(request, f'Validation Error: {e.message}')
        except (KeyError, ValueError) as e:
            messages.error(request, f'Error: Invalid form data - {str(e)}')

    return render(request, 'home.html', {'tracks': tracks})


@require_http_methods(["GET"])
def track_list_view(request):
    """Display the signed-in user's tracks ('My Tracks').
    Anonymous visitors see the latest tracks across the system."""
    user_id = request.session.get('user_id')
    qs = Track.objects.select_related('owner', 'generation_request')
    if user_id:
        qs = qs.filter(owner_id=user_id)
    tracks = qs.order_by('-created_at')
    return render(request, 'track_list.html', {'tracks': tracks})


@require_http_methods(["GET"])
def track_detail_view(request, pk):
    """Display details for a single track"""
    track = get_object_or_404(Track, pk=pk)
    return render(request, 'track_detail.html', {'track': track})


@require_http_methods(["GET"])
def request_list_view(request):
    """Display the signed-in user's generation requests."""
    user_id = request.session.get('user_id')
    qs = GenerationRequest.objects.select_related('owner')
    if user_id:
        qs = qs.filter(owner_id=user_id)
    requests = qs.order_by('-created_at')
    return render(request, 'request_list.html', {'requests': requests})


@require_http_methods(["GET"])
def request_detail_view(request, pk):
    """Display details for a single generation request"""
    request_obj = get_object_or_404(GenerationRequest, pk=pk)
    track = request_obj.track if hasattr(request_obj, 'track') else None
    return render(request, 'request_detail.html', {
        'request_obj': request_obj,
        'track': track
    })


@require_http_methods(["GET"])
def user_list_view(request):
    """
    Admins → see every registered user.
    Regular signed-in users → redirected to their own profile.
    Anonymous → redirected to login.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please sign in to view your profile.')
        return redirect('login')

    if not _is_admin(request):
        # Non-admins go straight to their own profile
        return redirect('user-detail', pk=user_id)

    users = User.objects.order_by('-created_at')
    return render(request, 'user_list.html', {'users': users})


@require_http_methods(["GET"])
def user_detail_view(request, pk):
    """
    A profile page is visible to:
      - the user themselves
      - any admin
    Anonymous visitors are sent to login. Non-admin users trying to view
    someone else's profile are bounced to their own.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please sign in to view profiles.')
        return redirect('login')

    if str(pk) != str(user_id) and not _is_admin(request):
        messages.error(request, "You can only view your own profile.")
        return redirect('user-detail', pk=user_id)

    user = get_object_or_404(User, pk=pk)
    generation_requests_count = user.generation_requests.count()
    tracks_count = user.tracks.count()
    share_links_count = ShareLink.objects.filter(track__owner=user).count()
    user_tracks = user.tracks.order_by('-created_at')[:10]

    return render(request, 'user_detail.html', {
        'user': user,
        'generation_requests_count': generation_requests_count,
        'tracks_count': tracks_count,
        'share_links_count': share_links_count,
        'user_tracks': user_tracks,
        'is_self': str(pk) == str(user_id),
    })


@require_http_methods(["GET", "POST"])
def sharelink_list_view(request):
    """Display and create share links"""
    share_links = ShareLink.objects.select_related('track', 'track__owner').order_by('-created_at')
    available_tracks = Track.objects.filter(status='completed').select_related('owner').order_by('-created_at')
    
    if request.method == 'POST':
        track_id = request.POST.get('track_id')
        if track_id:
            track = get_object_or_404(Track, pk=track_id)
            share_link = ShareLink.objects.create(track=track)
            site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
            return render(request, 'sharelink_list.html', {
                'share_links': share_links,
                'available_tracks': available_tracks,
                'success': f'Share link created! Share this: {site_url}/s/{share_link.token}/'
            })
    
    return render(request, 'sharelink_list.html', {
        'share_links': share_links,
        'available_tracks': available_tracks
    })


@require_http_methods(["GET"])
def sharelink_detail_view(request, pk):
    """Display details for a single share link"""
    share_link = get_object_or_404(ShareLink, pk=pk)
    return render(request, 'sharelink_detail.html', {'sharelink': share_link})


@require_http_methods(["GET"])
def sharelink_revoke_view(request, pk):
    """Revoke a share link"""
    from django.shortcuts import redirect
    
    share_link = get_object_or_404(ShareLink, pk=pk)
    share_link.revoke()
    return redirect('sharelink-list')


@require_http_methods(["GET"])
def public_share_view(request, token):
    """Display public share page for a track"""
    share_link = get_object_or_404(ShareLink, token=token)
    return render(request, 'public_share.html', {'track': share_link.track})
