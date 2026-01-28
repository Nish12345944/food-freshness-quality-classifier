from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from auth import db, User, Analysis
from predict import predict_image, analyze_image_quality, get_storage_tips
from camera import capture_image, check_camera_availability
from pdf_generator import generate_pdf_report
from email_sender import send_email_report, generate_email_body
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'food_freshness_secret_key_2024')
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(filename):
    name, ext = os.path.splitext(secure_filename(filename))
    return f"{name}_{uuid.uuid4().hex[:8]}{ext}"

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/demo")
def demo():
    return render_template("demo.html")

@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            return render_template("login.html", error="Please enter both username and password.")
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect("/dashboard")
        else:
            return render_template("auth.html", error="Invalid username or password.", is_register=False)
    
    return render_template("auth.html", is_register=False)

@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if User.query.filter_by(username=username).first():
            return render_template("auth.html", error="Username already exists.", is_register=True)
        
        if User.query.filter_by(email=email).first():
            return render_template("auth.html", error="Email already registered.", is_register=True)
        
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        return render_template("auth.html", success="Registration successful! Please login.", is_register=False)
    
    return render_template("auth.html", is_register=True)

@app.route("/dashboard")
@login_required
def dashboard():
    camera_available = check_camera_availability()
    recent_analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.timestamp.desc()).limit(5).all()
    return render_template("dashboard.html", camera_available=camera_available, recent_analyses=recent_analyses)

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    try:
        files = request.files.getlist('images')
        
        if not files or files[0].filename == '':
            flash("No image file selected.", "error")
            return redirect("/dashboard")
        
        results = []
        upload_path = os.path.join("static", "uploads")
        os.makedirs(upload_path, exist_ok=True)
        
        for file in files[:10]:
            if file and allowed_file(file.filename):
                filename = generate_unique_filename(file.filename)
                filepath = os.path.join(upload_path, filename)
                file.save(filepath)
                
                label, confidence, food_type = predict_image(filepath)
                quality_metrics = analyze_image_quality(filepath)
                
                analysis = Analysis(
                    user_id=current_user.id,
                    image_filename=filename,
                    label=label,
                    confidence=confidence,
                    food_type=food_type,
                    quality_score=quality_metrics.get('blur_score', 0),
                    resolution=quality_metrics.get('resolution', 'Unknown'),
                    blur_score=quality_metrics.get('blur_score', 0)
                )
                db.session.add(analysis)
                
                results.append({
                    'id': None,
                    'filename': filename,
                    'label': label,
                    'confidence': confidence,
                    'food_type': food_type,
                    'quality': quality_metrics
                })
        
        db.session.commit()
        
        for i, result in enumerate(results):
            result['id'] = Analysis.query.filter_by(
                user_id=current_user.id,
                image_filename=result['filename']
            ).first().id
        
        session['batch_results'] = results
        return redirect("/batch-results")
        
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        flash(f"Error processing images: {str(e)}", "error")
        return redirect("/dashboard")

@app.route("/batch-results")
@login_required
def batch_results():
    results = session.get('batch_results', [])
    if not results:
        flash("No results found.", "error")
        return redirect("/dashboard")
    return render_template("batch_results.html", results=results)

