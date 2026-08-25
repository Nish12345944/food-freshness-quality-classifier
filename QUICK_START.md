# 🚀 QUICK START GUIDE

## Get Started in 3 Steps

### Step 1: Start the Application (30 seconds)

**Option A: Double-click the batch file**
```
START_APP.bat
```

**Option B: Run from command line**
```bash
python app.py
```

Wait for this message:
```
* Running on http://0.0.0.0:5001
```

---

### Step 2: Login (10 seconds)

1. Open browser: **http://localhost:5001**
2. Enter credentials:
   - Username: `admin`
   - Password: `password`
3. Click **"Login to Dashboard"**

---

### Step 3: Start Analyzing! (1 minute)

You now have 3 ways to analyze food:

#### Method 1: Upload Images 📤
1. Click the upload area or drag images
2. Select 1-10 food images
3. Click **"Analyze Food Freshness"**
4. View results!

#### Method 2: Camera Capture 📷
1. Click **"Camera Capture"** in Quick Actions
2. Allow camera permissions
3. Position food in frame
4. Click **"Capture Photo"**
5. View results!

#### Method 3: Batch Upload 📁
1. Select multiple images (up to 10)
2. Preview all selected images
3. Click **"Analyze Food Freshness"**
4. View batch results!

---

## What You Can Do

### ✅ Analyze Food Freshness
- Upload images of any food
- Get instant classification (Fresh/Okay/Avoid)
- See confidence percentage
- Get food category (8 types)

### ✅ Use Camera
- Live camera preview
- Instant capture and analysis
- Works on desktop and mobile

### ✅ View Analytics
- Total analyses count
- Fresh/Okay/Avoid distribution
- 30-day trend chart
- Food type breakdown

### ✅ Manage Profile
- Update email
- Upload profile picture
- View analysis history

---

## Food Categories Detected

The system can identify **8 different food categories**:

1. **🍎 Fruit** - Apple, banana, orange, mango...
2. **🥕 Vegetable** - Carrot, lettuce, broccoli...
3. **🥩 Meat** - Chicken, beef, pork, fish...
4. **🥛 Dairy** - Milk, cheese, paneer, yogurt...
5. **🍛 Cooked Food** - Curry, sabji, rice, pasta...
6. **🍞 Bread** - Bread, roti, naan, toast...
7. **🦐 Seafood** - Fish, shrimp, crab, prawns...
8. **🥚 Eggs** - Egg, omelette, boiled egg...

Each category has specific storage recommendations!

---

## Understanding Results

### Fresh ✅
- **Score:** 60-100 (65-100 for cooked food)
- **Meaning:** Safe to eat, optimal quality
- **Action:** Consume normally

### Okay ⚠️
- **Score:** 35-59 (40-64 for cooked food)
- **Meaning:** Acceptable quality, consume soon
- **Action:** Eat within 1-2 days

### Avoid ❌
- **Score:** 0-34 (0-39 for cooked food)
- **Meaning:** Poor quality, not recommended
- **Action:** Discard the food

---

## Tips for Best Results

### 📸 Image Quality
- ✅ Good lighting (natural light is best)
- ✅ Clear focus (not blurry)
- ✅ Close-up shot (fill the frame)
- ✅ Show the food clearly
- ❌ Avoid dark/shadowy images
- ❌ Avoid extreme angles

### 🎯 What to Photograph
- ✅ The actual food item
- ✅ Areas showing spoilage (if any)
- ✅ Overall appearance
- ❌ Empty plates
- ❌ Packaging only

### 📱 Camera Tips
- ✅ Hold steady
- ✅ Good lighting
- ✅ Position food in center
- ✅ Wait for focus

---

## Navigation Guide

### Main Menu (Top Right)
- **Profile** - View and edit your profile
- **Analytics** - See statistics and charts
- **Logout** - Sign out of the app

### Quick Actions (Right Sidebar)
- **Camera Capture** - Take photo with camera
- **View Analytics** - Jump to analytics page
- **Analysis History** - See past results
- **Profile Settings** - Manage account

### Recent Analyses (Bottom)
- Click any card to view full details
- Color-coded by result (Green/Orange/Red)
- Shows confidence and food type

---

## Keyboard Shortcuts

- **Ctrl + Click** - Select multiple files
- **Drag & Drop** - Upload images
- **Esc** - Close camera modal
- **F5** - Refresh page

---

## Common Questions

### Q: How many images can I upload at once?
**A:** Up to 10 images in batch mode.

### Q: What image formats are supported?
**A:** JPG, JPEG, PNG, WEBP, GIF, BMP

### Q: Does the camera work on mobile?
**A:** Yes! Works on iOS 11+ and Android 5+

### Q: How accurate is the prediction?
**A:** ~85% accuracy for most food types

### Q: Can I analyze cooked food?
**A:** Yes! The system has a dedicated cooked food category

### Q: What if the prediction is wrong?
**A:** Try a clearer image with better lighting

### Q: How long does analysis take?
**A:** 2-5 seconds per image

### Q: Is my data saved?
**A:** Yes, in your local database (instance/users.db)

---

## Troubleshooting

### Camera not working?
1. Check browser permissions (click lock icon)
2. Close other apps using camera
3. Try different browser (Chrome recommended)
4. Refresh page and try again

### Upload not working?
1. Check file format (JPG, PNG, etc.)
2. Check file size (under 50MB)
3. Try different image
4. Refresh page

### Wrong prediction?
1. Ensure image is clear and well-lit
2. Try closer shot of food
3. Make sure spoilage is visible
4. Check if food is in focus

---

## Next Steps

### After Your First Analysis
1. ✅ Check the result page
2. ✅ Read storage recommendations
3. ✅ Download PDF report (optional)
4. ✅ Try camera capture
5. ✅ Upload more images
6. ✅ View analytics

### Explore Features
1. **Analytics** - See your statistics
2. **Profile** - Customize your account
3. **Batch Upload** - Analyze multiple items
4. **Camera** - Try live capture
5. **History** - Review past analyses

---

## Documentation

### Available Guides
- **README.md** - Full project documentation
- **COMPLETE_SUMMARY.md** - All changes summary
- **UPDATES_V2.md** - Detailed feature docs
- **TESTING_GUIDE.md** - Testing instructions
- **TROUBLESHOOTING.md** - Common issues
- **VISUAL_COMPARISON.md** - Before/after visuals

---

## Support

### Need Help?
1. Check **TROUBLESHOOTING.md**
2. Check browser console (F12)
3. Check terminal for errors
4. Review documentation

### Report Issues
- Check if all files are present
- Verify dependencies installed
- Check Python version (3.8+)
- Review error messages

---

## Success Checklist

After starting, verify:
- [ ] Dashboard loads with modern UI
- [ ] Upload area is visible
- [ ] Camera button is clickable
- [ ] Navigation buttons work
- [ ] Can upload images
- [ ] Can capture with camera
- [ ] Results display correctly
- [ ] Analytics page works
- [ ] Profile page works

If all checked ✅ - You're ready to go!

---

## Quick Commands

```bash
# Start app
python app.py

# Check setup
python check_setup.py

# Initialize database
python init_db.py

# Install dependencies
pip install -r requirements.txt
```

---

## Default Credentials

```
Username: admin
Password: password
```

**⚠️ Change these in production!**

---

## That's It! 🎉

You're now ready to use the Food Freshness Classifier!

**Start analyzing food and preventing waste!**

---

**Quick Links:**
- Dashboard: http://localhost:5001/dashboard
- Analytics: http://localhost:5001/analytics
- Profile: http://localhost:5001/profile

**Happy Analyzing! 🍎🥕🍞**
