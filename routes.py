from flask import Blueprint, redirect, url_for, flash, render_template, request, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db, User, MonthlyUsage, Upload


# Create blueprint
plans_bp = Blueprint('plans', __name__)

@plans_bp.route('/free')
@login_required
def free_plan():
    """Handle free plan selection"""
    # Update user plan to free
    current_user.plan_type = "free"
    current_user.plan_start_date = datetime.utcnow()
    current_user.plan_end_date = None  # Free plan has no end date
    db.session.commit()
    
    flash("You are now on the Free plan.", "success")
    return redirect(url_for('dashboard'))

@plans_bp.route('/starter')
@login_required
def starter_plan():
    """Handle starter plan selection"""
    # Redirect to subscription page for Starter plan
    return redirect(url_for('plans.subscribe', plan_type='starter'))

@plans_bp.route('/pro')
@login_required
def pro_plan():
    """Handle pro plan selection"""
    # Redirect to subscription page for Pro plan
    return redirect(url_for('plans.subscribe', plan_type='pro'))

@plans_bp.route('/subscribe/<plan_type>')
@login_required
def subscribe(plan_type):
    """Handle subscription process for paid plans"""
    if plan_type not in ['starter', 'pro']:
        flash("Invalid plan selected.", "error")
        return redirect(url_for('pricing'))
    
    # Store plan type in session for payment processing
    session['selected_plan'] = plan_type
    
    # In a real application, this would redirect to a payment page
    # For this mock implementation, we'll render a simple payment form
    return render_template('subscribe.html', plan=plan_type)

@plans_bp.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    """Process payment for subscription (mock implementation)"""
    plan_type = session.get('selected_plan')
    if not plan_type:
        flash("No plan selected.", "error")
        return redirect(url_for('pricing'))
    
    # In a real application, this would process payment through a payment gateway
    # For this mock implementation, we'll simulate a successful payment
    
    # Update user plan based on selection
    current_user.plan_type = plan_type
    current_user.plan_start_date = datetime.utcnow()
    
    # Set plan end date to 1 month from now
    current_user.plan_end_date = datetime.utcnow() + timedelta(days=30)
    
    db.session.commit()
    
    flash(f"Payment successful! You are now on the {plan_type.capitalize()} plan.", "success")
    return redirect(url_for('pricing'))

# Route for handling plan selection from pricing page
@plans_bp.route('/select_plan/<plan_type>')
def select_plan(plan_type):
    """Handle plan selection from pricing page"""
    if not current_user.is_authenticated:
        # Store intended plan in session for post-login redirect
        session['intended_plan'] = plan_type
        return redirect(url_for('login'))
    
    if plan_type == 'free':
        return redirect(url_for('plans.free_plan'))
    elif plan_type == 'starter':
        return redirect(url_for('plans.starter_plan'))
    elif plan_type == 'pro':
        return redirect(url_for('plans.pro_plan'))
    else:
        flash("Invalid plan selected.", "error")
        return redirect(url_for('pricing'))
