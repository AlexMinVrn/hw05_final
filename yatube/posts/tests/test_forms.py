import shutil
import tempfile

import mock
from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from ..models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='post_author')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create(self):
        """Валидная форма создает запись в Post."""
        self.image_mock = mock.MagicMock(spec=File)
        self.image_mock.name = 'image_mock'
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.image_mock,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.context.get('post').text, 'Тестовый текст')
        self.assertEqual(response.context.get('post').author, self.user)
        self.assertEqual(response.context.get('post').group, self.group)
        self.assertEqual(Post.objects.count(), 1)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user.username}))
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестовый текст',
        )
        form_data = {
            'text': 'Отредактированный тестовый текст',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.context.get('post').text,
                         'Отредактированный тестовый текст')
        self.assertEqual(response.context.get('post').author, self.user)
        self.assertEqual(response.context.get('post').group, self.group)
        self.assertEqual(Post.objects.count(), 1)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': 1}))
        response = self.client.post(
            reverse('posts:post_edit', kwargs={'post_id': 1}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='post_author')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='NoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_add_comment(self):
        """Валидная форма создает комментарий."""
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': 1}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.get().text, 'Тестовый комментарий')
        self.assertEqual(Comment.objects.get().author, self.user)
        self.assertEqual(Comment.objects.get().post, self.post)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': 1}))

    def test_add_comment_unauthorized_user(self):
        """При попытке создать комментарий неавторизованным пользователем
        комментарий не создается, пользователь перенаправляется на страницу
        авторизации"""
        form_data = {
            'text': 'Тестовый комментарий',
        }
        comment_url = reverse('posts:add_comment', kwargs={'post_id': 1})
        response = self.client.post(comment_url,
                                    data=form_data,
                                    follow=True
                                    )
        login_url = reverse('users:login')
        self.assertEqual(Comment.objects.count(), 0)
        self.assertRedirects(response, f'{login_url}?next={comment_url}')
