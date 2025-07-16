from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import os

from .models import CrewSheet

@receiver(post_delete, sender=CrewSheet)
def delete_crew_sheet_image(sender, instance, **kwargs):
    """Delete the image file when a CrewSheet instance is deleted."""
    # Delete the image file if it exists
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)
