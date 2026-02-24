from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    CustomUser, StudentProfile, TeacherProfile,
    Course, CourseMaterial, Deadline, Submission
)

# Registration form for new users
# This extends Django's built-in UserCreationForm
# I watched a tutorial that explained this is the standard way to do custom registration
class UserRegistrationForm(UserCreationForm):
    # added email field because the default form doesn't include it
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    # user needs to select if they're a student or teacher
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPES, required=True)
    
    # optional fields
    bio = forms.CharField(widget=forms.Textarea, required=False)
    profile_pic = forms.ImageField(required=False)
    
    class Meta:
        model = CustomUser
        # these are the fields that will show on the form
        fields = ['username', 'first_name', 'last_name', 'email', 'user_type', 'bio', 'profile_pic']
    
    # Requirement R2: add custom validation logic
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email
    
    # creating student or teacher profile 
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.user_type = self.cleaned_data['user_type']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.bio = self.cleaned_data.get('bio', '')
        
        if commit:
            user.save()
            # auto create profile
            if user.user_type == 'student':
                StudentProfile.objects.create(user=user)
            elif user.user_type == 'teacher':
                TeacherProfile.objects.create(user=user)
        
        return user


# Login form - just using Django's default for now
# might customize this later if needed
# This is the form I use every day to log in and check my courses!
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


# Form for editing user profile
class UserProfileEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['email', 'bio', 'profile_pic']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


# Form for student-specific profile info
class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['student_id']
        # student_id is optional so students can add it later


# Form for teacher-specific profile info
class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ['teacher_id', 'department', 'years_experience']


# Course creation form for teachers
# I'm including most of the important fields from the Course model
class CourseCreateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'max_students']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter course description...',
                'class': 'w-full bg-edustream-navy border border-edustream-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-edustream-emerald transition placeholder:text-text-muted resize-none'
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g., Introduction to Python',
                'class': 'w-full bg-edustream-navy border border-edustream-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-edustream-emerald transition placeholder:text-text-muted'
            }),
            'max_students': forms.NumberInput(attrs={
                'class': 'w-full bg-edustream-navy border border-edustream-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-edustream-emerald transition'
            }),
        }
        # I added help text to make it clearer for teachers
        help_texts = {
            'max_students': 'Maximum number of students allowed in this course',
        }
    


# Material upload form
# keeping it simple - just title, description, and file
class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = ['title', 'description', 'file']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional description of this material...'
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g., Week 1 Lecture Notes'
            }),
        }
    
    # check file size - 10MB max
    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            # check bytes
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File too big (max 10MB)')
        return f


# Form for creating deadlines
class DeadlineForm(forms.ModelForm):
    class Meta:
        model = Deadline
        fields = ['course', 'title', 'description', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    # check if date is in the future
    def clean_due_date(self):
        date = self.cleaned_data.get('due_date')
        from django.utils import timezone
        if date and date < timezone.now():
            raise forms.ValidationError('Must be in the future.')
        return date


# Form for students to submit assignments
class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add a comment (optional)...'}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # 10 MB limit
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB')
        return file
