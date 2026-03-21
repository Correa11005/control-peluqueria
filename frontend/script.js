const EMPLEADOS_FIJOS = [
  { empleado_id: 1, nombre: "Camilo" },
  { empleado_id: 2, nombre: "Ronald" },
  { empleado_id: 3, nombre: "Melany" }
];

const LIMITE_SEGUNDOS_MELANY = 4 * 3600;
let timers = {};

function formatear(segundos) {
  segundos = Math.max(0, parseInt(segundos || 0, 10));
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  return `${h}h ${m}m ${s}s`;
}

function limpiarTimers() {
  Object.values(timers).forEach(clearInterval);
  timers = {};
}

function toggleHistorial() {
  const panel = document.getElementById("panelHistorial");
  panel.classList.toggle("oculto");
}

function construirBaseTrabajadores(data) {
  return EMPLEADOS_FIJOS.map(empBase => {
    const encontrado = data.find(e => parseInt(e.empleado_id, 10) === empBase.empleado_id);

    if (encontrado) {
      return encontrado;
    }

    return {
      empleado_id: empBase.empleado_id,
      nombre: empBase.nombre,
      estado: "sin iniciar",
      neto: "0h 0m 0s",
      comida: "0h 0m 0s",
      descanso: "0h 0m 0s",
      segundos_netos: 0,
      segundos_comida: 0,
      segundos_descanso: 0
    };
  });
}

function crearTarjetaEmpleado(emp) {
  const card = document.createElement("div");
  card.className = "card-trabajador";

  const estadoClase = `estado-${String(emp.estado || "sin iniciar").replace(/\s+/g, "-")}`;
  card.classList.add(estadoClase);

  card.innerHTML = `
    <h3>${emp.nombre}</h3>
    <p class="estado"><strong>Estado:</strong> <span id="estado-${emp.empleado_id}">${emp.estado}</span></p>
    <p class="tiempo-principal" id="tiempo-${emp.empleado_id}">${formatear(emp.segundos_netos)}</p>
    <p><strong>Neto:</strong> <span id="neto-${emp.empleado_id}">${emp.neto}</span></p>
    <p><strong>Comida:</strong> <span id="comida-${emp.empleado_id}">${emp.comida}</span></p>
    <p><strong>Descanso:</strong> <span id="descanso-${emp.empleado_id}">${emp.descanso}</span></p>
  `;

  return card;
}

function iniciarCronometro(emp) {
  if (emp.estado !== "trabajando") return;

  let segundos = Math.max(0, parseInt(emp.segundos_netos || 0, 10));

  timers[emp.empleado_id] = setInterval(() => {
    if (emp.empleado_id === 3 && segundos >= LIMITE_SEGUNDOS_MELANY) {
      clearInterval(timers[emp.empleado_id]);
      return;
    }

    segundos++;

    const tiempoEl = document.getElementById(`tiempo-${emp.empleado_id}`);
    const netoEl = document.getElementById(`neto-${emp.empleado_id}`);

    if (tiempoEl) tiempoEl.innerText = formatear(segundos);
    if (netoEl) netoEl.innerText = formatear(segundos);
  }, 1000);
}

function renderizarTrabajadores(data) {
  const panel = document.getElementById("panelTrabajadores");
  panel.innerHTML = "";
  limpiarTimers();

  const empleados = construirBaseTrabajadores(data);

  empleados.forEach(emp => {
    const card = crearTarjetaEmpleado(emp);
    panel.appendChild(card);
    iniciarCronometro(emp);
  });
}

function cargarResumen() {
  fetch("/resumen_hoy")
    .then(async (res) => {
      if (!res.ok) throw new Error("No se pudo cargar el resumen");
      return res.json();
    })
    .then((data) => {
      renderizarTrabajadores(data);
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
      if (!res.ok) throw new Error("No se pudo cargar el historial");
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

window.addEventListener("load", () => {
  cargarResumen();
  setInterval(cargarResumen, 60000);
});