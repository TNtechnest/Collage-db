function createChart(elementId, configBuilder) {
    const canvas = document.getElementById(elementId);
    if (!canvas) return;
    const labels = JSON.parse(canvas.dataset.labels || "[]");
    const values = JSON.parse(canvas.dataset.values || "[]");
    new Chart(canvas, configBuilder(labels, values));
}
createChart("attendanceTrendChart", (labels, values) => ({ type: "line", data: { labels, datasets: [{ label: "Attendance %", data: values, borderColor: "#2F3FAF", backgroundColor: "rgba(47, 63, 175, 0.12)", tension: 0.35, fill: true }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } }, plugins: { legend: { display: false } } } }));
createChart("studentDistributionChart", (labels, values) => ({ type: "doughnut", data: { labels, datasets: [{ data: values, backgroundColor: ["#2F3FAF", "#1F2937", "#D1D5DB", "#94A3B8"], borderWidth: 0 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } } }));
createChart("performanceChart", (labels, values) => ({ type: "bar", data: { labels, datasets: [{ label: "Average %", data: values, backgroundColor: ["#2F3FAF", "#1F2937", "#D1D5DB", "#64748B"], borderRadius: 10 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } }, plugins: { legend: { display: false } } } }));
createChart("monthlyPerformanceChart", (labels, values) => ({ type: "line", data: { labels, datasets: [{ label: "Performance %", data: values, borderColor: "#1F2937", backgroundColor: "rgba(31, 41, 55, 0.08)", tension: 0.35, fill: true }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } }, plugins: { legend: { display: false } } } }));
