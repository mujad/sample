from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect, render

from apps.push.models import CampaignPush, CampaignPushUser
from apps.utils.admin import ReadOnlyAdmin, CampaignFilter, ReadOnlyTabularInline


def push_text_admin_submit(request, push_id):
    pass


@admin.register(PushText)
class PushTextAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_time']
    change_form_template = 'admin/push/change_form_with_push.html'

    def response_change(self, request, obj):
        if 'new_push' in request.POST:
            return redirect('admin:push_text', obj.pk)

        return super().response_change(request, obj)

    def get_urls(self):
        return [
                   path('pre_push_text/<int:push_id>/', self.admin_site.admin_view(push_text_admin_submit),
                        name='push_text'),
               ] + super().get_urls()


class PushUserInline(ReadOnlyTabularInline):
    fields = ('user', 'is_delivered')
    readonly_fields = ('is_delivered',)
    model = CampaignPushUser
    extra = 0

    def is_delivered(self, obj):
        return obj.is_delivered()
    is_delivered.boolean = True


@admin.register(CampaignPush)
class PushCampaignAdmin(ReadOnlyAdmin):
    list_display = ('campaign', 'status', 'channels', 'confirmed_channels')
    list_select_related = ('campaign',)
    filter_horizontal = ('publishers',)
    inlines = (PushUserInline,)
    list_filter = [
        ('campaign', CampaignFilter)
    ]

    def channels(self, obj):
        return ", ".join(obj.publishers.values_list('tag', flat=True))

    def confirmed_channels(self, obj):
        return ", ".join(obj.confirmed_channels().values_list('channels__tag', flat=True)) or "-"

    def is_delivered(self, obj):
        return obj.is_delivered()
    is_delivered.boolean = True
