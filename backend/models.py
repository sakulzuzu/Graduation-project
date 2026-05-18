from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="doctor")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ImageRecord(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_path = db.Column(db.String(512), nullable=False)
    processed_path = db.Column(db.String(512))
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=False, index=True)
    model_name = db.Column(db.String(64), nullable=False)
    prob_benign = db.Column(db.Float, nullable=False)
    prob_malignant = db.Column(db.Float, nullable=False)
    predicted_label = db.Column(db.String(32), nullable=False)
    heatmap_path = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(64), nullable=False)
    entity_type = db.Column(db.String(64), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    detail = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
