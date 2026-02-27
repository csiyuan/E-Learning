# 🎓 My E-Learning Platform

Hey there! Welcome to my E-Learning platform. I built this Django-based web application to create a seamless, interactive experience for both students and teachers. My main goal was to go beyond basic database operations and integrate some cool real-time features.

## ✨ What Does It Do?

I designed the app with two main types of users in mind:
- **Teachers** can easily create courses, set capacities, manage deadlines, and upload materials (like PDFs and images). They also have a dedicated dashboard to broadcast messages and track student feedback.
- **Students** can browse available courses, enroll, download materials, and submit their assignments before the deadline hits.

But the most exciting parts are the **real-time features**:
- **Live Notifications:** Whenever a teacher uploads new material or a student enrolls in a course, the notification pops up instantly without needing to refresh the page!
- **Real-Time Chat:** I built an interactive chat room using WebSockets (via Django Channels) so students and teachers can gather and talk to each other inside the course rooms.

Oh, and I also added a sleek, modern **Dark Mode** (Bento style) because everyone loves dark mode! 🌙

---

## 🛠️ The Tech Stack

Here's what I used under the hood:
- **Backend:** Python & Django (with Django REST Framework for the API)
- **Real-Time Magic:** Django Channels, Daphne, and Redis
- **Database:** SQLite for local development (super easy to swap to PostgreSQL for production)
- **Frontend:** HTML, Vanilla JavaScript, and TailwindCSS for that modern, clean look.

---

## 🚀 How to Run It Locally

If you want to spin this up on your own machine, follow these steps. It's pretty straightforward!

### 1. Grab the dependencies
Make sure you have a virtual environment set up and activated, then run:
```bash
pip install -r requirements.txt
```

### 2. Set up the Database
Let's get the database ready and create an admin account so you can poke around:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 3. Start the Server!
Because we're using WebSockets for the chat and notifications, the standard development server won't cut it. We need Daphne:
```bash
daphne -b 127.0.0.1 -p 8000 elearning_platform.asgi:application
```
*(But if you just want to test basic stuff without the real-time WebSockets, `python manage.py runserver` still works).*

### 4. Create Some Dummy Users (Optional)
To really test it out, you'll want a student and a teacher. You can run `python manage.py shell` and do this:
```python
from django.contrib.auth import get_user_model
from core.models import StudentProfile, TeacherProfile

User = get_user_model()

# Let's make a student
student = User.objects.create_user(username='student1', password='password123', user_type='student')
StudentProfile.objects.create(user=student)

# And a teacher
teacher = User.objects.create_user(username='teacher1', password='password123', user_type='teacher')
TeacherProfile.objects.create(user=teacher, expertise='Computer Science')
```

---

## 🧪 Testing

I wrote some automated tests to make sure things don't break. You can run them with:
```bash
python manage.py test
```
*(Just a heads up: make sure your local Redis server is running first, or the real-time tests might yell at you!)*

---

## 📂 Project Layout

If you're digging into the code, here's where everything lives:
- `core/`: This is where the magic happens. Models, views, forms, and the WebSocket consumers.
- `elearning_platform/`: The main configuration hub (settings, urls, and ASGI setup).
- `templates/` & `static/`: All the frontend HTML, CSS (Tailwind), and JavaScript.
- `media/`: Where user uploads get saved locally.

---

## 🤝 A Quick Note

I built this primarily as a learning project to push my skills with Django, WebSockets, and building REST APIs. The code is structured to be friendly and heavily commented so it's easy to follow. 

Feel free to explore the code, use it, or learn from it. (MIT License)

Thanks for checking it out! 😊
