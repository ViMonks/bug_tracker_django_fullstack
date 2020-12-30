from datetime import date, timedelta

from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect, Http404
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.core.validators import validate_email
from django.core import mail
from django.urls import reverse_lazy, reverse
from django.views import generic, View
from django.template.loader import render_to_string
from django.core import paginator
from django.core.exceptions import PermissionDenied
from django_filters.views import FilterView
from .filters import TicketFilter, ProjectFilter, TicketFilterArchivedProjects
from django_tables2.views import SingleTableMixin, SingleTableView
from . import tables as my_tables

from . import models
from .constants import NOTIFICATION_SETTING_DEFAULTS, NOTIFICATION_SETTING_DESCRIPTIONS
from .forms import CommentForm, CloseTicketResolutionForm, ProjectForm, CreateTicketForm, UpdateTicketForm, TicketFileUploadForm
from .utils import (CommonTemplateContextMixin, ViewTicketMixin, ViewProjectMixin,
                    TeamOwnerMixin, TeamMemberMixin, UpdateTicketMixin, )

from django.contrib.auth import get_user_model

User = get_user_model()

################################################################################ Team-related Views
class TeamDetails(LoginRequiredMixin, TeamMemberMixin, CommonTemplateContextMixin, generic.DetailView):
    model = models.Team
    template_name = 'tracker/team_details.html'
    context_object_name = 'team'
    slug_url_kwarg = 'team_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        managers = team.get_managers()
        context['managers'] = managers
        # all_members = team.members.all()
        # non_managers = [user for user in all_members if user not in managers]
        context['non_managers'] = team.get_only_members()
        return context


class TeamUpdateView(LoginRequiredMixin, TeamOwnerMixin, SuccessMessageMixin , CommonTemplateContextMixin, generic.UpdateView):
    model = models.Team
    fields = ['description',]
    template_name = 'tracker/team_update_form.html'
    success_message = 'Team updated.'
    slug_url_kwarg = 'team_slug'


class TeamListView(LoginRequiredMixin, CommonTemplateContextMixin, generic.ListView):
    model = models.Team
    context_object_name = 'teams'
    template_name = 'tracker/team_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if (project_pk:=self.request.user.last_viewed_project_pk):
            last_viewed_project = models.Project.objects.get(pk=project_pk)
            context['last_viewed_project'] = last_viewed_project
        return context

    def get_queryset(self):
        owned_teams = models.Team.objects.user_owned_teams(self.request.user).order_by('title')
        member_teams = models.Team.objects.user_member_teams(self.request.user).order_by('title')
        return {'owned_teams': owned_teams, 'member_teams': member_teams}

class TeamCreateView(LoginRequiredMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.CreateView):
    model = models.Team
    fields = ['title', 'description']
    template_name = 'tracker/team_create_form.html'
    success_message = '%(title)s created.'

    def form_valid(self, form):
        user = self.request.user
        new_team = form.save()
        models.TeamMembership.objects.create(team=new_team, user=user, role=3)
        return super(TeamCreateView, self).form_valid(form)


class ManageTeamOwnershipWarning(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.DetailView):
    template_name = 'tracker/add_team_owner_warning.html'
    model = models.Team
    slug_url_kwarg = 'team_slug'


class ManageTeamOwnership(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.DetailView):
    template_name = 'tracker/manage_team_ownership.html'
    context_object_name = 'members'
    model = models.Team
    slug_url_kwarg = 'team_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        managers = team.get_managers()
        members = team.get_only_members()
        multiple_owners = team.get_owners().count() > 1
        context['valid_members'] = managers|members
        context['multiple_owners'] = multiple_owners
        context['current_owners'] = team.get_owners()
        return context


