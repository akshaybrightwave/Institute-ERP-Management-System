from django.contrib import admin

from .models import CaseWorkItem, CaseWorkReport, FraudType, PoliceStation, RecoveryReport


@admin.register(FraudType)
class FraudTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(PoliceStation)
class PoliceStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(RecoveryReport)
class RecoveryReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_number',
        'report_month',
        'report_year',
        'name',
        'submitted_by',
        'approval_status',
        'submitted_at',
    )
    list_filter = ('approval_status', 'report_year', 'report_month', 'police_station', 'fraud_type')
    search_fields = ('report_number', 'name', 'submitted_by__username')
    readonly_fields = ('report_number', 'created_at', 'updated_at')


class CaseWorkItemInline(admin.TabularInline):
    model = CaseWorkItem
    extra = 0


@admin.register(CaseWorkReport)
class CaseWorkReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_number',
        'name',
        'case_no',
        'police_station',
        'case_status',
        'submitted_by',
        'approval_status',
        'submitted_at',
    )
    list_filter = ('approval_status', 'case_status', 'police_station')
    search_fields = ('report_number', 'name', 'case_no', 'investigating_officer', 'submitted_by__username')
    readonly_fields = ('report_number', 'created_at', 'updated_at')
    inlines = [CaseWorkItemInline]
