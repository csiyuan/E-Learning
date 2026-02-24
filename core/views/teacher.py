# teacher views - dashboard, course creation, uploads, student management
# everything that teachers interact with on their side of the app

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..forms import CourseCreateForm, CourseMaterialForm
from ..models import (
    StudentProfile, TeacherProfile,
    Course, Enrollment, CourseMaterial, StatusUpdate, Notification,
    CourseFeedback, Deadline, Submission
)


# Teacher dashboard view
@login_required
def teacher_dashboard(request):
    # only teachers can access
    if request.user.user_type != 'teacher':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    teacher_profile = request.user.teacher_profile
    
    # get all courses this teacher is teaching
    my_courses = teacher_profile.get_my_courses()
    
    # Check selected course from GET params
    selected_course_id_str = request.GET.get('course_filter')
    selected_course_id_int = int(selected_course_id_str) if selected_course_id_str and selected_course_id_str.isdigit() else None
    
    # Pre-calculate selection to avoid template equality check issues
    for course in my_courses:
        course.is_selected = (selected_course_id_int is not None and course.id == selected_course_id_int)
    
    # We fetch enrollments for courses taught by this teacher, excluding dropped
    # We include blocked students as requested (they have is_active=False)
    active_enrollments = Enrollment.objects.filter(
        course__instructor=teacher_profile
    ).filter(
        Q(is_active=True) | Q(completion_status='blocked')
    ).exclude(
        completion_status='dropped'
    )
    
    # Filter by course if selected
    selected_course_id = request.GET.get('course_filter')
    if selected_course_id:
        active_enrollments = active_enrollments.filter(course__id=selected_course_id)
        active_enrollments = active_enrollments.order_by('-enrolled_at')[:20]
    else:
        # When showing all courses, deduplicate by student
        # so each student only appears once in the list
        seen_students = set()
        unique_enrollments = []
        for enrollment in active_enrollments.order_by('-enrolled_at'):
            if enrollment.student_id not in seen_students:
                seen_students.add(enrollment.student_id)
                unique_enrollments.append(enrollment)
            if len(unique_enrollments) >= 20:
                break
        active_enrollments = unique_enrollments
    
    # get unread notifications
    unread_notifications = request.user.notifications.filter(is_read=False)

    # get recent activity (broadcasts + materials + deadlines)
    recent_broadcasts = StatusUpdate.objects.filter(user=request.user).order_by('-created_at')[:10]
    recent_materials = CourseMaterial.objects.filter(uploaded_by=teacher_profile).order_by('-uploaded_at')[:10]
    recent_deadlines = Deadline.objects.filter(course__instructor=teacher_profile).order_by('-created_at')[:10]
    
    # Add attributes for easier template rendering and sorting
    for update in recent_broadcasts:
        update.type = 'status'
        update.date = update.created_at
        
    for material in recent_materials:
        material.type = 'material'
        material.date = material.uploaded_at
        
    for deadline in recent_deadlines:
        deadline.type = 'deadline'
        deadline.date = deadline.created_at

    from operator import attrgetter
    # combine and sort safely
    recent_activity = sorted(
        list(recent_broadcasts) + list(recent_materials) + list(recent_deadlines), 
        key=attrgetter('date'), 
        reverse=True
    )[:10]
    
    context = {
        'teacher': teacher_profile,
        'courses': my_courses,
        'active_students': active_enrollments,
        'notifications': unread_notifications,
        'selected_course_id': int(selected_course_id) if selected_course_id and selected_course_id.isdigit() else None,
        'recent_activity': recent_activity, # unified feed
        'upcoming_deadlines': Deadline.objects.filter(course__instructor=teacher_profile, due_date__gte=timezone.now()).order_by('due_date')[:5],
    }
    
    return render(request, 'core/teacher/dashboard_v2.html', context)


# Create course view
@login_required
def create_course(request):
    # only teachers can create courses
    if request.user.user_type != 'teacher':
        messages.error(request, 'Only teachers can create courses')
        return redirect('home')
    
    if request.method == 'POST':
        form = CourseCreateForm(request.POST)
        
        if form.is_valid():
            # don't save yet, need to add instructor
            new_course = form.save(commit=False)
            new_course.instructor = request.user.teacher_profile
            new_course.save()
            
            messages.success(request, f'Course "{new_course.title}" created successfully!')
            return redirect('teacher_dashboard')
        else:
            messages.error(request, 'Please fix the errors below')
    else:
        form = CourseCreateForm()
    
    return render(request, 'core/teacher/create_course.html', {'form': form})


