from django.contrib import admin
from .models import Inquiry, Lead, CallLog, FollowUp, LeadImport, LeadNote, LeadActivity, ImportErrorLog, CounselingSession, InquiryCallStatusHistory

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile_number', 'email', 'city', 'course_interest', 'source', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'source', 'created_at')
    search_fields = ('full_name', 'mobile_number', 'email', 'city')
    ordering = ('-created_at',)

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('inquiry', 'assigned_telecaller', 'assigned_counselor', 'status', 'counselor_status', 'priority', 'next_followup_date', 'created_at')
    list_filter = ('status', 'counselor_status', 'priority', 'created_at')
    search_fields = ('inquiry__full_name', 'inquiry__mobile_number', 'notes')
    ordering = ('-created_at',)

@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ('lead', 'call_status', 'call_duration', 'created_by', 'call_date')
    list_filter = ('call_status', 'call_date')
    search_fields = ('lead__inquiry__full_name', 'lead__inquiry__mobile_number', 'remarks')
    ordering = ('-call_date',)


@admin.register(InquiryCallStatusHistory)
class InquiryCallStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('inquiry', 'call_status', 'updated_by', 'created_at')
    list_filter = ('call_status', 'created_at')
    search_fields = ('inquiry__full_name', 'inquiry__mobile_number', 'remarks', 'updated_by__username')
    ordering = ('-created_at',)

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('lead', 'followup_date', 'next_followup_date', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'followup_date')
    search_fields = ('lead__inquiry__full_name', 'response')
    ordering = ('-followup_date',)


@admin.register(LeadImport)
class LeadImportAdmin(admin.ModelAdmin):
    list_display = ('uploaded_by', 'file', 'total_records', 'successful_records', 'duplicate_records', 'failed_records', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('uploaded_by__username', 'file')
    ordering = ('-created_at',)


@admin.register(LeadNote)
class LeadNoteAdmin(admin.ModelAdmin):
    list_display = ('lead', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('lead__inquiry__full_name', 'note', 'created_by__username')
    ordering = ('-created_at',)


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ('lead', 'activity_type', 'description', 'created_by', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('lead__inquiry__full_name', 'description', 'created_by__username')
    ordering = ('-created_at',)


@admin.register(ImportErrorLog)
class ImportErrorLogAdmin(admin.ModelAdmin):
    list_display = ('lead_import', 'row_number', 'error_message', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('lead_import__uploaded_by__username', 'error_message')
    ordering = ('lead_import', 'row_number')


@admin.register(CounselingSession)
class CounselingSessionAdmin(admin.ModelAdmin):
    list_display = ('lead', 'counselor', 'session_date', 'next_action', 'created_at')
    list_filter = ('session_date', 'created_at')
    search_fields = ('lead__inquiry__full_name', 'counselor__username', 'discussion_notes', 'next_action')
    ordering = ('-session_date',)
