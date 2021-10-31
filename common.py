from flask import Flask, session, flash, redirect, g

CURR_USER_KEY = "curr_user"






def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

def redirect_guest():
    """redirect guests that are not logged in"""
    if g.user == None:
        flash("Access unauthorized.", "danger")
        return redirect("/login")