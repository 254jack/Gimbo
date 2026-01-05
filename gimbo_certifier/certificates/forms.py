from django import forms
from .models import UploadedPDF, CertificateTemplate,GeneratedCertificate


# 🧩 1️⃣ Combined upload form: PDF + DOCX
class UploadFileForm(forms.ModelForm):
    certificate_docx = forms.FileField(
        required=True,
        label="Certificate Word File (.docx)",
        help_text="Upload the blank certificate template to be filled automatically."
    )

    class Meta:
        model = UploadedPDF
        fields = ['file'] 
        labels = {
            'file': 'Thamini PDF File',
        }

class EditParsedDataForm(forms.Form):
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



class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = CertificateTemplate
        fields = ['name', 'file']
        labels = {
            'name': 'Template Name',
            'file': 'Upload Template (.docx)',
        }



WORKFLOW_CHOICES = (
    ('installation', 'Installation/De-installation Certificate'),
)

class UnifiedCertificateUploadForm(forms.Form):
    workflow_type = forms.ChoiceField(
        choices=WORKFLOW_CHOICES,
        label="Certificate Type",
        widget=forms.RadioSelect
    )
    pdf_file = forms.FileField(
        required=False,
        label="PDF (required for Installation & de-installation)"
    )
    certificate_docx = forms.FileField(
        required=True,
        label="Certificate DOCX Template"
    )
    start_number = forms.IntegerField(
        required=False,
        label="Certificate Number (optional)",
        help_text="If not provided, system auto-generates the next number"
    )


class ImeiUpdateForm(forms.ModelForm):
    class Meta:
        model = GeneratedCertificate
        fields = ['imei_1', 'imei_2']
        widgets = {
            'imei_1': forms.TextInput(attrs={'maxlength': 15, 'class': 'form-control'}),
            'imei_2': forms.TextInput(attrs={'maxlength': 15, 'class': 'form-control'}),
        }

    def clean_imei_1(self):
        imei = self.cleaned_data.get('imei_1')
        if imei:
            return imei.strip()
        return ""

    def clean_imei_2(self):
        imei = self.cleaned_data.get('imei_2')
        if imei:
            return imei.strip()
        return ""