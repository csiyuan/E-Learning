# views package - split up the monolithic views.py so it's easier to work with
# each module handles a different area of the app

from .auth import register_view, login_view, logout_view, home_view
from .student import (
    student_dashboard, course_browse, enroll_course, 
    course_detail_student, submit_assignment, submit_feedback,
    feedback_list, course_feedback
)
from .teacher import (
    teacher_dashboard, create_course, upload_material, 
    course_detail, view_submissions, remove_student_from_course,
    unified_dashboard_action
)
from .common import (
    post_status, chat_room, chat_history_api, profile_view,
    search_users, api_search_users
)
