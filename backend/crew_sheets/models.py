from django.db import models
from django.conf import settings
import uuid

class CrewSheet(models.Model):
    """Model for storing uploaded crew sheets and their extracted data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='crew_sheets')
    name = models.CharField(max_length=255, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='crew_sheets/')
    
    # Extracted data stored as JSON
    extracted_data = models.JSONField(null=True, blank=True)
    
    # Processing status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    date_processed = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name or 'Unnamed'} - {self.date_uploaded.strftime('%Y-%m-%d %H:%M')}"
