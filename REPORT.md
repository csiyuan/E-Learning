# EduStream – eLearning Platform: Design and Implementation Report

## 1. Introduction

This report covers the design, development, and evaluation of EduStream, a web-based eLearning platform I built using Django. The idea was to create something that works a bit like Moodle or Blackboard, but with a cleaner, more modern interface. Students and teachers each have their own dashboards and can interact through course materials, deadlines, a live chat system, and push notifications. The platform also includes a full REST API with interactive documentation.

I'll be honest — when I first read through the requirements, it seemed doable enough. User accounts, two roles, some CRUD stuff, nothing too crazy. But once I actually sat down and started coding, things got complicated fast. The WebSocket part in particular gave me a lot of trouble. I didn't realise how different async Python is from normal Django, and I spent way more time than I expected just trying to get the chat to work properly. The frontend also took longer than I thought it would — I wanted it to actually look good, not just work.

I built the whole thing on macOS using Python 3.12.4 and Django 6.0. The reason I picked Django was basically because it gives you so much for free — you get the ORM, templates, auth system, admin panel, all of that without having to install a bunch of separate things. For the chat and notification features I needed WebSockets, so I added Django Channels and the Daphne ASGI server (more on that later, it was a pain to set up). The REST API uses Django REST Framework with drf-spectacular for the Swagger docs. Frontend-wise I went with TailwindCSS and Alpine.js because I didn't want to deal with a full JavaScript framework like React.

## 2. Development Environment and Setup

### 2.1 System Information

- **OS:** macOS 26.0.1 (Build 25A362)
- **Python:** 3.12.4
- **Database:** SQLite for development (would use PostgreSQL in production)

### 2.2 Key Packages

| Package               | Version  | What it does                              |
|-----------------------|----------|-------------------------------------------|
| Django                | 6.0      | The main web framework                    |
| channels              | 4.3.2    | WebSocket support through ASGI            |
| daphne                | 4.2.1    | ASGI server that actually serves the WebSockets |
| djangorestframework   | 3.16.1   | Building the REST API                     |
| drf-spectacular       | 0.29.0   | Auto-generated Swagger docs               |
| Pillow                | 12.1.1   | Handling image uploads (profile pics)     |
| django-filter         | 25.2     | Filtering querysets in the API            |
| TailwindCSS           | 4.1.18   | CSS framework (loaded via CDN)            |

### 2.3 Running the Application

