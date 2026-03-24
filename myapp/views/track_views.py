from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from myapp.models.user import User
from myapp.models.generation_request import GenerationRequest
from myapp.models.track import Track
from .helpers import parse_json_body, validation_error_response


def _serialize(t):
    return {
        'id': str(t.id),
        'owner_id': str(t.owner_id),
        'generation_request_id': str(t.generation_request_id),
        'title': t.title,
        'duration_seconds': t.duration_seconds,
        'audio_url': t.audio_url,
        'status': t.status,
        'created_at': t.created_at.isoformat(),
        'updated_at': t.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
def track_list(request):
    """
    GET  /api/tracks/  — list all tracks
    POST /api/tracks/  — create a track
    """
    if request.method == 'GET':
        qs = Track.objects.select_related('owner', 'generation_request').order_by('-created_at')
        return JsonResponse({'tracks': [_serialize(t) for t in qs]})

    try:
        data = parse_json_body(request)
        owner = get_object_or_404(User, pk=data['owner_id'])
        gen_req = get_object_or_404(GenerationRequest, pk=data['generation_request_id'])

        # Domain invariant: track owner must match request owner
        if str(gen_req.owner_id) != str(owner.id):
            return JsonResponse(
                {'error': 'Track owner must match the GenerationRequest owner.'},
                status=422
            )

        track = Track(
            owner=owner,
            generation_request=gen_req,
            title=data['title'],
            duration_seconds=int(data['duration_seconds']),
            audio_url=data['audio_url'],
            status=data.get('status', 'pending'),
        )
        track.full_clean()
        track.save()
        return JsonResponse(_serialize(track), status=201)
    except (KeyError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except ValidationError as e:
        return validation_error_response(e)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def track_detail(request, pk):
    """
    GET    /api/tracks/<id>/  — retrieve a track
    PATCH  /api/tracks/<id>/  — update title, status, audio_url, duration_seconds
    DELETE /api/tracks/<id>/  — delete track (cascades ShareLinks; triggers S3 removal in prod)
    """
    track = get_object_or_404(Track, pk=pk)

    if request.method == 'GET':
        return JsonResponse(_serialize(track))

    if request.method == 'PATCH':
        try:
            data = parse_json_body(request)
            for field in ('title', 'status', 'audio_url', 'duration_seconds'):
                if field in data:
                    setattr(track, field, data[field])
            track.full_clean()
            track.save()
            return JsonResponse(_serialize(track))
        except (ValueError, ValidationError) as e:
            return JsonResponse({'error': str(e)}, status=400)

    # DELETE — in production, S3 deletion would be triggered here (FR4.3)
    track.delete()
    return JsonResponse({'deleted': str(pk)})
