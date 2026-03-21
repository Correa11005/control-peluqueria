let timersResumen = {};
let timerSeleccionado = null;
let ultimoResumen = [];

const LIMITE_SEGUNDOS_MELANY = 4 * 3600;

function formatear(segundos) {
  segundos = Math.max(0, parseInt(segundos || 0, 10));
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  return `${h}h ${m}m ${s}s`;
}

function limpiarTimersResumen() {
  Object.values(timersResumen).forEach(clearInterval);
  timersResumen = {};
}

function limpiarTimerSeleccionado() {
  if (timerSeleccionado) {
    clearInterval(timerSeleccionado);
    timerSeleccionado = null;
  }
}

function toggleHistorial() {
  const panel = document.getElementById("panelHistorial");
  panel.classList.toggle("oculto");
}

function cargarHistorial() {
  const empleadoId = document.getElementById("filtro_empleado").value;
  const fecha = document.getElementById("filtro_fecha").value;
  const contenedor = document.getElementById("historial");

  contenedor.innerHTML = "<p>Cargando historial...</p>";

  const params = new URLSearchParams();
  if (empleadoId) params.append("empleado_id", empleadoId);
  if (fecha) params.append("fecha", fecha);

  const url = params.toString() ? `/historial?${params.toString()}` : "/historial";

  fetch(url)
    .then(async (res) => {
      if (!res.ok) {
        throw new Error("No se pudo cargar el historial");
      }
      return res.json();
    })
    .then((data) => {
      if (!data.length) {
        contenedor.innerHTML = "<p>No hay registros para mostrar.</p>";
        return;
      }

      let html = `
        <table border="1" cellpadding="8" cellspacing="0" style="width:100%; border-collapse:collapse; margin-top:20px;">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Empleado</th>
              <th>Entrada</th>
              <th>Salida</th>
              <th>Inicio comida</th>
              <th>Fin comida</th>
              <th>Inicio descanso</th>
              <th>Fin descanso</th>
              <th>Trabajado</th>
              <th>Comida</th>
              <th>Descanso</th>
              <th>Neto</th>
            </tr>
          </thead>
          <tbody>
      `;

      data.forEach((item) => {
        html += `
          <tr>
            <td>${item.fecha}</td>
            <td>${item.nombre}</td>
            <td>${item.entrada}</td>
            <td>${item.salida}</td>
            <td>${item.inicio_comida}</td>
            <td>${item.fin_comida}</td>
            <td>${item.inicio_descanso}</td>
            <td>${item.fin_descanso}</td>
            <td>${item.trabajado}</td>
            <td>${item.comida}</td>
            <td>${item.descanso}</td>
            <td>${item.neto}</td>
          </tr>
        `;
      });

      html += "</tbody></table>";
      contenedor.innerHTML = html;
    })
    .catch((error) => {
      console.error(error);
      contenedor.innerHTML = `<p>${error.message}</p>`;
    });
}

function iniciarTimerCard(emp, tiempoId) {
  if (emp.estado !== "trabajando") return;

  let segundos = Math.max(0, parseInt(emp.segundos_netos || 0, 10));

  timersResumen[emp.empleado_id] = setInterval(() => {
    if (emp.empleado_id === 3 && segundos >= LIMITE_SEGUNDOS_MELANY) {
      clearInterval(timersResumen[emp.empleado_id]);
      return;
    }

    segundos++;
    const elementoTiempo = document.getElementById(tiempoId);
    if (elementoTiempo) {
      elementoTiempo.innerText = formatear(segundos);
    }
  }, 1000);
}

function renderizarCardsResumen(data) {
  const panel = document.getElementById("panel");
  panel.innerHTML = "";
  limpiarTimersResumen();

  data.forEach((emp) => {
    const card = document.createElement("div");
    card.className = "card";

    const claseEstado = `estado-${emp.estado.replace(/\s+/g, "-")}`;
    card.classList.add(claseEstado);

    const nombre = document.createElement("h3");
    nombre.textContent = emp.nombre;

    const estado = document.createElement("p");
    estado.innerHTML = `<strong>Estado:</strong> ${emp.estado}`;

    const tiempoId = `tiempo-${emp.empleado_id}`;
    const tiempo = document.createElement("p");
    tiempo.className = "tiempo";
    tiempo.id = tiempoId;
    tiempo.textContent = formatear(emp.segundos_netos || 0);

    const detalle = document.createElement("p");
    detalle.innerHTML = `
      <strong>Neto:</strong> ${emp.neto}<br>
      <strong>Comida:</strong> ${emp.comida}<br>
      <strong>Descanso:</strong> ${emp.descanso}
    `;

    card.appendChild(nombre);
    card.appendChild(estado);
    card.appendChild(tiempo);
    card.appendChild(detalle);
    panel.appendChild(card);

    iniciarTimerCard(emp, tiempoId);
  });
}

