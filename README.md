# Nexo Finanzas · Prototipo Kivy

Python 3.10.11 y Kivy 2.3.1. No se agregaron dependencias. Datos ficticios
en memoria: al cerrar el proceso se descartan los cambios.

## Ejecutar en Windows (PowerShell)

Desde la carpeta `nexo-finanzas-inicio`:

```powershell
.\.venv\Scripts\python.exe main.py
```

Desde la carpeta superior, primero ejecutar `cd .\nexo-finanzas-inicio`.
No es necesario activar el entorno virtual.

## Recorrido

Comenzar → Iniciar sesión demo → Inicio. La barra inferior abre Inicio,
Personal, Nuevo movimiento, Historial y Hogar. Presupuestos está disponible
desde Inicio y Hogar. El contenido se desplaza verticalmente en ventanas pequeñas.

- Nuevo movimiento valida monto entero positivo, fecha ISO, categoría y descripción.
  Las categorías cambian inmediatamente entre Ingreso y Egreso; al cambiar de tipo
  se solicita seleccionar una categoría válida otra vez. Internamente se conserva
  `Gasto` para mantener compatibles los cálculos existentes.
  El ámbito inicial es Personal para evitar compartir por accidente.
- Inicio suma exclusivamente movimientos familiares del mes actual.
- Personal muestra solo movimientos de Camila. Historial filtra mes, ámbito y categoría.
- Historial y movimientos recientes se ordenan por fecha del movimiento, hora de
  registro UTC e identificador secuencial estable durante la sesión, en orden
  descendente. Este criterio se aplica también a los datos en memoria. Un registro
  con fecha anterior se ubica según esa fecha, aunque se haya registrado ahora.
- Presupuestos compara egresos familiares con límites editables del mes actual.
- Hogar permite cambiar su nombre durante la sesión y consultar integrantes ficticios.
- Cerrar sesión vuelve al acceso y conserva la demo en memoria hasta cerrar la app.

## Verificar

```powershell
.\.venv\Scripts\python.exe verify_demo.py
```

Abre una ventana brevemente, recorre las pantallas y comprueba formato CLP,
validación y separación de datos personales/familiares. También registra Ingreso / Sueldo
y Egreso / Alimentación desde el formulario, cambia los tipos, rechaza categorías
incompatibles y comprueba el orden (incluidos empates de hora) y los resúmenes.
Sale con error si falla.

## Archivos

- `main.py`: entrada y clase `NexoFinanzas` importada para mantener su nombre.
- `nexo/app.py`: pantallas, navegación y acciones.
- `nexo/widgets.py`: componentes visuales y paleta oscura.
- `nexo/data.py`: datos demo, validaciones, filtros y sumas.

El acceso es simulado; no introducir credenciales reales. No hay servidor,
base de datos, invitaciones reales ni garantía de seguridad multiusuario.
La autorización real debe comprobarse en el servidor, como define PRODUCTO.md.
Los permisos de edición/borrado de movimientos compartidos siguen pendientes
de definición y no se simulan aquí.

La interfaz usa unidades dp, controles táctiles y contenido adaptable para
teléfonos. Esta entrega se verifica en escritorio Windows; no incluye paquetes
Android/iOS ni pruebas en dispositivos. Android requiere posteriormente
Buildozer en Linux/WSL2; iOS requiere una cadena de compilación en macOS.
