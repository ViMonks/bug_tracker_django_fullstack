from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField, BooleanField, IntegerField
from django.contrib.postgres.fields import JSONField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


from django.utils.deconstruct import deconstructible
from django.core import validators

@deconstructible
class MyUnicodeUsernameValidator(validators.RegexValidator):
    """This is identical to the validator used in Django's default AbstractUser class except I removed the '@' symbol from the regex and the message."""
    regex = r'^[\w.+-]+\Z'
    message = _(
        'Enter a valid username. This value may contain only letters, '
        'numbers, and ./+/-/_ characters.'
    )
    flags = 0


class User(AbstractUser):
    """Default user for Bug Tracker v2.
    """

    #: First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    is_manager = BooleanField(default=False)
    last_viewed_project_pk = IntegerField(null=True, blank=True, default=None)
    notification_settings = JSONField(null=True, blank=True, default=dict)

    # adding custom validation to username: no '@' symbol
    username_validator = MyUnicodeUsernameValidator()

    # this is identical to the field definition in Django's AbstractUser class except for the removal of "@" from the help_text attribute.
    # The primary change is in the username_validator attribute above, using my customized Validator.
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and ./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    def get_pending_invitations_count(self):
        return self.teaminvitation_set.filter(status=1).count()


