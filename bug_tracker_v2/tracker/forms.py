from django import forms
from django.core.exceptions import ValidationError

from . import models

class CommentForm(forms.Form):
    #comment = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Add new comment'})) # use TextInput widget if we want a small, one-line input
    comment = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'Add new comment', 'rows': 10}))


class CloseTicketResolutionForm(forms.Form):
    resolution = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'How did you resolve the ticket?', 'rows': 10}), required=False)


class ProjectForm(forms.ModelForm):

    class Meta:
        model = models.Project
        fields = ['title', 'description', 'manager']

    def __init__(self, *args, **kwargs):
        team_slug = kwargs.pop('team_slug')
        super(ProjectForm, self).__init__(*args, **kwargs)
        team = models.Team.objects.get(slug=team_slug)
        managers_or_owners = team.get_managers() | team.get_owners()
        self.fields['manager'].queryset = managers_or_owners


class CreateTicketForm(forms.ModelForm):

    class Meta:
        model = models.Ticket
        fields = ['title', 'description', 'developer', 'priority']

    def __init__(self, *args, **kwargs):
        project_pk = kwargs.pop('project_pk')
        super().__init__(*args, **kwargs)
        project = models.Project.objects.get(pk=project_pk)
        project_developers = project.developers.all()
        self.fields['developer'].queryset = project_developers


class UpdateTicketForm(CreateTicketForm):

    class Meta:
        model = models.Ticket
        fields = ['title', 'description', 'developer', 'priority', 'resolution']


class TicketFileUploadForm(forms.ModelForm):

    class Meta:
        model = models.TicketFile
        fields = ['title', 'file']
