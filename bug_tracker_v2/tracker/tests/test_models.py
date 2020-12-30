from django.test import TestCase
from django.utils.text import slugify
from django.utils.html import mark_safe
from bug_tracker_v2.users.models import User

from markdown import markdown

from ..models import Team, Project, Ticket, Comment
from .utils_for_test_creation import create_team, team_add_manager

class TestTeam(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(title='Title', description='Description of team')

    def test_title(self):
        self.assertEqual('Title', self.team.title)

    def test_str_is_title(self):
        self.assertEqual(self.team.title, self.team.__str__())

    def test_slug(self):
        self.assertEqual(self.team.slug, slugify(self.team.title))

    def test_get_absolute_url(self):
        self.assertEqual(f'/teams/{self.team.slug}/', self.team.get_absolute_url())


class TestProject(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(title='Team Title', description='Description of team')
        cls.project = Project.objects.create(title='Title', description='Description of a project.', team=cls.team)

    def test_str_is_title(self):
        self.assertEqual(self.project.title, self.project.__str__())

    def test_get_description_as_markdown(self):
        self.assertEqual(mark_safe(markdown(self.project.description, extensions=['codehilite', 'fenced_code'])),
                         self.project.get_description_as_markdown())

    def test_project_team_assocation(self):
        self.assertEqual(self.team, self.project.team)

    def test_get_absolute_url(self):
        self.assertEqual(f'/teams/{self.project.team.slug}/projects/{self.project.pk}/', self.project.get_absolute_url())


class TestTicket(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='username', password='password')
        cls.team = Team.objects.create(title='Team Title', description='Description of team')
        cls.project = Project.objects.create(title='Project Title', description='Description of a project.', team=cls.team)
        cls.ticket = Ticket.objects.create(user=cls.user, title='Ticket Title', project=cls.project, team=cls.team,
                                           description='Ticket description', resolution='Ticket resolution')

    def test_str_is_title(self):
        self.assertEqual(self.ticket.title, self.ticket.__str__())

    def test_get_description_as_markdown(self):
        self.assertEqual(mark_safe(markdown(self.ticket.description, extensions=['codehilite', 'fenced_code'])),
                         self.ticket.get_description_as_markdown())

    def test_get_resolution_as_markdown(self):
        self.assertEqual(mark_safe(markdown(self.ticket.resolution, extensions=['codehilite', 'fenced_code'])),
                         self.ticket.get_resolution_as_markdown())

    def test_ticket_team_assocation(self):
        self.assertEqual(self.team, self.ticket.team)

    def test_ticket_project_association(self):
        self.assertEqual(self.project, self.ticket.project)

    def test_get_absolute_url(self):
        self.assertEqual(f'/teams/{self.ticket.team.slug}/tickets/{self.ticket.pk}/', self.ticket.get_absolute_url())


class TestComment(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='username', password='password')
        cls.team = Team.objects.create(title='Team Title', description='Description of team')
        cls.project = Project.objects.create(title='Project Title', description='Description of a project.',
                                             team=cls.team)
        cls.ticket = Ticket.objects.create(user=cls.user, title='Ticket Title', project=cls.project, team=cls.team,
                                           description='Ticket description', resolution='Ticket resolution')
        cls.comment = Comment.objects.create(user=cls.user, text='Comment body text.<strong>test</strong>', ticket=cls.ticket)

    def test_str_is_text(self):
        self.assertEqual(self.comment.text, self.comment.__str__())

    def test_get_text_as_markdown(self):
        self.assertEqual(mark_safe(markdown(self.comment.text, extensions=['codehilite', 'fenced_code'])),
                         self.comment.get_text_as_markdown())

    def test_get_absolute_url(self):
        self.assertEqual(f'/teams/{self.comment.ticket.team.slug}/tickets/{self.comment.ticket.pk}/', self.comment.get_absolute_url())


class TestProjectQueryset(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team_owner = User.objects.create_user(username='team_owner', password='password')
        cls.project_manager = User.objects.create_user(username='project_manager', password='password')
        cls.project_developer = User.objects.create_user(username='project_developer', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.team_owner)
        cls.other_team_owner = User.objects.create_user(username='other', password='password')
        cls.unowned_team = create_team(cls.other_team_owner, title='Unowned team')
        cls.linked_project = Project.objects.create(title='Project Title', description='This project is assigned a manager and developers',
                                             team=cls.team, manager=cls.project_manager)
        cls.linked_project.developers.add(cls.project_developer)
        cls.unlinked_project = Project.objects.create(title='Unlinked Project', description='This project has no manager or developers',
                                                      team=cls.team)
        cls.unowned_team_project = Project.objects.create(title='Title', description='Desc', team=cls.unowned_team)

    def test_project_developers_set(self):
        devs = [self.project_developer]
        self.assertQuerysetEqual(qs=self.linked_project.developers.all(), values=[repr(dev) for dev in devs])

    def test_filter_for_team_owner(self):
        projects = [self.linked_project, self.unlinked_project]
        self.assertQuerysetEqual(qs=Project.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.team_owner),
                                 values=[repr(project) for project in projects], ordered=False)

    def test_filter_for_manager(self):
        projects = [self.linked_project]
        self.assertQuerysetEqual(qs=Project.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.project_manager),
                                 values=[repr(project) for project in projects], ordered=False)

    def test_filter_for_developer(self):
        projects = [self.linked_project]
        self.assertQuerysetEqual(
            qs=Project.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.project_developer),
            values=[repr(project) for project in projects], ordered=False)

    def test_filter_for_non_member(self):
        projects = []
        self.assertQuerysetEqual(qs=Project.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.non_member),
                                 values=[repr(project) for project in projects], ordered=False)


