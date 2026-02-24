from rest_framework import viewsets, permissions, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    Course, Enrollment, CourseMaterial, StudentProfile, TeacherProfile, 
    ChatMessage, StatusUpdate, CourseFeedback, Notification, CustomUser, Deadline, Submission
)
from .serializers import (
    CourseSerializer, EnrollmentSerializer, CourseMaterialSerializer,
    StudentProfileSerializer, TeacherProfileSerializer, ChatMessageSerializer,
    StatusUpdateSerializer, CourseFeedbackSerializer, NotificationSerializer,
    CustomUserSerializer, DeadlineSerializer, SubmissionSerializer
)

# API views using ViewSets - these make CRUD operations really easy
# struggled a bit understanding REST framework at first but it's not too bad
# my tutor said ViewSets are basically like mini-apps that do everything for you

class CourseViewSet(viewsets.ModelViewSet):
    # handles all the CRUD stuff for courses
    # GET /api/courses/ shows all courses
    # POST /api/courses/ creates new course (teachers only)
    # there's also update and delete but I mostly use the first two
    # hope my instructor doesn't delete my courses lol
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    
    def get_permissions(self):
        # anyone can view courses, only teachers can create/edit them
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        # when creating a course, set the teacher as current user
        if hasattr(self.request.user, 'teacher_profile'):
            serializer.save(instructor=self.request.user.teacher_profile)
        else:
            # students can't create courses - that would be chaos
            raise exceptions.PermissionDenied("Only teachers can create courses")
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        # custom endpoint to get all students in a course
        # URL: /api/courses/{id}/students/
        course = self.get_object()
        enrollments = course.enrollments.all()
        students = [e.student for e in enrollments]
        serializer = StudentProfileSerializer(students, many=True, context={'request': request})
        return Response(serializer.data)


class EnrollmentViewSet(viewsets.ModelViewSet):
    # this handles student enrollments in courses
    # basically signs students up for courses
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # students only see their own enrollments
        # teachers see enrollments in their courses
        user = self.request.user
        if hasattr(user, 'student_profile'):
            return Enrollment.objects.filter(student=user.student_profile)
        elif hasattr(user, 'teacher_profile'):
            teacher_courses = Course.objects.filter(instructor=user.teacher_profile)
            return Enrollment.objects.filter(course__in=teacher_courses)
        return Enrollment.objects.none()
    
    def perform_create(self, serializer):
        # enroll the current student in a course
        if hasattr(self.request.user, 'student_profile'):
            serializer.save(student=self.request.user.student_profile)
        else:
            raise exceptions.PermissionDenied("Only students can enroll")


class CourseMaterialViewSet(viewsets.ModelViewSet):
    # handles file uploads for courses (PDFs, slides, etc)
    queryset = CourseMaterial.objects.all()
    serializer_class = CourseMaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # students see materials from courses they're enrolled in
        # teachers see materials from their own courses
        user = self.request.user
        if hasattr(user, 'student_profile'):
            enrolled_courses = Enrollment.objects.filter(
                student=user.student_profile
            ).values_list('course', flat=True)
            return CourseMaterial.objects.filter(course__in=enrolled_courses)
        elif hasattr(user, 'teacher_profile'):
            teacher_courses = Course.objects.filter(instructor=user.teacher_profile)
            return CourseMaterial.objects.filter(course__in=teacher_courses)
        return CourseMaterial.objects.none()
    
    def perform_create(self, serializer):
        # only teachers can upload materials
        if not hasattr(self.request.user, 'teacher_profile'):
            raise exceptions.PermissionDenied("Only teachers can upload materials")
        serializer.save()


class ChatMessageViewSet(viewsets.ModelViewSet):
    # chat message API - mostly used to get message history for a room
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # filter by room if provided
        room_name = self.request.query_params.get('room', None)
        if room_name:
            return ChatMessage.objects.filter(room_name=room_name).order_by('-created_at')[:50]
        return ChatMessage.objects.all().order_by('-created_at')[:100]
    
    def perform_create(self, serializer):
        # set current user as sender
        serializer.save(sender=self.request.user)


