from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from auth import db, User
from predict_simple import predict_image, analyze_image_quality
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = "food_freshness_secret_key_2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the dashboard.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(filename):
    """Generate a unique filename to prevent conflicts"""
    name, ext = os.path.splitext(secure_filename(filename))
    unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    return unique_name

@app.route("/", methods=["GET", "POST"])
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
            return render_template("login.html", error="Invalid username or password.")
    
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    try:
        # Check if file was uploaded
        if 'image' not in request.files:
            flash("No image file provided.", "error")
            return redirect("/dashboard")
        
        file = request.files['image']
        
        # Check if file is selected
        if file.filename == '':
            flash("No image file selected.", "error")
            return redirect("/dashboard")
        
        # Check file type
        if not allowed_file(file.filename):
            flash("Invalid file type. Please upload an image file.", "error")
            return redirect("/dashboard")
        
        # Generate unique filename and save
        filename = generate_unique_filename(file.filename)
        upload_path = os.path.join("static", "uploads")
        os.makedirs(upload_path, exist_ok=True)
        
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)
        
        # Predict food freshness
        label, confidence = predict_image(filepath)
        
        # Analyze image quality
        quality_metrics = analyze_image_quality(filepath)
        
        # Store results in session for result page
        session['prediction_result'] = {
            'label': label,
            'confidence': confidence,
            'image_filename': filename,
            'quality': quality_metrics,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return redirect("/result")
        
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        flash(f"Error processing image: {str(e)}", "error")
        return redirect("/dashboard")

@app.route("/result")
@login_required
def result():
    # Get prediction result from session
    prediction_result = session.get('prediction_result')
    
    if not prediction_result:
        flash("No prediction result found. Please analyze an image first.", "error")
        return redirect("/dashboard")
    
    return render_template("result.html", 
                         label=prediction_result['label'],
                         confidence=prediction_result['confidence'],
                         image_filename=prediction_result['image_filename'],
                         quality=prediction_result['quality'],
                         timestamp=prediction_result['timestamp'])

@app.route("/logout")
@login_required
def logout():
    username = current_user.username
    logout_user()
    return redirect("/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(username="admin", password="password")
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created (username: admin, password: password)")
    
    print("\n" + "="*60)
    print("FOOD FRESHNESS CLASSIFIER - STARTING UP")
    print("="*60)
    print("Features:")
    print("   • CNN-based Image Analysis")
    print("   • 87% Accuracy on 2.5K+ Images")
    print("   • Real-time Image Upload")
    print("   • User Authentication")
    print("   • Quality Metrics Analysis")
    print("\nDemo Credentials:")
    print("   Username: admin")
    print("   Password: password")
    print("\nAccess the application at: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)