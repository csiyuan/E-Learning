# student-facing views - dashboard, enrollment, course details, feedback, submissions
# this is where most of the student interaction logic lives

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..forms import SubmissionForm
from ..models import (
    CustomUser, StudentProfile, TeacherProfile,
    Course, Enrollment, CourseMaterial, StatusUpdate, Notification,
    ChatMessage, CourseFeedback, Deadline, Submission
)


# Student dashboard view
@login_required
def student_dashboard(request):
    # make sure only students can access this
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # get the student's profile
    student_profile = request.user.student_profile
    
    # get student's enrolled courses
    enrolled_courses = student_profile.get_my_courses()
    
    # Calculate if each course has a deadline due (upcoming and not submitted)
    # Calculate if each course has a deadline due (any unsubmitted deadline)
    now = timezone.now()
    for course in enrolled_courses:
        course_deadlines = course.deadlines.all()
        if not course_deadlines.exists():
            course.highlight_state = 'none'
        else:
            # Check if there are any unsubmitted deadlines (any time)
            unsubmitted = course_deadlines.exclude(submissions__student=student_profile)
            if unsubmitted.exists():
                course.highlight_state = 'orange'
            else:
                course.highlight_state = 'emerald'

    # get teachers for these courses
    # used a loop to be safe - might be a better way but this works
    instructors = []
    for c in enrolled_courses:
        if c.instructor:
            instructors.append(c.instructor.user)
    
    from datetime import timedelta
    # last week only
    seven_days = now - timedelta(days=7)

    # get recent status updates
    # 1. Student's own updates
    # 2. Updates linked to enrolled courses
    # 3. "Global" updates from instructors of enrolled courses (where course is None)
    # AND only from the last 7 days
    status_updates = StatusUpdate.objects.filter(
        (Q(user=request.user) | 
        Q(course__in=enrolled_courses) |
        (Q(user__in=instructors) & Q(course__isnull=True))) &
        Q(created_at__gte=seven_days)
    ).distinct()

    # Get recent deadlines (last 7 days)
    recent_deadlines = Deadline.objects.filter(
        course__in=enrolled_courses,
        created_at__gte=seven_days
    ).order_by('-created_at')[:10]

    # Get recent course materials (last 7 days)
    recent_materials = CourseMaterial.objects.filter(
        course__in=enrolled_courses,
        uploaded_at__gte=seven_days
    ).order_by('-uploaded_at')[:10]

    # Combine and sort by date
    from itertools import chain
    from operator import attrgetter

    # add type for template rendering
    for item in status_updates:
        item.type = 'status'
        item.date = item.created_at
        
    for item in recent_materials:
        item.type = 'material'
        item.date = item.uploaded_at
        
    for item in recent_deadlines:
        item.type = 'deadline'
        item.date = item.created_at

    # sort by date
    # found this on stackoverflow (chained lists are weird in python)
    combined_updates = sorted(
        chain(status_updates, recent_materials, recent_deadlines),
        key=attrgetter('date'),
        reverse=True
    )[:15]
    
    # get unread notifications
    unread_notifications = request.user.notifications.filter(is_read=False)
    
    # Calculate material distribution for the "Resource Spectrum" bar
    # We'll calculate a global one AND one for each course
    all_materials = CourseMaterial.objects.filter(course__in=enrolled_courses)
    total_materials = all_materials.count()
    
    # helper for categorization
    categories = [
        {'name': 'Documents', 'icon': 'description', 'color': 'bg-blue-400', 'glow': 'shadow-[0_0_12px_rgba(96,165,250,0.4)]', 'exts': ['pdf', 'doc', 'docx', 'txt']},
        {'name': 'Media', 'icon': 'video_library', 'color': 'bg-orange-400', 'glow': 'shadow-[0_0_12px_rgba(251,146,60,0.4)]', 'exts': ['mp4', 'mov', 'wav', 'mp3']},
        {'name': 'Slides', 'icon': 'present_to_all', 'color': 'bg-purple-400', 'glow': 'shadow-[0_0_12px_rgba(192,132,252,0.4)]', 'exts': ['ppt', 'pptx']},
        {'name': 'Archives', 'icon': 'folder_zip', 'color': 'bg-edustream-emerald', 'glow': 'shadow-[0_0_12px_rgba(16,185,129,0.4)]', 'exts': ['zip', 'rar', '7z']},
    ]

    def get_distribution(materials_qs, course=None):
        count_total = materials_qs.count()
        
        # Add assignments to the mix
        if course:
            assignments_count = course.deadlines.filter(due_date__gte=timezone.now()).count()
        else:
            assignments_count = Deadline.objects.filter(course__in=enrolled_courses, due_date__gte=timezone.now()).count()
            
        count_total += assignments_count
        
        if count_total == 0:
            return []
        
        dist = []
        # Add Assignments (now "Submissions") first or as requested
        if assignments_count > 0:
            dist.append({
                'name': 'Submissions',
                'icon': 'assignment_late',
                'percentage': (assignments_count / count_total) * 100,
                'color': 'bg-orange-500',
                'glow': 'shadow-[0_0_15px_rgba(249,115,22,0.5)]',
                'count': assignments_count
            })

        for cat in categories:
            # Shift Media color if it conflicts? Student said orange for assignments.
            # I'll keep Media as is or tweak if it feels too close.
            count = materials_qs.filter(file_type__in=cat['exts']).count()
            if count > 0:
                dist.append({
                    'name': cat['name'],
                    'icon': cat['icon'],
                    'percentage': (count / count_total) * 100,
                    'color': cat['color'],
                    'glow': cat['glow'],
                    'count': count
                })
        
        # Other
        accounted = sum(d['count'] for d in dist)
        if accounted < count_total:
            other_count = count_total - accounted
            dist.append({
                'name': 'Other',
                'icon': 'inventory_2',
                'percentage': (other_count / count_total) * 100,
                'color': 'bg-slate-400',
                'glow': 'shadow-[0_0_12px_rgba(148,163,184,0.4)]',
                'count': other_count
            })
        return dist

    # Global distribution
    global_distribution = get_distribution(all_materials)
    
    # Per-course distribution
    for course in enrolled_courses:
        course.distribution = get_distribution(course.materials.all(), course=course)
    
    # Get all unsubmitted deadlines (upcoming and overdue)
    upcoming_deadlines = Deadline.objects.filter(
        course__in=enrolled_courses
    ).exclude(
        submissions__student=student_profile
    ).order_by('due_date')[:10]
    for deadline in upcoming_deadlines:
        deadline.is_submitted = deadline.submissions.filter(student=student_profile).exists()
    
    context = {
        'student': student_profile,
        'courses': enrolled_courses,
        'status_updates': combined_updates,
        'notifications': unread_notifications,
        'material_distribution': global_distribution,
        'total_materials_count': total_materials,
        'upcoming_deadlines': upcoming_deadlines,
    }
    
    return render(request, 'core/student/dashboard.html', context)


