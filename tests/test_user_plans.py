import pytest
from flask import url_for
from flask_login import current_user
import io
import os
from unittest.mock import patch, MagicMock


def test_user_plan_tagging(app, db_session, free_user, starter_user, pro_user):
    """Test that users can be tagged with different plans."""
    with app.app_context():
        # Refresh users from database to ensure they're attached to the session
        free_user = db_session.merge(free_user)
        starter_user = db_session.merge(starter_user)
        pro_user = db_session.merge(pro_user)
        
        # Verify users have correct plan types
        assert free_user.plan_type == "free"
        assert starter_user.plan_type == "starter"
        assert pro_user.plan_type == "pro"


def test_login_required_for_upload(client):
    """Test that users must be logged in to access upload routes."""
    response = client.get('/pdf/upload')
    # Should redirect to login page if not logged in
    assert response.status_code == 302
    # Check for any login-related redirect, not just specific endpoint
    assert '/login' in response.location or 'auth' in response.location

def test_free_user_can_access_upload(login_as_free):
    """Test that free users can access the upload page."""
    response = login_as_free.get('/pdf/upload')
    assert response.status_code == 200

def test_starter_user_can_access_upload(login_as_starter):
    """Test that starter users can access the upload page."""
    response = login_as_starter.get('/pdf/upload')
    assert response.status_code == 200

def test_pro_user_can_access_upload(login_as_pro):
    """Test that pro users can access the upload page."""
    response = login_as_pro.get('/pdf/upload')
    assert response.status_code == 200
