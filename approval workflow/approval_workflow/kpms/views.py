from django.shortcuts import render
from django.contrib.auth import login as auth_login, authenticate ,logout as auth_logout # Import login and rename it to auth_login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Max
from django.contrib.auth import login as auth_login, authenticate ,logout as auth_logout # Import login and rename it to auth_login
from django.http import JsonResponse,HttpResponse
from django.db import transaction 
from django.conf import settings
from django.utils.timezone import localtime
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.db.models import Count, Q  # Import Q for filtering
from .models import  User , BookingForm ,UpdateLog,Document, QueryLog, DocumentType ,QueryDocument
# Create your views here.
def index(request):
    return render(request,"index.html")

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.contrib import messages
from .models import  User , BookingForm

@login_required
def booking(req):
    return render(req,"booking.html")

def user_login(request):
    print("user_login")
    # Check if the user is already authenticated
    if request.user.is_authenticated:
        return redirect('booking')  

    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        try:
            # Check if a user with the entered email exists
            user = User.objects.get(email=email)
            if hasattr(user, "userprofile") and user.userprofile.is_deleted:
                print("No Active Account. Contact Admin")
                return JsonResponse({'status': 'error', 'message': 'No Active Account. Contact Admin'})

                # return redirect("login")  # Redirect back to login page

        except User.DoesNotExist:
            # Return an error response if email does not exist
            return JsonResponse({'status': 'error', 'message': 'No User Found'})

        # Authenticate using the username linked to the email
        user = authenticate(request, username=user.username, password=password)
        if user is not None:
            # If authentication is successful
            auth_login(request, user)
            request.session['login_success'] = True
            # request.session.set_expiry(900)  # Set session expiry to 15 minutes

            return JsonResponse({'status': 'success', 'redirect_url': reverse('booking')})
        else:
            # Return an error response if the password is incorrect
            return JsonResponse({'status': 'error', 'message': 'Invalid login credentials'})
    
    return render(request, 'login.html')

def user_logout(request):
    if request.method == 'POST':
        # Store the user object before logging out
        user = request.user
        
        # Log the user out
        auth_logout(request)
        
        # Clear the session
        request.session.flush()
        
        # Redirect to the login page
        return redirect('login')
    
    return redirect('login')

import random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import BookingForm  # Make sure this model exists with the proper fields
import random

def generate_doc_number():
    # Generates a random 8-digit number prefixed with 'DOC-'
    random_num = random.randint(10000000, 99999999)
    return f"DOC-{random_num}"

def save_mapping(request):
    if request.method == "POST":
        client_id = request.POST.get("client")
        assignees = request.POST.getlist("assignees")
        validation_process = request.POST.get("validation_process")

        if client_id and validation_process:
            client = User.objects.get(id=client_id)
            mapping, created = ClientAssigneeMapping.objects.get_or_create(client=client)

            # Update Assignees and Validation Process
            mapping.assignees.set(assignees)
            mapping.validation_process = validation_process
            mapping.save()

        return redirect("masters")  # Replace with actual redirect URL

    return redirect("masters")

def get_assignees(request):
    client_id = request.GET.get("client_id")
    if client_id:
        # Get mapped assignees for the client
        try:
            mapping = ClientAssigneeMapping.objects.get(client_id=client_id)
            mapped_assignees = list(mapping.assignees.values("id", "username"))
            validation_process = mapping.validation_process  # Fetch stored validation process

        except ClientAssigneeMapping.DoesNotExist:
            mapped_assignees = []
            validation_process = ""

        # Optionally, you can fetch all potential assignees (e.g., all users except superusers)
        # all_assignees = list(User.objects.filter(is_superuser=False).values("id", "username"))
        all_assignees = list(
            User.objects.exclude(id=client_id).values("id", "username")
        )
        return JsonResponse({
            "assignees": mapped_assignees,
            "all_assignees": all_assignees,
            "validation_process": validation_process
        })
    return JsonResponse({"assignees": [], "all_assignees": [],"validation_process": ""})

