from django.db import models
from django.utils import timezone
import os
from datetime import date, timedelta

def upload_path(instance, filename):
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f"uploads/{timestamp}_{filename}"


def generated_doc_path(instance, filename):
    return f"generated/{filename}"


def template_upload_path(instance, filename):
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f"templates/{timestamp}_{filename}"


class UploadedPDF(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to=upload_path)
    original_filename = models.CharField(max_length=255)
    parsed_data = models.JSONField(null=True, blank=True)
    processed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.original_filename


class CertificateTemplate(models.Model):
    name = models.CharField(max_length=255, default="Certificate Template")
    file = models.FileField(upload_to=template_upload_path, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    placeholders = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.uploaded_at.strftime('%Y-%m-%d')})"

    class Meta:
        ordering = ['-uploaded_at']
class GeneratedCertificate(models.Model):
    uploaded_pdf = models.ForeignKey(
        'UploadedPDF',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates'
    )
    template_used = models.ForeignKey(
        'CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_certificates'
    )

    docx_file = models.FileField(upload_to=generated_doc_path, null=True, blank=True)
    pdf_file = models.FileField(upload_to=generated_doc_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    certificate_date = models.DateField(default=timezone.now)
    certificate_number = models.PositiveIntegerField(null=True, blank=True, editable=False)
    issue_date = models.DateField(default=timezone.now)

    destination = models.CharField(max_length=255, blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True)
    engine_no = models.CharField(max_length=100, blank=True, null=True)
    chassis_no = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    body_type = models.CharField(max_length=100, blank=True, null=True)
    insurance_value = models.CharField(max_length=50, blank=True, null=True)
    expiry_date = models.DateField(default=date.today() + timedelta(days=365))

    imei_1 = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Tracker IMEI number 1 (max 15 chars)"
    )
    imei_2 = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Tracker IMEI number 2 (max 15 chars)"
    )

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            last_cert = GeneratedCertificate.objects.order_by('-certificate_number').first()
            if last_cert and last_cert.certificate_number is not None:
                self.certificate_number = last_cert.certificate_number + 1
            else:
                self.certificate_number = 1

        if not self.certificate_date:
            self.certificate_date = timezone.now().date()

        if self.customer_name:
            self.customer_name = self.customer_name.upper()
        if self.destination:
            if isinstance(self.destination, list):
                self.destination = " ".join(self.destination[:2])
            self.destination = self.destination.upper()
        if self.reg_no:
            self.reg_no = self.reg_no.upper()
        if self.engine_no:
            self.engine_no = self.engine_no.upper()
        if self.chassis_no:
            self.chassis_no = self.chassis_no.upper()
        if self.color:
            self.color = self.color.upper()
        if self.body_type:
            self.body_type = self.body_type.upper()
        if self.insurance_value:
            self.insurance_value = self.insurance_value.upper()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.docx_file and os.path.isfile(self.docx_file.path):
            os.remove(self.docx_file.path)
        if self.pdf_file and os.path.isfile(self.pdf_file.path):
            os.remove(self.pdf_file.path)
        super().delete(*args, **kwargs)