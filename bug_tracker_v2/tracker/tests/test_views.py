from datetime import date, timedelta

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.http import Http404
from django.core import mail

from bug_tracker_v2.users.models import User
from bug_tracker_v2.users.tests.factories import UserFactory
from .. import views
from ..models import Team, Project, Ticket, Comment, TeamInvitation
from ..models import TeamMembership as Membership

from .utils_for_test_creation import create_team, team_add_manager, team_add_member, user

class TestCommonTemplateContextMixin(TestCase):
    def setUp(self):
        self.team_owner = User.objects.create_user(username='team_owner', password='password')
        self.team = Team.objects.create(title='Test Team', description='desc')
        self.team_owner.memberships.create(team=self.team, user=self.team_owner, role=3)

    def test_context_exists(self):
        self.client.login(username='team_owner', password='password')
        response = self.client.get('/teams/test-team/')
        self.assertIn('current_team', response.context)
        self.assertIn('team_pk', response.context)
        self.assertIn('team_name', response.context)
        self.assertIn('team_slug', response.context)

    def test_context_content(self):
        self.client.login(username='team_owner', password='password')
        response = self.client.get('/teams/test-team/')
        self.assertEqual(self.team, response.context['current_team'])
        self.assertEqual(self.team.pk, response.context['team_pk'])
        self.assertEqual(self.team.title, response.context['team_name'])
        self.assertEqual('test-team', response.context['team_slug'])


# Team-related views

