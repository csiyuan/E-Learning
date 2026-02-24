from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# using DefaultRouter to automatically create URLs for our viewsets
# this is way easier than writing all the URL patterns manually
router = DefaultRouter()

# register our viewsets with the router
# the first argument is the URL prefix
router.register(r'courses', api_views.CourseViewSet)
router.register(r'enrollments', api_views.EnrollmentViewSet)
router.register(r'materials', api_views.CourseMaterialViewSet)
router.register(r'chat', api_views.ChatMessageViewSet)
router.register(r'status-updates', api_views.StatusUpdateViewSet)
router.register(r'feedback', api_views.CourseFeedbackViewSet)
router.register(r'notifications', api_views.NotificationViewSet, basename='notification')
router.register(r'users', api_views.CustomUserViewSet)
router.register(r'deadlines', api_views.DeadlineViewSet)
router.register(r'submissions', api_views.SubmissionViewSet)


# this creates URLs like:
# /api/courses/
# /api/courses/{id}/
# /api/enrollments/
# /api/materials/
# /api/chat/?room=general

urlpatterns = [
    path('', include(router.urls)),
]
