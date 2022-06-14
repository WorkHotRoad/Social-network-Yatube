from django.shortcuts import redirect, render, get_object_or_404
from .models import Post, Group, User, Follow

from .forms import PostForm, CommentForm
from django.contrib.auth.decorators import login_required
from .utils import my_pagin


def index(request):
    template = 'posts/index.html'
    page_obj = my_pagin(Post.objects.all(), request)
    context = {
        'page_obj': page_obj
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts_list = group.posts.all()
    count = group.posts.all().count()
    page_obj = my_pagin(posts_list, request)
    context = {
        'page_obj': page_obj,
        'group': group,
        'count': count
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    profile_user = get_object_or_404(User, username=username)
    posts = profile_user.posts.all()
    page_obj = my_pagin(posts, request)
    count = posts.count()
    following = False
    if request.user.is_authenticated and Follow.objects.filter(
        user=request.user,
        author=profile_user
    ).exists():
        following = True
    context = {
        'page_obj': page_obj,
        'author': profile_user,
        'count': count,
        'following': following
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    count = Post.objects.filter(author=post.author).count()
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'count': count,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect(
            'posts:profile',
            username=request.user.username
        )
    context = {
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author == request.user:
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post
        )
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id)
        context = {
            'form': form,
            'post': post,
            'is_edit': True
        }
        return render(request, template, context)
    return redirect(
        'posts:profile',
        username=request.user.username
    )


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = my_pagin(posts, request)
    context = {
        "page_obj": page_obj
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect(
        'posts:profile',
        username=username
    )


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(
        user=request.user,
        author=author
    ).delete()
    return redirect("posts:profile", username=username)
