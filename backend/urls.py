# E:\study\worker_inventory\worker_inventory_backend\backend\urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

# IMPORT ONLY THIS
from inventory.custom_token import CustomTokenView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('inventory.urls')),

    # CUSTOM LOGIN
    path('api/login/', CustomTokenView.as_view(), name='custom_token_obtain_pair'),

    # TOKEN REFRESH
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