class TestTeamDetailsView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.team_owner = User.objects.create_user(username='team_owner', password='password')
        self.team_manager = User.objects.create_user(username='manager', password='password')
        self.team_member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        self.team = Team.objects.create(title='Test Team', description='desc')
        self.team_owner.memberships.create(team=self.team, user=self.team_owner, role=3)
        self.team.members.add(self.team_member)
        self.team_manager.memberships.create(team=self.team, user=self.team_manager, role=2)

    def test_not_logged_in(self):
        request = self.factory.get('/teams/test-team/')
        request.user = AnonymousUser()
        response = views.TeamDetails.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/accounts/login/?next=/teams/test-team/')

    def test_team_slug(self):
        self.assertEqual(self.team.slug, 'test-team')

    def test_view_permissions_owner_rf(self):
        request = self.factory.get('/teams/test-team/')
        request.user = self.team_owner
        response = views.TeamDetails.as_view()(request, team_slug='test-team')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Team')

    def test_view_permissions_owner(self):
        self.client.login(username='team_owner', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response=response, text='Test Team')
        self.assertContains(response, 'Update Team')

    def test_view_permissions_owner_manual_url(self):
        self.client.login(username='team_owner', password='password')
        response = self.client.get('/teams/test-team/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Team')

    def test_view_permissions_member(self):
        self.client.login(username='member', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response=response, text='Test Team')
        self.assertNotContains(response, 'Update Team')

    def test_view_permissions_manager(self):
        self.client.login(username='manager', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response=response, text='Test Team')
        self.assertNotContains(response, 'Update Team')

    def test_view_permissions_non_member(self):
        self.client.login(username='non_member', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(response.status_code, 404)

    def test_context_exists_owner(self):
        self.client.login(username='team_owner', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertIn('current_team', response.context)
        self.assertIn('team_pk', response.context)
        self.assertIn('team_name', response.context)
        self.assertIn('team_slug', response.context)
        self.assertIn('managers', response.context)
        self.assertIn('non_managers', response.context)

    def test_context_content_owner(self):
        self.client.login(username='team_owner', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(self.team, response.context['current_team'])
        self.assertEqual(self.team.pk, response.context['team_pk'])
        self.assertEqual(self.team.title, response.context['team_name'])
        self.assertEqual('test-team', response.context['team_slug'])
        self.assertIn(self.team_manager, response.context['managers'])
        self.assertNotIn(self.team_member, response.context['managers'])
        self.assertIn(self.team_member, response.context['non_managers'])
        self.assertNotIn(self.team_manager, response.context['non_managers'])

    def test_context_exists_manager(self):
        self.client.login(username='manager', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertIn('current_team', response.context)
        self.assertIn('team_pk', response.context)
        self.assertIn('team_name', response.context)
        self.assertIn('team_slug', response.context)
        self.assertIn('managers', response.context)
        self.assertIn('non_managers', response.context)

    def test_context_content_manager(self):
        self.client.login(username='manager', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(self.team, response.context['current_team'])
        self.assertEqual(self.team.pk, response.context['team_pk'])
        self.assertEqual(self.team.title, response.context['team_name'])
        self.assertEqual('test-team', response.context['team_slug'])
        self.assertIn(self.team_manager, response.context['managers'])
        self.assertNotIn(self.team_member, response.context['managers'])
        self.assertIn(self.team_member, response.context['non_managers'])
        self.assertNotIn(self.team_manager, response.context['non_managers'])

    def test_context_exists_member(self):
        self.client.login(username='member', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertIn('current_team', response.context)
        self.assertIn('team_pk', response.context)
        self.assertIn('team_name', response.context)
        self.assertIn('team_slug', response.context)
        self.assertIn('managers', response.context)
        self.assertIn('non_managers', response.context)

    def test_context_content_member(self):
        self.client.login(username='member', password='password')
        response = self.client.get(reverse('team_details', kwargs={'team_slug': 'test-team'}))
        self.assertEqual(self.team, response.context['current_team'])
        self.assertEqual(self.team.pk, response.context['team_pk'])
        self.assertEqual(self.team.title, response.context['team_name'])
        self.assertEqual('test-team', response.context['team_slug'])
        self.assertIn(self.team_manager, response.context['managers'])
        self.assertNotIn(self.team_member, response.context['managers'])
        self.assertIn(self.team_member, response.context['non_managers'])
        self.assertNotIn(self.team_manager, response.context['non_managers'])


class TestTeamListView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.other_user = User.objects.create_user(username='other_user', password='password')
        self.owned_team = Team.objects.create(title='owned', description='desc')
        Membership.objects.create(team=self.owned_team, user=self.user, role=3)
        self.member_team = Team.objects.create(title='unowned', description='desc')
        Membership.objects.create(team=self.member_team, user=self.other_user, role=3)
        self.member_team.members.add(self.user)
        self.unassociated_team = Team.objects.create(title='unassociated', description='desc')
        Membership.objects.create(team=self.unassociated_team, user=self.other_user, role=3)

    def test_queryset(self):
        self.client.login(username='user', password='password')
        response = self.client.get('/teams/')
        self.assertQuerysetEqual(
            qs=response.context['teams']['owned_teams'],
            values=Team.objects.filter(memberships__role=3, memberships__user=self.user).order_by('title'),
            transform=lambda x: x
        )
        self.assertQuerysetEqual(
            qs=response.context['teams']['member_teams'],
            values=Team.objects.filter(memberships__role=1, memberships__user=self.user).order_by('title'),
            transform=lambda x: x
        )

    def test_response_content(self):
        self.client.login(username='user', password='password')
        response = self.client.get('/teams/')
        self.assertContains(response, 'owned')
        self.assertContains(response, 'unowned')
        self.assertContains(response, 'My Teams')
        self.assertContains(response, 'Teams I\'ve Joined')
        self.assertNotContains(response, 'unassociated')


class TestTeamCreateView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.form_data = {'title': 'Team Title', 'description': 'desc'}

    def test_response_get(self):
        self.client.force_login(self.user)
        response = self.client.get('/create-team/')
        self.assertEqual(response.status_code, 200)

    def test_response_post_no_follow(self):
        self.client.force_login(self.user)
        response = self.client.post('/create-team/', self.form_data)
        self.assertEqual(response.status_code, 302)

    def test_response_post_follow(self):
        self.client.force_login(self.user)
        response = self.client.post('/create-team/', self.form_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_post_redirect_chain(self):
        self.client.force_login(self.user)
        response = self.client.post('/create-team/', self.form_data, follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('team_details', kwargs={'team_slug': 'team-title'}))

    def test_team_created(self):
        self.assertEqual(Team.objects.all().count(), 0) # assert that no teams exist initially
        self.client.force_login(self.user)
        self.client.post('/create-team/', self.form_data, follow=True)
        self.assertEqual(Team.objects.all().count(), 1) # assert that a team has been created
        team = Team.objects.all().first()
        self.assertEqual(team.title, 'Team Title')  # assert team title is saved from form
        self.assertEqual(team.slug, 'team-title')  # assert that slug is properly formed
        self.assertIn(self.user, team.get_owners())  # assert that the user is assigned as the team's owner

    def test_success_message(self):
        self.client.force_login(self.user)
        response = self.client.post('/create-team/', self.form_data, follow=True)
        self.assertContains(response, 'Team Title created.')


class TestTeamUpdateView(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        self.team = Team.objects.create(title='Team Title', description='desc')
        Membership.objects.create(team=self.team, user=self.owner, role=3)
        Membership.objects.create(team=self.team, user=self.manager, role=2)
        self.team.members.add(self.member)
        self.form_data = {'description': 'New description'}

    def test_owner_permissions(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:team_update', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 200)

    def test_manager_permissions(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('tracker:team_update', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 404)

    def test_member_permissions(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('tracker:team_update', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 404)

    def test_non_member_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.get(reverse('tracker:team_update', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 404)

    # can't get members field to work
    def test_team_updated(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.team.description, 'desc')
        response = self.client.post(reverse('tracker:team_update', kwargs={'team_slug': self.team.slug}), data=self.form_data)
        self.assertEqual(response.status_code, 302)
        # self.assertEqual(response.context['form'].errors, 0)
        self.team.refresh_from_db()
        self.assertEqual(self.team.description, 'New description')


class TestTeamAddManager(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.manager.email = 'valid@email.com'
        self.manager.save()
        self.non_member = User.objects.create_user(username='non_member', password='password')
        self.team = Team.objects.create(title='Title', description='desc')
        Membership.objects.create(team=self.team, user=self.owner, role=3)
        self.team.members.add(self.manager) # not setting this user as a manager initially, as that is what this is testing

    def test_manager_added(self):
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/?username=manager')
        self.assertIn(self.manager, self.team.get_managers())

    def test_manager_receives_email_notification(self):
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/?username=manager')
        self.assertEqual(len(mail.outbox), 1)

    def test_email_subject(self):
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/?username=manager')
        self.assertIn(self.team.title, mail.outbox[0].subject)

    def test_email_body(self):
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/?username=manager')
        self.assertIn(self.team.title, mail.outbox[0].body)

    def test_email_to(self):
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/?username=manager')
        self.assertIn(self.manager.email, mail.outbox[0].to)

    def test_adding_non_member_as_manager(self):
        """Should redirect to team details view with a message (using Django messages system) about adding non-member or nonexistent user
        as manager. Does not specify which to obfuscate whether user with a given username exists."""
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/', {'username': 'non_member'}, follow=True)
        self.assertNotIn(self.non_member, self.team.get_managers())
        self.assertEqual(self.team.get_managers().count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': 'title'}))
        self.assertContains(response, 'Cannot make manager. User either does not exist or is not a member of your team.')

    def test_adding_nonexistent_user_as_manager(self):
        """Should redirect to team details view with a message (using Django messages system) about adding non-member or nonexistent user
        as manager. Does not specify which to obfuscate whether user with a given username exists."""
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager/', {'username': 'not_a_user'}, follow=True)
        self.assertEqual(self.team.get_managers().count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': 'title'}))
        self.assertContains(response, 'Cannot make manager. User either does not exist or is not a member of your team.')

    def test_permissions_manager(self):
        """Testing that the manager cannot add itself, as it is not the team owner."""
        self.client.force_login(self.manager)
        response = self.client.get('/teams/title/add-manager', {'username': 'manager'})
        self.assertNotIn(self.manager, self.team.get_managers())

    def test_permissions_non_member(self):
        """Testing that the non-member cannot add the manager, as it is not the team owner nor in the team."""
        self.client.force_login(self.non_member)
        response = self.client.get('/teams/title/add-manager', {'username': 'manager'})
        self.assertNotIn(self.manager, self.team.get_managers())

    def test_permissions_non_member_response_code(self):
        self.client.force_login(self.non_member)
        response = self.client.get('/teams/title/add-manager/', {'username': 'manager'})
        self.assertEqual(response.status_code, 404)

    def test_redirect(self):
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager', {'username': 'manager'}, follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('team_details', kwargs={'team_slug': 'title'}))

    def test_context_after_redirect(self):
        self.client.force_login(self.owner)
        response = self.client.get('/teams/title/add-manager', {'username': 'manager'}, follow=True)
        self.assertIn(self.manager, response.context['managers'])

    def test_anonymous_user_is_redirected_to_login(self):
        url = '/teams/title/add-manager/?username=manager'
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)


class TestAcceptTeamInvitationView(TestCase):
    def setUp(self):
        self.inviter = User.objects.create_user(username='inviter', password='password')
        self.invitee = User.objects.create_user(username='invitee', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.team = create_team(self.inviter)
        team_add_member(self.member, self.team)
        self.invitation = TeamInvitation.objects.create(team=self.team, invitee_email='valid@email.com')
        self.url = reverse('accept_team_invitation')

    def test_accepting_invite_response_status_code(self):
        self.assertEqual(self.team.members.all().count(), 2)
        self.client.force_login(self.invitee)
        response = self.client.get(self.url+f'?invitation={self.invitation.id}', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_accepting_invite_adds_member(self):
        self.assertEqual(self.team.members.all().count(), 2)
        self.client.force_login(self.invitee)
        response = self.client.get(self.url+f'?invitation={self.invitation.id}', follow=True)
        self.team.refresh_from_db()
        self.assertEqual(self.team.members.all().count(), 3)
        self.assertIn(self.invitee, self.team.members.all())

    def test_accepting_invite_redirects(self):
        self.client.force_login(self.invitee)
        response = self.client.get(self.url + f'?invitation={self.invitation.id}', follow=True)
        self.assertRedirects(response, reverse('tracker:team_details', kwargs={'team_slug': self.team.slug}))

    def test_anonymous_user(self):
        response = self.client.get(self.url + f'?invitation={self.invitation.id}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.team.members.all().count(), 2)

    def test_user_is_already_a_member(self):
        self.assertEqual(self.team.members.all().count(), 2)
        self.client.force_login(self.member)
        response = self.client.get(self.url + f'?invitation={self.invitation.id}', follow=True)
        self.team.refresh_from_db()
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tracker:team_details', kwargs={'team_slug': self.team.slug}))

    def test_invitation_status_updated(self):
        self.assertEqual(self.invitation.status, self.invitation.PENDING)
        self.client.force_login(self.invitee)
        self.client.get(self.url + f'?invitation={self.invitation.id}', follow=True)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, self.invitation.ACCEPTED)

    def test_already_accepted_invitation_unusable(self):
        accepted_invite = TeamInvitation.objects.create(team=self.team, invitee_email='valid@email.com', status=2)
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertNotIn(self.invitee, self.team.members.all())
        self.client.force_login(self.invitee)
        response = self.client.get(self.url + f'?invitation={accepted_invite.id}', follow=True)
        self.assertNotIn(self.invitee, self.team.members.all())
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.url)

    def test_bad_uuid(self):
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertNotIn(self.invitee, self.team.members.all())
        self.client.force_login(self.invitee)
        response = self.client.get(self.url + f'?invitation=this_is_not_a_valid_uuid', follow=True)
        self.assertNotIn(self.invitee, self.team.members.all())
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.url)

    def test_expired_invitation(self):
        expired_date = date.today() - timedelta(days=999)
        TeamInvitation.objects.all().update(created_on=expired_date)
        self.invitation.refresh_from_db()
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertNotIn(self.invitee, self.team.members.all())
        self.client.force_login(self.invitee)
        response = self.client.get(self.url + f'?invitation={self.invitation.id}', follow=True)
        self.assertNotIn(self.invitee, self.team.members.all())
        self.assertEqual(self.team.members.all().count(), 2)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.url)


class TestDeclineTeamInvitationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inviter = user('inviter')
        cls.invitee = user('invitee')
        cls.invitee.email = 'valid@email.com'
        cls.invitee.save()
        cls.non_invitee = user('non_invitee')
        cls.non_invitee.email = 'other@email.com'
        cls.non_invitee.save()
        cls.team = create_team(cls.inviter)
        team_add_member(cls.non_invitee, cls.team)
        cls.url = reverse('decline_team_invitation')

    def test_invitation_object_created(self):
        self.client.force_login(self.inviter)
        self.client.post(
            reverse('team_invite', kwargs={'team_slug': self.team.slug}),
            data={'invitee': self.invitee.username}
        )
        invite = TeamInvitation.objects.all().first()
        self.assertEqual(invite.invitee, self.invitee)

    def test_invitee_can_decline_linked_invite(self):
        invitation = TeamInvitation.objects.create(team=self.team, invitee=self.invitee, invitee_email=self.invitee.email)
        self.assertEqual(invitation.status, invitation.PENDING)
        self.client.force_login(self.invitee)
        response = self.client.get(self.url+f'?invitation={invitation.id}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('pending_invitations'))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, invitation.DECLINED)

    def test_invitee_can_decline_unlinked_invite(self):
        invitation = TeamInvitation.objects.create(team=self.team, invitee_email='random@email.com')
        self.assertEqual(invitation.status, invitation.PENDING)
        self.client.force_login(self.invitee)
        response = self.client.get(self.url+f'?invitation={invitation.id}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('pending_invitations'))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, invitation.DECLINED)

    def test_invitee_cannot_decline_others_invite(self):
        invitation = TeamInvitation.objects.create(team=self.team, invitee=self.non_invitee, invitee_email=self.non_invitee.email)
        self.assertEqual(invitation.status, invitation.PENDING)
        self.client.force_login(self.invitee)
        response = self.client.get(self.url+f'?invitation={invitation.id}', follow=True)
        self.assertEqual(response.status_code, 404)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, invitation.PENDING)

    def test_anonymous_user(self):
        invitation = TeamInvitation.objects.create(team=self.team, invitee=self.non_invitee,
                                                   invitee_email=self.non_invitee.email)
        self.assertEqual(invitation.status, invitation.PENDING)
        response = self.client.get(self.url + f'?invitation={invitation.id}')
        self.assertEqual(response.status_code, 302)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, invitation.PENDING)


class TestSendTeamInvitationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.invitee = User.objects.create_user(username='invitee_username', password='password')
        cls.invitee.email = 'existing_invitee@email.com'
        cls.invitee.save()
        cls.invitee_without_email = User.objects.create_user(username='no_email', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.member)
        cls.url = reverse('team_invite', kwargs={'team_slug': cls.team.slug})
        cls.post_data_email = {'invitee': 'invitee@email.com'}
        cls.post_data_username = {'invitee': cls.invitee.username}

    def test_get_permissions_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_permissions_manager(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_permissions_member(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_permissions_non_member(self):
        self.client.force_login(self.non_member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_permissions_anonymous_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_email_sends_owner(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, data=self.post_data_email)
        self.assertEqual(len(mail.outbox), 1)

    def test_post_email_sends_manager(self):
        self.client.force_login(self.manager)
        self.client.post(self.url, data=self.post_data_email)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_email_sends_member(self):
        self.client.force_login(self.member)
        self.client.post(self.url, data=self.post_data_email)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_email_sends_non_member(self):
        self.client.force_login(self.non_member)
        self.client.post(self.url, data=self.post_data_email)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_email_sends_anonymous_user(self):
        self.client.post(self.url, data=self.post_data_email)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_username_sends_owner(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 1)

    def test_post_username_sends_manager(self):
        self.client.force_login(self.manager)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_username_sends_member(self):
        self.client.force_login(self.member)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_username_sends_non_member(self):
        self.client.force_login(self.non_member)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_username_sends_anonymous_user(self):
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 0)

    def test_redirects_post_email(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data=self.post_data_email, follow=True)
        self.assertRedirects(response, reverse('team_invite', kwargs={'team_slug': self.team.slug}))

    def test_redirects_post_username(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data=self.post_data_username, follow=True)
        self.assertRedirects(response, reverse('team_invite', kwargs={'team_slug': self.team.slug}))

    def test_success_message_post_email(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data=self.post_data_email, follow=True)
        self.assertIn('Invitation sent.', response.content.decode('utf8'))

    def test_success_message_post_username(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data=self.post_data_username, follow=True)
        self.assertIn('Invitation sent.', response.content.decode('utf8'))

    def test_bad_username_does_not_email(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'invalid_username'})
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_username_redirects(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'invalid_username'}, follow=True)
        self.assertRedirects(response, reverse('team_invite', kwargs={'team_slug': self.team.slug}))

    def test_bad_username_displays_error(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'invalid_username'}, follow=True)
        self.assertIn('There is no user with that username.', response.content.decode('utf8'))

    def test_bad_email_does_not_email(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'invalid_email@'})
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_email_redirects(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'invalid_email@'}, follow=True)
        self.assertRedirects(response, reverse('team_invite', kwargs={'team_slug': self.team.slug}))

    def test_bad_email_displays_error(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'invalid_email@'}, follow=True)
        self.assertIn('Please enter a valid email address.', response.content.decode('utf8'))

    def test_post_email_addressed_correctly(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, data=self.post_data_email)
        self.assertEqual(mail.outbox[0].to, ['invitee@email.com'])

    def test_post_username_addressed_correctly(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(mail.outbox[0].to, [self.invitee.email])

    def test_post_username_user_has_no_email(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, data={'invitee': 'no_email'}, follow=True)
        self.assertRedirects(response, reverse('team_invite', kwargs={'team_slug': self.team.slug}))
        self.assertIn('That user does not have a registered email address.', response.content.decode('utf8'))

    def test_inviting_user_who_is_already_member(self):
        self.client.force_login(self.owner)
        self.member.email = 'valid@email.com'
        self.member.save()
        self.member.refresh_from_db()
        response = self.client.post(self.url, data={'invitee': self.member.username}, follow=True)
        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(response, reverse('team_invite', kwargs={'team_slug': self.team.slug}))
        self.assertIn('User is already a member of your team.', response.content.decode('utf8'))


# Project displaying views

class TestProjectDetailsViewPermissions(TestCase):
    """
    This tests the permissions to view a project of the various types of users that could try to access it.
    Team owners: can view all projects on a team.
    Team managers: can view projects they are assigned to manager.
    Team members: can view projects to which they are assigned as developers.
    Non members: cannot view any projects.
    """
    def setUp(self):
        """Create the users."""
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.developer = User.objects.create_user(username='developer', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        # Create a team and assign users.
        self.team = create_team(self.owner)
        self.team.members.add(self.manager, self.developer, self.member)
        team_add_manager(self.manager, self.team)
        # Create another team owned by the non-member.
        self.other_team = create_team(self.non_member, 'Other Title')
        # Create a project and assign manager and developer.
        self.linked_project = Project.objects.create(
            title='Linked Project', description='desc', team=self.team, manager=self.manager
        )
        self.linked_project.developers.add(self.developer)
        # Create another project with no manager or developer.
        self.unlinked_project = Project.objects.create(
            title='Unlinked Project', description='desc', team=self.team
        )
        # Create a project for the other team.
        self.other_team_project = Project.objects.create(
            title='Other Project', description='desc', team=self.other_team, manager=self.non_member
        )

    def test_team_owner_permissions(self):
        """Team owner should be able to view both projects on owned team but not the project on the other team."""
        self.client.force_login(self.owner)
        linked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.linked_project.pk})
        )
        unlinked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.unlinked_project.pk})
        )
        other_team_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.other_team.slug, 'project_pk': self.other_team_project.pk})
        )
        self.assertEqual(linked_project_response.status_code, 200)
        self.assertEqual(unlinked_project_response.status_code, 200)
        self.assertEqual(other_team_project_response.status_code, 404)

    def test_team_manager_permissions(self):
        """Team manager should be able to view the project to which it is assigned only."""
        self.client.force_login(self.manager)
        linked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.linked_project.pk})
        )
        unlinked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.unlinked_project.pk})
        )
        other_team_project_response = self.client.get(
            reverse('tracker:project_details',
                    kwargs={'team_slug': self.other_team.slug, 'project_pk': self.other_team_project.pk})
        )
        self.assertEqual(linked_project_response.status_code, 200)
        self.assertEqual(unlinked_project_response.status_code, 404)
        self.assertEqual(other_team_project_response.status_code, 404)

    def test_team_developer_permission(self):
        """Team developer should be able to view the project to which it is assigned only."""
        self.client.force_login(self.developer)
        linked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.linked_project.pk})
        )
        unlinked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.unlinked_project.pk})
        )
        other_team_project_response = self.client.get(
            reverse('tracker:project_details',
                    kwargs={'team_slug': self.other_team.slug, 'project_pk': self.other_team_project.pk})
        )
        self.assertEqual(linked_project_response.status_code, 200)
        self.assertEqual(unlinked_project_response.status_code, 404)
        self.assertEqual(other_team_project_response.status_code, 404)

    def test_non_member_permissions(self):
        """The non-member should not be able to view either project associated with the tested team, but should be able to view its own project."""
        self.client.force_login(self.non_member)
        linked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.linked_project.pk})
        )
        unlinked_project_response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.unlinked_project.pk})
        )
        other_team_project_response = self.client.get(
            reverse('tracker:project_details',
                    kwargs={'team_slug': self.other_team.slug, 'project_pk': self.other_team_project.pk})
        )
        self.assertEqual(linked_project_response.status_code, 404)
        self.assertEqual(unlinked_project_response.status_code, 404)
        self.assertEqual(other_team_project_response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        url = reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.linked_project.pk})
        response = self.client.get(url)
        self.assertRedirects(response, '/accounts/login/?next=' + url)

