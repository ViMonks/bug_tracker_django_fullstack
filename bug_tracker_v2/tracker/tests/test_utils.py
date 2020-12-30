from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.http import Http404

from bug_tracker_v2.users.models import User
from bug_tracker_v2.users.tests.factories import UserFactory
from .. import views
from ..models import Team, Project, Ticket, Comment

from .utils_for_test_creation import create_team, team_add_manager


class TestLastViewedProjectPkUserAttributeAssignment(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.team = create_team(self.user)
        self.project = Project.objects.create(title='Project Title', description='desc', manager=self.user, team=self.team)
        self.url = reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})

    def test_pk_attribute_assignment(self):
        self.client.force_login(self.user)
        self.assertEqual(None, self.user.last_viewed_project_pk)
        self.client.get(self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.project.pk, self.user.last_viewed_project_pk)

    def test_pk_overwritten_when_new_project_viewed(self):
        new_project = Project.objects.create(title='New Project', description='desc', manager=self.user, team=self.team)
        self.client.force_login(self.user)
        self.assertEqual(None, self.user.last_viewed_project_pk)
        self.client.get(self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.project.pk, self.user.last_viewed_project_pk)
        self.client.get(reverse(
            'tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': new_project.pk}
        ))
        self.user.refresh_from_db()
        self.assertEqual(new_project.pk, self.user.last_viewed_project_pk)

    def test_pk_not_overwritten_when_non_project_view_accessed(self):
        self.client.force_login(self.user)
        self.assertEqual(None, self.user.last_viewed_project_pk)
        self.client.get(self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.project.pk, self.user.last_viewed_project_pk)
        response = self.client.get(reverse(
            'tracker:project_list', kwargs={'team_slug': self.team.slug}
        ))
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.project.pk, self.user.last_viewed_project_pk)

    # def test_project_pk_in_homepage_context(self):
    #     self.client.force_login(self.user)
    #     self.assertEqual(None, self.user.last_viewed_project_pk)
    #     self.client.get(self.url)
    #     response = self.client.get('/')
    #     self.assertEqual(response.status_code, 200)
    #     self.assertIn('last_viewed_project_pk', response.context)
    #     self.assertIn('last_viewed_project', response.context)
    #     self.assertEqual(response.context['last_viewed_project_pk'], self.project.pk)
    #     self.assertEqual(response.context['last_viewed_project'], self.project)

    def test_homepage_context_when_no_project_pk_exists(self):
        self.client.force_login(self.user)
        self.assertEqual(None, self.user.last_viewed_project_pk)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('last_viewed_project_pk', response.context)
        self.assertNotIn('last_viewed_project', response.context)

    def test_project_details_link_appears_in_home_page(self):
        self.client.force_login(self.user)
        self.assertEqual(None, self.user.last_viewed_project_pk)
        self.client.get(self.url)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.url, response.content.decode('utf8')
        )
