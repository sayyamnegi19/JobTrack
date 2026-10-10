/* ==========================================================================
   JobTrack — chart helpers (Chart.js).

   Loaded on pages that render charts, before the page's init script.
   Keeps charts on-brand and re-themes them when the dark/light toggle fires
   (the theme toggle dispatches "jt:theme-changed").
   ========================================================================== */

(function () {
    "use strict";

    var registry = [];

    function themeColors() {
        var styles = getComputedStyle(document.documentElement);
        return {
            text: styles.getPropertyValue("--bs-body-color").trim() || "#212529",
            muted: styles.getPropertyValue("--bs-secondary-color").trim() || "#6c757d",
            border: styles.getPropertyValue("--bs-border-color").trim() || "#dee2e6",
            primary: "#6366f1",
            violet: "#8b5cf6",
            gradientFill: "rgba(139, 92, 246, 0.18)",
        };
    }

    function applyDefaults() {
        if (typeof Chart === "undefined") {
            return;
        }
        var colors = themeColors();
        Chart.defaults.font.family =
            '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
        Chart.defaults.font.size = 12;
        Chart.defaults.color = colors.muted;
        Chart.defaults.borderColor = colors.border;
    }

    function register(chart) {
        registry.push(chart);
    }

    function retheme() {
        if (typeof Chart === "undefined") {
            return;
        }

        var colors = themeColors();
        Chart.defaults.color = colors.muted;
        Chart.defaults.borderColor = colors.border;

        registry.forEach(function (chart) {
            var scales = chart.options.scales || {};

            Object.keys(scales).forEach(function (key) {
                var scale = scales[key];

                if (scale.ticks) {
                    scale.ticks.color = colors.muted;
                    if (key === "r") {
                        scale.ticks.backdropColor = "transparent";
                    }
                }
                if (scale.grid) {
                    scale.grid.color = colors.border;
                }
                if (scale.angleLines) {
                    scale.angleLines.color = colors.border;
                }
                if (scale.pointLabels) {
                    scale.pointLabels.color = colors.muted;
                }
            });

            chart.update();
        });
    }

    window.addEventListener("jt:theme-changed", retheme);

    window.jtCharts = {
        themeColors: themeColors,
        applyDefaults: applyDefaults,
        register: register,
    };

    applyDefaults();
})();
