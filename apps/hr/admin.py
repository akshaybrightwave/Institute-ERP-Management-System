from django.contrib import admin

from .models import (
    Candidate,
    CandidateActivity,
    CandidateNote,
    FollowUp,
    Interview,
    PlacementActivity,
    PlacementCompany,
    PlacementDrive,
    PlacementInterview,
    PlacementOffer,
    PlacementStudentAssignment,
)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile', 'applying_position', 'assigned_hr', 'status', 'date_added')
    list_filter = ('status', 'source', 'department')
    search_fields = ('full_name', 'mobile', 'email', 'applying_position')


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'follow_up_date', 'follow_up_time', 'follow_up_type', 'outcome', 'completed')
    list_filter = ('follow_up_type', 'outcome', 'completed')
    search_fields = ('candidate__full_name', 'candidate__mobile')


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'interview_type', 'interviewer', 'date', 'time', 'decision')
    list_filter = ('interview_type', 'decision')
    search_fields = ('candidate__full_name', 'interviewer')


admin.site.register(CandidateNote)
admin.site.register(CandidateActivity)


@admin.register(PlacementCompany)
class PlacementCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'contact_person', 'mobile', 'package_offered')
    search_fields = ('name', 'industry', 'contact_person', 'mobile')


@admin.register(PlacementDrive)
class PlacementDriveAdmin(admin.ModelAdmin):
    list_display = ('company', 'job_role', 'drive_date', 'status')
    list_filter = ('status',)
    search_fields = ('company__name', 'job_role', 'venue')


@admin.register(PlacementStudentAssignment)
class PlacementStudentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'company', 'drive', 'interview_status', 'final_status')
    list_filter = ('interview_status', 'final_status')
    search_fields = ('student_name', 'student__full_name', 'company__name')


@admin.register(PlacementInterview)
class PlacementInterviewAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'company', 'interview_round', 'date', 'time', 'status')
    list_filter = ('status',)
    search_fields = ('assignment__student_name', 'assignment__student__full_name', 'company__name')


@admin.register(PlacementOffer)
class PlacementOfferAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'company', 'offered_package', 'offer_status', 'joining_status')
    list_filter = ('offer_status', 'joining_status')


admin.site.register(PlacementActivity)
