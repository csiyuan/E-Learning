from rest_framework import serializers
from .models import (
    Course, Enrollment, CourseMaterial, StudentProfile, TeacherProfile, 
    ChatMessage, StatusUpdate, CourseFeedback, Notification, CustomUser, Deadline, Submission
)

# serializers convert our models to JSON and back
# had to look up the documentation for this part

class CourseSerializer(serializers.ModelSerializer):
    # adding extra info that's not just the raw model fields
    instructor_name = serializers.CharField(source='instructor.user.get_full_name', read_only=True)
    enrolled_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'instructor', 'instructor_name', 
                  'max_students', 'enrolled_count', 'created_at']
        read_only_fields = ['id', 'instructor', 'instructor_name', 'enrolled_count', 'created_at']
    
    def get_enrolled_count(self, obj):
        # count how many students are enrolled
        return obj.enrollments.count()


class EnrollmentSerializer(serializers.ModelSerializer):
    # showing student and course names instead of just IDs
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'course', 'course_title', 
                  'enrolled_at', 'completion_status']
        read_only_fields = ['id', 'enrolled_at']


class CourseMaterialSerializer(serializers.ModelSerializer):
    # making file URLs work properly in API
    file_url = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = CourseMaterial
        fields = ['id', 'course', 'course_title', 'title', 'description', 
                  'file', 'file_url', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_url']
    
    def get_file_url(self, obj):
        # returns the full URL for the file
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class StudentProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = ['id', 'user', 'username', 'email', 'full_name', 'student_id', 'enrollment_date', 'gpa']
        read_only_fields = ['id', 'enrollment_date']



class TeacherProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = TeacherProfile
        fields = ['id', 'user', 'username', 'email', 'full_name', 'teacher_id', 'title', 'department', 'years_experience']
        read_only_fields = ['id']



# simple serializer for chat messages
class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'sender_username', 'room_name', 'content', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at']


class StatusUpdateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.profile_pic', read_only=True)
    
    class Meta:
        model = StatusUpdate
        fields = ['id', 'user', 'user_name', 'user_avatar', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']
        
    def create(self, validated_data):
        # ensure the status update is linked to the currently logged in user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class CourseFeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    
    class Meta:
        model = CourseFeedback
        fields = ['id', 'course', 'student', 'student_name', 'rating', 'comment', 'created_at', 'is_anonymous']
        read_only_fields = ['id', 'created_at', 'student']
        
    def to_representation(self, instance):
        # if feedback is anonymous, hide student info
        data = super().to_representation(instance)
        if instance.is_anonymous:
            data.pop('student', None)
            data.pop('student_name', None)
            data['student_name'] = "Anonymous Student"
        return data


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'notification_type', 'message', 'course', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at', 'recipient']


class CustomUserSerializer(serializers.ModelSerializer):
    # Requirement R4: REST interface for User data
    student_profile = StudentProfileSerializer(read_only=True)
    teacher_profile = TeacherProfileSerializer(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'user_type', 
                  'bio', 'profile_pic', 'student_profile', 'teacher_profile', 'date_joined']
        read_only_fields = ['id', 'user_type', 'date_joined']


class DeadlineSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.title', read_only=True)
    time_remaining = serializers.ReadOnlyField()
    submission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Deadline
        fields = ['id', 'course', 'course_name', 'title', 'description', 
                  'due_date', 'time_remaining', 'submission_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_submission_count(self, obj):
        return obj.submissions.count()


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    deadline_title = serializers.CharField(source='deadline.title', read_only=True)
    file_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Submission
        fields = ['id', 'deadline', 'deadline_title', 'student', 'student_name', 
                  'file', 'file_name', 'comment', 'submitted_at']
        read_only_fields = ['id', 'student', 'submitted_at']
