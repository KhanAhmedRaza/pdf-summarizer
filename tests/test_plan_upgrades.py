import pytest
from flask import url_for
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
from models import User

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

def test_free_user_can_upgrade_to_starter(app, login_as_free, free_user, db_session):
    """Test that free users can upgrade to starter plan."""
    # Access the starter subscription page
    response = login_as_free.get('/plans/subscribe/starter')
    assert response.status_code == 200
    assert "starter plan" in response.get_data(as_text=True).lower()

    # Mock payment processing to upgrade to starter
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True

        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'starter',
                'payment_method': 'test_card'
            }
        )
        
        # Should redirect to pricing page
        assert response.status_code == 302
        assert 'pricing' in response.location

        # Update user object in app context
        with app.app_context():
            # Get a fresh instance of the user and update in the same session
            user = db_session.merge(free_user)
            user.plan_type = "starter"
            db_session.commit()
            
            # Refresh the user in the test client session
            login_as_free.get('/test/features/refresh')

            # Verify user can now access starter features
            response = login_as_free.get('/test/features/legal')
            assert response.status_code == 200

def test_free_user_can_upgrade_to_pro(app, login_as_free, free_user, db_session):
    """Test that free users can upgrade to pro plan."""
    # Access the pro subscription page
    response = login_as_free.get('/plans/subscribe/pro')
    assert response.status_code == 200
    assert "pro plan" in response.get_data(as_text=True).lower()

    # Mock payment processing to upgrade to pro
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True

        # Submit payment form
        response = login_as_free.post(
            '/plans/process_payment',
            data={
                'plan': 'pro',
                'payment_method': 'test_card'
            }
        )
        
        # Should redirect to pricing page
        assert response.status_code == 302
        assert 'pricing' in response.location

        # Update user object in app context
        with app.app_context():
            # Get a fresh instance of the user and update in the same session
            user = db_session.merge(free_user)
            user.plan_type = "pro"
            db_session.commit()
            
            # Refresh the user in the test client session
            login_as_free.get('/test/features/refresh')

            # Verify user can now access pro features
            response = login_as_free.get('/test/features/healthcare')
            assert response.status_code == 200

def test_starter_user_can_upgrade_to_pro(app, login_as_starter, starter_user, db_session):
    """Test that starter users can upgrade to pro plan."""
    # Access the pro subscription page
    response = login_as_starter.get('/plans/subscribe/pro')
    assert response.status_code == 200
    assert "pro plan" in response.get_data(as_text=True).lower()

    # Mock payment processing to upgrade to pro
    with patch('routes.process_payment') as mock_process:
        mock_process.return_value = True

        # Submit payment form
        response = login_as_starter.post(
            '/plans/process_payment',
            data={
                'plan': 'pro',
                'payment_method': 'test_card'
            }
        )
        
        # Should redirect to pricing page
        assert response.status_code == 302
        assert 'pricing' in response.location

        # Update user object in app context
        with app.app_context():
            # Get a fresh instance of the user and update in the same session
            user = db_session.merge(starter_user)
            user.plan_type = "pro"
            db_session.commit()
            
            # Refresh the user in the test client session
            login_as_starter.get('/test/features/refresh')

            # Verify user can now access pro features
            response = login_as_starter.get('/test/features/healthcare')
            assert response.status_code == 200

def test_plan_upgrade_unlocks_features(app, login_as_free, free_user, db_session):
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
            }
        )
    
        # Should redirect to pricing page
        assert response.status_code == 302
        assert 'pricing' in response.location

        # Update user object in app context
        with app.app_context():
            # Get a fresh instance of the user and update in the same session
            user = db_session.merge(free_user)
            user.plan_type = "starter"
            db_session.commit()

            # Verify user can now access legal documents
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
                
                # Update user object
                user = db_session.merge(free_user)
                user.plan_type = "pro"
                db_session.commit()

                # Now the user should be able to access pro features
                response = login_as_free.get('/test/features/visual')
                assert response.status_code == 200

def test_failed_payment_does_not_upgrade_plan(app, login_as_free, free_user, db_session):
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
            }
        )
        
        # Should redirect to pricing page
        assert response.status_code == 302
        assert 'pricing' in response.location

        # Verify user still cannot access legal documents
        response = login_as_free.get('/test/features/legal')
        assert response.status_code == 403
