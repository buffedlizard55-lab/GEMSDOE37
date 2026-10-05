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

  document.querySelectorAll("[data-copy-note]").forEach((copyButton) => {
    copyButton.addEventListener("click", async () => {
      const field = $(copyButton.getAttribute("data-copy-note") || "#submission-note");
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
  });

  const submissionStatus = $("#submission-status");
  if (submissionStatus) {
    fetch("data/current_submission.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`status ${response.status}`);
        return response.json();
      })
      .then((record) => {
        const ready = record.status === "CALIBRATION_GATE_PASSED_UNSCORED" && record.download_path;
        submissionStatus.classList.toggle("ready", Boolean(ready));
        safeText($("#submission-status-label"), ready ? "Spatial gate passed · organizer-unscored" : "Not submission-ready");
        safeText($("#submission-status-title"), ready ? "A validated candidate is available" : "No validated TIFF is available");
        safeText($("#submission-status-copy"), ready
          ? (record.status_copy || "A validated candidate GeoTIFF is available. This is not an organizer score or proof of hidden-label performance.")
          : (record.warning || "No candidate has passed the preregistered holdout and output checks."));
        const heroDownload = $("#hero-download");
        if (heroDownload) {
          if (ready) {
            heroDownload.href = record.download_path;
            heroDownload.download = record.filename || "gemsdoe37-candidate.tif";
            heroDownload.textContent = "\u2b07 Download the competition GeoTIFF";
            heroDownload.classList.remove("btn-disabled");
            heroDownload.removeAttribute("aria-disabled");
          } else {
            heroDownload.removeAttribute("href");
            heroDownload.textContent = "No validated GeoTIFF yet";
            heroDownload.classList.add("btn-disabled");
            heroDownload.setAttribute("aria-disabled", "true");
          }
        }
        safeText($("#hero-filename"), ready ? record.filename : "");
        const heroNote = $("#hero-note");
        if (heroNote) heroNote.value = record.submission_note || "";
        const heroBox = $("#hero-submission");
        if (heroBox) heroBox.hidden = !ready;

        const forecast = record.forecast || {};
        safeText($("#forecast-pessimistic"), forecast.pessimistic != null ? Number(forecast.pessimistic).toFixed(4) : "—");
        safeText($("#forecast-descriptor"), forecast.descriptor_model != null ? Number(forecast.descriptor_model).toFixed(4) : "—");
        safeText($("#forecast-powerlaw"), forecast.budget_power_law != null ? Number(forecast.budget_power_law).toFixed(4) : "—");
        safeText($("#forecast-ownerbest"), forecast.owner_best_so_far != null ? Number(forecast.owner_best_so_far).toFixed(4) : "—");
        safeText($("#forecast-top"), forecast.leaderboard_top != null ? Number(forecast.leaderboard_top).toFixed(4) : "—");
        safeText($("#forecast-reading"), forecast.reading || "");
        const uniq = record.uniqueness || {};
        safeText($("#uniqueness-jaccard"), uniq.max_jaccard_vs_prior_submissions != null
          ? `${(uniq.max_jaccard_vs_prior_submissions * 100).toFixed(1)}% (closest: ${uniq.closest_prior_map})` : "—");
        const desc = record.descriptors || {};
        safeText($("#descriptor-dotting"), desc.spacing_proxy != null ? Number(desc.spacing_proxy).toFixed(3) : "—");
        safeText($("#descriptor-nearcat"), desc.frac_mass_within_3px_of_catalogue != null
          ? `${(desc.frac_mass_within_3px_of_catalogue * 100).toFixed(1)}%` : "—");

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
        const downloadZip = $("#candidate-download-zip");
        if (downloadZip) {
          if (ready) {
            const zipPath = record.download_path.replace(/\.tif$/, ".zip");
            downloadZip.href = zipPath;
            downloadZip.download = (record.filename || "gemsdoe37-candidate.tif").replace(/\.tif$/, ".zip");
            downloadZip.classList.remove("btn-disabled");
            downloadZip.removeAttribute("aria-disabled");
            downloadZip.setAttribute("aria-label", `Download ${record.filename}.zip`);
          } else {
            downloadZip.removeAttribute("href");
            downloadZip.classList.add("btn-disabled");
            downloadZip.setAttribute("aria-disabled", "true");
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
