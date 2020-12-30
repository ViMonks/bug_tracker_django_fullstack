import django_tables2 as tables
from django.db.models import Func, F, Case, When, CharField, Value
from bug_tracker_v2.tracker import models, views

PRIORITY_ORDERING = {
    'urgent': '1',
    'high': '2',
    'medium': '3',
    'low': '4'
}

# STATUS_ORDERING = {
#     'open': '1',
#     'assigned': '2',
#     'in_progress': '3',
#     'closed': '4'
# }

class TicketTable(tables.Table):

    title = tables.Column(accessor='title', verbose_name='Title', linkify=True)
    created_on = tables.DateTimeColumn(accessor='created_on', verbose_name='Created', format='m/d/y', order_by='-created_on')
    last_updated_on = tables.DateTimeColumn(accessor='last_updated_on', verbose_name='Updated', format='m/d/y', order_by='-last_updated_on')
    project = tables.Column(accessor='project', linkify=True)

    def order_title(self, queryset, is_descending): # making title ordering case-insensitive
        queryset = queryset.annotate(
            title_lower=Func(F('title'), function='LOWER')
        ).order_by(('-' if is_descending else '') + 'title_lower')
        return (queryset, True)

    def order_priority(self, queryset, is_descending):
        queryset = queryset.annotate(
            priority_order=Case(
                *[When(priority=i, then=Value(j)) for i, j in PRIORITY_ORDERING.items()], default=0, output_field=CharField()
            )
        ).order_by(('-' if is_descending else '') + 'priority_order')
        return (queryset, True)

    # def order_status(self, queryset, is_descending):
    #     queryset = queryset.annotate(
    #         status_order=Case(
    #             *[When(status=i, then=Value(j)) for i, j in STATUS_ORDERING.items()], default=0,
    #             output_field=CharField()
    #         )
    #     ).order_by(('-' if is_descending else '') + 'status_order')
    #     return (queryset, True)

    class Meta:
        model = models.Ticket
        fields = ('title', 'user', 'developer', 'project', 'priority', 'created_on', 'last_updated_on')
        template_name = 'django_tables2/bootstrap4.html'
        attrs = {'class': "table table-striped table-bordered table-hover table-sm"}
        order_by = 'created_on'


class ProjectTable(tables.Table):
    title = tables.Column(accessor='title', verbose_name='Title', linkify=True)
    manager = tables.Column(accessor='manager', verbose_name='Manager')
    open_tickets = tables.Column(accessor='open_tickets', verbose_name='Open Tickets')
    created_on = tables.DateTimeColumn(accessor='created_on', verbose_name='Created', format='m/d/y', order_by='-created_on') # format='M d, Y' for old version

    class Meta:
        model = models.Project
        fields = ('title', 'description', 'manager', 'created_on', 'open_tickets') # including project_tickets__count in this tuple works too, but allows less customization
        sequence = ('title', '...', 'created_on')
        template_name = 'django_tables2/bootstrap4.html'
        attrs = {'class': "table table-striped table-bordered table-hover table-sm"}
        order_by = 'created_on'


class SubscriptionsTable(tables.Table):
    # if the name of the 'check' column is ever changed, be sure to update the JavaScript in the template where this view
    # is displayed to reflect the new column name
    check = tables.CheckBoxColumn(accessor='pk', attrs = { "th__input": {"onclick": "toggle(this)"}}, orderable=False)
    title = tables.Column(accessor='title', verbose_name='Title', linkify=True)
    team = tables.Column(accessor='team', verbose_name='Team', linkify=True)
    project = tables.Column(accessor='project', verbose_name='Project', linkify=True)
    last_updated_on = tables.DateTimeColumn(accessor='last_updated_on', verbose_name='Updated', format='m/d/y', order_by='-last_updated_on')
    # unsub = tables.Column(
    #     accessor='title',
    #     verbose_name='',
    #     linkify=('tracker:unsubscribe_ticket', {'team_slug': tables.A('team__slug'), 'pk': tables.A('pk')}),
    #     orderable=False
    # )

    # def render_unsub(self, value):
    #     return "Unsubscribe"

    class Meta:
        model = models.Ticket
        fields = ('title', 'team', 'project')
        sequence = ('check', '...', 'last_updated_on')
        template_name = 'django_tables2/bootstrap4.html'
        attrs = {'class': "table table-striped table-bordered table-hover table-sm"}
        order_by = 'team'

