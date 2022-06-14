from django.core.paginator import Paginator
from yatube.settings import COUNT_OF_POSTS_FOR_PAGINATOR as NUM


def my_pagin(posts, request):
    paginator = Paginator(posts, NUM)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
