document.addEventListener("DOMContentLoaded", function () {
    const workflowSelect = document.querySelector('select[name="workflow_type"]');

    const pdfField = document.getElementById("pdfField");
    const pdfLabel = document.getElementById("pdfLabel");

    const docxLabel = document.getElementById("docxLabel");
    const docxHelp = document.getElementById("docxHelp");

    if (!workflowSelect) return;

    function updateUI() {
        const workflow = workflowSelect.value;

        if (workflow === "installation") {
            // SHOW PDF
            pdfField.style.display = "block";

            // DOCX text
            docxLabel.textContent = "Installation Certificate DOCX Template";
            docxHelp.textContent =
                "Upload the installation certificate template (.docx).";

        } else {
            // HIDE PDF
            pdfField.style.display = "none";

            // DOCX text for de-installation
            docxLabel.textContent =
                "Existing Certificate (PDF or DOCX)";
            docxHelp.textContent =
                "Upload an already generated certificate to extract data for de-installation.";
        }
    }

    workflowSelect.addEventListener("change", updateUI);

    // Run on page load
    updateUI();
});


document.addEventListener("DOMContentLoaded", function() {
    const workflowRadios = document.querySelectorAll('input[name="workflow_type"]');
    const pdfField = document.getElementById("pdfField");

    function togglePDFField() {
        const selected = document.querySelector('input[name="workflow_type"]:checked');
        if (selected && selected.value === "installation") {
            pdfField.style.display = "block";
        } else {
            pdfField.style.display = "none";
        }
    }

    workflowRadios.forEach(radio => {
        radio.addEventListener("change", togglePDFField);
    });

    togglePDFField();
});


document.addEventListener('DOMContentLoaded', function() {
    const workflowRadios = document.querySelectorAll('input[name="workflow_type"]');
    const pdfField = document.getElementById('pdf-field');

    function togglePDFField() {
        const selected = document.querySelector('input[name="workflow_type"]:checked').value;
        pdfField.style.display = selected === 'installation' ? 'block' : 'none';
    }

    workflowRadios.forEach(radio => radio.addEventListener('change', togglePDFField));
    togglePDFField();
});
