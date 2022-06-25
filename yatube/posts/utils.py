from django.core.paginator import Paginator
from django.conf import settings


def paginate_page(request, posts):
    """Функция для разбивки постов на страницы."""
    paginator = Paginator(posts, settings.LIMIT)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
