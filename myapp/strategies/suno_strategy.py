import time
import threading
import requests
from django.conf import settings

from .base import TrackGeneratorStrategy
from .exceptions import SunoOfflineError, SunoInsufficientCreditsError
from myapp.models.track import Track
from myapp.models.enums import TrackStatus


class SunoTrackGeneratorStrategy(TrackGeneratorStrategy):
    """
    Live strategy that integrates with SunoApi.org to generate music.

    Flow:
    1. POST /generate  → receive taskId
    2. Create a Track in PENDING status with the taskId
    3. Poll GET /generate/record-info in a background thread
    4. Update the Track when generation reaches SUCCESS or FAILED
    """

    BASE_URL = "https://api.sunoapi.org/api/v1"
    POLL_INTERVAL_SECONDS = 5
    MAX_POLLS = 60  # 5 minutes maximum before marking FAILED

    # -----------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------

    def generate(self, generation_request) -> Track:
        """
        Start generation via Suno API and return a PENDING Track immediately.
        Background polling updates the Track status asynchronously.
        """
        # Idempotent: return existing track if already generated
        if hasattr(generation_request, "track"):
            return generation_request.track

        task_id = self._create_task(generation_request)

        title = (
            f"{generation_request.occasion.capitalize()} "
            f"{generation_request.mood.capitalize()} "
            f"{generation_request.genre.upper()}"
        )

        track = Track.objects.create(
            owner=generation_request.owner,
            generation_request=generation_request,
            title=title,
            duration_seconds=generation_request.requested_duration_seconds,
            audio_url="",           # filled in when Suno finishes
            status=TrackStatus.PENDING,
            task_id=task_id,
        )

        print(
            f"[SunoStrategy] Task {task_id} started – "
            f"Track {track.id} is PENDING."
        )

        # Poll in background so the HTTP request returns immediately
        thread = threading.Thread(
            target=self._poll_until_done,
            args=(track,),
            daemon=True,
        )
        thread.start()

        return track

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    def _headers(self):
        return {
            "Authorization": f"Bearer {settings.SUNO_API_KEY}",
            "Content-Type": "application/json",
        }

    def _create_task(self, generation_request) -> str:
        """
        Call POST /generate and return the taskId.
        Raises SunoOfflineError or SunoInsufficientCreditsError on known failures.
        """
        # Build a descriptive prompt from the domain fields
        prompt = (
            f"A {generation_request.mood} {generation_request.genre} song "
            f"for a {generation_request.occasion} event, "
            f"approximately {generation_request.requested_duration_seconds} seconds long."
        )

        # Suno requires a callBackUrl even if we use polling for status (we do).
        # Fall back to a no-op public URL if the setting is missing or still the
        # placeholder "your-ngrok-url" — Suno will try to POST to it, get 404,
        # and we'll keep polling /generate/record-info regardless.
        callback_url = getattr(settings, "SUNO_CALLBACK_URL", "") or ""
        if not callback_url or "your-ngrok-url" in callback_url:
            callback_url = "https://example.com/suno/callback"

        payload = {
            "prompt": prompt,
            "style": f"{generation_request.genre} {generation_request.mood}",
            "title": f"{generation_request.occasion} {generation_request.genre}",
            "model": "V4_5ALL",
            "customMode": True,
            "instrumental": True,
            "callBackUrl": callback_url,
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/generate",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise SunoOfflineError(
                "Cannot reach Suno API — check your internet connection."
            )
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Suno API request failed: {e}")

        if response.status_code == 402:
            raise SunoInsufficientCreditsError("Suno API credits are exhausted.")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"Suno API error: {e}. Status: {response.status_code}"
            )

        data = response.json()

        # Detect credit-exhaustion messages embedded in the response body
        credit_keywords = ("credit", "insufficient", "balance", "quota")
        combined_msg = " ".join(
            str(data.get(k) or "") for k in ("msg", "message", "error")
        ).lower()
        if data.get("code") == 429 or any(k in combined_msg for k in credit_keywords):
            raise SunoInsufficientCreditsError("Suno API credits are exhausted.")

        task_id = (data.get("data") or {}).get("taskId") or data.get("taskId")
        if not task_id:
            raise ValueError(f"No taskId in Suno response: {data}")

        print(f"[SunoStrategy] Generation task created: taskId={task_id}")
        return task_id

    def _poll_until_done(self, track: Track):
        """
        Background polling loop.  Calls GET /generate/record-info every
        POLL_INTERVAL_SECONDS until the task reaches SUCCESS or FAILED,
        or MAX_POLLS is exhausted.
        """
        for attempt in range(self.MAX_POLLS):
            time.sleep(self.POLL_INTERVAL_SECONDS)
            try:
                status, audio_url, duration = self._fetch_status(track.task_id)

                track.status = (
                    TrackStatus.COMPLETED if status == "SUCCESS"
                    else TrackStatus.FAILED if status == "FAILED"
                    else TrackStatus.PENDING
                )

                if audio_url:
                    track.audio_url = audio_url
                if duration:
                    track.duration_seconds = int(float(duration))

                track.save()

                print(
                    f"[SunoStrategy] Poll {attempt + 1}: "
                    f"task={track.task_id} status={status}"
                )

                if track.status in (TrackStatus.COMPLETED, TrackStatus.FAILED):
                    return

            except Exception as exc:
                # Log but keep polling — transient errors should not abort
                print(
                    f"[SunoStrategy] Warning: poll error for "
                    f"task {track.task_id}: {exc}"
                )

        # Exceeded MAX_POLLS without a terminal status
        track.status = TrackStatus.FAILED
        track.save()
        print(
            f"[SunoStrategy] Max polls reached for task "
            f"{track.task_id}. Marked FAILED."
        )

    def _fetch_status(self, task_id: str):
        """
        Call GET /generate/record-info and return (status, audio_url, duration).
        """
        response = requests.get(
            f"{self.BASE_URL}/generate/record-info",
            params={"taskId": task_id},
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        records = data.get("data") or {}
        record = (
            records[0]
            if isinstance(records, list) and records
            else records
        )

        status = (
            record.get("status", "PENDING")
            if isinstance(record, dict)
            else "PENDING"
        )

        audio_url = None
        duration = None

        if isinstance(record, dict):
            # Modern sunoData format
            resp_obj = record.get("response")
            if isinstance(resp_obj, dict):
                suno_data = resp_obj.get("sunoData") or []
                if isinstance(suno_data, list) and suno_data:
                    audio_url = (
                        suno_data[0].get("audioUrl")
                        or suno_data[0].get("audio_url")
                    )
                    duration = (
                        suno_data[0].get("duration")
                        or suno_data[0].get("audio_duration")
                    )

            # Fallback: legacy clips/songs format
            if not audio_url:
                clips = record.get("clips") or record.get("songs") or []
                if isinstance(clips, list) and clips:
                    audio_url = (
                        clips[0].get("audioUrl") or clips[0].get("audio_url")
                    )
                    duration = duration or (
                        clips[0].get("duration")
                        or clips[0].get("audio_duration")
                    )

        return status, audio_url, duration
