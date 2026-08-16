/* downloader.js — talks to the existing Flask API:
 *   GET /terabox?url=<share_url>&pwd=<optional>
 *   GET /dl?url=<b64 dlink>&cookie=<b64 cookie>&filename=<n>
 * No backend changes needed — this only calls what already exists.
 * Streaming / "Watch Online" has been removed: download only.
 */

(function () {
  const form = document.getElementById("link-form");
  const input = document.getElementById("link-input");
  const submitBtn = document.getElementById("submit-btn");
  const btnLabel = submitBtn.querySelector(".btn-label");
  const btnSpinner = submitBtn.querySelector(".btn-spinner");

  const pwdToggle = document.getElementById("pwd-toggle");
  const pwdWrap = document.getElementById("pwd-input-wrap");
  const pwdInput = document.getElementById("pwd-input");

  const resultArea = document.getElementById("result-area");
  const resultContainer = document.getElementById("result-container");

  pwdToggle.addEventListener("click", () => {
    const willShow = pwdWrap.hidden;
    pwdWrap.hidden = !willShow;
    pwdToggle.textContent = willShow
      ? "Hide password field"
      : "This link is password protected";
    if (willShow) pwdInput.focus();
  });

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    btnLabel.hidden = isLoading;
    btnSpinner.hidden = !isLoading;
  }

  function looksLikeUrl(value) {
    return /^https?:\/\/.+/i.test(value.trim());
  }

  function showResultArea() {
    resultArea.hidden = false;
    resultArea.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderLoading() {
    showResultArea();
    resultContainer.innerHTML = `
      <div class="loading-card">
        <div class="loading-spinner"></div>
        <h3>Analyzing your link</h3>
        <p>Please wait while we retrieve the available files.</p>
      </div>`;
  }

  function renderState(icon, title, message) {
    showResultArea();
    resultContainer.innerHTML = `
      <div class="state-card error">
        <div class="state-icon">${icon}</div>
        <h3>${UI.escapeHtml(title)}</h3>
        <p>${UI.escapeHtml(message)}</p>
      </div>`;
  }

  function triggerDownload(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    if (filename) a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  function renderResults(data) {
    const files = Array.isArray(data.files) ? data.files : [];

    if (!files.length) {
      renderState(
        "🔍",
        "No files found",
        "The shared content may have been deleted, expired, or unavailable."
      );
      return;
    }

    const downloadableCount = files.filter((f) => !!f.download_link).length;

    const rows = files
      .map((f) => {
        const name = f.filename || "Unnamed file";
        const hasDownload = !!f.download_link;
        const thumb = f.thumbnail
          ? `<img class="file-thumb" src="${UI.escapeHtml(f.thumbnail)}" alt="">`
          : `<div class="file-icon">${UI.fileIcon(name)}</div>`;

        const downloadBtn = hasDownload
          ? `<a class="btn-primary" href="${UI.escapeHtml(f.download_link)}" download="${UI.escapeHtml(name)}">Download</a>`
          : `<span class="btn-disabled">Download unavailable</span>`;

        return `
          <div class="file-row">
            ${thumb}
            <div class="file-meta">
              <div class="file-name" title="${UI.escapeHtml(name)}">${UI.escapeHtml(name)}</div>
              <div class="file-size">${UI.formatBytes(f.size)}</div>
            </div>
            <div class="file-actions">
              ${downloadBtn}
            </div>
          </div>`;
      })
      .join("");

    const downloadAllBtn =
      files.length > 1 && downloadableCount > 1
        ? `<button type="button" class="btn-download-all" id="download-all-btn">Download all (${downloadableCount})</button>`
        : "";

    showResultArea();
    resultContainer.innerHTML = `
      <div class="result-card">
        <div class="result-header">
          <div class="result-header-text">
            <h3>Files found</h3>
            <span class="result-count">${files.length} file${files.length === 1 ? "" : "s"}</span>
          </div>
          ${downloadAllBtn}
        </div>
        <div class="file-list">${rows}</div>
      </div>`;

    const allBtn = document.getElementById("download-all-btn");
    if (allBtn) {
      allBtn.addEventListener("click", () => {
        allBtn.disabled = true;
        const originalText = allBtn.textContent;
        allBtn.textContent = "Starting downloads…";

        const downloadable = files.filter((f) => !!f.download_link);
        downloadable.forEach((f, i) => {
          setTimeout(() => {
            triggerDownload(f.download_link, f.filename || "download");
            if (i === downloadable.length - 1) {
              setTimeout(() => {
                allBtn.disabled = false;
                allBtn.textContent = originalText;
              }, 400);
            }
          }, i * 500);
        });
      });
    }
  }

  async function resolveLink(url, pwd) {
    const params = new URLSearchParams({ url });
    if (pwd) params.set("pwd", pwd);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    let res;
    try {
      res = await fetch(`/terabox?${params.toString()}`, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
    } catch (err) {
      clearTimeout(timeout);
      if (err.name === "AbortError") {
        renderState("⏱️", "Request timed out", "The remote server took too long to respond. Please try again.");
      } else {
        renderState("⚠️", "Unable to process this link", "Please check your connection and try again later.");
      }
      return;
    }
    clearTimeout(timeout);

    let data;
    try {
      data = await res.json();
    } catch {
      renderState("⚠️", "Unable to process this link", "Please try again later.");
      return;
    }

    if (!res.ok || data.status === "error") {
      renderState(
        "⚠️",
        "Unable to process this link",
        "The link may be invalid, private, expired, or temporarily unavailable."
      );
      return;
    }

    renderResults(data);
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const url = input.value.trim();

    if (!url || !looksLikeUrl(url)) {
      renderState(
        "🔗",
        "Invalid link",
        "The link doesn't appear to be a valid public share link. Please check the URL and try again."
      );
      return;
    }

    const pwd = pwdWrap.hidden ? "" : pwdInput.value.trim();

    setLoading(true);
    renderLoading();

    resolveLink(url, pwd).finally(() => setLoading(false));
  });
})();
