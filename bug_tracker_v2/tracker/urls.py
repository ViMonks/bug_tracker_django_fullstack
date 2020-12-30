from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    path('tickets/', views.TicketTable.as_view(), name='ticket_list'),
    path('tickets/closed/', views.ClosedTicketTable.as_view(), name='closed_ticket_list'),
    path('tickets/assigned/', views.AssignedTicketTable.as_view(), name='assigned_ticket_list'),
    path('tickets/assigned/closed/', views.ClosedAssignedTicketTable.as_view(), name='closed_assigned_ticket_list'),
    path('tickets/create/', views.CreateTicket.as_view(), name='create_ticket'),
    path('tickets/<pk>/', views.SuperTicketDetails.as_view(), name='ticket_details'),
    path('tickets/<pk>/update', views.UpdateTicket.as_view(), name='ticket_update'),
    path('tickets/<pk>/subscribe/', views.SubscribeTicketView.as_view(), name='subscribe_ticket'),
    path('tickets/<pk>/unsubscribe/', views.UnsubscribeTicketView.as_view(), name='unsubscribe_ticket'),
    path('projects/', views.ProjectTable.as_view(), name='project_list'),
    path('projects/archived/', views.ArchivedProjectTable.as_view(), name='archived_project_list'),
    path('archive-project/<project_pk>/', views.ToggleArchiveProject.as_view(), name='archive_project'),
    path('projects/<project_pk>/', views.ProjectDetails.as_view(), name='project_details'),
    path('projects/<project_pk>/update', views.UpdateProject.as_view(), name='project_update'),
    path('projects/<project_pk>/manage-developers/', views.ProjectManageDevelopers.as_view(), name='project_manage_developers'),
    path('projects/<project_pk>/closed_tickets', views.ProjectDetailsClosedTickets.as_view(), name='project_details_closed_tickets'),
    path('projects/<project_pk>/subscribe_to_all/', views.ProjectSubscribeAllTicketsView.as_view(), name='subscribe_all'),
    path('projects/<project_pk>/unsubscribe_to_all/', views.ProjectUnsubscribeAllTicketsView.as_view(),
         name='unsubscribe_all'),
    path('projects/create', views.CreateProject.as_view(), name='create_project'),
    path('delete-comment/<pk>/', views.CommentDelete.as_view(), name='delete_comment'),
    ### Team-related URLs
    path('team_details/', views.TeamDetails.as_view(), name='team_details'),
    path('update/', views.TeamUpdateView.as_view(), name='team_update'),
]
