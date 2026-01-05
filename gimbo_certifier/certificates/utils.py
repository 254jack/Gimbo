import re
import io
import os
import sys
import pdfplumber
import subprocess
from datetime import datetime
from pathlib import Path
from docxtpl import DocxTemplate
from django.core.files.base import ContentFile

# ---------- PDF extraction helpers ----------
def extract_text_from_pdf(file_path_or_fileobj):
    """
    Returns full text from a pdf.
    file_path_or_fileobj: path or file-like object
    """
    text = ""
    if hasattr(file_path_or_fileobj, "read"):
        with pdfplumber.open(file_path_or_fileobj) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    else:
        with pdfplumber.open(file_path_or_fileobj) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    return text

# ---------- robust regex search ----------
def find_one(regex_list, text, flags=re.IGNORECASE):
    for pat in regex_list:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None

def normalize_spaces(s):
    return re.sub(r'\s+', ' ', s).strip() if s else s

# ---------- domain-specific extraction ----------
def parse_thamini_pdf_text(full_text):
    t = full_text
    data = {}

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
    # truncate to first two words
    if data['destination']:
        data['destination'] = " ".join(data['destination'].split()[:2])

    data['reg_no'] = find_one([
        r"REGISTRATION\s*NO[:\s]*([A-Z]{3}[\s\-]*\d{1,4}[A-Z])",
        r"VEHICLE\s*REG\s*NO[:\s]*([A-Z]{3}[\s\-]*\d{1,4}[A-Z])",
        r"\b([A-Z]{3}[\s\-]*\d{1,4}[A-Z])\b",
    ], t)



    data['engine_no'] = find_one([
        r"ENGINE NO[:\s]*([A-Z0-9\-]+)",
        r"Engine number[:\s]*([A-Z0-9\-]+)",
    ], t)

    data['chassis_no'] = find_one([
        r"CHASSIS NO[:\s]*([A-Z0-9\-]+)",
        r"CHASSIS NUMBER[:\s]*([A-Z0-9\-]+)",
        r"NCP165[-\s]*[0-9]+"
    ], t)

    data['color'] = find_one([
        r"COLOUR[:\s]*([A-Za-z]+)",
        r"Color[:\s]*([A-Za-z]+)",
    ], t)

    data['valuation_date'] = find_one([
        r"Valuation Date[:\s]*([0-3]?\d[\/\-\s][A-Za-z0-9\-\s\/]+)",
        r"Valuation Date[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        r"Date of Inspection[:\s]*([0-3]?\d[\/\-\s][A-Za-z0-9\-\s\/]+)"
    ], t)

    data['signatory'] = find_one([
        r"Examiner[:\s]*\(?([A-Za-z0-9\-\)]+)\)?",
        r"Signatory Name[:\s]*([A-Za-z\s\.]+)"
    ], t)

    # fallback for engine number
    if not data.get('engine_no'):
        m = re.search(r"\b(INZ-[A-Z0-9]+)\b", t)
        if m:
            data['engine_no'] = m.group(1).strip()

    # normalize spaces
    for k, v in data.items():
        data[k] = normalize_spaces(v) if v else ""

    return data

# ---------- render DOCX ----------
def render_certificate_docx(template_path, data_dict, output_filename=None):
    tpl = DocxTemplate(template_path)
    tpl.render(data_dict)
    buf = io.BytesIO()
    tpl.save(buf)
    buf.seek(0)
    filename = output_filename or f"{data_dict.get('reg_no','cert')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    return filename, buf.read()
def convert_docx_to_pdf(docx_path):
    docx_path = Path(docx_path).resolve()
    output_dir = docx_path.parent
    pdf_path = output_dir / f"{docx_path.stem}.pdf"

    if sys.platform.startswith("win"):
        # ---- WINDOWS: uses Microsoft Word via docx2pdf ----
        try:
            from docx2pdf import convert
        except ImportError:
            raise RuntimeError("docx2pdf is not installed on Windows")

        convert(str(docx_path), str(pdf_path))

    else:
        # ---- LINUX / UNIX: uses LibreOffice ----
        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(docx_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise RuntimeError("LibreOffice is not installed on this system")

    if not pdf_path.exists():
        raise RuntimeError("PDF conversion failed")

    return pdf_path
# ---------- generate & attach certificate ----------
def generate_and_attach_certificate(uploaded_pdf_instance, template_path, save_model_cls):
    """
    Generate DOCX certificate from template and uploaded PDF,
    save to GeneratedCertificate, convert to PDF cross-platform.
    """
    # 1️⃣ Extract text
    fp = uploaded_pdf_instance.file.path
    text = extract_text_from_pdf(fp)
    parsed = parse_thamini_pdf_text(text)

    # 2️⃣ Render DOCX
    filename, bytes_content = render_certificate_docx(template_path, parsed)

    # 3️⃣ Save GeneratedCertificate
    gen = save_model_cls(
        uploaded_pdf=uploaded_pdf_instance,
        customer_name=parsed.get('customer_name'),
        reg_no=parsed.get('reg_no'),
        destination=parsed.get('destination'),
    )
    # Save DOCX
    gen.docx_file.save(filename, ContentFile(bytes_content))
    gen.save()

    # 4️⃣ Convert to PDF
    try:
        pdf_path = convert_docx_to_pdf(gen.docx_file.path)
        with open(pdf_path, "rb") as f:
            gen.pdf_file.save(pdf_path.name, ContentFile(f.read()))
        gen.save()
    except RuntimeError as e:
        print(f"PDF conversion skipped: {e}")

    # 5️⃣ Update uploaded PDF instance
    uploaded_pdf_instance.parsed_data = parsed
    uploaded_pdf_instance.processed = True
    uploaded_pdf_instance.save()

    return gen
