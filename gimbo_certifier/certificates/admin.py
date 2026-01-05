from django.contrib import admin
from .models import UploadedPDF, GeneratedCertificate, CertificateTemplate

@admin.register(UploadedPDF)
class UploadedPDFAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'uploaded_at', 'processed')
    list_filter = ('processed',)
    search_fields = ('original_filename',)

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'uploaded_at')
    search_fields = ('name',)

@admin.register(GeneratedCertificate)
class GeneratedCertificateAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'reg_no', 'created_at','destination')
    search_fields = ('customer_name', 'reg_no')
