from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


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


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class':        'mc-input code-input',
            'placeholder':  '000000',
            'autocomplete': 'one-time-code',
            'inputmode':    'numeric',
            'pattern':      '[0-9]{6}',
            'maxlength':    '6',
        }),
        label='Verification code',
        error_messages={
            'required':   'Please enter the 6-digit code.',
            'min_length': 'The code must be exactly 6 digits.',
            'max_length': 'The code must be exactly 6 digits.',
        },
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        if not code.isdigit():
            raise forms.ValidationError('The code must contain digits only.')
        return code