class TestTicketQueryset(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team_owner = User.objects.create_user(username='team_owner', password='password')
        cls.project_manager = User.objects.create_user(username='project_manager', password='password')
        cls.project_developer = User.objects.create_user(username='project_developer', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.team_owner)
        cls.other_team_owner = User.objects.create_user(username='other', password='password')
        cls.unowned_team = create_team(cls.other_team_owner, title='Unowned team')
        cls.linked_project = Project.objects.create(title='Project Title', description='This project is assigned a manager and developers',
                                             team=cls.team, manager=cls.project_manager)
        cls.linked_project.developers.add(cls.project_developer)
        cls.unlinked_project = Project.objects.create(title='Unlinked Project', description='This project has no manager or developers',
                                                      team=cls.team)
        cls.unowned_team_project = Project.objects.create(title='Title', description='Desc', team=cls.unowned_team)
        cls.linked_project_ticket = Ticket.objects.create(user=cls.non_member, title='Ticket Title', project=cls.linked_project,
                          team=cls.team, description='Ticket description 1', resolution='Ticket resolution 1')
        cls.unlinked_project_ticket = Ticket.objects.create(user=cls.non_member, title='Ticket Title 2', project=cls.unlinked_project,
                          team=cls.team, description='Ticket description 1', resolution='Ticket resolution 1')
        cls.unowned_team_ticket = Ticket.objects.create(user=cls.non_member, title='Ticket TItle 3', project=cls.unowned_team_project,
                            team=cls.unowned_team, description='Desc', resolution='Resolution')

    def test_filter_for_team_owner(self):
        tickets = [self.linked_project_ticket, self.unlinked_project_ticket]
        self.assertQuerysetEqual(qs=Ticket.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.team_owner),
                                 values=[repr(ticket) for ticket in tickets], ordered=False)

    def test_filter_for_manager(self):
        tickets = [self.linked_project_ticket]
        self.assertQuerysetEqual(
            qs=Ticket.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.project_manager),
            values=[repr(ticket) for ticket in tickets], ordered=False)

    def test_filter_for_developer(self):
        tickets = [self.linked_project_ticket]
        self.assertQuerysetEqual(
            qs=Ticket.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.project_developer),
            values=[repr(ticket) for ticket in tickets], ordered=False)

    def test_filter_for_non_member(self):
        tickets = []
        self.assertQuerysetEqual(qs=Ticket.objects.filter_for_team_and_user(team_slug=self.team.slug, user=self.non_member),
                                 values=[repr(ticket) for ticket in tickets], ordered=False)
