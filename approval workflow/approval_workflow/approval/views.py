from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import RequestForm, Requirement, Approval, HighlightPoint ,EmailTemplate, QueryUpdates
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



# import os,mimetypes,json,openpyxl,re,pytz,xlsxwriter
from django.urls import reverse
@login_required
def workflow(req):
    return render(req,"workflow.html")

def superuser_required(user):
    return user.is_superuser

@login_required
def some_view(request):
    return render(request, "template.html", {"user": request.user})

@login_required
@user_passes_test(superuser_required)
def edit_email_template(request):
    email_template, created = EmailTemplate.objects.get_or_create(id=1)

    if request.method == "POST":
        first_body = request.POST.get("first_approver_body", "").strip()
        next_body = request.POST.get("next_approver_body", "").strip()

        email_template.first_approver_body = first_body
        email_template.next_approver_body = next_body
        email_template.save()

        messages.success(request, "Email templates updated successfully!")
        return redirect("document")  # Redirect back to the document page

    return render(request, "edit_email_template.html", {"email_template": email_template})


@login_required
def check_signature(request):
    """ Redirects user to upload signature if not already uploaded """
    has_signature = UserProfile.objects.filter(user=request.user).first()
    print(has_signature)
    if has_signature and has_signature.signature:
        print("document")
        return redirect("document")  # ✅ Redirect to document page if signature exists
    else:
        print("not document")
        return redirect("upload_signature")  # ✅ Stay on upload signature page

# @login_required
# def upload_signature(request):
#     """ Allows users to upload their digital signature """
#     if request.method == "POST":
#         signature_file = request.FILES.get("signature")

#         if not signature_file:
#             return render(request, "upload_signature.html", {"error": "Please upload a signature!"})

#         if signature_file.size > 2 * 1024 * 1024:  # ✅ Limit to 2MB
#             return render(request, "upload_signature.html", {"error": "File size exceeds 2MB!"})

#         # ✅ Store signature or update existing one
#         UserProfile.objects.update_or_create(user=request.user, defaults={"signature": signature_file})

#         return redirect("document")  # ✅ Redirect to document page after upload

#     return render(request, "upload_signature.html")

@login_required
def document(request):
    users = User.objects.exclude(id=request.user.id)

    with transaction.atomic():
        last_doc = RequestForm.objects.order_by("-doc_number").select_for_update().first()
        next_doc_number = f"DOC-{(int(last_doc.doc_number.split('-')[1]) + 1) if last_doc else 1001}"

    if request.method == "POST":
        doc_number = request.POST.get("doc-id", next_doc_number)
        description = request.POST.get("description", "No description provided")
        uploaded_file = request.FILES.get("document")  # ✅ Get uploaded file

        if uploaded_file and uploaded_file.size > 5 * 1024 * 1024:
            messages.error(request, "File size exceeds 5MB limit!")
            return redirect("document")

        new_request = RequestForm.objects.create(
            doc_number=doc_number,
            description=description,
            created_by=request.user,
            document=uploaded_file  # ✅ Save the file in DB
        )

        highlight_points = request.POST.getlist("highlight_points[]")
        for point in highlight_points:
            if point.strip():
                HighlightPoint.objects.create(request=new_request, point=point.strip())

        requirements = request.POST.getlist("requirement[]")
        quantities = request.POST.getlist("quantity[]")
        prices = request.POST.getlist("price[]")
        descriptions = request.POST.getlist("req_description[]")

        for i in range(len(requirements)):
            if requirements[i].strip():
                quantity = int(quantities[i]) if quantities[i] else 0
                price = float(prices[i]) if prices[i] else 0.00  
                amount = round(quantity * price, 2)

                Requirement.objects.create(
                    request=new_request,
                    requirement_name=requirements[i],
                    quantity=quantity,
                    price=price,
                    amount=amount,
                    description=descriptions[i] if descriptions[i] else ""
                )

        approvers = request.POST.getlist("approvers[]")
        if not approvers:
            return render(request, "document.html", {"users": users, "next_doc_number": next_doc_number, "error": "Please select at least one approver"})

        approver_users = [User.objects.get(id=int(user_id)) for user_id in approvers if user_id.isdigit()]
        
        # ✅ Set first approver as "Pending", others as "On Hold"
        for index, approver in enumerate(approver_users):
            Approval.objects.create(
                request=new_request,
                approver=approver,
                status="Pending" if index == 0 else "On Hold"
            )
        email_template, created = EmailTemplate.objects.get_or_create(id=1)

        # Notify all approvers about the new request using a professional email template
        # for approver in approver_users:
        #     # For the first approver, use first_approver_body; otherwise use next_approver_body
        #     if index == 0:
        #         email_body = email_template.first_approver_body
        #         template_file = "ff.html"  # ✅ First Approver Template
        #     else:
        #         email_body = email_template.next_approver_body
        #         template_file = "nx.html"
        approver=approver_users[0]
        email_body = email_template.first_approver_body
        # ✅ Notify all approvers about the new request
        # for approver in approver_users:
        email_context = {
                "approver_name": approver.username,
                "doc_number": doc_number,
                "requester_name": request.user.username,
                "approval_link": f"http://127.0.0.1:8000/approval_list/",
                "company_logo": "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png",
                "email_body": email_body,

            }
        html_message = render_to_string("ff.html", email_context)
        plain_message = strip_tags(html_message)

        email = EmailMultiAlternatives(
            subject=f"Approval Needed – Document ID {doc_number}",
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[approver.email],
        )        

        #     html_message = render_to_string("nn.html", email_context)
        #     plain_message = strip_tags(html_message)

        #     email = EmailMultiAlternatives(
        #         subject=f"New Approval Request – Document ID {doc_number}",
        #         body=plain_message,
        #         from_email=settings.DEFAULT_FROM_EMAIL,
        #         to=[approver.email],
        #     )

        #     if uploaded_file:  # ✅ Attach the uploaded document
        #         email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)

        #     email.attach_alternative(html_message, "text/html")
        #     email.send(fail_silently=False)

        # ✅ Notify only the first approver
        # first_approver = approver_users[0]
        # email_context["approver_name"] = first_approver.username
            # html_message = render_to_string("ff.html", email_context)
            # plain_message = strip_tags(html_message)

            

        if uploaded_file:
            email.attach(uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)

        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

        messages.success(request, "Document submitted successfully!")
        return redirect("request_history")  


    return render(request, "document.html", {"users": users, "next_doc_number": next_doc_number})

