// main.js — students will add JavaScript here as features are built

document.addEventListener("DOMContentLoaded", function () {
    var quickButtons = document.querySelectorAll(".profile-filter-quick-btn");
    var filterForm = document.querySelector(".profile-filter");
    var startInput = document.getElementById("start_date");
    var endInput = document.getElementById("end_date");

    if (!quickButtons.length || !filterForm || !startInput || !endInput) {
        return;
    }

    function formatDate(date) {
        var year = date.getFullYear();
        var month = String(date.getMonth() + 1).padStart(2, "0");
        var day = String(date.getDate()).padStart(2, "0");
        return year + "-" + month + "-" + day;
    }

    quickButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            var months = parseInt(button.dataset.months, 10);

            if (months === 0) {
                startInput.value = "";
                endInput.value = "";
            } else {
                var today = new Date();
                // Align to calendar months: "3 Months" means the 1st of the
                // month 2 months back through today, i.e. 3 whole calendar
                // months including the current one — not a rolling 90-day
                // window from today's exact date.
                var start = new Date(today.getFullYear(), today.getMonth() - (months - 1), 1);
                startInput.value = formatDate(start);
                endInput.value = formatDate(today);
            }

            filterForm.submit();
        });
    });
});
