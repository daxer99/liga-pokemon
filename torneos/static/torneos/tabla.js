// Mostrar/ocultar estadísticas extra y ordenar la tabla al tocar un encabezado.
document.querySelectorAll("[data-alternar-stats]").forEach((boton) => {
  const carta = boton.closest(".tabla-controles").nextElementSibling;
  boton.addEventListener("click", () => {
    const abierta = carta.classList.toggle("con-extras");
    boton.setAttribute("aria-pressed", abierta);
    boton.textContent = abierta ? "Ver menos estadísticas" : "Ver más estadísticas";
  });
});

document.querySelectorAll("table[data-ordenable]").forEach((tabla) => {
  const encabezados = [...tabla.tHead.rows[0].cells];
  encabezados.forEach((th, col) => {
    if (!th.dataset.orden) return;
    th.tabIndex = 0;
    th.classList.add("ordenable");
    const ordenar = () => {
      // Por defecto, números de mayor a menor (salvo # y "Mejor puesto") y texto A-Z
      const menorPrimero = th.dataset.orden === "texto" || col === 0 || th.textContent.trim() === "Mejor";
      const asc = th.getAttribute("aria-sort") === (menorPrimero ? "ascending" : "descending") ? !menorPrimero : menorPrimero;
      encabezados.forEach((h) => h.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", asc ? "ascending" : "descending");
      const valor = (fila) => {
        const celda = fila.cells[col];
        const v = celda.dataset.valor ?? celda.textContent.trim();
        return th.dataset.orden === "num" ? parseFloat(v) || 0 : v.toLowerCase();
      };
      const filas = [...tabla.tBodies[0].rows].sort((a, b) => {
        const x = valor(a), y = valor(b);
        const c = typeof x === "number" ? x - y : x.localeCompare(y, "es");
        return asc ? c : -c;
      });
      tabla.tBodies[0].append(...filas);
    };
    th.addEventListener("click", ordenar);
    th.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ordenar(); } });
  });
});
