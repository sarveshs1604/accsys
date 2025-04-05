# from django.urls import path
# from . import views
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns=[
#     path('index/',views.index,name="index")
# ]

from django.urls import path
from . import views
urlpatterns = [
    # path('', views.index,name="index"),
    path('login2/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),  # Fixed the root URL issue
    path('booking/', views.booking, name="booking"),
    path('submit_form/', views.submit_form, name="submit_form"),
    path('forms/', views.form_list, name="form_list"),
    path('forms/<int:form_id>/', views.form_detail, name="form_detail"),
    path("update__form/<int:form_id>/", views.update_form, name="update_form"),
    path("add-reference/<int:form_id>/", views.add_reference, name="add_reference"),
    path('add-query/<int:form_id>/', views.add_query, name='add_query'),
    path('resolve_query/<int:form_id>/', views.resolve_query, name='resolve_query'),
    path('masters/', views.masters, name="masters"),
    path('save_mapping/', views.save_mapping, name="save_mapping"),
    path('save_document_type/', views.save_document_type, name="save_document_type"),
    path("get_assignees/", views.get_assignees, name="get_assignees"),
    path('delete_document_type/<int:dt_id>/', views.delete_document_type, name="delete_document_type"),
    path('validate_form/<int:form_id>/', views.validate_form, name="validate_form"),
    path('close_document/<int:form_id>/', views.close_document, name='close_document'),
    path('assign_validator_both/<int:form_id>/', views.assign_validator_both, name='assign_validator_both'),
    path('client_validate_both/<int:form_id>/', views.client_validate_both, name='client_validate_both'),
    path('close_document_both/<int:form_id>/', views.close_document_both, name='close_document_both'),
    path('client_validate_form/<int:form_id>/', views.client_validate_form, name='client_validate_form'),

]
