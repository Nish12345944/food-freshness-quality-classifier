# 🍎 Food Freshness Classifier

An AI-powered web application that uses Convolutional Neural Networks (CNN) to classify food freshness and quality in real-time. Built with Flask and TensorFlow/Keras.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.0+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Features

- **AI-Powered Analysis**: CNN-based model with 87% accuracy trained on 2.5K+ images
- **Batch Processing**: Upload and analyze multiple images simultaneously
- **Real-time Webcam Capture**: Capture and analyze food directly from your camera
- **User Authentication**: Secure login/registration system with user profiles
- **Analysis History**: Track all previous food analyses with detailed records
- **Advanced Analytics**: Visual charts and statistics dashboard
- **Storage Recommendations**: Get personalized storage tips based on food type
- **Export Options**: Download PDF reports and email results
- **Responsive Design**: Modern glassmorphism UI with dark mode support

## 🎯 Classification Categories

- **Fresh**: Safe to consume, optimal quality
- **Okay**: Acceptable quality, consume soon
- **Avoid**: Poor quality, not recommended

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Webcam (optional, for camera capture feature)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/food-freshness-classifier.git
cd food-freshness-classifier
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Initialize the database**
```bash
python init_db.py
```

4. **Run the application**
```bash
python app.py
```

5. **Access the application**
```
Open your browser and navigate to: http://localhost:5000
```

### Default Credentials
```
Username: admin
Password: password
```

## 📁 Project Structure

```
food_freshness_classifier/
├── app.py                  # Main Flask application
├── auth.py                 # Authentication & database models
├── predict.py              # ML prediction logic
├── model.py                # CNN model architecture
├── camera.py               # Webcam capture functionality
├── pdf_generator.py        # PDF report generation
├── email_sender.py         # Email functionality
├── templates/              # HTML templates
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── result.html
│   ├── batch_results.html
│   ├── analytics.html
│   └── profile.html
├── static/                 # Static files
│   ├── uploads/           # Uploaded images
│   └── reports/           # Generated PDF reports
├── instance/              # Database files
│   └── users.db
└── requirements.txt       # Python dependencies
```

## 🛠️ Technologies Used

### Backend
- **Flask**: Web framework
- **Flask-Login**: User session management
- **Flask-SQLAlchemy**: Database ORM
- **TensorFlow/Keras**: Deep learning model
- **OpenCV**: Image processing
- **Pillow**: Image manipulation
- **ReportLab**: PDF generation

### Frontend
- **HTML5/CSS3**: Structure and styling
- **JavaScript**: Interactive functionality
- **Font Awesome**: Icons
- **Chart.js**: Analytics visualizations

### Database
- **SQLite**: Lightweight database for user data and analysis history

## 📊 Model Details

- **Architecture**: Convolutional Neural Network (CNN)
- **Training Dataset**: 2,500+ labeled food images
- **Accuracy**: 87%
- **Classes**: 3 (Fresh, Okay, Avoid)
- **Input Size**: 224x224 RGB images
- **Framework**: TensorFlow/Keras

## 🎨 Key Features Explained

### 1. Batch Upload
Upload up to 10 images at once for simultaneous analysis. Results are displayed in a grid view with individual confidence scores.

### 2. Analytics Dashboard
- Total analyses count
- Fresh/Okay/Avoid distribution
- 30-day trend analysis
- Food type statistics
- Interactive charts

### 3. Storage Tips
Personalized recommendations including:
- Optimal temperature
- Humidity levels
- Expected shelf life
- Storage best practices

### 4. Quality Metrics
- Image resolution analysis
- Blur/sharpness detection
- Quality scoring

## 📸 Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Analysis Result
![Result](screenshots/result.png)

### Analytics
![Analytics](screenshots/analytics.png)

## 🔧 Configuration

### Email Setup (Optional)
To enable email reports, configure SMTP settings in `email_sender.py`:
```python
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@gmail.com"
SENDER_PASSWORD = "your-app-password"
```

### Model Training
To retrain the model with your own dataset:
```bash
python model.py
```

## 🐛 Troubleshooting

**Issue**: Camera not working
- **Solution**: Grant browser camera permissions and ensure no other application is using the camera

**Issue**: Model prediction errors
- **Solution**: Ensure image format is supported (JPG, PNG, JPEG, WEBP)

**Issue**: Database errors
- **Solution**: Delete `instance/users.db` and run `python init_db.py` again

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Future Enhancements

- [ ] Real-time freshness tracking with expiry alerts
- [ ] Multi-user household management
- [ ] Nutritional analysis & recipe suggestions
- [ ] Mobile app with barcode scanner
- [ ] IoT integration with smart fridges
- [ ] Multi-language support
- [ ] Cloud deployment (AWS/Azure)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/yourprofile)
- Email: your.email@example.com

## 🙏 Acknowledgments

- Dataset: [Kaggle Food Freshness Dataset](https://www.kaggle.com/)
- Icons: [Font Awesome](https://fontawesome.com/)
- Inspiration: Food waste reduction initiatives

## 📞 Support

For support, email your.email@example.com or open an issue in the GitHub repository.

---

⭐ **Star this repository if you find it helpful!**
