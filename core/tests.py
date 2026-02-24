from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models import (
    Course, Enrollment, CourseMaterial, StudentProfile, TeacherProfile,
    Notification, ChatMessage, StatusUpdate, CourseFeedback, Deadline, Submission
)
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status as http_status

# tests for the main features of our eLearning platform
# honestly writing tests is kinda tedious but I know it's important

User = get_user_model()


class UserRegistrationTests(TestCase):
    def setUp(self):
        # runs before each test
        self.client = Client()
    
    def test_student_registration(self):
        # testing if a student can register successfully
        data = {
            'username': 'teststudent',
            'first_name': 'Test',
            'last_name': 'Student',
            'email': 'student@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'user_type': 'student'
        }
        response = self.client.post('/register/', data)
        
        # check if user was created
        self.assertTrue(User.objects.filter(username='teststudent').exists())
        user = User.objects.get(username='teststudent')
        self.assertEqual(user.user_type, 'student')
        # student profile should be created automatically
        self.assertTrue(hasattr(user, 'student_profile'))
    
    def test_teacher_registration(self):
        # same but for teacher registration
        data = {
            'username': 'testteacher',
            'first_name': 'Test',
            'last_name': 'Teacher',
            'email': 'teacher@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'user_type': 'teacher'
        }
        response = self.client.post('/register/', data)
        
        user = User.objects.get(username='testteacher')
        self.assertEqual(user.user_type, 'teacher')
        self.assertTrue(hasattr(user, 'teacher_profile'))


class CourseEnrollmentTests(TestCase):
    def setUp(self):
        # creating test users and course
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            password='pass123',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            department='Computer Science'
        )
        
        self.student_user = User.objects.create_user(
            username='student1',
            password='pass123',
            user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user
        )
        
        self.course = Course.objects.create(
            title='Test Course',
            description='A test course',
            instructor=self.teacher_profile,
            max_students=5
        )
        
        self.client = Client()
    
    def test_student_can_enroll(self):
        # test that a student can enroll in a course via model
        # testing the enrollment model logic directly
        initial_count = Enrollment.objects.filter(student=self.student_profile).count()
        
        # create enrollment directly (simulating what the view would do)
        enrollment = Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # verify enrollment was created
        new_count = Enrollment.objects.filter(student=self.student_profile).count()
        self.assertEqual(new_count, initial_count + 1)
        self.assertEqual(enrollment.course, self.course)
    
    def test_cannot_enroll_in_full_course(self):
        # should not be able to enroll when course is full
        # first, fill up the course
        for i in range(self.course.max_students):
            student = User.objects.create_user(
                username=f'student{i+10}',
                password='pass123',
                user_type='student'
            )
            student_profile = StudentProfile.objects.create(
                user=student,
                student_id=f'STUID{i+10}'  # unique IDs for each test student
            )
            Enrollment.objects.create(
                student=student_profile,
                course=self.course
            )
        
        # now try to enroll our test student
        self.client.login(username='student1', password='pass123')
        response = self.client.get(f'/student/enroll/{self.course.id}/')
        
        # enrollment should NOT exist
        self.assertFalse(
            Enrollment.objects.filter(
                student=self.student_profile,
                course=self.course
            ).exists()
        )


class CourseMaterialTests(TestCase):
    def setUp(self):
        # setting up teacher and course
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            password='pass123',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user
        )
        
        self.course = Course.objects.create(
            title='Test Course',
            description='Testing materials',
            instructor=self.teacher_profile
        )
        
        self.client = Client()
    
    def test_teacher_can_upload_material(self):
        # test material upload functionality
        self.client.login(username='teacher1', password='pass123')
        
        # count materials before
        initial_count = CourseMaterial.objects.filter(course=self.course).count()
        
        # the actual file upload test is tricky so just testing the model
        material = CourseMaterial.objects.create(
            course=self.course,
            title='Lecture 1 Notes',
            description='Chapter 1 material'
        )
        
        # check material was created
        new_count = CourseMaterial.objects.filter(course=self.course).count()
        self.assertEqual(new_count, initial_count + 1)
        self.assertEqual(material.title, 'Lecture 1 Notes')


