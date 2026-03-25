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
    } catch (error) {
        mensaje.textContent = "Error de conexión con el servidor.";
        console.error(error);
    }
}