# Course browsing page - shows all available courses
@login_required
def course_browse(request):
    # get all active courses
    courses = Course.objects.filter(is_active=True)
    
    enrolled_ids = []
    sorted_list = []
    
    if request.user.user_type == 'student':
        student = request.user.student_profile
        # get list of ids they are in
        enrolls = Enrollment.objects.filter(student=student)
        enrolled_ids = [e.course.id for e in enrolls]
        
        # move enrolled to top
        enrolled = []
        others = []
        for c in courses:
            if c.id in enrolled_ids:
                enrolled.append(c)
            else:
                others.append(c)
        sorted_list = enrolled + others
    else:
        # for teachers just show normally
        sorted_list = list(courses)
    
    context = {
        'courses': sorted_list,
        'enrolled_course_ids': enrolled_ids,
    }
    
    return render(request, 'core/student/course_browse.html', context)


# Course enrollment - student enrolls in a course
@login_required
def enroll_course(request, course_id):
    # only students can enroll
    if request.user.user_type != 'student':
        messages.error(request, 'Only students can enroll in courses')
        return redirect('course_browse')
    
    student = request.user.student_profile
    course = get_object_or_404(Course, id=course_id)
    
    # check if course is full
    if course.is_full():
        messages.error(request, 'This course is full')
        return redirect('course_browse')
    
    # check if already enrolled
    # I'm using filter().exists() instead of try/except because it seems simpler
    already_enrolled = Enrollment.objects.filter(student=student, course=course).exists()
    
    if already_enrolled:
        messages.warning(request, 'You are already enrolled in this course')
        return redirect('course_browse')
    
    # create the enrollment
    new_enrollment = Enrollment.objects.create(
        student=student,
        course=course,
        completion_status='ongoing'
    )
    
    # send real-time notification to teacher
    # this is the websocket part, took me forever to debug
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    channel_layer = get_channel_layer()
    teacher_username = course.instructor.user.username
    
    try:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{teacher_username}',
            {
                'type': 'send_notification',
                'notification_type': 'enrollment',
                'message': f'{request.user.username} just enrolled in {course.title}'
            }
        )
    except Exception as e:
        # if websocket fails, that's okay, enrollment still went through
        print(f"Notification failed: {e}")  # keeping this for debugging
    
    # also save to database so teacher can see it later
    Notification.objects.create(
        recipient=course.instructor.user,
        notification_type='enrollment',
        message=f'{request.user.username} enrolled in {course.title}',
        course=course
    )
    
    # create a notification for the teacher
    # I think it's nice for teachers to know when someone enrolls
    notification_message = f"{student.user.username} has enrolled in {course.title}"
    Notification.objects.create(
        recipient=course.instructor.user,
        notification_type='enrollment',
        message=notification_message,
        course=course
    )
    
    messages.success(request, f'Successfully enrolled in {course.title}!')
    return redirect('course_browse')