@login_required
def submit_form(request):
    if request.method == "POST":
        # Retrieve booking form fields from POST data
        doc_number = request.POST.get("doc_number")
        vendor_name = request.POST.get("vendor_name")
        invoice_value = request.POST.get("invoice_value")

        document_type_id = request.POST.get("document_type")  # Expect an ID from the dropdown
        remarks = request.POST.get("remarks", "").strip()
        special_instructions = request.POST.get("special_instructions", "").strip()
        # profit_center = request.POST.get("profit_center")
        # taxable_value = request.POST.get("taxable_value")
        # igst_value = request.POST.get("igst_value")
        # cgst_value = request.POST.get("cgst_value")
        # sgst_value = request.POST.get("sgst_value")
        # selected_user_id = request.POST.get("selected_user")
        selected_assignees_ids = request.POST.getlist("selected_assignees")
        assignees = User.objects.filter(id__in=selected_assignees_ids)

        document_type = None
        if document_type_id:
            document_type = get_object_or_404(DocumentType, id=document_type_id)

        # Create a new booking entry
        booking = BookingForm.objects.create(
            doc_number=doc_number,
            vendor_name=vendor_name,
            invoice_value=invoice_value,
            document_type=document_type,
            remarks=remarks,
            special_instructions=special_instructions,
            # reference_number=reference_number,
            # profit_center=profit_center,
            # taxable_value=taxable_value,
            # igst_value=igst_value if igst_value else None,
            # cgst_value=cgst_value if cgst_value else None,
            # sgst_value=sgst_value if sgst_value else None,
            # The selected user (for example, an accountant or assigned user)
            # user=selected_user,
            # The logged-in user is the creator of the booking
            created_by=request.user,
            # documents=request.FILES.get("documents"),
            status="In Progress",

        )

        booking.assignees.set(assignees)

        documents = request.FILES.getlist("documents")
        for document in documents:
            Document.objects.create(booking=booking, file=document)
        booking.save()

        # Optionally send an email notification to the selected user
        for assignee in assignees:
            send_mail(
                "New Booking Assigned",
                f"A new booking has been submitted by {request.user.username}.",
                "your_email@example.com",  # Replace with your sender email
                [assignee.email],
                fail_silently=False,
            )

        messages.success(request, "Booking submitted successfully!")
        return redirect("form_list")
    else:
        # For GET requests, generate a random doc number and fetch users (excluding the logged-in user)
        doc_number = generate_doc_number()
        try:
            mapping = request.user.assignee_mapping  # using the related_name from ClientAssigneeMapping
            users = mapping.assignees.all()
        except ClientAssigneeMapping.DoesNotExist:
            users = User.objects.none()  # Or fallback to an empty queryset
        document_types = DocumentType.objects.all()

        # users = User.objects.exclude(id=request.user.id)

        return render(request, "submit_form.html", {"users": users, "doc_number": doc_number, "document_types": document_types})

# @login_required
# def get_assignees(request):
#     client_id = request.GET.get("client_id")
#     if client_id:
#         assignees = ClientAssigneeMapping.objects.filter(client_id=client_id).values("assignee__id", "assignee__username")
#         return JsonResponse({"assignees": list(assignees)})
#     return JsonResponse({"assignees": []})

@login_required
def form_list(request):
    user = request.user  # Logged-in user
    try:
        mapping = user.assignee_mapping  # via the related_name on ClientAssigneeMapping
        users = mapping.assignees.all()   # Only mapped assignees for this client
    except ClientAssigneeMapping.DoesNotExist:
        users = User.objects.none()       # Or fallback to an empty queryset
    
    document_types = DocumentType.objects.all()



    # Show forms where the user is either an assignee or the creator.
    forms = BookingForm.objects.filter(Q(assignees=user) | Q(created_by=user)).order_by("-id").distinct()
    in_progress_count = forms.filter(status="In Progress").count()
    query_raised_count = forms.filter(status="Raise Query").count()
    validation_count = forms.filter(status__in=["Validation", "Client Validation", "Validation In Progress"]).count()
    closed_count = forms.filter(status="Closed").count()
    # status_counts = forms.values('status').annotate(count=Count('id'))

    # validator_forms = BookingForm.objects.filter(validator=user, status="Validation").order_by("-id")
    # client_validation_forms = BookingForm.objects.filter(created_by=user, status="Validation").order_by("-id")
    # validator_forms = BookingForm.objects.filter(validator=user, status__iexact="validation").order_by("-id").distinct()
    validator_forms = BookingForm.objects.filter(
    Q(validator=user, status__iexact="Validation") |  # Validator is assigned
    Q(validator=user, status__iexact="Validation In Progress") |  # Validator in progress
    Q(created_by=user, status__iexact="Client Validation")  # Client validation stage
).order_by("-id").distinct()
    return render(request, "form_list.html",{"forms": forms,
                                              "users": users,
                                              "document_types": document_types,
                                              "validator_forms": validator_forms,
                                            #   "status_counts": status_counts,})
                                                "in_progress_count": in_progress_count,
                                                "query_raised_count": query_raised_count,
                                                "validation_count": validation_count,
                                                "closed_count": closed_count,})

@login_required
def client_validate_form(request, form_id):
    """
    This function allows only the client (the form creator) to validate the form.
    When validated, the form status changes to "Validated by Client".
    """
    form_instance = get_object_or_404(BookingForm, id=form_id)

    # Ensure only the client (form creator) can validate
    if request.user not in form_instance.assignees.all():
        messages.error(request, "Only the client can validate this form.")
        return redirect("form_detail", form_id=form_id)

    if request.method == "POST":
        # Change status to "Validated by Client"
        form_instance.status = "Client Validation"
        form_instance.save()

        messages.success(request, "Form validated successfully by the client!")
        return redirect("form_detail", form_id=form_id)

    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)

