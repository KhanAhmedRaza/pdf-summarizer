from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta

# Import db from your existing setup
# This assumes you have a db.py or similar that initializes SQLAlchemy
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    name = db.Column(db.String(100))
    profile_pic = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Plan information
    plan_type = db.Column(db.String(20), default="free")  # free, starter, pro
    plan_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    plan_end_date = db.Column(db.DateTime)
    
    # Relationships to usage tracking models
    monthly_usage = db.relationship('MonthlyUsage', backref='user', lazy=True)
    uploads = db.relationship('Upload', backref='user', lazy=True)
    
    def get_current_monthly_usage(self):
        """Get or create the current month's usage record"""
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Import here to avoid circular imports
        from models.usage import MonthlyUsage
        
        usage = MonthlyUsage.query.filter_by(
            user_id=self.id,
            month_start=current_month
        ).first()
        
        if not usage:
            # Create new monthly usage record
            next_month = (current_month + timedelta(days=32)).replace(day=1)
            usage = MonthlyUsage(
                user_id=self.id,
                month_start=current_month,
                month_end=next_month - timedelta(seconds=1),
                pdf_count=0,
                token_count=0
            )
            db.session.add(usage)
            db.session.commit()
            
        return usage
    
    def can_upload_pdf(self):
        """Check if user can upload more PDFs this month based on plan limits"""
        usage = self.get_current_monthly_usage()
        
        if self.plan_type == "free" and usage.pdf_count >= 5:
            return False
        elif self.plan_type == "starter" and usage.pdf_count >= 50:
            return False
        elif self.plan_type == "pro" and usage.pdf_count >= 100:
            return False
            
        return True
    
    def get_max_pages_per_file(self):
        """Get maximum pages allowed per file based on plan"""
        if self.plan_type == "free":
            return 20
        elif self.plan_type == "starter":
            return 20
        elif self.plan_type == "pro":
            return 30
        return 20  # Default fallback
    
    def get_ai_model(self):
        """Get AI model to use based on plan"""
        if self.plan_type == "free":
            return "gpt-3.5-turbo"
        else:
            return "gpt-4"
    
    def has_priority_processing(self):
        """Check if user has priority processing"""
        return self.plan_type == "pro"
    
    def can_access_feature(self, feature):
        """Check if user can access a specific feature based on plan"""
        # Feature access mapping
        feature_access = {
            # Document types
            "academic": ["free", "starter", "pro"],
            "business": ["free", "starter", "pro"],
            "legal": ["starter", "pro"],
            "healthcare": ["pro"],
            "finance": ["pro"],
            "tech": ["pro"],
            
            # Summary formats
            "plain_text": ["free", "starter", "pro"],
            "interactive": ["starter", "pro"],
            "todo_list": ["starter", "pro"],
            "visual": ["pro"],
            "flowchart": ["pro"],
            
            # Other features
            "community_access": ["pro"],
            "priority_support": ["starter", "pro"]
        }
        
        if feature in feature_access:
            return self.plan_type in feature_access[feature]
        
        return False
