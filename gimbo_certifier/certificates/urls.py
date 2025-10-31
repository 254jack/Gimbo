from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # 🧾 Main upload page — user uploads Thamini PDF + certificate DOCX
    path('', views.upload_pdf_view, name='upload'),

    # ✅ Success page after generating certificates

    # 💾 Download generated files
    path('download/<int:pk>/', views.download_generated_view, name='download_docx'),
    path('preview/<int:pk>/', views.preview_view, name='preview'),
    path('download/<int:pk>/<str:filetype>/', views.download_generated_view, name='download'),
]