@login_required
def assign_validator_both(request, form_id):
    """
    Called when an assignee selects a validator from the modal (Validation 3 flow).
    This view assigns the selected validator and sets status to "Validation In Progress".
    """
    form_instance = get_object_or_404(BookingForm, id=form_id)
    # Ensure the user is an assignee
    if request.user not in form_instance.assignees.all():
        messages.error(request, "You are not authorized to assign a validator for this form.")
        return redirect("form_detail", form_id=form_id)
    
    if request.method == "POST":
        validator_id = request.POST.get("validator")
        if not validator_id:
            messages.error(request, "Please select a validator before submitting.")
            return redirect("form_detail", form_id=form_id)
        validator = get_object_or_404(User, id=validator_id)
        form_instance.validator = validator
        form_instance.status = "Validation In Progress"
        form_instance.save()
        messages.success(request, f"Validator {validator.username} assigned. Now the validator must click 'Client Validation'.")
        return redirect("form_detail", form_id=form_id)
    
    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)

@login_required
def client_validate_both(request, form_id):
    """
    Called when the assigned validator clicks the "Client Validation" button.
    This updates the status to "Client Validation" so that the client can then close the document.
    """
    form_instance = get_object_or_404(BookingForm, id=form_id)
    if request.user != form_instance.validator:
        messages.error(request, "Only the assigned validator can perform client validation.")
        return redirect("form_detail", form_id=form_id)
    
    if request.method == "POST":
        form_instance.status = "Client Validation"
        form_instance.save()
        messages.success(request, "Validation passed to the client for final approval.")
        return redirect("form_detail", form_id=form_id)
    
    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)

# @login_required
# def form_list(request):
#     user = request.user  # Get the logged-in user

#     # Fetch all users (only for superusers)
#     users = User.objects.all()
#     # users = User.objects.all() if user.is_superuser else None

#     # Superusers see all booking forms; others see only their relevant ones
#     # if user.is_superuser:
#     #     forms = BookingForm.objects.all().order_by('-id')  # Ordering by latest entry
#     # else:
#     #     forms = BookingForm.objects.filter(Q(created_by=user) | Q(accountant=user)).order_by('-id')

#     forms = BookingForm.objects.filter(Q(assignees=user) | Q(created_by=user)
#      ).order_by('-id').distinct()

#     return render(request, "form_list.html", {"forms": forms, "users": users})


# @login_required
# def form_detail(request, form_id):
#     form = get_object_or_404(BookingForm, id=form_id)
#     documents = form.documents.all()
#     if request.method == "POST" and request.user in form.assignees.all():
#         new_status = request.POST.get("status")
#         if new_status in ["In Progress", "Raise Query", "Closed"]:
#             form.status = new_status
#             form.save()
#             messages.success(request, "Status updated successfully!")
#         return redirect("form_detail", form_id=form.id)
#     return render(request, "form_detail.html", {"form": form, "documents": documents})

@login_required
def form_detail(request, form_id):
    form = get_object_or_404(BookingForm, id=form_id)
    user = request.user

    documents = form.documents.all()
    # query_logs = form.query_logs.order_by("-created_at")
    latest_query = form.query_logs.last() # For query history (if exists)
    # reference_filled = form.reference_number is not None and form.reference_number.strip() != ""
    # latest_query = form.query_logs.all().order_by('resolved_at')
    # status_valid = form.status.lower() != "raise query"
    document_types = DocumentType.objects.all()
    query_history = form.query_logs.all().order_by("-resolved_at")  # Reverse order by date
    update_history = form.updates.all().order_by("-updated_at")

    forms_qs = BookingForm.objects.filter(Q(assignees=user) | Q(created_by=user)).order_by("id").distinct()
    forms_list = list(forms_qs)

    # Find index of current form
    current_index = None
    for index, f in enumerate(forms_list):
        if f.id == form.id:
            current_index = index
            break
        
    prev_form = forms_list[current_index - 1] if current_index is not None and current_index > 0 else None
    next_form = forms_list[current_index + 1] if current_index is not None and current_index < len(forms_list) - 1 else None

    try:
        mapping = form.created_by.assignee_mapping  # using related_name in ClientAssigneeMapping
        validation_process = mapping.validation_process
    except ClientAssigneeMapping.DoesNotExist:
        try:
            validation_process = form.created_by.assignee_mapping.validation_process
        except ClientAssigneeMapping.DoesNotExist:
            validation_process = None  # Or a default value

    exclude_ids = list(form.assignees.values_list("id", flat=True))
    exclude_ids.append(form.created_by.id)
    possible_validators = User.objects.exclude(id__in=exclude_ids)

    # Use filter().exists() to reliably check if user is an assignee.
    is_assignee = form.assignees.filter(id=request.user.id).exists()
    show_resolve_button = form.status == "Raise Query" and request.user == form.created_by
    # show_validate_button = reference_filled and status_valid and is_assignee

    if request.method == "POST" and is_assignee:
        new_status = request.POST.get("status")
        # Debug: print new status to server logs
        print("DEBUG: Received new_status =", new_status)

        if new_status in ["In Progress", "Raise Query", "Closed","Validation"]:
            form.status = new_status
            form.save()
            print("DEBUG: Status updated to", form.status)
            messages.success(request, "Status updated successfully!")
        else:
            messages.error(request, "Invalid status value.")

        return redirect("form_detail", form_id=form.id)

    return render(request, "form_detail.html", {
        "form": form,
        "documents": documents,
        "latest_query": latest_query,
        "show_resolve_button": show_resolve_button,
        "document_types":document_types,
        # "show_validate_button": show_validate_button,
        "possible_validators": possible_validators,
        "validation_process": validation_process,
        "query_history": query_history,  # Pass reversed query history
        "update_history": update_history,
        "prev_form": prev_form,
        "next_form": next_form,
    })

