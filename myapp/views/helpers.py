import json
from django.http import JsonResponse


def parse_json_body(request):
    """Parse request body as JSON dict, raise ValueError on failure."""
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Invalid JSON body.")


def validation_error_response(exc):
    """Turn a Django ValidationError into a 422 JsonResponse."""
    try:
        detail = exc.message_dict
    except AttributeError:
        detail = list(exc.messages)
    return JsonResponse({'error': detail}, status=422)
