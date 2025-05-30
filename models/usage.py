from datetime import datetime
# In models/user.py and models/usage.py
from extensions import db


class MonthlyUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month_start = db.Column(db.DateTime, nullable=False)
    month_end = db.Column(db.DateTime, nullable=False)
    pdf_count = db.Column(db.Integer, default=0)
    token_count = db.Column(db.Integer, default=0)
    
    def increment_pdf_count(self):
        """Increment PDF count for the month"""
        self.pdf_count += 1
        db.session.commit()
    
    def add_token_usage(self, tokens):
        """Add token usage"""
        self.token_count += tokens
        db.session.commit()
    
    def get_daily_token_usage(self, date=None):
        """Get token usage for a specific day"""
        if date is None:
            date = datetime.utcnow().date()
        
        # Get all uploads for this day
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        uploads = Upload.query.filter(
            Upload.user_id == self.user_id,
            Upload.upload_date >= start_of_day,
            Upload.upload_date <= end_of_day
        ).all()
        
        return sum(upload.token_count for upload in uploads)


class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    token_count = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    document_type = db.Column(db.String(50))  # academic, business, legal, healthcare, finance, tech
    summary_format = db.Column(db.String(50))  # plain_text, interactive, todo_list, visual, flowchart
