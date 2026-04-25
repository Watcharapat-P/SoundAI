from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404

from myapp.models.generation_request import GenerationRequest
from myapp.services.generation_service import generate_track_from_request
from myapp.strategies.exceptions import SunoOfflineError, SunoInsufficientCreditsError


@csrf_exempt
@require_http_methods(["POST"])
def generate_track(request, pk):
    """
    POST /api/requests/<id>/generate/

    Triggers song generation for an existing GenerationRequest using the
    currently active strategy (mock or suno, set via GENERATOR_STRATEGY).

    Returns the created Track (status may be 'pending' for Suno mode).
    """
    generation_request = get_object_or_404(GenerationRequest, pk=pk)

    try:
        track = generate_track_from_request(generation_request)
    except SunoOfflineError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except SunoInsufficientCreditsError as e:
        return JsonResponse({"error": str(e)}, status=402)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(
        {
            "track": {
                "id": str(track.id),
                "owner_id": str(track.owner_id),
                "generation_request_id": str(track.generation_request_id),
                "title": track.title,
                "duration_seconds": track.duration_seconds,
                "audio_url": track.audio_url,
                "status": track.status,
                "task_id": track.task_id,
                "created_at": track.created_at.isoformat(),
                "updated_at": track.updated_at.isoformat(),
            }
        },
        status=201,
    )