# @login_required
# def validate_form(request, form_id):
    form_instance = get_object_or_404(BookingForm, id=form_id)

    # Ensure the user is an assignee of this form
    if request.user not in form_instance.assignees.all():
        messages.error(request, "You are not authorized to assign a validator for this form.")
        return redirect('form_detail', form_id=form_id)

    if request.method == "POST":
        validator_id = request.POST.get("validator")
        validator = get_object_or_404(User, id=validator_id)

        # Assign the validator to the form
        form_instance.validator = validator
        form_instance.status = "Validation"  # Change status to Validation
        form_instance.save()

        messages.success(request, f"Validator {validator.username} assigned successfully.")
        return redirect('form_detail', form_id=form_id)

    # Get a list of possible validators (Exclude Assignees + Client)
    possible_validators = User.objects.exclude(id__in=form_instance.assignees.values_list('id', flat=True)) \
                                      .exclude(id=form_instance.client.id)

    return render(request, "assign_validator.html", {
        "form_instance": form_instance,
        "possible_validators": possible_validators
    })

@login_required
def validate_form(request, form_id):
    form_instance = get_object_or_404(BookingForm, id=form_id)

    # Ensure the user is an assignee of this form
    if request.user not in form_instance.assignees.all():
        messages.error(request, "You are not authorized to assign a validator for this form.")
        return redirect('form_detail', form_id=form_id)

    if request.method == "POST":
        validator_id = request.POST.get("validator")
        validator = get_object_or_404(User, id=validator_id)

        # Assign the validator to the form
        form_instance.validator = validator
        form_instance.status = "Validation"  # Or another appropriate status
        form_instance.save()

        messages.success(request, f"Validator {validator.username} assigned successfully.")
        return redirect('form_detail', form_id=form_id)

    # Get a list of possible validators
    possible_validators = User.objects.all().exclude(id=request.user.id)  # Exclude the current user

    return render(request, "assign_validator.html", {
        "form_instance": form_instance,
        "possible_validators": possible_validators
    })


# @login_required
# def validate_form(request, form_id):
    print(f"View Triggered for Form ID: {form_id}")
    form_instance = get_object_or_404(BookingForm, id=form_id)

    # Retrieve validation process type from the mapped client
    try:
        validation_process = form_instance.created_by.assignee_mapping.validation_process
    except ClientAssigneeMapping.DoesNotExist:
        validation_process = None  # Set default if mapping does not exist

    # Authorization checks for validation actions
    if validation_process == "Validation 1" and request.user not in form_instance.assignees.all():
        messages.error(request, "You are not authorized to assign a validator for this form.")
        return redirect("form_detail", form_id=form_id)

    if validation_process == "Validation 2" and request.user != form_instance.created_by:
        messages.error(request, "Only the client can validate this form.")
        return redirect("form_detail", form_id=form_id)

    if request.method == "POST":
        # **Validation 1 & 3**: Assignee selects a validator from a dropdown modal
        if validation_process in ["Validation 1", "Validation 3"]:
            validator_id = request.POST.get("validator")
            if not validator_id:
                messages.error(request, "Please select a validator before submitting.")
                return redirect("form_detail", form_id=form_id)

            validator = get_object_or_404(User, id=validator_id)
            form_instance.validator = validator
            form_instance.status = "Validation"  # Update status
            form_instance.save()

            messages.success(request, f"Validator {validator.username} assigned successfully.")
            return redirect("form_detail", form_id=form_id)

        # **Validation 2**: The client validates directly
        elif validation_process == "Validation 2":
            form_instance.validator = request.user  # Client is automatically assigned as validator
            form_instance.status = "Validation"
            form_instance.save()
            print(f"Status Updated to: {form_instance.status}")

            messages.success(request, "You have validated this form successfully!")
            return redirect("form_detail", form_id=form_id)

        else:
            messages.error(request, "Invalid validation process.")
            return redirect("form_detail", form_id=form_id)

    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)

