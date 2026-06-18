from django.contrib import admin
from .models import Inquiry, Lead, CallLog, FollowUp

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile_number', 'email', 'city', 'course_interest', 'source', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'source', 'created_at')
    search_fields = ('full_name', 'mobile_number', 'email', 'city')
    ordering = ('-created_at',)

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('inquiry', 'assigned_telecaller', 'status', 'priority', 'next_followup_date', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('inquiry__full_name', 'inquiry__mobile_number', 'notes')
    ordering = ('-created_at',)

@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ('lead', 'call_status', 'call_duration', 'created_by', 'call_date')
    list_filter = ('call_status', 'call_date')
    search_fields = ('lead__inquiry__full_name', 'lead__inquiry__mobile_number', 'remarks')
    ordering = ('-call_date',)

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('lead', 'followup_date', 'next_followup_date', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'followup_date')
    search_fields = ('lead__inquiry__full_name', 'response')
    ordering = ('-followup_date',)
