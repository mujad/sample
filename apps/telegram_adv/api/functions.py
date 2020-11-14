from django.db.models import Sum, Case, When, Max, F
from django.db.models.functions import Coalesce

from apps.telegram_adv.models import CampaignContent


def get_campaign_publisher_views(campaign_id):
    """
        return partial contents views for a specific campaign

    """
    report = []
    for content in CampaignContent.objects.prefetch_related(
        'campaignpost_set__logs'
    ).filter(
        campaign_id=campaign_id,
        view_type=CampaignContent.TYPE_VIEW_PARTIAL
    ).order_by(
        'id'
    ):
        views = content.campaignpost_set.filter(
            is_enable=True
        ).annotate(
            post_views=Case(
                When(
                    views__isnull=True, then=Max('logs__banner_views')
                ), default=F('views')
            )
        ).aggregate(
            views=Coalesce(Sum('post_views'), 0)
        )['views']
        report.append({'content': content.id, 'views': views})

    return report


def test_create_campaign(campaign):
    """
        create contents in their mother channels then forward to a test_user
            1- create a push object for test_user with it's telegram channels
            2- try to render contents in their mother channels then forward to test_user

    """
    pass