class TestProjectDetailsView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.team = create_team(self.user, 'Team')
        self.client.force_login(self.user)

    def test_archive_toggle_label(self):
        """Tests the label for the button to toggle archived status. Should read 'Reopen Project' for archived projects and 'Archive Project' for open projects."""
        open_project = Project.objects.create(
            title='Open', description='desc', team=self.team, manager=self.user
        )
        archived_project = Project.objects.create(
            title='Closed', description='desc', team=self.team, manager=self.user, is_archived=True
        )
        open_response = self.client.get(reverse('tracker:project_details', kwargs={'project_pk': open_project.pk, 'team_slug': self.team.slug}))
        archived_response = self.client.get(reverse('tracker:project_details', kwargs={'project_pk': archived_project.pk, 'team_slug': self.team.slug}))
        self.assertEqual(open_response.context['archive_toggle_label'], 'Archive Project')
        self.assertEqual(archived_response.context['archive_toggle_label'], 'Reopen Project')

    def test_project_details_ticket_display(self):
        """Tests whether tickets are displayed in the project details page."""
        project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        first_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='First Ticket')
        second_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Second Ticket')
        closed_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Closed Ticket Title', status='closed')
        response = self.client.get(reverse('tracker:project_details', kwargs={'project_pk': project.pk, 'team_slug': self.team.slug}))
        self.assertContains(response, 'First Ticket')
        self.assertContains(response, 'Second Ticket')
        self.assertNotContains(response, 'Closed Ticket Title')

    def test_ticket_counter_display(self):
        """Tests whether the project details page correctly displays the number of open tickets."""
        project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        first_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='First Ticket')
        second_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Second Ticket')
        closed_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Closed Ticket Title', status='closed')
        response = self.client.get(reverse('tracker:project_details', kwargs={'project_pk': project.pk, 'team_slug': self.team.slug}))
        self.assertEqual(response.context['ticket_counter'], 2)
        self.assertContains(response, '2')

    def test_project_details_ticket_display_closed_tickets(self):
        """Tests whether tickets are displayed in the project details page."""
        project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        first_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='First Ticket')
        second_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Second Ticket')
        closed_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Closed Ticket Title', status='closed')
        response = self.client.get(reverse('tracker:project_details_closed_tickets', kwargs={'project_pk': project.pk, 'team_slug': self.team.slug}))
        self.assertNotContains(response, 'First Ticket')
        self.assertNotContains(response, 'Second Ticket')
        self.assertContains(response, 'Closed Ticket Title')

    def test_ticket_counter_display_closed_tickets(self):
        """Tests whether the project details page correctly displays the number of open tickets."""
        project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        first_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='First Ticket')
        second_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Second Ticket')
        closed_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Closed Ticket Title', status='closed')
        response = self.client.get(reverse('tracker:project_details_closed_tickets', kwargs={'project_pk': project.pk, 'team_slug': self.team.slug}))
        self.assertEqual(response.context['ticket_counter'], 1)
        self.assertContains(response, '1')

    def test_ticket_title_search(self):
        project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        first_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='First Ticket')
        second_ticket = Ticket.objects.create(user=self.user, project=project, team=self.team, title='Second Ticket')
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}
            )+f'?q=first'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('First', response.content.decode('utf8'))
        self.assertNotIn('Second', response.content.decode('utf8'))


class TestProjectDetailsClosedTicketsView(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.team = create_team(self.user, 'Team')
        self.project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        self.open_ticket = Ticket.objects.create(
            user=self.user, title='Open Ticket Title', project=self.project, team=self.team
        )
        self.first_closed_ticket = Ticket.objects.create(
            user=self.user, title='First Closed Ticket Title', project=self.project, team=self.team, status='closed'
        )
        self.second_closed_ticket = Ticket.objects.create(
            user=self.user, title='Second Closed Ticket Title', project=self.project, team=self.team, status='closed'
        )
        self.client.force_login(self.user)
        self.response = self.client.get(reverse('tracker:project_details_closed_tickets', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_closed_ticket_table_display(self):
        self.assertContains(self.response, 'First Closed Ticket Title')
        self.assertContains(self.response, 'Second Closed Ticket Title')
        self.assertNotContains(self.response, 'Open Ticket Title')

    def test_closed_ticket_counter_context(self):
        self.assertEqual(self.response.context['ticket_counter'], 2)

    def test_closed_ticket_counter_display(self):
        self.assertContains(self.response, 'Closed Tickets (2)')


class TestProjectTableViewPermissions(TestCase):
    """
    This tests the permissions to view the project table (similar to a list view) for a given team
    of the various types of users that could try to access it.
    Team owners: see all projects.
    Team managers: see all projects they are assigned to manage.
    Team members: see all projects to which they are assigned as developers.
    Non-members: access forbidden.
    Also tests that the proper content is displayed on the page by testing the response for the project titles which a user should be able to view.
    Also tests that the create new project button is only available for team owners.
    """

    def setUp(self):
        """Create the users."""
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.developer = User.objects.create_user(username='developer', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        # Create a team and assign users.
        self.team = create_team(self.owner, 'Title')
        self.team.members.add(self.manager, self.developer, self.member)
        team_add_manager(self.manager, self.team)
        # Create another team owned by the non-member.
        self.other_team = create_team(self.non_member, 'Other Title')
        # Create two projects and assign manager and developer.
        self.first_linked_project = Project.objects.create(
            title='First Linked Project', description='desc', team=self.team, manager=self.manager
        )
        self.first_linked_project.developers.add(self.developer)
        self.second_linked_project = Project.objects.create(
            title='Second Linked Project', description='desc', team=self.team, manager=self.manager
        )
        self.second_linked_project.developers.add(self.developer)
        # Create another project with no manager or developer.
        self.unlinked_project = Project.objects.create(
            title='Unlinked Project', description='desc', team=self.team
        )
        # Create a project for the other team.
        self.other_team_project = Project.objects.create(
            title='Other Project', description='desc', team=self.other_team, manager=self.non_member
        )

    def test_owner_permissions(self):
        """Should show both linked projects and the unlinked project."""
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Linked Project')
        self.assertContains(response, 'Second Linked Project')
        self.assertContains(response, 'Unlinked Project')
        self.assertNotContains(response, 'Other Project')
        self.assertContains(response, 'Create New Project')

    def test_manager_permissions(self):
        """Should show both linked projects only."""
        self.client.force_login(self.manager)
        response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Linked Project')
        self.assertContains(response, 'Second Linked Project')
        self.assertNotContains(response, 'Unlinked Project')
        self.assertNotContains(response, 'Other Project')
        self.assertNotContains(response, 'Create New Project')

    def test_developer_permissions(self):
        """Should show both linked projects only."""
        self.client.force_login(self.developer)
        response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Linked Project')
        self.assertContains(response, 'Second Linked Project')
        self.assertNotContains(response, 'Unlinked Project')
        self.assertNotContains(response, 'Other Project')
        self.assertNotContains(response, 'Create New Project')

    def test_member_permissions(self):
        """Should show no projects since this user is not assigned as manager or developer to any project."""
        self.client.force_login(self.member)
        response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'First Linked Project')
        self.assertNotContains(response, 'Second Linked Project')
        self.assertNotContains(response, 'Unlinked Project')
        self.assertNotContains(response, 'Other Project')
        self.assertContains(response, 'There are no open projects.')
        self.assertNotContains(response, 'Create New Project')

    def test_non_member_permission(self):
        """Should 404."""
        self.client.force_login(self.non_member)
        response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 404)

class TestProjectTableViewContent(TestCase):
    """Testing that the appropriate projects are displayed on the project table with all columns present."""
    def setUp(self):
        self.user = User.objects.create_user(username='TeamOwnerUsername', password='password')
        self.team = create_team(self.user)
        self.other_team = create_team(self.user, 'Other Team Title')
        self.first_project = Project.objects.create(
            title='First Project Title', description='First Project Description', manager=self.user, team=self.team
        )
        self.second_project = Project.objects.create(
            title='Second Project Title', description='Second Project Description', manager=self.user, team=self.team
        )
        self.first_project_first_ticket = Ticket.objects.create(
            user=self.user, title='title', project=self.first_project, team=self.team
        )
        self.first_project_second_ticket = Ticket.objects.create(
            user=self.user, title='title', project=self.first_project, team=self.team
        )
        self.first_project_closed_ticket = Ticket.objects.create(
            user=self.user, title='title', project=self.first_project, team=self.team, status='closed'
        )
        self.second_project_ticket = Ticket.objects.create(
            user=self.user, title='title', project=self.second_project, team=self.team
        )
        self.archived_project = Project.objects.create(
            title='Archived Project Title', description='Archived Project Description', manager=self.user, team=self.team, is_archived=True
        )
        self.client.force_login(self.user)
        self.response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.team.slug}))

    def test_team_with_no_projects(self):
        """Should not display any projects because the view is for a team with no projects."""
        response = self.client.get(reverse('tracker:project_list', kwargs={'team_slug': self.other_team.slug}))
        self.assertNotContains(response, 'First Project Title')
        self.assertNotContains(response, 'Second Project Title')
        self.assertNotContains(response, 'Archived Project Title')
        self.assertContains(response, 'There are no open projects.')

    def test_project_titles_display(self):
        self.assertContains(self.response, 'First Project Title')
        self.assertContains(self.response, 'Second Project Title')
        self.assertNotContains(self.response, 'Archived Project Title')

    def test_project_description_display(self):
        self.assertContains(self.response, 'First Project Description')
        self.assertContains(self.response, 'Second Project Description')
        self.assertNotContains(self.response, 'Archived Project Description')

    def test_project_manager_display(self):
        self.assertContains(self.response, f'<td>{self.user.username}</td>', count=2, html=True)

    def test_project_ticket_count_display(self):
        """This also tests that closed tickets are not counted."""
        self.assertContains(self.response, f'<td>2</td>', count=1, html=True)
        self.assertContains(self.response, f'<td>1</td>', count=1, html=True)

    def test_view_archived_projects_link_text(self):
        self.assertContains(self.response, 'View archived projects.')


class TestArchivedProjectTableViewContent(TestCase):
    """Testing that the appropriate projects are displayed on the archived project table."""
    def setUp(self):
        self.user = User.objects.create_user(username='TeamOwnerUsername', password='password')
        self.team = create_team(self.user)
        self.open_project = Project.objects.create(
            title='Open Project Title', description='Open Project Description', manager=self.user, team=self.team
        )
        self.archived_project = Project.objects.create(
            title='Archived Project Title', description='Archived Project Description', manager=self.user,
            team=self.team, is_archived=True
        )
        self.client.force_login(self.user)
        self.response = self.client.get(reverse('tracker:archived_project_list', kwargs={'team_slug': self.team.slug}))

    def test_archived_project_display(self):
        self.assertContains(self.response, 'Archived Project Title')
        self.assertNotContains(self.response, 'Open Project Title')

    def test_view_active_projects_link_text(self):
        self.assertContains(self.response, 'View active projects.')


# Ticket displaying views

