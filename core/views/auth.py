# authentication related views - register, login, logout, home redirect
# kept these together since they all deal with user auth flow

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..forms import UserRegistrationForm, UserLoginForm


# Registration view - handles new user sign up
def register_view(request):
    # check if they're already logged in
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        # print(form.errors) - debugging (took me ages to find why it wasn't saving)
        
        if form.is_valid():
            # saving user
            u = form.save()
            
            # autologin 
            login(request, u)
            
            messages.success(request, 'Account created!')
            return redirect('home')
        else:
            messages.error(request, 'Please fix the errors.')
    else:
        # get empty form
        form = UserRegistrationForm()
    
    return render(request, 'core/register.html', {'form': form})


# Login view
def login_view(request):
    if request.user.is_authenticated:
        # Check user type before redirecting to home
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin:index')
        if request.user.user_type in ['student', 'teacher']:
            return redirect('home')
        # If authenticated but invalid type, log them out to prevent home loop
        logout(request)
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # authenticate checks if username/password combo is correct
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # redirect to home page after login
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = UserLoginForm()
    
    return render(request, 'core/login.html', {'form': form})


# Logout view - simple one
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# Home page - redirects based on user type
@login_required
def home_view(request):
    current_user = request.user
    
    # If it's a staff user or superuser, they should go to the admin panel
    if current_user.is_staff or current_user.is_superuser:
        return redirect('admin:index')
    
    # send student to student dashboard
    if current_user.user_type == 'student':
        return redirect('student_dashboard')
    # send teacher to teacher dashboard
    elif current_user.user_type == 'teacher':
        return redirect('teacher_dashboard')
    else:
        # This is where the loop happens if we don't logout.
        # If we just redirect to login, and they are authenticated, 
        # login_view redirects them back here.
        messages.error(request, 'Invalid user profile type. Please contact support.')
        logout(request)
        return redirect('login')