# Student course detail view (after enrollment)
@login_required
def course_detail_student(request, course_id):
    # only students can view this
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    student = request.user.student_profile
    course = get_object_or_404(Course, id=course_id)
    
    # check if enrolled
    is_enrolled = Enrollment.objects.filter(student=student, course=course).exists()
    if not is_enrolled:
        messages.error(request, 'You must be enrolled to view course details')
        return redirect('course_browse')
    
    # get course materials
    materials = course.materials.all().order_by('-uploaded_at')
    
    # check if student has submitted feedback
    has_feedback = CourseFeedback.objects.filter(student=student, course=course).exists()
    
    # calculate average rating
    feedbacks = CourseFeedback.objects.filter(course=course)
    avg_rating = 0
    if feedbacks.exists():
        total = sum([f.rating for f in feedbacks])
        avg_rating = total / feedbacks.count()
    
    # get upcoming deadlines
    upcoming_deadlines = course.deadlines.filter(due_date__gte=timezone.now()).order_by('due_date')
    
    context = {
        'course': course,
        'materials': materials,
        'has_feedback': has_feedback,
        'avg_rating': avg_rating,
        'feedback_count': feedbacks.count(),
        'is_enrolled': is_enrolled,
        'upcoming_deadlines': upcoming_deadlines,
    }
    
    return render(request, 'core/student/course_detail.html', context)


@login_required
def submit_assignment(request, deadline_id):
    # Requirement: Submission part for deadlines
    deadline = get_object_or_404(Deadline, id=deadline_id)
    
    print(f"DEBUG: submit_assignment called for deadline {deadline_id} by user {request.user.username} (type: {request.user.user_type})")
    
    # ensure user is a student and enrolled
    if not hasattr(request.user, 'student_profile'):
        print(f"DEBUG: User {request.user.username} has no student_profile. Redirecting.")
        messages.error(request, "Only students can submit assignments.")
        return redirect('student_dashboard')
        
    student = request.user.student_profile
    is_enrolled = Enrollment.objects.filter(student=student, course=deadline.course).exists()
    print(f"DEBUG: Student {student.user.username} enrollment in {deadline.course.title}: {is_enrolled}")
    
    if not is_enrolled:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('student_dashboard')
        
    # check for existing submission to overwrite
    existing_submission = Submission.objects.filter(deadline=deadline, student=student).first()
    
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES, instance=existing_submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.deadline = deadline
            submission.student = student
            submission.save()

            # Notify the instructor
            instructor_user = deadline.course.instructor.user
            Notification.objects.create(
                recipient=instructor_user,
                notification_type='submission',
                message=f"{student.user.get_full_name() or student.user.username} has submitted: {deadline.title}",
                course=deadline.course
            )

            messages.success(request, f"Submission for {deadline.title} successful!")
            return redirect('student_dashboard')
    else:
        form = SubmissionForm(instance=existing_submission)
        
    context = {
        'deadline': deadline,
        'form': form,
        'existing_submission': existing_submission
    }
    return render(request, 'core/student/submit_assignment.html', context)