1. Clone the repo and go into the project folder.
2. Set up a virtual environment and install everything:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install django channels daphne djangorestframework drf-spectacular Pillow django-filter
   ```
3. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
4. Seed the database with demo data:
   ```bash
   python manage.py seed_data
   ```
5. Start the server with WebSocket support:
   ```bash
   daphne -b 127.0.0.1 -p 8000 elearning_platform.asgi:application
   ```
   Or without WebSockets (just for quick testing):
   ```bash
   python manage.py runserver
   ```

### 2.4 Admin Panel

You can access Django's built-in admin at `/admin/` by creating a superuser:
```bash
python manage.py createsuperuser
```

### 2.5 Demo Accounts

After seeding, these accounts are ready to use:

| Role    | Username     | Password     |
|---------|-------------|-------------|
| Teacher | prof_davis  | password123  |
| Student | emma1       | password123  |

### 2.6 Live Deployment

The application is also deployed on Railway and can be accessed at:

**Live URL:** [https://web-production-c78d.up.railway.app](https://web-production-c78d.up.railway.app)

You can log in using the demo accounts listed above (prof_davis / password123 for teacher, emma1 / password123 for student). The deployed version uses the same SQLite database seeded with demo data, so all features including the chat, notifications, course management, and API documentation are fully functional online.

### 2.7 Running Tests

```bash
python manage.py test
```

This runs all 45 tests — model tests, view tests, API tests, WebSocket tests, and permission edge cases.

## 3. Architecture and Design Choices

### 3.1 Project Layout

I kept everything in one `core` app instead of splitting it up into multiple apps. I know you're supposed to separate things out in Django — like have a separate app for users, one for courses, one for chat, that kind of thing. But I actually tried doing that at the start and it was a mess. I kept getting circular import errors where one app needed something from another app, and then that app needed something from the first one. Eventually I just threw it all into one app and honestly it's been fine. For a project this size it's way easier to just have everything in one place where you can find it.

That said, I did split up `views.py` into a package because it was getting really long (it was over 1200 lines at one point and I kept losing track of which function was where). So now it's organised into `views/auth.py`, `views/student.py`, `views/teacher.py`, and `views/common.py`, with an `__init__.py` that re-exports everything so the URL config didn't need to change at all. It's way easier to navigate now.

```
elearning_platform/
├── core/
│   ├── models.py             # 11 models
│   ├── views/                # view functions, split by area
│   │   ├── __init__.py       # re-exports all views
│   │   ├── auth.py           # register, login, logout
│   │   ├── student.py        # student dashboard, enrollment, submissions
│   │   ├── teacher.py        # teacher dashboard, uploads, student mgmt
│   │   └── common.py         # chat, profiles, search, status updates
│   ├── forms.py              # Django forms
│   ├── consumers.py          # WebSocket consumers
│   ├── signals.py            # post_save signal handlers
│   ├── serializers.py        # DRF serializers
│   ├── api_views.py          # DRF ViewSets
│   ├── api_urls.py           # API URL config
│   ├── templates/core/       # all HTML templates
│   ├── static/core/          # CSS, JS, images
│   └── management/commands/  # custom management commands
├── elearning_platform/
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py               # ASGI config for WebSockets
└── media/                    # user uploads go here
```

### 3.2 Database Models (R2)

For the user model, I extended Django's `AbstractUser` and added a `user_type` field that's either 'student' or 'teacher'. I did think about making two completely separate models for students and teachers, but then I realised that would completely mess up Django's built-in auth — like, the login system expects one user model, not two. So having one model with a type field was the much simpler option and it meant I could still use things like `@login_required` without any issues.

There are 11 models in total. **CustomUser** is the base — it has `user_type`, `bio`, and `profile_pic`. Then there's **StudentProfile** and **TeacherProfile**, both linked via OneToOne. The student one holds things like `student_id`, `gpa`, and `enrollment_date`, while the teacher version stores `title`, `department`, and `years_experience`.

The **Course** model is pretty central to everything. It has the usual fields (title, description) plus an FK to TeacherProfile for the instructor, and an auto-generated `course_code` which I'll talk about more later because that was a whole thing on its own.

For **Enrollment**, I specifically chose not to use Django's built-in ManyToManyField because I needed extra data on the relationship — stuff like `enrolled_at`, `is_active`, and `completion_status` (which can be 'ongoing', 'completed', 'dropped', or 'blocked'). Making it an explicit model gave me full control over that.

The rest of the models are more straightforward: **CourseMaterial** for uploaded files with metadata like `file_type` and size, **Deadline** for assignment due dates (it has a cool `time_remaining` property that computes automatically), **Submission** for student uploads against deadlines, and **CourseFeedback** for ratings and comments with an anonymous toggle. I also have **StatusUpdate** for short text posts (kind of like a mini Twitter thing), **ChatMessage** for the real-time chat messages grouped by room, and **Notification** for in-app alerts.

One thing that took me ages was the auto-incrementing course codes. I wanted courses to automatically get codes like CS101, CS102, CS103. My first attempt was just hardcoding them but that obviously doesn't scale. I ended up looking up how to parse strings with regex in Python and wrote a parser in the `Course.save()` method. It goes through all existing codes, pulls out the number part with `re.match(r'([A-Z]+)(\d+)', code)`, finds the biggest number, and adds one. It's probably not the most elegant solution but it works and I haven't had any issues with it.

### 3.3 Views and Routing

I used function-based views for all the actual pages and class-based ViewSets for the API. I know some people prefer class-based views and they're supposedly the "proper" way to do things in Django, but I personally find them really confusing. Like, with function-based views you can just read the code top to bottom and understand what's happening. The student dashboard view for example has to pull stuff from like five different models, work out material distributions, combine different types of data into one feed — trying to figure out which method to override in a class-based view for all that would've driven me crazy. I did eventually split up the views file into separate modules though (auth, student, teacher, common) because scrolling through 1200 lines every time I needed to change something was getting painful.

The URL structure:
- `/login/`, `/register/`, `/logout/` — auth stuff
- `/student/dashboard/` — student's main page
- `/teacher/dashboard/` — the Faculty Hub
- `/courses/` — browse all courses
- `/student/course/<id>/` and `/teacher/course/<id>/` — course detail pages
- `/chat/` — the real-time chat
- `/feedback/` — course reviews page
- `/profile/<username>/` — user profiles
- `/search/` — search for users
- `/api/` — REST API root
- `/api/docs/` — Swagger UI

### 3.4 Authentication (R1a, R1b)

Registration works for both students and teachers through the same form — you just pick your account type from a dropdown. When you register as a student it automatically creates a `StudentProfile` for you, and same thing for teachers. I stuck `@login_required` on pretty much every view that should be protected, and then inside the view I check `request.user.user_type` to make sure students can't get into teacher pages. It's not the most sophisticated permission system but it does the job.

For the API I used DRF's permission classes which are a bit more proper. GET requests are mostly open so you can browse courses without being logged in, but anything that changes data needs you to be authenticated. I also added a check in the `CourseViewSet` so that only teachers can create courses — I forgot to add this initially and realised during testing that any logged-in user could create courses, which obviously shouldn't happen.

## 4. How the Requirements are Met

### 4.1 R1: Core Features

Starting with **secure accounts (a)** — Django handles password hashing with PBKDF2 + SHA256 out of the box, so passwords are never stored in plaintext. Users log in through a form at `/login/`. I didn't have to do much here since Django's auth system covers most of it, which was nice.

For **two user types (b)**, the `user_type` field on CustomUser splits everyone into students and teachers. Each type gets their own dashboard and course detail page with different capabilities. This is probably the most fundamental design decision in the whole project because nearly every view checks this field to decide what to show.

**User search (c)** was fairly simple to implement. There's a search bar on the teacher dashboard and a separate `/search/` page. I used Django's `Q` objects to query across username, first name, last name, and email all at once — before I discovered `Q` objects I was doing four separate queries which was really slow and ugly.

Every user gets a **profile page (d)** at `/profile/<username>/` that shows their bio, courses, and status updates. The dashboards double as the main "home page" for each role. **Status updates (e)** are short text posts capped at 500 characters that appear in the activity feed for people in the same courses.

The **course feedback system (f)** lets enrolled students rate courses 1-5 stars and leave written comments. I added an anonymous mode after one of my friends said they'd never leave honest feedback if their name was attached to it — seemed like a realistic concern. The serializer strips out the student name by checking `is_anonymous` in `to_representation()`. **Course creation and materials (g)** is handled from the teacher dashboard — they can upload PDFs, images, documents, whatever really. The system figures out the file type and tracks the size automatically, and materials render with appropriate icons on the course page.

Lastly, **enrollment and student lists (h)** — students browse the course catalogue and click "Enroll Now". There's a capacity check before it goes through. On the teacher side, they get a filterable list of enrolled students with options to block or remove people.

### 4.2 R3: Validation and Security

Security was something I tried to keep in mind throughout, although I'll admit I probably could have done more in some areas.

**CSRF protection** — Django's `CsrfViewMiddleware` is active by default, and every form includes `{% csrf_token %}`. This stops cross-site request forgery attacks.

**File upload limits** — There's a 2MB cap on uploaded files, enforced in the model's `save()` method. If someone tries to upload something bigger, it raises a `ValidationError`. The `CourseMaterial` model also tracks the file extension, pulling it from the filename automatically. I'll admit I didn't implement a file type whitelist (so technically someone could upload a .exe), but in a real production app that would definitely need addressing.

**Database-level constraints** — `Enrollment` has `unique_together = ('student', 'course')`, so duplicate enrollments are literally impossible even if you bypass the frontend. Same thing with `CourseFeedback` — one review per student per course.

**Password requirements** — I'm using Django's built-in validators: minimum 8 characters, can't be too similar to your username, can't be on the common passwords list, can't be all numbers.

**Role-based access** — Every protected view checks `request.user.user_type` before doing anything. If a student tries to hit a teacher URL, they get an error message and a redirect.

**API security** — The `StatusUpdateSerializer` overrides `create()` to force-set the user from `request.user`, so you can't impersonate someone else through the API.

### 4.3 R4: REST API

The API is built with DRF and covers all the main resources. The router in `api_urls.py` registers ViewSets for courses, enrollments, materials, students, teachers, chat messages, status updates, feedback, notifications, deadlines, and submissions.

Some key endpoints:
- `GET /api/courses/` — list all courses (public)
- `POST /api/courses/` — create a course (teacher-only)
- `GET /api/courses/{id}/students/` — see who's enrolled
- `POST /api/enrollments/` — enroll in a course
- `POST /api/materials/` — upload material
- `GET /api/chat/?room=<name>` — get messages for a chat room
- `GET /api/users/me/` — get the current user's info (custom action)

The API also has pagination built in — I set it to 20 results per page using DRF's `PageNumberPagination`. I added this after I realised that if a teacher had like 200 students, the enrollments endpoint would just dump everything in one massive response, which obviously isn't ideal. The whole API is documented automatically through drf-spectacular. You can go to `/api/docs/` and get a full Swagger UI where you can try out every endpoint. I configured this in `settings.py` under `SPECTACULAR_SETTINGS`.

### 4.4 R1g, R1k, R1l: WebSocket / Real-time Features

This was by far the hardest part of the whole project and the part I spent the most time on. Honestly, I almost gave up on it at one point and nearly just used AJAX polling instead of proper WebSockets. The problem was that Django Channels works completely differently from normal Django — you need to set up ASGI instead of WSGI, you need to understand async/await, and the errors you get when something goes wrong are not very helpful.

The `asgi.py` file uses `ProtocolTypeRouter` to route HTTP requests normally and WebSocket connections through a separate URL router. There are two consumers:

**ChatConsumer** — When a user opens the chat page, a WebSocket connection is established to `/ws/chat/{room_name}/`. The consumer's `connect()` method extracts the room name from the URL, adds the user to a Channels group for that room, and accepts the connection. When a message arrives via `receive()`, it's parsed from JSON, saved to the database through `@database_sync_to_async` (you have to wrap all ORM operations in this decorator because Django's database layer is synchronous and you'll get errors if you call it from async code), and then broadcast to everyone in the group via `group_send()`. The `chat_message()` method handles the group event and sends the formatted message back out through each user's WebSocket. Each chat room corresponds to a course, so students and their teacher can discuss things in the context of that specific module.

One thing that tripped me up early on was understanding the flow of data through the consumer. When you call `group_send()`, it doesn't directly call `send()` on every connected WebSocket. Instead, it dispatches an event with a `type` field (like `chat_message`), and Channels calls the method on each consumer whose name matches that type. So if your `type` is `chat.message`, it looks for a method called `chat_message`. I had this wrong initially and messages were being silently dropped.

**NotificationConsumer** — This one lives at `/ws/notifications/`. Each logged-in user gets their own personal notification channel (`notifications_{username}`). The `connect()` method first checks if the user is authenticated — if they're anonymous, it closes the connection immediately. When events happen elsewhere in the app (new enrollment, material upload, new deadline), Django signals fire and push notifications through the channel layer to the appropriate user's group.

The signal handlers in `signals.py` listen for `post_save` on `Enrollment`, `CourseMaterial`, `StatusUpdate`, and `Deadline`. For each, the handler checks that the event is a creation (not an update), builds the notification message, creates a `Notification` database record, and dispatches a WebSocket message through the channel layer using `async_to_sync(channel_layer.group_send)()`. I also added a `_silent` attribute that the seed data command sets on objects to prevent triggering hundreds of notifications during database population.

I had a really frustrating bug at one point where notifications weren't being sent for new materials. After about three hours of debugging, I figured out I had a `return` statement in the wrong place inside an `if not created:` guard clause. The function was bailing out before it even reached the WebSocket dispatch code. The annoying thing about signal handler bugs is that they never throw visible errors — they just silently do nothing, and you're left wondering why the feature doesn't work.

### 4.5 R5: Unit Tests

45 tests in total, organised into test classes by feature:

- **UserRegistrationTests** — registration, profile creation, duplicate prevention
- **CourseManagementTests** — course creation, student restriction
- **EnrollmentTests** — enrolling, duplicate checks, max capacity
- **MaterialUploadTests** — file upload, size validation
- **FeedbackTests** — creating feedback, one-per-student enforcement
- **StatusUpdateTests** — posting updates, character limit
- **SearchTests** — partial matching across fields
- **ChatModelTests** — message creation
- **DashboardAccessTests** — cross-role access prevention
- **NotificationTests** — auto-notification on enrollment
- **StudentManagementTests** — blocking students
- **APIEndpointTests** — full API CRUD testing
- **WebSocketTests** — chat connection, message exchange, auth rejection
- **ModelRobustnessTests** — edge cases (missing files, etc.)
- **ViewAccessControlTests** — making sure teachers can't load student pages and vice versa, and that unauthenticated users get redirected to login
- **FormValidationTests** — duplicate email rejection, empty/too-long status posts
- **APIPermissionEdgeCaseTests** — unauthenticated users can't create resources, pagination format verification
- **DuplicateEnrollmentTests** — can't enroll in the same course twice through the view

All 45 pass. I won't pretend I ran them after every single change like you're supposed to, but I did run them fairly regularly and they caught a couple of bugs that I would have missed otherwise. The access control tests in particular were useful — I wrote them after realising I hadn't actually verified that a student couldn't just type in the teacher dashboard URL and get in. Turns out the checks were already in place, but it's good to know for sure.

## 5. Extra Features (Beyond Requirements)

This is where a lot of the development time went. I wanted the platform to feel like something you'd actually want to use, not just a checkbox exercise.

### 5.1 Auto-Incrementing Course Codes

Every new course automatically gets a code like CS101, CS102, etc. The `Course.save()` method parses all existing codes with regex, finds the highest number, and increments it. I handled the edge case where the database is empty (it defaults to 101), and the code is unique at the database level.

### 5.2 Unified Activity Feed

The student dashboard doesn't just show status updates — it pulls together status updates, new course materials, and recently created deadlines into one chronological feed. This was surprisingly tricky because you're merging three different querysets with completely different model types. I spent a while trying to figure out how to combine them, and after some googling I found that Python's `itertools.chain` was the easiest way to merge different lists together. I also had to add a common `type` and `date` attribute to each item so I could sort them all chronologically — I used `sorted()` with a key function to get them in the right order. The feed only shows activity from the last 7 days and from courses the student is actually enrolled in.

### 5.3 Resource Spectrum (Material Distribution Chart)

On the student dashboard there's a colour-coded bar that shows the breakdown of material types across your courses — documents, media files, slides, archives, and active submissions. It updates dynamically when you click on different course modules thanks to Alpine.js managing the state client-side. I had to categorise each file by its extension in the view and compute percentages for each category, which was fiddly but looks really nice in the final product.

### 5.4 Deadline Countdown Timer

Both dashboards show upcoming deadlines with a human-readable countdown like "4 days, 23 hours left." This is computed by a `time_remaining` property on the `Deadline` model that does the maths based on the current time. Students can click on a deadline to go straight to the submission page.

### 5.5 Dark Mode Bento Grid UI

I probably spent too long on this part if I'm being honest. The app uses a dark colour scheme because I think light mode looks kind of dated, and I used a "bento grid" layout which is basically just cards of different sizes arranged in a grid. I added some little animations here and there — like pulsing dots to show someone's online, cards that slightly grow when you hover over them, that sort of thing. Most of it is done through TailwindCSS which made it pretty quick to style things. I just didn't want it to look like every other Bootstrap site out there.

### 5.6 Student Management (Block/Remove)

Teachers can hover over a student's name in their dashboard to reveal action buttons. They can block a student (which sets `completion_status` to 'blocked' and prevents access to course content) or remove them entirely. Blocked students keep their enrollment record for admin purposes. There's also an unblock button for blocked students.

### 5.7 Full Assignment Submission System

I didn't just stop at creating deadlines — there's a complete submission workflow. Students can upload files and add comments for each deadline. Teachers can navigate to a dedicated submissions page for any deadline and see every student's submission with download links. This felt important because having deadlines without a way to actually submit work would be a bit pointless.

### 5.8 Chat Resource Sidebar

The chat page includes a sidebar showing course materials for whatever course you're currently chatting in. The idea is that if you're discussing a lecture slides with classmates, you can pull up the actual file without leaving the chat. The sidebar updates when you switch between course channels.

### 5.9 Seed Data Management Command

I wrote a custom `python manage.py seed_data` command that sets up the entire database with realistic demo data — a teacher account, a student account, two courses, materials, deadlines, enrollments, feedback, and chat messages. This was mainly so that anyone marking the project can see it working immediately without having to manually create everything. The command also cleans up existing data first to avoid duplicates.

### 5.10 Deduplication in Teacher Dashboard

When a teacher has students enrolled across multiple courses, the "Active Students" panel on the dashboard only shows each student once when "All Courses" is selected. But when you filter by a specific course, it correctly shows that course's enrolled students. This required careful queryset handling in the view — I iterate through enrollments and track which student IDs I've already seen, only adding an enrollment to the display list if the student is new.

### 5.11 Anonymous Feedback System

Students can choose to submit feedback anonymously. When they tick the anonymous box, the `CourseFeedbackSerializer` strips out the student name and replaces it with "Anonymous Student" in the API response. The database still stores who left the feedback (for moderation purposes), but the frontend and API never reveal it.

### 5.12 Course Capacity Management

Each course has a `max_students` field, and the system checks this before allowing enrollment. The `Course.is_full` property computes whether the cap has been reached, and views use this to either allow or deny enrollment requests. This prevents overcrowding without the teacher having to manually monitor numbers.

### 5.13 Auto-Generated User Avatars

Rather than using generic placeholder icons, the platform generates personalised avatars for every user using the UI Avatars API. Each avatar displays the user's initials against a dark background, and the border colour changes based on context — green for active students, red for blocked ones. It's a small touch but it makes the active students list and chat messages look way more polished than just having a blank circle or a default silhouette.

### 5.14 Swagger API Documentation

The API docs at `/api/docs/` are automatically generated from the serializers and ViewSets. You can browse every endpoint, see the expected request/response formats, and even try out API calls directly from the browser. This was pretty easy to set up with drf-spectacular but it adds a lot of professional polish.

### 5.15 Mobile Responsiveness Polish

A significant amount of effort was put into ensuring the app feels native on mobile devices. The main navigation features a clean, hidden-on-desktop slide-out sidebar where the platform logo and navigation links live, triggered by a universally accessible hamburger menu pinned to the top left of the screen. I also made sure that scrollable components within the modern Bento grid—like the Student Dashboard Activity Feed—have precise padding offsets so that content isn't clipped by bottom navigation bars on smartphones.

## 6. Use of Taught Techniques

### 6.1 Django Fundamentals

The project follows Django conventions for the most part — models use the right field types, views have `@login_required` where needed, forms handle validation, templates extend from `base.html`. I set up the custom user model in `settings.py` with `AUTH_USER_MODEL` which I initially forgot to do and got a really confusing error about user models not matching. The admin panel has custom `ModelAdmin` classes so you can actually see useful information in there.

### 6.2 REST Framework

I used the main DRF features — `ModelSerializer` to turn models into JSON, `ModelViewSet` for the standard CRUD endpoints, and `@action` for custom routes that don't fit the normal pattern. The serializers also do some slightly fancier things like showing nested data. Like, instead of just showing an instructor ID on a course, the `CourseSerializer` uses `source='instructor.user.get_full_name'` to show the actual teacher name. It took me a while to figure out the `source` parameter but once I got it working it was really useful.

### 6.3 Channels and Async

The WebSocket implementation uses `AsyncWebsocketConsumer` for both the chat and notification consumers. All database operations inside the consumers are wrapped in `@database_sync_to_async` because Django's ORM is synchronous. The routing in `routing.py` maps WebSocket URLs to consumers, and `asgi.py` uses `ProtocolTypeRouter` to handle both HTTP and WebSocket protocols.

### 6.4 Signals

I used Django's `post_save` signals to automatically create notifications when things happen — like when someone enrolls or a teacher uploads new materials. The main reason for using signals was so I didn't have to put notification code in every single view function, which would have been really messy and easy to forget. I also had to add a `_silent` flag that the seed data command uses, because otherwise seeding the database would fire off like a hundred notifications and it was really annoying during testing.

## 7. Critical Evaluation

### 7.1 What Went Well

Django was genuinely a good choice for this project. The ORM alone saved me so much time — I could define my models and immediately query them without touching SQL. The auth system, the template engine, the admin panel, it all just works out of the box. I honestly think if I'd used Flask or something more lightweight I'd still be building the login system right now. The template engine can be a bit verbose sometimes (especially when you're nesting loops and conditionals), but it handled everything I threw at it.

The REST API came together way faster than I expected. I struggled a lot with the first ViewSet — kept getting confused about which methods to override and what `get_queryset` was supposed to return. But after that first one clicked, I was genuinely knocking them out in about 10 minutes each. Copy the pattern, change the model and serializer, tweak the permissions, done. And drf-spectacular generating the Swagger docs automatically was just the cherry on top.

WebSockets were a different story. Setting them up was painful (covered that earlier), but the end result is actually really reliable. You can open chat in two tabs and messages appear instantly in both, which felt pretty satisfying after all the debugging. The notification system pushing real-time alerts is the kind of thing that doesn't look like much visually, but technically it's probably the most complex part of the whole project.

I'll also say the dark mode bento UI turned out way better than I thought it would. TailwindCSS made iterating on the design really fast, and the little animations — hover effects, pulsing online indicators, cards that grow slightly when you mouse over them — give it that polished feel. I know it's not really a "technical" achievement, but I think presentation matters and I didn't want this to look like yet another generic Bootstrap project.

### 7.2 What Could Be Better

The biggest limitation is probably the **channel layer**. Right now I'm using the in-memory one, which works fine when it's just one server process, but it falls apart completely if you try to scale horizontally. You'd need Redis backing the channel layer for anything production-grade. I decided against adding Redis because it's an extra dependency to install and configure, and for a demo project it felt like overkill. But I know it's the first thing that would need changing in a real deployment.

On the frontend side, I think Django templates and Alpine.js were fine for this project's scope, but I can already see the cracks. My student dashboard template is over 325 lines of HTML and it's getting hard to work with. If the app grew any further, moving to React or Vue with a proper component system would make a huge difference. I used `{% include %}` to break out some bits like the sidebar and the activity feed, but I probably should have been more aggressive about splitting things up from the start.

File storage is another area — everything just goes to the `media/` folder on disk. That's fine locally, but in production you'd lose all uploads if the server gets redeployed. Something like AWS S3 through `django-storages` would fix that, but I didn't want to add cloud dependencies for what's essentially a coursework submission.

The search could also be a lot smarter. Right now it's just `icontains` lookups, so literally just substring matching. No typo handling, no relevance ranking, nothing fancy. PostgreSQL has `SearchVector` for full-text search which would be a massive step up. And my test suite, while all 45 tests pass, could definitely go deeper — I'm not testing WebSocket edge cases like dropped connections, or whether a student can mess with another student's submission through the API. Integration tests covering full user flows would be valuable too, but I honestly ran out of time.

### 7.3 Things I'd Do Differently

1. I'd try class-based views for the simpler pages (course list, profile view) and keep function-based views only for the complex ones.
2. I'd split the notification system into its own Django app — the signals and WebSocket consumer are conceptually separate from course management.
3. I'd use environment variables for the secret key and other sensitive settings instead of hardcoding them.
4. I'd implement more granular form validation with better error messages — especially for registration.

## 8. Conclusion

Looking back, I'm pretty happy with where the project ended up. It covers everything in the specification, and I think the extra features — the auto-incrementing course codes, the unified activity feed, the resource spectrum chart, the submission system, chat with its resource sidebar, the deduplication stuff on the teacher dashboard — push it beyond a basic checkbox exercise into something that actually feels like a usable platform. What I'm most pleased about is that most of the extras aren't just visual fluff. The submission workflow, deadline countdowns, and anonymous feedback mode all add real functionality.

The biggest learning experience was definitely Django Channels. Before this project I had never touched WebSockets, and honestly the whole async/sync split in Django confused me for a solid week. Like, I couldn't understand why I needed `database_sync_to_async` — it just seemed like unnecessary wrapping. But once I actually understood that the ORM is fundamentally synchronous and the consumer is running in an async event loop, it all clicked. Being able to have normal request-response views for 90% of the app and then layer real-time stuff on top is genuinely really cool.

I also learned a lot from debugging the signal handlers. There's something uniquely frustrating about code that fails silently — no error, no traceback, it just doesn't do anything. I ended up littering the signal handlers with print statements at every branch point to trace the execution. Definitely not sophisticated debugging, but it got the job done when nothing else was working.

Building the API with DRF was probably the most enjoyable part. Once you get one ViewSet working properly, the rest just flow naturally from the same pattern. The auto-generated Swagger docs were a nice bonus too — meant I always had a live reference for every endpoint without maintaining separate documentation.

Overall, there are things I'd change if I had more time. The frontend templates are getting unwieldy and would benefit from a component framework, and the deployment setup needs real work. But as a project that demonstrates full-stack Django development — models, views, REST APIs, WebSockets, real-time notifications, and a polished UI — I think it shows that I've understood and applied the concepts from this module pretty well.

## 9. References

1. Django Software Foundation. (2024). *Django Documentation*. Available at: https://docs.djangoproject.com/en/6.0/
2. Django REST Framework. (2024). *Django REST Framework Documentation*. Available at: https://www.django-rest-framework.org/
3. Django Channels. (2024). *Channels Documentation*. Available at: https://channels.readthedocs.io/en/latest/
4. drf-spectacular. (2024). *Sane and flexible OpenAPI 3 schema generation for Django REST framework*. Available at: https://drf-spectacular.readthedocs.io/
5. TailwindCSS. (2024). *Tailwind CSS Documentation*. Available at: https://tailwindcss.com/docs
6. Alpine.js. (2024). *Alpine.js Documentation*. Available at: https://alpinejs.dev/
7. Daphne. (2024). *HTTP, HTTP2 and WebSocket protocol server for ASGI*. Available at: https://github.com/django/daphne
8. Pillow. (2024). *Python Imaging Library (Fork)*. Available at: https://pillow.readthedocs.io/