@login_required
def request_history(request):
    user_requests = RequestForm.objects.filter(created_by=request.user).order_by("-created_at")
    
    for req in user_requests:
        approvals = req.approvals.all()

        if req.has_query == 1:
            req.overall_status = "Query Raised"
        elif req.has_query == 2:
            pending_approver = approvals.filter(status="Pending").order_by("id").first()
            req.overall_status = f"Pending - {pending_approver.approver.username}" if pending_approver else "Pending"
        else:
            # ✅ Handle Normal Approval Status
            if approvals.filter(status="Rejected").exists():
                req.overall_status = "Rejected"
            elif approvals.filter(status="Pending").exists():
                pending_approver = approvals.filter(status="Pending").order_by("id").first()
                req.overall_status = f"Pending - {pending_approver.approver.username}" if pending_approver else "Pending"
            else:
                req.overall_status = "Approved"

        # Determine Overall Status
        # if approvals.filter(status="Rejected").exists():
        #     req.overall_status = "Rejected"
        # elif approvals.filter(status="Pending").exists():
        #     pending_approver = approvals.filter(status="Pending").order_by("id").first()
        #     req.overall_status = f"Pending - {pending_approver.approver.username}" if pending_approver else "Pending"

        # else:
        #     req.overall_status = "Approved"

        # Collect Approver Comments
        req.approver_comments = [
            {   "id": approval.id,#approval id
                "name": approval.approver.username,
                "status": approval.status,
                "comment": approval.comments if approval.comments else "No comments"
            }
            for approval in approvals.exclude(status="Pending")  # Exclude pending approvals
        ]
        # queried_approval = approvals.filter(status="Queried").first()
        # req.first_approval_id = queried_approval.id if queried_approval else None
        queried_approval = approvals.filter(status="Queried").first()
        if queried_approval:
            req.first_approval_id = queried_approval.id
        else:
            pending_approval = approvals.filter(status="Pending").order_by("id").first()
            req.first_approval_id = pending_approval.id if pending_approval else None


    return render(request, "request_history.html", {"requests": user_requests})

# @login_required
# def request_history(request):
    user_requests = RequestForm.objects.filter(created_by=request.user).order_by("-created_at")
    
    for req in user_requests:
        approvals = req.approvals.all()

        # Determine Overall Status
        if approvals.filter(status="Rejected").exists():
            req.overall_status = "Rejected"
        elif approvals.filter(status="Pending").exists():
            pending_approver = approvals.filter(status="Pending").order_by("id").first()
            req.overall_status = f"Pending - {pending_approver.approver.username}" if pending_approver else "Pending"
        else:
            req.overall_status = "Approved"

        # Collect Approver Comments and Approval IDs
        req.approver_comments = [
            {
                "id": approval.id,  # ✅ Pass the approval ID
                "name": approval.approver.username,
                "status": approval.status,
                "comment": approval.comments if approval.comments else "No comments"
            }
            for approval in approvals.exclude(status="Pending")  # Exclude pending approvals
        ]

        # ✅ Store first approval ID (if exists) for "View Query" button
        req.first_approval_id = approvals.filter(status="Queried").first().id if approvals.filter(status="Queried").exists() else None

    return render(request, "request_history.html", {"requests": user_requests})


def user_login(request):
    print("user_login")
    # Check if the user is already authenticated
    if request.user.is_authenticated:
        return redirect('workflow')  

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

            return JsonResponse({'status': 'success', 'redirect_url': reverse('workflow')})
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

