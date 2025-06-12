from flask import Flask, redirect, url_for, session, request, jsonify, abort
from authlib.integrations.flask_client import OAuth
import os

def setup_oauth(app):
    oauth = OAuth(app)
    
    # Check if Google OAuth credentials are configured
    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        app.logger.warning("Google OAuth credentials not found. Google login will be disabled.")
        return oauth
    
    # Configure Google OAuth
    google = oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    
    return oauth
