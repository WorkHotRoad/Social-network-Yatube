import shutil
import tempfile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from posts.models import Post, Group, Follow
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
import time
from django.core.cache import cache

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='auth')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group
        )
        cls.form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

    def test_all_page_uses_correct_template(self):
        templates_pages_names1 = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:group_list', kwargs={'slug': 'Test_slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'auth'}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names1.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_create_post_show_correct_context(self):
        '''Проверка context формы создания поста'''
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_edit_post_show_correct_context(self):
        '''Проверка context формы редактирование поста'''
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.pk}
            )
        )
        for value, expected in self.form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context['is_edit'], True)
        self.assertEqual(response.context['post'], self.post)

    def test_post_detail_show_correct_context(self):
        """Проверка context в шаблоне - post_detail"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            )
        )
        count_post = Post.objects.filter(author=self.post.author).count()
        self.assertEqual(
            response.context['post'].text, 'Тестовая пост'
        )
        self.assertEqual(
            response.context['post'].author, self.user
        )
        self.assertEqual(
            response.context['post'].group, self.group
        )
        self.assertEqual(
            response.context['count'], count_post
        )


class ContextPaginatorPages(TestCase):
    """тестируем context страниц с пагинатором"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='pinki')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_slug',
            description='Тестовое описание'
        )
        cls.num_of_post = 3
        for new_post in range(1, cls.num_of_post + 1):
            time.sleep(0.1)
            cls.post = Post.objects.create(
                author=cls.user,
                text='Тестовый пост ' + str(new_post),
                group=cls.group
            )

    def context_test_page_obj(self, response):
        """функция проверки context 1го объекта страницы"""
        object = response.context['page_obj'][0]
        fieldd = {
            object.author: self.user,
            object.text: 'Тестовый пост 3',
            object.group: self.group
        }
        for value, expected in fieldd.items():
            with self.subTest(expected=expected):
                self.assertEqual(value, expected)

    def test_index_show_correct_context_first_post(self):
        """Проверка контекста шаблона 'posts:index' """
        response = self.authorized_client.get(reverse('posts:index'))
        self.context_test_page_obj(response)

    def test_group_list_show_correct_context(self):
        """Проверка контекста шаблона 'posts:group_list' """
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': 'Test_slug'}
            )
        )
        self.context_test_page_obj(response)
        self.assertEqual(response.context['count'], self.num_of_post)
        self.assertEqual(response.context['group'], self.group)

    def test_profile_show_correct_context(self):
        """Проверка context в шаблона: 'posts:profile' """
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'pinki'})
        )
        self.context_test_page_obj(response)
        self.assertEqual(response.context['count'], self.num_of_post)
        self.assertEqual(response.context['author'], self.user)


class PaginatorViewsTest(TestCase):
    """Тестируем пагинатор"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='pinki')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_slug',
            description='Тестовое описание'
        )
        cls.num_of_post = 13
        objs = [
            Post(
                author=cls.user,
                text='Тестовая пост ' + str(new_post),
                group=cls.group
            )
            for new_post in range(cls.num_of_post)
        ]
        cls.post = Post.objects.bulk_create(objs)

    def test_first_page_contains_ten_records(self):
        """Тестируем пагинатор первой страницы"""
        reverse_dict_for_paginator_test = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={
                    'slug': self.group.slug}),
            reverse('posts:profile', kwargs={
                    'username': self.user.username})
        ]
        for reverse_name in reverse_dict_for_paginator_test:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_ten_records(self):
        """Тестируем пагинатор второй страницы"""
        reverse_dict_for_paginator_test = [
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list', kwargs={
                    'slug': self.group.slug}) + '?page=2',
            reverse('posts:profile', kwargs={
                    'username': self.user.username}) + '?page=2'
        ]
        for reverse_name in reverse_dict_for_paginator_test:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 3)


class CreatePostTest(TestCase):
    """Тестируем создание поста"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем клиент
        cls.guest_client = Client()
        # Создаем юзера
        cls.user = User.objects.create_user(username='Alloha')
        # Авторизуем юзера
        cls.guest_client.force_login(cls.user)
        # Создаем группу
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Test_slug',
            description='Тестовое описание'
        )
        # Создаем 2 группу
        cls.grop2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='Test_slug2',
            description='Тестовое описание'
        )
        # Создаем пост
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            group=cls.group
        )

    def test_create_post_on_main_page(self):
        """Проверяем отображение созданного поста на главной странице"""
        response = self.guest_client.get(reverse('posts:index'))
        context_object = response.context['page_obj']
        self.assertIn(self.post, context_object)

    def test_create_post_in_group(self):
        """Проверяем отображение созданного поста в группе"""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'Test_slug'})
        )
        context_object = response.context['page_obj']
        self.assertIn(self.post, context_object)

    def test_create_post_in_profile_user(self):
        """Проверяем отображение созданного поста в профиле автора"""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': 'Alloha'})
        )
        context_object = response.context['page_obj']
        self.assertIn(self.post, context_object)

    def test_create_post_in_wrong_group(self):
        """Проверяем отображение созданного поста в другой группе"""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'Test_slug2'})
        )
        context_object = response.context['page_obj']
        self.assertNotIn(self.post, context_object)


