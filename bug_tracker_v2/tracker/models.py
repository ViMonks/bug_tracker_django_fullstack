import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.utils.html import mark_safe
from django.core import paginator, mail
from django.core.exceptions import ValidationError
from markdown import markdown

from .model_validators import ContentTypeRestrictedFileField
from .signals import unique_slug_generator
from .constants import NOTIFICATION_SETTING_DEFAULTS

User = get_user_model()


class ProjectQueryset(models.QuerySet):
    def filter_for_team_and_user(self, team_slug, user):
        team = Team.objects.get(slug=team_slug)
        if user in team.get_owners():
            return self.filter(team__slug=team_slug)
        else:
            return self.filter(Q(team__slug=team_slug), Q(manager=user)|Q(developers=user))


class TicketQueryset(models.QuerySet):
    def filter_for_team_and_user(self, team_slug, user):
        team = Team.objects.get(slug=team_slug)
        if user in team.get_owners():
            return self.filter(team__slug=team_slug)
        else:
            return self.filter(Q(team__slug=team_slug), Q(project__manager=user)|Q(project__developers=user))


# owned_teams = models.Team.objects.filter(memberships__role=3, memberships__user=self.request.user).order_by('title')

class TeamQueryset(models.QuerySet):
    def user_owned_teams(self, user):
        return self.filter(memberships__role=3, memberships__user=user)

    def user_managed_teams(self, user):
        return self.filter(memberships__role=2, memberships__user=user)

    def user_member_teams(self, user):
        return self.filter(memberships__role=1, memberships__user=user)


class Team(models.Model):
    title = models.CharField(unique=True, max_length=255)
    description = models.TextField()
    members = models.ManyToManyField(User, related_name='teams', blank=True, through='TeamMembership')
    slug = models.SlugField(unique=True)

    objects = models.Manager.from_queryset(TeamQueryset)()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('team_details', kwargs={'team_slug': self.slug})

    def save(self, *args, **kwargs):
        self.slug = self.slug or unique_slug_generator(self)
        super().save(*args, **kwargs)

    def get_description_as_markdown(self):
        return mark_safe(markdown(self.description, extensions=['codehilite', 'fenced_code']))

    def get_managers(self):
        return self.members.filter(memberships__role=2)

    def get_owners(self):
        return self.members.filter(memberships__role=3)

    def get_only_members(self):
        return self.members.filter(memberships__role=1)

    def add_owner(self, user):
        if user in self.get_managers() or user in self.get_only_members():
            membership = user.memberships.get(user=user, team=self)
            membership.role = 3
            membership.save()

    def remove_owner(self, user):
        if self.get_owners().count() > 1:
            if user in self.get_owners():
                membership = user.memberships.get(user=user, team=self)
                membership.role = 1
                membership.save()
                return True
        return False

    def add_manager(self, user):
        if user in self.get_only_members():
            membership = user.memberships.get(user=user, team=self)
            if membership.role != 3:
                membership.role = 2
                membership.save()

    def remove_manager(self, user):
        if user in self.get_managers():
            membership = user.memberships.get(user=user, team=self)
            if membership.role != 3:
                membership.role = 1
                membership.save()
                self.projects.filter(manager=user).update(manager=None)

    def remove_member(self, user):
        if user in self.members.all() and user not in self.get_owners():
            membership = user.memberships.get(user=user, team=self)
            if membership.role == 2:
                self.projects.filter(manager=user).update(manager=None)
            Project.developers.through.objects.filter(project__in=self.projects.all(), user=user).delete()
            Ticket.developer.through.objects.filter(ticket__team=self, user=user).delete()
            membership.delete()

    def get_users_role(self, user):
        membership = user.memberships.get(user=user, team=self)
        return membership.role


class TeamMembership(models.Model):

    MEMBER = 1
    MANAGER = 2
    OWNER = 3

    ROLES = (
        (MEMBER, "Member",),
        (MANAGER, "Manager",),
        (OWNER, "Owner",),
            )

    team = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id', related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='memberships')
    role = models.IntegerField(choices=ROLES, default=MEMBER)

    class Meta:
        db_table = 'tracker_team_members'
        unique_together = ('user', 'team',)

    def __str__(self):
        return f'{self.user}-{self.team}'


class TeamInvitation(models.Model):
    PENDING = 1
    ACCEPTED = 2
    DECLINED = 3

    STATUSES = (
        (PENDING, 'Pending',),
        (ACCEPTED, 'Accepted',),
        (DECLINED, 'Declined',),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, default=None, null=True, blank=True)
    invitee_email = models.EmailField()
    # is_accepted = models.BooleanField(default=False)
    created_on = models.DateField(auto_now_add=True, editable=False)
    status = models.IntegerField(choices=STATUSES, default=PENDING)

    def send_email(self, inviter, team, invitation_uuid):
        domain = get_current_site(request=None).domain
        message_text = f"""You have been invited to join {team} by {inviter}.
If you are already registered, click this link to accept this invitation: https://{domain}{(reverse('accept_team_invitation'))}?invitation={invitation_uuid}.
If you are not registered, click this link to register first: https://{domain}/accounts/signup."""
        mail.send_mail(
            subject='Team Invitation',
            message=message_text,
            from_email='noreply@monksbugtracker.com',
            recipient_list=[self.invitee_email]
        )