#this is the real one
@login_required
def get_request_details_all(request, doc_id):
    print("request_detail print hello")
    try:
        request_form = RequestForm.objects.prefetch_related("highlights", "requirements", "approvals").get(id=doc_id)
        document_url = request_form.document.url if request_form.document else None
        if document_url:
            document_url = request.build_absolute_uri(document_url)
        query_documents = QueryDocument.objects.filter(request=request_form)
        data = {
            "success": True,
            "doc_number": request_form.doc_number,
            "description": request_form.description,
            "created_by": request_form.created_by.username,
            "created_at": localtime(request_form.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            "highlights": [highlight.point for highlight in request_form.highlights.all()],
            "query_documents": [
            {"name": doc.document.name, "url": doc.document.url} for doc in query_documents
            ],
            "requirements": [
                {
                    "requirement_name": req.requirement_name,
                    "quantity": req.quantity,
                    "price": req.price,
                    "amount": req.amount,
                    "description": req.description
                }
                for req in request_form.requirements.all()
            ],
            "approvers": [
                {
                    "name": approval.approver.username,
                    "status": approval.status,
                    "comments": approval.comments if approval.comments else "No comments",
                    "updated_at": localtime(approval.updated_at).strftime("%Y-%m-%d %H:%M:%S") if approval.updated_at else "Not yet updated"

                }
                for approval in request_form.approvals.all()  # Fetch **all** approvers
            ],
            "document_url": document_url,
        
        }
        return JsonResponse(data)

    except RequestForm.DoesNotExist:
        return JsonResponse({"success": False, "error": "Request not found"}, status=404)

@login_required
def get_request_details_user(request, doc_id):
    try:
        request_form = RequestForm.objects.prefetch_related("highlights", "requirements", "approvals").get(id=doc_id)
        user_approval = request_form.approvals.filter(approver=request.user).first()
        document_url = request_form.document.url if request_form.document else None
        if document_url:
            document_url = request.build_absolute_uri(document_url)
        query_documents = QueryDocument.objects.filter(request=request_form)

        data = {
            "success": True,
            "doc_number": request_form.doc_number,
            "description": request_form.description,
            "created_by": request_form.created_by.username,
            "created_at": localtime(request_form.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            "highlights": [highlight.point for highlight in request_form.highlights.all()],
            "document_url": document_url,
            "query_documents": [
            {"name": doc.document.name, "url": doc.document.url} for doc in query_documents
            ],
            "requirements": [
                {
                    "requirement_name": req.requirement_name,
                    "quantity": req.quantity,
                    "price": req.price,
                    "amount": req.amount,
                    "description": req.description
                }
                for req in request_form.requirements.all()
            ],
            "approvers": [
                {
                    "name": user_approval.approver.username,
                    "status": user_approval.status,
                    "comments": user_approval.comments if user_approval.comments else "No comments"
                }
            ]if user_approval else [],
        
        }
        return JsonResponse(data)

    except RequestForm.DoesNotExist:
        return JsonResponse({"success": False, "error": "Request not found"}, status=404)

# @login_required
# def approval_list(request):
    print("hello")
    # Get the first pending approval assigned to the logged-in user
    approvals = Approval.objects.filter(
        approver=request.user, status="Pending"
    ).order_by("-id")  # ✅ Show only the first pending approval

    return render(request, "approval_list.html", {"approvals": approvals})

@login_required
def approval_list(request):
    # Get pending approvals assigned to the logged-in user
    approvals = Approval.objects.filter(
        approver=request.user, status="Pending"
    ).order_by("-id")
    
    # For each approval, compute a custom status based on the related request’s has_query value
    for approval in approvals:
        print(f"Approval ID: {approval.id}, Has Query: {approval.request.has_query}")
        # Make sure the RequestForm has the attribute "has_query"
        has_query = getattr(approval.request, "has_query", 0)
        if has_query == 1:
            approval.computed_status = "Query Raised"
        elif has_query == 2:
            # You might want to include the name of the approver who is next
            # For now, we just display "Query Resolved"
            approval.computed_status = "Query Resolved"
        else:
            approval.computed_status = "Pending"
    
    return render(request, "approval_list.html", {"approvals": approvals})


# @login_required
# def approval_list(request):
    approvals = Approval.objects.filter(approver=request.user).select_related("request").order_by("-id")

    for approval in approvals:
        if approval.request.has_query == 1:
            approval.query_status = "Query Submitted"
        elif approval.request.has_query == 2:
            approval.query_status = "Query Resolved - Pending Approval"
        else:
            approval.query_status = approval.status  # Default to existing status

    return render(request, "approval_list.html", {"approvals": approvals})


@login_required
def get_approval_details(request, approval_id):
    print("get_approval_details")  # Fix: Changed doc_id to approval_id
    try:
        approval = Approval.objects.select_related("request").get(id=approval_id, approver=request.user)
        query_docs = QueryDocument.objects.filter(request=approval.request)

        query_docs_data = [{"name": doc.document.name, "url": doc.document.url} for doc in query_docs]

        document_url = approval.request.document.url if approval.request.document else None
        if document_url:
            document_url = request.build_absolute_uri(document_url) 
        request_doc = approval.request

        previous_approvers = Approval.objects.filter(
            request=request_doc,
            status__in=["Approved", "Rejected"]
        ).values_list("approver__username", flat=True)

        data = {
            "success": True,
            "doc_number": approval.request.doc_number,
            "description": approval.request.description,
            "created_by": approval.request.created_by.username if approval.request.created_by else "Unknown",
            "created_at": localtime(approval.request.created_at).strftime("%Y-%m-%d %H:%M:%S") if approval.request.created_at else "N/A",
            "status": approval.status,
            "highlights": [highlight.point for highlight in approval.request.highlights.all()],
            "requirements": [
                {
                    "requirement_name": req.requirement_name,
                    "quantity": req.quantity,
                    "price": req.price,
                    "amount": req.amount,
                    "description": req.description
                }
                for req in approval.request.requirements.all()
            ],
            "comments": approval.comments if approval.comments else "No comments",
            "document_url": document_url,
            "previous_approvers": list(previous_approvers),
            "query_reply": approval.query_reply if approval.query_reply else "No query reply yet.",
            "query_documents": query_docs_data,
        }
        return JsonResponse(data)

    except Approval.DoesNotExist:
        return JsonResponse({"success": False, "error": "Approval not found"}, status=404)

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.decorators import login_required
from django.conf import settings

@login_required
def submit_approval(request):
    if request.method == "POST":
        approval_id = request.POST.get("approval_id")
        action = request.POST.get("action")
        comments = request.POST.get("comments", "").strip()

        try:
            approval = get_object_or_404(Approval, id=approval_id, approver=request.user)
            requestform=approval.request
            if action == "approve":
                approval.status = "Approved"
                approval.comments = comments
                approval.save()

                requestform.has_query=0
                requestform.save()

                # ✅ Get the next approver in sequence
                next_approval = Approval.objects.filter(
                    request=approval.request, status="On Hold"
                ).order_by("id").first()

                if next_approval:
                    next_approval.status = "Pending"
                    next_approval.save()
                    

                    # ✅ Send email to the next approver
                    email_template, created = EmailTemplate.objects.get_or_create(id=1)
                    email_context = {
                        "approver_name": next_approval.approver.username,
                        "doc_number": approval.request.doc_number,
                        "previous_approver": request.user.username,
                        "approval_link": "http://127.0.0.1:8000/approval_list/",
                        "company_logo": "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png",
                        "email_body": email_template.next_approver_body,

                    }
                    html_message = render_to_string("nx.html", email_context)
                    plain_message = strip_tags(html_message)

                    email = EmailMultiAlternatives(
                        subject=f"Approval Needed: {approval.request.doc_number}",
                        body=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[next_approval.approver.email],
                    )
                    email.attach_alternative(html_message, "text/html")
                    email.send(fail_silently=False)

                    messages.success(request, f"Request {approval.request.doc_number} approved! Next approval request sent.")

                else:
                    approval.request.status = "Approved"
                    approval.request.save()
                    print(approval.request.has_query)

                    recipients = [approval.request.created_by.email] + list(
                        approval.request.approvals.values_list("approver__email", flat=True)
                    )

                    email_context = {
                        "requester_name": approval.request.created_by.username,
                        "doc_number": approval.request.doc_number,
                        "company_logo": "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png",
                    }   
                    html_message = render_to_string("mm.html", email_context)
                    plain_message = strip_tags(html_message)

                    email = EmailMultiAlternatives(
                        subject=f"Approval Completed: {approval.request.doc_number}",
                        body=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=recipients,
                    )
                    email.attach_alternative(html_message, "text/html")
                    email.send(fail_silently=False)

                    messages.success(request, f"Request {approval.request.doc_number} fully approved!")

            elif action == "reject":
                approval.status = "Rejected"
                approval.comments = comments
                approval.save()
                
                requestform.has_query=0
                requestform.save()

                # ✅ Mark request as rejected & notify all previous approvers + requester
                approval.request.status = "Rejected"
                approval.request.save()

                recipients = [approval.request.created_by.email] + list(
                    approval.request.approvals.values_list("approver__email", flat=True)
                )

                email_context = {
                    "requester_name": approval.request.created_by.username,
                    "doc_number": approval.request.doc_number,
                    "rejected_by": request.user.username,
                    "rejection_reason": comments,
                    "company_logo": "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png"
                }
                html_message = render_to_string("rr.html", email_context)
                plain_message = strip_tags(html_message)

                email = EmailMultiAlternatives(
                    subject=f"Approval Request Rejected: {approval.request.doc_number}",
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipients,
                )
                email.attach_alternative(html_message, "text/html")
                email.send(fail_silently=False)

                messages.error(request, f"Request {approval.request.doc_number} has been rejected!")

        except Approval.DoesNotExist:
            messages.error(request, "Approval not found!")

        # ✅ Redirect to Approval List Page (No JSON response, just reloads the page)
        return redirect("approval_list")

    return redirect("approval_list")



@login_required
def approval_details(request):
    print("approval_detail")
    # ✅ Fetch only requests where the user has either Approved or Rejected (Exclude "Pending" and "On Hold")
    approvals = Approval.objects.filter(
        approver=request.user
    ).exclude(status__in=["Pending", "On Hold"]).select_related("request").order_by("-updated_at")
    #-request__created_at
    # Debugging: Print out fetched approvals
    print(f"User: {request.user.username} - Approvals Seen in Details Page AFTER FIX:")
    for approval in approvals:
        print(f"Doc ID: {approval.request.doc_number} | Status: {approval.status}")

    return render(request, "approval_details.html", {"approvals": approvals})

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from reportlab.lib.pagesizes import A4
from io import BytesIO
from reportlab.lib.utils import ImageReader
from django.shortcuts import get_object_or_404
from .models import RequestForm, Approval, UserProfile

def generate_approval_pdf(request, doc_id):
    # ✅ Get the request document
    approval_request = get_object_or_404(RequestForm, id=doc_id)

    # ✅ Create PDF response
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ✅ Load the company logo
    logo_url = "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png"
    logo = ImageReader(logo_url)
    p.drawImage(logo, 40, height - 80, width=100, height=50)  # Position at top-left

    # ✅ Company Details
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 30,"-------------------------------------------------------------------------------------------------------------------------------------------------------")

    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 50, "ACCSYS CONSULTING")
    
    p.setFont("Helvetica", 10)
    p.drawString(150, height - 65, "4/202, Second Floor, North Usman Road, Tnagar, Chennai, Tamil Nadu 600017")
    p.drawString(150, height - 80, "Email: info@accsysconsult.com | Phone: +91 72999 54249")
    p.drawString(40, height - 95,"-------------------------------------------------------------------------------------------------------------------------------------------------------")

    # ✅ Document Title
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 120, f"Approval Document - {approval_request.doc_number}")

    # ✅ Approval Details Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, height - 160, "Approval Details")

    p.setFont("Helvetica", 10)
    p.drawString(40, height - 180, f"Document ID: {approval_request.doc_number}")
    p.drawString(40, height - 200, f"Created By: {approval_request.created_by.username}")
    p.drawString(40, height - 220, f"Description: {approval_request.description}")

    # ✅ Requirements Table Header
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, height - 260, "Requirements")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, height - 280, "S.No")
    p.drawString(80, height - 280, "Requirement")
    p.drawString(200, height - 280, "Quantity")
    p.drawString(280, height - 280, "Price")
    p.drawString(360, height - 280, "Amount")

    # ✅ Add Requirements Data
    y_position = height - 300
    p.setFont("Helvetica", 10)
    for index, requirement in enumerate(approval_request.requirements.all(), start=1):
        p.drawString(40, y_position, str(index))
        p.drawString(80, y_position, requirement.requirement_name[:15])  # Limit name length
        p.drawString(200, y_position, str(requirement.quantity))
        p.drawString(280, y_position, f"{requirement.price:.2f}")
        p.drawString(360, y_position, f"{requirement.amount:.2f}")
        y_position -= 20

    # ✅ Approvers and Signatures Section
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y_position - 30, "Approvers & Signatures")

    y_position -= 50
    p.setFont("Helvetica", 10)
    for approval in approval_request.approvals.filter(status="Approved"):
        p.drawString(40, y_position, f"{approval.approver.username} - Approved on {approval.updated_at}")
        # Load and draw the signature (if exists)
        if approval.approver.userprofile.signature:
            signature = ImageReader(approval.approver.userprofile.signature.path)
            p.drawImage(signature, 300, y_position - 10, width=85, height=30)
        y_position -= 40

    # ✅ Footer
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(40, 30, "This document is auto-generated and does not require a physical signature.")

    # ✅ Finalize PDF
    p.showPage()
    p.save()
    buffer.seek(0)

    # ✅ Return the PDF response
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Approval_{approval_request.doc_number}.pdf"'
    return response

