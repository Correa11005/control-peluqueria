const selectEmpleado = document.getElementById("empleado")

fetch("http://127.0.0.1:5000/empleados")

.then(res => res.json())

.then(data => {

data.forEach(emp => {

let option = document.createElement("option")

option.value = emp.id
option.text = emp.nombre

selectEmpleado.appendChild(option)

})

})

function registrar(){

const empleado_id = selectEmpleado.value

fetch("http://127.0.0.1:5000/registro",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
empleado_id:empleado_id
})

})

.then(res=>res.json())

.then(data=>{

document.getElementById("mensaje").innerText=data.mensaje

})

}