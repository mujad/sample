from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=PushText)
def base_push_post_save(sender, instance, created, **kwargs):
    if not instance.telegram_file_hash:
        upload_file.apply_async(args=[instance.id, True], countdown=1)