class TeamAddOwner(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.View):
    def get(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = models.Team.objects.get(slug=team_slug)
        username = self.request.GET.get('username')
        try:
            user = User.objects.get(username=username)
            if user in team.members.all() or user in team.get_only_members():
                team.add_owner(user)
                messages.success(request, f'{username} added as a co-owner.')
                notification_setting = user.notification_settings.get(
                    'team_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('team_role_assignment', True)
                )
                if user.email and notification_setting:
                    body = render_to_string('emails/added_as_team_owner.txt', {'team_title': team.title})
                    mail.send_mail(
                        subject=f'Added as co-owner of team {team.title}',
                        message=body,
                        from_email='noreply@monksbugtracker.com',
                        recipient_list=[user.email]
                    )
            else:
                messages.warning(request, 'Cannot make co-owner. User either does not exist or is not a member of your team.')
        except ObjectDoesNotExist:
            messages.warning(request, 'Cannot make co-owner. User either does not exist or is not a member of your team.')
        return redirect(reverse_lazy('team_details', kwargs={'team_slug': team_slug}))


class TeamRemoveOwner(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.View):
    def get(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = models.Team.objects.get(slug=team_slug)
        user = self.request.user
        if team.remove_owner(user):
            messages.success(request, f'You are no longer an owner of team {team.title}.')
            notification_setting = user.notification_settings.get(
                'team_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('team_role_assignment', True)
            )
            if user.email and notification_setting:
                body = render_to_string('emails/removed_as_team_owner.txt', {'team_title': team.title})
                mail.send_mail(
                    subject=f'No longer an owner of team {team.title}',
                    message=body,
                    from_email='noreply@monksbugtracker.com',
                    recipient_list=[user.email]
                )
            return HttpResponseRedirect(reverse('team_details', kwargs={'team_slug': team_slug}))
        else:
            messages.warning(request, 'You cannot step down as team owner until you promote a new member as co-owner.')
            return HttpResponseRedirect(reverse('manage_team_ownership', kwargs={'team_slug': team_slug}))


class TeamAddManager(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.View):
    def get(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = models.Team.objects.get(slug=team_slug)
        username = self.request.GET.get('username')
        try:
            user = User.objects.get(username=username)
            if user in team.members.all():
                team.add_manager(user)
                messages.success(request, f'{username} added as manager.')
                notification_setting = user.notification_settings.get(
                    'team_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('team_role_assignment', True)
                )
                if user.email and notification_setting:
                    body = render_to_string('emails/added_as_team_manager.txt', {'team_title': team.title})
                    mail.send_mail(
                        subject=f'Added as manager to team {team.title}',
                        message=body,
                        from_email='noreply@monksbugtracker.com',
                        recipient_list=[user.email]
                    )
            else:
                messages.warning(request, 'Cannot make manager. User either does not exist or is not a member of your team.')
        except ObjectDoesNotExist:
            messages.warning(request, 'Cannot make manager. User either does not exist or is not a member of your team.')
        return redirect(reverse_lazy('team_details', kwargs={'team_slug': team_slug}))


class TeamRemoveManager(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.View):
    def get(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = models.Team.objects.get(slug=team_slug)
        username = self.request.GET.get('username')
        try:
            user = User.objects.get(username=username)
            if user in team.get_managers():
                team.remove_manager(user)
                messages.success(request, f'{username} is no longer a team manager.')
                notification_setting = user.notification_settings.get(
                    'team_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('team_role_assignment', True)
                )
                if user.email and notification_setting:
                    body = render_to_string('emails/removed_as_team_manager.txt', {'team_title': team.title})
                    mail.send_mail(
                        subject=f'Removed from managers to team {team.title}',
                        message=body,
                        from_email='noreply@monksbugtracker.com',
                        recipient_list=[user.email]
                    )
            else:
                messages.warning(request, 'Cannot remove manager. User either does not exist or is not a manager of your team.')
        except ObjectDoesNotExist:
            messages.warning(request, 'Cannot remove manager. User either does not exist or is not a manager of your team.')
        return redirect(reverse_lazy('team_details', kwargs={'team_slug': team_slug}))


class TeamRemoveMember(LoginRequiredMixin, TeamOwnerMixin, CommonTemplateContextMixin, generic.View):
    def get(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = models.Team.objects.get(slug=team_slug)
        username = self.request.GET.get('username')
        try:
            user = User.objects.get(username=username)
            if user in team.members.all():
                team.remove_member(user)
                messages.success(request, f'{username} removed from team.')
                notification_setting = user.notification_settings.get(
                    'team_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('team_role_assignment', True)
                )
                if user.email and notification_setting:
                    body = render_to_string('emails/removed_as_team_member.txt', {'team_title': team.title})
                    mail.send_mail(
                        subject=f'Removed from team {team.title}',
                        message=body,
                        from_email='noreply@monksbugtracker.com',
                        recipient_list=[user.email]
                    )
            else:
                messages.warning(request,
                                 'Cannot remove member. User either does not exist or is not a member of your team.')
        except ObjectDoesNotExist:
            messages.warning(request,
                             'Cannot remove member. User either does not exist or is not a member of your team.')
        return redirect(reverse_lazy('team_details', kwargs={'team_slug': team_slug}))

class LeaveTeam(LoginRequiredMixin, TeamMemberMixin, CommonTemplateContextMixin, generic.View):
    def get(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = models.Team.objects.get(slug=team_slug)
        user = self.request.user
        if user not in team.get_owners():
            team.remove_member(user)
            messages.success(request, f'You have left team {team.title}.')
            notification_setting = user.notification_settings.get(
                'team_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('team_role_assignment', True)
            )
            if user.email and notification_setting:
                body = render_to_string('emails/left_team.txt', {'team_title': team.title})
                mail.send_mail(
                    subject=f'Left team {team.title}',
                    message=body,
                    from_email='noreply@monksbugtracker.com',
                    recipient_list=[user.email]
                )
            return redirect(reverse_lazy('team_list'))
        else:
            messages.warning(request, 'You cannot leave a team you own. Step down as owner first.')
            return redirect(reverse_lazy('team_details', kwargs={'team_slug': team_slug}))


class AcceptTeamInvitation(LoginRequiredMixin, generic.TemplateView):
    template_name = 'tracker/accept_team_invitation.html'

    def get(self, request, *args, **kwargs):
        if (invitation_id:=request.GET.get('invitation')):
            try:
                invitation = models.TeamInvitation.objects.get(id=invitation_id)
                expired = date.today() > invitation.created_on + timedelta(days=7)
                if expired or invitation.status != invitation.PENDING:
                    messages.warning(request, 'That invitation is no longer valid.')
                    return HttpResponseRedirect(reverse('accept_team_invitation'))
                team = invitation.team
                team.members.add(request.user)
                team.save()
                invitation.status = invitation.ACCEPTED
                invitation.save()
                messages.success(request, 'Invitation accepted.')
                return HttpResponseRedirect(reverse('tracker:team_details', kwargs={'team_slug': team.slug}))
            except (ValidationError, ObjectDoesNotExist):
                messages.warning(request, 'Please enter a valid invitation ID.')
                return HttpResponseRedirect(reverse('accept_team_invitation'))
        else:
            return super().get(request, *args, **kwargs)


class DeclineTeamInvitation(LoginRequiredMixin, generic.View):
    template_name = 'tracker/accept_team_invitation.html'

    def get(self, request, *args, **kwargs):
        if (invitation_id:=request.GET.get('invitation')):
            try:
                invitation = models.TeamInvitation.objects.get(id=invitation_id)
                if invitation.invitee and invitation.invitee != request.user:
                    raise Http404
                if invitation.status == invitation.PENDING:
                    invitation.status = invitation.DECLINED
                    invitation.save()
                    messages.success(request, 'Team invitation declined.')
                    return HttpResponseRedirect(reverse('pending_invitations'))
                else:
                    messages.warning('That invitation is no longer valid.')
                    return HttpResponseRedirect(reverse('pending_invitations'))
            except (ValidationError, ObjectDoesNotExist):
                messages.warning(request, 'Please enter a valid invitation ID.')
                return HttpResponseRedirect(reverse('accept_team_invitation'))
        else:
            return HttpResponseRedirect(reverse('pending_invitations'))


class SendTeamInvitation(LoginRequiredMixin, TeamOwnerMixin, generic.TemplateView):
    template_name = 'tracker/send_team_invitation.html'

    def get_context_data(self, **kwargs):
        team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
        return {'team_slug': self.kwargs['team_slug'], 'team_name': team.title}

    def post(self, request, *args, **kwargs):
        team_slug = self.kwargs['team_slug']
        team = get_object_or_404(models.Team, slug=team_slug)
        email = ''
        if (invitee:=request.POST.get('invitee')):
            if '@' not in invitee:
                try:
                    user = User.objects.get(username=invitee)
                    if user in team.members.all():
                        messages.info(request, 'User is already a member of your team.')
                        return HttpResponseRedirect(reverse('team_invite', kwargs={'team_slug': team_slug}))
                    if user.email:
                        email = user.email
                    else:
                        messages.info(request, 'That user does not have a registered email address.')
                        return HttpResponseRedirect(reverse('team_invite', kwargs={'team_slug': team_slug}))
                except ObjectDoesNotExist:
                    messages.warning(request, 'There is no user with that username.')
                    return HttpResponseRedirect(reverse('team_invite', kwargs={'team_slug': team_slug}))
            else:
                try:
                    validate_email(invitee)
                    email = invitee
                    try:
                        user = User.objects.get(email=email)
                    except ObjectDoesNotExist:
                        user = None
                except ValidationError:
                    messages.warning(request, 'Please enter a valid email address.')
                    return HttpResponseRedirect(reverse('team_invite', kwargs={'team_slug': team_slug}))
            new_invitation = models.TeamInvitation.objects.create(team=team, invitee_email=email, invitee=user)
            new_invitation.save()
            try:
                notification_setting = user.notification_settings.get(
                    'team_invites', NOTIFICATION_SETTING_DEFAULTS.get('team_invites', True)
                )
            except AttributeError:
                notification_setting = True
            if notification_setting:
                new_invitation.send_email(
                    inviter=self.request.user.username,
                    team=team.title,
                    invitation_uuid=new_invitation.id
                )
            messages.success(request, 'Invitation sent.')
            return HttpResponseRedirect(reverse('team_invite', kwargs={'team_slug': team_slug}))
        else:
            return HttpResponseRedirect(reverse('team_invite', kwargs={'team_slug': team_slug}))


class InvitationsListView(LoginRequiredMixin, generic.ListView):
    model = models.TeamInvitation
    template_name = 'tracker/team_invitation_list.html'
    context_object_name = 'invites'

    def get_queryset(self):
        return models.TeamInvitation.objects.filter(invitee=self.request.user, status=1).order_by('created_on')


class ManageSubscriptions(LoginRequiredMixin, SingleTableView):
    table_class = my_tables.SubscriptionsTable
    context_object_name = 'ticket'
    template_name = 'tracker/manage_subscriptions.html'
    table_pagination = {"per_page": 10}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            if (project_pk := self.request.user.last_viewed_project_pk):
                context['last_viewed_project_pk'] = project_pk
                last_viewed_project = models.Project.objects.get(pk=project_pk)
                context['last_viewed_project'] = last_viewed_project
        # context['current_team_pk'] = self.kwargs['team_pk']
        return context

    def get_queryset(self):
        return self.request.user.ticket_subscriptions.filter(status='open', project__is_archived=False).select_related('team')


class ManageNotificationSettings(LoginRequiredMixin, generic.TemplateView):
    template_name = 'tracker/notification_settings.html'

    def get_setting(self, setting):
        """A helper function to get a user's setting for a particular notification type or get defaults if unavailable."""
        try:
            return self.request.user.notification_settings.get(
                        setting, NOTIFICATION_SETTING_DEFAULTS.get(setting, True)
                    )
        except AttributeError:
            return True

    def get_context_data(self, **kwargs):
        settings_list = NOTIFICATION_SETTING_DEFAULTS.keys()
        enabled = []
        disabled = []
        for setting in settings_list:
            preference = self.get_setting(setting=setting)
            if preference:
                enabled.append(NOTIFICATION_SETTING_DESCRIPTIONS[setting])
            else:
                disabled.append(NOTIFICATION_SETTING_DESCRIPTIONS[setting])
        return {'enabled': enabled, 'disabled': disabled}


class EnableNotificationSetting(LoginRequiredMixin, generic.View):

    def get(self, request, *args, **kwargs):
        if (setting:=request.GET.get('setting')):
            if setting in NOTIFICATION_SETTING_DEFAULTS.keys():
                request.user.notification_settings[setting] = True
                request.user.save()
                messages.success(request, 'Email notifications enabled.')
                return HttpResponseRedirect(reverse('manage_notifications'))
            else:
                messages.warning(request, 'Please select a valid notification setting.')
                return HttpResponseRedirect(reverse('manage_notifications'))
        else:
            messages.warning(request, 'Please select a valid notification setting.')
            return HttpResponseRedirect(reverse('manage_notifications'))


class DisableNotificationSetting(LoginRequiredMixin, generic.View):

    def get(self, request, *args, **kwargs):
        if (setting:=request.GET.get('setting')):
            if setting in NOTIFICATION_SETTING_DEFAULTS.keys():
                request.user.notification_settings[setting] = False
                request.user.save()
                messages.success(request, 'Email notifications disabled.')
                return HttpResponseRedirect(reverse('manage_notifications'))
            else:
                messages.warning(request, 'Please select a valid notification setting.')
                return HttpResponseRedirect(reverse('manage_notifications'))
        else:
            messages.warning(request, 'Please select a valid notification setting.')
            return HttpResponseRedirect(reverse('manage_notifications'))


################################################################################ Ticket Displaying Views
class TicketTable(LoginRequiredMixin, CommonTemplateContextMixin, TeamMemberMixin, SingleTableMixin, FilterView):
    table_class = my_tables.TicketTable
    template_name = 'tracker/ticket_list.html'
    filterset_class = TicketFilter
    context_object_name = 'page'
    table_pagination = {"per_page": 10}
    PAGE_TITLE = 'Open Tickets'
    TICKET_STATUS_TOGGLE = 'Show Closed Tickets'
    TICKET_STATUS_TOGGLE_URL = 'tracker:closed_ticket_list'
    DISPLAY_DEV_FILTER = True
    NO_TICKETS_MESSAGE = 'There are no open tickets.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.PAGE_TITLE
        context['ticket_status_toggle'] = self.TICKET_STATUS_TOGGLE
        context['ticket_status_toggle_url'] = self.TICKET_STATUS_TOGGLE_URL
        context['display_dev_filter'] = self.DISPLAY_DEV_FILTER
        context['no_tickets_message'] = self.NO_TICKETS_MESSAGE
        return context

    def get_queryset(self):
        return models.Ticket.objects.filter_for_team_and_user(team_slug=self.kwargs['team_slug'], user=self.request.user).exclude(status='closed').distinct().select_related('project').prefetch_related('developer').select_related('user')


class AssignedTicketTable(TicketTable): # removed DeveloperMixin
    PAGE_TITLE = 'My Open Tickets'
    TICKET_STATUS_TOGGLE = 'Show My Closed Tickets'
    TICKET_STATUS_TOGGLE_URL = 'tracker:closed_assigned_ticket_list'
    DISPLAY_DEV_FILTER = False
    NO_TICKETS_MESSAGE = 'There are no open tickets assigned to you.'

    def get_queryset(self):
        return models.Ticket.objects.filter_for_team_and_user(team_slug=self.kwargs['team_slug'], user=self.request.user).filter(developer=self.request.user).exclude(status='closed').distinct().select_related('project').prefetch_related('developer').select_related('user')


class ClosedTicketTable(TicketTable):
    PAGE_TITLE = 'Closed Tickets'
    TICKET_STATUS_TOGGLE = 'Show Open Tickets'
    TICKET_STATUS_TOGGLE_URL = 'tracker:ticket_list'
    filterset_class = TicketFilterArchivedProjects
    NO_TICKETS_MESSAGE = 'There are no closed tickets.'

    def get_queryset(self):
        return models.Ticket.objects.filter_for_team_and_user(team_slug=self.kwargs['team_slug'], user=self.request.user).filter(status='closed').distinct().select_related('project').prefetch_related('developer').select_related('user')


class ClosedAssignedTicketTable(TicketTable): # removed DeveloperMixin
    PAGE_TITLE = 'My Closed Tickets'
    TICKET_STATUS_TOGGLE = 'Show My Open Tickets'
    TICKET_STATUS_TOGGLE_URL = 'tracker:assigned_ticket_list'
    DISPLAY_DEV_FILTER = False
    filterset_class = TicketFilterArchivedProjects
    NO_TICKETS_MESSAGE = 'There are no closed tickets assigned to you.'

    def get_queryset(self):
        return models.Ticket.objects.filter_for_team_and_user(team_slug=self.kwargs['team_slug'], user=self.request.user).filter(developer=self.request.user).filter(status='closed').distinct().select_related('project').prefetch_related('developer').select_related('user')


################################################################################ Project Displaying Views
class ProjectTable(LoginRequiredMixin, CommonTemplateContextMixin, TeamMemberMixin, SingleTableMixin, FilterView):
    table_class = my_tables.ProjectTable
    table_pagination = {"per_page": 10}
    model = models.Project
    template_name = 'tracker/project_list.html'
    filterset_class = ProjectFilter
    EMPTY_PROJECT_MESSAGE = 'There are no open projects.'
    ARCHIVED_VIEW_TOGGLE = 'View archived projects.'
    ARCHIVED_VIEW_TOGGLE_URL = 'tracker:archived_project_list'

    def get_queryset(self):
        user = self.request.user
        team_slug=self.kwargs['team_slug']
        return models.Project.objects.filter_for_team_and_user(team_slug=team_slug, user=user).filter(is_archived=False).annotate(open_tickets=Count('project_tickets', filter=~Q(project_tickets__status='closed'))).select_related('manager')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_count'] = models.Project.objects.filter_for_team_and_user(team_slug=self.kwargs['team_slug'], user=self.request.user).filter(is_archived=False).count()
        context['empty_project_message'] = self.EMPTY_PROJECT_MESSAGE
        context['archived_view_toggle'] = self.ARCHIVED_VIEW_TOGGLE
        context['archived_view_toggle_url'] = self.ARCHIVED_VIEW_TOGGLE_URL
        return context


class ArchivedProjectTable(ProjectTable):
    # PROJECT_COUNT = models.Project.objects.filter(is_archived=True).count()
    EMPTY_PROJECT_MESSAGE = 'There are no archived projects.'
    ARCHIVED_VIEW_TOGGLE = 'View active projects.'
    ARCHIVED_VIEW_TOGGLE_URL = 'tracker:project_list'

    @property
    def project_count(self):
        return models.Project.objects.filter(is_archived=True).count()

    def get_queryset(self):
        user = self.request.user
        team_slug=self.kwargs['team_slug']
        return models.Project.objects.filter_for_team_and_user(team_slug=team_slug, user=user).filter(is_archived=True).annotate(open_tickets=Count('project_tickets', filter=~Q(project_tickets__status='closed'))).select_related('manager')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_count'] = models.Project.objects.filter_for_team_and_user(team_slug=self.kwargs['team_slug'], user=self.request.user).filter(is_archived=True).count()
        return context


class ProjectDetails(LoginRequiredMixin, ViewProjectMixin, TeamMemberMixin, CommonTemplateContextMixin, SingleTableMixin, generic.DetailView):
    model = models.Project
    table_class = my_tables.TicketTable
    template_name = 'tracker/project_details.html'
    context_object_name = 'project'
    pk_url_kwarg = 'project_pk'
    table_pagination = {"per_page": 10, } # "class": "pagination pagination-sm justify-content-center"
    TICKET_TABLE_TITLE = 'Open Tickets'
    TICKET_STATUS_TOGGLE = 'View Closed Tickets'
    TICKET_STATUS_TOGGLE_URL = 'tracker:project_details_closed_tickets'
    EMPTY_TICKET_MESSAGE = 'There are no open tickets.'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('developers')

    def get_table_data(self):
        table_data = self.object.project_tickets.exclude(status='closed').select_related('user').prefetch_related('developer')
        if (q := self.request.GET.get('q')):
            return table_data.filter(title__icontains=q)
        return table_data

    def get_table_kwargs(self):
        return {'exclude': 'project'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket_counter'] = self.object.project_tickets.exclude(status='closed').count()
        context['ticket_table_title'] = self.TICKET_TABLE_TITLE
        context['ticket_status_toggle_url'] = self.TICKET_STATUS_TOGGLE_URL
        context['ticket_status_toggle'] = self.TICKET_STATUS_TOGGLE
        context['empty_ticket_message'] = self.EMPTY_TICKET_MESSAGE
        if self.object.is_archived:
            context['archive_toggle_label'] = 'Reopen Project'
        else:
            context['archive_toggle_label'] = 'Archive Project'
        return context


class ProjectDetailsClosedTickets(ProjectDetails):
    TICKET_TABLE_TITLE = 'Closed Tickets'
    TICKET_STATUS_TOGGLE = 'View Open Tickets'
    TICKET_STATUS_TOGGLE_URL = 'tracker:project_details'
    EMPTY_TICKET_MESSAGE = 'There are no closed tickets.'

    def get_table_data(self):
        table_data = self.object.project_tickets.filter(status='closed').select_related('user').prefetch_related('developer')
        if (q := self.request.GET.get('q')):
            return table_data.filter(title__icontains=q)
        return table_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket_counter'] = self.object.project_tickets.filter(status='closed').count()
        return context


class ProjectSubscribeAllTicketsView(LoginRequiredMixin, ViewProjectMixin, CommonTemplateContextMixin, generic.detail.SingleObjectMixin, View):
    pk_url_kwarg = 'project_pk'
    model = models.Project

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        project.subscribers.add(self.request.user)
        tickets = project.project_tickets.filter(status='open')
        for ticket in tickets:
            ticket.subscribers.add(self.request.user)
        messages.success(request, 'Successfully subscribed to project.')
        return HttpResponseRedirect(reverse('tracker:project_details', kwargs={'team_slug': project.team.slug, 'project_pk': project.pk}))


class ProjectUnsubscribeAllTicketsView(LoginRequiredMixin, ViewProjectMixin, CommonTemplateContextMixin, generic.detail.SingleObjectMixin, View):
    pk_url_kwarg = 'project_pk'
    model = models.Project

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        project.subscribers.remove(self.request.user)
        tickets = project.project_tickets.filter(status='open')
        for ticket in tickets:
            ticket.subscribers.remove(self.request.user)
        messages.success(request, 'Successfully unsubscribed from project.')
        return HttpResponseRedirect(reverse('tracker:project_details', kwargs={'team_slug': project.team.slug, 'project_pk': project.pk}))


############################################################################################# Ticket CRUD Views
class UpdateTicket(LoginRequiredMixin, UpdateTicketMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.edit.UpdateView):
    model = models.Ticket
    # fields = ['title', 'description', 'developer', 'priority', 'resolution']
    template_name = 'tracker/ticket_update.html'
    success_message = 'Ticket updated.'
    form_class = UpdateTicketForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.get_object().project.pk
        return kwargs


class CreateTicket(LoginRequiredMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.edit.CreateView):
    model = models.Ticket
    template_name = 'tracker/create_ticket.html'
    success_url = 'tracker/'
    success_message = 'Ticket created.'
    form_class = CreateTicketForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request.GET.get('project')
        return kwargs

    def get(self, request, *args, **kwargs):
        if (project_pk := self.request.GET.get('project')):
            project = get_object_or_404(models.Project, pk=project_pk)
            team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
            user = self.request.user
            if not (user in team.get_owners() or user == project.manager or user in project.developers.all() or user.is_staff):
                raise Http404
            return super().get(request, *args, **kwargs)
        else:
            raise Http404

    def post(self, request, *args, **kwargs):
        if (project_pk := self.request.GET.get('project')):
            project = get_object_or_404(models.Project, pk=project_pk)
            team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
            user = self.request.user
            if not (user in team.get_owners() or user == project.manager or user in project.developers.all() or user.is_staff):
                raise Http404
            return super().post(request, *args, **kwargs)
        else:
            raise Http404

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        if (project_pk := self.request.GET.get('project')):
            project = get_object_or_404(models.Project, pk=project_pk)
            form.instance.project = project
            form.instance.team = project.team
        else:
            raise Http404
        return super(CreateTicket, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('tracker:project_details', kwargs={
            'project_pk': self.object.project.pk, 'team_slug': self.object.project.team.slug
        })

#generic.detail.SingleObjectMixin, generic.FormView
class TicketFileUploadView(LoginRequiredMixin, UpdateTicketMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.CreateView):
    model = models.TicketFile
    form_class = TicketFileUploadForm
    success_message = 'File successfully uploaded.'
    template_name = 'tracker/ticket_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket_pk = self.kwargs.get('pk')
        project = get_object_or_404(models.Ticket, pk=ticket_pk).project
        context['project_pk'] = project.pk
        return context

    def get_success_url(self):
        ticket = self.object.ticket
        return reverse('tracker:ticket_details', kwargs={'pk': ticket.pk, 'team_slug': ticket.team.slug})

    def form_valid(self, form):
        try:
            user = self.request.user
            ticket_pk = self.kwargs.get('pk')
            ticket = get_object_or_404(models.Ticket, pk=ticket_pk)
            form.instance.uploaded_by = user
            form.instance.ticket = ticket
            return super().form_valid(form)
        except IntegrityError:
            messages.warning(self.request, 'A file upload with that title already exists for this ticket. Please choose a different title.')
            return HttpResponseRedirect(reverse('tracker:ticket_details', kwargs={'team_slug': self.kwargs['team_slug'], 'pk': self.kwargs['pk']}))

    def form_invalid(self, form):
        messages.warning(self.request, form.errors['file'][0])
        return HttpResponseRedirect(reverse('tracker:ticket_details', kwargs={'team_slug': self.kwargs['team_slug'], 'pk': self.kwargs['pk']}))


############################################################################################## Project CRUD Views
class CreateProject(LoginRequiredMixin, TeamOwnerMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.edit.CreateView):
    model = models.Project
    template_name = 'tracker/create_or_update_project.html'
    success_message = '%(title)s created.'
    form_class = ProjectForm

    def get_form_kwargs(self):
        kwargs = super(CreateProject, self).get_form_kwargs()
        kwargs['team_slug'] = self.kwargs['team_slug']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_or_update'] = 'Create'
        return context

    def form_valid(self, form):
        team_slug = self.kwargs.get('team_slug')
        team = get_object_or_404(models.Team, slug=team_slug)
        form.instance.team = team
        if (manager:=form.instance.manager):
            notification_setting = manager.notification_settings.get(
                'project_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('project_role_assignment', True)
            )
            if manager.email and notification_setting:
                body = render_to_string('emails/added_as_project_manager.txt', {'project_title': form.instance.title})
                mail.send_mail(
                    subject=f'Assigned as manager of {form.instance.title}',
                    message=body,
                    from_email='noreply@monksbugtracker.com',
                    recipient_list=[manager.email]
                )
        return super(CreateProject, self).form_valid(form)


class UpdateProject(LoginRequiredMixin, TeamOwnerMixin, ViewProjectMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.edit.UpdateView):
    model = models.Project
    template_name = 'tracker/create_or_update_project.html'
    success_message = '%(title)s project updated.'
    form_class = ProjectForm
    pk_url_kwarg = 'project_pk'

    def get_form_kwargs(self):
        kwargs = super(UpdateProject, self).get_form_kwargs()
        kwargs['team_slug'] = self.kwargs['team_slug']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_or_update'] = 'Update'
        return context

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        if (manager_id_from_form := request.POST.get('manager')):
            new_manager = User.objects.get(id=manager_id_from_form)
            if new_manager != project.manager:
                notification_setting = new_manager.notification_settings.get(
                    'project_role_assignment', NOTIFICATION_SETTING_DEFAULTS.get('project_role_assignment', True)
                )
                if new_manager.email and notification_setting:
                    body = render_to_string('emails/added_as_project_manager.txt', {'project_title': project.title})
                    mail.send_mail(
                        subject=f'Assigned as manager of {project.title}',
                        message=body,
                        from_email='noreply@monksbugtracker.com',
                        recipient_list=[new_manager.email]
                    )
        return super().post(request, *args, **kwargs)


class ToggleArchiveProject(LoginRequiredMixin, TeamOwnerMixin, ViewProjectMixin, CommonTemplateContextMixin, generic.detail.SingleObjectMixin, View):
    model = models.Project
    pk_url_kwarg = 'project_pk'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_archived = not self.object.is_archived
        success_message = 'archived.' if self.object.is_archived else 'reopened.'
        messages.info(request, f'{self.object.title} project {success_message}')
        self.object.save()
        return HttpResponseRedirect(reverse('tracker:project_details', kwargs={'project_pk': self.object.pk, 'team_slug': self.object.team.slug}))


class ProjectManageDevelopers(LoginRequiredMixin, TeamMemberMixin, ViewProjectMixin, CommonTemplateContextMixin, generic.DetailView):
    model = models.Project
    context_object_name = 'project'
    template_name = 'tracker/project_manage_developers.html'
    pk_url_kwarg = 'project_pk'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('team__members')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_developers = self.get_object().developers.all()
        context['project_developers'] = project_developers
        team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
        team_members = team.members.all()
        team_members = [member for member in team_members if member not in project_developers]
        context['team_members'] = team_members
        return context

    def get(self, request, *args, **kwargs):
        team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
        project = self.get_object()
        if request.user in team.get_owners() or request.user == project.manager:
            try:
                if (member_username := request.GET.get('add')):
                    member = User.objects.get(username=member_username)
                    if member in team.members.all():
                        project.developers.add(member)
                        notification_setting = member.notification_settings.get(
                            'project_role_assignment',
                            NOTIFICATION_SETTING_DEFAULTS.get('project_role_assignment', True)
                        )
                        if member.email and notification_setting:
                            body = render_to_string('emails/added_as_project_developer.txt', {'project_title': project.title})
                            mail.send_mail(
                                subject=f'Added as developer to project {project.title}',
                                message=body,
                                from_email='noreply@monksbugtracker.com',
                                recipient_list=[member.email]
                            )
                    else:
                        messages.warning(request, 'User does not exist or is not a member of this team.')
                elif (member_username := request.GET.get('remove')):
                    member = User.objects.get(username=member_username)
                    if member in project.developers.all():
                        project.developers.remove(member)
                    else:
                        messages.warning(request, 'User is not a project developer.')
            except User.DoesNotExist:
                messages.warning(request, 'User does not exist or is not a member of this team.')
            return super().get(request, *args, **kwargs)
        else:
            raise Http404







''' TICKET DETAILS/COMMENT HANDLING VIEWS
The following three classes (TicketDetails, TicketDetailsCommentPost, and SuperTicketDetails) are used to render a ticket DetailView and a comment CreateView-like on one page.
The general process comes from the official documentation: https://docs.djangoproject.com/en/3.0/topics/class-based-views/mixins/#an-alternative-better-solution
The basic links connecting the three classes:

SuperTicketDetails:
This is simply a super-view that controls which of the two subviews (TicketDetails and TicketDetailsCommentPost) gets displayed.
All it does is override the default View class's get() and post() methods.
If the method is get(), meaning the user simply visited the ticket details page, it returns the TicketDetails view.
If the method is post(), meaning the user posted a comment, it returns the TicketDetailsCommentPost view to handle the creation of the new comment.

TicketDetails:
extending the context by overriding get_context_data() method, adding a form_context key connected to the CommentForm() from forms.py
This allows the comment creation form to be displayed on the same template that references TicketDetails.

TicketDetailsCommentPost:
This does the heavy lifting. It inherits from FormView so we can easily save the data from the comment form, even though the form is initially displayed in the TicketDetails view from a get request.
First, template_name is defined the same as TicketDetails, because this view renders on the same template.
The associated form_class is the CommentForm from forms.py
The linked model is Ticket, even though this is for comment creation. The Comment model will be called later, on an actual post request.
Then the methods:
We override post() to return the self.ticket attribute and associate it with the TICKET we're looking at, not a comment. We need to be able to pull the pk from this ticket, as well as link it to a new comment.
The get_success_url() method returns us to the ticket_details url (where we currently are, but it will be a get request at that time), and sets pk = self.ticket.pk, i.e., the pk connected to the ticket object we retrieved in post()
Then the form_valid() method does the work of saving the comment. First, we pull the cleaned_data from the form ('comment' is the name of the form attribute as defined in CommentForm() in forms.py
The user is just the current user.
The ticket is the ticket object we pulled from post(), so we can link the newly created comment to the current ticket, since the comment's ForeignKey is Ticket.
Then we instantiate a Comment object with the given parameters and save it.

The rest of the work is done in the html template, ticket_details.html, and it's fairly straightforward.
Simply displays the comments associated with the current ticket and creates a form, using bootstrap4, connected to the form_context added in TicketDetails.
'''

#paginating
class TicketDetails(LoginRequiredMixin, ViewTicketMixin, CommonTemplateContextMixin, generic.DetailView):
    '''Displays the ticket details. Also provides additional context linked to the CommentForm so that a comment creation form can be rendered on the same template.'''
    model = models.Ticket
    template_name = 'tracker/ticket_details.html'
    context_object_name = 'ticket'

    def post(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['close_ticket_form'] = CloseTicketResolutionForm()
        context['file_upload_form'] = TicketFileUploadForm()
        page_obj = self.object.get_comments(self.request)
        context['page_obj'] = page_obj
        subscribed = self.request.user in self.get_object().subscribers.all()
        context['subscribed'] = subscribed
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('user').prefetch_related('developer').select_related('project')


class TicketDetailsCommentPost(LoginRequiredMixin, ViewTicketMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.detail.SingleObjectMixin, generic.FormView):
    '''Handles new comment creation through the form_valid() method. Gets the associated ticket with the post() method, in association with the model = models.Ticket attribute. This is so the comment can be linked to a ticket.'''
    template_name = 'tracker/ticket_details.html'
    form_class = CommentForm
    model = models.Ticket
    success_message = 'Comment created.'

    def post(self, request, *args, **kwargs):
        self.ticket = self.get_object() # this is the method that requires SingleObjectMixin, in association with the model = models.Ticket to know what model we're looking at
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        self.ticket.save()
        return reverse('tracker:ticket_details', kwargs={'pk': self.ticket.pk, 'team_slug': self.ticket.team.slug})

    def form_valid(self, form):
        text = form.cleaned_data['comment']
        user = self.request.user
        ticket = self.ticket
        new_comment = models.Comment(text=text, user=user, ticket=ticket)
        new_comment.save()
        return super().form_valid(form)


class TicketDetailsResolution(LoginRequiredMixin, ViewTicketMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.detail.SingleObjectMixin, generic.FormView):
    '''Handles the closing of a ticket and the form for the resolution field.'''
    template_name = 'tracker/ticket_details.html'
    form_class = CloseTicketResolutionForm
    model = models.Ticket
    success_message = 'Ticket closed.'

    def post(self, request, *args, **kwargs):
        user = self.request.user
        self.ticket = self.get_object()
        project = get_object_or_404(models.Project, pk=self.ticket.project.pk)
        team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
        if user in self.ticket.developer.all() or user == project.manager or user in team.get_owners():
            return super().post(request, *args, **kwargs)
        raise Http404

    def get_success_url(self):
        self.ticket.save()
        return reverse('tracker:project_details', kwargs={'project_pk': self.ticket.project.pk, 'team_slug': self.ticket.project.team.slug})

    def form_valid(self, form):
        if (resolution := form.cleaned_data['resolution']):
            self.ticket.resolution = resolution
        elif self.ticket.resolution:
            pass
        else:
            self.ticket.resolution = 'Unspecified.'
        self.ticket.status = 'closed'
        new_comment = models.Comment.objects.create(text='Closed.', user=self.request.user, ticket=self.ticket)
        new_comment.save()
        self.ticket.save()
        if not self.ticket.project.is_archived:
            email_tuples = []
            team = self.ticket.team
            project = self.ticket.project
            for subscriber in self.ticket.subscribers.all():
                if subscriber in team.members.all() and (
                    subscriber in project.developers.all() or subscriber == project.manager):
                    email_tuples.append((
                        f'Ticket closed: {self.ticket.title}',
                        f'Closed by {self.request.user}. Resolution: {self.ticket.resolution}',
                        'noreply@monksbugtracker.com',
                        [subscriber.email]
                    ))
            email_tuples = tuple(email_tuples)
            mail.send_mass_mail(email_tuples)
        return super().form_valid(form)


class TicketReopen(LoginRequiredMixin, ViewTicketMixin, SuccessMessageMixin, CommonTemplateContextMixin, generic.detail.SingleObjectMixin, View):
    model = models.Ticket

    def post(self, request, *args, **kwargs):
        user = self.request.user
        self.ticket = self.get_object()
        project = get_object_or_404(models.Project, pk=self.ticket.project.pk)
        team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
        if user in self.ticket.developer.all() or user == project.manager or user in team.get_owners():
            self.ticket.status = 'open'
            new_comment = models.Comment.objects.create(text='Reopened.', user=self.request.user, ticket=self.ticket)
            # new_comment.save()
            self.ticket.save()
            messages.info(request, 'Ticket reopened.')
            return HttpResponseRedirect(reverse('tracker:ticket_details', kwargs={'pk': self.ticket.pk, 'team_slug': self.kwargs['team_slug']}))
        raise Http404


class SuperTicketDetails(CommonTemplateContextMixin, View):
    '''A helper view: this is the view referenced in urls.py. It serves the TicketDetails view if the request method is GET and serves up different form views if the request method is POST.'''
    def get(self, request, *args, **kwargs):
        view = TicketDetails.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if 'post_comment' in request.POST:
            view = TicketDetailsCommentPost.as_view()
        elif 'close_ticket' in request.POST:
            view = TicketDetailsResolution.as_view()
        elif 'reopen_ticket' in request.POST:
            view = TicketReopen.as_view()
        elif 'upload_file' in request.POST:
            view = TicketFileUploadView.as_view()
        else:
            view = TicketDetails.as_view()
        return view(request, *args, **kwargs)

### END OF TICKET DETAILS/COMMENT HANDLING VIEWS ###

class CommentDelete(LoginRequiredMixin, CommonTemplateContextMixin, TeamMemberMixin, generic.DeleteView):
    model = models.Comment

    def post(self, request, *args, **kwargs):
        team = get_object_or_404(models.Team, slug=self.kwargs['team_slug'])
        comment = get_object_or_404(models.Comment, pk=self.kwargs['pk'])
        comment_submitter = comment.user
        if request.user in team.get_owners() or request.user == comment_submitter:
            return super().post(request, *args, **kwargs)
        messages.warning(request, "You do not have permission to delete that comment.")
        return HttpResponseRedirect(reverse_lazy('tracker:ticket_details', kwargs={'team_slug': team.slug, 'pk': comment.ticket.pk}))

    def get_success_url(self):
        ticket = self.get_object().ticket
        ticket.save()
        messages.info(self.request, 'Comment deleted.')
        return reverse_lazy('tracker:ticket_details', kwargs={'pk': ticket.pk, 'team_slug': ticket.team.slug})


class SubscribeTicketView(LoginRequiredMixin, CommonTemplateContextMixin, ViewTicketMixin, generic.detail.SingleObjectMixin, View):
    model = models.Ticket

    def get(self, request, *args, **kwargs):
        ticket = self.get_object()
        ticket.subscribers.add(request.user)
        ticket.save()
        messages.success(request, 'You will now receive emails when comments are posted to this ticket or when it is closed.')
        return HttpResponseRedirect(reverse('tracker:ticket_details', kwargs={'team_slug': ticket.team.slug, 'pk': ticket.pk}))


class UnsubscribeTicketView(LoginRequiredMixin, CommonTemplateContextMixin, ViewTicketMixin, generic.detail.SingleObjectMixin, View):
    model = models.Ticket

    def get(self, request, *args, **kwargs):
        ticket = self.get_object()
        ticket.subscribers.remove(request.user)
        ticket.save()
        messages.success(request, 'You will no longer receive emails when comments are posted to this ticket or when it is closed.')
        return HttpResponseRedirect(reverse('tracker:ticket_details', kwargs={'team_slug': ticket.team.slug, 'pk': ticket.pk}))


class MultipleUnsubscribeView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if (pks:=request.POST.getlist('check')):
            for pk in pks:
                ticket = get_object_or_404(models.Ticket, pk=pk)
                ticket.subscribers.remove(request.user)
            messages.success(request, f'Successfully unsubscribed from {len(pks)} tickets.')
        else:
            messages.warning(request, 'No tickets selected.')
        return HttpResponseRedirect(reverse('manage_subscriptions'))



# request.POST.getlist('check')
