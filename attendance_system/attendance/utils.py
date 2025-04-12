import qrcode
from django.conf import settings
import os

def generate_qr_code(student_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(student_id)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Save QR code to media directory
    media_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
    os.makedirs(media_path, exist_ok=True)
    file_path = os.path.join(media_path, f'{student_id}.png')
    img.save(file_path)
    return file_path
