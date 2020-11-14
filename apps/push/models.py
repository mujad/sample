from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.telegram_adv.models import TelegramChannel, Campaign, CampaignUser


class CampaignPushUser(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    message_id = models.PositiveIntegerField(_('message id'), null=True, editable=False)

    campaign_push = models.ForeignKey("CampaignPush", on_delete=models.PROTECT, related_name="user_pushes")
    user = models.ForeignKey("TelegramUser", on_delete=models.PROTECT, related_name="pushes")

    def __str__(self):
        return f"user: {self.user_id} push_id: {self.campaign_push_id}"

    def is_delivered(self):
        return self.message_id is not None


class CampaignPush(models.Model):
    STATUS_SENT = 0
    STATUS_RECEIVED = 1
    STATUS_REJECTED = 2
    STATUS_EXPIRED = 3
    STATUS_TYPES = (
        (STATUS_SENT, _('sent')),
        (STATUS_RECEIVED, _('received')),
        (STATUS_REJECTED, _('rejected')),
        (STATUS_EXPIRED, _('expired')),
    )
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    status = models.SmallIntegerField(_('status'), choices=STATUS_TYPES, default=STATUS_SENT)

    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="pushes")
    users = models.ManyToManyField("TelegramUser", through=CampaignPushUser)
    publishers = models.ManyToManyField(TelegramChannel)

    def __str__(self):
        return f"campaign: #{self.campaign_id} id: {self.id} status: {self.status}"

    def confirmed_channels(self):
        return CampaignUser.objects.filter(
            campaign_id=self.campaign_id,
            channels__in=self.publishers.values_list('id', flat=True)
        ).distinct()

    def __base_remain_push_data(self):
        return CampaignPublisher.objects.select_related(
            'publisher__sheba'
        ).filter(
            campaign_id=self.campaign_id,
            publisher_id__in=self.publishers.exclude(
                id__in=self.confirmed_channels().values_list('channels__id', flat=True)
            ).values_list('id', flat=True)
        ).distinct()

    def has_push_data(self):
        return self.__base_remain_push_data().exists()

    def get_push_data(self):
        data = {}
        for publisher in self.__base_remain_push_data():
            data.setdefault(
                publisher.publisher.sheba.sheba_number, []
            ).append(
                {
                    'tag': publisher.publisher.tag,
                    'id': publisher.publisher.id,
                    'tariff': publisher.tariff
                }
            )
        return data
