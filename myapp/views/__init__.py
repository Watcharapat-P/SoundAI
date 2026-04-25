from .user_views import user_list, user_detail
from .generation_request_views import request_list, request_detail
from .track_views import track_list, track_detail
from .share_link_views import sharelink_list, sharelink_detail, sharelink_revoke, public_share
from .generation_views import generate_track
from .frontend_views import (
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
from .auth_views import (
    login_view,
    google_login,
    google_callback,
    logout_view,
)