from .models import UserProfile


# @login_required
# def upload_signature(request):
    # profile, created = UserProfile.objects.get_or_create(user=request.user)  # ✅ Correct indentation

    # if request.method == "POST":
    #     form = SignatureUploadForm(request.POST, request.FILES, instance=profile)
    #     if form.is_valid():
    #         form.save()
    #         return redirect("document")  # ✅ Redirect to profile page after upload

    # else:
    #     form = SignatureUploadForm(instance=profile)

    # return render(request, "upload_signature.html", {"form": form})

@login_required
def upload_signature(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        if "signature" in request.FILES:
            profile.signature = request.FILES["signature"]
            profile.save()
            messages.success(request, "Signature uploaded successfully!")  # ✅ Add success message
            return redirect("document")
            return JsonResponse({"success": True})  # ✅ Return JSON response for AJAX reload
        
        messages.error(request, "Please upload a signature!")  # ✅ Add error message
        return redirect("upload_signature")
        return JsonResponse({"success": False, "error": "Please upload a signature!"})

    return render(request, "upload_signature.html", {"profile": profile})

@login_required
def clear_signature(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if profile.signature:
        profile.signature.delete()
        profile.signature = None
        profile.save()
        return JsonResponse({"success": True})  # ✅ Return success response

    return JsonResponse({"success": False, "error": "No signature found!"})

from io import BytesIO  # ✅ Import BytesIO for PDF generation
from django.http import HttpResponse
from reportlab.pdfgen import canvas  # ✅ Import ReportLab for PDF
from reportlab.lib.pagesizes import letter

@login_required
def download_history_pdf(request, history_type):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{history_type}_history.pdf"'

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f"{history_type.capitalize()} History Report")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 750, f"{history_type.capitalize()} History Report")

    pdf.setFont("Helvetica", 12)
    y = 720  # Start Y position

    # ✅ Handle both request history and approval history separately
    if history_type == "request":
        table_headers = ["Document ID                       Created By                                     Created At"]
        table_data = RequestForm.objects.all()

        for header in table_headers:
            pdf.drawString(100, y, header)
            y -= 20  # Move to the next line

        for record in table_data:
            pdf.drawString(100, y, str(record.doc_number))
            pdf.drawString(250, y, record.created_by.username)
            pdf.drawString(400, y, str(record.created_at.strftime("%Y-%m-%d %H:%M:%S")))
            y -= 20  # Move to the next line

            if y < 50:  # Page overflow
                pdf.showPage()
                y = 750

    elif history_type == "approval":
        table_headers = ["Document ID                       Approver                                 Status                                 Updated At"]
        table_data = Approval.objects.all()

        for header in table_headers:
            pdf.drawString(100, y, header)
            y -= 20  # Move to the next line

        for record in table_data:
            pdf.drawString(100, y, str(record.request.doc_number))
            pdf.drawString(250, y, record.approver.username)
            pdf.drawString(400, y, record.status)
            pdf.drawString(550, y, str(record.updated_at.strftime("%Y-%m-%d %H:%M:%S")))
            y -= 20  # Move to the next line

            if y < 50:  # Page overflow
                pdf.showPage()
                y = 750

    pdf.save()
    buffer.seek(0)
    response.write(buffer.read())

    return response

