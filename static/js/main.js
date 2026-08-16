/* main.js — global UI interactions (nav, scroll-reveal) not specific to the downloader */

(function () {
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("main-nav");

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("open");
      toggle.classList.toggle("open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
    });

    nav.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", () => {
        nav.classList.remove("open");
        toggle.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }
})();

/* Scroll reveal for .reveal sections — staggers children (.step, .feature-card,
   .hiw-row, .disclaimer-block, etc.) one after another instead of popping in
   all at once. */
(function () {
  const targets = document.querySelectorAll(".reveal");
  if (!targets.length) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    targets.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );

  targets.forEach((el) => observer.observe(el));
})();

/* Fade the page in on load (pairs with the cross-document @view-transition
   rule in base.html for browsers that support it; harmless no-op fade
   elsewhere). Respects prefers-reduced-motion. */
(function () {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  requestAnimationFrame(() => {
    document.body.classList.remove("page-enter");
  });
  if (prefersReducedMotion) document.body.classList.remove("page-enter");
})();

/* Animated <details>/<summary> accordions (.accordion-item). Keeps native
   semantics (keyboard + screen reader support) but replaces the instant
   open/close with a smooth height + fade transition. Used on Help and FAQ. */
(function () {
  const items = document.querySelectorAll(".accordion-item");
  if (!items.length) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  items.forEach((item) => {
    const body = item.querySelector(".accordion-body");
    if (!body) return;

    if (prefersReducedMotion) {
      // Let the browser handle it natively, no animation.
      return;
    }

    let animation = null;

    const setOpenHeight = () => `${body.scrollHeight}px`;

    item.addEventListener("click", (e) => {
      const summary = item.querySelector("summary");
      if (!summary || !summary.contains(e.target)) return;
      e.preventDefault();

      if (animation) animation.cancel();

      if (item.open) {
        // Closing.
        const startHeight = `${body.scrollHeight}px`;
        animation = body.animate(
          [{ height: startHeight, opacity: 1 }, { height: "0px", opacity: 0 }],
          { duration: 240, easing: "cubic-bezier(.4,0,.2,1)" }
        );
        animation.onfinish = () => { item.open = false; };
      } else {
        // Opening.
        item.open = true;
        const endHeight = setOpenHeight();
        animation = body.animate(
          [{ height: "0px", opacity: 0 }, { height: endHeight, opacity: 1 }],
          { duration: 260, easing: "cubic-bezier(.4,0,.2,1)" }
        );
      }
    });
  });
})();

/* Hero 3D scene — subtle cursor-follow parallax on desktop, disabled on
   touch devices and when prefers-reduced-motion is set. Pure CSS transform,
   no library. */
(function () {
  const stage = document.getElementById("scene-stage");
  if (!stage) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isCoarsePointer = window.matchMedia("(pointer: coarse)").matches;
  if (prefersReducedMotion || isCoarsePointer) return;

  const scene = document.getElementById("hero-scene");
  let rafId = null;
  let targetX = 0, targetY = 0, currentX = 0, currentY = 0;

  function loop() {
    currentX += (targetX - currentX) * 0.08;
    currentY += (targetY - currentY) * 0.08;
    stage.style.transform = `rotateY(${currentX}deg) rotateX(${currentY}deg)`;
    rafId = requestAnimationFrame(loop);
  }

  scene.addEventListener("mousemove", (e) => {
    const rect = scene.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    targetX = px * 14;
    targetY = py * -10;
  });

  scene.addEventListener("mouseleave", () => {
    targetX = 0;
    targetY = 0;
  });

  rafId = requestAnimationFrame(loop);
})();
