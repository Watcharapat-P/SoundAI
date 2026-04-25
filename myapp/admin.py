from django.contrib import admin
from django.utils.html import format_html

from myapp.models.user import User
from myapp.models.generation_request import GenerationRequest
from myapp.models.track import Track
from myapp.models.share_link import ShareLink


# Inline Admin Classes

class TrackInline(admin.TabularInline):
    """Shows a user's tracks inline on the User detail page."""
    model = Track
    fields = ('title', 'status', 'duration_seconds', 'audio_url', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True


class GenerationRequestInline(admin.TabularInline):
    """Shows a user's generation requests inline on the User detail page."""
    model = GenerationRequest
    fields = ('occasion', 'mood', 'genre', 'requested_duration_seconds', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    show_change_link = True


class ShareLinkInline(admin.TabularInline):
    """Shows share links inline on the Track detail page."""
    model = ShareLink
    fields = ('token', 'is_active', 'expires_at', 'created_at')
    readonly_fields = ('token', 'created_at')
    extra = 0


# User Admin

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display   = ('email', 'google_id', 'total_storage_used', 'track_count', 'created_at')
    list_filter    = ('created_at',)
    search_fields  = ('email', 'google_id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines        = [TrackInline, GenerationRequestInline]

    fieldsets = (
        ('Identity', {
            'fields': ('id', 'google_id', 'email')
        }),
        ('Storage', {
            'fields': ('total_storage_used',),
            'description': 'SRS: 500 MB per-user storage limit'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Tracks')
    def track_count(self, obj):
        return obj.tracks.count()


# GenerationRequest Admin

@admin.register(GenerationRequest)
class GenerationRequestAdmin(admin.ModelAdmin):
    list_display  = ('id', 'owner', 'occasion', 'mood', 'genre',
                     'requested_duration_seconds', 'has_track', 'created_at')
    list_filter   = ('occasion', 'mood', 'genre', 'created_at')
    search_fields = ('owner__email',)
    readonly_fields = ('id', 'created_at')

    fieldsets = (
        ('Ownership', {
            'fields': ('id', 'owner')
        }),
        ('Generation Parameters', {
            'fields': ('occasion', 'mood', 'genre', 'requested_duration_seconds'),
            'description': 'Duration must be 120–360 seconds (SRS FR2.1)'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Track Generated', boolean=True)
    def has_track(self, obj):
        return hasattr(obj, 'track')


# Track Admin

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner', 'status', 'duration_seconds',
                     'audio_url_short', 'sharelink_count', 'created_at')
    list_filter   = ('status', 'created_at')
    search_fields = ('title', 'owner__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines       = [ShareLinkInline]

    fieldsets = (
        ('Identity', {
            'fields': ('id', 'title', 'owner')
        }),
        ('Generation', {
            'fields': ('generation_request', 'status')
        }),
        ('Audio', {
            'fields': ('duration_seconds', 'audio_url'),
            'description': 'Duration must be within ±5s of requested duration (NFR 5.4.1)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Audio URL')
    def audio_url_short(self, obj):
        if obj.audio_url:
            short = obj.audio_url[:40] + '…' if len(obj.audio_url) > 40 else obj.audio_url
            return format_html('<code>{}</code>', short)
        return '—'

    @admin.display(description='Share Links')
    def sharelink_count(self, obj):
        return obj.share_links.count()


# ShareLink Admin

@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display  = ('token_short', 'track', 'is_active', 'is_currently_valid',
                     'expires_at', 'created_at')
    list_filter   = ('is_active', 'created_at')
    search_fields = ('token', 'track__title')
    readonly_fields = ('id', 'token', 'created_at')
    actions       = ['revoke_links']

    fieldsets = (
        ('Identity', {
            'fields': ('id', 'token')
        }),
        ('Access Control', {
            'fields': ('track', 'is_active', 'expires_at'),
            'description': 'Token is cryptographically random and non-guessable (Security Rule)'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Token')
    def token_short(self, obj):
        return format_html('<code>{}</code>', obj.token[:16] + '…')

    @admin.display(description='Currently Valid', boolean=True)
    def is_currently_valid(self, obj):
        return obj.is_valid()

    @admin.action(description='Revoke selected share links')
    def revoke_links(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} share link(s) revoked.")
