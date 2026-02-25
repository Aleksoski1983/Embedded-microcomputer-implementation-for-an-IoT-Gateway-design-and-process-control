(function () {
  const apiBase = "http://" + location.hostname + ":8080";

  const el = (id) => document.getElementById(id);
  const fmtUptime = (ms) => {
    const s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    if (h > 0) return `${h}h ${m}m ${ss}s`;
    if (m > 0) return `${m}m ${ss}s`;
    return `${ss}s`;
  };

  function badge(text, kind) {
    const cls = kind === "ok" ? "badge ok" : kind === "warn" ? "badge warn" : "badge bad";
    return `<span class="${cls}">${text}</span>`;
  }

  async function loadConfig() {
    try {
      const r = await fetch(apiBase + "/api/config", { cache: "no-store" });
      const j = await r.json();
      const mqtt = j.mqtt || {};
      el("mqttEnabled").checked = !!mqtt.enabled;
      el("broker").value = mqtt.broker_ip || "";
      el("topic").value = mqtt.topic || "";
    } catch (e) {
      // ignore
    }
  }

  async function loadData() {
    try {
      const r = await fetch(apiBase + "/api/data", { cache: "no-store" });
      const j = await r.json();

      el("uptime").textContent = fmtUptime(j.uptime_ms || 0);
      el("ip").textContent = (j.wifi && j.wifi.ip) || "--";

      if (j.sensor && j.sensor.valid) {
        el("temp").textContent = `${j.sensor.temperature_c.toFixed(1)} °C`;
        el("hum").textContent = `${j.sensor.humidity_percent.toFixed(1)} %`;
      } else {
        el("temp").textContent = "--";
        el("hum").textContent = "--";
      }

      const mqtt = j.mqtt || {};
      if (!mqtt.enabled) {
        el("mqttStatus").innerHTML = badge("Disabled", "bad");
      } else if (mqtt.connected) {
        el("mqttStatus").innerHTML = badge("Connected", "ok");
      } else if (mqtt.state === "connecting") {
        el("mqttStatus").innerHTML = badge("Connecting", "warn");
      } else {
        el("mqttStatus").innerHTML = badge("Disconnected", "bad");
      }
    } catch (e) {
      el("mqttStatus").innerHTML = badge("API offline", "bad");
    }
  }

  async function saveConfig() {
    el("save").disabled = true;
    el("saveMsg").textContent = "Saving...";

    const payload = {
      mqtt: {
        enabled: el("mqttEnabled").checked,
        broker_ip: (el("broker").value || "").trim(),
        topic: (el("topic").value || "").trim(),
      },
    };

    // Server expects flat keys too; keep both (safe for our minimal parser).
    const flatPayload = {
      enabled: payload.mqtt.enabled,
      broker_ip: payload.mqtt.broker_ip,
      topic: payload.mqtt.topic,
    };

    try {
      const r = await fetch(apiBase + "/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(flatPayload),
      });

      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.ok) {
        el("saveMsg").textContent = (j && j.error) ? `Error: ${j.error}` : `Error (${r.status})`;
        el("save").disabled = false;
        return;
      }

      el("saveMsg").textContent = "Saved. Rebooting...";

      // Give the Pico time to reboot; then refresh config + data.
      setTimeout(() => {
        el("save").disabled = false;
        el("saveMsg").textContent = "";
        loadConfig();
      }, 7000);

    } catch (e) {
      el("saveMsg").textContent = "Save failed (API unreachable)";
      el("save").disabled = false;
    }
  }

  el("save").addEventListener("click", saveConfig);

  loadConfig();
  loadData();
  setInterval(loadData, 2000);
})();