# Upload material view
@login_required
def upload_material(request, course_id):
    if request.user.user_type != 'teacher':
        messages.error(request, 'Only teachers can upload materials')
        return redirect('home')
    
    course = get_object_or_404(Course, id=course_id)
    
    # make sure this teacher owns this course
    if course.instructor != request.user.teacher_profile:
        messages.error(request, 'You can only upload materials to your own courses')
        return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        form = CourseMaterialForm(request.POST, request.FILES)
        
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.save()
            
            
            # notify all enrolled students about new material
            # database notifications + websocket updates
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            enrolled_students = course.enrollments.all()
            
            for enrollment in enrolled_students:
                student_user = enrollment.student.user
                
                # send websocket notification (real-time)
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'notifications_{student_user.username}',
                        {
                            'type': 'send_notification',
                            'notification_type': 'material',
                            'message': f'New material in {course.title}: {material.title}'
                        }
                    )
                except:
                    pass  # continue even if websocket fails
                
                # save notification to database too
                Notification.objects.create(
                    recipient=student_user,
                    notification_type='material',
                    message=f'New material uploaded in {course.title}: {material.title}',
                    course=course
                )
            
            messages.success(request, f'Material "{material.title}" uploaded successfully!')
            return redirect('course_detail', course_id=course.id)
        else:
            messages.error(request, 'Please fix the errors below')
    else:
        form = CourseMaterialForm()
    
    context = {
        'form': form,
        'course': course,
    }
    
    return render(request, 'core/teacher/upload_material.html', context)


# Course detail view (for teachers to see enrolled students and materials)
@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # check access permissions
    if request.user.user_type == 'teacher':
        # teacher can only view their own courses
        if course.instructor != request.user.teacher_profile:
            messages.error(request, 'You can only view your own courses')
            return redirect('teacher_dashboard')
    elif request.user.user_type == 'student':
        # student can only view courses they're enrolled in
        is_enrolled = course.enrollments.filter(student=request.user.student_profile).exists()
        if not is_enrolled:
            messages.error(request, 'You must be enrolled to view this course')
            return redirect('course_browse')
    
    # get enrolled students (for teacher view)
    enrolled_students = course.enrollments.all()
    
    # get course materials
    materials = course.materials.all().order_by('-uploaded_at')
    
    # get deadlines and submissions (for teacher view)
    deadlines = course.deadlines.all().order_by('-due_date')
    upcoming_deadlines = course.deadlines.filter(due_date__gte=timezone.now()).order_by('due_date')
    
    # get course feedback (for teacher view)
    feedbacks = CourseFeedback.objects.filter(course=course).order_by('-created_at')
    
    # calculate average rating
    avg_rating = 0
    if feedbacks.exists():
        total = sum([f.rating for f in feedbacks])
        avg_rating = total / feedbacks.count()
    
    context = {
        'course': course,
        'enrolled_students': enrolled_students,
        'materials': materials,
        'deadlines': deadlines,
        'upcoming_deadlines': upcoming_deadlines,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating,
        'feedback_count': feedbacks.count(),
        'courses': request.user.teacher_profile.get_my_courses() if request.user.user_type == 'teacher' else [],
    }
    
    return render(request, 'core/teacher/course_detail.html', context)


@login_required
def view_submissions(request, deadline_id):
    # Requirement: Teacher side to receive submissions
    deadline = get_object_or_404(Deadline, id=deadline_id)
    
    # ensure user is the teacher of this course
    if not hasattr(request.user, 'teacher_profile') or deadline.course.instructor != request.user.teacher_profile:
        messages.error(request, "Access Restricted: You are not authorized to view these submissions.")
        return redirect('teacher_dashboard')
        
    submissions = deadline.submissions.all().select_related('student__user')
    
    # Provide courses context for the dashboard sidebar
    courses = request.user.teacher_profile.get_my_courses()
    
    context = {
        'deadline': deadline,
        'submissions': submissions,
        'teacher': request.user.teacher_profile,
        'courses': deadline.course.instructor.get_my_courses()
    }
    return render(request, 'core/teacher/deadline_submissions.html', context)