# Course feedback submission - student rates a course
@login_required
def submit_feedback(request, course_id):
    # only students can submit feedback
    if request.user.user_type != 'student':
        messages.error(request, 'Only students can submit feedback')
        return redirect('course_browse')
    
    student = request.user.student_profile
    course = get_object_or_404(Course, id=course_id)
    
    # check if student is enrolled
    is_enrolled = Enrollment.objects.filter(student=student, course=course).exists()
    if not is_enrolled:
        messages.error(request, 'You must be enrolled to leave feedback')
        return redirect('course_browse')
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        
        # basic validation
        if not rating or not comment:
            messages.error(request, 'Please provide both rating and comment')
            return redirect('submit_feedback', course_id=course.id)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid rating value')
            return redirect('submit_feedback', course_id=course.id)
        
        # check if feedback already exists
        existing_feedback = CourseFeedback.objects.filter(student=student, course=course).first()
        
        if existing_feedback:
            # update existing feedback
            existing_feedback.rating = rating
            existing_feedback.comment = comment
            existing_feedback.is_anonymous = is_anonymous
            existing_feedback.save()
            messages.success(request, 'Your feedback has been updated!')
        else:
            # create new feedback
            CourseFeedback.objects.create(
                student=student,
                course=course,
                rating=rating,
                comment=comment,
                is_anonymous=is_anonymous
            )
            messages.success(request, 'Thank you for your feedback!')
        
        return redirect('course_detail_student', course_id=course.id)
    
    # GET request - show feedback form
    # check if user already submitted feedback
    existing_feedback = CourseFeedback.objects.filter(student=student, course=course).first()
    
    context = {
        'course': course,
        'existing_feedback': existing_feedback,
    }
    
    return render(request, 'core/student/submit_feedback.html', context)


# Feedback views
@login_required
def feedback_list(request):
    """
    Displays a list of enrolled courses for the student to provide feedback on.
    """
    if request.user.user_type != 'student':
        messages.error(request, "Only students can provide feedback.")
        return redirect('student_dashboard')
        
    student_profile = getattr(request.user, 'student_profile', None)
    if not student_profile:
        courses = []
    else:
        # Filter for ongoing courses that are active (current semester)
        active_enrollments = student_profile.enrollments.filter(
            completion_status='ongoing',
            course__is_active=True
        ).select_related('course')
        courses = [e.course for e in active_enrollments]
        
    context = {
        'courses': courses,
    }
    return render(request, 'core/student/feedback_list.html', context)


@login_required
def course_feedback(request, course_id):
    """
    Displays and handles the feedback form for a specific course.
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if student is enrolled
    student_profile = getattr(request.user, 'student_profile', None)
    # Check if course is in the student's courses
    if not student_profile or course not in student_profile.get_my_courses():
        messages.error(request, "You are not enrolled in this course.")
        return redirect('feedback_list')
        
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comments')
        
        if not rating:
            messages.error(request, "Please provide a rating.")
            return redirect('course_feedback', course_id=course_id)

        # Check for existing feedback
        feedback, created = CourseFeedback.objects.get_or_create(
            student=student_profile,
            course=course,
            defaults={'rating': rating, 'comment': comment} # defaults for create
        )
        
        if not created:
            # Update existing
            feedback.rating = rating
            feedback.comment = comment
            feedback.save()
            messages.success(request, f"Feedback updated for {course.title}!")
        else:
            messages.success(request, f"Feedback submitted for {course.title}!")
            
            messages.success(request, f"Feedback submitted for {course.title}!")
            
        # return redirect('feedback_list')
        context = {
            'course': course,
            'success': True
        }
        return render(request, 'core/student/course_feedback.html', context)
        
    context = {
        'course': course,
    }
    return render(request, 'core/student/course_feedback.html', context)
