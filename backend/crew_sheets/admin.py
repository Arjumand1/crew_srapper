from django.contrib import admin
from .models import CrewSheet

# Register your models here.

@admin.register(CrewSheet)
class CrewSheetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'date_uploaded', 'status')
    list_filter = ('status', 'date_uploaded')
    search_fields = ('name', 'user__email', 'user__username')
    readonly_fields = ('id', 'date_uploaded', 'date_processed')
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'user', 'image')
        }),
        ('Processing Information', {
            'fields': ('status', 'date_uploaded', 'date_processed', 'error_message')
        }),
        ('Extracted Data', {
            'fields': ('extracted_data',)
        }),
    )