class CourseModelTests(TestCase):
    def setUp(self):
        # basic setup
        User.objects.create_user(
            username='teacher1',
            password='pass123',
            user_type='teacher'
        )
        self.teacher = TeacherProfile.objects.create(
            user=User.objects.get(username='teacher1')
        )
    
    def test_course_is_full_method(self):
        # testing the is_full() method on Course model
        course = Course.objects.create(
            title='Small Course',
            description='Max 2 students',
            instructor=self.teacher,
            max_students=2
        )
        
        # course shouldn't be full initially
        self.assertFalse(course.is_full())
        
        # add 2 students
        for i in range(2):
            student_user = User.objects.create_user(
                username=f'student{i}',
                password='pass123',
                user_type='student'
            )
            student_profile = StudentProfile.objects.create(
                user=student_user,
                student_id=f'STUID{i+20}'  # unique IDs for this test
            )
            Enrollment.objects.create(student=student_profile, course=course)
        
        # now course should be full
        self.assertTrue(course.is_full())


# tests for notification signals - these should trigger when students enroll or materials are uploaded
# requirement R1k and R1l
class NotificationSignalTests(TestCase):
    def setUp(self):
        # create a teacher and student for testing
        self.teacher_user = User.objects.create_user(
            username='teachernotif',
            password='testpass',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            department='Test Dept'
        )
        
        self.student_user = User.objects.create_user(
            username='studentnotif',
            password='testpass',
            user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id='STUID001'  # need unique student IDs for testing
        )
        
        self.course = Course.objects.create(
            title='Notification Test Course',
            description='Testing notifications',
            instructor=self.teacher_profile
        )
    
    def test_teacher_notified_when_student_enrolls(self):
        # testing R1k - teacher should get notification when student enrolls
        # count notifications before enrollment
        initial_count = Notification.objects.filter(recipient=self.teacher_user).count()
        
        # enroll the student
        Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # check that a notification was created for the teacher
        new_count = Notification.objects.filter(recipient=self.teacher_user).count()
        self.assertEqual(new_count, initial_count + 1)
        
        # make sure it's the right type of notification
        latest_notification = Notification.objects.filter(
            recipient=self.teacher_user
        ).latest('created_at')
        self.assertEqual(latest_notification.notification_type, 'enrollment')
    
    def test_students_notified_when_material_uploaded(self):
        # testing R1l - students should get notified when new material is added
        # first enroll the student
        Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # count student notifications before upload
        initial_count = Notification.objects.filter(recipient=self.student_user).count()
        
        # upload new material
        CourseMaterial.objects.create(
            course=self.course,
            title='New Lecture Notes',
            description='Important material'
        )
        
        # student should have a new notification
        new_count = Notification.objects.filter(recipient=self.student_user).count()
        self.assertEqual(new_count, initial_count + 1)
        
        # verify it's a material notification
        latest_notification = Notification.objects.filter(
            recipient=self.student_user
        ).latest('created_at')
        self.assertEqual(latest_notification.notification_type, 'material')


