import logging

from celery import shared_task
from telegram import Bot

from django.db.models import Case, When, F, Sum, IntegerField

from .texts import PAID_PUSH
from .models import CampaignUser, Campaign, BankAccount, CampaignContent

logger = logging.getLogger(__name__)


@shared_task
def check_to_calculate_campaign_user(campaign_users_ids):
    """
        check if admin approve all posts, calculate all banners price and sum
    """
    campaign_users = CampaignUser.objects.prefetch_related(
        'campaignpost_set'
        ).filter(
        id__in=campaign_users_ids,
        campaign__status__in=[Campaign.STATUS_APPROVED, Campaign.STATUS_CLOSE],
        receipt_date__isnull=True,
    ).annotate(
        has_tariif_posts=Sum(
            Case(
                When(campaignpost__campaign_content__view_type=CampaignContent.TYPE_VIEW_PARTIAL, then=1),
                default=0,
            ), output_field=IntegerField()
        ),
        approved_posts=Sum(
            Case(
                When(campaignpost__approve_time__isnull=False, then=1),
                default=0
            ), output_field=IntegerField()
        )
    ).filter(
        has_tariif_posts=F('approved_posts')
    )

    for campaign_user in campaign_users:
        campaign_user.receipt_price = campaign_user.calculate_price()
        campaign_user.save(update_fields=['updated_time', 'receipt_price'])


@shared_task
def send_paid_push(chat_id, bot_token, campaign_title, channels_tag):
    try:
        push_bot = Bot(token=bot_token)
        push_bot.send_message(chat_id=chat_id, text=PAID_PUSH % (campaign_title, channels_tag), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"send paid push failed user: {chat_id} error: {e}")


@shared_task
def delete_invalid_campaign_users():
    CampaignUser.objects.filter(channels__isnull=True).delete()

    for c in CampaignUser.objects.filter(campaignpost__isnull=True).distinct():
        c.channels.clear()
        c.delete()


@shared_task
def disable_campaign_by_max_view():
    """
        disable campaigns which even one of the contents views achieved max_view
        and don't read banner views until campaign end datetime.
    """
    campaigns = Campaign.objects.filter(
        status=Campaign.STATUS_APPROVED,
        is_enable=True
    ).only(
        'max_view'
    )

    for campaign in campaigns:
        contents_info = campaign.partial_contents_views()
        if any([cc['views'] >= campaign.max_view for cc in contents_info]):
            campaign.is_enable = False
            campaign.save(update_fields=['updated_time', 'is_enable'])
