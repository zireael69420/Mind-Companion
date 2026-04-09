from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Comment


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'mc-input',
            'placeholder': 'your@email.com',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model  = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mc-input',
                'placeholder': 'Choose a username',
                'autocomplete': 'username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'mc-input',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'mc-input',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CommentForm(forms.ModelForm):
    class Meta:
        model  = Comment
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'mc-input mc-textarea',
                'placeholder': 'Share your thoughts about this video…',
                'rows': 3,
                'maxlength': 500,
            }),
        }
        labels = {'body': ''}
