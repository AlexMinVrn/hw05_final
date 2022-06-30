from django.contrib.auth.decorators import login_required
from .utils import paginate_page
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow


@cache_page(20, key_prefix='index_page')
def index(request):
    """Главная страница"""
    last_posts = Post.objects.select_related('group', 'author')
    page_obj = paginate_page(request, last_posts)
    return render(request, 'posts/index.html', {'page_obj': page_obj})


def group_posts(request, slug):
    """Страница постов выбранной группы"""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('group', 'author').all()
    page_obj = paginate_page(request, posts)
    return render(
        request,
        'posts/group_list.html',
        {'group': group, 'page_obj': page_obj}
    )


def profile(request, username):
    """Страница постов выбранного автора"""
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group', 'author').all()
    page_obj = paginate_page(request, posts)
    following = False
    if request.user.is_authenticated and Follow.objects.filter(
            user=request.user,
            author=author).exists():
        following = True
    context = {
        'page_obj': page_obj,
        'author': author,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница выбранного поста"""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    context = {
        'post': post,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Создание нового поста, после успешного заполнения -
    переход на страницу профиля"""
    form = PostForm(request.POST or None)
    if not request.method == 'POST':
        return render(request, 'posts/create_post.html', {'form': form})
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', request.user.username)


@login_required
def post_edit(request, post_id):
    """Редактирование поста - доступно только автору поста,
    если пользователь - не автор - переход на страницу поста.
    После успешного редактирования - переход на страницу поста"""
    post = get_object_or_404(
        Post, pk=post_id
    )
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.method == "POST":
        if form.is_valid():
            form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    """Создание комментария к посту"""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Страница постов авторов, на которых подписан текущий пользователь."""
    user = get_object_or_404(User, username=request.user)
    posts_list = Post.objects.filter(
        author__following__user=user).select_related('group', 'author')
    page_obj = paginate_page(request, posts_list)
    return render(request, 'posts/follow.html', {'page_obj': page_obj})


@login_required
def profile_follow(request, username):
    """Подписаться на автора"""
    author = get_object_or_404(User, username=username)
    if request.user != author and not Follow.objects.filter(
            user=request.user,
            author=author).exists():
        follower = request.user
        followed = User.objects.get(username=username)
        Follow.objects.create(user=follower, author=followed)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Дизлайк, отписка"""
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(user=request.user, author=author).exists():
        Follow.objects.filter(
            user=request.user,
            author=author).delete()
    return redirect('posts:profile', username=username)
