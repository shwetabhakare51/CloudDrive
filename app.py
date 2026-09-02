from flask import Flask, render_template, request, redirect, session
import boto3
import mimetypes
import webbrowser
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-dev-key')

# AWS S3 setup
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

BUCKET = os.getenv('S3_BUCKET_NAME')


# 🔐 LOGIN
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == os.getenv('APP_USERNAME') and password == os.getenv('APP_PASSWORD'):
            session['user'] = username
            return redirect('/dashboard')
        else:
            error = "Invalid credentials ❌"

    return render_template('login.html', error=error)


# 🚪 LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# ☁️ DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    objects = s3.list_objects_v2(Bucket=BUCKET)

    files = []
    for obj in objects.get('Contents', []):
        files.append({
            'key': obj['Key']
        })

    return render_template('dashboard.html', files=files)


# 🔗 SHORT LINK ROUTE (IMPORTANT FEATURE)
@app.route('/file/<filename>')
def serve_file(filename):
    if 'user' not in session:
        return redirect('/')

    url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': BUCKET,
            'Key': filename,
            'ResponseContentDisposition': 'inline'
        },
        ExpiresIn=3600   # 1 hour
    )

    return redirect(url)


# 📤 UPLOAD
@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return redirect('/')

    file = request.files['file']

    if file and file.filename != "":
        content_type = mimetypes.guess_type(file.filename)[0]

        s3.upload_fileobj(
            file,
            BUCKET,
            file.filename,
            ExtraArgs={
                "ContentType": content_type or "application/octet-stream"
            }
        )

    return redirect('/dashboard')


# ❌ DELETE
@app.route('/delete/<filename>')
def delete(filename):
    if 'user' not in session:
        return redirect('/')

    s3.delete_object(Bucket=BUCKET, Key=filename)
    return redirect('/dashboard')


if __name__ == '__main__':
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)