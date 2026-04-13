from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from userauths.models import User, Profile
from userauths.email_utils import send_agent_approved_email
# Register your models here.
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'email', 'full_name']
    list_display = ['user_identity', 'contact_info', 'profile_meta', 'role_badge', 'approval_badge', 'agent_document_preview', 'approval_actions']
    list_filter = ['role', 'agent_approval_status', 'gender']
    actions = ['approve_selected_agents', 'reject_selected_agents']

    fieldsets = (
        ('Basic Info', {'fields': ('username', 'email', 'full_name', 'phone', 'gender', 'role')}),
        ('Agent Approval', {'fields': ('agent_approval_status', 'agent_rejection_reason')}),
    )

    def agent_document_preview(self, obj):
        try:
            profile = obj.profile
        except Profile.DoesNotExist:
            profile = None

        if profile and profile.identity_image:
            return format_html('<a class="doc-link" href="{}" target="_blank">View document</a>', profile.identity_image.url)
        return format_html('<span class="chip chip-muted">{}</span>', 'No document')

    agent_document_preview.short_description = 'Agent Document'

    def user_identity(self, obj):
        initials_source = obj.full_name or obj.username or 'U'
        initials = ''.join(part[0] for part in initials_source.split()[:2]).upper() or 'U'
        return format_html(
            '<div class="user-cell">'
            '  <span class="user-avatar">{}</span>'
            '  <div>'
            '    <div class="user-name">{}</div>'
            '    <div class="user-username">@{}</div>'
            '  </div>'
            '</div>',
            initials,
            obj.full_name or obj.username,
            obj.username,
        )
    user_identity.short_description = 'User'
    user_identity.admin_order_field = 'username'

    def contact_info(self, obj):
        email = obj.email or '-'
        phone = obj.phone or '-'
        return format_html(
            '<div class="contact-stack">'
            '  <div><strong>Email:</strong> {}</div>'
            '  <div><strong>Phone:</strong> {}</div>'
            '</div>',
            email,
            phone,
        )
    contact_info.short_description = 'Contact'

    def profile_meta(self, obj):
        gender = obj.gender.title() if obj.gender else 'Not set'
        return format_html('<span class="chip chip-muted">{}</span>', gender)
    profile_meta.short_description = 'Gender'
    profile_meta.admin_order_field = 'gender'

    def role_badge(self, obj):
        role = (obj.role or 'user').lower()
        role_class = 'chip-role-agent' if role == 'agent' else 'chip-role-customer'
        return format_html('<span class="chip {}">{}</span>', role_class, role.title())
    role_badge.short_description = 'Role'
    role_badge.admin_order_field = 'role'

    def approval_badge(self, obj):
        status = (obj.agent_approval_status or 'pending').lower()
        status_class_map = {
            'approved': 'chip-status-approved',
            'rejected': 'chip-status-rejected',
            'pending': 'chip-status-pending',
        }
        status_class = status_class_map.get(status, 'chip-status-pending')
        return format_html('<span class="chip {}">{}</span>', status_class, status.title())
    approval_badge.short_description = 'Approval'
    approval_badge.admin_order_field = 'agent_approval_status'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:user_id>/approve-agent/',
                self.admin_site.admin_view(self.approve_agent_view),
                name='userauths_user_approve_agent',
            ),
            path(
                '<int:user_id>/reject-agent/',
                self.admin_site.admin_view(self.reject_agent_view),
                name='userauths_user_reject_agent',
            ),
        ]
        return custom_urls + urls

    def approval_actions(self, obj):
        if obj.role != 'agent':
            return format_html('<span class="chip chip-muted">{}</span>', 'Not required')

        if obj.agent_approval_status == 'approved':
            reject_url = reverse('admin:userauths_user_reject_agent', args=[obj.pk])
            return format_html('<a class="crud-btn crud-btn-delete" href="{}">Reject</a>', reject_url)

        approve_url = reverse('admin:userauths_user_approve_agent', args=[obj.pk])
        reject_url = reverse('admin:userauths_user_reject_agent', args=[obj.pk])
        return format_html(
            '<a class="crud-btn crud-btn-edit" href="{}">Approve</a> '
            '<a class="crud-btn crud-btn-delete" href="{}">Reject</a>',
            approve_url,
            reject_url,
        )

    approval_actions.short_description = 'Actions'

    def approve_agent_view(self, request, user_id):
        user = User.objects.filter(pk=user_id, role='agent').first()
        if not user:
            self.message_user(request, 'Agent account not found.', level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:userauths_user_changelist'))

        user.agent_approval_status = 'approved'
        user.agent_rejection_reason = ''
        user.save(update_fields=['agent_approval_status', 'agent_rejection_reason'])
        email_sent = send_agent_approved_email(user)
        if email_sent:
            self.message_user(request, f'Agent {user.username} approved successfully and notified by email.', level=messages.SUCCESS)
        else:
            self.message_user(request, f'Agent {user.username} approved, but email notification failed.', level=messages.WARNING)
        return HttpResponseRedirect(reverse('admin:userauths_user_changelist'))

    def reject_agent_view(self, request, user_id):
        user = User.objects.filter(pk=user_id, role='agent').first()
        if not user:
            self.message_user(request, 'Agent account not found.', level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:userauths_user_changelist'))

        user.agent_approval_status = 'rejected'
        if not user.agent_rejection_reason:
            user.agent_rejection_reason = 'Rejected by admin.'
        user.save(update_fields=['agent_approval_status', 'agent_rejection_reason'])
        self.message_user(request, f'Agent {user.username} rejected.', level=messages.WARNING)
        return HttpResponseRedirect(reverse('admin:userauths_user_changelist'))

    @admin.action(description='Approve selected agent accounts')
    def approve_selected_agents(self, request, queryset):
        agents = list(queryset.filter(role='agent'))
        for agent in agents:
            agent.agent_approval_status = 'approved'
            agent.agent_rejection_reason = ''
            agent.save(update_fields=['agent_approval_status', 'agent_rejection_reason'])
            send_agent_approved_email(agent)

        self.message_user(request, f'{len(agents)} agent account(s) approved and notification emails attempted.')

    @admin.action(description='Reject selected agent accounts')
    def reject_selected_agents(self, request, queryset):
        updated = queryset.filter(role='agent').update(agent_approval_status='rejected')
        self.message_user(request, f'{updated} agent account(s) rejected.')


class ProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'full_name']
    list_display = ['user', 'full_name', 'verified', 'identity_type', 'identity_image']

admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
