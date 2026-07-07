from django.contrib import admin
from .models import JourneyEntry, ChildNote, Attendance, CourseProgress


@admin.register(JourneyEntry)
class JourneyEntryAdmin(admin.ModelAdmin):
    list_display = ['child', 'type', 'date', 'staff_name']
    list_filter = ['type', 'date']
    search_fields = ['child__first_name', 'child__last_name', 'text']


@admin.register(ChildNote)
class ChildNoteAdmin(admin.ModelAdmin):
    list_display = ['child', 'date', 'staff_name']
    list_filter = ['date']
    search_fields = ['child__first_name', 'child__last_name', 'text']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['child', 'session', 'date', 'status', 'teacher']
    list_filter = ['status', 'date', 'session']
    search_fields = ['child__first_name', 'child__last_name']


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ['child', 'current_month', 'current_week', 'updated_at']
    search_fields = ['child__first_name', 'child__last_name']
