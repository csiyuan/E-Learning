# eLearning Platform

A Django-based eLearning web application with real-time features and REST API support

## Features

- **User Authentication**: Separate student and teacher accounts with role-based dashboards
- **Course Management**: Teachers can create courses and upload materials (PDFs, images, etc)
- **Enrollment System**: Students can browse and enroll in courses
- **Real-Time Chat**: WebSocket-powered chat rooms using Django Channels
- **Live Notifications**: Real-time alerts for enrollments and new materials
- **REST API**: Full API access for courses, enrollments, materials, and chat
- **Bento Dark Mode**: Modern dark theme UI

## Tech Stack

- **Backend**: Django 6.0
- **Database**: SQLite (dev), PostgreSQL recommended for production
- **Real-Time**: Django Channels + Daphne (WebSockets)
- **API**: Django REST Framework
- **Frontend**: HTML, CSS (TailwindCSS), JavaScript

## Setup Instructions

### 1. Install Dependencies

```bash
pip install django channels channels-redis daphne djangorestframework
```

### 2. Database Setup

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 3. Running the Server

**For WebSocket support (real-time chat/notifications):**
```bash
daphne -b 127.0.0.1 -p 8000 elearning_platform.asgi:application
```

**For basic development (no WebSockets):**
```bash
python manage.py runserver
```

### 4. Create Test Users

```bash
python manage.py shell
```

Then run:
```python
from django.contrib.auth import get_user_model
from core.models import StudentProfile, TeacherProfile

User = get_user_model()

# Create student1
student_user = User.objects.create_user(
    username='student1',
    password='password123',
    user_type='student',
    email='student1@test.com'
)
StudentProfile.objects.create(user=student_user)

# Create teacher1
teacher_user = User.objects.create_user(
    username='teacher1',
    password='password123',
    user_type='teacher',
    email='teacher1@test.com'
)
TeacherProfile.objects.create(user=teacher_user, expertise='Computer Science')
```

## Project Structure

```
elearning_platform/
├── core/                     # Main app
│   ├── models.py            # Database models
│   ├── views.py             # View logic
│   ├── forms.py             # Form definitions
│   ├── consumers.py         # WebSocket consumers
│   ├── serializers.py       # API serializers
│   ├── api_views.py         # API viewsets
│   ├── templates/           # HTML templates
│   └── static/              # CSS, JS, images
├── elearning_platform/      # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py             # ASGI config for WebSockets
└── media/                   # Uploaded files
```

## API Endpoints

Base URL: `http://127.0.0.1:8000/api/`

### Courses
- `GET /api/courses/` - List all courses
- `POST /api/courses/` - Create course (teachers only)
- `GET /api/courses/{id}/` - Get course details
- `GET /api/courses/{id}/students/` - List enrolled students

### Enrollments
- `GET /api/enrollments/` - List enrollments
- `POST /api/enrollments/` - Enroll in course (students only)

### Materials
- `GET /api/materials/` - List course materials
- `POST /api/materials/` - Upload material (teachers only)

### Chat
- `GET /api/chat/?room=general` - Get chat messages for a room

## WebSocket Endpoints

- `ws://127.0.0.1:8000/ws/chat/{room_name}/` - Chat room connection
- `ws://127.0.0.1:8000/ws/notifications/` - Personal notifications

## Running Tests

```bash
python manage.py test
```

## Key Features Explained

### Real-Time Chat
- Uses WebSockets for instant messaging
- Room-based chat system
- Message history stored in database

### Notifications
- Real-time WebSocket notifications
- Triggers: student enrollment, material upload
- Both WebSocket (instant) and database storage

### Course Management
- Max student limits
- Material upload with file handling
-Start/end dates
- Teacher-specific course views

## Notes

- This project uses student-friendly code style with lots of comments
- Default settings use DEBUG=True (change for production!)
- Media files stored locally in `/media/` directory
- CSRF protection enabled for forms
- Authentication required for most views

## License

MIT License - feel free to use this for learning!

## Author

Built as a learning project demonstrating Django, WebSockets, and REST APIs
# E-Learning-Platform