import pandas as pd

@login_required
def download_history_excel(request, history_type):
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{history_type}_history.xlsx"'

    if history_type == "request":
        table_data = RequestForm.objects.all()

        data = {
            "Document ID": [record.doc_number for record in table_data],
            "Created By": [record.created_by.username for record in table_data],
            "Created At": [record.created_at.strftime("%Y-%m-%d %H:%M:%S") for record in table_data],
        }

    elif history_type == "approval":
        table_data = Approval.objects.all()

        data = {
            "Document ID": [record.request.doc_number for record in table_data],
            "Approver": [record.approver.username for record in table_data],
            "Status": [record.status for record in table_data],
            "Updated At": [record.updated_at.strftime("%Y-%m-%d %H:%M:%S") for record in table_data],
        }

    df = pd.DataFrame(data)
    df.to_excel(response, index=False, engine="openpyxl")

    return response

def testing(req):
    print("table")
    return render(req, 'testing.html')
import json
# @login_required
# def submit_query(request):
    # if request.method == "POST":
    #     data = json.loads(request.body)
    #     approval_id = data.get("approval_id")
    #     doc_id = data.get("doc_id")
    #     query_comment = data.get("query_comment")

    #     try:
    #         request_form = get_object_or_404(RequestForm, id=doc_id)
    #         request_form.has_query = True
    #         request_form.query_comment = query_comment
    #         request_form.save()

    #         # ✅ Notify requester via email
    #         email_context = {
    #             "requester_name": request_form.created_by.username,
    #             "doc_number": request_form.doc_number,
    #             "query_comment": query_comment,
    #             "edit_link": f"http://127.0.0.1:8000/edit_request/{doc_id}/",
    #         }

    #         html_message = render_to_string("emails/query_notification.html", email_context)
    #         plain_message = strip_tags(html_message)

    #         email = EmailMultiAlternatives(
    #             subject=f"Clarification Needed – Document ID {request_form.doc_number}",
    #             body=plain_message,
    #             from_email=settings.DEFAULT_FROM_EMAIL,
    #             to=[request_form.created_by.email],
    #         )
    #         email.attach_alternative(html_message, "text/html")
    #         email.send(fail_silently=False)

    #         return JsonResponse({"success": True, "message": "Query submitted successfully!"})

    #     except Exception as e:
    #         return JsonResponse({"success": False, "error": str(e)})

    # return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# @login_required
