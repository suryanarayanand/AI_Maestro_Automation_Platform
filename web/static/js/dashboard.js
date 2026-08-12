async function updateExecutionStatus() {
    const statusElement = document.getElementById("execution-status");
    if (!statusElement) return;

    const response = await fetch("/execution-status");
    if (!response.ok) return;
    const data = await response.json();

    const statusLabels = {
        running: "Running",
        queued: "Queued",
        cancel_requested: "Cancelling",
        idle: "Idle",
    };
    statusElement.textContent = statusLabels[data.status] || data.status;
    statusElement.className = `status-pill status-${data.status}`;
    document.getElementById("execution-suite").textContent = data.suite || "-";
    document.getElementById("execution-time").textContent = data.start_time || "-";
    document.getElementById("execution-progress").textContent =
        data.total ? `${data.completed}/${data.total}` : "-";
    const cancelButton = document.getElementById("cancel-execution");
    if (cancelButton) {
        const cancellable = ["running", "queued", "cancel_requested"].includes(data.status) && data.job_id;
        cancelButton.classList.toggle("d-none", !cancellable);
        cancelButton.disabled = data.status === "cancel_requested";
        cancelButton.textContent = data.status === "cancel_requested" ? "Cancelling..." : "Cancel Execution";
        cancelButton.onclick = cancellable && data.status !== "cancel_requested" ? async () => {
            if (!confirm(`Cancel job #${data.job_id}?`)) return;
            cancelButton.disabled = true;
            cancelButton.textContent = "Cancelling...";
            await fetch(`/jobs/${data.job_id}/cancel`, {method: "POST"});
            updateExecutionStatus();
        } : null;
    }
}

updateExecutionStatus();
setInterval(updateExecutionStatus, 5000);

function initializeYamlGenerationProgress() {
    const form = document.getElementById("yaml-generation-form");
    if (!form) return;

    const panel = document.getElementById("yaml-generation-progress");
    const bar = document.getElementById("yaml-generation-bar");
    const percent = document.getElementById("yaml-generation-percent");
    const stage = document.getElementById("yaml-generation-stage");
    const submit = document.getElementById("yaml-generation-submit");
    const stages = [
        [5, "Uploading workbook..."],
        [20, "Detecting test-case worksheets..."],
        [38, "Converting to the supported Excel format..."],
        [58, "Reading normalized test cases..."],
        [74, "Generating Maestro YAML drafts..."],
        [88, "Applying AI fallback where needed..."],
        [94, "Saving drafts for review..."],
    ];

    form.addEventListener("submit", () => {
        panel.classList.remove("d-none");
        submit.disabled = true;
        submit.textContent = "Generating...";
        let index = 0;

        const showStage = () => {
            const [value, label] = stages[index];
            bar.style.width = `${value}%`;
            bar.setAttribute("aria-valuenow", value);
            percent.textContent = `${value}%`;
            stage.textContent = label;
            if (index < stages.length - 1) index += 1;
        };
        showStage();
        window.setInterval(showStage, 1400);
    });
}

initializeYamlGenerationProgress();
