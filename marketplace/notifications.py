import json
from django.utils import timezone

from .models import DismissedNotification, UserNotification


def get_user_notifications(request):
    """Return list of notification dicts for the current user (if authenticated).

    Each dict has: id (str), title, message, url, unread (bool), time (human-friendly).
    """
    if not request.user.is_authenticated:
        return []

    dismissed = list(DismissedNotification.objects.filter(user=request.user).values_list('notification_id', flat=True))
    qs = UserNotification.objects.filter(user=request.user).order_by('-created_at')
    out = []
    for n in qs:
        nid = str(n.id)
        if nid in dismissed:
            continue
        out.append({
            'id': nid,
            'title': n.title,
            'message': n.message,
            'url': n.url or '#',
            'unread': not n.is_read,
            'time': timezone.localtime(n.created_at).strftime('%Y-%m-%d %H:%M'),
        })
    return out


def is_valid_notification_id(notification_id, user=None):
    """Return True if notification_id exists for the given user (or any user if user is None)."""
    if not str(notification_id).isdigit():
        return False
    nid = int(notification_id)
    qs = UserNotification.objects.filter(id=nid)
    if user is not None:
        qs = qs.filter(user=user)
    return qs.exists()
