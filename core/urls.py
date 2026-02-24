from django.urls import path
from . import views

# URL patterns for the core app
# I'm naming each URL so I can use {% url 'name' %} in templates
urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard URLs
    path('', views.home_view, name='home'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    
    # Student feature URLs
    path('courses/', views.course_browse, name='course_browse'),
    path('courses/enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('courses/<int:course_id>/', views.course_detail_student, name='course_detail_student'),
    path('courses/<int:course_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('status/post/', views.post_status, name='post_status'),
    
    # Teacher feature URLs
    path('teacher/course/create/', views.create_course, name='create_course'),
    path('teacher/course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('teacher/course/<int:course_id>/upload/', views.upload_material, name='upload_material'),
    path('teacher/dashboard/action/', views.unified_dashboard_action, name='unified_dashboard_action'),
    
    # Feedback URLs
    path('feedback/', views.feedback_list, name='feedback_list'),
    path('feedback/<int:course_id>/', views.course_feedback, name='course_feedback'),

    # Chat URL
    path('chat/<str:room_name>/', views.chat_room, name='chat_room'),
    path('api/chat/<str:room_name>/history/', views.chat_history_api, name='chat_history_api'),
    path('api/search/users/', views.api_search_users, name='api_search_users'),
    
    # Management & Profile URLs
    path('course/<int:course_id>/remove-student/<int:student_id>/', views.remove_student_from_course, name='remove_student'),
    path('search/', views.search_users, name='search_users'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('deadline/<int:deadline_id>/submit/', views.submit_assignment, name='submit_assignment'),
    path('deadline/<int:deadline_id>/submissions/', views.view_submissions, name='view_submissions'),
]