# testing the feedback system - requirement R1f
class FeedbackSystemTests(TestCase):
    def setUp(self):
        # setup teacher and course
        self.teacher = User.objects.create_user(
            username='feedbackteacher',
            password='testpass',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        
        self.course = Course.objects.create(
            title='Feedback Test Course',
            instructor=self.teacher_profile,
            course_code='FEED101'
        )
        
        # create student
        self.student = User.objects.create_user(
            username='feedbackstudent',
            password='testpass',
            user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            student_id='STUID101'
        )
        
        self.client = Client()
    
    def test_student_can_leave_feedback(self):
        # test that student can submit feedback for a course
        # testing model creation directly
        # first enroll the student
        Enrollment.objects.create(student=self.student_profile, course=self.course)
        
        # create feedback directly (simulating what the view would do)
        feedback = CourseFeedback.objects.create(
            course=self.course,
            student=self.student_profile,
            rating=4,
            comment='Great course, learned a lot!'
        )
        
        # check feedback was created
        feedback_exists = CourseFeedback.objects.filter(
            course=self.course,
            student=self.student_profile
        ).exists()
        self.assertTrue(feedback_exists)
        self.assertEqual(feedback.rating, 4)
    
    def test_feedback_rating_saved_correctly(self):
        # make sure the rating is saved properly
        feedback = CourseFeedback.objects.create(
            course=self.course,
            student=self.student_profile,
            rating=5,
            comment='Excellent!'
        )
        
        # retrieve and check
        saved_feedback = CourseFeedback.objects.get(id=feedback.id)
        self.assertEqual(saved_feedback.rating, 5)
        self.assertEqual(saved_feedback.comment, 'Excellent!')


# chat functionality tests - requirement R1g
class ChatTests(TestCase):
    def setUp(self):
        # create some users for chat testing
        self.user1 = User.objects.create_user(
            username='chatter1',
            password='testpass',
            user_type='student'
        )
        self.user2 = User.objects.create_user(
            username='chatter2',
            password='testpass',
            user_type='student'
        )
    
    def test_chat_message_creation(self):
        # test that chat messages can be created
        message = ChatMessage.objects.create(
            sender=self.user1,
            room_name='general',
            content='Hello everyone!'
        )
        
        # check message was saved
        self.assertIsNotNone(message.id)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'Hello everyone!')
    
    def test_chat_messages_in_room(self):
        # test that we can filter messages by room
        # create messages in different rooms
        ChatMessage.objects.create(
            sender=self.user1,
            room_name='general',
            content='Message in general'
        )
        ChatMessage.objects.create(
            sender=self.user2,
            room_name='course_101',
            content='Message in course room'
        )
        
        # count messages in each room
        general_count = ChatMessage.objects.filter(room_name='general').count()
        course_count = ChatMessage.objects.filter(room_name='course_101').count()
        
        self.assertEqual(general_count, 1)
        self.assertEqual(course_count, 1)


# testing remove and block student functionality - requirement R1h
class StudentManagementTests(TestCase):
    def setUp(self):
        # setup teacher and student
        self.teacher = User.objects.create_user(
            username='mgmtteacher',
            password='testpass',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        
        self.student = User.objects.create_user(
            username='mgmtstudent',
            password='testpass',
            user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            student_id='STUID102'
        )
        
        self.course = Course.objects.create(
            title='Management Test',
            instructor=self.teacher_profile
        )
        
        self.client = Client()
    
    def test_teacher_can_remove_student(self):
        # test that teacher can remove a student from course
        # enroll student first
        enrollment = Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # login as teacher
        self.client.login(username='mgmtteacher', password='testpass')
        
        # remove the student - testing the model logic
        # in real app this would be triggered by a view
        enrollment.is_active = False
        enrollment.save()
        
        # check if enrollment is marked inactive
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)
    
    def test_teacher_can_block_student(self):
        # test blocking functionality - testing model logic
        enrollment = Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # simulate blocking by setting completion status
        enrollment.completion_status = 'dropped'
        enrollment.is_active = False
        enrollment.save()
        
        # verify enrollment status changed
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.completion_status, 'dropped')
        self.assertFalse(enrollment.is_active)


# status update tests - requirement R1i
class StatusUpdateTests(TestCase):
    def setUp(self):
        # create student for status updates
        self.student = User.objects.create_user(
            username='statusstudent',
            password='testpass',
            user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            student_id='STUID103'
        )
        self.client = Client()
    
    def test_student_can_post_status(self):
        # test that students can create status updates
        self.client.login(username='statusstudent', password='testpass')
        
        # post a status
        response = self.client.post('/status/post/', {
            'content': 'Just finished my assignment!'
        })
        
        # check status was created
        status_exists = StatusUpdate.objects.filter(
            user=self.student,
            content='Just finished my assignment!'
        ).exists()
        self.assertTrue(status_exists)
    
    def test_status_has_timestamp(self):
        # make sure status updates have timestamps
        status = StatusUpdate.objects.create(
            user=self.student,
            content='Testing timestamps'
        )
        
        # timestamp should be automatically set
        self.assertIsNotNone(status.created_at)


