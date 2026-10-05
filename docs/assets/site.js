(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const safeText = (element, value) => { if (element) element.textContent = value ?? ""; };

  const menuButton = $(".menu-toggle");
  const nav = $(".nav");
  if (menuButton && nav) {
    menuButton.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(open));
    });
  }
  const current = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav a").forEach((link) => {
    if (link.getAttribute("href") === current) link.setAttribute("aria-current", "page");
  });

  const copyButton = $("[data-copy-note]");
  if (copyButton) {
    copyButton.addEventListener("click", async () => {
      const field = $("#submission-note");
      const text = field?.value ?? "";
      try {
        await navigator.clipboard.writeText(text);
        copyButton.textContent = "Copied";
      } catch {
        field?.select();
        document.execCommand("copy");
        copyButton.textContent = "Copied";
      }
      window.setTimeout(() => { copyButton.textContent = "Copy note"; }, 1800);
    });
  }

  const submissionStatus = $("#submission-status");
  if (submissionStatus) {
    fetch("data/current_submission.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json();
      })
      .then((record) => {
        const ready = record.status === "HOLDOUT_GATE_PASSED_UNSCORED" && record.download_path;
        submissionStatus.classList.toggle("ready", Boolean(ready));
        safeText($("#submission-status-label"), ready ? "Spatial gate passed · organizer-unscored" : "Not submission-ready");
        safeText($("#submission-status-title"), ready ? "A validated candidate is available" : "No validated TIFF is available");
        safeText($("#submission-status-copy"), ready
          ? "The candidate passed the preregistered pooled spatial pseudo-holdout and GeoTIFF checks. The exact known-fault pixels are excluded; there is no proximity buffer. This is not an organizer score or proof of hidden-label performance."
          : (record.warning || "No candidate has passed the preregistered holdout and output checks."));
        const download = $("#candidate-download");
        if (download) {
          if (ready) {
            download.href = record.download_path;
            download.download = record.filename || "gemsdoe37-candidate.tif";
            download.classList.remove("btn-disabled");
            download.removeAttribute("aria-disabled");
            download.setAttribute("aria-label", `Download ${record.filename}`);
          } else {
            download.removeAttribute("href");
            download.classList.add("btn-disabled");
            download.setAttribute("aria-disabled", "true");
          }
        }
        const details = $("#candidate-details");
        if (details) details.hidden = !ready;
        if (ready) {
          safeText($("#submission-filename"), record.filename);
          safeText($("#submission-name"), record.submission_name);
          safeText($("#submission-hash"), record.sha256);
          safeText($("#submission-pixels"), Number(record.positive_pixels).toLocaleString());
          safeText($("#submission-holdout"), Number(record.public_catalogue_holdout_pooled_dti).toFixed(4));
          const reportLink = $("#holdout-report-link");
          if (reportLink && record.holdout_report_path) reportLink.href = record.holdout_report_path;
          const note = $("#submission-note");
          if (note) note.value = record.submission_note || "";
        }
      })
      .catch((error) => {
        safeText($("#submission-status-copy"), `Submission status unavailable (${error.message}). Treat this page as not submission-ready until the status file can be checked.`);
      });
  }
})();
