from django.contrib import admin
from .models import Feedback,FeedbackCategory,FeedbackPriority,FeedbackStatus

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'email', 'category', 'status', 'priority', 'rating', 'submitted_at')
    list_filter = ('category', 'status', 'priority', 'rating')
    search_fields = ('user__username', 'email', 'comment')
    readonly_fields = ('submitted_at', 'updated_at')
    list_editable = ('status', 'priority')
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'email')
        }),
        ('Feedback Information', {
            'fields': ('category', 'rating', 'comment', 'screenshot')
        }),
        ('Status Information', {
            'fields': ('status', 'priority', 'submitted_at', 'updated_at')
        }),
    )

