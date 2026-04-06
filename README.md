📦 Installation Guide

Follow these steps to set up the environment and install all required dependencies for the Smart Voting System with Face Recognition.

🐍 **1. Install Python**

Download Python (recommended: 3.10)

**Verify installation:**

python --version

**📁 2. Clone or Download the Project**

git clone <your-repository-link>

cd Smart-Voting-System-main

**🧪 3. Create Virtual Environment**

python -m venv voting_env

Activate environment:

▶️ Windows

voting_env\Scripts\activate

▶️ Mac/Linux

source voting_env/bin/activate

**⬆️ 4. Upgrade pip**

pip install --upgrade pip

**📚 5. Install Required Libraries**

🔹 Step 5.1: Install Basic Dependencies

pip install Flask==3.1.0 numpy==1.23.5 pandas==2.2.2 Pillow==9.5.0 reportlab==4.4.1 opencv-python==4.9.0.80

⚠️ Step 5.2: Install dlib (Important)

Installing dlib directly via pip may fail on Windows. Use the precompiled wheel method:

👉 Download:

Go to:
https://huggingface.co/hanamizuki-ai/pypi-wheels/blob/main/dlib/dlib-19.24.1-cp310-cp310-win_amd64.whl.metadata

Download:

dlib-19.24.2-cp310-cp310-win_amd64.whl

👉 Install:
Place the downloaded file in your project folder, then run:

pip install dlib-19.24.2-cp310-cp310-win_amd64.whl

🤖 Step 5.3: Install face_recognition

pip install face_recognition==1.3.0

**✅ 6. Verify Installation**

python -c "import cv2, dlib, face_recognition, numpy; print('All libraries installed successfully!')"

**🚀 7. Run the Application**

python app.py

Open in browser:

http://127.0.0.1:5000/

**📝 8. (Optional) requirements.txt**

You can also install all dependencies using:

pip install -r requirements.txt

Example requirements.txt:

Flask==3.1.0
numpy==1.23.5
pandas==2.2.2
Pillow==9.5.0
reportlab==4.4.1
opencv-python==4.9.0.80
face_recognition==1.3.0

**⚠️ Note:** dlib should still be installed manually using the .whl file.

❗ Common Issues

🔸 dlib installation error

Do NOT install using pip install dlib

Always use precompiled .whl file

🔸 No module named cv2

pip install opencv-python

🔸 Camera / face recognition errors

Ensure OpenCV is installed
