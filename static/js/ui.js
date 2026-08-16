/* ui.js — shared helpers (no page-specific logic here) */

const UI = {
  formatBytes(bytes) {
    const n = Number(bytes);
    if (!n || n <= 0) return "Unknown size";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    let val = n;
    while (val >= 1024 && i < units.length - 1) {
      val /= 1024;
      i++;
    }
    return `${val < 10 ? val.toFixed(1) : Math.round(val)} ${units[i]}`;
  },

  escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  },

  getExtension(filename) {
    if (!filename) return "";
    const parts = filename.split(".");
    return parts.length > 1 ? parts.pop().toLowerCase() : "";
  },

  VIDEO_EXTENSIONS: ["mp4", "mkv", "mov", "webm", "avi", "m4v", "3gp"],

  isVideo(filename) {
    return UI.VIDEO_EXTENSIONS.includes(UI.getExtension(filename));
  },

  fileIcon(filename) {
    const ext = UI.getExtension(filename);
    if (UI.isVideo(filename)) return "🎬";
    if (["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"].includes(ext)) return "🖼️";
    if (["mp3", "wav", "flac", "aac", "ogg", "m4a"].includes(ext)) return "🎵";
    if (["zip", "rar", "7z", "tar", "gz"].includes(ext)) return "📦";
    if (["pdf"].includes(ext)) return "📄";
    if (["doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"].includes(ext)) return "📃";
    return "📁";
  },
};
