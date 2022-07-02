import shutil
import tempfile

import mock
from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

from ..forms import PostForm
from ..models import Group, Post, Comment, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTest(TestCase):
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
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()
        self.image_mock = mock.MagicMock(spec=File)
        self.image_mock.name = 'image_mock'
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестовый пост',
            image=self.image_mock
        )
        self.comment = Comment.objects.create(
            text='Тестовый комментарий',
            author=self.user,
            post=self.post
        )

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = (
            (reverse('posts:index'), 'posts/index.html'),
            (reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ), 'posts/group_list.html'),
            (reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ), 'posts/profile.html'),
            (reverse(
                'posts:post_detail', kwargs={'post_id': 1}
            ), 'posts/post_detail.html'),
            (reverse(
                'posts:post_edit', kwargs={'post_id': 1}
            ), 'posts/create_post.html'),
            (reverse('posts:post_create'), 'posts/create_post.html'),
            (reverse('posts:follow_index'), 'posts/follow.html'),
        )
        for reverse_name, template in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_create_post_edit_page_show_correct_context(self):
        """Шаблон post_create и post_edit
        сформированы с правильным контекстом."""
        views_names = (
            reverse('posts:post_create'),
            reverse(
                'posts:post_edit', kwargs={'post_id': 1}
            )
        )
        for reverse_name in views_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                form_fields = (
                    ('text', forms.fields.CharField),
                    ('group', forms.fields.ChoiceField),
                    ('image', forms.fields.ImageField),
                )
            for value, expected in form_fields:
                with self.subTest(value=value):
                    form_field = response.context['form'].fields[value]
                    self.assertIsInstance(form_field, expected)
                    self.assertIsInstance(response.context['form'], PostForm)

    def test_post_edit_is_edit_bool(self):
        """В шаблоне post_edit тип переменной is_edit Boolean"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': 1}))
        self.assertIsInstance(response.context['is_edit'], bool)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': 1}))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)
        self.assertEqual(response.context.get('post').comments.all()[0].text,
                         self.comment.text)

    def test_pages_show_correct_context(self):
        """Шаблон index, group_list, profile, post_detail сформированы
        с правильным контекстом."""
        pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
            reverse('posts:post_detail', kwargs={'post_id': 1})
        )
        for reverse_name in pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(response.context.get('post').text,
                                 self.post.text)
                self.assertEqual(response.context.get('post').author,
                                 self.post.author)
                self.assertEqual(response.context.get('post').group,
                                 self.post.group)
                self.assertEqual(response.context.get('post').image,
                                 self.post.image)

    def test_index_cache(self):
        """Проверяем работу Кэша в post_index"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context.get('page_obj')), 1)
        Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестовый пост 2',
        )
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_2.content)

        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, response_3.content)
        self.assertEqual(len(response_3.context.get('page_obj')), 2)

        Post.objects.first().delete()
        response_4 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_3.content, response_4.content)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()
        post = [Post(
            text=f'Тестовый пост{i}',
            author=self.user,
            group=self.group,
        ) for i in range(13)]
        self.post = Post.objects.bulk_create(post)

    def test_paginate_page_contains_correct_number_of_posts(self):
        pages_names = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        )
        for reverse_name in pages_names:
            first_object = self.authorized_client.get(
                reverse_name).context.get('page_obj')[0]
            cache.clear()
            self.assertIsInstance(first_object, Post)
            response_first_page = self.authorized_client.get(reverse_name)
            response_second_page = self.authorized_client.get(
                reverse_name + '?page=2')
            self.assertEqual(len(
                response_first_page.context.get('page_obj')), 10)
            self.assertEqual(len(
                response_second_page.context.get('page_obj')), 3)


class GroupViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group_1 = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group_1,
            text='Тестовый пост',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug 2',
            description='Тестовое описание 2',
        )
        cls.post_2 = Post.objects.create(
            author=cls.user,
            group=cls.group_2,
            text='Тестовый пост 2',
        )

    def test_group_list_pages_show_correct_context(self):
        """В шаблон group_list переданы посты нужной группы."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group_1.slug}
                    )
        )
        self.assertEqual(len(
            response.context.get('page_obj')), 1)
        self.assertNotEqual(
            response.context.get('post'), self.post_2)


class FollowViewsTest(TestCase):
    def setUp(self):
        self.user_1 = User.objects.create_user(username='author_1')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_1)
        self.post_1 = Post.objects.create(
            author=self.user_1,
            text='Тестовый пост 1',
        )
        self.user_2 = User.objects.create_user(username='author_2')
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user_2)
        self.post_2 = Post.objects.create(
            author=self.user_2,
            text='Тестовый пост 2',
        )
        self.follow = Follow.objects.create(
            user=self.user_1,
            author=self.user_2
        )

    def test_follow_pages_show_correct_context(self):
        """В шаблон follow переданы посты автора на которого подписан
        пользователь и не передаются посты если нет подписки."""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context.get('page_obj')), 1)
        self.assertEqual(response.context.get('page_obj')[0], self.post_2)
        self.assertNotEqual(response.context.get('post'), self.post_1)
        response_2 = self.authorized_client_2.get(
            reverse('posts:follow_index'))
        self.assertEqual(len(response_2.context.get('page_obj')), 0)

    def test_profile_follow_unfollow_pages_show_correct_context(self):
        """Авторизованный пользователь может подписываться на других
        пользователей и удалять их из подписок."""
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_2.username})
        )
        self.assertFalse(Follow.objects.filter().exists())
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username})
        )
        self.assertEqual(Follow.objects.count(), 1)