# @login_required
# def validate_form(request, form_id):
    print(f"View Triggered for Form ID: {form_id}")  
    form_instance = get_object_or_404(BookingForm, id=form_id)

    try:
        validation_process = form_instance.created_by.assignee_mapping.validation_process
    except ClientAssigneeMapping.DoesNotExist:
        validation_process = None

    print(f"Validation Process: {validation_process}")  

    # Ensure only the client can validate for Validation 2
    if validation_process == "Validation 2" and request.user != form_instance.created_by:
        messages.error(request, "Only the client can validate this form.")
        return redirect("form_detail", form_id=form_id)

    if request.method == "POST":
        print("POST Data:", request.POST)  
        
        if validation_process == "Validation 2":
            if request.user == form_instance.created_by:
                form_instance.validator = request.user  
                form_instance.status = "Validation"
                try:
                    form_instance.save()
                    print(f"Status Updated Successfully: {form_instance.status}")  
                except Exception as e:
                    print(f"Error while saving form: {e}")  
                    messages.error(request, "An error occurred while saving the form.")
                
                messages.success(request, "You have validated this form successfully!")
                return redirect("form_detail", form_id=form_id)

    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)




# @login_required
# def form_detail(request, form_id):
#     form = get_object_or_404(BookingForm, id=form_id)
#     documents = form.documents.all()
#     latest_query = form.query_logs.last()  # Get the latest query

#     # Show "Resolve Query" button instead of "Edit" if status is "Raise Query"
#     show_resolve_button = form.status == "Raise Query" and request.user == form.created_by

#     if request.method == "POST" and request.user in form.assignees.all():
#         new_status = request.POST.get("status")
#         query_comment = request.POST.get("query_comment", "").strip()

        

#         # ✅ Only require a comment when raising a query
#         if new_status == "Raise Query" and not query_comment:
#             messages.error(request, "Query comment is required when raising a query.")
#             return redirect("form_detail", form_id=form.id)

#         # ✅ Update the status based on user input
#         if new_status in ["In Progress", "Raise Query", "Closed"]:
#             form.status = new_status
#             form.save()

#             # ✅ Log query ONLY if raising a query
#             if new_status == "Raise Query":
#                 QueryLog.objects.create(
#                     form=form,
#                     assignee=request.user,
#                     query_comment=query_comment
#                 )
#                 messages.success(request, "Query raised successfully!")
#             else:
#                 messages.success(request, "Status updated successfully!")

#         return redirect("form_detail", form_id=form.id)

#     return render(request, "form_detail.html", {
#         "form": form,
#         "documents": documents,
#         "latest_query": latest_query,
#         "show_resolve_button": show_resolve_button
#     })

@login_required
def close_document(request, form_id):
    form_instance = get_object_or_404(BookingForm, id=form_id)
    
    # Ensure only the assigned validator can close the document
    if request.user != form_instance.validator:
        messages.error(request, "You are not authorized to close this document.")
        return redirect("form_detail", form_id=form_id)
    
    if request.method == "POST":
        form_instance.status = "Closed"
        form_instance.save()
        messages.success(request, "Document closed successfully!")
        return redirect("form_detail", form_id=form_id)
    
    return redirect("form_detail", form_id=form_id)

@login_required
def close_document_both(request, form_id):
    """
    Called when the client clicks "Close Document" after client validation.
    This updates the form's status to "Closed".
    """
    form_instance = get_object_or_404(BookingForm, id=form_id)
    if request.user != form_instance.created_by:
        messages.error(request, "Only the client can close this document.")
        return redirect("form_detail", form_id=form_id)
    
    if request.method == "POST":
        form_instance.status = "Closed"
        form_instance.save()
        messages.success(request, "Document closed successfully!")
        return redirect("form_detail", form_id=form_id)
    
    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)

