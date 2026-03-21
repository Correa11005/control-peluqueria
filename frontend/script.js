const URL =
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname === "localhost"
    ? "http://127.0.0.1:5000"
    : "https://control-peluqueria.onrender.com";
let timers = {};

function formatear(segundos) {
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  return `${h}h ${m}m ${s}s`;
}

function cargarHistorial() {
  const empleadoId = document.getElementById("filtro_empleado").value;
  const fecha = document.getElementById("filtro_fecha").value;
  const contenedor = document.getElementById("historial");

  contenedor.innerHTML = "<p>Cargando historial...</p>";

  let url = `${URL}/historial`;
  const params = [];

  if (empleadoId) {
    params.push(`empleado_id=${empleadoId}`);
  }

  if (fecha) {
    params.push(`fecha=${fecha}`);
  }

  if (params.length > 0) {
    url += `?${params.join("&")}`;
  }

  fetch(url)
    .then(res => {
      if (!res.ok) {
        throw new Error("No se pudo cargar el historial");
      }
      return res.json();
    })
    .then(data => {
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

      data.forEach(item => {
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

      html += `
          </tbody>
        </table>
      `;

      contenedor.innerHTML = html;
    })
    .catch(error => {
      console.error(error);
      contenedor.innerHTML = `<p>${error.message}</p>`;
    });
}

function limpiarTimers() {
  for (const key in timers) {
    clearInterval(timers[key]);
  }
  timers = {};
}

function cargarResumen() {
  fetch(`${URL}/resumen_hoy`)
    .then(res => {
      if (!res.ok) {
        throw new Error("No se pudo cargar el resumen");
      }
      return res.json();
    })
    .then(data => {
      const panel = document.getElementById("panel");
      panel.innerHTML = "";
      limpiarTimers();

      data.forEach(emp => {
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
        tiempo.textContent = formatear(Math.max(0, emp.segundos_netos || 0));

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

        if (emp.estado === "trabajando") {
          let segundos = Math.max(0, emp.segundos_netos || 0);

          timers[emp.nombre] = setInterval(() => {
            if (emp.empleado_id === 3 && segundos >= 14400) {
              clearInterval(timers[emp.nombre]);
              return;
            }

            segundos++;

            const elementoTiempo = document.getElementById(tiempoId);
            if (elementoTiempo) {
              elementoTiempo.innerText = formatear(segundos);
            }
          }, 1000);
        }
      });
    })
    .catch(error => {
      console.error(error);
      document.getElementById("mensaje").innerText =
        "No se pudo cargar el resumen de hoy.";
    });
}
function toggleHistorial() {
  const panel = document.getElementById("panelHistorial");
  panel.classList.toggle("oculto");
}

function marcar(tipo) {
  const empleado_id = document.getElementById("empleado_id").value;
  const mensaje = document.getElementById("mensaje");

  if (!empleado_id) {
    mensaje.innerText = "Selecciona un empleado.";
    return;
  }

  mensaje.innerText = "Registrando...";

  fetch(`${URL}/marcar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      empleado_id: parseInt(empleado_id, 10),
      tipo: tipo
    })
  })
    .then(async res => {
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "No se pudo registrar la marcación");
      }
      return data;
    })
    .then(data => {
      const textos = {
        entrada: "ya está empezando la labor",
        salida: "ha finalizado la jornada",
        inicio_comida: "inició su tiempo de comida",
        fin_comida: "finalizó su tiempo de comida",
        inicio_descanso: "inició su descanso",
        fin_descanso: "finalizó su descanso"
      };

      const nombre = document.getElementById("empleado_id")
        .options[document.getElementById("empleado_id").selectedIndex].text;

      mensaje.innerText = `${nombre} ${textos[tipo]}.`;
      console.log(data);

      cargarResumen();
    })
    .catch(error => {
      console.error(error);
      mensaje.innerText = error.message || "Error de conexión.";
    });
}

window.addEventListener("load", () => {
  cargarResumen();
;
}); 