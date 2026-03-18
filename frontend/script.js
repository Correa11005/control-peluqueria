function marcar(tipo) {
  const empleado_id = document.getElementById("empleado_id").value;

  if (!empleado_id) {
    document.getElementById("mensaje").innerText = "Selecciona un empleado";
    return;
  }

  fetch("https://control-peluqueria.onrender.com/marcar", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      empleado_id: parseInt(empleado_id),
      tipo: tipo
    })
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("mensaje").innerText =
        data.mensaje || data.error || JSON.stringify(data);
    })
    .catch(err => {
      document.getElementById("mensaje").innerText = "Error de conexión";
      console.error(err);
    });
}