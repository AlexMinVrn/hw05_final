from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Group, Post, Comment

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для проверки',
        )
        cls.comment = Comment.objects.create(
            text='Тестовый коммент для проверки',
            author=cls.user,
            post=cls.post,
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        group = PostModelTest.group
        comment = PostModelTest.comment
        fields = (
            (post, post.text[:15]),
            (group, group.title),
            (comment, comment.text[:15])
        )
        for field, expected_field in fields:
            with self.subTest(field=field):
                self.assertEqual(
                    expected_field,
                    str(field))

    def test_text_label(self):
        """verbose_name поля совпадает с ожидаемым."""
        post = PostModelTest.post
        field_verboses = (
            ('text', 'Текст поста'),
            ('pub_date', 'Дата публикации'),
            ('author', 'Автор'),
            ('group', 'Группа'),
            ('image', 'Картинка'),
        )
        for field, expected_value in field_verboses:
            self.assertEqual(
                post._meta.get_field(field).verbose_name, expected_value)

    def test_text_help_text(self):
        """help_text поля text совпадает с ожидаемым."""
        post = PostModelTest.post
        field_help_texts = (
            ('text', 'Введите текст поста'),
            ('group', 'Группа, к которой будет относиться пост'),
            ('image', 'Загрузите картинку'),
        )
        for field, expected_value in field_help_texts:
            self.assertEqual(
                post._meta.get_field(field).help_text, expected_value)
