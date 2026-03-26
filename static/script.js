const EMPLEADOS_FIJOS = [
  { empleado_id: 1, nombre: "Camilo" },
  { empleado_id: 2, nombre: "Ronald" },
  { empleado_id: 3, nombre: "Melany" }
];

const timers = {};
const LIMITE_SEGUNDOS_MELANY = 4 * 3600;

function formatear(segundos) {
  segundos = Math.max(0, parseInt(segundos || 0, 10));
  const horas = Math.floor(segundos / 3600);
  const minutos = Math.floor((segundos % 3600) / 60);
  const segs = segundos % 60;
  return `${horas}h ${minutos}m ${segs}s`;
}

function aplicarLogicaMelany(segundosReales) {
  segundosReales = Math.max(0, parseInt(segundosReales || 0, 10));

  if (segundosReales < LIMITE_SEGUNDOS_MELANY) {
    return segundosReales;
  }

  return 3 * 3600 + ((segundosReales - LIMITE_SEGUNDOS_MELANY) % 3600);
}

function limpiarTimers() {
  Object.values(timers).forEach((timer) => clearInterval(timer));
  Object.keys(timers).forEach((key) => delete timers[key]);
}

function construirBaseTrabajadores(data) {
  return EMPLEADOS_FIJOS.map((empBase) => {
    const encontrado = data.find(
      (e) => parseInt(e.empleado_id, 10) === empBase.empleado_id
    );

    if (encontrado) {
      return encontrado;
    }

    return {
      empleado_id: empBase.empleado_id,
      nombre: empBase.nombre,
      estado: "sin iniciar",
      trabajado: "0h 0m 0s",
      neto: "0h 0m 0s",
      comida: "0h 0m 0s",
      descanso: "0h 0m 0s",
      segundos_trabajados: 0,
      segundos_trabajados_reales: 0,
      segundos_netos: 0,
      segundos_netos_reales: 0,
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

  const tiempoPrincipal = emp.trabajado || formatear(emp.segundos_trabajados || 0);

  card.innerHTML = `
    <h3>${emp.nombre}</h3>
    <p class="estado"><strong>Estado:</strong> <span id="estado-${emp.empleado_id}">${emp.estado}</span></p>
    <p class="tiempo-principal" id="tiempo-${emp.empleado_id}">${tiempoPrincipal}</p>
    <p><strong>Neto:</strong> <span id="neto-${emp.empleado_id}">${emp.neto || "0h 0m 0s"}</span></p>
    <p><strong>Comida:</strong> <span id="comida-${emp.empleado_id}">${emp.comida || "0h 0m 0s"}</span></p>
    <p><strong>Descanso:</strong> <span id="descanso-${emp.empleado_id}">${emp.descanso || "0h 0m 0s"}</span></p>
  `;

  return card;
}

function iniciarCronometro(emp) {
  const empleadoId = emp.empleado_id;
  const estado = emp.estado;

  if (!["trabajando", "en comida", "en descanso"].includes(estado)) return;

  if (timers[empleadoId]) {
    clearInterval(timers[empleadoId]);
  }

  let trabajadoReal = Math.max(
    0,
    parseInt(emp.segundos_trabajados_reales ?? emp.segundos_trabajados ?? 0, 10)
  );

  let netoReal = Math.max(
    0,
    parseInt(emp.segundos_netos_reales ?? emp.segundos_netos ?? 0, 10)
  );

  let comida = Math.max(
    0,
    parseInt(emp.segundos_comida ?? 0, 10)
  );

  let descanso = Math.max(
    0,
    parseInt(emp.segundos_descanso ?? 0, 10)
  );

  timers[empleadoId] = setInterval(() => {
    if (estado === "trabajando") {
      trabajadoReal++;
      netoReal++;
    } else if (estado === "en comida") {
      comida++;
    } else if (estado === "en descanso") {
      descanso++;
    }

    let trabajadoMostrado = trabajadoReal;
    let netoMostrado = netoReal;

    if (empleadoId === 3) {
      trabajadoMostrado = aplicarLogicaMelany(trabajadoReal);
      netoMostrado = aplicarLogicaMelany(netoReal);
    }

    const tiempoEl = document.getElementById(`tiempo-${empleadoId}`);
    const netoEl = document.getElementById(`neto-${empleadoId}`);
    const comidaEl = document.getElementById(`comida-${empleadoId}`);
    const descansoEl = document.getElementById(`descanso-${empleadoId}`);

    if (tiempoEl) tiempoEl.innerText = formatear(trabajadoMostrado);
    if (netoEl) netoEl.innerText = formatear(netoMostrado);
    if (comidaEl) comidaEl.innerText = formatear(comida);
    if (descansoEl) descansoEl.innerText = formatear(descanso);
  }, 1000);
}

function renderizarTrabajadores(data) {
  const panel = document.getElementById("panelTrabajadores");
  if (!panel) return;

  limpiarTimers();
  panel.innerHTML = "";

  const empleados = construirBaseTrabajadores(data);

  empleados.forEach((emp) => {
    const tarjeta = crearTarjetaEmpleado(emp);
    panel.appendChild(tarjeta);
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
    })
    .catch((error) => {
      console.error(error);
      const panel = document.getElementById("panelTrabajadores");
      if (panel) {
        panel.innerHTML = "<p>No se pudo cargar el resumen de hoy.</p>";
      }
    });
}

function toggleHistorial() {
  const panel = document.getElementById("panelHistorial");
  if (!panel) return;
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
        const texto = await res.text();
        throw new Error(`No se pudo cargar el historial (${res.status}) ${texto}`);
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
      console.error("Error al cargar historial:", error);
      contenedor.innerHTML = `<p>${error.message}</p>`;
    });
}

document.addEventListener("DOMContentLoaded", () => {
  cargarResumen();
});