from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.accounts.models import AuthActivityLog, SuperAdminExport, SuperAdminNotification, User, Feedback

# Register your models here.

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Feedback)


@admin.register(AuthActivityLog)
class AuthActivityLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'username', 'user', 'ip_address', 'path', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('username', 'details', 'path', 'ip_address')
    readonly_fields = ('user', 'username', 'event_type', 'ip_address', 'user_agent', 'path', 'details', 'created_at')


@admin.register(SuperAdminNotification)
class SuperAdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'is_read', 'created_by', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message')


@admin.register(SuperAdminExport)
class SuperAdminExportAdmin(admin.ModelAdmin):
    list_display = ('report_name', 'export_format', 'status', 'requested_by', 'created_at')
    list_filter = ('export_format', 'status', 'created_at')
    search_fields = ('report_name', 'file_name', 'error_message')

