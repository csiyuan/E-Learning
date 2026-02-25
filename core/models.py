from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import random
import string

# custom user for student/teacher
class CustomUser(AbstractUser):
    USER_TYPES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    bio = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
    def __str__(self):
        # show username and type in admin
        return f"{self.username} ({self.user_type})"


# extra student info
class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True, blank=True)
    enrollment_date = models.DateField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"Student: {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.student_id:
            # generate id like STU-12345
            while True:
                num = ''.join(random.choices(string.digits, k=5))
                id = 'STU-' + num
                if not StudentProfile.objects.filter(student_id=id).exists():
                    self.student_id = id
                    break
        super().save(*args, **kwargs)
    
    def get_my_courses(self):
        # find all courses student is in
        obs = Enrollment.objects.filter(student=self)
        list = []
        for o in obs:
            list.append(o.course)
        return list


# Teacher profile - similar to StudentProfile but for teachers
# Teachers can create courses and upload materials
class TeacherProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='teacher_profile')
    teacher_id = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=100, default="Lecturer", blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    # added this field but not sure if I'll actually use it
    years_experience = models.IntegerField(default=0, blank=True)
    
    def __str__(self):
        return f"{self.title} {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.teacher_id:
            # auto-generate a unique teacher ID like TCH-12345
            while True:
                new_id = 'TCH-' + ''.join(random.choices(string.digits, k=5))
                if not TeacherProfile.objects.filter(teacher_id=new_id).exists():
                    self.teacher_id = new_id
                    break
        super().save(*args, **kwargs)
    
    # gets all courses created by this teacher
    def get_my_courses(self):
        courses_i_teach = Course.objects.filter(instructor=self)
        return courses_i_teach


class Course(models.Model):
    title = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    description = models.TextField()
    instructor = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='courses_teaching')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_students = models.IntegerField(default=50, blank=True)
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.course_code:
            # Find the highest existing CSXXX code using filter and order_by
            # Use regex to find only CS followed by numbers to be more robust
            last_course = Course.objects.filter(course_code__regex=r'^CS\d+$').order_by('-course_code').first()
            if last_course:
                try:
                    # Extract numeric part, handle potential extraction issues
                    num_str = last_course.course_code[2:]
                    if num_str.isdigit():
                        new_num = int(num_str) + 1
                        self.course_code = f'CS{new_num}'
                    else:
                        self.course_code = 'CS101'
                except Exception:
                    self.course_code = 'CS101'
            else:
                self.course_code = 'CS101'
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.course_code} - {self.title}" if self.course_code else self.title
    
    # counts how many students are enrolled
    def student_count(self):
        count = self.enrollments.count()
        return count
    
    # checks if the course is at capacity
    def is_full(self):
        current_count = self.student_count()
        if current_count >= self.max_students:
            return True
        else:
            return False


# Enrollment model - this is the "join table" between students and courses
# I couldn't use Django's built-in ManyToMany because I needed extra fields
# like enrollment date and completion status
class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)
    # status field - using choices for easy template work
    completion_status = models.CharField(
        max_length=20,
        choices=[
            ('ongoing', 'Ongoing'),
            ('completed', 'Completed'),
            ('dropped', 'Dropped'),
            ('blocked', 'Blocked') 
        ],
        default='ongoing'
    )
    
    class Meta:
        # this makes sure a student can't enroll in the same course twice
        unique_together = ('student', 'course')
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.student.user.username} enrolled in {self.course.course_code}"


# CourseMaterial - for storing PDFs, images, etc that teachers upload
class CourseMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # file field for uploading documents
    # MEDIA_ROOT is already set up in settings.py
    file = models.FileField(upload_to='course_materials/')
    uploaded_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # stores the file type so we can show different icons on the frontend
    file_type = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.course.course_code}"
        
    @property
    def filename(self):
        import os
        try:
            if not self.file or not self.file.name:
                return "Untitled"
            return os.path.basename(self.file.name)
        except Exception:
            return "Untitled"
    
    @property
    def safe_size(self):
        try:
            if self.file and self.file.storage.exists(self.file.name):
                return self.file.size
        except Exception:
            pass
        return None
    
    # auto gets file ext when saving
    def save(self, *args, **kwargs):
        if self.file:
            # get name after the dot
            ext = self.file.name.split('.')[-1].lower()
            self.file_type = ext
        super().save(*args, **kwargs)


