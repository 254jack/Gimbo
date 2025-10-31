import os
import re
import zipfile
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, Http404
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from docxtpl import DocxTemplate
from docx2pdf import convert
from .models import UploadedPDF, GeneratedCertificate
from .forms import UploadFileForm
from .utils import extract_text_from_pdf, parse_thamini_pdf_text


# -------------------------------------------------------------------------
# Helper: Extract placeholders from DOCX template
# -------------------------------------------------------------------------
def extract_placeholders_from_docx(docx_path):
    """Find {{ variable }} placeholders inside a .docx template."""
    try:
        tpl = DocxTemplate(docx_path)
        return sorted(list(tpl.get_undeclared_template_variables()))
    except Exception:
        vars_found = set()
        with zipfile.ZipFile(docx_path) as docx:
            for name in docx.namelist():
                if name.endswith("document.xml"):
                    xml_content = docx.read(name).decode("utf-8")
                    vars_found.update(re.findall(r"{{\s*(.*?)\s*}}", xml_content))
        return sorted(list(vars_found))


# -------------------------------------------------------------------------
# Upload and generate certificate → Preview before download
# -------------------------------------------------------------------------
def upload_pdf_view(request):
    """
    Upload Thamini PDF + certificate .docx.
    Extract values, fill placeholders, generate files,
    then redirect to preview screen before downloading.
    """
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # --- Validate uploaded files ---
            pdf_file = request.FILES.get('file')
            docx_file = request.FILES.get('certificate_docx')
            if not pdf_file or not docx_file:
                return HttpResponse("Please upload both Thamini PDF and Certificate DOCX.", status=400)
            if not pdf_file.name.lower().endswith('.pdf'):
                return HttpResponse("Invalid PDF file format.", status=400)
            if not docx_file.name.lower().endswith('.docx'):
                return HttpResponse("Invalid DOCX file format.", status=400)

            # --- Save uploaded PDF ---
            up = form.save(commit=False)
            up.original_filename = pdf_file.name
            up.save()
            pdf_path = up.file.path

            # --- Save uploaded DOCX template temporarily ---
            temp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            docx_path = os.path.join(temp_dir, f"{up.id}_template.docx")
            with open(docx_path, "wb+") as destination:
                for chunk in docx_file.chunks():
                    destination.write(chunk)

            # --- Extract and parse data from Thamini PDF ---
            try:
                file_type, _ = mimetypes.guess_type(pdf_path)
                if file_type != 'application/pdf':
                    return HttpResponse("Please upload a valid Thamini PDF file.", status=400)

                text = extract_text_from_pdf(pdf_path)
                parsed_data = parse_thamini_pdf_text(text)
                up.parsed_data = parsed_data
                up.save()
            except Exception as e:
                return HttpResponse(f"Error reading PDF: {e}", status=500)

            # --- Render DOCX with parsed data ---
            tpl = DocxTemplate(docx_path)
            placeholders = extract_placeholders_from_docx(docx_path)
            for key in placeholders:
                if key not in parsed_data:
                    parsed_data[key] = ""

            tpl.render(parsed_data)

            output_dir = os.path.join(settings.MEDIA_ROOT, "generated")
            os.makedirs(output_dir, exist_ok=True)

            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"{parsed_data.get('reg_no', 'CERT')}_{timestamp}"
            docx_output_path = os.path.join(output_dir, f"{base_filename}.docx")
            tpl.save(docx_output_path)

            # --- Convert DOCX → PDF (if possible) ---
            pdf_output_path = docx_output_path.replace(".docx", ".pdf")
            try:
                convert(docx_output_path, pdf_output_path)
            except Exception as e:
                print(f"PDF conversion failed: {e}")
                pdf_output_path = None

            # --- Save GeneratedCertificate record ---
            gen = GeneratedCertificate(
                uploaded_pdf=up,
                customer_name=parsed_data.get('customer_name'),
                reg_no=parsed_data.get('reg_no'),
                engine_no=parsed_data.get('engine_no'),
                chassis_no=parsed_data.get('chassis_no'),
                color=parsed_data.get('color'),
                body_type=parsed_data.get('body_type'),
                insurance_value=parsed_data.get('insurance_value'),
            )

            # Save DOCX
            with open(docx_output_path, "rb") as f:
                gen.docx_file.save(os.path.basename(docx_output_path), ContentFile(f.read()))

            # Save PDF (optional)
            if pdf_output_path and os.path.exists(pdf_output_path):
                with open(pdf_output_path, "rb") as f:
                    gen.pdf_file.save(os.path.basename(pdf_output_path), ContentFile(f.read()))

            gen.save()
            up.processed = True
            up.save()

            # --- Clean temp ---
            try:
                os.remove(docx_path)
            except FileNotFoundError:
                pass

            # Redirect to preview page
            return redirect('certificates:preview', pk=gen.pk)
    else:
        form = UploadFileForm()

    return render(request, 'upload.html', {'form': form})


# -------------------------------------------------------------------------
# Preview generated certificate (before download)
# -------------------------------------------------------------------------
def preview_view(request, pk):
    gen = get_object_or_404(GeneratedCertificate, pk=pk)
    return render(request, 'preview.html', {'gen': gen})


# -------------------------------------------------------------------------
# Download certificate file (DOCX or PDF)
# -------------------------------------------------------------------------
def download_generated_view(request, pk, filetype='docx'):
    gen = get_object_or_404(GeneratedCertificate, pk=pk)
    if filetype == 'pdf' and gen.pdf_file:
        return FileResponse(
            gen.pdf_file.open('rb'),
            as_attachment=True,
            filename=os.path.basename(gen.pdf_file.name)
        )
    elif filetype == 'docx' and gen.docx_file:
        return FileResponse(
            gen.docx_file.open('rb'),
            as_attachment=True,
            filename=os.path.basename(gen.docx_file.name)
        )
    else:
        raise Http404("Requested file type not found.")


# -------------------------------------------------------------------------
# Legacy manual download endpoint (optional)
# -------------------------------------------------------------------------
def download_certificate(request, id):
    file_path = f"/path/to/generated/certificates/certificate_{id}.docx"
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
    else:
        raise Http404("Certificate not found")
