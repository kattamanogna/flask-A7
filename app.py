from flask import Flask, request, render_template, redirect
import boto3
import os

app = Flask(__name__)

# AWS S3 Setup
s3 = boto3.client('s3', region_name='ap-south-1')

# Bucket Names
INPUT_BUCKET = 'lambda-image-input-bucket'
OUTPUT_BUCKET = 'lambda-image-output-bucket'

# File type check
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    selected_filter = request.form.get('filter')

    if file and selected_filter and allowed_file(file.filename):
        try:
            s3.upload_fileobj(
                file,
                INPUT_BUCKET,
                file.filename,
                ExtraArgs={'Metadata': {'filter': selected_filter}}
            )

            image_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': INPUT_BUCKET, 'Key': file.filename},
                ExpiresIn=3600
            )

            return render_template(
                'current_processed.html',
                filename=file.filename,
                filter=selected_filter,
                image_url=image_url
            )
        except Exception as e:
            return render_template('error.html', message=f'Upload failed: {str(e)}')

    return render_template('error.html', message='Invalid input: ensure file and filter are selected.')

@app.route('/show_processed/<filename>')
def show_processed(filename):
    try:
        processed_key = filename  # Assuming Lambda keeps the same filename
        processed_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': OUTPUT_BUCKET, 'Key': processed_key},
            ExpiresIn=3600
        )
        return render_template('show_processed.html', filename=filename, image_url=processed_url)
    except Exception as e:
        return render_template('error.html', message=f'❌ Could not fetch processed image: {str(e)}')


@app.route('/processed')
def processed():
    try:
        response = s3.list_objects_v2(Bucket=OUTPUT_BUCKET)
        image_list = []

        for item in response.get('Contents', []):
            key = item['Key']
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': OUTPUT_BUCKET, 'Key': key},
                ExpiresIn=3600
            )
            image_list.append({'name': key, 'url': url})

        return render_template('processed.html', images=image_list)

    except Exception as e:
        return render_template('error.html', message=f"❌ Error loading processed images: {str(e)}")


@app.route('/download/<filename>')
def download(filename):
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': OUTPUT_BUCKET, 'Key': filename},
            ExpiresIn=600
        )
        return redirect(url)
    except Exception as e:
        return render_template('error.html', message=f'Download failed: {str(e)}')

if __name__ == '__main__':
    app.run(debug=True)
