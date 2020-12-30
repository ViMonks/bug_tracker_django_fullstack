from django.test import TestCase
from bug_tracker_v2.users.models import User

# testing coverage: coverage run manage.py test --settings=config.settings.test
# coverage html --omit="admin.py"

class TrivialTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='name', password='password')

    def test_trivial(self):
        self.assertEqual(True, True)

    def test_bad_login(self):
        self.assertEqual(False, self.client.login(username='name', password='wrong_password'))

    def test_good_login(self):
        self.assertEqual(True, self.client.login(username='name', password='password'))

    def test_nonexistent_user_login(self):
        self.assertEqual(False, self.client.login(username='not_exist', password='password'))
