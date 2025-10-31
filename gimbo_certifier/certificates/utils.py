import re
import io
import os
import pdfplumber
from datetime import datetime
from docxtpl import DocxTemplate
from django.conf import settings
from django.core.files.base import ContentFile

# ---------- PDF extraction helpers ----------
def extract_text_from_pdf(file_path_or_fileobj):
    """
    Returns full text from a pdf.
    file_path_or_fileobj: path or file-like object
    """
    text = ""
    if hasattr(file_path_or_fileobj, "read"):
        # file-like object
        with pdfplumber.open(file_path_or_fileobj) as pdf:
            for page in pdf.pages:
                part = page.extract_text() or ""
                text += part + "\n"
    else:
        with pdfplumber.open(file_path_or_fileobj) as pdf:
            for page in pdf.pages:
                part = page.extract_text() or ""
                text += part + "\n"
    return text

# ---------- robust regex search ----------
def find_one(regex_list, text, flags=re.IGNORECASE):
    """
    Try a list of regex patterns; return first group(1) match stripped, else None.
    Each pattern should have a capturing group for the target value.
    """
    for pat in regex_list:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None

def normalize_spaces(s):
    return re.sub(r'\s+', ' ', s).strip() if s else s

# ---------- domain-specific extraction (customize as needed) ----------
def parse_thamini_pdf_text(full_text):
    """
    Returns a dict with parsed fields from the Thamini-style valuation PDF.
    Patterns are intentionally broad and robust.
    """
    t = full_text

    data = {}
    # Examples from your sample:
    # "CLIENT NAME: Elijah Wanyoike Mwaniki CONTACTS: 0769259545"
    data['customer_name'] = find_one([
        r"CLIENT NAME[:\s]*([A-Z][\w\s\.\-,'()]+?)(?:CONTACTS:|\n|DESTINATION:|$)",
        r"CLIENT NAME[:\s]*([^\n\r]+)"
    ], t) or find_one([
        r"CLIENT[:\s]*([A-Z][\w\s\.\-,'()]+?)(?:\n|$)",
    ], t)

    data['destination'] = find_one([
        r"(?:DESTINATION|DESTINATION:)\s*[:]*\s*([A-Z][\w\s\.\-&,]+)",
        r"Destination\s*[:]*\s*([^\n]+)"
    ], t)

    data['reg_no'] = find_one([
        r"REGISTRATION NO[:\s]*([A-Z0-9\-]+)",
        r"Vehicle Reg no[:\s]*([A-Z0-9\-]+)",
        r"VEHICLE REG NO[:\s]*([A-Z0-9\-]+)",
        r"\b([A-Z]{1,3}\s*\d{1,4}[A-Z]{0,2})\b"
    ], t)

    data['engine_no'] = find_one([
        r"ENGINE NO[:\s]*([A-Z0-9\-]+)",
        r"Engine number[:\s]*([A-Z0-9\-]+)",
    ], t)

    data['chassis_no'] = find_one([
        r"CHASSIS NO[:\s]*([A-Z0-9\-]+)",
        r"CHASSIS NUMBER[:\s]*([A-Z0-9\-]+)",
        r"NCP165[-\s]*[0-9]+"  # sample pattern; keep as fallback
    ], t)

    data['color'] = find_one([
        r"COLOUR[:\s]*([A-Za-z]+)",
        r"Color[:\s]*([A-Za-z]+)",
    ], t)

    # dates — accept formats like 30-10-2025 or 2025-10-30 or 30 Oct-25
    data['valuation_date'] = find_one([
        r"Valuation Date[:\s]*([0-3]?\d[\/\-\s][A-Za-z0-9\-\s\/]+)",
        r"Valuation Date[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        r"Date of Inspection[:\s]*([0-3]?\d[\/\-\s][A-Za-z0-9\-\s\/]+)"
    ], t)

    # signatory / examiner
    data['signatory'] = find_one([
        r"Examiner[:\s]*\(?([A-Za-z0-9\-\)]+)\)?",
        r"Signatory Name[:\s]*([A-Za-z\s\.]+)"
    ], t)

    # other fallback heuristics
    # Example: If engine pattern not found, search for capital tokens starting with INZ- style
    if not data.get('engine_no'):
        m = re.search(r"\b(INZ-[A-Z0-9]+)\b", t)
        if m:
            data['engine_no'] = m.group(1).strip()

    # Normalize
    for k, v in data.items():
        data[k] = normalize_spaces(v) if v else ""

    return data

# ---------- document rendering ----------
def render_certificate_docx(template_path, data_dict, output_filename=None):
    """
    Render a docx from a docxtpl template and return bytes content.
    template_path: path to .docx template with docxtpl placeholders e.g. {{customer_name}}
    data_dict: mapping placeholder->value
    returns: (filename, bytes)
    """
    tpl = DocxTemplate(template_path)
    # Optionally process dates into nice format
    # e.g. data_dict['install_date'] = format_date_string(data_dict.get('install_date'))
    tpl.render(data_dict)

    # Save to in-memory buffer
    buf = io.BytesIO()
    tpl.save(buf)
    buf.seek(0)
    filename = output_filename or f"{data_dict.get('reg_no','cert')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return filename, buf.read()

# ---------- optional docx -> pdf conversion ----------
def convert_docx_to_pdf_linux(docx_path, pdf_path):
    """
    Convert docx to pdf using libreoffice (headless).
    Requires libreoffice installed on the server.
    """
    import subprocess
    subprocess.check_call([
        "libreoffice", "--headless", "--convert-to", "pdf", "--outdir",
        os.path.dirname(pdf_path), docx_path
    ])

# ---------- wrapper to generate and save FileField content ----------
def generate_and_attach_certificate(uploaded_pdf_instance, template_path, save_model_cls):
    """
    uploaded_pdf_instance: UploadedPDF model instance
    template_path: path to docx template
    save_model_cls: class for GeneratedCertificate model (or module import)
    Returns instance of GeneratedCertificate
    """
    # 1. Extract text
    fp = uploaded_pdf_instance.file.path
    text = extract_text_from_pdf(fp)
    parsed = parse_thamini_pdf_text(text)

    # 2. Render docx
    filename, bytes_content = render_certificate_docx(template_path, parsed)

    # 3. Save GeneratedCertificate model
    gen = save_model_cls(
        uploaded_pdf=uploaded_pdf_instance,
        customer_name=parsed.get('customer_name'),
        reg_no=parsed.get('reg_no'),
    )
    # create Django ContentFile to save to FileField
    gen.file.save(filename, ContentFile(bytes_content))
    gen.save()

    # update uploaded_pdf_instance
    uploaded_pdf_instance.parsed_data = parsed
    uploaded_pdf_instance.processed = True
    uploaded_pdf_instance.save()

    return gen