class StatusUpdateViewSet(viewsets.ModelViewSet):
    # handles student status updates that show on the feed
    queryset = StatusUpdate.objects.all()
    serializer_class = StatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # link the status update to the current student
        if hasattr(self.request.user, 'student_profile'):
            serializer.save(student=self.request.user.student_profile)
        else:
            raise exceptions.PermissionDenied("Only students can post status updates")


class CourseFeedbackViewSet(viewsets.ModelViewSet):
    # API for course reviews/feedback from students
    # need this for requirement R1f
    queryset = CourseFeedback.objects.all()
    serializer_class = CourseFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        # link feedback to the current student
        if hasattr(self.request.user, 'student_profile'):
            serializer.save(student=self.request.user.student_profile)
        else:
            raise exceptions.PermissionDenied("Only students can leave feedback")


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    # This is for the Activity Feed
    # I made it read-only because I don't want anyone to manually delete or create notifications thru API
    # they should only happen when someone enrolls or uploads something
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # return notifications for current user only
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        # endpoint to mark all as read or specific one
        # POST /api/notifications/mark_read/
        notification_id = request.data.get('id')
        if notification_id:
            Notification.objects.filter(id=notification_id, recipient=request.user).update(is_read=True)
        else:
            # mark all as read
            self.get_queryset().update(is_read=True)
        return Response({'status': 'marked read'})


class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    # Requirement R4: REST interface for User data
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        # returns the current user's profile
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student_profile'):
            # students only see their own submissions
            return Submission.objects.filter(student=user.student_profile)
        elif hasattr(user, 'teacher_profile'):
            # teachers see submissions for their courses
            teacher_courses = Course.objects.filter(instructor=user.teacher_profile)
            return Submission.objects.filter(deadline__course__in=teacher_courses)
        return Submission.objects.none()
    
    def perform_create(self, serializer):
        # only students can submit
        if not hasattr(self.request.user, 'student_profile'):
            raise exceptions.PermissionDenied("Only students can submit assignments")
        
        # ensure student is enrolled in the course associated with the deadline
        deadline = serializer.validated_data.get('deadline')
        student = self.request.user.student_profile
        
        if not Enrollment.objects.filter(student=student, course=deadline.course).exists():
            raise exceptions.PermissionDenied("You must be enrolled in the course to submit this assignment")
            
        # check if deadline is overdue (optional: we can allow late submissions if needed)
        # for now let's allow it but maybe flag it? model doesn't have late flag yet.
        
        # support overwriting existing submission
        Submission.objects.filter(deadline=deadline, student=student).delete()
        
        serializer.save(student=student)


class DeadlineViewSet(viewsets.ModelViewSet):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # students see deadlines for their courses
        # teachers see deadlines for courses they teach
        user = self.request.user
        if hasattr(user, 'student_profile'):
            enrolled_courses = Enrollment.objects.filter(
                student=user.student_profile
            ).values_list('course', flat=True)
            return Deadline.objects.filter(course__in=enrolled_courses)
        elif hasattr(user, 'teacher_profile'):
            teacher_courses = Course.objects.filter(instructor=user.teacher_profile)
            return Deadline.objects.filter(course__in=teacher_courses)
        return Deadline.objects.none()
    
    def perform_create(self, serializer):
        # only teachers can create deadlines
        if not hasattr(self.request.user, 'teacher_profile'):
            raise exceptions.PermissionDenied("Only teachers can create deadlines")
        
        # ensure the course belongs to the teacher
        course = serializer.validated_data.get('course')
        if course.instructor != self.request.user.teacher_profile:
            raise exceptions.PermissionDenied("You can only create deadlines for your own courses")
            
        serializer.save()


