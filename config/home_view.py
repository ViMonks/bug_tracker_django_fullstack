from django.views.generic import TemplateView

from bug_tracker_v2.tracker.models import Project

class CommonTemplateContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if kwargs.get('team_pk'):
            context.setdefault('team_pk', kwargs.get('team_pk'))
        return context

class HomePage(CommonTemplateContextMixin, TemplateView):
    template_name = 'pages/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            if (project_pk := self.request.user.last_viewed_project_pk):
                context['last_viewed_project_pk'] = project_pk
                last_viewed_project = Project.objects.get(pk=project_pk)
                context['last_viewed_project'] = last_viewed_project
        # context['current_team_pk'] = self.kwargs['team_pk']
        return context
