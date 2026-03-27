const resumenInicial = window.RESUMEN_QR_INICIAL || {};

let estadoActual = resumenInicial.estado || "sin iniciar";
let trabajadoSeg = Number(
  resumenInicial.segundos_trabajados_reales ??
  resumenInicial.segundos_trabajados ??
  0
);
let netoSeg = Number(
  resumenInicial.segundos_netos_reales ??
  resumenInicial.segundos_netos ??
  0
);
let comidaSeg = Number(resumenInicial.segundos_comida ?? 0);
let descansoSeg = Number(resumenInicial.segundos_descanso ?? 0);

let intervaloCronometroQR = null;
let intervaloSyncQR = null;

function formatearTiempo(segundos) {
  segundos = Math.max(0, parseInt(segundos || 0, 10));

  const horas = Math.floor(segundos / 3600);
  const minutos = Math.floor((segundos % 3600) / 60);
  const segs = segundos % 60;

  return `${horas}h ${minutos}m ${segs}s`;
}

function actualizarVistaQR() {
  const estadoEl = document.getElementById("estado-qr");
  const tiempoEl = document.getElementById("tiempo-qr");
  const netoEl = document.getElementById("neto-qr");
  const comidaEl = document.getElementById("comida-qr");
  const descansoEl = document.getElementById("descanso-qr");

  if (estadoEl) {
    estadoEl.textContent = estadoActual;
  }

  if (tiempoEl) {
    tiempoEl.textContent = formatearTiempo(trabajadoSeg);
  }

  if (netoEl) {
    netoEl.textContent = formatearTiempo(netoSeg);
  }

  if (comidaEl) {
    comidaEl.textContent = formatearTiempo(comidaSeg);
  }

  if (descansoEl) {
    descansoEl.textContent = formatearTiempo(descansoSeg);
  }
}

function detenerCronometroQR() {
  if (intervaloCronometroQR) {
    clearInterval(intervaloCronometroQR);
    intervaloCronometroQR = null;
  }
}

function iniciarCronometroQR() {
  detenerCronometroQR();

  if (!["trabajando", "en comida", "en descanso"].includes(estadoActual)) {
    actualizarVistaQR();
    return;
  }

  intervaloCronometroQR = setInterval(() => {
    if (estadoActual === "trabajando") {
      trabajadoSeg += 1;
      netoSeg += 1;
    } else if (estadoActual === "en comida") {
      comidaSeg += 1;
    } else if (estadoActual === "en descanso") {
      descansoSeg += 1;
    }

    actualizarVistaQR();
  }, 1000);
}

async function cargarResumenQR() {
  const tokenInput = document.getElementById("token");
  if (!tokenInput) return;

  const token = tokenInput.value.trim();
  if (!token) return;

  try {
    const response = await fetch(`/api/qr_resumen?token=${encodeURIComponent(token)}`);
    const data = await response.json();

    if (!response.ok) {
      console.error(data.error || "No se pudo cargar el resumen QR.");
      return;
    }

    estadoActual = data.estado || "sin iniciar";
    trabajadoSeg = Number(data.segundos_trabajados_reales ?? data.segundos_trabajados ?? 0);
    netoSeg = Number(data.segundos_netos_reales ?? data.segundos_netos ?? 0);
    comidaSeg = Number(data.segundos_comida ?? 0);
    descansoSeg = Number(data.segundos_descanso ?? 0);

    actualizarVistaQR();
    iniciarCronometroQR();
  } catch (error) {
    console.error("Error cargando resumen QR:", error);
  }
}

async function marcarQr(tipo) {
  const pinInput = document.getElementById("pin");
  const tokenInput = document.getElementById("token");
  const mensaje = document.getElementById("mensaje");

  const pin = pinInput.value.trim();
  const token = tokenInput.value.trim();

  mensaje.textContent = "";

  if (!/^\d{4}$/.test(pin)) {
    mensaje.textContent = "El PIN debe tener exactamente 4 dígitos.";
    return;
  }

  try {
    const response = await fetch("/api/marcar_qr", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        token: token,
        pin: pin,
        tipo: tipo
      })
    });

    const data = await response.json();

    if (!response.ok) {
      mensaje.textContent = data.error || "No se pudo registrar la marcación.";
      return;
    }

    mensaje.textContent = data.mensaje || "Marcación registrada correctamente.";
    pinInput.value = "";
    pinInput.focus();

    await cargarResumenQR();
  } catch (error) {
    mensaje.textContent = "Error de conexión con el servidor.";
    console.error(error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  actualizarVistaQR();
  iniciarCronometroQR();

  if (intervaloSyncQR) {
    clearInterval(intervaloSyncQR);
  }

  intervaloSyncQR = setInterval(() => {
    cargarResumenQR();
  }, 60000);
}); 