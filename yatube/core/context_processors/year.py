from django.utils import timezone


def year(request):
    now = timezone.now().strftime("%Y")
    return {
        'year': now
    }
