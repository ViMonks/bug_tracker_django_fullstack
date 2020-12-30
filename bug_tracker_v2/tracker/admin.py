from django.contrib import admin

from . import models

# Register your models here.
admin.site.register(models.Project)
admin.site.register(models.Ticket)
admin.site.register(models.Comment)
# admin.site.register(models.Team)
admin.site.register(models.TeamMembership)
admin.site.register(models.TicketFile)

class TeamMembershipInline(admin.TabularInline):
    model = models.TeamMembership
    extra = 1

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        user = formset.form.base_fields['user']
        user.widget.can_delete_related = False
        user.widget.can_add_related = False
        return formset

class TeamAdmin(admin.ModelAdmin):
    inlines = (TeamMembershipInline,)

admin.site.register(models.Team, TeamAdmin)
