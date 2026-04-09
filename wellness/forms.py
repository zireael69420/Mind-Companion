# wellness/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-rose-300 bg-white/70',
            'placeholder': 'you@example.com',
        }),
        help_text='We keep your email private.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-rose-300 bg-white/70',
                'placeholder': 'Choose a username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply consistent styling to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-rose-300 bg-white/70',
            'placeholder': 'Create a strong password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-rose-300 bg-white/70',
            'placeholder': 'Confirm your password',
        })
        # Clear Django's default verbose help text — template shows custom tips
        self.fields['username'].help_text = 'Letters, digits, and @/./+/-/_ only.'
        self.fields['password1'].help_text = (
            'Must be at least 8 characters, not too common, and not entirely numeric.'
        )
        self.fields['password2'].help_text = 'Enter the same password again to confirm.'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
