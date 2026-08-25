import os
import sys

print("=" * 60)
print("Food Freshness Classifier - System Check")
print("=" * 60)
print()

# Check Python version
print("✓ Checking Python version...")
print(f"  Python {sys.version}")
print()

# Check required files
print("✓ Checking required files...")
required_files = [
    'app.py',
    'auth.py',
    'predict.py',
    'camera.py',
    'pdf_generator.py',
    'email_sender.py',
    'requirements.txt',
    'templates/login.html',
    'templates/dashboard.html',
    'templates/result.html',
    'templates/batch_results.html',
    'templates/analytics.html',
    'templates/profile.html'
]

missing_files = []
for file in required_files:
    if os.path.exists(file):
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} - MISSING!")
        missing_files.append(file)
print()

# Check required directories
print("✓ Checking required directories...")
required_dirs = [
    'static',
    'static/uploads',
    'static/reports',
    'static/profiles',
    'templates',
    'instance'
]

missing_dirs = []
for directory in required_dirs:
    if os.path.exists(directory):
        print(f"  ✓ {directory}/")
    else:
        print(f"  ✗ {directory}/ - MISSING! Creating...")
        os.makedirs(directory, exist_ok=True)
        missing_dirs.append(directory)
print()

# Check database
print("✓ Checking database...")
if os.path.exists('instance/users.db'):
    print("  ✓ Database exists")
else:
    print("  ✗ Database not found!")
    print("  → Run: python init_db.py")
print()

# Check dependencies
print("✓ Checking dependencies...")
try:
    import flask
    print(f"  ✓ Flask {flask.__version__}")
except ImportError:
    print("  ✗ Flask not installed!")

try:
    import flask_login
    print("  ✓ Flask-Login installed")
except ImportError:
    print("  ✗ Flask-Login not installed!")

try:
    import flask_sqlalchemy
    print("  ✓ Flask-SQLAlchemy installed")
except ImportError:
    print("  ✗ Flask-SQLAlchemy not installed!")

try:
    import cv2
    print(f"  ✓ OpenCV {cv2.__version__}")
except ImportError:
    print("  ✗ OpenCV not installed!")

try:
    import PIL
    print(f"  ✓ Pillow {PIL.__version__}")
except ImportError:
    print("  ✗ Pillow not installed!")

try:
    import numpy
    print(f"  ✓ NumPy {numpy.__version__}")
except ImportError:
    print("  ✗ NumPy not installed!")

try:
    from reportlab.pdfgen import canvas
    print("  ✓ ReportLab installed")
except ImportError:
    print("  ✗ ReportLab not installed!")

print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)

if missing_files:
    print(f"✗ Missing {len(missing_files)} required file(s)")
    for f in missing_files:
        print(f"  - {f}")
else:
    print("✓ All required files present")

if missing_dirs:
    print(f"✓ Created {len(missing_dirs)} missing director(ies)")
else:
    print("✓ All required directories present")

print()
print("To install missing dependencies, run:")
print("  pip install -r requirements.txt")
print()
print("To initialize the database, run:")
print("  python init_db.py")
print()
print("To start the application, run:")
print("  python app.py")
print("  OR double-click START_APP.bat")
print()
print("=" * 60)
