const form = document.getElementById("predictionForm");
const resultTitle = document.getElementById("resultTitle");
const resultMessage = document.getElementById("resultMessage");
const score = document.getElementById("score");
const scoreRing = document.getElementById("scoreRing");
const statusDot = document.getElementById("statusDot");

const demo = {
    daily_screen_time: 8.5,
    social_media_hours: 3.5,
    gaming_hours: 2.0,
    night_phone_usage: 2.2,
    sleep_hours: 5.8,
    notifications_per_day: 145,
    app_opens_per_day: 105
};

document.getElementById("demoBtn").addEventListener("click", () => {
    Object.entries(demo).forEach(([key, value]) => {
        document.querySelector(`[name="${key}"]`).value = value;
    });
});

document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-btn").forEach(x => x.classList.remove("active"));
        document.querySelectorAll(".section").forEach(x => x.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.section).classList.add("active");
        if (btn.dataset.section === "history") loadHistory();
    });
});

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    Object.keys(data).forEach(k => data[k] = Number(data[k]));

    const button = form.querySelector(".predict-btn");
    button.disabled = true;
    button.querySelector("span").textContent = "Analyzing...";

    try {
        const response = await fetch("/predict", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (!result.success) throw new Error(result.error);

        const pct = result.probability;
        score.textContent = `${pct}%`;
        scoreRing.style.background = `conic-gradient(${pct < 35 ? "#20d4b2" : pct < 65 ? "#f2b84b" : "#ff5d73"} ${pct * 3.6}deg, #252b3c ${pct * 3.6}deg)`;

        const cls = pct < 35 ? "low" : pct < 65 ? "moderate" : "high";
        statusDot.className = `status-dot ${cls}`;
        resultTitle.textContent = result.label;
        resultMessage.textContent =
            pct < 35 ? "The current usage profile shows a relatively low estimated risk."
            : pct < 65 ? "The current usage profile shows a moderate estimated risk. Consider reducing high-intensity usage."
            : "The current usage profile shows a high estimated risk. Consider healthier screen-time and sleep habits.";

        loadStats();
    } catch (err) {
        alert(err.message);
    } finally {
        button.disabled = false;
        button.querySelector("span").textContent = "Predict Risk";
    }
});

async function loadHistory() {
    const res = await fetch("/history");
    const rows = await res.json();
    const body = document.getElementById("historyBody");
    const empty = document.getElementById("emptyHistory");
    body.innerHTML = "";

    if (!rows.length) {
        empty.style.display = "block";
        return;
    }
    empty.style.display = "none";

    rows.forEach(r => {
        const cls = r.risk_label.startsWith("High") ? "high" :
                    r.risk_label.startsWith("Moderate") ? "moderate" : "low";
        body.innerHTML += `
            <tr>
                <td>${r.created_at}</td>
                <td>${r.daily_screen_time}h</td>
                <td>${r.social_media_hours}h</td>
                <td>${r.gaming_hours}h</td>
                <td>${r.sleep_hours}h</td>
                <td>${r.notifications_per_day}</td>
                <td>${r.app_opens_per_day}</td>
                <td><span class="badge ${cls}">${r.risk_label}</span></td>
                <td>${(r.probability * 100).toFixed(1)}%</td>
            </tr>`;
    });
}

async function loadStats() {
    const res = await fetch("/stats");
    const s = await res.json();
    document.getElementById("totalStat").textContent = s.total;
    document.getElementById("highStat").textContent = s.high_risk;
    document.getElementById("avgStat").textContent = `${s.average_probability}%`;
}
loadStats();

document.getElementById("clearHistory").addEventListener("click", async () => {
    if (!confirm("Delete all saved prediction history?")) return;
    await fetch("/clear-history", {method: "DELETE"});
    loadHistory();
    loadStats();
});