@login_required
def close_document_both(request, form_id):
    form_instance = get_object_or_404(BookingForm, id=form_id)
    
    print(f"DEBUG: Current Status: {form_instance.status}, Request User: {request.user}")

    if request.user != form_instance.created_by:
        messages.error(request, "Only the client can close this document.")
        return redirect("form_detail", form_id=form_id)
    
    if request.method == "POST":
        form_instance.status = "Closed"
        form_instance.save()
        
        print(f"DEBUG: Status Updated to {form_instance.status}")  # Debugging line
        
        messages.success(request, "Document closed successfully!")
        return redirect("form_detail", form_id=form_id)
    
    messages.error(request, "Invalid request method.")
    return redirect("form_detail", form_id=form_id)


@login_required
def update_status(request, form_id):
    form = get_object_or_404(BookingForm, id=form_id)

    if request.user != form.accountant:
        messages.error(request, "Only the assigned accountant can update status.")
        return redirect("form_list")

    if request.method == "POST":
        new_status = request.POST.get("status")
        print(new_status,"hello")
        form.status = new_status
        form.save()

        # Send email notification to customer
        send_mail(
            "Form Status Updated",
            f"Your form status has been updated to {new_status}.",
            "your_email@example.com",
            [form.customer.email],
            fail_silently=False,
        )

        messages.success(request, "Status updated successfully!")
        return redirect("form_detail", form_id=form.id)

    return render(request, "update_status.html", {"form": form})

from django.http import HttpResponseForbidden

from decimal import Decimal
import decimal
@login_required
def update_form(request, form_id):
    form = get_object_or_404(BookingForm, id=form_id)
    updated_fields = {}

    if request.method == "POST":
        # Process text fields (including reference_number)
        for field in ["vendor_name","special_instructions","remarks",]:
            old_value = getattr(form, field, "").strip() if getattr(form, field) else ""
            new_value = request.POST.get(field, "").strip()
            if old_value.strip() != new_value:
                updated_fields[field] = (old_value, new_value)
                setattr(form, field, new_value)

        # Process numeric fields
        numeric_fields = ["invoice_value"]
        for field in numeric_fields:
            old_value = getattr(form, field, None)
            new_value_str = request.POST.get(field, "").strip()
            if new_value_str:
                try:
                    new_value = Decimal(new_value_str)
                    if old_value is None or str(old_value) != str(new_value):
                        updated_fields[field] = (str(old_value) if old_value is not None else "N/A", str(new_value))
                        setattr(form, field, new_value)
                except ValueError:
                    messages.error(request, f"Invalid value for {field.replace('_', ' ').title()}.")
                    return redirect("form_detail", form_id=form.id)

        # Process multiple file uploads from "documents"
        document_files = request.FILES.getlist("documents")
        if document_files:
            # Get a list of old document names (if any)
            old_docs = list(form.documents.values_list("file", flat=True))
            form.documents.all().delete()   
            # Create Document objects for each newly uploaded file
            new_doc_names = [doc_file.name for doc_file in document_files]

            for doc_file in document_files:
                Document.objects.create(booking=form, file=doc_file)
                # new_doc_names.append(new_doc.file.name)
            # Log the changes (if any old documents exist, join them, otherwise indicate no previous doc)
            updated_fields["documents"] = (", ".join(old_docs), ", ".join(new_doc_names))

        # Save changes if any updates were made
        if updated_fields:
            form.save()
            # Log each change in the UpdateLog table
            for field, (old, new) in updated_fields.items():
                UpdateLog.objects.create(
                    form=form,
                    updated_by=request.user,
                    field_name=field.replace("_", " ").title(),
                    old_value=old,
                    new_value=new,
                )
            messages.success(request, "Form updated successfully!")
        else:
            messages.info(request, "No changes detected.")

        return redirect("form_detail", form_id=form.id)

    return redirect("form_detail", form_id=form.id)

@login_required
def add_reference(request, form_id):
    form = get_object_or_404(BookingForm, id=form_id)
    
    if request.method == "POST":
        new_reference = request.POST.get("reference_number", "").strip()
        old_reference = form.reference_number.strip() if form.reference_number else "N/A"
        
        # Check if the new reference is different from the old one
        if old_reference != new_reference:
            form.reference_number = new_reference
            form.save(update_fields=["reference_number"])

            # Log the update in UpdateLog
            UpdateLog.objects.create(
                form=form,
                updated_by=request.user,
                field_name="Reference Number",
                old_value=old_reference,
                new_value=new_reference,
            )
            messages.success(request, "Reference number updated successfully!")
        else:
            messages.info(request, "No changes detected in the reference number.")

        return redirect("form_detail", form_id=form.id)
    
    return redirect("form_detail", form_id=form.id)

# @login_required
# def add_query(request, form_id):
#     form_instance = get_object_or_404(BookingForm, id=form_id)
    
#     # Ensure the logged-in user is an assignee and the form status is "Raise Query"
#     if request.user not in form_instance.assignees.all() or form_instance.status != "Raise Query":
#         messages.error(request, "You are not authorized to add a query for this form.")
#         return redirect("form_detail", form_id=form_id)
    