class TestTicketTableViewPermissions(TestCase):
    """
    Tests whether the ticket table filters tickets appropriately based on team and project view permissions for each user type.
    Team owners: see all tickets for all projects on their team.
    Managers: see all tickets for projects they are assigned to managed.
    Developers: see all tickets for projects to which they are assigned as developers.
    Members who aren't assigned to projects: see no tickets.
    Non-members: see no tickets.
    """
    def setUp(self):
        """Create the users."""
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.developer = User.objects.create_user(username='developer', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        # Create a team and assign users.
        self.team = create_team(self.owner, 'Title')
        self.team.members.add(self.manager, self.developer, self.member)
        team_add_manager(self.manager, self.team)
        # Create another team owned by the non-member.
        self.other_team = create_team(self.non_member, 'Other Title')
        # Create two projects and assign manager and developer.
        self.first_linked_project = Project.objects.create(
            title='First Linked Project', description='desc', team=self.team, manager=self.manager
        )
        self.first_linked_project.developers.add(self.developer)
        self.second_linked_project = Project.objects.create(
            title='Second Linked Project', description='desc', team=self.team, manager=self.manager
        )
        self.second_linked_project.developers.add(self.developer)
        # Create another project with no manager or developer.
        self.unlinked_project = Project.objects.create(
            title='Unlinked Project', description='desc', team=self.team
        )
        # Create a project for the other team.
        self.other_team_project = Project.objects.create(
            title='Other Project', description='desc', team=self.other_team, manager=self.non_member
        )
        # Create four tickets: one for each project.
        self.first_linked_project_ticket = Ticket.objects.create(
            user=self.owner, title='First Linked Project Ticket Title', project=self.first_linked_project, team=self.team
        )
        self.second_linked_project_ticket = Ticket.objects.create(
            user=self.owner, title='Second Linked Project Ticket Title', project=self.second_linked_project, team=self.team
        )
        self.unlinked_project_ticket = Ticket.objects.create(
            user=self.owner, title='Unlinked Project Ticket Title', project=self.unlinked_project, team=self.team
        )
        self.other_team_ticket = Ticket.objects.create(
            user=self.owner, title='Other Team Project Ticket Title', project=self.other_team_project, team=self.other_team
        )
        # Create a closed ticket to verify that it isn't displayed.
        self.closed_ticket = Ticket.objects.create(
            user=self.owner, title='Closed Ticket Title', project=self.first_linked_project, team=self.team, status='closed'
        )

    def test_owner_ticket_table_content(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:ticket_list', kwargs={'team_slug': self.team.slug}))
        self.assertContains(response, 'First Linked Project Ticket Title')
        self.assertContains(response, 'Second Linked Project Ticket Title')
        self.assertContains(response, 'Unlinked Project Ticket Title')
        self.assertNotContains(response, 'Other Team Project Ticket Title')
        self.assertNotContains(response, 'Closed Ticket Title')

    def test_manager_ticket_table_content(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('tracker:ticket_list', kwargs={'team_slug': self.team.slug}))
        self.assertContains(response, 'First Linked Project Ticket Title')
        self.assertContains(response, 'Second Linked Project Ticket Title')
        self.assertNotContains(response, 'Unlinked Project Ticket Title')
        self.assertNotContains(response, 'Other Team Project Ticket Title')
        self.assertNotContains(response, 'Closed Ticket Title')

    def test_developer_ticket_table_content(self):
        self.client.force_login(self.developer)
        response = self.client.get(reverse('tracker:ticket_list', kwargs={'team_slug': self.team.slug}))
        self.assertContains(response, 'First Linked Project Ticket Title')
        self.assertContains(response, 'Second Linked Project Ticket Title')
        self.assertNotContains(response, 'Unlinked Project Ticket Title')
        self.assertNotContains(response, 'Other Team Project Ticket Title')
        self.assertNotContains(response, 'Closed Ticket Title')

    def test_member_ticket_table_content(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('tracker:ticket_list', kwargs={'team_slug': self.team.slug}))
        self.assertNotContains(response, 'First Linked Project Ticket Title')
        self.assertNotContains(response, 'Second Linked Project Ticket Title')
        self.assertNotContains(response, 'Unlinked Project Ticket Title')
        self.assertNotContains(response, 'Other Team Project Ticket Title')
        self.assertNotContains(response, 'Closed Ticket Title')
        self.assertContains(response,'There are no open tickets.')

    def test_non_member_ticket_table_content(self):
        self.client.force_login(self.non_member)
        response = self.client.get(reverse('tracker:ticket_list', kwargs={'team_slug': self.team.slug}))
        self.assertEqual(response.status_code, 404)


class TestTicketTableContent(TestCase):
    """Tests that the open ticket table displays only the open tickets, while the closed ticket table display closed tickets."""
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.team = create_team(self.user, 'Title')
        self.project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        self.open_ticket = Ticket.objects.create(
            user=self.user, title='Open Ticket Title', project=self.project, team=self.team
        )
        self.closed_ticket = Ticket.objects.create(
            user=self.user, title='Closed Ticket Title', project=self.project, team=self.team, status='closed'
        )
        self.client.force_login(self.user)
        self.open_response = self.client.get(reverse('tracker:ticket_list', kwargs={'team_slug': self.team.slug}))
        self.closed_response = self.client.get(reverse('tracker:closed_ticket_list', kwargs={'team_slug': self.team.slug}))

    def test_open_ticket_table_content(self):
        self.assertContains(self.open_response, 'Open Ticket Title')
        self.assertNotContains(self.open_response, 'Closed Ticket Title')

    def test_closed_ticket_table_content(self):
        self.assertNotContains(self.closed_response, 'Open Ticket Title')
        self.assertContains(self.closed_response, 'Closed Ticket Title')


class TestAssignedTicketTableContent(TestCase):
    """Tests that the assigned ticket tables (both closed and open) display only those tickets assigned to the current user."""
    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password')
        self.team = create_team(self.user, 'Title')
        self.project = Project.objects.create(
            title='Project', description='desc', team=self.team, manager=self.user
        )
        self.assigned_open_ticket = Ticket.objects.create(
            user=self.user, title='Assigned Open Ticket Title', project=self.project, team=self.team
        )
        self.assigned_open_ticket.developer.add(self.user)
        self.assigned_closed_ticket = Ticket.objects.create(
            user=self.user, title='Assigned Closed Ticket Title', project=self.project, team=self.team, status='closed'
        )
        self.assigned_closed_ticket.developer.add(self.user)
        self.unassigned_open_ticket = Ticket.objects.create(
            user=self.user, title='Unassigned Open Ticket Title', project=self.project, team=self.team
        )
        self.unassigned_closed_ticket = Ticket.objects.create(
            user=self.user, title='Unassigned Closed Ticket Title', project=self.project, team=self.team, status='closed'
        )
        self.client.force_login(self.user)
        self.open_response = self.client.get(reverse('tracker:assigned_ticket_list', kwargs={'team_slug': self.team.slug}))
        self.closed_response = self.client.get(reverse('tracker:closed_assigned_ticket_list', kwargs={'team_slug': self.team.slug}))

    def test_open_assigned_ticket_table_content(self):
        self.assertContains(self.open_response, 'Assigned Open Ticket Title')
        self.assertNotContains(self.open_response, 'Assigned Closed Ticket Title')
        self.assertNotContains(self.open_response, 'Unassigned Open Ticket Title')
        self.assertNotContains(self.open_response, 'Unassigned Closed Ticket Title')

    def test_closed_assigned_ticket_table_content(self):
        self.assertNotContains(self.closed_response, 'Assigned Open Ticket Title')
        self.assertContains(self.closed_response, 'Assigned Closed Ticket Title')
        self.assertNotContains(self.closed_response, 'Unassigned Open Ticket Title')
        self.assertNotContains(self.closed_response, 'Unassigned Closed Ticket Title')


# Ticket Creation/Update view testing

class TestTicketUpdateView(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.assigned_developer = User.objects.create_user(username='assigned_developer', password='password')
        self.unassigned_developer = User.objects.create_user(username='unassigned_developer', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        self.team = create_team(self.owner)
        self.team.members.add(self.manager, self.assigned_developer, self.unassigned_developer, self.member)
        team_add_manager(self.manager, self.team)
        self.project = Project.objects.create(title='Project Title', description='desc', manager=self.manager, team=self.team)
        self.project.developers.add(self.assigned_developer, self.unassigned_developer)
        self.ticket = Ticket.objects.create(title='Ticket Title', user=self.owner, project=self.project, team=self.team)
        self.ticket.developer.add(self.assigned_developer)
        self.form_data = {'title': 'New Ticket Title', 'priority': self.ticket.priority, 'status': self.ticket.status}

    def test_owner_get_permissions(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 200)

    def test_manager_get_permissions(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 200)

    def test_assigned_developer_get_permissions(self):
        self.client.force_login(self.assigned_developer)
        response = self.client.get(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 200)

    def test_unassigned_developer_get_permissions(self):
        self.client.force_login(self.unassigned_developer)
        response = self.client.get(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 404)

    def test_member_get_permissions(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 404)

    def test_non_member_get_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.get(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))
        self.assertEqual(response.status_code, 404)

    def test_ticket_updated_owner(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}), data=self.form_data)
        # self.assertEqual(response.context['form'].errors, 0)
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'New Ticket Title')

    def test_ticket_updated_manager(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}), data=self.form_data)
        # self.assertEqual(response.context['form'].errors, 0)
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'New Ticket Title')

    def test_ticket_updated_assigned_developer(self):
        self.client.force_login(self.assigned_developer)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}), data=self.form_data)
        # self.assertEqual(response.context['form'].errors, 0)
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'New Ticket Title')

    def test_ticket_updated_unassigned_developer(self):
        self.client.force_login(self.unassigned_developer)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}), data=self.form_data)
        # self.assertEqual(response.context['form'].errors, 0)
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'Ticket Title')

    def test_ticket_updated_member(self):
        self.client.force_login(self.member)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}), data=self.form_data)
        # self.assertEqual(response.context['form'].errors, 0)
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'Ticket Title')

    def test_ticket_updated_non_member(self):
        self.client.force_login(self.non_member)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}), data=self.form_data)
        # self.assertEqual(response.context['form'].errors, 0)
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.title, 'Ticket Title')

    def test_redirect(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.ticket.title, 'Ticket Title')
        response = self.client.post(
            reverse('tracker:ticket_update', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}),
            data=self.form_data, follow=True)
        self.assertRedirects(response, reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))


class TestTicketCreateView(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.developer = User.objects.create_user(username='assigned_developer', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        self.team = create_team(self.owner)
        team_add_manager(self.manager, self.team)
        self.team.members.add(self.manager, self.developer, self.member)
        self.project = Project.objects.create(title='Project Title', description='desc', manager=self.manager, team=self.team)
        self.project.developers.add(self.developer)
        self.url = reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug})+f'?project={self.project.pk}'
        self.form_data = {
            'title': 'Ticket Title',
            'priority': 'low',
            'status': 'open',
            'resolution': ''
        }

    def test_owner_get_permissions(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_manager_get_permissions(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_developer_get_permissions(self):
        self.client.force_login(self.developer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_member_get_permissions(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_non_member_get_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_ticket_creation_owner(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.project.project_tickets.all().count(), 0)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.project_tickets.all().count(), 1)
        self.assertEqual(self.project.project_tickets.all().first().title, 'Ticket Title')
        self.assertEqual(self.project.project_tickets.all().first().user, self.owner)

    def test_ticket_creation_manager(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.project.project_tickets.all().count(), 0)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.project_tickets.all().count(), 1)
        self.assertEqual(self.project.project_tickets.all().first().title, 'Ticket Title')
        self.assertEqual(self.project.project_tickets.all().first().user, self.manager)

    def test_ticket_creation_developer(self):
        self.client.force_login(self.developer)
        self.assertEqual(self.project.project_tickets.all().count(), 0)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.project_tickets.all().count(), 1)
        self.assertEqual(self.project.project_tickets.all().first().title, 'Ticket Title')
        self.assertEqual(self.project.project_tickets.all().first().user, self.developer)

    def test_ticket_creation_member(self):
        self.client.force_login(self.member)
        self.assertEqual(self.project.project_tickets.all().count(), 0)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.project.project_tickets.all().count(), 0)

    def test_ticket_creation_non_member(self):
        self.client.force_login(self.non_member)
        self.assertEqual(self.project.project_tickets.all().count(), 0)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.project.project_tickets.all().count(), 0)

    def test_nonexistent_project_ticket_creation_owner(self):
        self.client.force_login(self.owner)
        self.assertEqual(Ticket.objects.all().count(), 0)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug})+'?project=999', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Ticket.objects.all().count(), 0)

    def test_nonexistent_project_ticket_creation_manager(self):
        self.client.force_login(self.manager)
        self.assertEqual(Ticket.objects.all().count(), 0)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug})+'?project=999', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Ticket.objects.all().count(), 0)

    def test_nonexistent_project_ticket_creation_developer(self):
        self.client.force_login(self.developer)
        self.assertEqual(Ticket.objects.all().count(), 0)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug})+'?project=999', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Ticket.objects.all().count(), 0)

    def test_nonexistent_project_ticket_creation_member(self):
        self.client.force_login(self.member)
        self.assertEqual(Ticket.objects.all().count(), 0)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug})+'?project=999', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Ticket.objects.all().count(), 0)

    def test_nonexistent_project_ticket_creation_non_member(self):
        self.client.force_login(self.non_member)
        self.assertEqual(Ticket.objects.all().count(), 0)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug})+'?project=999', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Ticket.objects.all().count(), 0)

    def test_no_project_pk_url_querystring_provided(self):
        self.client.force_login(self.owner)
        self.assertEqual(Ticket.objects.all().count(), 0)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': self.team.slug}), self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Ticket.objects.all().count(), 0)

    def test_adding_ticket_to_unowned_team_owner(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_team = create_team(other_user, 'Other Team')
        other_project = Project.objects.create(title='Other Project', description='desc', team=other_team)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': other_team.slug})+f'?project={other_project.pk}', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other_project.project_tickets.all().count(), 0)

    def test_adding_ticket_to_unowned_team_manager(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_team = create_team(other_user, 'Other Team')
        other_project = Project.objects.create(title='Other Project', description='desc', team=other_team)
        self.client.force_login(self.manager)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': other_team.slug})+f'?project={other_project.pk}', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other_project.project_tickets.all().count(), 0)

    def test_adding_ticket_to_unowned_team_developer(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_team = create_team(other_user, 'Other Team')
        other_project = Project.objects.create(title='Other Project', description='desc', team=other_team)
        self.client.force_login(self.developer)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': other_team.slug})+f'?project={other_project.pk}', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other_project.project_tickets.all().count(), 0)

    def test_adding_ticket_to_unowned_team_member(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_team = create_team(other_user, 'Other Team')
        other_project = Project.objects.create(title='Other Project', description='desc', team=other_team)
        self.client.force_login(self.member)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': other_team.slug})+f'?project={other_project.pk}', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other_project.project_tickets.all().count(), 0)

    def test_adding_ticket_to_unowned_team_non_member(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_team = create_team(other_user, 'Other Team')
        other_project = Project.objects.create(title='Other Project', description='desc', team=other_team)
        self.client.force_login(self.non_member)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': other_team.slug})+f'?project={other_project.pk}', self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other_project.project_tickets.all().count(), 0)

    def test_adding_ticket_to_unowned_team_other_team_owner(self):
        other_user = User.objects.create_user(username='other_user', password='password')
        other_team = create_team(other_user, 'Other Team')
        other_project = Project.objects.create(title='Other Project', description='desc', team=other_team)
        self.client.force_login(other_user)
        response = self.client.post(reverse('tracker:create_ticket', kwargs={'team_slug': other_team.slug})+f'?project={other_project.pk}', self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(other_project.project_tickets.all().count(), 1)

# Project creation, updating, archiving, unarchiving

class TestCreateProjectView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.manager.email = 'valid@email.com'
        cls.manager.save()
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.other_team_owner = User.objects.create_user(username='other_team_owner', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.member)
        cls.form_data = {'title': 'Project Title', 'description': 'Project description'}
        cls.other_team = create_team(cls.other_team_owner, 'Other Team')

    def test_owner_permissions(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}), self.form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.all().count(), 1)
        self.assertEqual(self.team.projects.all().count(), 1)

    def test_manager_is_emailed(self):
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertEqual(project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_subjeect(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertIn(project.title, mail.outbox[0].subject)

    def test_email_body(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertIn(project.title, mail.outbox[0].body)

    def test_email_to(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertIn(self.manager.email, mail.outbox[0].to)

    def test_manager_permissions(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}), self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Project.objects.all().count(), 0)
        self.assertEqual(self.team.projects.all().count(), 0)

    def test_member_permissions(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}), self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Project.objects.all().count(), 0)
        self.assertEqual(self.team.projects.all().count(), 0)

    def test_non_member_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}), self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Project.objects.all().count(), 0)
        self.assertEqual(self.team.projects.all().count(), 0)

    def test_anonymous_user_permissions(self):
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}), self.form_data)
        self.assertEqual(Project.objects.all().count(), 0)
        self.assertEqual(self.team.projects.all().count(), 0)

    def test_other_team_project_creation(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.other_team.slug}), self.form_data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Project.objects.all().count(), 0)
        self.assertEqual(self.other_team.projects.all().count(), 0)
        self.assertEqual(self.team.projects.all().count(), 0)

    def test_redirect(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    self.form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        project = Project.objects.all().first()
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))

    def test_invalid_form_data(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}), {'title': 'Project Title'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Project.objects.all().count(), 0)
        self.assertEqual(self.team.projects.all().count(), 0)

