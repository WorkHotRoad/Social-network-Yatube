from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': 'Текст поста',
            'group': 'Выбор группы',
            'image': 'Картинка'
        }
        help_texts = {
            'text': ('Введите текст поста'),
            'group': ('Группа, к которой будет относиться пост')
        }
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'placeholder': 'Введите текст сюда',
                    'class': "form-control"
                }
            ),
            'group': forms.Select(attrs={'class': "form-control"}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'placeholder': 'Есть что сказать?',
                    'class': "form-control"
                }
            )
        }