# Remove student from course
@login_required
def remove_student_from_course(request, course_id, student_id):
    if request.user.user_type != 'teacher':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != request.user.teacher_profile:
        messages.error(request, 'You can only manage your own courses')
        return redirect('teacher_dashboard')
    
    student_profile = get_object_or_404(StudentProfile, user__id=student_id)
    enrollment = get_object_or_404(Enrollment, course=course, student=student_profile)
    
    # Check if we are blocking or removing
    action = request.GET.get('action', 'remove')
    
    if action == 'block':
        enrollment.completion_status = 'blocked'
        enrollment.is_active = False
        enrollment.save()
        messages.success(request, f'Student {student_profile.user.username} has been blocked from the course.')
    elif action == 'unblock':
        enrollment.completion_status = 'ongoing'
        enrollment.is_active = True
        enrollment.save()
        messages.success(request, f'Student {student_profile.user.username} has been unblocked and re-instated.')
    else:
        # Default is remove (delete enrollment)
        enrollment.delete()
        messages.success(request, f'Student {student_profile.user.username} has been removed from the course.')
    
    return redirect(request.META.get('HTTP_REFERER', 'teacher_dashboard'))


@login_required
def unified_dashboard_action(request):
    # handles all the teacher dashboard buttons
    if request.method != 'POST':
        return redirect('teacher_dashboard')
        
    type = request.POST.get('upload_type')
    title = request.POST.get('title')
    desc = request.POST.get('description', '')
    
    # material upload
    if type == 'material':
        cid = request.POST.get('course_id')
        if not cid:
            messages.error(request, "Need to pick a course.")
            return redirect('teacher_dashboard')
            
        c = get_object_or_404(Course, id=cid)
        
        # security check
        if hasattr(request.user, 'teacher_profile') and c.instructor != request.user.teacher_profile:
            messages.error(request, "Not your course!")
            return redirect('teacher_dashboard')
            
        # multiple files support
        files = request.FILES.getlist('file')
        if not files:
            messages.error(request, "No files found.")
            return redirect('teacher_dashboard')
            
        for f in files:
            CourseMaterial.objects.create(
                course=c,
                title=title if title else f.name,
                description=desc,
                file=f,
                uploaded_by=request.user.teacher_profile if hasattr(request.user, 'teacher_profile') else None
            )
        messages.success(request, f"Uploaded {len(files)} items.")
        
    # broadcasts/status updates
    elif type == 'broadcast':
        cid = request.POST.get('course_id')
        files = request.FILES.getlist('file')
        
        if not cid or cid == 'all':
            messages.error(request, "Pick a specific course for broadcasts.")
            return redirect('teacher_dashboard')
            
        target = get_object_or_404(Course, id=cid)

        # check if it's their course
        if hasattr(request.user, 'teacher_profile') and target.instructor != request.user.teacher_profile:
            messages.error(request, "Denied.")
            return redirect('teacher_dashboard')

        if not files:
            # text only
            StatusUpdate.objects.create(
                user=request.user,
                title=title,
                content=desc,
                course=target,
                file=None
            )
        else:
            # text + files
            for file_item in files:
                StatusUpdate.objects.create(
                    user=request.user,
                    title=title,
                    content=desc,
                    course=target,
                    file=file_item
                )
        messages.success(request, "Broadcast sent.")
        
    elif type == 'deadline':
        course_id = request.POST.get('course_id')
        due_date = request.POST.get('due_date')
        files = request.FILES.getlist('file')
        
        if not course_id or course_id == 'all':
            messages.error(request, "Assignments must be assigned to a specific cohort.")
            return redirect('teacher_dashboard')
            
        course = get_object_or_404(Course, id=course_id)
        
        # Create the deadline entry
        Deadline.objects.create(
            course=course,
            title=title,
            description=desc,
            due_date=due_date,
            file=files[0] if files else None # Take first file as prompt
        )
        
        messages.success(request, f"Assignment deadline set for {course.title}: {title}")
        
    return redirect(request.META.get('HTTP_REFERER', 'teacher_dashboard'))