class TestUpdateProjectView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.manager.email = 'valid@email.com'
        cls.manager.save()
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.other_team_owner = User.objects.create_user(username='other_team_owner', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.member)
        cls.other_team = create_team(cls.other_team_owner, 'Other team')

    def test_form_context(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['create_or_update'], 'Update')
        self.assertIn('<input type="submit" value="Update">', response.content.decode('utf8'))

    def test_owner_permissions(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}), form_data)
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Updated Project Title')

    def test_manager_is_emailed(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertEqual(project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 1)

    def test_already_existing_manager_not_emailed(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, manager=self.manager)
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description',
                                     'manager': str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertEqual(project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_subject(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description',
                                     'manager': str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertIn(project.title, mail.outbox[0].subject)

    def test_email_body(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description',
                                     'manager': str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertIn(project.title, mail.outbox[0].body)

    def test_email_to(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description',
                                     'manager': str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertIn(self.manager.email, mail.outbox[0].to)

    def test_manager_permissions(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        self.client.force_login(self.manager)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}), form_data)
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Project Title')

    def test_member_permissions(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        self.client.force_login(self.member)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}), form_data)
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Project Title')

    def test_non_member_permissions(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        self.client.force_login(self.non_member)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}), form_data)
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Project Title')

    def test_anonymous_user_permissions(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}), form_data)
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Project Title')

    def test_other_team_project_update(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.other_team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.other_team.slug}), form_data)
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.title, 'Project Title')

    def test_redirect(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        form_data = {'title': 'Updated Project Title', 'description': project.description}
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}), form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))

class TestToggleArchiveProjectView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.other_team_owner = User.objects.create_user(username='other_team_owner', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.member)
        cls.other_team = create_team(cls.other_team_owner, 'Other team')

    def test_owner_permissions_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.owner)
        self.assertEqual(project.is_archived, False)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, True)

    def test_manager_permissions_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.manager)
        self.assertEqual(project.is_archived, False)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, False)

    def test_member_permissions_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.member)
        self.assertEqual(project.is_archived, False)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, False)

    def test_non_member_permissions_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.non_member)
        self.assertEqual(project.is_archived, False)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, False)

    def test_anonymous_user_permissions_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.assertEqual(project.is_archived, False)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, False)

    def test_other_team_project_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.other_team)
        self.client.force_login(self.owner)
        self.assertEqual(project.is_archived, False)
        response = self.client.post(
            reverse('tracker:archive_project', kwargs={'team_slug': self.other_team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, False)

    def test_owner_permissions_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, is_archived=True)
        self.client.force_login(self.owner)
        self.assertEqual(project.is_archived, True)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, False)

    def test_manager_permissions_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, is_archived=True)
        self.client.force_login(self.manager)
        self.assertEqual(project.is_archived, True)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, True)

    def test_member_permissions_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, is_archived=True)
        self.client.force_login(self.member)
        self.assertEqual(project.is_archived, True)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, True)

    def test_non_member_permissions_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, is_archived=True)
        self.client.force_login(self.non_member)
        self.assertEqual(project.is_archived, True)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, True)

    def test_anonymous_user_permissions_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, is_archived=True)
        self.assertEqual(project.is_archived, True)
        response = self.client.post(reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, True)

    def test_other_team_project_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.other_team, is_archived=True)
        self.client.force_login(self.owner)
        self.assertEqual(project.is_archived, True)
        response = self.client.post(
            reverse('tracker:archive_project', kwargs={'team_slug': self.other_team.slug, 'project_pk': project.pk}))
        self.assertEqual(response.status_code, 404)
        project.refresh_from_db()
        self.assertEqual(project.is_archived, True)

    def test_redirect_archiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team)
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))

    def test_redirect_unarchiving(self):
        project = Project.objects.create(title='Project Title', description='desc', team=self.team, is_archived=True)
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('tracker:archive_project', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': project.pk}))


class TestProjectManageDevelopersView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.team_manager = User.objects.create_user(username='team_manager', password='password')
        cls.project_manager = User.objects.create_user(username='project_manager', password='password')
        cls.developer = User.objects.create_user(username='developer', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.member.email = 'valid@email.com'
        cls.member.save()
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.other_team_owner = User.objects.create_user(username='other_team_owner', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.team_manager, cls.team)
        team_add_manager(cls.project_manager, cls.team)
        cls.team.members.add(cls.team_manager, cls.project_manager, cls.developer, cls.member)
        cls.other_team = create_team(cls.other_team_owner, 'Other team')

    def setUp(self):
        self.project = Project.objects.create(
            title='Project Title', description='desc', team=self.team, manager=self.project_manager
        )
        self.project.developers.add(self.developer)
        self.url = reverse('tracker:project_manage_developers', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})

    def test_owner_get_permissions(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_team_manager_get_permissions(self):
        self.client.force_login(self.team_manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_project_manager_get_permissions(self):
        self.client.force_login(self.project_manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_developer_get_permissions(self):
        self.client.force_login(self.developer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_member_get_permissions(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_non_member_get_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_other_team_owner_get_permissions(self):
        self.client.force_login(self.other_team_owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_get_permissions(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_owner_add_developer(self):
        self.client.force_login(self.owner)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.member, self.project.developers.all())

    def test_added_developer_receives_email(self):
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?add={self.member.username}', follow=True)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_subject(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?add={self.member.username}', follow=True)
        self.assertIn(self.project.title, mail.outbox[0].subject)

    def test_email_body(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?add={self.member.username}', follow=True)
        self.assertIn(self.project.title, mail.outbox[0].body)

    def test_email_to(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?add={self.member.username}', follow=True)
        self.assertIn(self.member.email, mail.outbox[0].to)

    def test_team_manager_add_developer(self):
        self.client.force_login(self.team_manager)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.member, self.project.developers.all())

    def test_project_manager_add_developer(self):
        self.client.force_login(self.project_manager)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.member, self.project.developers.all())

    def test_developer_add_developer(self):
        self.client.force_login(self.developer)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.member, self.project.developers.all())

    def test_member_add_developer(self):
        self.client.force_login(self.member)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertNotIn(self.member, self.project.developers.all())
        self.assertEqual(response.status_code, 404)

    def test_non_member_add_developer(self):
        self.client.force_login(self.non_member)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.member, self.project.developers.all())

    def test_other_team_owner_add_developer(self):
        self.client.force_login(self.other_team_owner)
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.member, self.project.developers.all())

    def test_anonymous_user_add_developer(self):
        self.assertNotIn(self.member, self.project.developers.all())
        response = self.client.get(self.url+f'?add={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.member, self.project.developers.all())

    def test_owner_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.owner)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertNotIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 200)

    def test_team_manager_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.team_manager)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 404)

    def test_project_manager_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.project_manager)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertNotIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 200)

    def test_developer_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.developer)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 404)

    def test_member_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.member)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 404)

    def test_non_member_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.non_member)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 404)

    def test_other_team_owner_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        self.client.force_login(self.other_team_owner)
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_remove_developer(self):
        self.assertIn(self.developer, self.project.developers.all())
        response = self.client.get(self.url+f'?remove={self.developer.username}', follow=True)
        self.assertIn(self.developer, self.project.developers.all())
        self.assertEqual(response.status_code, 200)

    def test_add_invalid_username(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.project.developers.all().count(), 1)
        response = self.client.get(self.url+f'?add=not_a_user', follow=True)
        self.assertEqual(self.project.developers.all().count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertIn('User does not exist or is not a member of this team.', response.content.decode('utf8'))

    def test_remove_invalid_username(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.project.developers.all().count(), 1)
        response = self.client.get(self.url+f'?remove=not_a_user', follow=True)
        self.assertEqual(self.project.developers.all().count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertIn('User does not exist or is not a member of this team.', response.content.decode('utf8'))

    def test_add_non_team_member(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.project.developers.all().count(), 1)
        response = self.client.get(self.url+f'?add={self.non_member}', follow=True)
        self.assertEqual(self.project.developers.all().count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertIn('User does not exist or is not a member of this team.', response.content.decode('utf8'))

    def test_remove_non_developer(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.project.developers.all().count(), 1)
        response = self.client.get(self.url+f'?remove={self.member}', follow=True)
        self.assertEqual(self.project.developers.all().count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertIn('User is not a project developer.', response.content.decode('utf8'))

    def test_owner_displays_manage_developers_link(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Manage developers', response.content.decode('utf8'))

    def test_team_manager_displays_manage_developers_link(self):
        self.client.force_login(self.team_manager)
        response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_project_manager_displays_manage_developers_link(self):
        self.client.force_login(self.project_manager)
        response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Manage developers', response.content.decode('utf8'))

    def test_developer_displays_manage_developers_link(self):
        self.client.force_login(self.developer)
        response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Manage developers', response.content.decode('utf8'))

    def test_member_displays_manage_developers_link(self):
        self.client.force_login(self.member)
        response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_non_member_displays_manage_developers_link(self):
        self.client.force_login(self.non_member)
        response = self.client.get(
            reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})
        )
        self.assertEqual(response.status_code, 404)


# Ticket Details Super View Testing

class TestCommentViewAndDeletion(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.developer = User.objects.create_user(username='developer', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.comment_submitter = User.objects.create_user(username='comment_submitter', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.developer, cls.member, cls.comment_submitter)
        cls.project = Project.objects.create(title='Project Title', description='desc', team=cls.team,
                                             manager=cls.manager)
        cls.project.developers.add(cls.developer, cls.comment_submitter)

    def test_comment_display(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf8')
        self.assertIn('Comment text.', html)

    def test_context(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        comment_from_context = response.context['page_obj'][0]
        self.assertEqual(comment_from_context.text, comment.text)
        self.assertEqual(comment_from_context.pk, comment.pk)

    def test_comment_delete_owner(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.owner)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.all().count(), 0)
        self.assertNotIn('Comment text.', response.content.decode('utf8'))
        self.assertIn('Comment deleted.', response.content.decode('utf8'))

    def test_comment_delete_manager(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.manager)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        self.assertIn('You do not have permission to delete that comment.', response.content.decode('utf8'))

    def test_comment_delete_developer(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.developer)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        self.assertIn('You do not have permission to delete that comment.', response.content.decode('utf8'))

    def test_comment_delete_member(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.member)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Comment.objects.all().count(), 1)

    def test_comment_delete_non_member(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.non_member)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Comment.objects.all().count(), 1)

    def test_comment_delete_comment_submitter(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.comment_submitter)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.all().count(), 0)
        self.assertNotIn('Comment text.', response.content.decode('utf8'))
        self.assertIn('Comment deleted.', response.content.decode('utf8'))

    def test_comment_delete_anonymous_user(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.assertEqual(Comment.objects.all().count(), 1)
        response = self.client.post(
            reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk}), follow=True)
        self.assertEqual(Comment.objects.all().count(), 1)

    def test_comment_delete_url_presence_owner(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        delete_url = reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk})
        self.assertIn(delete_url, response.content.decode('utf8'))

    def test_comment_delete_url_presence_manager(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        delete_url = reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk})
        self.assertNotIn(delete_url, response.content.decode('utf8'))

    def test_comment_delete_url_presence_developer(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.developer)
        response = self.client.get(
            reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        delete_url = reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk})
        self.assertNotIn(delete_url, response.content.decode('utf8'))

    def test_comment_delete_url_presence_comment_submitter(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        comment = Comment.objects.create(text='Comment text.', user=self.comment_submitter, ticket=ticket)
        self.client.force_login(self.comment_submitter)
        response = self.client.get(
            reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        delete_url = reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': comment.pk})
        self.assertIn(delete_url, response.content.decode('utf8'))

    def test_multiple_comments_url_presence(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner)
        owned_comment = Comment.objects.create(text='First comment text.', user=self.comment_submitter, ticket=ticket)
        unowned_comment = Comment.objects.create(text='Second comment text.', user=self.owner, ticket=ticket)
        self.client.force_login(self.comment_submitter)
        response = self.client.get(
            reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertIn('First comment text.', response.content.decode('utf8'))
        self.assertIn('Second comment text.', response.content.decode('utf8'))
        owned_delete_url = reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': owned_comment.pk})
        unowned_delete_url = reverse('tracker:delete_comment', kwargs={'team_slug': self.team.slug, 'pk': unowned_comment.pk})
        self.assertIn(owned_delete_url, response.content.decode('utf8'))
        self.assertNotIn(unowned_delete_url, response.content.decode('utf8'))


class TestCommentEmailSubscription(TestCase):

    def setUp(self):
        self.subscriber = User.objects.create_user(username='subscriber', password='password')
        self.subscriber.email = 'subscriber@email.com'
        self.subscriber.save()
        self.commenter = User.objects.create_user(username='commenter', password='password')
        self.commenter.email = 'commenter@email.com'
        self.commenter.save()
        self.team = create_team(self.commenter)
        self.team.members.add(self.subscriber, self.commenter)
        self.project = Project.objects.create(title='Project Title', description='desc')
        self.project.developers.add(self.subscriber)
        self.ticket = Ticket.objects.create(title='Ticket Title', user=self.commenter, project=self.project, team=self.team)
        self.ticket.subscribers.remove(self.commenter)
        self.ticket.subscribers.add(self.subscriber)
        self.comment_data = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        self.post_url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk})

    def test_subscriber_receives_email_on_comment(self):
        self.client.force_login(self.commenter)
        self.client.post(self.post_url, self.comment_data)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.subscriber.email])
        self.assertIn('Comment text.', mail.outbox[0].body)
        self.assertIn(self.ticket.title, mail.outbox[0].subject)

    def test_no_email_on_closed_tickets(self):
        self.client.force_login(self.commenter)
        self.ticket.status = 'closed'
        self.ticket.save()
        self.client.post(self.post_url, self.comment_data)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_non_subscriber_receives_no_email_on_comment(self):
        self.client.force_login(self.commenter)
        self.client.post(self.post_url, self.comment_data)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotEqual(mail.outbox[0].to, [self.commenter.email])

    def test_multiple_subscribers(self):
        second_subscriber = User.objects.create_user(username='second', password='password')
        second_subscriber.email = 'second@email.com'
        second_subscriber.save()
        self.project.manager = second_subscriber
        self.project.save()
        self.team.members.add(second_subscriber)
        self.team.save()
        self.ticket.subscribers.add(second_subscriber)
        self.ticket.save()
        self.client.force_login(self.commenter)
        self.client.post(self.post_url, self.comment_data)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, [self.subscriber.email])
        self.assertEqual(mail.outbox[1].to, [second_subscriber.email])

    def test_non_team_member_subscriber(self):
        user = User.objects.create_user(username='user', password='password')
        user.email = 'valid@email.com'
        user.save()
        self.project.developers.add(user)
        self.ticket.subscribers.add(user)
        self.ticket.save()
        self.assertEqual(self.ticket.subscribers.all().count(), 2)
        self.client.force_login(self.commenter)
        self.client.post(self.post_url, self.comment_data)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_non_project_member_subscriber(self):
        user = User.objects.create_user(username='user', password='password')
        user.email = 'valid@email.com'
        user.save()
        self.team.members.add(user)
        self.ticket.subscribers.add(user)
        self.ticket.save()
        self.assertEqual(self.ticket.subscribers.all().count(), 2)
        self.client.force_login(self.commenter)
        self.client.post(self.post_url, self.comment_data)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertEqual(len(mail.outbox), 1)


