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
})();