function actualizarVistaEmpleadoSeleccionado() {
  const select = document.getElementById("empleado_id");
  const estadoEl = document.getElementById("estadoEmpleadoSeleccionado");
  const cronometroEl = document.getElementById("cronometroEmpleado");
  const detalleEl = document.getElementById("detalleEmpleadoSeleccionado");

  limpiarTimerSeleccionado();

  if (!select || !select.value) {
    estadoEl.innerText = "Estado: sin iniciar";
    cronometroEl.innerText = "0h 0m 0s";
    detalleEl.innerText = "Neto: 0h 0m 0s | Comida: 0h 0m 0s | Descanso: 0h 0m 0s";
    return;
  }

  const empleadoId = parseInt(select.value, 10);
  const emp = ultimoResumen.find((item) => item.empleado_id === empleadoId);

  if (!emp) {
    estadoEl.innerText = "Estado: sin datos";
    cronometroEl.innerText = "0h 0m 0s";
    detalleEl.innerText = "Neto: 0h 0m 0s | Comida: 0h 0m 0s | Descanso: 0h 0m 0s";
    return;
  }

  estadoEl.innerText = `Estado: ${emp.estado}`;
  cronometroEl.innerText = formatear(emp.segundos_netos || 0);
  detalleEl.innerText = `Neto: ${emp.neto} | Comida: ${emp.comida} | Descanso: ${emp.descanso}`;

  if (emp.estado === "trabajando") {
    let segundos = Math.max(0, parseInt(emp.segundos_netos || 0, 10));

    timerSeleccionado = setInterval(() => {
      if (emp.empleado_id === 3 && segundos >= LIMITE_SEGUNDOS_MELANY) {
        clearInterval(timerSeleccionado);
        return;
      }

      segundos++;
      cronometroEl.innerText = formatear(segundos);
    }, 1000);
  }
}

function cargarResumen() {
  fetch("/resumen_hoy")
    .then(async (res) => {
      if (!res.ok) {
        throw new Error("No se pudo cargar el resumen");
      }
      return res.json();
    })
    .then((data) => {
      ultimoResumen = data;
      renderizarCardsResumen(data);
      actualizarVistaEmpleadoSeleccionado();
      document.getElementById("mensaje").innerText = "";
    })
    .catch((error) => {
      console.error(error);
      document.getElementById("mensaje").innerText = "No se pudo cargar el resumen de hoy.";
    });
}

function marcar(tipo) {
  const empleadoSelect = document.getElementById("empleado_id");
  const empleado_id = empleadoSelect.value;
  const mensaje = document.getElementById("mensaje");

  if (!empleado_id) {
    mensaje.innerText = "Selecciona un empleado.";
    return;
  }

  mensaje.innerText = "Registrando...";

  fetch("/marcar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      empleado_id: parseInt(empleado_id, 10),
      tipo: tipo
    })
  })
    .then(async (res) => {
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "No se pudo registrar la marcación");
      }

      return data;
    })
    .then(() => {
      const textos = {
        entrada: "ya está empezando la labor",
        salida: "ha finalizado la jornada",
        inicio_comida: "inició su tiempo de comida",
        fin_comida: "finalizó su tiempo de comida",
        inicio_descanso: "inició su descanso",
        fin_descanso: "finalizó su descanso"
      };

      const nombre = empleadoSelect.options[empleadoSelect.selectedIndex].text;
      mensaje.innerText = `${nombre} ${textos[tipo]}.`;

      cargarResumen();
    })
    .catch((error) => {
      console.error(error);
      mensaje.innerText = error.message || "Error de conexión.";
    });
}

window.addEventListener("load", () => {
  cargarResumen();

  const selectEmpleado = document.getElementById("empleado_id");
  if (selectEmpleado) {
    selectEmpleado.addEventListener("change", actualizarVistaEmpleadoSeleccionado);
  }
});