class TestProjectSubscribeToAllTickets(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subscriber = User.objects.create_user(username='subscriber', password='password')
        cls.commenter = User.objects.create_user(username='commenter', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.non_project_member = User.objects.create_user(username='non_project_member', password='password')
        cls.team = create_team(cls.owner)
        cls.team.members.add(cls.subscriber, cls.commenter, cls.manager, cls.non_project_member)
        team_add_manager(cls.manager, cls.team)
        cls.project = Project.objects.create(title='Project Title', description='desc', manager=cls.manager, team=cls.team)
        cls.project.developers.add(cls.subscriber)
        cls.first_ticket = Ticket.objects.create(title='First Ticket Title', user=cls.commenter, project=cls.project, team=cls.team)
        cls.first_ticket.subscribers.remove(cls.commenter)
        cls.second_ticket = Ticket.objects.create(title='Second Ticket Title', user=cls.commenter, project=cls.project, team=cls.team)
        cls.second_ticket.subscribers.remove(cls.commenter)
        cls.url = reverse('tracker:subscribe_all', kwargs={'team_slug': cls.team.slug, 'project_pk': cls.project.pk})

    def test_subscriber(self):
        user = self.subscriber
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.first_ticket.subscribers.all().first(), user)
        self.assertEqual(self.second_ticket.subscribers.all().first(), user)

    def test_owner(self):
        user = self.owner
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.first_ticket.subscribers.all().first(), user)
        self.assertEqual(self.second_ticket.subscribers.all().first(), user)

    def test_project_level_subscription(self):
        user = self.owner
        self.assertEqual(self.project.subscribers.all().count(), 0)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.project.subscribers.all().count(), 1)

    def test_manager(self):
        user = self.manager
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.first_ticket.subscribers.all().first(), user)
        self.assertEqual(self.second_ticket.subscribers.all().first(), user)

    def test_non_project_member(self):
        user = self.non_project_member
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)

    def test_non_member(self):
        user = self.non_member
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)

    def test_anonymous_user(self):
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)

    def test_redirects(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_success_message(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertIn('Successfully subscribed to project.', response.content.decode('utf8'))

    def test_double_subscription(self):
        user = self.subscriber
        self.first_ticket.subscribers.add(user)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 1)


class TestSubscribeToTicket(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subscriber = User.objects.create_user(username='subscriber', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.owner)
        cls.team.members.add(cls.subscriber, cls.manager, cls.member)
        team_add_manager(cls.manager, cls.team)
        cls.project = Project.objects.create(title='Project Title', description='desc', manager=cls.manager,
                                             team=cls.team)
        cls.project.developers.add(cls.subscriber)
        cls.ticket = Ticket.objects.create(title='Ticket Title', user=cls.owner, project=cls.project,
                                                 team=cls.team, description='')
        cls.ticket.subscribers.remove(cls.owner)
        cls.url = reverse('tracker:subscribe_ticket', kwargs={'team_slug': cls.team.slug, 'pk': cls.ticket.pk})

    def test_subscriber(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        user = self.subscriber
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 1)

    def test_owner(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        user = self.owner
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 1)

    def test_manager(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        user = self.manager
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 1)

    def test_member(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        user = self.member
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        self.assertEqual(response.status_code, 404)

    def test_non_member(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        user = self.non_member
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        response = self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 0)
        self.assertEqual(response.status_code, 302)

    def test_redirects(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))

    def test_success_message(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertIn('You will now receive emails when comments are posted to this ticket or when it is closed.', response.content.decode('utf8'))


class TestUnsubscribeToTicket(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subscriber = User.objects.create_user(username='subscriber', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.owner)
        cls.team.members.add(cls.subscriber, cls.manager, cls.member)
        team_add_manager(cls.manager, cls.team)
        cls.project = Project.objects.create(title='Project Title', description='desc', manager=cls.manager,
                                             team=cls.team)
        cls.project.developers.add(cls.subscriber)
        cls.ticket = Ticket.objects.create(title='Ticket Title', user=cls.owner, project=cls.project,
                                                 team=cls.team, description='')
        cls.ticket.subscribers.remove(cls.owner)
        cls.ticket.subscribers.add(cls.subscriber)
        cls.ticket.save()
        cls.url = reverse('tracker:unsubscribe_ticket', kwargs={'team_slug': cls.team.slug, 'pk': cls.ticket.pk})

    def test_subscriber(self):
        self.assertEqual(self.ticket.subscribers.all().count(), 1)
        user = self.subscriber
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.ticket.subscribers.all().count(), 0)

    def test_redirects(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': self.ticket.pk}))

    def test_success_message(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertIn('You will no longer receive emails when comments are posted to this ticket or when it is closed.', response.content.decode('utf8'))


class TestProjectUnsubscribeToAllTickets(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.subscriber = User.objects.create_user(username='subscriber', password='password')
        cls.commenter = User.objects.create_user(username='commenter', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.team = create_team(cls.owner)
        cls.team.members.add(cls.subscriber, cls.commenter, cls.manager)
        team_add_manager(cls.manager, cls.team)
        cls.project = Project.objects.create(title='Project Title', description='desc', manager=cls.manager, team=cls.team)
        cls.project.developers.add(cls.subscriber)
        cls.first_ticket = Ticket.objects.create(title='First Ticket Title', user=cls.commenter, project=cls.project, team=cls.team)
        cls.first_ticket.subscribers.remove(cls.commenter)
        cls.second_ticket = Ticket.objects.create(title='Second Ticket Title', user=cls.commenter, project=cls.project, team=cls.team)
        cls.second_ticket.subscribers.remove(cls.commenter)
        cls.url = reverse('tracker:unsubscribe_all', kwargs={'team_slug': cls.team.slug, 'project_pk': cls.project.pk})
        cls.first_ticket.subscribers.add(cls.subscriber)
        cls.second_ticket.subscribers.add(cls.subscriber)

    def test_subscriber(self):
        user = self.subscriber
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 1)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)
        self.assertEqual(self.second_ticket.subscribers.all().count(), 0)

    def test_project_level_unsubscribe(self):
        user = self.subscriber
        self.project.subscribers.add(user)
        self.assertEqual(self.project.subscribers.all().count(), 1)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(self.project.subscribers.all().count(), 0)

    def test_closed_ticket(self):
        closed = Ticket.objects.create(title='closed', user=self.commenter, project=self.project, team=self.team, status='closed')
        closed.subscribers.remove(self.commenter)
        user = self.subscriber
        self.assertEqual(closed.subscribers.all().count(), 0)
        self.client.force_login(user)
        self.client.get(self.url)
        self.assertEqual(closed.subscribers.all().count(), 0)

    def test_redirects(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_success_message(self):
        user = self.subscriber
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        self.assertIn('Successfully unsubscribed from project.', response.content.decode('utf8'))

    def test_double_subscription(self):
        user = self.subscriber
        self.first_ticket.subscribers.add(user)
        self.first_ticket.save()
        self.assertEqual(self.first_ticket.subscribers.all().count(), 1)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(self.first_ticket.subscribers.all().count(), 0)


class TestSuperTicketDetailsViewCommentPost(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.developer = User.objects.create_user(username='developer', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.developer, cls.member)
        cls.project = Project.objects.create(title='Project Title', description='desc', team=cls.team, manager=cls.manager)
        cls.project.developers.add(cls.developer)

    def test_post_without_specifying_name(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_owner_get_view(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf8')
        self.assertIn('Testing the Ticket Title', html)

    def test_manager_get_view(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        self.client.force_login(self.manager)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf8')
        self.assertIn('Testing the Ticket Title', html)

    def test_developer_get_view(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        self.client.force_login(self.developer)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf8')
        self.assertIn('Testing the Ticket Title', html)

    def test_member_get_view(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        self.client.force_login(self.member)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 404)
        html = response.content.decode('utf8')
        self.assertNotIn('Testing the Ticket Title', html)

    def test_non_member_get_view(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        self.client.force_login(self.non_member)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 404)
        html = response.content.decode('utf8')
        self.assertNotIn('Testing the Ticket Title', html)

    def test_anonymous_user_get_view(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        response = self.client.get(reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf8')
        self.assertNotIn('Testing the Ticket Title', html)

    def test_owner_post_comment(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        comment = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(Comment.objects.all().count(), 0)
        response = self.client.post(url, comment, follow=True)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        posted_comment = Comment.objects.all().first()
        self.assertEqual(user, posted_comment.user)

    def test_manager_post_comment(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        comment = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        user = self.manager
        self.client.force_login(user)
        self.assertEqual(Comment.objects.all().count(), 0)
        response = self.client.post(url, comment, follow=True)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        posted_comment = Comment.objects.all().first()
        self.assertEqual(user, posted_comment.user)

    def test_developer_post_comment(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        comment = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        user = self.developer
        self.client.force_login(user)
        self.assertEqual(Comment.objects.all().count(), 0)
        response = self.client.post(url, comment, follow=True)
        self.assertEqual(Comment.objects.all().count(), 1)
        self.assertIn('Comment text.', response.content.decode('utf8'))
        posted_comment = Comment.objects.all().first()
        self.assertEqual(user, posted_comment.user)

    def test_member_post_comment(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        comment = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        user = self.member
        self.client.force_login(user)
        self.assertEqual(Comment.objects.all().count(), 0)
        response = self.client.post(url, comment, follow=True)
        self.assertEqual(Comment.objects.all().count(), 0)

    def test_non_member_post_comment(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        comment = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        user = self.non_member
        self.client.force_login(user)
        self.assertEqual(Comment.objects.all().count(), 0)
        response = self.client.post(url, comment, follow=True)
        self.assertEqual(Comment.objects.all().count(), 0)

    def test_anonymous_user_post_comment(self):
        ticket = Ticket.objects.create(title='Testing the Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        comment = {'comment': 'Comment text.', 'post_comment': 'Submit'}
        self.assertEqual(Comment.objects.all().count(), 0)
        response = self.client.post(url, comment, follow=True)
        self.assertEqual(Comment.objects.all().count(), 0)


class TestSuperTicketDetailsResolutionView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.project_developer = User.objects.create_user(username='developer', password='password')
        cls.ticket_assigned_developer = User.objects.create_user(username='ticket_assigned_developer', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.ticket_assigned_developer, cls.project_developer, cls.member)
        cls.project = Project.objects.create(title='Project Title', description='desc', team=cls.team, manager=cls.manager)
        cls.project.developers.add(cls.ticket_assigned_developer, cls.project_developer)

    def test_owner_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolution text')
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_subscribers_receive_email(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        subscriber = User.objects.create_user(username='subscriber', password='password')
        subscriber.email = 'valid@email.com'
        subscriber.save()
        ticket.subscribers.add(subscriber)
        self.project.developers.add(subscriber)
        self.team.members.add(subscriber)
        ticket.save()
        self.project.save()
        self.team.save()
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        response = self.client.post(url, form_data, follow=True)
        ticket.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [subscriber.email])
        self.assertIn(ticket.title, mail.outbox[0].subject)
        self.assertIn(ticket.resolution, mail.outbox[0].body)

    def test_manager_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.manager
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolution text')
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_assigned_developer_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        ticket.developer.add(self.ticket_assigned_developer)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.ticket_assigned_developer
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolution text')
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_unassigned_developer_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        ticket.developer.add(self.ticket_assigned_developer)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.project_developer
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)

    def test_member_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.member
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)

    def test_non_member_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.non_member
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)

    def test_anonymous_user_close_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)

    def test_unspecified_resolution_field(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'close_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, None)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Unspecified.')
        self.assertRedirects(response, reverse('tracker:project_details', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_pre_existing_resolution_field(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Already resolved')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'close_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, 'Already resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Already resolved')
        self.assertRedirects(response, reverse('tracker:project_details',
                                               kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_overwriting_pre_existing_resolution_field(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Already resolved')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'New resolution value', 'close_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, 'Already resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'New resolution value')
        self.assertRedirects(response, reverse('tracker:project_details',
                                               kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk}))

    def test_close_ticket_creates_closing_comment(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.comments.all().count(), 0)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.comments.all().count(), 1)
        comment = ticket.comments.all().first()
        self.assertEqual('Closed.', comment.text)

    def test_closing_comment_not_created_for_user_without_permissions(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team, user=self.owner)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'resolution': 'Resolution text', 'close_ticket': ''}
        user = self.member
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.comments.all().count(), 0)
        response = self.client.post(url, form_data, follow=True)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.comments.all().count(), 0)


class TestTicketReopenView(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.manager = User.objects.create_user(username='manager', password='password')
        self.project_developer = User.objects.create_user(username='developer', password='password')
        self.ticket_assigned_developer = User.objects.create_user(username='ticket_assigned_developer',
                                                                 password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.non_member = User.objects.create_user(username='non_member', password='password')
        self.team = create_team(self.owner)
        team_add_manager(self.manager, self.team)
        self.team.members.add(self.manager, self.ticket_assigned_developer, self.project_developer, self.member)
        self.project = Project.objects.create(title='Project Title', description='desc', team=self.team,
                                             manager=self.manager)
        self.project.developers.add(self.ticket_assigned_developer, self.project_developer)

    def test_owner_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, 'Resolved')
        self.assertRedirects(response, reverse('tracker:ticket_details',
                                               kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}))

    def test_manager_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.manager
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, 'Resolved')
        self.assertRedirects(response, reverse('tracker:ticket_details',
                                               kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}))

    def test_assigned_developer_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        ticket.developer.add(self.ticket_assigned_developer)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.ticket_assigned_developer
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.resolution, 'Resolved')
        self.assertRedirects(response, reverse('tracker:ticket_details',
                                               kwargs={'team_slug': self.team.slug, 'pk': ticket.pk}))

    def test_unassigned_developer_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.project_developer
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')

    def test_member_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.member
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')

    def test_non_member_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.non_member
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 404)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')

    def test_anonymous_user_reopen_ticket(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.resolution, 'Resolved')

    def test_owner_displays_ticket_reopen_button(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        user = self.owner
        self.client.force_login(user)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Reopen Ticket', response.content.decode('utf8'))

    def test_manager_displays_ticket_reopen_button(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        user = self.manager
        self.client.force_login(user)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Reopen Ticket', response.content.decode('utf8'))

    def test_assigned_developer_displays_ticket_reopen_button(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        ticket.developer.add(self.ticket_assigned_developer)
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        user = self.ticket_assigned_developer
        self.client.force_login(user)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Reopen Ticket', response.content.decode('utf8'))

    def test_unassigned_developer_displays_ticket_reopen_button(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        user = self.project_developer
        self.client.force_login(user)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Reopen Ticket', response.content.decode('utf8'))

    def test_member_displays_ticket_reopen_button(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        user = self.member
        self.client.force_login(user)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_reopening_ticket_creates_reopening_comment(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.comments.all().count(), 0)
        response = self.client.post(url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.comments.all().count(), 1)
        comment = ticket.comments.all().first()
        self.assertEqual('Reopened.', comment.text)

    def test_reopening_comment_not_created_for_user_without_permissions(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project, team=self.team,
                                       user=self.owner, resolution='Resolved', status='closed')
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.member
        self.client.force_login(user)
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.comments.all().count(), 0)
        response = self.client.post(url, form_data, follow=True)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'closed')
        self.assertEqual(ticket.comments.all().count(), 0)

    def test_subscribers_receive_email_upon_reopening(self):
        ticket = Ticket.objects.create(title='Ticket Title', description='desc', project=self.project,
                                       team=self.team, user=self.owner, status='closed')
        subscriber = User.objects.create_user(username='subscriber', password='password')
        subscriber.email = 'valid@email.com'
        subscriber.save()
        ticket.subscribers.add(subscriber)
        self.project.developers.add(subscriber)
        self.team.members.add(subscriber)
        ticket.save()
        self.project.save()
        self.team.save()
        url = reverse('tracker:ticket_details', kwargs={'team_slug': self.team.slug, 'pk': ticket.pk})
        form_data = {'reopen_ticket': ''}
        user = self.owner
        self.client.force_login(user)
        response = self.client.post(url, form_data, follow=True)
        ticket.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [subscriber.email])
        self.assertIn(ticket.title, mail.outbox[0].subject)
        self.assertIn('Reopened', mail.outbox[0].body)


class TestManageSubscriptions(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='user', password='password')
        cls.other_user = User.objects.create_user(username='other_user', password='password')
        cls.first_team = create_team(cls.user, 'First Team Title')
        cls.second_team = create_team(cls.user, 'Second Team Title')
        cls.first_project = Project.objects.create(title='First Project', description='desc', team=cls.first_team)
        cls.second_project = Project.objects.create(title='Second Project', description='desc', team=cls.second_team)
        cls.first_ticket = Ticket.objects.create(title='First Ticket', user=cls.user, team=cls.first_team, project=cls.first_project)
        cls.second_ticket = Ticket.objects.create(title='Second Ticket', user=cls.user, team=cls.first_team, project=cls.first_project)
        cls.third_ticket = Ticket.objects.create(title='Third Ticket', user=cls.user, team=cls.second_team, project=cls.second_project)
        cls.unassigned_project = Project.objects.create(title='Unassigned', description='desc', team=cls.first_team)
        cls.unassigned_ticket = Ticket.objects.create(title='Unassigned', user=cls.other_user, team=cls.first_team, project=cls.unassigned_project)
        cls.first_team.members.add(cls.user)
        cls.second_team.members.add(cls.user)
        cls.first_project.developers.add(cls.user)
        cls.second_project.developers.add(cls.user)
        cls.first_ticket.subscribers.add(cls.user)
        cls.second_ticket.subscribers.add(cls.user)
        cls.third_ticket.subscribers.add(cls.user)
        cls.first_team.save()
        cls.second_team.save()
        cls.first_project.save()
        cls.second_project.save()
        cls.first_ticket.save()
        cls.second_ticket.save()
        cls.third_ticket.save()
        cls.url = reverse('manage_subscriptions')

    def test_tickets_display(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.first_ticket.title, response.content.decode('utf8'))
        self.assertIn(self.second_ticket.title, response.content.decode('utf8'))
        self.assertIn(self.third_ticket.title, response.content.decode('utf8'))
        self.assertNotIn(self.unassigned_ticket.title, response.content.decode('utf8'))

    def test_closed_tickets_not_displayed(self):
        closed = Ticket.objects.create(title='Closed Ticket', user=self.user, team=self.first_team, project=self.first_project, status='closed')
        closed.subscribers.add(self.user)
        closed.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn(self.user, closed.subscribers.all())
        self.assertNotIn(closed.title, response.content.decode('utf8'))

    def test_archived_project_tickets_not_displayed(self):
        archived = Project.objects.create(title='Archived Project', description='desc', team=self.first_team, is_archived=True)
        ticket = Ticket.objects.create(title='Archived Ticket', user=self.user, team=self.first_team, project=archived)
        archived.developers.add(self.user)
        archived.save()
        ticket.subscribers.add(self.user)
        ticket.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn(self.user, ticket.subscribers.all())
        self.assertNotIn(ticket.title, response.content.decode('utf8'))


class TestCreateTicketAddsSubscribers(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.project_subscriber = User.objects.create_user(username='project_subscriber', password='password')
        self.team = create_team(self.owner)
        self.team.members.add(self.project_subscriber)
        self.project = Project.objects.create(title='Project Title', description='desc', manager=self.owner,
                                              team=self.team)
        self.project.subscribers.add(self.project_subscriber)
        self.url = reverse('tracker:create_ticket',
                           kwargs={'team_slug': self.team.slug}) + f'?project={self.project.pk}'
        self.form_data = {
            'title': 'Ticket Title',
            'priority': 'low',
            'status': 'open',
            'resolution': ''
        }

    def test_project_subscriber_added_to_ticket_subscribers(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(self.project.project_tickets.all().count(), 1)
        ticket = self.project.project_tickets.all().first()
        self.assertIn(self.project_subscriber, ticket.subscribers.all())

    def test_ticket_submitter_added_to_ticket_subscribers(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(self.project.project_tickets.all().count(), 1)
        ticket = self.project.project_tickets.all().first()
        self.assertIn(self.owner, ticket.subscribers.all())

    def test_ticket_submitter_not_added_when_notification_disabled(self):
        self.owner.notification_settings['auto_subscribe_to_submitted_tickets'] = False
        self.owner.save()
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(self.project.project_tickets.all().count(), 1)
        ticket = self.project.project_tickets.all().first()
        self.assertNotIn(self.owner, ticket.subscribers.all())

class TestProjectSubscribersReceiveEmailsOnTicketSubmission(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.subscriber = User.objects.create_user(username='subscriber', password='password')
        cls.subscriber.email = 'valid@email.com'
        cls.subscriber.save()
        cls.team = create_team(cls.owner)
        cls.team.members.add(cls.subscriber)
        cls.project = Project.objects.create(title='Project Title', description='desc', team=cls.team)
        cls.project.developers.add(cls.subscriber)
        cls.project.subscribers.add(cls.subscriber)

    def test_subscriber_receives_email(self):
        self.assertEqual(len(mail.outbox), 0)
        Ticket.objects.create(title='Ticket Title', user=self.owner, project=self.project, team=self.team)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_subject(self):
        Ticket.objects.create(title='Ticket Title', user=self.owner, project=self.project, team=self.team)
        self.assertIn(self.project.title, mail.outbox[0].subject)

    def test_email_body(self):
        Ticket.objects.create(title='Ticket Title', user=self.owner, project=self.project, team=self.team)
        self.assertIn(self.project.title, mail.outbox[0].body)

    def test_email_to(self):
        Ticket.objects.create(title='Ticket Title', user=self.owner, project=self.project, team=self.team)
        self.assertIn(self.subscriber.email, mail.outbox[0].to)


class TestTicketFileUploadView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.developer = User.objects.create_user(username='developer', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.developer, cls.member)
        cls.project = Project.objects.create(title='Project', description='desc', team=cls.team, manager=cls.manager)
        cls.project.developers.add(cls.developer)
        cls.ticket = Ticket.objects.create(title='Ticket', team=cls.team, project=cls.project, user=cls.owner, description='')
        cls.ticket.developer.add(cls.developer)
        cls.url = reverse('tracker:ticket_details', kwargs={'team_slug': cls.team.slug, 'pk': cls.ticket.pk})
        cls.form_data = {'upload_file': ''}

    def test_owner_get_permissions(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_manager_get_permissions(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_developer_get_permissions(self):
        self.client.force_login(self.developer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_member_get_permissions(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_non_member_get_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_get_permissions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_member_post_permissions(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 404)

    def test_non_member_post_permissions(self):
        self.client.force_login(self.non_member)
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_post_permissions(self):
        response = self.client.post(self.url, self.form_data)
        self.assertEqual(response.status_code, 302)


class TestNotificationSettingsTeamRoles(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = user('owner')
        cls.manager = user('manager')
        cls.manager.email = 'valid@email.com'
        cls.manager.save()
        cls.team = create_team(cls.owner)
        cls.team.members.add(cls.manager)

    def test_manual_key_assignment_false(self):
        self.manager.notification_settings['team_role_assignment'] = False
        self.assertFalse(self.manager.notification_settings.get('team_role_assignment'))

    def test_manual_key_assignment_true(self):
        self.manager.notification_settings['team_role_assignment'] = True
        self.assertTrue(self.manager.notification_settings.get('team_role_assignment'))

    def test_team_add_manager_false(self):
        self.manager.notification_settings['team_role_assignment'] = False
        self.manager.save()
        self.client.force_login(self.owner)
        self.client.get(f'/teams/{self.team.slug}/add-manager/?username=manager')
        self.assertIn(self.manager, self.team.get_managers())
        self.assertEqual(len(mail.outbox), 0)

    def test_team_add_manager_true(self):
        self.client.force_login(self.owner)
        self.client.get(f'/teams/{self.team.slug}/add-manager/?username=manager')
        self.assertIn(self.manager, self.team.get_managers())
        self.assertEqual(len(mail.outbox), 1)


class TestNotificationSettingsProjectRolesUpdateProject(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = user('owner')
        cls.manager = user('manager')
        cls.manager.email = 'valid@email.com'
        cls.manager.save()
        cls.developer = user('developer')
        cls.developer.email = 'valid@email.com'
        cls.developer.save()
        cls.team = create_team(cls.owner)
        cls.team.save()
        cls.existing_project = Project.objects.create(title='Project', description='desc', team=cls.team)
        cls.team.members.add(cls.manager, cls.developer)
        cls.team.add_manager(cls.manager)

    def test_update_project_manager_true(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': self.existing_project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description',
                                     'manager': str(self.manager.pk)})
        self.assertEqual(response.status_code, 302)
        self.existing_project.refresh_from_db()
        self.assertEqual(self.existing_project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 1)

    def test_update_project_manager_false(self):
        self.manager.notification_settings['project_role_assignment'] = False
        self.manager.save()
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:project_update',
                                            kwargs={'team_slug': self.team.slug, 'project_pk': self.existing_project.pk}),
                                    {'title': 'Project Title', 'description': 'Project description',
                                     'manager': str(self.manager.pk)})
        self.existing_project.refresh_from_db()
        self.assertEqual(self.existing_project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 0)


class TestNotificationSettingsProjectRolesCreateProject(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = user('owner')
        cls.manager = user('manager')
        cls.manager.email = 'valid@email.com'
        cls.manager.save()
        cls.developer = user('developer')
        cls.developer.email = 'valid@email.com'
        cls.developer.save()
        cls.team = create_team(cls.owner)
        cls.team.save()
        cls.team.members.add(cls.manager, cls.developer)
        cls.team.add_manager(cls.manager)

    def test_create_project_manager_true(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertEqual(project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 1)

    def test_create_project_manager_false(self):
        self.manager.notification_settings['project_role_assignment'] = False
        self.manager.save()
        self.client.force_login(self.owner)
        response = self.client.post(reverse('tracker:create_project', kwargs={'team_slug': self.team.slug}),
                                    {'title': 'Project Title', 'description': 'Project description', 'manager':str(self.manager.pk)})
        project = Project.objects.all().first()
        self.assertEqual(project.manager, self.manager)
        self.assertEqual(len(mail.outbox), 0)


class TestNotificationSettingsManageDevelopers(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.team_manager = User.objects.create_user(username='team_manager', password='password')
        cls.project_manager = User.objects.create_user(username='project_manager', password='password')
        cls.developer = User.objects.create_user(username='developer', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.member.email = 'valid@email.com'
        cls.member.save()
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.other_team_owner = User.objects.create_user(username='other_team_owner', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.team_manager, cls.team)
        team_add_manager(cls.project_manager, cls.team)
        cls.team.members.add(cls.team_manager, cls.project_manager, cls.developer, cls.member)
        cls.other_team = create_team(cls.other_team_owner, 'Other team')

    def setUp(self):
        self.project = Project.objects.create(
            title='Project Title', description='desc', team=self.team, manager=self.project_manager
        )
        self.project.developers.add(self.developer)
        self.url = reverse('tracker:project_manage_developers', kwargs={'team_slug': self.team.slug, 'project_pk': self.project.pk})

    def test_added_developer_true(self):
        self.client.force_login(self.owner)
        self.client.get(self.url + f'?add={self.member.username}', follow=True)
        self.project.refresh_from_db()
        self.assertIn(self.member, self.project.developers.all())
        self.assertEqual(len(mail.outbox), 1)

    def test_added_developer_false(self):
        self.member.notification_settings['project_role_assignment'] = False
        self.member.save()
        self.client.force_login(self.owner)
        self.client.get(self.url + f'?add={self.member.username}', follow=True)
        self.project.refresh_from_db()
        self.assertIn(self.member, self.project.developers.all())
        self.assertEqual(len(mail.outbox), 0)


class TestNotificationSettingsSendTeamInvitationView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='owner', password='password')
        cls.manager = User.objects.create_user(username='manager', password='password')
        cls.member = User.objects.create_user(username='member', password='password')
        cls.non_member = User.objects.create_user(username='non_member', password='password')
        cls.invitee = User.objects.create_user(username='invitee_username', password='password')
        cls.invitee.email = 'existing_invitee@email.com'
        cls.invitee.save()
        cls.invitee_without_email = User.objects.create_user(username='no_email', password='password')
        cls.team = create_team(cls.owner)
        team_add_manager(cls.manager, cls.team)
        cls.team.members.add(cls.manager, cls.member)
        cls.url = reverse('team_invite', kwargs={'team_slug': cls.team.slug})
        cls.post_data_email = {'invitee': 'invitee@email.com'}
        cls.post_data_username = {'invitee': cls.invitee.username}

    def test_username_post_true(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 1)

    def test_username_post_false(self):
        self.invitee.notification_settings['team_invites'] = False
        self.invitee.save()
        self.client.force_login(self.owner)
        self.client.post(self.url, data=self.post_data_username)
        self.assertEqual(len(mail.outbox), 0)


class TestTeamRemoveOwner(TestCase):
    def setUp(self):
        self.owner = user('owner')
        self.member = user('member')
        self.team = create_team(self.owner)
        self.team.members.add(self.member)
        self.url = reverse('team_remove_owner', kwargs={'team_slug': self.team.slug})

    def test_remove_owner_forbidden_when_solo_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 1)
        self.assertIn(self.owner, self.team.get_owners())
        self.assertRedirects(response, reverse('manage_team_ownership', kwargs={'team_slug': self.team.slug}))
        self.assertIn('You cannot step down as team owner until you', response.content.decode('utf8'))

    def test_remove_owner_success(self):
        self.team.add_owner(self.member)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 2)
        self.client.force_login(self.owner)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 1)
        self.assertNotIn(self.owner, self.team.get_owners())
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn(f'You are no longer an owner of team {self.team.title}', response.content.decode('utf8'))

    def test_member_cannot_access(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_email(self):
        self.owner.email='valid@email.com'
        self.owner.save()
        self.team.add_owner(self.member)
        self.client.force_login(self.owner)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.team.title, mail.outbox[0].body)
        self.assertIn(self.team.title, mail.outbox[0].subject)
        self.assertIn(self.owner.email, mail.outbox[0].to)


class TestTeamAddOwner(TestCase):
    def setUp(self):
        self.owner = user('owner')
        self.member = user('member')
        self.team = create_team(self.owner)
        self.team.members.add(self.member)
        self.url = reverse('team_add_owner', kwargs={'team_slug': self.team.slug})

    def test_owner_can_add(self):
        self.assertEqual(len(self.team.get_owners()), 1)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.member.username}', follow=True)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 2)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.member, self.team.get_owners())
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn(f'{self.member.username} added as a co-owner.', response.content.decode('utf8'))

    def test_member_cannot_add(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url + f'?username={self.member.username}', follow=True)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 1)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(self.member, self.team.get_owners())

    def test_adding_non_member(self):
        non_member = user('non_member')
        self.assertEqual(len(self.team.get_owners()), 1)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={non_member.username}', follow=True)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 1)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(non_member, self.team.get_owners())
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn('Cannot make co-owner.', response.content.decode('utf8'))

    def test_adding_nonexistent_user(self):
        self.assertEqual(len(self.team.get_owners()), 1)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + '?username=not_a_user', follow=True)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 1)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn('Cannot make co-owner.', response.content.decode('utf8'))

    def test_no_querystring(self):
        self.assertEqual(len(self.team.get_owners()), 1)
        self.client.force_login(self.owner)
        response = self.client.get(self.url, follow=True)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_owners()), 1)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn('Cannot make co-owner.', response.content.decode('utf8'))


class TestTeamRemoveManager(TestCase):
    def setUp(self):
        self.owner = user('owner')
        self.member = user('member')
        self.team = create_team(self.owner)
        self.team.members.add(self.member)
        self.team.add_manager(self.member)
        self.url = reverse('team_remove_manager', kwargs={'team_slug': self.team.slug})

    def test_remove_manager_success(self):
        self.assertEqual(len(self.team.get_managers()), 1)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_managers()), 0)
        self.assertNotIn(self.member, self.team.get_managers())
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn(f'{self.member.username} is no longer a team manager.', response.content.decode('utf8'))

    def test_invalid_username(self):
        self.assertEqual(len(self.team.get_managers()), 1)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + '?username=not_a_user', follow=True)
        self.assertEqual(response.status_code, 200)
        self.team.refresh_from_db()
        self.assertEqual(len(self.team.get_managers()), 1)
        self.assertIn(self.member, self.team.get_managers())
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn('Cannot remove manager.', response.content.decode('utf8'))

    def test_removing_manager_removes_from_team_projects(self):
        team_project = Project.objects.create(title='Title', description='desc', team=self.team, manager=self.member)
        owner_project = Project.objects.create(title='Title', description='desc', team=self.team, manager=self.owner)
        other_team_owner = user('other')
        other_team = create_team(owner=other_team_owner, title='Other Team')
        other_team.add_manager(self.member)
        other_project = Project.objects.create(title='Other', description='desc', team=other_team, manager=self.member)
        self.assertEqual(self.member, team_project.manager)
        self.assertEqual(self.member, other_project.manager)
        self.assertEqual(self.owner, owner_project.manager)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.member.username}', follow=True)
        team_project.refresh_from_db()
        owner_project.refresh_from_db()
        other_project.refresh_from_db()
        self.assertNotEqual(self.member, team_project.manager)
        self.assertEqual(self.member, other_project.manager)
        self.assertEqual(self.owner, owner_project.manager)


class TestTeamRemoveTeamMember(TestCase):
    def setUp(self):
        self.owner = user('owner')
        self.member = user('member')
        self.manager = user('manager')
        self.team = create_team(self.owner)
        self.team.members.add(self.member, self.manager)
        self.team.add_manager(self.manager)
        self.team.save()
        self.url = reverse('team_remove_manager', kwargs={'team_slug': self.team.slug})
        self.project = Project.objects.create(title='Project', description='desc', team=self.team, manager=self.manager)
        self.project.developers.add(self.member)
        self.ticket = Ticket.objects.create(title='Ticket', team=self.team, project=self.project, user=self.owner)
        self.ticket.developer.add(self.member)
        self.url = reverse('remove_team_member', kwargs={'team_slug': self.team.slug})

    def test_model_method_on_manager(self):
        self.assertEqual(self.project.manager, self.manager)
        self.team.remove_member(self.manager)
        self.team.refresh_from_db()
        self.project.refresh_from_db()
        self.assertNotIn(self.manager, self.team.members.all())
        self.assertNotEqual(self.project.manager, self.manager)

    def test_model_method_on_developer(self):
        self.assertIn(self.member, self.ticket.developer.all())
        self.assertIn(self.member, self.project.developers.all())
        self.team.remove_member(self.member)
        self.team.refresh_from_db()
        self.ticket.refresh_from_db()
        self.project.refresh_from_db()
        self.assertNotIn(self.member, self.team.members.all())
        self.assertNotIn(self.member, self.project.developers.all())
        self.assertNotIn(self.member, self.ticket.developer.all())

    def test_remove_manager_from_team(self):
        self.assertIn(self.manager, self.team.members.all())
        self.assertEqual(self.manager, self.project.manager)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.manager.username}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertNotIn(self.manager, self.team.members.all())
        self.assertNotEqual(self.project.manager, self.manager)

    def test_remove_developer_from_team(self):
        self.assertIn(self.member, self.team.members.all())
        self.assertIn(self.member, self.ticket.developer.all())
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.member.username}', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.member, self.team.members.all())
        self.assertNotIn(self.member, self.ticket.developer.all())

    def test_invalid_username(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username=not_a_user', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.team.members.all()), 3)
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))

    def test_remove_manager_related_projects(self):
        other_owner = user('other')
        other_team = create_team(owner=other_owner, title='Other Team')
        other_team.members.add(self.manager)
        other_team.add_manager(self.manager)
        manager_other_project = Project.objects.create(title='Other', description='desc', manager=self.manager, team=other_team)
        owner_other_project = Project.objects.create(title='Other', description='desc', manager=self.owner, team=self.team)
        self.assertEqual(manager_other_project.manager, self.manager)
        self.assertIn(self.manager, other_team.get_managers())
        self.assertEqual(owner_other_project.manager, self.owner)
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.manager.username}', follow=True)
        manager_other_project.refresh_from_db()
        other_team.refresh_from_db()
        self.assertEqual(manager_other_project.manager, self.manager)
        self.assertIn(self.manager, other_team.get_managers())
        self.assertEqual(owner_other_project.manager, self.owner)

    def test_remove_developer_related_projects(self):
        other_owner = user('other')
        other_team = create_team(owner=other_owner, title='Other Team')
        other_team.members.add(self.manager, self.member)
        other_team.add_manager(self.manager)
        manager_other_project = Project.objects.create(title='Other', description='desc', manager=self.manager, team=other_team)
        manager_other_project.developers.add(self.member)
        other_team_ticket = Ticket.objects.create(title='title', team=other_team, project=manager_other_project, user=other_owner)
        other_team_ticket.developer.add(self.member)
        self.assertIn(self.member, manager_other_project.developers.all())
        self.assertIn(self.member, other_team_ticket.developer.all())
        self.assertIn(self.member, other_team.members.all())
        self.client.force_login(self.owner)
        response = self.client.get(self.url + f'?username={self.member.username}', follow=True)
        manager_other_project.refresh_from_db()
        other_team.refresh_from_db()
        other_team_ticket.refresh_from_db()
        self.assertIn(self.member, manager_other_project.developers.all())
        self.assertIn(self.member, other_team_ticket.developer.all())
        self.assertIn(self.member, other_team.members.all())


class TestLeaveTeam(TestCase):
    def setUp(self):
        self.owner = user('owner')
        self.member = user('member')
        self.member.email = 'valid@email.com'
        self.member.save()
        self.team = create_team(self.owner)
        self.team.members.add(self.member)
        self.url = reverse('leave_team', kwargs={'team_slug': self.team.slug})

    def test_member_leaves_team(self):
        self.assertIn(self.member, self.team.members.all())
        self.client.force_login(self.member)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('team_list'))
        self.assertIn('You have left', response.content.decode('utf8'))
        self.assertNotIn(self.member, self.team.members.all())

    def test_owner_cannot_leave_team(self):
        self.assertIn(self.owner, self.team.members.all())
        self.client.force_login(self.owner)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('team_details', kwargs={'team_slug': self.team.slug}))
        self.assertIn('You cannot', response.content.decode('utf8'))
        self.assertIn(self.owner, self.team.members.all())

    def test_email(self):
        self.assertEqual(len(mail.outbox), 0)
        self.client.force_login(self.member)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(len(mail.outbox), 1)
