from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.agency.models import Employee
from apps.telephony.models import TelephonyLink

@receiver(post_save, sender=Employee)
def ensure_telephony_link(sender, instance: Employee, created: bool, **kwargs):
    if created:
        TelephonyLink.objects.get_or_create(employee=instance)
