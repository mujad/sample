from jsonfield import JSONField

from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Case, When, F, IntegerField, Max, Sum

from apps.utils.url_encoder import UrlEncoder

url_encoder = UrlEncoder()


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=TelegramChannel.STATUS_CONFIRMED)


class TelegramChannel(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('update time'), auto_now=True)
    tag = models.CharField(_('channel tag'), max_length=32)
    title = models.CharField(_('channel title'), max_length=255, blank=True)
    channel_id = models.BigIntegerField(_('channel id'), unique=True, null=True, blank=True)
    member_no = models.PositiveIntegerField(_('channel members'), null=True, blank=True)
    view_efficiency = models.PositiveIntegerField(_('view efficiency'), default=1000)

    admins = models.ManyToManyField('telegram_user.TelegramUser', blank=True)

    objects = models.Manager()
    live = LiveManager()

    class Meta:
        db_table = 'telegram_channel'

    def __str__(self):
        return f"#{self.id} - {self.tag}"


class Campaign(models.Model):
    STATUS_WAITING = 'waiting'
    STATUS_TEST = 'test'
    STATUS_APPROVED = 'approved'
    STATUS_CLOSE = 'close'
    STATUS_REJECTED = 'rejected'

    STATUS_TYPES = (
        (STATUS_WAITING, _('waiting')),
        (STATUS_TEST, _('test')),
        (STATUS_APPROVED, _('approved')),
        (STATUS_CLOSE, _('close')),
        (STATUS_REJECTED, _('rejected'))
    )
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    title = models.CharField(_('title'), max_length=150)
    max_view = models.PositiveIntegerField(_('max view'))
    is_enable = models.BooleanField(_("is enable"), default=False)
    start_datetime = models.DateTimeField(_('start datetime'))
    end_datetime = models.DateTimeField(_('end datetime'))

    publishers = models.ManyToManyField(TelegramChannel, through="CampaignPublisher")

    class Meta:
        db_table = "campaigns"
        ordering = ['-id']

    def __str__(self):
        return f'c_{self.id} - {self.title}'

    def url_encode(self):
        return url_encoder.encode_id(self.id)

    def total_contents_views(self):
        """
        max Campaign total contents views
        * views is same for all CampaignUser then max of views if enough
            1 - their views field if is not null
            2 - else last CampaignPostLog of that CampaignPost views

        :return: list of Content name and it's views
        """
        return list(self.contents.filter(
            view_type=CampaignContent.TYPE_VIEW_TOTAL,
            campaignpost__is_enable=True,
        ).annotate(
            views=Max(
                Case(
                    When(campaignpost__views__isnull=False, then=F("campaignpost__views")),
                    output_field=IntegerField(),
                    default=F("campaignpost__logs__banner_views"),
                ), output_field=IntegerField()
            )
        ).values("id", "display_text", "views"))

    def partial_contents_views(self):
        """
        Sum Campaign partial contents views
            condition CampaignPost views:
                1 - their views field if is not null
                2 - else last CampaignPostLog of that CampaignPost views
            then:
                Sum views together

        :return: list of Content name and it's views
        """

        campaign_contents_info = {
            x['id']: dict(text=x['display_text'], views=x['views'])
            for x in self.contents.filter(
                view_type=CampaignContent.TYPE_VIEW_PARTIAL,
                campaignpost__is_enable=True,
                campaignpost__views__isnull=False,
            ).annotate(
                views=Sum("campaignpost__views")
            ).values("id", "display_text", "views")
        }

        for cp in CampaignPost.objects.select_related('campaign_content').filter(
                campaign_content__campaign=self,
                campaign_content__view_type=CampaignContent.TYPE_VIEW_PARTIAL,
                is_enable=True,
                views__isnull=True,
        ):
            views = getattr(cp.logs.last(), 'banner_views', 0)
            cc = cp.campaign_content
            if cc.id in campaign_contents_info:
                campaign_contents_info[cc.id]['views'] += views
            else:
                campaign_contents_info[cc.id] = dict(id=cc.id, display_text=cc.display_text, views=views)

        return list(campaign_contents_info.values())

    def shortlink_views(self):
        links = list(
            self.contents.filter(
                links__isnull=False
            ).prefetch_related(
                "links__short_links__logs"
            ).values(
                'id', 'display_text'
            ).annotate(
                ip_count=Sum('links__short_links__logs__ip_count'),
                hit_count=Sum('links__short_links__logs__hit_count')
            )
        )
        return links

    @property
    def report_link(self):
        return settings.BASE_REPORT_URL + reverse('advertiser-report', args=[self.url_encode()])

    @staticmethod
    def url_decode(decode_string):
        return url_encoder.decode_id(decode_string)


