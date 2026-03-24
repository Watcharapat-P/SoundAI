from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from myapp.models.user import User
from myapp.models.generation_request import GenerationRequest
from .helpers import parse_json_body, validation_error_response


def _serialize(r):
    return {
        'id': str(r.id),
        'owner_id': str(r.owner_id),
        'occasion': r.occasion,
        'mood': r.mood,
        'genre': r.genre,
        'requested_duration_seconds': r.requested_duration_seconds,
        'created_at': r.created_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
def request_list(request):
    """
    GET  /api/requests/  — list all generation requests
    POST /api/requests/  — create a generation request
    """
    if request.method == 'GET':
        qs = GenerationRequest.objects.select_related('owner').order_by('-created_at')
        return JsonResponse({'generation_requests': [_serialize(r) for r in qs]})

    try:
        data = parse_json_body(request)
        owner = get_object_or_404(User, pk=data['owner_id'])
        gen_req = GenerationRequest(
            owner=owner,
            occasion=data['occasion'],
            mood=data['mood'],
            genre=data['genre'],
            requested_duration_seconds=int(data['requested_duration_seconds']),
        )
        gen_req.full_clean()
        gen_req.save()
        return JsonResponse(_serialize(gen_req), status=201)
    except (KeyError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except ValidationError as e:
        return validation_error_response(e)


@csrf_exempt
@require_http_methods(["GET", "DELETE"])
def request_detail(request, pk):
    """
    GET    /api/requests/<id>/  — retrieve a generation request
    DELETE /api/requests/<id>/  — delete a generation request
    """
    gen_req = get_object_or_404(GenerationRequest, pk=pk)

    if request.method == 'GET':
        return JsonResponse(_serialize(gen_req))

    gen_req.delete()
    return JsonResponse({'deleted': str(pk)})
