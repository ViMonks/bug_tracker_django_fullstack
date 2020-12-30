from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.views import generic
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .models import Team, Ticket, Project, TeamInvitation


# CBV MIXINS
class CommonTemplateContextMixin:
    """Provides template context needed for all views: the current team_pk based on url kwargs."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if (project_pk:=self.kwargs.get('project_pk')):
            self.request.user.last_viewed_project_pk = project_pk
            self.request.user.save()
        if (team_slug:=self.kwargs.get('team_slug')):
            team = get_object_or_404(Team, slug=team_slug)
            team_name = team.title
            context.setdefault('current_team', team)
            context.setdefault('team_pk', team.pk)
            context.setdefault('team_name', team_name)
            context.setdefault('team_slug', team.slug)
        pending_invites = TeamInvitation.objects.filter(invitee=self.request.user, status=1).count()
        context['pending_invites_count'] = pending_invites
        return context



# Custom permission mixins
class TeamManagerMixin(UserPassesTestMixin):
    def test_func(self):
        team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
        user = self.request.user
        return user in team.managers.all() or user==team.owner or user.is_staff


class StaffOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ViewProjectMixin(UserPassesTestMixin, generic.detail.SingleObjectMixin):
    """Determines whether a user has permission to view a particular project based on whether they are staff or are assigned as that project's manager or one of its developers."""
    def get_project(self):
        return self.get_object()

    def test_func(self):
        project = self.get_project()
        team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
        user = self.request.user
        if user.is_staff or user in team.get_owners():
            return True
        elif not user in team.members.all():
            return False
        return user in project.developers.all() or user == project.manager

    def handle_no_permission(self): # raises 404 rather than 403 to obfuscate whether a project exists at that pk
        if self.raise_exception or self.request.user.is_authenticated:
            raise Http404("ViewProjectMixin")
        return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())


# class ViewTicketMixin(UserPassesTestMixin, generic.detail.SingleObjectMixin):
#     """Determines whether a user has permission to view a particular ticket based on whether they are staff or are assigned as that ticket's project's manager or one of its developers."""
#     def get_associated_project(self):
#         return self.get_object().project
#
#     def test_func(self):
#         project = self.get_associated_project()
#         team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
#         user = self.request.user
#         if user.is_staff or user==team.owner:
#             return True
#         elif not user==team.owner or user in team.members.all():
#             return False
#         return user in project.developers.all() or user == project.manager
#
#     def handle_no_permission(self): # raises 404 rather than 403 to obfuscate whether a project exists at that pk
#         if self.raise_exception or self.request.user.is_authenticated:
#             raise Http404()
#         return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())

class ViewTicketMixin(ViewProjectMixin):
    def get_project(self):
        return self.get_object().project

    def handle_no_permission(self): # raises 404 rather than 403 to obfuscate whether a project exists at that pk
        if self.raise_exception or self.request.user.is_authenticated:
            raise Http404("ViewTicketMixin")
        return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())


class UpdateTicketMixin(UserPassesTestMixin):
    """A mixin requiring that the user is either the team's owner, the project's manager, or the ticket's assigned developer."""
    def test_func(self):
        team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
        ticket = get_object_or_404(Ticket, pk=self.kwargs['pk'])
        project = get_object_or_404(Project, pk=ticket.project.pk)
        user = self.request.user
        return user in team.get_owners() or user == project.manager or user in ticket.developer.all() or user.is_staff

    def handle_no_permission(self):
        if self.raise_exception or self.request.user.is_authenticated:
            raise Http404()
        return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())


class TeamOwnerMixin(UserPassesTestMixin, generic.detail.SingleObjectMixin):
    """A mixin requiring that the user is the owner of the currently selected team."""
    def test_func(self):
        team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
        return self.request.user in team.get_owners()

    def handle_no_permission(self):
        if self.raise_exception or self.request.user.is_authenticated:
            raise Http404()
        return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())


class TeamMemberMixin(UserPassesTestMixin):
    """A mixin requiring that the user is a member of the currently selected team."""
    def test_func(self):
        team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
        return self.request.user in team.members.all() or self.request.user.is_staff

    def handle_no_permission(self):
        if self.raise_exception or self.request.user.is_authenticated:
            raise Http404("TeamMemberMixin")
        return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())
