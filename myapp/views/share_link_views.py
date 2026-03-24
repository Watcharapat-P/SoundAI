from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from myapp.models.track import Track
from myapp.models.share_link import ShareLink
from .helpers import parse_json_body, validation_error_response


def _serialize(s):
    return {
        'id': str(s.id),
        'track_id': str(s.track_id),
        'token': s.token,
        'is_active': s.is_active,
        'is_valid': s.is_valid(),
        'expires_at': s.expires_at.isoformat() if s.expires_at else None,
        'created_at': s.created_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
def sharelink_list(request):
    """
    GET  /api/share-links/  — list all share links
    POST /api/share-links/  — create a share link for a completed track
    """
    if request.method == 'GET':
        qs = ShareLink.objects.select_related('track').order_by('-created_at')
        return JsonResponse({'share_links': [_serialize(s) for s in qs]})

    try:
        data = parse_json_body(request)
        track = get_object_or_404(Track, pk=data['track_id'])

        if track.status != 'completed':
            return JsonResponse(
                {'error': 'Only completed tracks can be shared.'},
                status=422
            )

        expires_at = parse_datetime(data['expires_at']) if data.get('expires_at') else None
        link = ShareLink(track=track, expires_at=expires_at)
        link.full_clean()
        link.save()
        return JsonResponse(_serialize(link), status=201)
    except (KeyError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except ValidationError as e:
        return validation_error_response(e)


@csrf_exempt
@require_http_methods(["GET", "DELETE"])
def sharelink_detail(request, pk):
    """
    GET    /api/share-links/<id>/  — retrieve a share link
    DELETE /api/share-links/<id>/  — permanently delete a share link
    """
    link = get_object_or_404(ShareLink, pk=pk)

    if request.method == 'GET':
        return JsonResponse(_serialize(link))

    link.delete()
    return JsonResponse({'deleted': str(pk)})


@csrf_exempt
@require_http_methods(["POST"])
def sharelink_revoke(request, pk):
    """POST /api/share-links/<id>/revoke/ — soft-revoke (is_active → False)."""
    link = get_object_or_404(ShareLink, pk=pk)
    link.revoke()
    return JsonResponse({'revoked': str(pk), 'is_active': False})


def public_share(request, token):
    """
    GET /api/s/<token>/
    Public endpoint — no authentication required (SRS Assumption 8.2.7).
    """
    try:
        link = ShareLink.objects.select_related('track').get(token=token)
    except ShareLink.DoesNotExist:
        return JsonResponse({'error': 'Share link not found.'}, status=404)

    if not link.is_valid():
        return JsonResponse({'error': 'This share link is no longer active.'}, status=410)

    t = link.track
    return JsonResponse({
        'track': {
            'title': t.title,
            'duration_seconds': t.duration_seconds,
            'audio_url': t.audio_url,
            'status': t.status,
        },
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
    })
