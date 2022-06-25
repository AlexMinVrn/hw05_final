from django.test import TestCase, Client

from django.contrib.auth import get_user_model
from http import HTTPStatus

from ..models import Group, Post

User = get_user_model()


class PostURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Тестовый пост',
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_guest_url_code_200(self):
        """Страницы доступны любому пользователю."""
        guest_url = (
            '/',
            '/group/test-slug/',
            '/profile/auth/',
            '/posts/1/'
        )
        for address in guest_url:
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK,
                                 f'статус код страницы {address} не 200')

    def test_unexisting_page_url_code_404(self):
        """Страница /unexisting_page/ не доступна."""
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND,
                         'статус код страницы /unexisting_page/ не 404')
        self.assertTemplateUsed(response, 'core/404.html')

    def test_authorized_url_code_200(self):
        """Страницы доступны авторизованному пользователю."""
        authorized_url = (
            '/create/',
            '/posts/1/edit/',
            '/follow/'
        )
        for address in authorized_url:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK,
                                 f'статус код страницы {address} не 200')

    def test_authorized_url_redirect_anonymous_on_admin_login(self):
        """Страницы перенаправит анонимного
        пользователя на страницу логина.
        """
        authorized_url = (
            '/create/',
            '/follow/'
        )
        for address in authorized_url:
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertRedirects(response, f'/auth/login/?next={address}')

    def test_edit_url_redirect_not_author_on_post_detail(self):
        """Страница по адресу /posts/1/edit/ перенаправит не автора
        на страницу просмотра поста.
        """
        self.user_2 = User.objects.create_user(username='Вася')
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user_2)
        response = self.authorized_client_2.get('/posts/1/edit/', follow=True)
        self.assertRedirects(response, '/posts/1/')
