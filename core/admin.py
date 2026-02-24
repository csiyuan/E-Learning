from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, StudentProfile, TeacherProfile, 
    Course, Enrollment, CourseMaterial, 
    CourseFeedback, StatusUpdate, Notification, ChatMessage
)

# Custom user admin - extending the default one
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'user_type', 'is_staff']
    list_filter = ['user_type', 'is_staff', 'is_active']
    
    # adding our custom fields to the fieldsets
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'bio', 'profile_pic')}),
    )
    
    # for when we create new users in admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'bio', 'profile_pic')}),
    )

# Student profile admin
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'student_id', 'enrollment_date', 'last_active']
    search_fields = ['user__username', 'student_id']
    list_filter = ['enrollment_date']
    
    # auto-generate student_id if blank? might add later
    # prepopulated_fields = {'student_id': ('user__username',)}

# Teacher profile admin
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'teacher_id', 'department', 'years_experience']
    search_fields = ['user__username', 'teacher_id', 'department']
    list_filter = ['department']

# Course admin
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'course_code', 'instructor', 'student_count', 'is_active', 'created_at']
    search_fields = ['title', 'course_code', 'instructor__user__username']
    list_filter = ['is_active', 'created_at']
    
    # makes it easier to see the course info
    readonly_fields = ['created_at', 'updated_at']
    
    def student_count(self, obj):
        return obj.student_count()
    student_count.short_description = 'Enrolled Students'

# Enrollment admin
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrolled_at', 'completion_status']
    search_fields = ['student__user__username', 'course__title']
    list_filter = ['completion_status', 'enrolled_at']
    
    # prevent duplicate enrollments - handled by unique_together in model


# Course material admin
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'file_type', 'uploaded_by', 'uploaded_at']
    search_fields = ['title', 'course__title']
    list_filter = ['file_type', 'uploaded_at']
    readonly_fields = ['uploaded_at', 'file_type']

# Course feedback admin  
class CourseFeedbackAdmin(admin.ModelAdmin):
    list_display = ['course', 'student', 'rating', 'is_anonymous', 'created_at']
    search_fields = ['course__title', 'student__user__username']
    list_filter = ['rating', 'is_anonymous', 'created_at']
    readonly_fields = ['created_at']

# Status update admin
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_preview', 'created_at']
    search_fields = ['user__username', 'content']
    list_filter = ['created_at']
    
    def content_preview(self, obj):
        # showing just first 50 chars so it doesn't overflow
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

# Notification admin
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'message']
    list_filter = ['notification_type', 'is_read', 'created_at']
    
    # quick action to mark as read?
    actions = ['mark_as_read']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark selected as read'

# Chat message admin
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'room_name', 'message_preview', 'created_at', 'is_read']
    search_fields = ['sender__username', 'content', 'room_name']
    list_filter = ['is_read', 'created_at', 'room_name']
    
    def message_preview(self, obj):
        return obj.content[:40] + '...' if len(obj.content) > 40 else obj.content
    message_preview.short_description = 'Message'


# Register all the models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(TeacherProfile, TeacherProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(CourseMaterial, CourseMaterialAdmin)
admin.site.register(CourseFeedback, CourseFeedbackAdmin)
admin.site.register(StatusUpdate, StatusUpdateAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)

# Customize admin site header
admin.site.site_header = "eLearning Platform Admin"
admin.site.site_title = "eLearning Admin"
admin.site.index_title = "Welcome to eLearning Platform Administration"
