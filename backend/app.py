from datetime import datetime
import os

from flask import Flask, g, jsonify, request, send_file
from flask_cors import CORS

from dotenv import load_dotenv

load_dotenv()

import config as app_config
from ml.model import ModelService
from models import AuditLog, ImageRecord, Prediction, Report, User, db
from services.auth import generate_token, hash_password, require_auth, verify_password
from services.storage import allowed_file, save_upload


def create_app():
    app = Flask(__name__)
    app.config.from_object(app_config)
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    model_service = ModelService(app.config["MODEL_WEIGHTS"], app.config["MODEL_NAME"])

    def resolve_existing_file_path(raw_path):
        if not raw_path:
            return None
        normalized = os.path.normpath(raw_path)
        candidates = []

        def add_candidate(path):
            if path and path not in candidates:
                candidates.append(path)

        if os.path.isabs(normalized):
            add_candidate(normalized)
            backend_name = os.path.basename(os.path.normpath(app_config.BASE_DIR))
            duplicated = f"{os.sep}{backend_name}{os.sep}{backend_name}{os.sep}"
            if duplicated in normalized:
                add_candidate(normalized.replace(duplicated, f"{os.sep}{backend_name}{os.sep}"))
        else:
            add_candidate(os.path.normpath(os.path.join(app_config.BASE_DIR, normalized)))
            add_candidate(os.path.normpath(os.path.join(app_config.PROJECT_ROOT, normalized)))

        parts = normalized.split(os.sep)
        if parts and parts[0].lower() == "backend" and len(parts) > 1:
            stripped = os.path.join(*parts[1:])
            add_candidate(os.path.normpath(os.path.join(app_config.BASE_DIR, stripped)))
            add_candidate(os.path.normpath(os.path.join(app_config.PROJECT_ROOT, stripped)))

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return candidates[0] if candidates else normalized

    def log_action(user_id, action, entity_type, entity_id, detail=None):
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
        db.session.add(entry)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        role = data.get("role", "doctor")
        admin_code = data.get("admin_code", "")

        if not email or not password:
            return jsonify({"error": "email and password required"}), 400
        if role not in {"doctor", "admin"}:
            return jsonify({"error": "invalid role"}), 400
        if role == "admin" and app.config["ADMIN_INVITE_CODE"]:
            if admin_code != app.config["ADMIN_INVITE_CODE"]:
                return jsonify({"error": "invalid admin code"}), 403

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "email already exists"}), 409

        user = User(email=email, password_hash=hash_password(password), role=role)
        db.session.add(user)
        db.session.commit()
        log_action(user.id, "register", "user", user.id, f"role={role}")
        db.session.commit()
        return jsonify({"message": "registered"})

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(password, user.password_hash):
            return jsonify({"error": "invalid credentials"}), 401

        token = generate_token(user)
        log_action(user.id, "login", "user", user.id)
        db.session.commit()
        return jsonify({"token": token, "role": user.role, "user_id": user.id})

    @app.route("/api/users/me", methods=["GET"])
    @require_auth()
    def current_user_info():
        return jsonify({
            "id": g.current_user.id,
            "email": g.current_user.email,
            "role": g.current_user.role,
        })

    @app.route("/api/images/upload", methods=["POST"])
    @require_auth()
    def upload_image():
        if "file" not in request.files:
            return jsonify({"error": "file required"}), 400
        file = request.files["file"]
        if file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "invalid file"}), 400

        filename, path = save_upload(file, app.config["UPLOAD_DIR"])
        image_record = ImageRecord(
            user_id=g.current_user.id,
            filename=filename,
            original_path=path,
        )
        db.session.add(image_record)
        db.session.commit()
        log_action(g.current_user.id, "upload", "image", image_record.id, filename)
        db.session.commit()
        return jsonify({"image_id": image_record.id, "filename": filename})

    @app.route("/api/predict/<int:image_id>", methods=["POST"])
    @require_auth()
    def predict(image_id):
        image_record = ImageRecord.query.get_or_404(image_id)
        if g.current_user.role != "admin" and image_record.user_id != g.current_user.id:
            return jsonify({"error": "forbidden"}), 403

        result = model_service.predict(
            image_record.original_path,
            app.config["PROCESSED_DIR"],
            app.config["HEATMAP_DIR"],
        )
        image_record.processed_path = result["processed_path"]
        prediction = Prediction(
            image_id=image_record.id,
            model_name=app.config["MODEL_NAME"],
            prob_benign=result["prob_benign"],
            prob_malignant=result["prob_malignant"],
            predicted_label=result["predicted_label"],
            heatmap_path=result["heatmap_path"],
        )
        db.session.add(prediction)
        db.session.commit()
        log_action(g.current_user.id, "predict", "prediction", prediction.id)
        db.session.commit()

        return jsonify({
            "prediction_id": prediction.id,
            "label": prediction.predicted_label,
            "prob_benign": prediction.prob_benign,
            "prob_malignant": prediction.prob_malignant,
            "heatmap_url": f"/api/images/{image_record.id}/heatmap",
        })

    @app.route("/api/images/<int:image_id>/original", methods=["GET"])
    @require_auth()
    def get_original(image_id):
        image_record = ImageRecord.query.get_or_404(image_id)
        if g.current_user.role != "admin" and image_record.user_id != g.current_user.id:
            return jsonify({"error": "forbidden"}), 403
        original_path = resolve_existing_file_path(image_record.original_path)
        if not original_path or not os.path.exists(original_path):
            return jsonify({"error": "original image not found"}), 404
        return send_file(original_path)

    @app.route("/api/images/<int:image_id>/heatmap", methods=["GET"])
    @require_auth()
    def get_heatmap(image_id):
        image_record = ImageRecord.query.get_or_404(image_id)
        prediction = Prediction.query.filter_by(image_id=image_id).order_by(Prediction.created_at.desc()).first()
        if not prediction or not prediction.heatmap_path:
            return jsonify({"error": "heatmap not available"}), 404
        if g.current_user.role != "admin" and image_record.user_id != g.current_user.id:
            return jsonify({"error": "forbidden"}), 403
        heatmap_path = resolve_existing_file_path(prediction.heatmap_path)
        if not heatmap_path or not os.path.exists(heatmap_path):
            return jsonify({"error": "heatmap file not found"}), 404
        return send_file(heatmap_path)

    @app.route("/api/history", methods=["GET"])
    @require_auth()
    def history():
        user_id = request.args.get("user_id", type=int)
        prediction_id_raw = (request.args.get("prediction_id") or "").strip()
        start_date = request.args.get("start")
        end_date = request.args.get("end")
        prediction_id = None

        if prediction_id_raw:
            if not prediction_id_raw.isdigit() or int(prediction_id_raw) <= 0:
                return jsonify({"error": "invalid prediction_id"}), 400
            prediction_id = int(prediction_id_raw)

        query = Prediction.query.join(ImageRecord, Prediction.image_id == ImageRecord.id)
        if g.current_user.role != "admin":
            query = query.filter(ImageRecord.user_id == g.current_user.id)
        elif user_id:
            query = query.filter(ImageRecord.user_id == user_id)

        if prediction_id is not None:
            query = query.filter(Prediction.id == prediction_id)

        if start_date:
            query = query.filter(Prediction.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(Prediction.created_at <= datetime.fromisoformat(end_date))

        predictions = query.order_by(Prediction.created_at.desc()).limit(200).all()
        results = []
        for pred in predictions:
            results.append({
                "prediction_id": pred.id,
                "image_id": pred.image_id,
                "label": pred.predicted_label,
                "prob_benign": pred.prob_benign,
                "prob_malignant": pred.prob_malignant,
                "created_at": pred.created_at.isoformat(),
            })
        return jsonify({"items": results})

    @app.route("/api/reports", methods=["POST"])
    @require_auth()
    def create_report():
        data = request.get_json(silent=True) or {}
        prediction_id = data.get("prediction_id")
        content = data.get("content", "").strip()
        if not prediction_id or not content:
            return jsonify({"error": "prediction_id and content required"}), 400

        prediction = Prediction.query.get_or_404(prediction_id)
        image_record = db.session.get(ImageRecord, prediction.image_id)
        if not image_record:
            return jsonify({"error": "image not found"}), 404
        if g.current_user.role != "admin" and image_record.user_id != g.current_user.id:
            return jsonify({"error": "forbidden"}), 403

        report = Report(
            prediction_id=prediction_id,
            content=content,
            created_by=g.current_user.id,
            status="draft",
        )
        db.session.add(report)
        db.session.commit()
        log_action(g.current_user.id, "create_report", "report", report.id)
        db.session.commit()
        return jsonify({"report_id": report.id})

    @app.route("/api/reports", methods=["GET"])
    @require_auth()
    def list_reports():
        prediction_id = request.args.get("prediction_id", type=int)

        query = (
            Report.query
            .join(Prediction, Report.prediction_id == Prediction.id)
            .join(ImageRecord, Prediction.image_id == ImageRecord.id)
        )
        if g.current_user.role != "admin":
            query = query.filter(ImageRecord.user_id == g.current_user.id)
        if prediction_id:
            query = query.filter(Report.prediction_id == prediction_id)

        reports = query.order_by(Report.created_at.desc()).limit(200).all()
        items = []
        for report in reports:
            items.append({
                "report_id": report.id,
                "prediction_id": report.prediction_id,
                "content": report.content,
                "status": report.status,
                "created_by": report.created_by,
                "reviewed_by": report.reviewed_by,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
            })
        return jsonify({"items": items})

    @app.route("/api/reports/<int:report_id>/review", methods=["POST"])
    @require_auth(role="admin")
    def review_report(report_id):
        data = request.get_json(silent=True) or {}
        status = (data.get("status", "approved") or "").strip().lower()
        if status not in {"approved", "rejected"}:
            return jsonify({"error": "invalid review status"}), 400

        report = Report.query.get_or_404(report_id)
        report.status = status
        report.reviewed_by = g.current_user.id
        report.reviewed_at = datetime.utcnow()
        db.session.commit()
        log_action(g.current_user.id, "review_report", "report", report.id, status)
        db.session.commit()
        return jsonify({
            "message": "updated",
            "report_id": report.id,
            "status": report.status,
            "reviewed_by": report.reviewed_by,
            "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        })

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