@app.route("/result/<int:analysis_id>")
@login_required
def result(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != current_user.id:
        flash("Unauthorized access.", "error")
        return redirect("/dashboard")
    
    storage_tips = get_storage_tips(analysis.food_type)
    
    return render_template("result.html",
                         analysis=analysis,
                         storage_tips=storage_tips)

@app.route("/analytics")
@login_required
def analytics():
    analyses = Analysis.query.filter_by(user_id=current_user.id).all()
    
    total = len(analyses)
    fresh = len([a for a in analyses if a.label == 'Fresh'])
    okay = len([a for a in analyses if a.label == 'Okay'])
    avoid = len([a for a in analyses if a.label == 'Avoid'])
    
    last_30_days = datetime.now() - timedelta(days=30)
    recent = Analysis.query.filter(
        Analysis.user_id == current_user.id,
        Analysis.timestamp >= last_30_days
    ).all()
    
    daily_stats = {}
    for analysis in recent:
        date_key = analysis.timestamp.strftime('%Y-%m-%d')
        if date_key not in daily_stats:
            daily_stats[date_key] = {'Fresh': 0, 'Okay': 0, 'Avoid': 0}
        daily_stats[date_key][analysis.label] += 1
    
    food_type_stats = {}
    for analysis in analyses:
        food_type = analysis.food_type or 'unknown'
        if food_type not in food_type_stats:
            food_type_stats[food_type] = 0
        food_type_stats[food_type] += 1
    
    return render_template("analytics.html",
                         total=total,
                         fresh=fresh,
                         okay=okay,
                         avoid=avoid,
                         daily_stats=json.dumps(daily_stats),
                         food_type_stats=json.dumps(food_type_stats))

@app.route("/profile")
@login_required
def profile():
    total_analyses = Analysis.query.filter_by(user_id=current_user.id).count()
    return render_template("profile.html", total_analyses=total_analyses)

@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    try:
        email = request.form.get("email")
        if email:
            current_user.email = email
        
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1]}"
                filepath = os.path.join("static", "profiles", filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                current_user.profile_picture = filename
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating profile: {str(e)}", "error")
    
    return redirect("/profile")

@app.route("/download-pdf/<int:analysis_id>")
@login_required
def download_pdf(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != current_user.id:
        flash("Unauthorized access.", "error")
        return redirect("/dashboard")
    
    storage_tips = get_storage_tips(analysis.food_type)
    
    analysis_data = {
        'id': analysis.id,
        'timestamp': analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'label': analysis.label,
        'confidence': analysis.confidence,
        'food_type': analysis.food_type,
        'quality': {
            'quality': 'Good' if analysis.blur_score > 100 else 'Fair',
            'resolution': analysis.resolution,
            'blur_score': analysis.blur_score
        },
        'image_path': os.path.join('static', 'uploads', analysis.image_filename),
        'storage_tips': storage_tips
    }
    
    pdf_path = os.path.join('static', 'reports', f'report_{analysis.id}.pdf')
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    if generate_pdf_report(analysis_data, pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=f'analysis_report_{analysis.id}.pdf')
    else:
        flash("Error generating PDF report.", "error")
        return redirect(f"/result/{analysis_id}")

@app.route("/email-report/<int:analysis_id>", methods=["POST"])
@login_required
def email_report(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    recipient_email = request.form.get('email') or current_user.email
    
    if not recipient_email:
        return jsonify({'success': False, 'error': 'No email provided'}), 400
    
    storage_tips = get_storage_tips(analysis.food_type)
    
    analysis_data = {
        'id': analysis.id,
        'timestamp': analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'label': analysis.label,
        'confidence': analysis.confidence,
        'food_type': analysis.food_type,
        'quality': {
            'quality': 'Good' if analysis.blur_score > 100 else 'Fair',
            'resolution': analysis.resolution
        },
        'image_path': os.path.join('static', 'uploads', analysis.image_filename),
        'storage_tips': storage_tips
    }
    
    pdf_path = os.path.join('static', 'reports', f'report_{analysis.id}.pdf')
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    generate_pdf_report(analysis_data, pdf_path)
    
    subject = f"Food Freshness Analysis Report - {analysis.label}"
    body = generate_email_body(analysis_data)
    
    if send_email_report(recipient_email, subject, body, pdf_path):
        return jsonify({'success': True, 'message': 'Email sent successfully!'})
    else:
        return jsonify({'success': False, 'error': 'Failed to send email'}), 500

@app.route("/api/history")
@login_required
def api_history():
    analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.timestamp.desc()).limit(20).all()
    return jsonify([{
        'id': a.id,
        'label': a.label,
        'confidence': round(a.confidence, 2),
        'food_type': a.food_type,
        'timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M')
    } for a in analyses])

@app.route("/capture-camera", methods=["POST"])
@login_required
def capture_camera():
    try:
        # Check if image is from browser camera
        if 'camera_image' in request.files:
            file = request.files['camera_image']
            if file:
                upload_path = os.path.join("static", "uploads")
                os.makedirs(upload_path, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"camera_{timestamp}.jpg"
                filepath = os.path.join(upload_path, filename)
                file.save(filepath)
        else:
            # Fallback to OpenCV camera capture
            from camera import capture_image
            upload_path = os.path.join("static", "uploads")
            os.makedirs(upload_path, exist_ok=True)
            filepath, filename = capture_image(upload_path)
        
        label, confidence, food_type = predict_image(filepath)
        quality_metrics = analyze_image_quality(filepath)
        
        analysis = Analysis(
            user_id=current_user.id,
            image_filename=filename,
            label=label,
            confidence=confidence,
            food_type=food_type,
            quality_score=quality_metrics.get('blur_score', 0),
            resolution=quality_metrics.get('resolution', 'Unknown'),
            blur_score=quality_metrics.get('blur_score', 0)
        )
        db.session.add(analysis)
        db.session.commit()
        
        return redirect(f"/result/{analysis.id}")
        
    except Exception as e:
        print(f"Camera capture error: {str(e)}")
        flash(f"Camera error: {str(e)}", "error")
        return redirect("/dashboard")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

# Initialize database
with app.app_context():
    db.create_all()
    
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", email="admin@example.com", password="password")
        db.session.add(admin)
        db.session.commit()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
