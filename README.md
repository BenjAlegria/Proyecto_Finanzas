# Nexo Finanzas · Python + Kivy

Python 3.10.11 y Kivy 2.3.1. SQLite utiliza `sqlite3`, incluido con Python;
no se instalaron dependencias adicionales. Se conservan el diseño oscuro,
las tarjetas, los filtros, la navegación y el formato CLP sin decimales.

## Ejecutar desde VS Code en Windows

Abre la terminal PowerShell y entra en `nexo-finanzas-inicio`:

```powershell
cd .\nexo-finanzas-inicio
.\.venv\Scripts\python.exe main.py
```

Si la terminal ya está en esa carpeta, omite el `cd`.
También puedes seleccionar `.venv\Scripts\python.exe` mediante
**Python: Select Interpreter** y ejecutar `main.py` con Run Python File.
No es necesario activar el entorno.

## Modos separados

En **Comenzar** puedes elegir:

- **Abrir modo personal local**: la primera vez empieza sin movimientos ni
  presupuestos. Las siguientes veces recupera lo guardado en SQLite. El autor
  es Usuario local, sin cuenta ni autenticación. Personal y Familiar son ámbitos
  organizativos; sus saldos se calculan por separado. Inicio resume Familiar y
  Mis finanzas resume Personal. No hay sincronización ni permisos multiusuario.
- **Iniciar sesión demo**: datos ficticios de Camila y Diego, únicamente en memoria.
  Al salir de la demo se reinician. Nunca se copian a SQLite.

La cabecera identifica el modo. Desde Hogar puedes cambiar de modo. Cerrar la
app o cambiar de modo no elimina los datos locales ya guardados.

## Probar la persistencia manualmente

1. Abre el modo personal local. En `+ Nuevo`, registra un Ingreso / Sueldo y un
   Egreso / Alimentación, con fecha actual y monto entero sin separadores.
2. Revisa Historial y Mis finanzas (o Inicio si elegiste ámbito Familiar).
3. Cierra completamente la ventana. Ejecuta de nuevo `main.py` y elige el modo
   personal local. Comprueba que aparecen los mismos movimientos y saldos.
4. Usa **Editar** en una tarjeta, cambia el monto y guarda. Se conserva el ID y
   la hora de creación; los saldos se recalculan al abrir cada pantalla.
5. Usa **Eliminar**, confirma y vuelve a abrir la app: el movimiento sigue eliminado.
   Cancelar la confirmación conserva el movimiento.
6. Cambia a demo y registra algo. Regresa al modo local: ese registro no aparecerá.
7. Configura un presupuesto en Presupuestos o cambia el nombre en Hogar: ambos
   también se conservan tras reiniciar.

Los filtros por mes/categoría/ámbito siguen disponibles. Después de guardar o
editar se muestra el historial del mes correspondiente al movimiento. El orden
es fecha del movimiento, hora de creación UTC e ID, descendentes. Editar conserva
la hora de creación y el ID; cambiar la fecha puede cambiar su posición.
Las categorías se actualizan inmediatamente entre Ingreso y Egreso y se validan
al guardar. El valor interno `Gasto` se conserva por compatibilidad.

## Ubicación de la base

La app usa `Path(App.user_data_dir) / "nexo.sqlite3"`. La ruta completa se muestra
en **Hogar y ajustes** dentro del modo local. Nunca se guarda en el código fuente.
En Windows, Kivy normalmente usa `%APPDATA%\nexofinanzas\nexo.sqlite3`.
Copia ese archivo con la app cerrada si deseas respaldar tus datos locales.

SQLite no está cifrado. Quien tenga acceso al archivo puede leerlo. Esta etapa
es de un solo usuario, sin seguridad entre integrantes; la autenticación y los
permisos reales pertenecen al futuro backend. No subas tu base a GitHub.
Los archivos de SQLite y sus auxiliares están excluidos por `.gitignore`.
Los errores de lectura/escritura se muestran en pantalla para poder reintentar;
no se reemplaza silenciosamente una base inaccesible por una vacía.

## Pruebas automatizadas

Desde `nexo-finanzas-inicio`:

```powershell
.\.venv\Scripts\python.exe -m unittest test_storage -v
.\.venv\Scripts\python.exe verify_demo.py
```

Las pruebas SQLite usan bases temporales: ingresos, egresos, reapertura, edición,
eliminación, orden con empates, separación demo/local, saldos, validaciones y
fallos de almacenamiento. La verificación gráfica abre una ventana brevemente,
recorre la demo y el modo local temporal, guarda, edita, elimina y cambia de modo.
No toca tu base personal. Ambos comandos terminan con error si algo falla.

## Módulos

- `main.py`: punto de entrada.
- `nexo/app.py`: pantallas, elección de modo, edición, confirmación de borrado y errores.
- `nexo/widgets.py`: componentes visuales y colores, conservados.
- `nexo/data.py`: demo, categorías, validaciones compartidas y cálculos.
- `nexo/storage.py`: tablas automáticas, consultas parametrizadas y transacciones SQLite.
- `test_storage.py`: pruebas aisladas de persistencia.
- `verify_demo.py`: comprobaciones gráficas y de regresión.

Android/iOS conservan la interfaz adaptable; esta entrega se verifica en Windows.
No incluye paquetes ni pruebas en dispositivos. Android requiere Buildozer en
Linux/WSL2 y iOS una cadena de compilación en macOS.