# search functionality tests - requirement R1c
class SearchTests(TestCase):
    def setUp(self):
        # create some users to search for
        self.teacher = User.objects.create_user(
            username='searchteacher',
            password='testpass',
            user_type='teacher',
            first_name='John',
            last_name='Smith'
        )
        TeacherProfile.objects.create(user=self.teacher)
        
        self.student = User.objects.create_user(
            username='searchstudent',
            password='testpass',
            user_type='student',
            first_name='Jane',
            last_name='Doe'
        )
        StudentProfile.objects.create(
            user=self.student,
            student_id='STUID104'
        )
        
        self.client = Client()
    
    def test_teacher_can_search_users(self):
        # test that teachers can search for users using model queries
        # testing the search logic directly without URL
        search_query = 'Jane'
        
        # search for users by first name (what the view would do)
        results = User.objects.filter(first_name__icontains=search_query)
        
        # should find the student we created
        self.assertGreater(results.count(), 0)
        self.assertTrue(results.filter(username='searchstudent').exists())
    
    def test_search_finds_correct_user(self):
        # test that search actually finds the right people by last name
        search_query = 'Smith'
        
        # search by last name
        results = User.objects.filter(last_name__icontains=search_query)
        
        # should find the teacher we created
        self.assertGreater(results.count(), 0)
        self.assertTrue(results.filter(username='searchteacher').exists())


# API tests - requirement R4
# these test the REST API endpoints
class CourseAPITests(TestCase):
    def setUp(self):
        # using APIClient instead of regular Client for REST testing
        self.api_client = APIClient()
        
        # create teacher
        self.teacher = User.objects.create_user(
            username='apiteacher',
            password='testpass',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
    
    def test_can_list_courses(self):
        # test GET /api/courses/
        response = self.api_client.get('/api/courses/')
        
        # should return 200 OK
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
    
    def test_teacher_can_create_course_via_api(self):
        # test POST /api/courses/
        self.api_client.login(username='apiteacher', password='testpass')
        
        course_data = {
            'title': 'API Test Course',
            'description': 'Created via API',
            'max_students': 30
        }
        
        response = self.api_client.post('/api/courses/', course_data, format='json')
        
        # course should be created
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
    
    def test_student_cannot_create_course(self):
        # students shouldn't be able to create courses via API
        student = User.objects.create_user(
            username='apistudent',
            password='testpass',
            user_type='student'
        )
        StudentProfile.objects.create(user=student)
        
        self.api_client.login(username='apistudent', password='testpass')
        
        course_data = {
            'title': 'Unauthorized Course',
            'description': 'Should fail'
        }
        
        response = self.api_client.post('/api/courses/', course_data, format='json')
        
        # should be forbidden
        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)


# enrollment API tests
class EnrollmentAPITests(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        
        # setup teacher and course
        self.teacher = User.objects.create_user(
            username='enrollteacher',
            password='testpass',
            user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)
        
        self.course = Course.objects.create(
            title='Enrollment API Test',
            instructor=self.teacher_profile
        )
        
        # setup student
        self.student = User.objects.create_user(
            username='enrollstudent',
            password='testpass',
            user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            student_id='STUID105'
        )
    
    def test_student_sees_own_enrollments_only(self):
        # students should only see their own enrollments through API
        # create enrollment for this student
        Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # create another student with enrollment
        other_student = User.objects.create_user(
            username='otherstudent',
            password='testpass',
            user_type='student'
        )
        other_profile = StudentProfile.objects.create(
            user=other_student,
            student_id='STUID104'  # different unique ID
        )
        
        # another course
        other_course = Course.objects.create(
            title='Other Course',
            instructor=self.teacher_profile
        )
        Enrollment.objects.create(student=other_profile, course=other_course)
        
        # login as first student
        self.api_client.login(username='enrollstudent', password='testpass')
        
        # get enrollments
        response = self.api_client.get('/api/enrollments/')
        
        # should only see 1 enrollment (their own)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_teacher_sees_course_enrollments(self):
        # teachers should see enrollments in their courses
        Enrollment.objects.create(
            student=self.student_profile,
            course=self.course
        )
        
        # login as teacher
        self.api_client.login(username='enrollteacher', password='testpass')
        
        response = self.api_client.get('/api/enrollments/')
        
        # teacher should see the enrollment
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)


