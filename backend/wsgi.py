import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()

# Create default users on startup
try:
    from django.contrib.auth.models import User
    from django.db import connection
    connection.ensure_connection()
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    
    if not User.objects.filter(username='member1').exists():
        User.objects.create_user('member1', 'member1@example.com', 'member123')
    
    if not User.objects.filter(username='member2').exists():
        User.objects.create_user('member2', 'member2@example.com', 'member123')
        
except Exception as e:
    pass
