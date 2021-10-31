import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from werkzeug.exceptions import NotFound
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, MessageForm
from models import db, connect_db, User, Message
from common import do_login, do_logout, redirect_guest

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "esUnSecreto")
toolbar = DebugToolbarExtension(app)

connect_db(app)

# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""
    if CURR_USER_KEY in session:
        g.user = User.get_user(session[CURR_USER_KEY])
    else:
        g.user = None



@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.
    Create new user and add to DB. Redirect to home page.
    If form not valid, present form.
    If the there already is a user with that username: flash message
    and re-present form.
    """
    do_logout()
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""
    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()
    flash("You have successfully logged out.", 'success')
    return redirect("/login")


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.
    Can take a 'q' param in querystring to search by that username.
    """

    search_term = request.args.get('q')

    if not search_term:
        users = User.all_users()
    else:
        users = User.search_users(search_term)

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""
    user = User.get_user(user_id)
    messages = Message.get_user_messages(user_id)
    likes = [message.id for message in user.likes]
    return render_template('users/show.html', user=user, messages=messages, likes=likes)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""
    redirect_guest()
    user = User.get_user(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""
    redirect_guest()
    user = User.get_user(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""
    redirect_guest()
    followed_user = User.get_user(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""
    redirect_guest()
    followed_user = User.get_user(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")

@app.route('/users/<int:user_id>/likes', methods=["GET"])
def show_likes(user_id):
    """get user likes by user_id"""
    redirect_guest()
    user = User.get_user(user_id)
    return render_template('users/likes.html', user=user, likes=user.likes)


@app.route('/messages/<int:message_id>/like', methods=['POST'])
def add_like(message_id):
    """Toggle a liked message for the currently-logged-in user."""

    redirect_guest()
    liked_message = Message.get_message(message_id)
    try:
        if liked_message.user_id == g.user.id:
            flash("you can only like someone else's message", "warning")
            return redirect("/")
    except AttributeError:
        flash("Access unauthorized", "warning")
        return redirect("/login")

    user_likes = g.user.likes

    if liked_message in user_likes:
        g.user.likes = [like for like in user_likes if like != liked_message]
        flash("unliked", "warning")
    else:
        g.user.likes.append(liked_message)
        flash("liked", "primary")

    db.session.commit()

    return redirect("/")

    


@app.route('/users/profile', methods=["GET", "POST"])
def edit_profile():
    """Update profile for current user."""
    redirect_guest()
    user = g.user
    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/images/default-pic.png"
            user.header_image_url = form.header_image_url.data or "/static/images/warbler-hero.jpg"
            user.bio = form.bio.data

            db.session.commit()
            return redirect(f"/users/{user.id}")

        flash("Wrong password, please try again.", 'danger')

    return render_template('users/edit.html', form=form, user_id=user.id)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""
    redirect_guest()
    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:
    Show form if GET. If valid, update message and redirect to user page.
    """
    redirect_guest()
    form = MessageForm()

    if form.validate_on_submit():
        try:
            msg = Message(text=form.text.data)
            g.user.messages.append(msg)
            db.session.commit()
        except AttributeError:
            return redirect("/login")

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.get_message(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""
    redirect_guest()
    msg = Message.get_message(message_id)
    try:
        if msg.user_id != g.user.id:
            flash("Access unauthorized.", "danger")
            return redirect("/")
    except AttributeError:
        flash("Access unauthorized.", "danger")
        return redirect("/login")

    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """
    if g.user != None:
        following_ids = [f.id for f in g.user.following] + [g.user.id]
        messages = (Message.get_messages(following_ids))
        liked_msg_ids = [msg.id for msg in g.user.likes]

        return render_template('home.html', messages=messages, likes=liked_msg_ids)

    else:
        return render_template('home-anon.html')


@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return render_template('404.html'), 404


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
