from .notifications import get_user_notifications


def notifications(request):
    if not request.user.is_authenticated:
        return {'notifications': [], 'notifications_count': 0}
    notifications = get_user_notifications(request)
    return {
        'notifications': notifications,
        'notifications_count': len(notifications),
    }
