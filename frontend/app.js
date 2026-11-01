const API_BASE = "/api";

const form = document.getElementById("search-form");
const cityInput = document.getElementById("city-input");
const weatherDiv = document.getElementById("weather");
const errorDiv = document.getElementById("error");
const historyDiv = document.getElementById("history");

const WEATHER_EMOJI = {
  0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
  45: "🌫️", 48: "🌫️",
  51: "🌦️", 53: "🌦️", 55: "🌧️",
  61: "🌧️", 63: "🌧️", 65: "⛈️",
  71: "🌨️", 73: "🌨️", 75: "❄️",
  80: "🌧️", 81: "🌧️", 82: "⛈️",
  95: "⛈️", 96: "⛈️", 99: "⛈️",
};

function showError(msg) {
  errorDiv.textContent = msg;
  errorDiv.classList.remove("hidden");
}

function hideError() {
  errorDiv.classList.add("hidden");
}

async function fetchWeather(city) {
  hideError();
  weatherDiv.classList.add("hidden");

  try {
    const resp = await fetch(`${API_BASE}/weather?city=${encodeURIComponent(city)}`);
    const data = await resp.json();

    if (!resp.ok) {
      showError(data.error || "Ошибка запроса");
      return;
    }

    const emoji = WEATHER_EMOJI[data.weather_code] || "🌡️";
    weatherDiv.innerHTML = `
      <div class="city">${emoji} ${data.city}, ${data.country}</div>
      <div class="temp">${data.temperature}°C</div>
      <div>${data.description}</div>
      <div class="meta">
        <span>💧 Влажность: ${data.humidity}%</span>
        <span>💨 Ветер: ${data.wind_speed} км/ч</span>
      </div>
    `;
    weatherDiv.classList.remove("hidden");
    loadHistory();
  } catch (e) {
    showError("Не удалось подключиться к серверу");
  }
}

async function loadHistory() {
  try {
    const resp = await fetch(`${API_BASE}/history`);
    const data = await resp.json();
    if (!Array.isArray(data) || data.length === 0) {
      historyDiv.innerHTML = "<div class='history-item'>Пока нет запросов</div>";
      return;
    }
    historyDiv.innerHTML = data
      .map(
        (r) => `
        <div class="history-item">
          <span>${r.city} — ${r.description}</span>
          <span>${r.temperature}°C · ${new Date(r.created_at).toLocaleString("ru-RU")}</span>
        </div>`
      )
      .join("");
  } catch (e) {
    console.error(e);
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const city = cityInput.value.trim();
  if (city) fetchWeather(city);
});

loadHistory();
