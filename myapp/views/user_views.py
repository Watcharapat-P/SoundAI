from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from myapp.models.user import User
from .helpers import parse_json_body, validation_error_response


def _serialize(u):
    return {
        'id': str(u.id),
        'google_id': u.google_id,
        'email': u.email,
        'total_storage_used': u.total_storage_used,
        'created_at': u.created_at.isoformat(),
        'updated_at': u.updated_at.isoformat(),
    }


@csrf_exempt
@require_http_methods(["GET", "POST"])
def user_list(request):
    """
    GET  /api/users/  — list all users
    POST /api/users/  — create a user
    """
    if request.method == 'GET':
        return JsonResponse({'users': [_serialize(u) for u in User.objects.all()]})

    try:
        data = parse_json_body(request)
        user = User(
            google_id=data['google_id'],
            email=data['email'],
            total_storage_used=data.get('total_storage_used', 0.0),
        )
        user.full_clean()
        user.save()
        return JsonResponse(_serialize(user), status=201)
    except (KeyError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)
    except ValidationError as e:
        return validation_error_response(e)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
def user_detail(request, pk):
    """
    GET    /api/users/<id>/  — retrieve a user
    PATCH  /api/users/<id>/  — update email or storage
    DELETE /api/users/<id>/  — delete user (cascades to Tracks + Requests)
    """
    user = get_object_or_404(User, pk=pk)

    if request.method == 'GET':
        return JsonResponse(_serialize(user))

    if request.method == 'PATCH':
        try:
            data = parse_json_body(request)
            for field in ('email', 'total_storage_used'):
                if field in data:
                    setattr(user, field, data[field])
            user.full_clean()
            user.save()
            return JsonResponse(_serialize(user))
        except (ValueError, ValidationError) as e:
            return JsonResponse({'error': str(e)}, status=400)

    user.delete()
    return JsonResponse({'deleted': str(pk)})
