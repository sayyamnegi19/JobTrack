/* ==========================================================================
   JobTrack — shared behaviors. Plain JS, no build step.

   1. Toast messages (Django messages framework)
   2. Submit feedback for forms marked with [data-loading]
   3. Password visibility toggles ([data-toggle-password])
   ========================================================================== */

(function () {
    "use strict";

    // 1. Toast messages ----------------------------------------------------
    document.querySelectorAll(".toast").forEach(function (toastEl) {
        new bootstrap.Toast(toastEl).show();
    });

    // 2. Submit feedback ---------------------------------------------------
    // Usage: <form data-loading> with a submit button optionally carrying
    // data-loading-text="Saving…". The button is disabled and gets a spinner
    // so slow requests (AI analysis, searches) always feel responsive.
    document.querySelectorAll("form[data-loading]").forEach(function (form) {
        form.addEventListener("submit", function () {
            var button = form.querySelector('[type="submit"]');
            if (!button || button.disabled) {
                return;
            }

            button.disabled = true;

            var label = button.getAttribute("data-loading-text") || "Please wait…";
            button.innerHTML =
                '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
                label;
        });
    });

    // 3. Password visibility toggles ----------------------------------------
    document.querySelectorAll("[data-toggle-password]").forEach(function (toggle) {
        toggle.addEventListener("click", function () {
            var input = document.querySelector(
                toggle.getAttribute("data-toggle-password")
            );
            if (!input) {
                return;
            }

            var show = input.type === "password";
            input.type = show ? "text" : "password";
            toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");

            var icon = toggle.querySelector("i");
            if (icon) {
                icon.classList.toggle("bi-eye", !show);
                icon.classList.toggle("bi-eye-slash", show);
            }
        });
    });

    // 4. Theme toggle ---------------------------------------------------------
    // The no-flash <head> script already set data-bs-theme; this wires the
    // toggle buttons, persists the choice and follows the OS while unchosen.
    (function () {
        var root = document.documentElement;
        var toggles = document.querySelectorAll("[data-theme-toggle]");
        var media = window.matchMedia("(prefers-color-scheme: dark)");

        function currentTheme() {
            return root.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
        }

        function syncToggles() {
            var dark = currentTheme() === "dark";

            toggles.forEach(function (toggle) {
                var icon = toggle.querySelector("i");
                if (icon) {
                    icon.className = dark ? "bi bi-sun" : "bi bi-moon-stars";
                }
                toggle.setAttribute("aria-pressed", dark ? "true" : "false");
                toggle.setAttribute(
                    "aria-label",
                    dark ? "Switch to light mode" : "Switch to dark mode"
                );
            });
        }

        function applyTheme(theme, persist) {
            root.setAttribute("data-bs-theme", theme);

            if (persist) {
                try {
                    localStorage.setItem("jt-theme", theme);
                } catch (e) { /* private mode — nothing to persist */ }
            }

            syncToggles();

            // Charts and other widgets listen for this and re-theme.
            window.dispatchEvent(
                new CustomEvent("jt:theme-changed", { detail: { theme: theme } })
            );
        }

        toggles.forEach(function (toggle) {
            toggle.addEventListener("click", function () {
                applyTheme(currentTheme() === "dark" ? "light" : "dark", true);
            });
        });

        media.addEventListener("change", function (event) {
            var stored = null;
            try {
                stored = localStorage.getItem("jt-theme");
            } catch (e) { /* ignore */ }

            if (!stored) {
                applyTheme(event.matches ? "dark" : "light", false);
            }
        });

        syncToggles();
    })();

    // 5. Scroll & motion ------------------------------------------------------
    (function () {
        var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        // Navbar shadow after scrolling.
        var navbar = document.querySelector(".navbar");
        if (navbar) {
            var onScroll = function () {
                navbar.classList.toggle("jt-scrolled", window.scrollY > 8);
            };
            window.addEventListener("scroll", onScroll, { passive: true });
            onScroll();
        }

        // Reveal-on-scroll with a small stagger per batch.
        var revealEls = document.querySelectorAll(".jt-reveal");
        if (revealEls.length) {
            if (reduced || !("IntersectionObserver" in window)) {
                revealEls.forEach(function (el) {
                    el.classList.add("jt-reveal-visible");
                });
            } else {
                var revealObserver = new IntersectionObserver(function (entries) {
                    var batch = entries.filter(function (entry) {
                        return entry.isIntersecting;
                    });

                    batch.forEach(function (entry, index) {
                        var el = entry.target;
                        el.style.transitionDelay = index * 70 + "ms";
                        el.classList.add("jt-reveal-visible");
                        revealObserver.unobserve(el);
                    });
                }, { threshold: 0.12, rootMargin: "0px 0px -36px 0px" });

                revealEls.forEach(function (el) {
                    revealObserver.observe(el);
                });
            }
        }

        // Count-up numbers (progressive enhancement: real value is in HTML).
        document.querySelectorAll("[data-countup]").forEach(function (el) {
            var target = parseInt(el.getAttribute("data-countup"), 10);
            if (isNaN(target)) {
                return;
            }
            if (reduced) {
                el.textContent = String(target);
                return;
            }

            var duration = 800;
            var started = null;

            var run = function (timestamp) {
                if (started === null) {
                    started = timestamp;
                }
                var progress = Math.min((timestamp - started) / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3);
                el.textContent = String(Math.round(target * eased));
                if (progress < 1) {
                    window.requestAnimationFrame(run);
                }
            };

            el.textContent = "0";
            window.requestAnimationFrame(run);
        });

        // Progress bars grow from 0 to their data-progress value.
        document.querySelectorAll("[data-progress]").forEach(function (bar) {
            var target = bar.getAttribute("data-progress") + "%";

            if (reduced) {
                bar.style.width = target;
                return;
            }

            bar.style.width = "0%";
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    bar.style.width = target;
                });
            });
        });
    })();

    // 6. Segmented tabs (progressive enhancement) -----------------------------
    // Without JS every panel stays visible (like a plain stacked form); with
    // JS, switching tabs clears the other panels' inputs so "multiple resume
    // sources" can never be submitted.
    document.querySelectorAll("[data-tabs]").forEach(function (tabs) {
        tabs.classList.add("jt-tabs-ready");

        var buttons = tabs.querySelectorAll("[data-tab-target]");
        var panels = tabs.querySelectorAll("[data-tab-panel]");

        function clearPanel(panel) {
            panel.querySelectorAll("input, select, textarea").forEach(function (input) {
                if (input.type === "file" || input.type === "checkbox" || input.type === "radio") {
                    input.value = "";
                    input.checked = false;
                } else {
                    input.value = "";
                }
            });
        }

        function activate(target) {
            buttons.forEach(function (button) {
                var isActive = button.getAttribute("data-tab-target") === target;
                button.classList.toggle("active", isActive);
                button.setAttribute("aria-selected", isActive ? "true" : "false");
            });

            panels.forEach(function (panel) {
                var isActive = panel.getAttribute("data-tab-panel") === target;
                panel.classList.toggle("active", isActive);
                if (!isActive) {
                    clearPanel(panel);
                }
            });
        }

        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                activate(button.getAttribute("data-tab-target"));
            });
        });
    });

    // 7. Form error affordances -----------------------------------------------
    document.querySelectorAll(".jt-field").forEach(function (field) {
        if (field.querySelector(".jt-field-error")) {
            var input = field.querySelector("input, select, textarea");
            if (input) {
                input.setAttribute("aria-invalid", "true");
            }
        }
    });

    var firstError = document.querySelector(".jt-field-error");
    if (firstError) {
        var errorField = firstError.closest(".jt-field");
        if (errorField) {
            errorField.scrollIntoView({
                block: "center",
                behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
                    ? "auto"
                    : "smooth",
            });
        }
    }
})();
