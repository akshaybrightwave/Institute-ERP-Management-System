from django.contrib import admin
from .models import TimeTable, AcademicSession, Occupation


@admin.register(TimeTable)
class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('id', 'timetable_name', 'is_deleted', 'created_at')
    list_filter = ('is_deleted',)
    search_fields = ('timetable_name',)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_name', 'is_deleted', 'created_at')
    list_filter = ('is_deleted',)
    search_fields = ('session_name',)


@admin.register(Occupation)
class OccupationAdmin(admin.ModelAdmin):
    list_display = ('id', 'occupation_name', 'is_deleted', 'created_at')
    list_filter = ('is_deleted',)
    search_fields = ('occupation_name',)
