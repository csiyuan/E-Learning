# common views - shared between student and teacher
# stuff like chat, profiles, search, status updates

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from ..models import (
    CustomUser, StudentProfile,
    Course, Enrollment, CourseMaterial, StatusUpdate, Notification,
    ChatMessage, Deadline
)


# Status update posting - for both students and teachers
@login_required
def post_status(request):
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        # basic validation
        if not content:
            messages.error(request, 'Status update cannot be empty')
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        
        if len(content) > 500:
            messages.error(request, 'Status update is too long (max 500 characters)')
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        
        # create the status update
        StatusUpdate.objects.create(
            user=request.user,
            content=content
        )
        
        messages.success(request, 'Status update posted!')
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    # if not POST, just redirect back
    return redirect(request.META.get('HTTP_REFERER', 'home'))


# Chat room view
@login_required
def chat_room(request, room_name):
    # Fetch enrolled courses for the "Channels" sidebar
    enrolled_courses = []
    if request.user.user_type == 'student':
        if hasattr(request.user, 'student_profile'):
            enrollments = request.user.student_profile.enrollments.select_related('course').all()
            enrolled_courses = [e.course for e in enrollments]
    elif request.user.user_type == 'teacher':
        if hasattr(request.user, 'teacher_profile'):
            enrolled_courses = request.user.teacher_profile.courses_teaching.all()
    
    # Check if the current room corresponds to a course (for the "Materials" sidebar)
    current_course = None
    course_materials = []
    
    # Try to find a course with this room_name (could be ID or code)
    try:
        if room_name.isdigit():
            current_course = Course.objects.filter(id=int(room_name)).first()
        else:
            current_course = Course.objects.filter(course_code=room_name).first()
            
        # Standardize room_name to ID if course found for better isolation
        if current_course:
            room_name = str(current_course.id)
    except (ValueError, TypeError):
        current_course = None
    
    if current_course:
        # Security check: Ensure user is allowed to access this course chat
        has_access = False
        if request.user.user_type == 'student':
            has_access = Enrollment.objects.filter(student=request.user.student_profile, course=current_course).exists()
        elif request.user.user_type == 'teacher':
            has_access = current_course.instructor == request.user.teacher_profile
            
        if has_access:
            course_materials = current_course.materials.all().order_by('-uploaded_at')
        else:
            # If no access, maybe specific handling? For now, we'll just not show materials/course info
            # or could redirect. Let's keep it simple and just unset current_course
            current_course = None
            
    # Get chat history
    previous_messages = ChatMessage.objects.filter(room_name=room_name).order_by('created_at')
    
    # Fetch upcoming deadlines for this course
    upcoming_course_deadlines = []
    if current_course:
        upcoming_course_deadlines = Deadline.objects.filter(
            course=current_course, 
            due_date__gte=timezone.now()
        ).order_by('due_date')
        
        # Check submission status if student, or get counts if teacher
        if request.user.user_type == 'student' and hasattr(request.user, 'student_profile'):
            student_profile = request.user.student_profile
            for deadline in upcoming_course_deadlines:
                deadline.is_submitted = deadline.submissions.filter(student=student_profile).exists()
        elif request.user.user_type == 'teacher':
            for deadline in upcoming_course_deadlines:
                deadline.submission_count = deadline.submissions.count()
    
    context = {
        'room_name': room_name,
        'chat_history': previous_messages,
        'enrolled_courses': enrolled_courses,
        'current_course': current_course,
        'course_materials': course_materials,
        'upcoming_course_deadlines': upcoming_course_deadlines,
    }
    
    return render(request, 'core/chat.html', context)


@login_required
def chat_history_api(request, room_name):
    # Security check: Ensure user is allowed to access this course chat
    has_access = False
    current_course = None
    try:
        if room_name.isdigit():
            current_course = Course.objects.filter(id=int(room_name)).first()
        else:
            current_course = Course.objects.filter(course_code=room_name).first()
            
        # Standardize room_name to ID if course found for better isolation
        if current_course:
            room_name = str(current_course.id)
    except (ValueError, TypeError):
        pass
    
    if current_course:
        if request.user.user_type == 'student':
            has_access = Enrollment.objects.filter(student=request.user.student_profile, course=current_course).exists()
        elif request.user.user_type == 'teacher':
            has_access = current_course.instructor == request.user.teacher_profile
            
    if not has_access and room_name != 'general':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    previous_messages = ChatMessage.objects.filter(room_name=room_name).order_by('-created_at')[:50]
    
    messages_data = []
    for msg in reversed(previous_messages):
        messages_data.append({
            'username': msg.sender.username,
            'full_name': msg.sender.get_full_name() or msg.sender.username,
            'message': msg.content,
            'timestamp': msg.created_at.isoformat(),
        })
        
    return JsonResponse({'messages': messages_data})


# Public profile view - requirement: "discoverable and visible to other users"
def profile_view(request, username):
    viewed_user = get_object_or_404(CustomUser, username=username)
    
    # get their status updates
    status_updates = StatusUpdate.objects.filter(user=viewed_user).order_by('-created_at')[:10]
    
    # get their courses
    courses = []
    if viewed_user.user_type == 'student':
        if hasattr(viewed_user, 'student_profile'):
            courses = viewed_user.student_profile.get_my_courses()
    elif viewed_user.user_type == 'teacher':
        if hasattr(viewed_user, 'teacher_profile'):
            courses = viewed_user.teacher_profile.get_my_courses()
            
    # get deadlines if it's the user's own profile or they are a teacher/student in same courses
    # requirement says "interesting data such as registered courses, upcoming deadlines, etc"
    # we'll show public deadlines (upcoming)
    upcoming_deadlines = Deadline.objects.filter(course__in=courses, due_date__gte=timezone.now()).order_by('due_date')[:5] if courses else []
    
    context = {
        'viewed_user': viewed_user,
        'status_updates': status_updates,
        'courses': courses,
        'upcoming_deadlines': upcoming_deadlines,
    }
    
    return render(request, 'core/profile.html', context)


# Search users
@login_required
def search_users(request):
    q = request.GET.get('q', '')
    res = []
    
    if q:
        # searching across username and names
        # used Q because I needed 'OR' logic
        res = CustomUser.objects.filter(
            Q(username__icontains=q) | 
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).filter(is_active=True).distinct()
    
    return render(request, 'core/search_results.html', {'results': res, 'query': q})


@login_required
def api_search_users(request):
    # This is for the live search dropdown in the navigation bar
    # I'm using JsonResponse so the JavaScript can read the data easily
    query = request.GET.get('q', '')
    results = []
    
    if len(query) >= 2:
        # Only search if the user typed at least 2 characters
        users = CustomUser.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query)
        ).filter(is_active=True).distinct()[:5] # limit to 5 results to keep it fast
        
        for user in users:
            # Build the dictionary for each user to send back as JSON
            user_data = {
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'user_type': 'Lecturer' if user.user_type == 'teacher' else 'Student',
                'pfp_url': user.profile_pic.url if user.profile_pic else f'https://ui-avatars.com/api/?name={user.username}&background=0D1117&color=10B981'
            }
            results.append(user_data)
            
    return JsonResponse({'results': results})
