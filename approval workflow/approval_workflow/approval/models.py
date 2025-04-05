from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now  # Import this to get the current timestamp
from django.core.exceptions import ValidationError

def validate_file_size(value):
    max_size = 5 * 1024 * 1024  # 5MB limit
    if value.size > max_size:
        raise ValidationError("File size must be less than 5MB!")
    
class RequestForm(models.Model):
    doc_number = models.CharField(max_length=50, unique=True, blank=False, null=True)  # Removed `null=True`
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=False, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requests",null=True)
    created_at = models.DateTimeField(default=now)  # Add this line  # Ensuring it is required
    document = models.FileField(upload_to="uploaded_documents/", null=True, blank=True, validators=[validate_file_size])
    has_query = models.IntegerField(default=0) 
    # has_query = models.BooleanField(default=False)  # ✅ Marks if a query is raised
    query_comment = models.TextField(null=True, blank=True)  # ✅ Stores the approver's query
    update_history = models.JSONField(null=True, blank=True)  # ✅ Stores change logs (Old → New)

    def __str__(self):
        return f"{self.doc_number} - {self.date}"

class HighlightPoint(models.Model):
    request = models.ForeignKey(RequestForm, on_delete=models.CASCADE, related_name="highlights")
    point = models.TextField()

class Requirement(models.Model):
    request = models.ForeignKey(RequestForm, on_delete=models.CASCADE, related_name="requirements")
    requirement_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=now)
    def __str__(self):
        return f"{self.requirement_name} ({self.quantity})"



# class RequirementRevision(models.Model):
#     request = models.ForeignKey(RequestForm, on_delete=models.CASCADE, related_name="requirement_revisions")
#     requirement_name = models.CharField(max_length=255)
#     old_quantity = models.IntegerField(null=True, blank=True)
#     new_quantity = models.IntegerField(null=True, blank=True)
#     old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     new_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     old_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     new_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     old_description = models.TextField(null=True, blank=True)
#     new_description = models.TextField(null=True, blank=True)
#     changed_at = models.DateTimeField(auto_now_add=True)


class Approval(models.Model):
    request = models.ForeignKey(RequestForm, on_delete=models.CASCADE, related_name="approvals")
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending'
    )
    comments = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    query_reply = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"{self.approver.username} - {self.status}"
    

from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    signature = models.ImageField(upload_to="signatures/", blank=True, null=True)  # ✅ Store signature image
    is_deleted = models.BooleanField(default=False)  # ✅ Add this field

    def __str__(self):
        return f"{self.user.username}'s Profile"

class EmailTemplate(models.Model):
    first_approver_body = models.TextField(default="Default first approver email content.")
    next_approver_body = models.TextField(default="Default next approver email content.")

    def __str__(self):
        return "Email Template"

class QueryDocument(models.Model):
    request = models.ForeignKey(RequestForm, on_delete=models.CASCADE, related_name="query_documents")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.FileField(upload_to="query_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class QueryUpdates(models.Model):
    approval = models.ForeignKey(Approval, on_delete=models.CASCADE, related_name="query_updates")
    field_name = models.CharField(max_length=255)  # E.g., "Row 2 (Price)"
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True)