class CampaignContent(models.Model):
    TYPE_VIEW_TOTAL = 'total'
    TYPE_VIEW_PARTIAL = 'partial'

    VIEW_TYPES = (
        (TYPE_VIEW_TOTAL, _('total')),
        (TYPE_VIEW_PARTIAL, _('partial')),
    )

    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    display_text = models.CharField(_('display text'), max_length=150)
    content = models.TextField(_('content'), blank=True)
    extra_data = JSONField(editable=False)
    view_type = models.CharField(_('view type'), max_length=7, choices=VIEW_TYPES)
    message_id = models.PositiveIntegerField(_('message id'), null=True, blank=True)
    post_link = models.URLField(
        _('post link'), null=True, blank=True,
        validators=[
            RegexValidator(
                regex=r"(?:https?:)?//(?:t(?:elegram)?\.me|telegram\.org)/[a-zA-Z_]+/[0-9]+(/([0-9]+)?/?)?",
                message=_("this link is not a valid telegram post link")
            )
        ]
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="contents")

    class Meta:
        db_table = "campaigns_contents"

    def __str__(self):
        return f"c_{self.campaign_id} - {self.display_text}"

    def clean(self):
        if self.content:
            count_markup_chars = [self.content.count('*'), self.content.count('_'), self.content.count('`')]
            if any(count for count in count_markup_chars if count % 2 != 0):
                raise ValidationError(
                    _("your template has invalid markdown tags check your text where has: [* ` _ ```]"),
                    code='invalid'
                )

        if all([self.content, self.is_sticker]) or not any([self.content, self.is_sticker]):
            raise ValidationError(_('one of content or is_sticker should fill'), code='invalid')


class CampaignUserManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'campaign'
        ).filter(
            channels__isnull=False,
            campaignpost__is_enable=True,
            campaignpost__campaign_content__view_type=CampaignContent.TYPE_VIEW_PARTIAL
        ).distinct()


class CampaignUser(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    receipt_price = models.PositiveIntegerField(_('receipt price'), null=True, blank=True)
    receipt_date = models.DateField(_('receipt date'), null=True, blank=True)
    sheba_number = models.CharField(_('sheba number'), max_length=26)

    objects = models.Manager()
    report = CampaignUserManager()

    class Meta:
        db_table = "campaigns_users"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_receipt_date = self.receipt_date

    def __str__(self):
        return f"{self.campaign} user: `{self.user}`"

    @property
    def paid(self):
        return bool(self.receipt_date)


class CampaignPost(models.Model):
    def shot_directory_path(self, filename):
        ext = filename.split('.')[-1]
        return f'shot_{self.id}.{ext}'

    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    message_id = models.PositiveIntegerField(_('message id'), null=True)
    views = models.PositiveIntegerField(null=True, blank=True)

    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        db_table = "campaigns_posts"

    def _screen_preview(self):
        if not self.screen_shot:
            return '-'

        elif self.screen_shot == 'no_shot':
            return format_html('<img src="/static/admin/img/icon-deletelink.svg" alt="no_video">')

        else:
            return mark_safe(
                '<a href={} class="nowrap" onclick="return windowpop(this.href, this.width, this.height)"><span class="viewlink" title="View Screenshot"></span>{}</a>'.format(
                    self.screen_shot.url,
                    self.screen_time.strftime('%y/%m/%d %H:%M')
                )
            )


