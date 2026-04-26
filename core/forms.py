from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, BloodRequest, Inventory, Donation, Hospital

BLOOD_CHOICES = [
    ('', '-- Select Blood Type --'),
    ('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
    ('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-'),
]


class RegisterForm(UserCreationForm):
    """Public registration — donors and patients ONLY. Staff created by admin."""
    ROLE_CHOICES = [
        ('donor',   'Donor'),
        ('patient', 'Patient / Receiver'),
    ]
    first_name = forms.CharField(max_length=50, required=True)
    last_name  = forms.CharField(max_length=50, required=True)
    email      = forms.EmailField(required=True)
    role       = forms.ChoiceField(choices=ROLE_CHOICES)
    blood_type = forms.ChoiceField(choices=BLOOD_CHOICES, required=False)
    phone      = forms.CharField(max_length=20, required=False)
    city       = forms.CharField(max_length=80, required=False)

    class Meta:
        model  = User
        fields = ['username','first_name','last_name','email','role',
                  'blood_type','phone','city','password1','password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['role'].widget.attrs['class'] = 'form-select'
        self.fields['blood_type'].widget.attrs['class'] = 'form-select'


class StaffCreationForm(forms.ModelForm):
    """Admin-only: create a hospital staff account. Password auto-generated and emailed."""
    first_name = forms.CharField(max_length=50, required=True)
    last_name  = forms.CharField(max_length=50, required=True)
    email      = forms.EmailField(required=True, help_text='Login credentials will be sent to this address.')
    phone      = forms.CharField(max_length=20, required=False)
    city       = forms.CharField(max_length=80, required=False)
    hospital   = forms.ModelChoiceField(
        queryset=Hospital.objects.filter(is_active=True),
        required=True,
        empty_label='-- Select Hospital --',
        help_text='The hospital this staff member will manage.'
    )

    class Meta:
        model  = User
        fields = ['username','first_name','last_name','email','phone','city','hospital']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['hospital'].widget.attrs['class'] = 'form-select'


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name','last_name','email','blood_type','phone','city','is_available']
        widgets = {
            'blood_type':   forms.Select(attrs={'class':'form-select'}),
            'is_available': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('blood_type', 'is_available'):
                field.widget.attrs['class'] = 'form-control'


class BloodRequestForm(forms.ModelForm):
    class Meta:
        model  = BloodRequest
        fields = ['blood_type','qty_units','urgency','hospital','notes']
        widgets = {
            'blood_type': forms.Select(attrs={'class':'form-select'}),
            'qty_units':  forms.NumberInput(attrs={'class':'form-control','min':1,'max':20}),
            'urgency':    forms.Select(attrs={'class':'form-select'}),
            'hospital':   forms.Select(attrs={'class':'form-select'}),
            'notes':      forms.Textarea(attrs={'class':'form-control','rows':3,
                            'placeholder':'Any additional medical information…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hospital'].queryset      = Hospital.objects.filter(is_active=True)
        self.fields['hospital'].empty_label   = '-- Select Nearest Hospital --'
        self.fields['hospital'].required      = False


class InventoryUpdateForm(forms.ModelForm):
    class Meta:
        model  = Inventory
        fields = ['blood_type','qty_available']
        widgets = {
            'blood_type':    forms.Select(attrs={'class':'form-select'}),
            'qty_available': forms.NumberInput(attrs={'class':'form-control','min':0}),
        }


class DonationRecordForm(forms.ModelForm):
    class Meta:
        model  = Donation
        fields = ['blood_type','qty_ml','donated_at','hospital','notes']
        widgets = {
            'blood_type':  forms.Select(attrs={'class':'form-select'}),
            'qty_ml':      forms.NumberInput(attrs={'class':'form-control','min':100}),
            'donated_at':  forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'hospital':    forms.Select(attrs={'class':'form-select'}),
            'notes':       forms.Textarea(attrs={'class':'form-control','rows':2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hospital'].queryset    = Hospital.objects.filter(is_active=True)
        self.fields['hospital'].empty_label = '-- Select Hospital (optional) --'
        self.fields['hospital'].required    = False


class HospitalForm(forms.ModelForm):
    class Meta:
        model  = Hospital
        fields = ['name','city','address','contact_email','phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class TrackRequestForm(forms.Form):
    reference_no = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter reference number e.g. LS-A1B2C3D4',
        })
    )