#     if request.method == "POST":
#         query_comment = request.POST.get("query_comment", "").strip()
#         if not query_comment:
#             messages.error(request, "Query comment cannot be empty.")
#             return redirect("form_detail", form_id=form_id)
        
#         # Create a QueryLog record for this query (initially without a resolve comment)
#         QueryLog.objects.create(
#             form=form_instance,
#             assignee=request.user,
#             query_comment=query_comment,
#             updated_by=request.user
#         )
#         messages.success(request, "Query submitted successfully!")
#         return redirect("form_detail", form_id=form_id)
    
#     return redirect("form_detail", form_id=form_id)

# @login_required
# def add_query(request, form_id):
#     form = get_object_or_404(BookingForm, id=form_id)
    
#     # Check that the logged-in user is indeed an assignee:
#     if not form.assignees.filter(id=request.user.id).exists():
#         messages.error(request, "You are not authorized to add a query for this form.")
#         return redirect("form_detail", form_id=form.id)
    
#     if request.method == "POST":
#         query_comment = request.POST.get("query_comment", "").strip()
#         if not query_comment:
#             messages.error(request, "Query comment cannot be empty.")
#             return redirect("form_detail", form_id=form.id)
        
#         # existing_query = form.query_logs.filter(assignee=request.user,resolution_comment__isnull=True).exists()
#         # if existing_query:
#         #     messages.error(request, "A query is already raised and pending resolution.")
#         #     return redirect("form_detail", form_id=form.id)
        
#         # Create the QueryLog record with the logged-in user as the assignee.
#         QueryLog.objects.create(
#             form=form,
#             assignee=request.user,       # Ensure this is set and request.user is valid.
#             query_comment=query_comment,
#             updated_by=None      # You can adjust this if needed.
#         )


#         messages.success(request, "Query raised successfully!")
#         return redirect("form_detail", form_id=form.id)
    
#     return redirect("form_detail", form_id=form.id)

@login_required
def add_query(request, form_id):
    form = get_object_or_404(BookingForm, id=form_id)

    # Check that the logged-in user is an assignee
    if not form.assignees.filter(id=request.user.id).exists():
        messages.error(request, "You are not authorized to add a query for this form.")
        return redirect("form_detail", form_id=form.id)

    if request.method == "POST":
        query_comment = request.POST.get("query_comment", "").strip()
        uploaded_files = request.FILES.getlist("query_documents")  # Get multiple files
        
        if not query_comment and not uploaded_files:
            messages.error(request, "Query comment or at least one document is required.")
            return redirect("form_detail", form_id=form.id)

        # ✅ Create the QueryLog entry FIRST and store it in a variable
        query_log = QueryLog.objects.create(
            form=form,
            assignee=request.user,
            query_comment=query_comment,
            updated_by=None  # Not resolved yet
        )

        # ✅ Now, save each uploaded file and link it to the query
        for file in uploaded_files:
            QueryDocument.objects.create(query=query_log,file=file)  # Link document to the query

        messages.success(request, "Query raised successfully with documents!")
        return redirect("form_detail", form_id=form.id)

    return redirect("form_detail", form_id=form.id)

import decimal



