from django.urls import path
from .views import upload

app_name = 'certificates'

urlpatterns = [
    path('upload/', upload.unified_certificate_upload_view, name='unified_upload'),
    path('preview/<int:pk>/', upload.preview_view, name='preview'),
    path('download/<int:pk>/<str:filetype>/', upload.download_generated_view, name='download'),
]
