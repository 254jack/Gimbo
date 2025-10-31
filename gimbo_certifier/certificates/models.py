from django.db import models
from django.utils import timezone
import os


# 🗂 Helper for naming uploaded files
def upload_path(instance, filename):
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f"uploads/{timestamp}_{filename}"


def generated_doc_path(instance, filename):
    return f"generated/{filename}"


def template_upload_path(instance, filename):
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f"templates/{timestamp}_{filename}"


# 🧩 1️⃣ UploadedPDF: The raw Thamini PDF uploaded for data extraction
class UploadedPDF(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=upload_path)
    original_filename = models.CharField(max_length=255)
    parsed_data = models.JSONField(null=True, blank=True)  # Extracted info
    processed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.original_filename


# 🧩 2️⃣ CertificateTemplate: Uploaded certificate DOCX with placeholders
class CertificateTemplate(models.Model):
    name = models.CharField(max_length=255, default="Certificate Template")
    file = models.FileField(upload_to=template_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    placeholders = models.JSONField(null=True, blank=True)  # e.g. ["customer_name", "reg_no"]

    def __str__(self):
        return f"{self.name} ({self.uploaded_at.strftime('%Y-%m-%d')})"

    class Meta:
        ordering = ['-uploaded_at']  # newest first


# 🧩 3️⃣ GeneratedCertificate: Resulting DOCX + PDF after filling template
class GeneratedCertificate(models.Model):
    uploaded_pdf = models.ForeignKey(
        UploadedPDF,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates'
    )
    template_used = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_certificates'
    )

    # ✅ Separate file fields for both generated files
    docx_file = models.FileField(upload_to=generated_doc_path, null=True, blank=True)
    pdf_file = models.FileField(upload_to=generated_doc_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # Extracted & populated fields
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True)
    engine_no = models.CharField(max_length=100, blank=True, null=True)
    chassis_no = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    body_type = models.CharField(max_length=100, blank=True, null=True)
    insurance_value = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.customer_name or 'Unknown'} - {self.reg_no or 'No Reg'}"

    class Meta:
        ordering = ['-created_at']

    # 🧹 Auto-delete files when a certificate record is removed
    def delete(self, *args, **kwargs):
        if self.docx_file and os.path.isfile(self.docx_file.path):
            os.remove(self.docx_file.path)
        if self.pdf_file and os.path.isfile(self.pdf_file.path):
            os.remove(self.pdf_file.path)
        super().delete(*args, **kwargs)