# def submit_query(request):
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body)
#             approval_id = data.get("approval_id")
#             doc_id = data.get("doc_id")
#             query_comment = data.get("query_comment")

#             # ✅ Debugging: Print received data
#             print(f"Received Data: approval_id={approval_id}, doc_id={doc_id}, query_comment={query_comment}")

#             if not approval_id or not doc_id:
#                 return JsonResponse({"success": False, "error": "Missing approval or document ID"}, status=400)

#             # ✅ Fetch the RequestForm object
#             request_form = get_object_or_404(RequestForm, id=doc_id)
#             approval = get_object_or_404(Approval, id=approval_id, request=request_form)
            
#             # ✅ Save query details in the request form
#             request_form.has_query = True
#             request_form.query_comment = query_comment
#             request_form.save()

#             return JsonResponse({"success": True, "message": "Query submitted successfully!"})

#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)}, status=500)

#     return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


#old true
from .models import QueryDocument, RequestForm

@login_required
def submit_query(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            approval_id = data.get("approval_id")
            # doc_id = data.get("doc_id")
            query_comment = data.get("query_comment")
            uploaded_files = request.FILES.getlist("query_documents")  # Get multiple files

            print("Received Approval ID:", approval_id)
            print("Received Query Comment:", query_comment)
            print("Uploaded Files:", uploaded_files)  

            # ✅ Debug: Print received data
            # print(f"Received Data: approval_id={approval_id}, doc_id={doc_id}, query_comment={query_comment}")

            if not approval_id or not query_comment:
                return JsonResponse({"success": False, "error": "Missing required fields"}, status=400)

            # ✅ Fetch the request and approval
            approval = get_object_or_404(Approval, id=approval_id)
            # approval = get_object_or_404(Approval, id=approval_id, request=request_form)
            request_form = approval.request
            # ✅ Store query in the database
            request_form.doc_number
            print(request_form.doc_number,"hello testing")
            request_form.has_query = True
            # request_form.has_query = True  # Mark request as having a query
            request_form.query_comment = query_comment  # Save query comment
            request_form.save()
            #newwwwwwww
            if not uploaded_files:
                print("⚠️ No files received!")
            for file in uploaded_files:
                QueryDocument.objects.create(request=request_form, uploaded_by=request.user, document=file)

            # ✅ Notify the requester via email (Optional)
            requester_email = request_form.created_by.email
            email_context = {
                "requester_name": request_form.created_by.username,
                "doc_number": request_form.doc_number,
                "query_comment": query_comment,
                "company_logo": "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png"
            }
            html_message = render_to_string("emails/qnoti.html", email_context)
            plain_message = strip_tags(html_message)

            email = EmailMultiAlternatives(
                subject=f"Query Received for Document ID {request_form.doc_number}",
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[requester_email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)

            return JsonResponse({"success": True, "message": "Query submitted successfully!"})
        
        except Exception as e:
            print(f"Error: {e}")  # ✅ Debugging the error
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# @login_required
# def edit_request(request, doc_id):
#     doc_id = request.POST.get("doc_id")
#     request_form = get_object_or_404(RequestForm, id=doc_id)

#     if request.method == "POST":
#         request_form.description = request.POST.get("description")
#         request_form.document = request.FILES.get("document")
#         request_form.has_query = False  # Reset query status
#         request_form.query_comment = ""  # Clear previous query
#         request_form.save()

#         return redirect("request_history")

#     return render(request, "edit_request.html", {"request_form": request_form})
# @login_required
# def get_query_details(request, doc_id):
    try:
        request_form = get_object_or_404(RequestForm, id=doc_id)

        data = {
        "success": True,
        "doc_id": request_form.id,
        "query_comment": request_form.query_comment,
        "description": request_form.description,
        "highlights": list(request_form.highlightpoint_set.values_list("point", flat=True)),
        "requirements": list(request_form.requirement_set.values("name", "quantity", "price", "amount", "description")),
    }
        return JsonResponse(data)
    
        if not request_form.has_query:
            return JsonResponse({"success": False, "error": "No query found for this request."})

        return JsonResponse({"success": True, "query_comment": request_form.query_comment})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    
def get_query_details(request, approval_id):
    approval = get_object_or_404(Approval, id=approval_id)
    request_form = approval.request
    highlights=list(request_form.highlights.values_list("point", flat=True))

    data = {
        "success": True,
        "query_comment": approval.request.query_comment,  # ✅ Fetch query comment
        "description": approval.request.description,  # ✅ Get request details
        "highlights":highlights,
        "requirements": list(request_form.requirements.values('requirement_name', 'quantity', 'price', 'amount', 'description'))
        # "requirements": list(requirements)

        # "highlights": [highlight.point for highlight in request_form.highlights.all()],
        # "highlights": [highlight.point for highlight in approval.request.highlights.all()],
        #     "requirements": [
        #         {
        #             "requirement_name": req.requirement_name,
        #             "quantity": req.quantity,
        #             "price": req.price,
        #             "amount": req.amount,
        #             "description": req.description
        #         }
        #         for req in approval.request.requirements.all()]
        # "highlights": list(approval.request.highlightpoints.values_list("point", flat=True)),
        # "requirements": list(approval.request.requirement_set.values("requirement_name", "quantity", "price", "amount", "description"))
    }   

    return JsonResponse(data)

from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt
def submit_edited_request(request):
    if request.method == "POST":
        try:
            approval_id = request.POST.get("approval_id")
            uploaded_files = request.FILES.getlist("query_documents")  # ✅ Handle multiple files
            reply_text = request.POST.get("query_reply", "").strip()
            print(f"Received approval_id: {approval_id}, query_reply: {reply_text}")  # ✅ Debugging


        
            approval = get_object_or_404(Approval, id=approval_id)
            request_form = approval.request
            if reply_text:
                approval.query_reply = reply_text  # ✅ Save reply to the database
                approval.save()
                print("Query reply saved successfully!")

            # Update document if provided
            for file in uploaded_files:
                print(f"Saving File: {file.name}")  # ✅ Debugging
                QueryDocument.objects.create(
                    request=request_form,
                    uploaded_by=request.user,
                    document=file
                )

            # Update requirements
            requirements_data = request.POST.getlist("requirements[]")
            # Requirement.objects.filter(request=request_form).delete()

            for req_json in requirements_data:
                req_data = json.loads(req_json)
                row_number = req_data.get("row_number", None)  # Default if missing
                req_id = req_data.get("id", None)
                # row_number = req_data["row_number"]  # Get row number
                # old_requirement = Requirement.objects.filter(request=request_form, id=req_data["id"]).first()

                if req_id:
                    old_requirement = Requirement.objects.filter(request=request_form, id=req_id).first()
                    if old_requirement:
                        if old_requirement.requirement_name != req_data["name"]:
                                QueryUpdates.objects.create(
                                    approval=approval,
                                    field_name=f"Row {row_number} (Requirement Name)",
                                    old_value=old_requirement.requirement_name,
                                    new_value=req_data["name"]
                                )

                        # Check for changes
                        if old_requirement.quantity != int(req_data["quantity"]):
                            QueryUpdates.objects.create(
                                approval=approval,
                                field_name=f"Row {row_number} (Quantity)",
                                old_value=str(old_requirement.quantity),
                                new_value=req_data["quantity"]
                            )
                        if old_requirement.price != float(req_data["price"]):
                            QueryUpdates.objects.create(
                                approval=approval,
                                field_name=f"Row {row_number} (Price)",
                                old_value=str(old_requirement.price),
                                new_value=req_data["price"]
                            )
                        if old_requirement.amount != round(int(req_data["quantity"]) * float(req_data["price"]), 2):
                                QueryUpdates.objects.create(
                                    approval=approval,
                                    field_name=f"Row {row_number} (Amount)",
                                    old_value=str(old_requirement.amount),
                                    new_value=str(round(int(req_data["quantity"]) * float(req_data["price"]), 2))
                                )
                        if old_requirement.description != req_data["description"]:
                                QueryUpdates.objects.create(
                                    approval=approval,
                                    field_name=f"Row {row_number} (Description)",
                                    old_value=old_requirement.description,
                                    new_value=req_data["description"]
                                )

                        # Update the requirement
                        old_requirement.requirement_name = req_data["name"]
                        old_requirement.quantity = int(req_data["quantity"])
                        old_requirement.price = float(req_data["price"])
                        old_requirement.amount = round(int(req_data["quantity"]) * float(req_data["price"]), 2)
                        old_requirement.description = req_data["description"]
                        old_requirement.save()
                    else:
                            print(f"Requirement with ID {req_id} not found.")
            else:
                print("Missing requirement ID.")
                Requirement.objects.filter(request=request_form).delete()
                for req_json in requirements_data:
                    req_data = json.loads(req_json)
                    Requirement.objects.create(
                        request=request_form,
                        requirement_name=req_data["name"],
                        quantity=int(req_data["quantity"]),
                        price=float(req_data["price"]),
                        amount=round(int(req_data["quantity"]) * float(req_data["price"]), 2),
                        description=req_data["description"]
                    )
            request_form.has_query=2
            request_form.save()
            approval.status="pending"
            approval.save()
            return JsonResponse({"success": True, "message": "Request updated successfully!"})
        
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


#new test
# @login_required
# def submit_query(request):
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body)
#             approval_id = data.get("approval_id")
#             query_comment = data.get("query_comment")

#             if not approval_id or not query_comment:
#                 return JsonResponse({"success": False, "error": "Missing required fields"}, status=400)

#             approval = get_object_or_404(Approval, id=approval_id)
#             request_form = approval.request

#             # ✅ Mark request as having an unresolved query (has_query=1)
#             request_form.has_query = 1
#             request_form.query_comment = query_comment
#             request_form.save()

#             # ✅ Notify the requester via email
#             email_context = {
#                 "requester_name": request_form.created_by.username,
#                 "doc_number": request_form.doc_number,
#                 "query_comment": query_comment,
#                 "company_logo": "http://www.accsysconsult.com/wp-content/uploads/2023/05/Accsys-Consulting.png"
#             }
#             html_message = render_to_string("emails/qnoti.html", email_context)
#             plain_message = strip_tags(html_message)

#             email = EmailMultiAlternatives(
#                 subject=f"Query Received for Document ID {request_form.doc_number}",
#                 body=plain_message,
#                 from_email=settings.DEFAULT_FROM_EMAIL,
#                 to=[request_form.created_by.email],
#             )
#             email.attach_alternative(html_message, "text/html")
#             email.send(fail_silently=False)

#             return JsonResponse({"success": True, "message": "Query submitted successfully!"})
        
#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)})

#     return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# from django.views.decorators.csrf import csrf_exempt

# @login_required
# @csrf_exempt
# def submit_edited_request(request):
#     if request.method == "POST":
#         approval_id = request.POST.get("approval_id")
#         edited_document = request.FILES.get("document")

#         try:
#             approval = get_object_or_404(Approval, id=approval_id)
#             request_form = approval.request

#             # ✅ Update document if provided
#             if edited_document:
#                 request_form.document = edited_document

#             # ✅ Track requirement changes instead of deleting all
#             new_requirements = request.POST.getlist("requirements[]")
#             existing_requirements = {req.id: req for req in request_form.requirements.all()}

#             for req_json in new_requirements:
#                 req_data = json.loads(req_json)
#                 req_id = req_data.get("id")

#                 quantity = int(req_data["quantity"]) if req_data["quantity"] else 0
#                 price = float(req_data["price"]) if req_data["price"] else 0.00
#                 amount = round(quantity * price, 2)

#                 if req_id and int(req_id) in existing_requirements:
#                     existing_req = existing_requirements[int(req_id)]
#                     if (
#                         existing_req.quantity != quantity
#                         or existing_req.price != price
#                         or existing_req.amount != amount
#                         or existing_req.description != req_data["description"]
#                     ):
#                         # ✅ Track requirement changes
#                         RequirementRevision.objects.create(
#                             request=request_form,
#                             requirement_name=req_data["name"],
#                             old_quantity=existing_req.quantity,
#                             new_quantity=quantity,
#                             old_price=existing_req.price,
#                             new_price=price,
#                             old_amount=existing_req.amount,
#                             new_amount=amount,
#                             old_description=existing_req.description,
#                             new_description=req_data["description"],
#                         )

#                         # ✅ Update existing requirement
#                         existing_req.requirement_name = req_data["name"]
#                         existing_req.quantity = quantity
#                         existing_req.price = price
#                         existing_req.amount = amount
#                         existing_req.description = req_data["description"]
#                         existing_req.save()
#                 else:
#                     # ✅ Create new requirement
#                     Requirement.objects.create(
#                         request=request_form,
#                         requirement_name=req_data["name"],
#                         quantity=quantity,
#                         price=price,
#                         amount=amount,
#                         description=req_data["description"]
#                     )

#             # ✅ Mark query as resolved (has_query=2) & change status
#             request_form.has_query = 2
#             request_form.save()

#             approval.status = "Pending"
#             approval.save()

#             return JsonResponse({"success": True, "message": "Request updated successfully!"})
        
#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)})

#     return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# def get_query_details(request, approval_id):
    approval = get_object_or_404(Approval, id=approval_id)
    request_form = approval.request

    data = {
        "success": True,
        "query_comment": approval.request.query_comment,
        "description": approval.request.description,
        "highlights": list(request_form.highlights.values_list("point", flat=True)),
        "requirements": list(request_form.requirements.values('id', 'requirement_name', 'quantity', 'price', 'amount', 'description')),
        "requirement_changes": [
            {
                "requirement_name": rev.requirement_name,
                "old_quantity": rev.old_quantity,
                "new_quantity": rev.new_quantity,
                "old_price": rev.old_price,
                "new_price": rev.new_price,
                "old_amount": rev.old_amount,
                "new_amount": rev.new_amount,
                "old_description": rev.old_description,
                "new_description": rev.new_description,
                "changed_at": rev.changed_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for rev in request_form.requirement_revisions.all().order_by("changed_at")
        ]
    }

    return JsonResponse(data)
