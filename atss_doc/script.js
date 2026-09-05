(function () {
  "use strict";

  /* ---------- theme (in-memory, no persistence) ---------- */
  var root = document.documentElement;
  var themeBtn = document.getElementById("theme-toggle");
  var themeLabel = document.getElementById("theme-label");

  function setTheme(mode) {
    root.setAttribute("data-theme", mode);
    if (themeLabel) themeLabel.textContent = mode === "light" ? "Light" : "Dark";
  }
  setTheme("dark");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      setTheme(next);
    });
  }

  /* ---------- mobile sidebar ---------- */
  var sidebar = document.querySelector(".sidebar");
  var scrim = document.querySelector(".sidebar-scrim");
  var menuBtn = document.getElementById("menu-btn");

  function openSidebar() {
    sidebar.classList.add("open");
    scrim.classList.add("show");
  }
  function closeSidebar() {
    sidebar.classList.remove("open");
    scrim.classList.remove("show");
  }
  if (menuBtn) menuBtn.addEventListener("click", openSidebar);
  if (scrim) scrim.addEventListener("click", closeSidebar);
  document.querySelectorAll(".nav-link").forEach(function (a) {
    a.addEventListener("click", closeSidebar);
  });

  /* ---------- search ---------- */
  var searchInput = document.getElementById("search-input");
  var searchCount = document.getElementById("search-count");
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".nav-link"));
  var sections = Array.prototype.slice.call(document.querySelectorAll(".doc-section"));

  function normalize(s) {
    return s.toLowerCase();
  }

  function runSearch() {
    var q = normalize(searchInput.value.trim());
    if (!q) {
      navLinks.forEach(function (a) { a.classList.remove("hidden"); });
      sections.forEach(function (s) { s.style.display = ""; });
      searchCount.style.display = "none";
      return;
    }
    var matchCount = 0;
    sections.forEach(function (s) {
      var hay = normalize(s.dataset.title + " " + s.textContent);
      var match = hay.indexOf(q) !== -1;
      s.style.display = match ? "" : "none";
      var link = document.querySelector('.nav-link[data-num="' + s.dataset.num + '"]');
      if (link) link.classList.toggle("hidden", !match);
      if (match) matchCount++;
    });
    searchCount.style.display = "block";
    searchCount.textContent = matchCount + " of " + sections.length + " sections match";
  }
  if (searchInput) {
    searchInput.addEventListener("input", runSearch);
    searchInput.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        searchInput.value = "";
        runSearch();
        searchInput.blur();
      }
    });
  }

  /* keyboard shortcut: "/" focuses search */
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== searchInput) {
      e.preventDefault();
      searchInput.focus();
    }
  });

  /* ---------- active-section highlighting ---------- */
  var crumbCurrent = document.getElementById("crumb-current");

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var num = entry.target.dataset.num;
        navLinks.forEach(function (a) {
          a.classList.toggle("active", a.dataset.num === num);
        });
        if (crumbCurrent) crumbCurrent.textContent = entry.target.dataset.title;
      });
    },
    { rootMargin: "-15% 0px -75% 0px", threshold: 0 }
  );
  sections.forEach(function (s) { observer.observe(s); });

  /* ---------- wrap tables for horizontal scroll ---------- */
  document.querySelectorAll(".section-body table").forEach(function (table) {
    var wrap = document.createElement("div");
    wrap.className = "table-wrap";
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  });

  /* ---------- copy buttons on code blocks ---------- */
  document.querySelectorAll("pre").forEach(function (pre) {
    var codeEl = pre.querySelector("code");
    if (!codeEl) return;
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var text = codeEl.textContent;
      navigator.clipboard
        .writeText(text)
        .then(function () {
          btn.textContent = "Copied";
          btn.classList.add("copied");
          setTimeout(function () {
            btn.textContent = "Copy";
            btn.classList.remove("copied");
          }, 1400);
        })
        .catch(function () {
          btn.textContent = "Failed";
        });
    });
    pre.appendChild(btn);
  });

  /* ---------- mermaid diagrams ---------- */
  var mermaidBlocks = document.querySelectorAll("code.language-mermaid");
  if (mermaidBlocks.length && window.mermaid) {
    mermaidBlocks.forEach(function (code, i) {
      var wrap = document.createElement("div");
      wrap.className = "mermaid-wrap";
      var container = document.createElement("div");
      container.className = "mermaid";
      container.id = "mermaid-" + i;
      container.textContent = code.textContent;
      wrap.appendChild(container);
      var pre = code.closest("pre");
      pre.replaceWith(wrap);
    });
    try {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        themeVariables: {
          background: "#0d0f14",
          primaryColor: "#1a1d25",
          primaryTextColor: "#e7e8ec",
          primaryBorderColor: "#ff9000",
          lineColor: "#9297a6",
          secondaryColor: "#262a35",
          tertiaryColor: "#12141a"
        }
      });
      window.mermaid.run({ querySelector: ".mermaid" });
    } catch (e) {
      /* mermaid failed to load/render — raw diagram text remains visible */
    }
  }

  /* ---------- syntax highlighting ---------- */
  if (window.hljs) {
    document.querySelectorAll("pre code:not(.language-mermaid)").forEach(function (block) {
      window.hljs.highlightElement(block);
    });
  }

  /* ---------- back-to-top ---------- */
  var backTop = document.getElementById("back-top");
  window.addEventListener("scroll", function () {
    backTop.classList.toggle("show", window.scrollY > 600);
  });
  backTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();
