import pytest
from flask import url_for
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta

def test_subscribe_starter_route_requires_login(client):
    """Test that the starter subscription route requires login."""
    response = client.get('/plans/subscribe/starter')
    # Should redirect to login
    assert response.status_code == 302
    assert '/login' in response.location

def test_subscribe_pro_route_requires_login(client):
    """Test that the pro subscription route requires login."""
    response = client.get('/plans/subscribe/pro')
    # Should redirect to login
    assert response.status_code == 302
    assert '/login' in response.location

def test_free_user_can_upgrade_to_starter(app, login_as_free, free_user):
    """Test that free users can upgrade to starter plan."""
    # Access the starter subscription page
    response = login_as_free.get('/plans/subscribe/starter')
    assert response.status_code == 200
    
    # Mock payment processing
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True
        
        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'starter',
                'payment_method': 'test_card'
            },
            follow_redirects=True
        )
        
        # Verify user plan was updated
        with app.app_context():
            assert free_user.plan_type == "starter"
            assert free_user.plan_start_date is not None
            assert free_user.plan_end_date is not None
            # Plan should be valid for 30 days
            assert free_user.plan_end_date > datetime.utcnow() + timedelta(days=29)

def test_free_user_can_upgrade_to_pro(app, login_as_free, free_user):
    """Test that free users can upgrade to pro plan."""
    # Access the pro subscription page
    response = login_as_free.get('/plans/subscribe/pro')
    assert response.status_code == 200
    
    # Mock payment processing
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True
        
        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'pro',
                'payment_method': 'test_card'
            },
            follow_redirects=True
        )
        
        # Verify user plan was updated
        with app.app_context():
            assert free_user.plan_type == "pro"
            assert free_user.plan_start_date is not None
            assert free_user.plan_end_date is not None
            # Plan should be valid for 30 days
            assert free_user.plan_end_date > datetime.utcnow() + timedelta(days=29)

def test_starter_user_can_upgrade_to_pro(app, login_as_starter, starter_user):
    """Test that starter users can upgrade to pro plan."""
    # Access the pro subscription page
    response = login_as_starter.get('/plans/subscribe/pro')
    assert response.status_code == 200
    
    # Mock payment processing
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True
        
        # Submit payment form
        response = login_as_starter.post(
            '/plans/process_payment',
            data={
                'plan': 'pro',
                'payment_method': 'test_card'
            },
            follow_redirects=True
        )
        
        # Verify user plan was updated
        with app.app_context():
            assert starter_user.plan_type == "pro"
            assert starter_user.plan_start_date is not None
            assert starter_user.plan_end_date is not None
            # Plan should be valid for 30 days
            assert starter_user.plan_end_date > datetime.utcnow() + timedelta(days=29)

def test_plan_upgrade_unlocks_features(app, login_as_free, free_user):
    """Test that upgrading plans unlocks new features."""
    # Verify free user cannot access legal documents
    response = login_as_free.get('/test/features/legal')
    assert response.status_code == 403
    
    # Mock payment processing to upgrade to starter
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True
        
        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'starter',
                'payment_method': 'test_card'
            },
            follow_redirects=True
        )
        
        # Update user object in app context
        with app.app_context():
            free_user.plan_type = "starter"
            app.db.session.commit()
    
    # Now the user should be able to access legal documents
    response = login_as_free.get('/test/features/legal')
    assert response.status_code == 200
    
    # But still cannot access pro features
    response = login_as_free.get('/test/features/visual')
    assert response.status_code == 403
    
    # Mock payment processing to upgrade to pro
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True
        
        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'pro',
                'payment_method': 'test_card'
            },
            follow_redirects=True
        )
        
        # Update user object in app context
        with app.app_context():
            free_user.plan_type = "pro"
            app.db.session.commit()
    
    # Now the user should be able to access pro features
    response = login_as_free.get('/test/features/visual')
    assert response.status_code == 200

def test_failed_payment_does_not_upgrade_plan(app, login_as_free, free_user):
    """Test that failed payments do not upgrade the user's plan."""
    # Mock payment processing to fail
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = False
        
        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'starter',
                'payment_method': 'invalid_card'
            },
            follow_redirects=True
        )
        
        # Verify user plan was not updated
        with app.app_context():
            assert free_user.plan_type == "free"