@login_required
def resolve_query(request, form_id):
    form = get_object_or_404(BookingForm, id=form_id)
    
    # Only allow the client (creator) to resolve the query.
    if request.user.id != form.created_by.id:
        messages.error(request, "You are not authorized to resolve this query.")
        return redirect("form_detail", form_id=form.id)
    
    query_log = form.query_logs.filter(resolution_comment__isnull=True).last()
    if not query_log:
        messages.error(request, "No pending query to resolve.")
        return redirect("form_detail", form_id=form.id)
    
    if not query_log.assignee:
        messages.error(request, "The query record is missing the original assignee. Please contact support.")
        return redirect("form_detail", form_id=form.id)
    
    if request.method == "POST":
        resolution_comment = request.POST.get("resolution_comment", "").strip()
        if not resolution_comment:
            messages.error(request, "Resolution comment is required.")
            return redirect("form_detail", form_id=form.id)
        
        # Define the fields that can be edited during resolution.
        fields_to_update = [
            "vendor_name", "invoice_value","special_instructions","remarks","document_type"
        ]
        updated_fields = {}

        for field in fields_to_update:
            old_value = getattr(form, field, None)
            new_value_raw = request.POST.get(field, "").strip()

            # Handle numeric fields separately
            if field in ["invoice_value"]:
                try:
                    new_value = Decimal(new_value_raw) if new_value_raw else None
                except decimal.InvalidOperation:
                    messages.error(request, f"Invalid value for {field.replace('_', ' ').title()}.")
                    return redirect("form_detail", form_id=form.id)
                
                old_value_str = str(old_value) if old_value is not None else "N/A"
                new_value_str = str(new_value) if new_value is not None else "N/A"
                if old_value_str != new_value_str:
                    updated_fields[field] = f"{old_value_str} → {new_value_str}"
                    setattr(form, field, new_value)
            elif field == "document_type":  # Handle document type separately
                if new_value_raw:
                    try:
                        document_type_obj = DocumentType.objects.get(id=new_value_raw)
                        if form.document_type != document_type_obj:
                            updated_fields[field] = f"{form.document_type} → {document_type_obj}"
                            form.document_type = document_type_obj
                    except DocumentType.DoesNotExist:
                        messages.error(request, "Invalid Document Type selected.")
                        return redirect("form_detail", form_id=form.id)
                else:
                    form.document_type = None  # Allow clearing the document type
            else:
                # For text fields, allow empty string (but log as "N/A" if empty)
                old_value_str = old_value.strip() if old_value else ""
                if old_value_str != new_value_raw:
                    updated_fields[field] = f"{old_value_str or 'N/A'} → {new_value_raw or 'N/A'}"
                    setattr(form, field, new_value_raw)

        # Handle file uploads: Replace existing documents with new ones.
        document_files = request.FILES.getlist("documents")
        if document_files:
            # Get a list of old document names (if any)
            old_docs = list(form.documents.values_list("file", flat=True))
            form.documents.all().delete()   
            # Create Document objects for each newly uploaded file
            new_doc_names = [doc_file.name for doc_file in document_files]

            for doc_file in document_files:
                Document.objects.create(booking=form, file=doc_file)
                # new_doc_names.append(new_doc.file.name)
            # Log the changes (if any old documents exist, join them, otherwise indicate no previous doc)
            updated_fields["documents"] = (", ".join(old_docs), ", ".join(new_doc_names))

        
        # Save form and update status if any changes have been made.
        if updated_fields or resolution_comment:
            # Change status to "In Progress"
            form.status = "In Progress"
            form.save()
            
            # Create a QueryLog entry with details of the resolution.
            # We'll assume the assignee's original query comment is from the latest query log.
            latest_query = form.query_logs.last()
            original_query_comment = latest_query.query_comment if latest_query else ""
            print(form.assignees.first())
            QueryLog.objects.create(
                form=form,
                # assignee=query_log.updated_by if query_log else None,
                assignee=query_log.assignee,
  # or select appropriate assignee if multiple
                query_comment=original_query_comment,
                updated_by=request.user,
                updated_fields=updated_fields,
                resolution_comment=resolution_comment,
            )
            # if new_doc_names:
            #     for doc_file in document_files:
            #         QueryDocument.objects.create(query=new_query_log, file=doc_file)
            # Send email to all assignees
            for assignee in form.assignees.all():
                send_mail(
                    "Query Resolved",
                    f"The query for form {form.doc_number} has been resolved by {request.user.username}.",
                    "noreply@example.com",
                    [assignee.email],
                    fail_silently=False,
                )
            messages.success(request, "Query resolved and form updated successfully!")
        else:
            messages.info(request, "No changes detected.")

        return redirect("form_detail", form_id=form.id)
    
    return redirect("form_detail", form_id=form.id)

from django.contrib.auth.models import User
from .models import DocumentType, ClientAssigneeMapping

@login_required
def masters(request):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to access the Masters page.")
        return redirect("form_list")
    
    clients = User.objects.all()
    # clients = User.objects.filter(is_staff=False)  # Assuming clients are not staff
    document_types = DocumentType.objects.all()
    mappings = ClientAssigneeMapping.objects.all()
    
    context = {
        "clients": clients,
        "document_types": document_types,
        "mappings": mappings,
    }
    return render(request, "masters.html", context)

# @login_required
# def save_mapping(request):
#     if request.method == "POST" and request.user.is_superuser:
#         client_id = request.POST.get("client")
#         assignee_ids = request.POST.getlist("assignees")
#         client = get_object_or_404(User, id=client_id)
#         mapping, created = ClientAssigneeMapping.objects.get_or_create(client=client)
#         mapping.assignees.set(assignee_ids)
#         messages.success(request, "Mapping saved successfully!")
#     return redirect("masters")

@login_required
def save_document_type(request):
    if request.method == "POST" and request.user.is_superuser:
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        DocumentType.objects.create(name=name, description=description)
        messages.success(request, "Document type saved successfully!")
    return redirect("masters")

@login_required
def delete_document_type(request, dt_id):
    # Only superusers should be able to delete a document type.
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to delete document types.")
        return redirect("masters")
    
    dt = get_object_or_404(DocumentType, id=dt_id)
    dt.delete()
    messages.success(request, "Document type deleted successfully!")
    return redirect("masters")
