NOTIFICATION_SETTING_DEFAULTS = {
    'team_role_assignment': True,
    'project_role_assignment': True,
    'auto_subscribe_to_submitted_tickets': True,
    'team_invites': True,
}

NOTIFICATION_SETTING_DESCRIPTIONS = {
    'team_role_assignment': {
        'title': 'Team Manager Assignment',
        'description': 'This setting notifies you when you have been assigned as a team manager.',
        'slug': 'team_role_assignment',
            },
    'project_role_assignment': {
        'title': 'Project Role Assignment',
        'description': 'This setting notifies you when you have been assigned as a project manager or developer.',
        'slug': 'project_role_assignment',
            },
    'auto_subscribe_to_submitted_tickets': {
        'title': 'Your Submitted Tickets',
        'description': 'This setting controls whether you will be automatically subscribed to email notifications for tickets you submit.',
        'slug': 'auto_subscribe_to_submitted_tickets',
            },
    'team_invites': {
        'title': 'Team Invites',
        'description': 'This setting controls whether you will receive notifications when you receive new team invitations.',
        'slug': 'team_invites',
            },
}
