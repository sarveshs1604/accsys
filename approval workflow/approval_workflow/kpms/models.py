import random
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now


def generate_doc_number():
    while True:
        random_number = str(random.randint(1000000, 9999999))  # Generate a 7-digit number
        if not BookingForm.objects.filter(doc_number=random_number).exists():
            return random_number  # Return only if unique

class BookingForm(models.Model):
    STATUS_CHOICES = [
        ("In Progress", "In Progress"),
        ("Raise Query", "Raise Query"),
        ("Validation In Progress", "Validation In Progress"),
        ("Client Validation", "Client Validation"),
        ("Validation", "Validation"),
        ("Closed", "Closed"),
    ]
    vendor_name = models.CharField(max_length=255)
    reference_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    doc_number = models.CharField(max_length=50, unique=True)
    invoice_value = models.DecimalField(max_digits=12, decimal_places=2)

    document_type = models.ForeignKey('DocumentType', on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    special_instructions = models.TextField(blank=True, null=True)
    validator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_forms"
    )
    # profit_center = models.CharField(max_length=100, blank=True, null=True)
    # taxable_value = models.DecimalField(max_digits=12, decimal_places=2)
    # igst_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    # cgst_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    # sgst_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    # documents = models.FileField(upload_to="uploads/", blank=True, null=True)

    assignees = models.ManyToManyField(User, related_name="assigned_bookings")

    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='bookings_created',
        default=None
    )
    created_at = models.DateTimeField(default=now, editable=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="In Progress")
    updated_fields = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.vendor_name} - {self.doc_number}"

class DocumentType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Document(models.Model):
    booking = models.ForeignKey(BookingForm, related_name="documents", on_delete=models.CASCADE)
    file = models.FileField(upload_to="documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
# from django.utils.timezone import now

class UpdateLog(models.Model):
    form = models.ForeignKey('bookingform', on_delete=models.CASCADE, related_name='updates')
    field_name = models.CharField(max_length=255)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.field_name} updated by {self.updated_by} on {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
class QueryDocument(models.Model):
    """ Model to store multiple documents related to a query. """
    query = models.ForeignKey("QueryLog", related_name="documents", on_delete=models.CASCADE)  # ✅ Use a string reference
    file = models.FileField(upload_to="query_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class QueryLog(models.Model):
    form = models.ForeignKey(BookingForm, related_name="query_logs", on_delete=models.CASCADE)
    assignee = models.ForeignKey(User, related_name="raised_queries", on_delete=models.CASCADE)
    query_comment = models.TextField()  # Assignee's Query Comment
    updated_by = models.ForeignKey(User, related_name="resolved_queries", on_delete=models.CASCADE, null=True, blank=True)  # Client resolving the query
    updated_fields = models.JSONField(default=dict, blank=True)  # Stores old → new values
    resolution_comment = models.TextField(blank=True, null=True)  # Client's Resolution Comment
    resolved_at = models.DateTimeField(auto_now_add=True)  # Timestamp

    def __str__(self):
        return f"Query by {self.assignee} resolved by {self.updated_by} on {self.resolved_at}"
    
class ClientAssigneeMapping(models.Model):
    client = models.OneToOneField(User, on_delete=models.CASCADE, related_name="assignee_mapping")
    assignees = models.ManyToManyField(User, related_name="mapped_clients")
    
    VALIDATION_CHOICES = [
        ("Validation 1", "Validation 1"),
        ("Validation 2", "Validation 2"),
        ("Validation 3", "Validation 3"),
    ]
    validation_process = models.CharField(max_length=20, choices=VALIDATION_CHOICES, default="Validation 1")

    def __str__(self):
        return f"{self.client.username} - {self.validation_process}"
    