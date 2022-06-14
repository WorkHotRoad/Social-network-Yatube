import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from posts.models import Post, Group
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='auth')
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
        cls.group_test2 = Group.objects.create(
            title='Тестовая группа_2',
            slug='Test_slug_2',
            description='Тестовое описание2_'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестоый пост',
            group=cls.group_test1
        )
        cls.text_for_post = {
            1: "Первый пост",
            2: 'Новый текст'
        }
        cls.not_authorized_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_valid_form(self):
        """создание записи в Б.Д при валидной форме"""
        tasks_count = Post.objects.count()
        form_data = {
            "text": self.text_for_post[1],
            "group": self.group_test2.id,
            "image": self.uploaded  # добавляем картинку
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # проверка перенаправления после создания поста
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': 'auth'})
        )
        # проверка постов по колличеству
        self.assertEqual(Post.objects.count(), tasks_count + 1)
        # Проверка правильности заполнения полей посSта
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': 'auth'})
        )
        # берем последний пост автора
        first_object = response.context['page_obj'][0]
        # проверяем поля
        n = first_object.image
        print(n)
        self.assertEqual(first_object.group, self.group_test2)
        self.assertEqual(first_object.author, self.user)
        self.assertEqual(first_object.text, self.text_for_post[1])
        self.assertTrue(Post.objects.filter(image='posts/small.gif').exists())

    def test_post_edit_form(self):
        """Проверка изменениячя поста при его редактировании"""
        tasks_count = Post.objects.count()
        form_data = {
            "text": self.text_for_post[2],
            "group": self.group_test2.id
        }
        response = self.authorized_client.post(reverse(
            'posts:post_edit',
            args=(self.post.id,)),
            data=form_data
        )
        # проверка перехода на страницу поста после успешного заполнения формы
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        # проверка, что не создалась новая запись
        self.assertEqual(Post.objects.count(), tasks_count)
        # проверка изменения поста
        response = Post.objects.get(id=self.post.id)
        self.assertEqual(response.text, self.text_for_post[2])
        self.assertEqual(response.group, self.group_test2)
        self.assertEqual(response.author, self.user)

    def test_create_comment(self):
        """Тестировение создания комментариев"""
        count_comments = self.post.comments.count()
        form_data = {
            "text": "My_comment"
        }
        client_for_test = [
            self.authorized_client,
            self.not_authorized_client
        ]
        # после успешной отправки комментарий появляется на странице поста
        # проверка авторизированного и не авторизированного пользователя
        for client in client_for_test:
            with self.subTest(client=client):
                client.post(reverse(
                    'posts:add_comment',
                    args=(self.post.id,)),
                    data=form_data,
                    follow=True
                )
                self.assertEqual(
                    self.post.comments.count(), count_comments + 1
                )
        # после успешной комментарий появляется на странице поста.
        self.assertTrue(
            self.post.comments.filter(
                text='My_comment',
                author=self.user,
                post=self.post
            ).exists()
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
