from django import forms
from .models import UploadedPDF, CertificateTemplate


# 🧩 1️⃣ Combined upload form: PDF + DOCX
class UploadFileForm(forms.ModelForm):
    certificate_docx = forms.FileField(
        required=True,
        label="Certificate Word File (.docx)",
        help_text="Upload the blank certificate template to be filled automatically."
    )

    class Meta:
        model = UploadedPDF
        fields = ['file']  # file will be the Thamini PDF
        labels = {
            'file': 'Thamini PDF File',
        }


# 🧩 2️⃣ Optional: simple form if you ever want to upload PDFs alone
class UploadPDFForm(forms.ModelForm):
    class Meta:
        model = UploadedPDF
        fields = ['file']
        labels = {
            'file': 'Upload Thamini PDF File',
        }


# 🧩 3️⃣ Form for reviewing and editing parsed data before generating the certificate
class EditParsedDataForm(forms.Form):
    # These fields should match what appears in your Word template placeholders
    customer_name = forms.CharField(max_length=255, required=True, label="Customer Name")
    reg_no = forms.CharField(max_length=64, required=False, label="Registration No.")
    engine_no = forms.CharField(max_length=64, required=False, label="Engine No.")
    chassis_no = forms.CharField(max_length=64, required=False, label="Chassis No.")
    color = forms.CharField(max_length=64, required=False, label="Color")
    body_type = forms.CharField(max_length=64, required=False, label="Body Type")
    insurance_value = forms.CharField(max_length=64, required=False, label="Insurance Value")
    destination = forms.CharField(max_length=255, required=False, label="Destination")
    install_date = forms.CharField(max_length=64, required=False, label="Installation Date")
    due_date = forms.CharField(max_length=64, required=False, label="Due Date")
    signatory = forms.CharField(max_length=255, required=False, label="Signatory")

    # add or remove fields depending on the placeholders in your Word docx template


# 🧩 4️⃣ Certificate template upload form (admin or management use)
class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = CertificateTemplate
        fields = ['name', 'file']
        labels = {
            'name': 'Template Name',
            'file': 'Upload Template (.docx)',
        }
