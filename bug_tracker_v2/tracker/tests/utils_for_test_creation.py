from bug_tracker_v2.users.models import User
from .. import models

def create_team(owner, title='Team Title'):
    team = models.Team.objects.create(title=title, description='desc')
    models.TeamMembership.objects.create(team=team, user=owner, role=3)
    return team

def team_add_manager(user, team):
    if user in team.members.all():
        membership = models.TeamMembership.objects.get(team=team, user=user)
        membership.role = 2
        membership.save()
    else:
        models.TeamMembership.objects.create(team=team, user=user, role=2)

def team_add_member(user, team):
    models.TeamMembership.objects.create(team=team, user=user)

def user(username):
    return User.objects.create_user(username=username, password='password')
