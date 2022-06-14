from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from posts.models import Post, Group
from posts.tests.utils import get_sort_302_feeld
from http import HTTPStatus
from django.core.cache import cache

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем неавторизованный клиент
        cls.guest_client = Client()
        # Создаем пользователя
        cls.user = User.objects.create_user(username='auth')
        # Создаем второй клиент
        cls.authorized_client = Client()
        # Авторизуем пользователя
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_slag',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group
        )
        cls.field_verboses = {
            "/": HTTPStatus.OK,
            "/group/Test_slag/": HTTPStatus.OK,
            "/profile/auth/": HTTPStatus.OK,
            "/posts/" + str(cls.post.pk) + "/": HTTPStatus.OK,
            "/posts/" + str(cls.post.pk) + "/edit/": HTTPStatus.FOUND,
            "/create/": HTTPStatus.FOUND,
            "not_exist_page": HTTPStatus.NOT_FOUND
        }

    def test_all_pages_for_guest_client(self):
        ''' проверяем доступность всех страниц
        для не авторизованных пользователей'''
        for key, value in self.field_verboses.items():
            if value == HTTPStatus.FOUND:
                response = self.guest_client.get(key, follow=True)
                with self.subTest(key=key):
                    self.assertRedirects(
                        response, '/auth/login/?next=' + str(key)
                    )
            else:
                response = self.guest_client.get(key)
                with self.subTest(key=key):
                    self.assertEqual(
                        response.status_code, value, "ошибка в " + str(key)
                    )

    def test_pages_for_author_post_log_in(self):
        '''проверяем доступность страниц edit и create
        для автора поста (авторизованного)'''
        field_verboses = get_sort_302_feeld(self.field_verboses)
        for key in field_verboses:
            response = self.authorized_client.get(key)
            with self.subTest(key=key):
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_for_author_log_in(self):
        '''проверяем доступность edit и create
        для авторизованного(не автора)'''
        # создаем еще одного пользователя
        self.user2 = User.objects.create_user(username='NON')
        # создаем клиент
        self.authorized_client2 = Client()
        # авторизуемся
        self.authorized_client2.force_login(self.user2)
        field_verboses = get_sort_302_feeld(self.field_verboses)
        for key in field_verboses:
            if key == "/create/":
                response = self.authorized_client2.get(key)
                self.assertEqual(response.status_code, HTTPStatus.OK)
            else:
                response = self.authorized_client2.get(key, follow=True)
                self.assertRedirects(
                    response, "/profile/" + self.user2.username + "/"
                )

    def test_urls_posts_correct_template(self):
        cache.clear()
        ''' проверка соответствия URL-адресов и шаблонов. '''
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/Test_slag/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/create/': 'posts/create_post.html',
            '/posts/' + str(self.post.pk) + '/': 'posts/post_detail.html',
            '/posts/' + str(self.post.pk) + '/edit/': 'posts/create_post.html'
        }
        for template, address in templates_url_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, address)
