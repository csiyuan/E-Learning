from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import (
    CustomUser, StudentProfile, TeacherProfile, Course, 
    Enrollment, CourseMaterial, StatusUpdate, ChatMessage,
    CourseFeedback, Notification, Deadline
)
from datetime import timedelta
import random
from django.core.files.base import ContentFile

# this command populates the database with test data
# run it with: python manage.py seed_data
class Command(BaseCommand):
    help = 'Seeds the database with test data for demonstration (Davis Only)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting to seed database (Davis Mode)...')
        
        # clear existing data first
        self.stdout.write('Purging all existing data...')
        Course.objects.all().delete()
        CourseMaterial.objects.all().delete()
        Deadline.objects.all().delete()
        Notification.objects.all().delete()
        StatusUpdate.objects.all().delete()
        Enrollment.objects.all().delete()
        ChatMessage.objects.all().delete()
        CourseFeedback.objects.all().delete()
        # Keep users but we will filter them in seed
        
        # 1. Create Teacher pro_davis
        data = {'username': 'prof_davis', 'first_name': 'James', 'last_name': 'Davis', 'email': 'jdavis@edu.com', 'title': 'Professor', 'dept': 'Data Science'}
        
        if not CustomUser.objects.filter(username=data['username']).exists():
            user = CustomUser.objects.create_user(
                username=data['username'],
                password='password123',
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                user_type='teacher'
            )
            teacher = TeacherProfile.objects.create(
                user=user,
                teacher_id='TCH1001',
                title=data['title'],
                department=data['dept']
            )
            self.stdout.write(f'Created teacher: {data["username"]}')
        else:
            user = CustomUser.objects.get(username=data['username'])
            # Ensure user is teacher type
            user.user_type = 'teacher'
            user.save()
            teacher, _ = TeacherProfile.objects.get_or_create(user=user, defaults={'teacher_id': 'TCH1001', 'title': data['title'], 'department': data['dept']})
            self.stdout.write(f'Teacher already exists: {data["username"]}')

        # Clean up other teachers
        CustomUser.objects.filter(user_type='teacher').exclude(username='prof_davis').delete()

        # 2. Create Davis Courses
        course_data = [
            {'title': 'Data Science Fundamentals', 'desc': 'Introduction to data analysis, visualization, and machine learning basics.', 'max': 28},
            {'title': 'Machine Learning Applications', 'desc': 'Practical machine learning techniques and real-world applications.', 'max': 20},
        ]
        
        courses = []
        for data in course_data:
            course = Course.objects.create(
                title=data['title'],
                description=data['desc'],
                instructor=teacher,
                max_students=data['max']
            )
            courses.append(course)
            self.stdout.write(f"Created course: {data['title']}")
        
        # 3. Create Student (emma1 only)
        if not CustomUser.objects.filter(username='emma1').exists():
            emma_user = CustomUser.objects.create_user(
                username='emma1',
                password='password123',
                first_name='Emma',
                last_name='Brown',
                email='emma1@student.edu',
                user_type='student'
            )
            emma_profile = StudentProfile.objects.create(
                user=emma_user,
                student_id='STU2001'
            )
            self.stdout.write('Created student: emma1')
        else:
            emma_user = CustomUser.objects.get(username='emma1')
            emma_profile = emma_user.student_profile
            self.stdout.write('Student already exists: emma1')
        
        students = [emma_profile]
        
        # Clean up other students (keep only emma1)
        CustomUser.objects.filter(user_type='student').exclude(username='emma1').delete()

        # 4. Enrollments (enroll all 6 students in both courses)
        for course in courses:
            for student in students:
                enrollment = Enrollment.objects.create(
                    student=student,
                    course=course,
                    enrolled_at=timezone.now() - timedelta(days=random.randint(1, 15))
                )
                enrollment._silent = True
                enrollment.save()

        # 5. Course Materials
        material_titles = ['Lecture Slides - Week 1', 'Assignment Guidelines', 'Practical Dataset']
        for course in courses:
            for title in material_titles:
                material = CourseMaterial(
                    course=course,
                    title=title,
                    description=f'Essential resource for {course.title}',
                    file=ContentFile(b"Davis Data Asset"),
                    uploaded_at=timezone.now() - timedelta(days=random.randint(1, 10))
                )
                material.file.name = f"{title.replace(' ', '_').lower()}.txt"
                material._silent = True
                material.save()

        # 6. Deadlines
        deadline_templates = [
            {'title': 'Exploratory Data Quiz', 'days_offset': 5},
            {'title': 'Model Deployment Milestone', 'days_offset': 15},
        ]
        for course in courses:
            for template in deadline_templates:
                deadline = Deadline(
                    course=course,
                    title=f"{course.course_code}: {template['title']}",
                    description="Standard academic requirement.",
                    due_date=timezone.now() + timedelta(days=template['days_offset']),
                    file=ContentFile(b"Davis Prompt Asset"),
                    created_at=timezone.now() - timedelta(days=5)
                )
                deadline.file.name = f"{template['title'].replace(' ', '_').lower()}.txt"
                deadline._silent = True
                deadline.save()

        # 7. Feedback & Chat
        for course in courses:
            student = students[0]
            CourseFeedback.objects.create(
                course=course,
                student=student,
                rating=5,
                comment="Professor Davis is exceptional.",
                created_at=timezone.now() - timedelta(days=2)
            )
            
            ChatMessage.objects.create(
                room_name=str(course.id),
                sender=student.user,
                content="Excited for this ML course!",
                created_at=timezone.now() - timedelta(hours=1)
            )

        self.stdout.write(self.style.SUCCESS('Successfully cleaned up and re-seeded for Davis only!'))
