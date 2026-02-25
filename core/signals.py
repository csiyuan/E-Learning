from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment, CourseMaterial, Notification, StatusUpdate, Deadline

# These signals automatically trigger when certain actions happen in the database
# I found this much cleaner than putting all the logic in the views

@receiver(post_save, sender=Enrollment)
def notify_teacher_on_enrollment(sender, instance, created, **kwargs):
    # only run this when a NEW enrollment is created
    if not created or getattr(instance, '_silent', False):
        return
        
    course = instance.course
    student = instance.student
    teacher = course.instructor.user
    
    # create a notification for the teacher
    Notification.objects.create(
        recipient=teacher,
        notification_type='enrollment',
        message=f"{student.user.get_full_name()} has enrolled in {course.title}",
        course=course
    )

@receiver(post_save, sender=CourseMaterial)
def notify_students_on_material(sender, instance, created, **kwargs):
    # notify all students when new material is added to a course
    if not created or getattr(instance, '_silent', False):
        return
        
    course = instance.course
    material_title = instance.title
    
    # get all active students in the course
    enrollments = course.enrollments.filter(is_active=True)
    
    # loop through and notify each student
    # this might be slow if there are tons of students, could use bulk_create optimization later
    for enrollment in enrollments:
        Notification.objects.create(
            recipient=enrollment.student.user,
            notification_type='material',
            message=f"New material '{material_title}' added to {course.title}",
            course=course
        )
            
        # Notification only - no chat message for materials as per user request

@receiver(post_save, sender=StatusUpdate)
def notify_students_on_broadcast(sender, instance, created, **kwargs):
    # notify all students when a new broadcast (status update about a course) is posted
    if not created or not instance.course or getattr(instance, '_silent', False):
        return
        
    course = instance.course
    # use title if available, otherwise truncate content
    broadcast_title = instance.title if instance.title else (instance.content[:30] + '...')
    
    # get all active students in the course
    enrollments = course.enrollments.filter(is_active=True)
    
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    
    for enrollment in enrollments:
        student_user = enrollment.student.user
        
        # Create DB notification
        Notification.objects.create(
            recipient=student_user,
            notification_type='general', # or could add a 'broadcast' type
            message=f"New announcement in {course.title}: {broadcast_title}",
            course=course
        )
        
        # Send WebSocket notification
        try:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{student_user.username}',
                {
                    'type': 'send_notification',
                    'notification_type': 'general',
                    'message': f"New announcement in {course.title}: {broadcast_title}"
                }
            )
        except Exception as e:
            # print(f"WebSocket notification failed: {e}")
            pass
    
    # Post to chat channel (once, outside the loop)
    from .models import ChatMessage
    ChatMessage.objects.create(
        sender=instance.user,
        room_name=str(course.id),
        content=f"Announcement: {broadcast_title}",
        is_read=False
    )

@receiver(post_save, sender=Deadline)
def notify_students_on_deadline(sender, instance, created, **kwargs):
    # notify all students when a new deadline is established
    if not created or getattr(instance, '_silent', False):
        return
        
    course = instance.course
    deadline_title = instance.title
    
    # get all active students in the course
    enrollments = course.enrollments.filter(is_active=True)
    
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    
    for enrollment in enrollments:
        student_user = enrollment.student.user
        
        # Create DB notification
        Notification.objects.create(
            recipient=student_user,
            notification_type='deadline',
            message=f"NEW ASSIGNMENT: '{deadline_title}' for {course.title}. Due: {instance.due_date}",
            course=course
        )
        
        # Send WebSocket notification
        try:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{student_user.username}',
                {
                    'type': 'send_notification',
                    'notification_type': 'deadline',
                    'message': f"New Assignment in {course.title}: {deadline_title}. Check your dashboard."
                }
            )
        except Exception as e:
            pass
                
        # Post to chat channel
        from .models import ChatMessage
        instructor_user = course.instructor.user
        ChatMessage.objects.create(
            sender=instructor_user,
            room_name=str(course.id),
            content=f"🚨 NEW ASSIGNMENT POSTED: {deadline_title}. Deadline: {instance.due_date}",
            is_read=False
        )