# CourseFeedback - students can leave reviews/ratings for courses
class CourseFeedback(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='feedback')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    
    # rating from 1-5 stars. I loop through numbers to make the choices list
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # option for anonymous feedback
    is_anonymous = models.BooleanField(default=False)
    
    class Meta:
        # each student can only leave one feedback per course
        unique_together = ('course', 'student')
        ordering = ['-created_at']
    
    def __str__(self):
        if self.is_anonymous:
            return f"Anonymous feedback for {self.course.title}"
        else:
            return f"{self.student.user.username}'s feedback for {self.course.title}"


# StatusUpdate - for the student and teacher "feed" on their home page
# Kind of like social media posts but for users to share what they're working on
class StatusUpdate(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='status_updates', null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField(max_length=500)
    # optional link to a specific course (cohort)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='status_updates', null=True, blank=True)
    # added file support for "broadcast upload of files"
    file = models.FileField(upload_to='status_uploads/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # might add image support later if I have time
    # image = models.ImageField(upload_to='status_images/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        # formats the date nicely
        username = self.user.username if self.user else "System"
        return f"{username}: {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# Notification model - sends alerts to users
# For things like: new enrollment, new material uploaded, etc.
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('enrollment', 'New Enrollment'),
        ('material', 'New Material'),
        ('feedback', 'New Feedback'),
        ('submission', 'New Submission'),
        ('general', 'General'),
        ('system', 'System'),
        ('deadline', 'Deadline'),
    )
    
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    
    # saving when the notification was created
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # optional link to a course (not all notifications are course-related)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        # shows if the notification has been read or not
        if self.is_read:
            read_status = "Read"
        else:
            read_status = "Unread"
        return f"{self.recipient.username} - {self.notification_type} - {read_status}"


# ChatMessage - for the real-time chat feature
# Updated this to use room-based chat instead of person-to-person
# Using Django Channels for the WebSocket implementation
class ChatMessage(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    # room_name is the chat room identifier (like "general", "course_101", etc)
    room_name = models.CharField(max_length=255)
    
    # renamed from message to content for consistency with StatusUpdate
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # keeping this in case we want to mark messages as read later
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']  # oldest first, like a normal chat
    
    def __str__(self):
        return f"{self.sender.username} in {self.room_name}: {self.content[:50]}"


# Deadline model - tracks upcoming assignments and due dates
# requirement R1: "upcoming deadlines"
class Deadline(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='deadlines')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    # file for assignment instructions/sheet
    file = models.FileField(upload_to='deadlines/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.course.title} - {self.title} (Due: {self.due_date.strftime('%Y-%m-%d')})"
    
    def is_overdue(self):
        return timezone.now() > self.due_date

    @property
    def time_remaining(self):
        if self.is_overdue():
            return "Overdue"
        
        diff = self.due_date - timezone.now()
        
        if diff.days > 0:
            return f"{diff.days}d {diff.seconds // 3600}h left"
        
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h { (diff.seconds // 60) % 60}m left"
        
        minutes = (diff.seconds // 60) % 60
        if minutes > 0:
            return f"{minutes}m left"
            
        return "Seconds left"


class Submission(models.Model):
    deadline = models.ForeignKey(Deadline, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/%Y/%m/%d/')
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # ensures a student can only have one submission per deadline
        # they can overwrite it if we implement that logic in the view
        unique_together = ('deadline', 'student')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.user.username} - {self.deadline.title}"

    @property
    def file_name(self):
        if not self.file or not self.file.name:
            return "No file uploaded"
        return self.file.name.split('/')[-1]

