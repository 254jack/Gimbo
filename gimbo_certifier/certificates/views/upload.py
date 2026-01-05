from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, FileResponse
from certificates.forms import UnifiedCertificateUploadForm
from certificates.workflows.installation_flow import generate_certificate,regenerate_certificate_with_imei
from certificates.forms import ImeiUpdateForm
import os
from certificates.models import GeneratedCertificate
from certificates.utils import extract_text_from_pdf, parse_thamini_pdf_text


def unified_certificate_upload_view(request):
    """
    Unified view for both Installation and De-installation certificate workflows.

    Installation:
        - Requires PDF + DOCX template
    De-installation:
        - Accepts PDF (extract data) or DOCX (with placeholders)
        - Generates de-installation certificate
    """
    if request.method == "POST":
        form = UnifiedCertificateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            workflow_type = form.cleaned_data.get("workflow_type")
            pdf_file = form.cleaned_data.get("pdf_file")
            certificate_docx = form.cleaned_data.get("certificate_docx")
            start_number = form.cleaned_data.get("start_number")

            try:
                # -------------------- Installation Workflow --------------------
                if workflow_type == "installation":
                    if not pdf_file:
                        messages.error(request, "Please upload a PDF for Installation or Deinstallation workflow.")
                        return redirect("certificates:unified_upload")
                    if not certificate_docx:
                        messages.error(request, "Please upload a DOCX template for Installation workflow.")
                        return redirect("certificates:unified_upload")

                    gen = generate_certificate(pdf_file, certificate_docx, start_number=start_number)

                # ------------------ De-installation Workflow -------------------
                else:
                    parsed_data = {}

                    # If PDF is uploaded, extract data
                    if pdf_file:
                        try:
                            text = extract_text_from_pdf(pdf_file)
                            parsed_data = parse_thamini_pdf_text(text)
                        except Exception as e:
                            messages.error(request, f"Failed to extract data from PDF: {e}")
                            return redirect("certificates:unified_upload")

                    # DOCX must be uploaded
                    if not certificate_docx:
                        messages.error(request, "Please upload a DOCX template for De-installation workflow.")
                        return redirect("certificates:unified_upload")

                messages.success(request, f"{workflow_type.replace('_', ' ').title()} certificate generated successfully!")
                return redirect("certificates:preview", pk=gen.pk)

            except Exception as e:
                raise

    else:
        form = UnifiedCertificateUploadForm()

    return render(request, "upload.html", {"form": form})
def preview_view(request, pk):
    gen = get_object_or_404(GeneratedCertificate, pk=pk)

    if request.method == "POST":
        form = ImeiUpdateForm(request.POST, instance=gen)
        if form.is_valid():
            form.save()
            regenerate_certificate_with_imei(gen)
            messages.success(request, "IMEIs updated and certificate regenerated!")
            return redirect('certificates:preview', pk=gen.pk)
    else:
        form = ImeiUpdateForm(instance=gen)

    return render(request, 'preview.html', {'gen': gen, 'form': form})

def download_generated_view(request, pk, filetype='docx'):
    """
    Download generated certificate as DOCX or PDF, maintaining original name.
    """
    gen = get_object_or_404(GeneratedCertificate, pk=pk)
    
    if filetype == 'pdf' and gen.pdf_file:
        download_name = os.path.basename(gen.pdf_file.name)
        return FileResponse(gen.pdf_file.open('rb'), as_attachment=True, filename=download_name)
        
    elif filetype == 'docx' and gen.docx_file:
        download_name = os.path.basename(gen.docx_file.name)
        return FileResponse(gen.docx_file.open('rb'), as_attachment=True, filename=download_name)
        
    else:
        raise Http404("Requested file not found.")