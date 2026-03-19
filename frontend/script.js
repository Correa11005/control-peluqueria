const URL = "https://control-peluqueria.onrender.com";

let timers = {};

function formatear(segundos) {
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = segundos % 60;
  return `${h}h ${m}m ${s}s`;
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

        const nombre = document.createElement("h3");
        nombre.textContent = emp.nombre;

        const estado = document.createElement("p");
        estado.innerHTML = `<strong>Estado:</strong> ${emp.estado}`;

        const tiempo = document.createElement("p");
        tiempo.className = "tiempo";
        tiempo.id = `tiempo-${emp.empleado_id}`;
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

        if (emp.estado === "trabajando") {
          let segundos = emp.segundos_netos || 0;
          timers[emp.empleado_id] = setInterval(() => {
            segundos += 1;
            tiempo.textContent = formatear(segundos);
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
  setInterval(cargarResumen, 30000);
});