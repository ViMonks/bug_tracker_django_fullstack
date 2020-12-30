from django.contrib.auth import get_user_model
import django_filters
from .models import Ticket, Project, Team
from django.forms import DateInput

User = get_user_model()

class TicketFilter(django_filters.FilterSet):
    # STATUS_CHOICES = (
    #     ('open', 'Open'),
    #     ('assigned', 'Assigned'),
    #     ('in_progress', 'In progress'),
    # )

    developer = django_filters.ModelChoiceFilter(queryset=lambda request: Team.objects.get(slug=request.resolver_match.kwargs['team_slug']).members.all(), null_label = 'Unassigned')
    title = django_filters.CharFilter(lookup_expr='icontains')
    user = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    created_start_date = django_filters.DateFilter(field_name='created_on', lookup_expr='date__gte', widget=DateInput(attrs={'type': 'date'}))
    created_end_date = django_filters.DateFilter(field_name='created_on', lookup_expr='date__lte', widget=DateInput(attrs={'type': 'date'}))
    updated_start_date = django_filters.DateFilter(field_name='last_updated_on', lookup_expr='date__gte', widget=DateInput(attrs={'type': 'date'}))
    updated_end_date = django_filters.DateFilter(field_name='last_updated_on', lookup_expr='date__lte', widget=DateInput(attrs={'type': 'date'}))
    # status = django_filters.ChoiceFilter(choices=STATUS_CHOICES)
    project = django_filters.ModelChoiceFilter(queryset=lambda request: Project.objects.filter_for_team_and_user(team_slug=request.resolver_match.kwargs['team_slug'], user=request.user).filter(is_archived=False))

    class Meta:
        model = Ticket
        exclude = ('description', 'team', 'status' )


class TicketFilterArchivedProjects(TicketFilter):
    project = django_filters.ModelChoiceFilter(queryset=lambda request: Project.objects.filter_for_team_and_user(team_slug=request.resolver_match.kwargs['team_slug'], user=request.user).filter(is_archived=True))


class ProjectFilter(django_filters.FilterSet):
    manager = django_filters.ModelChoiceFilter(queryset=lambda request: Team.objects.get(slug=request.resolver_match.kwargs['team_slug']).get_managers())
    title = django_filters.CharFilter(lookup_expr='icontains')
    start_date = django_filters.DateFilter(field_name='created_on', lookup_expr='date__gte', widget=DateInput(attrs={'type': 'date'}))
    end_date = django_filters.DateFilter(field_name='created_on', lookup_expr='date__lte', widget=DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Project
        exclude = ('description', 'team', )
