/* faq.js — search + category filtering for the FAQ page only.
   Does not touch downloader logic or any API calls. */

(function () {
  const searchInput = document.getElementById("faq-search");
  const catButtons = document.querySelectorAll(".faq-cat-btn");
  const items = document.querySelectorAll("#faq-list .faq-item");
  const emptyState = document.getElementById("faq-empty");

  if (!searchInput || !items.length) return;

  let activeCat = "all";

  function applyFilter() {
    const query = searchInput.value.trim().toLowerCase();
    let visibleCount = 0;

    items.forEach((item) => {
      const cat = item.getAttribute("data-cat") || "general";
      const text = item.textContent.toLowerCase();

      const matchesCat = activeCat === "all" || cat === activeCat;
      const matchesQuery = !query || text.includes(query);
      const visible = matchesCat && matchesQuery;

      item.hidden = !visible;
      if (visible) visibleCount++;
    });

    if (emptyState) emptyState.hidden = visibleCount !== 0;
  }

  searchInput.addEventListener("input", applyFilter);

  catButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      catButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeCat = btn.getAttribute("data-cat") || "all";
      applyFilter();
    });
  });
})();