class Project(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    manager = models.ForeignKey(User, related_name='assigned_projects', on_delete=models.CASCADE, null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    developers = models.ManyToManyField(User, related_name='developer_assigned_projects', blank=True)
    team = models.ForeignKey(Team, related_name='projects', on_delete=models.SET_NULL, null=True)
    subscribers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='project_subscriptions', blank=True)

    objects = models.Manager.from_queryset(ProjectQueryset)()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tracker:project_details', kwargs={'project_pk': self.pk, 'team_slug': self.team.slug})

    def get_description_as_markdown(self):
        return mark_safe(markdown(self.description, extensions=['codehilite', 'fenced_code']))


class Ticket(models.Model):
    # ticket priority constants
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'
    PRIORITY_CHOICES = [(LOW, 'Low'), (MEDIUM, 'Medium'), (HIGH, 'High'), (URGENT, 'Urgent')]

    # ticket status constants
    OPEN = 'open'
    # ASSIGNED = 'assigned'
    # IN_PROGRESS = 'in_progress'
    CLOSED = 'closed'
    STATUS_CHOICES = ((OPEN, 'Open'), (CLOSED, 'Closed'))

    user = models.ForeignKey(User, related_name='tickets', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    resolution = models.TextField(null=True, default=None, blank=True)
    developer = models.ManyToManyField(User, related_name='assigned_tickets', blank=True)
    project = models.ForeignKey(Project, related_name='project_tickets', on_delete=models.CASCADE)
    priority = models.CharField(choices=PRIORITY_CHOICES, default=LOW, max_length=50)
    status = models.CharField(choices=STATUS_CHOICES, default=OPEN, max_length=50)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated_on = models.DateTimeField(auto_now=True)
    team = models.ForeignKey(Team, related_name='tickets', on_delete=models.SET_NULL, null=True)
    subscribers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='ticket_subscriptions', blank=True)

    objects = models.Manager.from_queryset(TicketQueryset)()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tracker:ticket_details', kwargs={'pk': self.pk, 'team_slug': self.team.slug})

    def get_description_as_markdown(self):
        return mark_safe(markdown(self.description, extensions=['codehilite', 'fenced_code']))

    def get_resolution_as_markdown(self):
        return mark_safe(markdown(self.resolution, extensions=['codehilite', 'fenced_code']))

    def save(self, *args, **kwargs):
        created = False
        if self.pk == None:
            created = True
        super().save(*args, **kwargs)
        if created:
            email_tuples = []
            team = self.team
            project = self.project
            if self.user in team.members.all():
                notification_preference = self.user.notification_settings.get(
                    'auto_subscribe_to_submitted_tickets', NOTIFICATION_SETTING_DEFAULTS.get('auto_subscribe_to_submitted_tickets', True)
                )
                if notification_preference:
                    self.subscribers.add(self.user)
            for user in project.subscribers.all():
                self.subscribers.add(user)
                if user in team.members.all() and (user in project.developers.all() or user == project.manager):
                    email_tuples.append((
                        f'New ticket submitted to subscribed project {project.title}: {self.title}',
                        f'A new ticket has been posted to the project {project.title}: {self.title}',
                        'noreply@monksbugtracker.com',
                        [user.email]
                    ))
            if email_tuples:
                email_tuples = tuple(email_tuples)
                mail.send_mass_mail(email_tuples)

    def get_comments(self, request):
        queryset = self.comments.all()
        paginator_instance = paginator.Paginator(queryset, 8)
        page = request.GET.get('page')
        page_obj = paginator_instance.get_page(page)
        return page_obj


class Comment(models.Model):
    user = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    ticket = models.ForeignKey(Ticket, related_name='comments', on_delete=models.CASCADE)

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        """After comment is posted, return to ticket_details view with pk equal to the comment's linked ticket.pk"""
        return reverse('tracker:ticket_details', kwargs={'pk': self.ticket.pk, 'team_slug': self.ticket.team.slug})

    def get_text_as_markdown(self):
        return mark_safe(markdown(self.text, extensions=['codehilite', 'fenced_code']))

    def save(self, *args, **kwargs):
        if self.ticket.status == 'open' and not self.ticket.project.is_archived:
            email_tuples = []
            team = self.ticket.team
            project = self.ticket.project
            for subscriber in self.ticket.subscribers.all():
                if subscriber in team.members.all() and (subscriber in project.developers.all() or subscriber == project.manager):
                    email_tuples.append((
                        f'New comment on subscribed ticket: {self.ticket.title}',
                        f'Comment posted by {self.user}: {self.text}',
                        'noreply@monksbugtracker.com',
                        [subscriber.email]
                    ))
            email_tuples = tuple(email_tuples)
            mail.send_mass_mail(email_tuples)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_on']


def ticket_file_upload_path(instance, filename):
    return f'ticket_files/{instance.ticket.title}/{filename}'

class TicketFile(models.Model):
    title = models.CharField(max_length=200)
    ticket = models.ForeignKey(Ticket, related_name='files', on_delete=models.CASCADE)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='uploads', on_delete=models.SET_NULL, null=True)
    file = ContentTypeRestrictedFileField(
        upload_to=ticket_file_upload_path,
        content_types=['application/pdf', 'application/json', 'application/zip', 'audio/mpeg', 'image/gif', 'image/jpeg', 'image/png', 'image/tiff', 'text/csv', 'text/html', 'text/plain', 'video/mpeg', 'video/mp4'],
        max_upload_size= 10 * 1024 * 1024
    )

    class Meta:
        unique_together = ('ticket', 'title',)

    def __str__(self):
        return self.title
