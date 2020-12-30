from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from .home_view import HomePage
from bug_tracker_v2.tracker.views import (
    TeamDetails, TeamListView, TeamCreateView, TeamAddManager, AcceptTeamInvitation, SendTeamInvitation,
    ManageSubscriptions, MultipleUnsubscribeView, InvitationsListView, DeclineTeamInvitation, ManageNotificationSettings,
    EnableNotificationSetting, DisableNotificationSetting, TeamRemoveManager, TeamAddOwner, ManageTeamOwnership,
    ManageTeamOwnershipWarning, TeamRemoveOwner, TeamRemoveMember, LeaveTeam,
)

from django.urls import reverse

urlpatterns = [
    # path("", HomePage.as_view(), name="home"),
    path("", TeamListView.as_view(), name='home'),
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("bug_tracker_v2.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path('teams/<slug:team_slug>/', TeamDetails.as_view(), name='team_details'),
    path('teams/<slug:team_slug>/', include('bug_tracker_v2.tracker.urls', namespace='tracker')),
    path('teams/', TeamListView.as_view(), name='team_list'),
    path('create-team/', TeamCreateView.as_view(), name='team_create'),
    path('teams/<slug:team_slug>/leave-team/', LeaveTeam.as_view(), name='leave_team'),
    path('teams/<slug:team_slug>/add-manager/', TeamAddManager.as_view(), name='team_add_manager'),
    path('teams/<slug:team_slug>/remove-manager/', TeamRemoveManager.as_view(), name='team_remove_manager'),
    path('teams/<slug:team_slug>/warning/', ManageTeamOwnershipWarning.as_view(), name='team_ownership_warning'),
    path('teams/<slug:team_slug>/manage-ownership/', ManageTeamOwnership.as_view(), name='manage_team_ownership'),
    path('teams/<slug:team_slug>/add-owner/', TeamAddOwner.as_view(), name='team_add_owner'),
    path('teams/<slug:team_slug>/remove-owner/', TeamRemoveOwner.as_view(), name='team_remove_owner'),
    path('teams/<slug:team_slug>/remove-member/', TeamRemoveMember.as_view(), name='remove_team_member'),
    path('teams/<slug:team_slug>/invite/', SendTeamInvitation.as_view(), name='team_invite'),
    path('accept-invitation/', AcceptTeamInvitation.as_view(), name='accept_team_invitation'),
    path('decline-invitation/', DeclineTeamInvitation.as_view(), name='decline_team_invitation'),
    path('pending-invitations/', InvitationsListView.as_view(), name='pending_invitations'),
    path('my-subscriptions/', ManageSubscriptions.as_view(), name='manage_subscriptions'),
    path('manage-notifications/', ManageNotificationSettings.as_view(), name='manage_notifications'),
    path('disable-notifications/', DisableNotificationSetting.as_view(), name='disable_notification'),
    path('enable-notifications/', EnableNotificationSetting.as_view(), name='enable_notification'),
    path('multiple-unsubscribe/', MultipleUnsubscribeView.as_view(), name='multiple_unsubscribe'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "error-400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "error-403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "error-404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("error-500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