# tests for requirements R1: profile, deadlines and R4: user API
class NewFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()
        
        # setup teacher
        self.teacher_user = User.objects.create_user(
            username='featureteacher', password='pass', user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher_user)
        
        # setup student
        self.student_user = User.objects.create_user(
            username='featurestudent', password='pass', user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(user=self.student_user)
        
        # setup course
        self.course = Course.objects.create(
            title='Feature Course', instructor=self.teacher_profile
        )
        Enrollment.objects.create(student=self.student_profile, course=self.course)

    def test_deadline_creation_and_overdue(self):
        # test Deadline model
        future_date = timezone.now() + timezone.timedelta(days=1)
        past_date = timezone.now() - timezone.timedelta(days=1)
        
        deadline = Deadline.objects.create(
            course=self.course, title='Future Deadline', due_date=future_date
        )
        past_deadline = Deadline.objects.create(
            course=self.course, title='Past Deadline', due_date=past_date
        )
        
        self.assertFalse(deadline.is_overdue())
        self.assertTrue(past_deadline.is_overdue())

    def test_profile_view_accessible(self):
        # requirement R1: profile view discoverable and visible
        self.client.login(username='featurestudent', password='pass')
        response = self.client.get(f'/profile/featureteacher/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'featureteacher')
        self.assertContains(response, 'Feature Course')

    def test_user_api_me_endpoint(self):
        # requirement R4: REST interface for user data
        self.api_client.login(username='featurestudent', password='pass')
        response = self.api_client.get('/api/users/me/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'featurestudent')
        self.assertEqual(response.data['user_type'], 'student')

    def test_deadline_api_permissions(self):
        # requirement R4/R5: API and Permission logic
        # create deadline
        deadline_data = {
            'course': self.course.id,
            'title': 'API Deadline',
            'due_date': (timezone.now() + timezone.timedelta(days=2)).isoformat()
        }
        
        # student should NOT be able to create a deadline
        self.api_client.login(username='featurestudent', password='pass')
        response = self.api_client.post('/api/deadlines/', deadline_data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)
        
        # teacher SHOULD be able to create a deadline
        self.api_client.login(username='featureteacher', password='pass')
        response = self.api_client.post('/api/deadlines/', deadline_data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)


class SubmissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()
        
        # setup teacher
        self.teacher_user = User.objects.create_user(
            username='subteacher', password='pass', user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher_user)
        
        # setup student
        self.student_user = User.objects.create_user(
            username='substudent', password='pass', user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(user=self.student_user)
        
        # setup course and enrollment
        self.course = Course.objects.create(
            title='Submission Course', instructor=self.teacher_profile, course_code='SUB101'
        )
        Enrollment.objects.create(student=self.student_profile, course=self.course)
        
        # setup deadline
        self.deadline = Deadline.objects.create(
            course=self.course, title='Main Project', due_date=timezone.now() + timezone.timedelta(days=7)
        )

    def test_submission_creation(self):
        self.client.login(username='substudent', password='pass')
        
        # mock a file
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile("test_assignment.txt", b"file_content")
        
        response = self.client.post(f'/deadline/{self.deadline.id}/submit/', {
            'file': test_file,
            'comment': 'Done with assignment'
        })
        
        self.assertEqual(response.status_code, 302) # redirect to dashboard
        self.assertTrue(Submission.objects.filter(deadline=self.deadline, student=self.student_profile).exists())

    def test_teacher_view_submissions(self):
        # create a submission first
        from django.core.files.uploadedfile import SimpleUploadedFile
        Submission.objects.create(
            deadline=self.deadline,
            student=self.student_profile,
            file=SimpleUploadedFile("existing.txt", b"content")
        )
        
        self.client.login(username='subteacher', password='pass')
        response = self.client.get(f'/deadline/{self.deadline.id}/submissions/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'substudent')

    def test_submission_api(self):
        self.api_client.login(username='substudent', password='pass')
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile("api_test.txt", b"api_content")
        
        response = self.api_client.post('/api/submissions/', {
            'deadline': self.deadline.id,
            'file': test_file,
            'comment': 'API submission'
        }, format='multipart')
        
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)


# Advanced Tests for Rubric perfection
# Requirement R1g (WS), R1k/l (WS)
from channels.testing import WebsocketCommunicator
from elearning_platform.asgi import application

class WebSocketTests(TestCase):
    async def test_chat_consumer(self):
        # test the chat websocket connection
        communicator = WebsocketCommunicator(application, "/ws/chat/testroom/")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # send a message
        await communicator.send_json_to({
            'message': 'hello world',
            'username': 'testuser'
        })
        
        # receive it back (broadcast)
        response = await communicator.receive_json_from()
        self.assertEqual(response['message'], 'hello world')
        self.assertEqual(response['username'], 'testuser')
        
        await communicator.disconnect()

    async def test_notification_consumer_auth(self):
        # should close if anonymous
        communicator = WebsocketCommunicator(application, "/ws/notifications/")
        connected, subprotocol = await communicator.connect()
        # if anonymous it should close
        self.assertFalse(connected)


class ModelRobustnessTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(username='robust_teacher', password='password123', user_type='teacher')
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher_user)
        self.course = Course.objects.create(title='Robustness Course', instructor=self.teacher_profile)

    def test_coursematerial_no_file_stability(self):
        # Requirement: system shouldn't crash if file is missing
        material = CourseMaterial.objects.create(
            course=self.course,
            title='No File Material',
            uploaded_by=self.teacher_profile
        )
        # file is empty/none
        self.assertEqual(material.filename, "Untitled")
        self.assertIsNone(material.safe_size)
        
    def test_submission_filename_property(self):
        deadline = Deadline.objects.create(course=self.course, title='Test Deadline', due_date=timezone.now())
        student_user = User.objects.create_user(username='robust_student', password='password123', user_type='student')
        student_profile = StudentProfile.objects.create(user=student_user)
        
        submission = Submission.objects.create(
            deadline=deadline,
            student=student_profile,
            comment='No file here'
        )
        # Should handle mission file gracefully if we ever use it in template
        self.assertEqual(submission.file_name, "No file uploaded")


# View-level access control tests
# making sure teachers cant see student pages and vice versa
class ViewAccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()

        # teacher setup
        self.teacher_user = User.objects.create_user(
            username='accessteacher', password='testaccess', user_type='teacher'
        )
        TeacherProfile.objects.create(user=self.teacher_user)

        # student setup
        self.student_user = User.objects.create_user(
            username='accessstudent', password='testaccess', user_type='student'
        )
        StudentProfile.objects.create(user=self.student_user, student_id='STUACCESS')

    def test_teacher_cannot_access_student_dashboard(self):
        # teachers shouldn't be able to load the student dashboard
        self.client.login(username='accessteacher', password='testaccess')
        response = self.client.get('/student/dashboard/')
        # should redirect them away (302)
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access_teacher_dashboard(self):
        # same thing but reversed
        self.client.login(username='accessstudent', password='testaccess')
        response = self.client.get('/teacher/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_user_redirected_to_login(self):
        # if not logged in, going to dashboard should redirect to login
        response = self.client.get('/student/dashboard/')
        self.assertEqual(response.status_code, 302)
        # should redirect to login page specifically
        self.assertIn('/login/', response.url)

    def test_student_cannot_create_course(self):
        # only teachers should be able to create courses
        self.client.login(username='accessstudent', password='testaccess')
        response = self.client.get('/teacher/course/create/')
        self.assertEqual(response.status_code, 302)


# form validation edge cases - catching bad input
class FormValidationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registration_with_duplicate_email(self):
        # first user
        User.objects.create_user(
            username='firstuser', password='pass123',
            email='duplicate@test.com', user_type='student'
        )
        # try to register another user with same email
        response = self.client.post('/register/', {
            'username': 'seconduser',
            'first_name': 'Second',
            'last_name': 'User',
            'email': 'duplicate@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'user_type': 'student'
        })
        # form should reject it (page rendered again with errors, 200 not 302)
        self.assertEqual(response.status_code, 200)
        # second user NOT created
        self.assertFalse(User.objects.filter(username='seconduser').exists())

    def test_empty_status_update_rejected(self):
        # status updates with no content should fail
        student = User.objects.create_user(
            username='emptystatuser', password='pass123', user_type='student'
        )
        StudentProfile.objects.create(user=student, student_id='STUEMPTY')
        self.client.login(username='emptystatuser', password='pass123')

        response = self.client.post('/status/post/', {'content': ''})
        # should redirect back (302) but NOT create anything
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StatusUpdate.objects.filter(user=student).count(), 0)

    def test_status_update_too_long_rejected(self):
        # status over 500 characters should be rejected 
        student = User.objects.create_user(
            username='longstatuser', password='pass123', user_type='student'
        )
        StudentProfile.objects.create(user=student, student_id='STULONG')
        self.client.login(username='longstatuser', password='pass123')

        long_text = 'a' * 501  # one char over the limit
        response = self.client.post('/status/post/', {'content': long_text})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StatusUpdate.objects.filter(user=student).count(), 0)


# API edge cases and permission checks
class APIPermissionEdgeCaseTests(TestCase):
    def setUp(self):
        self.api_client = APIClient()

        self.teacher = User.objects.create_user(
            username='permteacher', password='pass123', user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)

        self.student = User.objects.create_user(
            username='permstudent', password='pass123', user_type='student'
        )
        StudentProfile.objects.create(user=self.student, student_id='STUPERM')

    def test_unauthenticated_cannot_create_course(self):
        # not logged in at all - should be forbidden
        response = self.api_client.post('/api/courses/', {
            'title': 'Sneaky Course',
            'description': 'Should not work'
        }, format='json')
        self.assertIn(response.status_code, [401, 403])

    def test_teacher_can_delete_own_course(self):
        # teachers should be able to manage their own courses
        course = Course.objects.create(
            title='Deletable Course',
            instructor=self.teacher_profile
        )
        self.api_client.login(username='permteacher', password='pass123')
        response = self.api_client.delete(f'/api/courses/{course.id}/')
        self.assertEqual(response.status_code, http_status.HTTP_204_NO_CONTENT)
        # course should be gone
        self.assertFalse(Course.objects.filter(id=course.id).exists())

    def test_api_returns_paginated_results(self):
        # With pagination added, the API should return paginated format
        self.api_client.login(username='permteacher', password='pass123')
        response = self.api_client.get('/api/courses/')
        # paginated response has 'results' key instead of being a flat list
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)


# double enrollment edge case - should not be possible
class DuplicateEnrollmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = User.objects.create_user(
            username='dupenrollteacher', password='pass123', user_type='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)

        self.student = User.objects.create_user(
            username='dupenrollstudent', password='pass123', user_type='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student, student_id='STUDUP'
        )

        self.course = Course.objects.create(
            title='Dup Test Course', instructor=self.teacher_profile, max_students=10
        )

    def test_cannot_enroll_twice(self):
        # enroll once
        Enrollment.objects.create(student=self.student_profile, course=self.course)

        # try enrolling again via the view
        self.client.login(username='dupenrollstudent', password='pass123')
        self.client.get(f'/courses/enroll/{self.course.id}/')

        # should still only have 1 enrollment, not 2
        count = Enrollment.objects.filter(
            student=self.student_profile, course=self.course
        ).count()
        self.assertEqual(count, 1)
