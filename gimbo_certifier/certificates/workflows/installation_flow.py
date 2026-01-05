import os
import mimetypes
import logging
from datetime import date, timedelta
import tempfile
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from docxtpl import DocxTemplate
from certificates.models import UploadedPDF, GeneratedCertificate, CertificateTemplate
from certificates.utils import extract_text_from_pdf, parse_thamini_pdf_text,convert_docx_to_pdf

logger = logging.getLogger(__name__)

def generate_certificate(uploaded_pdf_file, certificate_docx_file, start_number=None, imei_1='', imei_2=''):
    up = UploadedPDF(original_filename=uploaded_pdf_file.name)
    up.file.save(uploaded_pdf_file.name, uploaded_pdf_file)
    up.save()

    if not uploaded_pdf_file.name.lower().endswith('.pdf'):
        raise ValueError("Uploaded PDF file is invalid.")
    if not certificate_docx_file.name.lower().endswith('.docx'):
        raise ValueError("Uploaded DOCX template is invalid.")

    text = extract_text_from_pdf(up.file.path)
    parsed_data = parse_thamini_pdf_text(text)

    for field in ['customer_name', 'reg_no', 'engine_no', 'chassis_no', 'color', 'body_type', 'destination']:
        val = parsed_data.get(field)
        if val:
            parsed_data[field] = str(val).upper()

    last_cert = GeneratedCertificate.objects.order_by('-id').first()
    certificate_number = int(last_cert.certificate_number) + 1 if last_cert else 1
    if start_number:
        certificate_number = int(start_number)
    parsed_data['certificate_number'] = certificate_number

    today = date.today()
    expiry_date = today + timedelta(days=365)
    parsed_data.setdefault('certificate_date', today.isoformat())
    parsed_data.setdefault('expiry_date', expiry_date.isoformat())

    parsed_data['imei1'] = imei_1.upper() if imei_1 else ""
    parsed_data['imei2'] = imei_2.upper() if imei_2 else ""

    temp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_docx_path = os.path.join(temp_dir, f"{up.id}_template.docx")
    with open(temp_docx_path, "wb+") as f:
        for chunk in certificate_docx_file.chunks():
            f.write(chunk)

    tpl = DocxTemplate(temp_docx_path)
    placeholders = tpl.get_undeclared_template_variables()
    for key in placeholders:
        parsed_data.setdefault(key, "")
    tpl.render(parsed_data)

    output_dir = os.path.join(settings.MEDIA_ROOT, "generated")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"{parsed_data.get('reg_no', 'CERT')}_{timestamp}"
    docx_output_path = os.path.join(output_dir, f"{base_filename}.docx")
    tpl.save(docx_output_path)

    pdf_output_path = None
    try:
        pdf_path = convert_docx_to_pdf(docx_output_path)
        pdf_output_path = str(pdf_path)
    except Exception as e:
        logger.warning(f"PDF conversion failed: {e}")

    tpl_record = CertificateTemplate.objects.create(
    name=f"Template {uploaded_pdf_file.name}",
    file=certificate_docx_file
)

    gen = GeneratedCertificate(
        uploaded_pdf=up,
        template_used=tpl_record,
        customer_name=parsed_data.get('customer_name'),
        destination=parsed_data.get('destination'),
        reg_no=parsed_data.get('reg_no'),
        engine_no=parsed_data.get('engine_no'),
        chassis_no=parsed_data.get('chassis_no'),
        color=parsed_data.get('color'),
        body_type=parsed_data.get('body_type'),
        insurance_value=parsed_data.get('insurance_value'),
        certificate_number=parsed_data.get('certificate_number'),
        certificate_date=today,
        expiry_date=expiry_date,
        imei_1=parsed_data.get('imei_1'),
        imei_2=parsed_data.get('imei_2'),
    )
    gen.save()

    with open(docx_output_path, "rb") as f:
        gen.docx_file.save(os.path.basename(docx_output_path), ContentFile(f.read()), save=False)
    if pdf_output_path and os.path.exists(pdf_output_path):
        with open(pdf_output_path, "rb") as f:
            gen.pdf_file.save(os.path.basename(pdf_output_path), ContentFile(f.read()), save=True)
    else:
        gen.save()

    os.remove(temp_docx_path)
    up.file.delete(save=False)
    if pdf_output_path and os.path.exists(pdf_output_path):
        os.remove(pdf_output_path)

    return gen


def regenerate_certificate_with_imei(gen: GeneratedCertificate):
    """
    Re-render DOCX + PDF when IMEIs are added/updated.
    Always uses the original template from template_used.file.
    Updates both docx_file and pdf_file on GeneratedCertificate.
    """
    if not gen.template_used or not gen.template_used.file:
        raise ValueError("No original template available for regeneration.")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
        temp_docx_path = tmp_file.name

    tpl = DocxTemplate(gen.template_used.file.path)

    data = {
        "customer_name": gen.customer_name or "",
        "destination": gen.destination or "",
        "reg_no": gen.reg_no or "",
        "engine_no": gen.engine_no or "",
        "chassis_no": gen.chassis_no or "",
        "color": gen.color or "",
        "body_type": gen.body_type or "",
        "certificate_number": gen.certificate_number or "",
        "certificate_date": gen.certificate_date or "",
        "expiry_date": gen.expiry_date or "",
        "imei1": gen.imei_1 or "",
        "imei2": gen.imei_2 or "",
    }

    tpl.render(data)
    tpl.save(temp_docx_path)

    with open(temp_docx_path, "rb") as f:
        gen.docx_file.save(os.path.basename(temp_docx_path), ContentFile(f.read()), save=False)

    pdf_path = convert_docx_to_pdf(temp_docx_path)
    with open(pdf_path, "rb") as f:
        gen.pdf_file.save(os.path.basename(pdf_path), ContentFile(f.read()), save=True)

    os.remove(temp_docx_path)
    os.remove(pdf_path)