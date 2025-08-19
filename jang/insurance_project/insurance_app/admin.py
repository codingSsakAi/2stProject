# insurance_app/admin.py
from django.contrib import admin
from .models import CustomUser, Clause, InsuranceQuote, GlossaryTerm
from django.contrib.auth.admin import UserAdmin

@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ("term", "category", "slug", "updated_at")
    list_filter = ("category", )
    search_fields = ("term", "short_def", "long_def", "aliases")

admin.site.register(Clause)
admin.site.register(InsuranceQuote)
admin.site.register(CustomUser, UserAdmin)