class CacheTest(TestCase):
    """тестируем работу кэша"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='pinki')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def response(self):
        return self.authorized_client.get(reverse('posts:index'))

    def test_cache(self):
        # создаем пост
        post = Post.objects.create(
            author=self.user,
            text='Тестоый пост1'
        )
        cache.clear()
        # Проверяем , что пост в кэше
        self.assertIn(post.text, self.response().content.decode())
        # Удаляем пост
        Post.objects.filter(author=self.user).delete()
        # Проверяем что пост еще находится в кэше
        self.assertIn(post.text, self.response().content.decode())
        # чистим кэш
        cache.clear()
        # Проверяем что поста нет в кэше
        self.assertNotIn(post.text.encode(), self.response().content)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='first')
        cls.user2 = User.objects.create_user(username='second')
        cls.user3 = User.objects.create_user(username='third')

        cls.authorized_client = Client()
        cls.authorized_client2 = Client()
        cls.authorized_client3 = Client()

        cls.authorized_client.force_login(cls.user1)
        cls.authorized_client2.force_login(cls.user2)
        cls.authorized_client3.force_login(cls.user3)

        cls.post1 = Post.objects.create(
            author=cls.user1,
            text='Тестовая пост0',
        )
        # создаем запись в моделе
        Follow.objects.create(
            user=cls.user2,
            author=cls.user1
        )

    def test_profile_follow(self):
        """авторизованного пользователь может подписаться на автора"""
        self.authorized_client2.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user3.username})
        )
        count_follow = Follow.objects.filter(user=self.user2).count()
        self.assertEqual(count_follow, 2, "Пользоватьель не смог подписаться")

    def test_profile_unfollow(self):
        """авторизованного пользователь может отписаться от автора"""
        self.authorized_client2.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user1.username})
        )
        count_follow = Follow.objects.filter(user=self.user2).count()
        self.assertEqual(count_follow, 0, "Пользоватьель не смог отписаться")

    def test_follow_new_post(self):
        """новая запись пользователя появиться у тех кто на него подписан"""
        response = self.authorized_client2.get(
            reverse('posts:follow_index')
        )
        post_follow = response.context.get('page_obj')[0]
        self.assertEqual(
            post_follow, self.post1,
            'Не найден новый пост в ленте подписчика'
        )
        response = self.authorized_client3.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(
            len(response.context['page_obj']), 0,
            'найден лишний пост в ленте подписчика'
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CreatePostImageTest(TestCase):
    """Проверка передачи картинки в словаре"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='Brain')
        cls.authorized_client.force_login(cls.user)
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group_test1 = Group.objects.create(
            title='Тестовая группа_1',
            slug='Test_slug_1',
            description='Тестовое описание_1'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестоый пост',
            group=cls.group_test1,
            image=cls.uploaded
        )

    def test_image_idex_page(self):
        """Проверяем image на страницах:
        index,
        profile,
        group_list,
        """
        pages = [
            self.authorized_client.get(
                reverse('posts:index')
            ),
            self.authorized_client.get(
                reverse(
                    'posts:profile', kwargs={'username': 'Brain'}
                )
            ),
            self.authorized_client.get(
                reverse(
                    'posts:group_list', kwargs={'slug': 'Test_slug_1'}
                )
            )
        ]
        for response in pages:
            with self.subTest(response=response):
                object = response.context['page_obj'][0]
                self.assertEqual(object.image, 'posts/small.gif')

    def test_image_in_post_detail(self):
        """Проверка отображение image в post_detail"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            )
        )
        self.assertEqual(response.context['post'].image, 'posts/small.gif')

    @classmethod
    def tearDownClass(cls):
        """удаляем временное хранилище для image"""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
