"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase

from models import db, User, Message, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        self.uid = 94566
        u = User.signup("testing", "testing@test.com", "password", None)
        u.id = self.uid
        db.session.commit()

        self.u = User.query.get(self.uid)

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does basic model work?"""
        
        m = Message(
            text="a warble",
            user_id=self.uid
        )

        db.session.add(m)
        db.session.commit()

        # User should have 1 message
        self.assertEqual(len(self.u.messages), 1)
        self.assertEqual(self.u.messages[0].text, "a warble")

    def test_message_likes(self):
        m1 = Message(
            text="a warble",
            user_id=self.uid
        )

        m2 = Message(
            text="a very interesting warble",
            user_id=self.uid 
        )

        u = User.signup("yetanothertest", "t@email.com", "password", None)
        uid = 888
        u.id = uid
        db.session.add_all([m1, m2, u])
        db.session.commit()

        u.likes.append(m1)

        db.session.commit()

        l = Likes.query.filter(Likes.user_id == uid).all()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0].message_id, m1.id)


    def test_get_user_messages(self):
        user_messages = Message.get_user_messages(self.u.id)
        self.assertEqual(len(user_messages), 0)
        self.assertEqual(self.u.messages, user_messages)

        m = Message(
            text="a warble",
            user_id=self.uid
        )

        db.session.add(m)
        db.session.commit()

        user_messages = Message.get_user_messages(self.u.id)
        self.assertEqual(len(user_messages), 1)
        self.assertEqual(self.u.messages, user_messages)

    def test_get_messages(self):
        """get logged in user following messages and logged in user messages"""
        following_ids = [f.id for f in self.u.following] + [self.u.id]
        messages = Message.get_messages(following_ids)
        self.assertEqual(len(messages), 0)

        user = User.signup("yetanothertest", "t@email.com", "password", None)
        uid = 888
        user.id = uid

        m1 = Message(
            text="a warble",
            user_id=user.id
        )

        m2 = Message(
            text="a very interesting warble",
            user_id=self.u.id
        )

        self.u.following.append(user)


        db.session.add_all([user, m1, m2])
        db.session.commit()

        following_ids = [f.id for f in self.u.following] + [self.u.id]
        messages = Message.get_messages(following_ids)
        self.assertEqual(len(messages), 2)

    def test_get_message(self):
        m2 = Message(
            text="a very interesting warble",
            user_id=self.u.id
        )
        m2.id = 101
        db.session.add(m2)
        db.session.commit()

        message = Message.get_message(m2.id)
        self.assertEqual(message, m2)