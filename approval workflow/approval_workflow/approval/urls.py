from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('workflow/', views.workflow, name='workflow'),
    path('document/', views.document, name='document'),
    path("edit_email_template/", views.edit_email_template, name="edit_email_template"),

    path('approval_list/', views.approval_list, name='approval_list'),  # Keep this one
    path('approval_details/', views.approval_details, name='approval_details'),
    path('request_history/', views.request_history, name='request_history'),
    
    # Approval Details API
    path("upload_signature/", views.upload_signature, name="upload_signature"),
    path("clear_signature/", views.clear_signature, name="clear_signature"),
    path("check_signature/", views.check_signature, name="check_signature"),
    path("download_history/pdf/<str:history_type>/", views.download_history_pdf, name="download_history_pdf"),
    path("download_history/excel/<str:history_type>/", views.download_history_excel, name="download_history_excel"),
    path("generate_approval_pdf/<int:doc_id>/", views.generate_approval_pdf, name="generate_approval_pdf"),
    path("get_request_details_all/<int:doc_id>/", views.get_request_details_all, name="get_request_details_all"),
    path("get_request_details_user/<int:doc_id>/", views.get_request_details_user, name="get_request_details_user"),
    # path("get_request_details/<int:doc_id>/", views.get_request_details, name="get_request_details"),
    path('get_approval_details/<int:approval_id>/', views.get_approval_details, name="get_approval_details"),
    path("submit_approval/", views.submit_approval, name="submit_approval"),

    # Authentication
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),  # Fixed the root URL issue

    # Optional: Alias for approval list
    path("pending-approvals/", views.approval_list, name="pending_approvals"),
    # path("edit_request/<int:doc_id>/", views.edit_request, name="edit_request"),
    path("submit_query/", views.submit_query, name="submit_query"),
    path("submit_edited_request/", views.submit_edited_request, name="submit_edited_request"),# ✅ Add this URL
    path("get_query_details/<int:approval_id>/", views.get_query_details, name="get_query_details"),
    path("testing/", views.testing, name="testing")   # Different name
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)