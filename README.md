# Nexo Finanzas · Python + Kivy

Python 3.10.11 y Kivy 2.3.1. SQLite utiliza `sqlite3`, incluido con Python;
no se instalaron dependencias adicionales. Se conservan los filtros, los cálculos
y el formato CLP sin decimales.

## Identidad visual · Primera etapa para revisión

Marca: **Nexo Finanzas**. Lema: **Tu dinero, en equilibrio.**
Paletas oficiales claro y oscuro con azul índigo; verde para ingresos, rojo para
egresos y ámbar para avisos. El selector compacto está únicamente en
**Hogar y ajustes → Apariencia → Tema**. El encabezado queda sin controles de
apariencia. Cambia los colores inmediatamente sin reconstruir el
formulario ni perder texto, selección, filtros o posición de desplazamiento.

La preferencia se guarda en `appearance.json` junto al directorio de datos de
Kivy, independiente de SQLite y común a los modos local/demo. Se recupera al
reiniciar. Automático está disponible cuando se puede leer el tema de aplicaciones
de Windows y comprueba cambios cada dos segundos. En plataformas sin detección
compatible se ofrecen Claro y Oscuro; una preferencia automática importada usa
Claro como alternativa. No requiere dependencias nuevas ni permisos de escritura
en el registro de Windows.

Esta entrega rediseña primero **Inicio, Personal y Nuevo movimiento**, con
indicadores financieros, espacios más compactos y navegación con iconos dibujados
en Kivy (sin fuentes adicionales). El resto recibe la paleta y componentes
compartidos, pero su rediseño de distribución queda pendiente de revisión visual.
No se han cambiado las tablas ni los datos financieros por este trabajo.

Para revisar: ejecuta `main.py`, entra en demo o modo local, abre **Hogar** y
busca **Apariencia**. Alterna Claro/Oscuro (y Automático si está disponible);
el cambio es inmediato. Vuelve a Inicio: el encabezado no debe mostrar un selector.
Cierra y vuelve a abrir para verificar la preferencia seleccionada.
Reduce la ventana para comprobar el desplazamiento vertical y la navegación fija.

```powershell
.\.venv\Scripts\python.exe preview_design.py
```

Genera capturas de demo en `docs/previews`: Inicio, Personal, Nuevo movimiento,
Hogar y Categorías en ambos temas; las tres últimas también a 360×640. Usa preferencias temporales; no
modifica tu configuración ni abre la base personal. `test_design.py` comprueba
persistencia del tema, cambio de colores, detección automática y errores.

Archivos visuales: `nexo/design.py` (paletas/gestor), `nexo/widgets.py` (componentes),
`nexo/app.py` (composición), `test_design.py` y `preview_design.py` (verificación).

## Ejecutar desde VS Code en Windows

### Revisión visual: Hogar y ajustes

Esta etapa cambia únicamente la composición de Hogar y ajustes. Los componentes
en `nexo/settings_widgets.py` son optativos y no sustituyen los controles de las
otras pantallas: botones/campos/selectores redondeados con Canvas, filas de ajuste
con iconos vectoriales y flechas, y tarjetas ajustadas al contenido.
Mi hogar no añade el mensaje de estado hasta que haya un resultado que mostrar.
Apariencia coloca el tema actual y el selector en una sola fila. Categorías y
Privacidad son filas táctiles completas, sin botones rectangulares anidados.
La separación entre bloques es 12 dp y los controles táctiles miden 44 dp.

```powershell
.\.venv\Scripts\python.exe verify_settings.py
```

Ejecuta una demo temporal, verifica alturas, guardado del nombre y acceso al final
del ScrollView por encima de la navegación. Genera capturas reales en ambos temas
a 360×640 y 430×860, sin abrir la base local ni cambiar tus preferencias.
Se guardan en `docs/previews/Hogar-<tema>-<ancho>.png` y las versiones `-final.png`
muestran la pantalla desplazada hasta abajo. Revisión pendiente antes de aplicar
estos componentes a otras pantallas. No se modificó el esquema ni los cálculos.

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

## Presupuestos mensuales

Desde Inicio o Hogar, abre **Presupuestos**. Conserva las tarjetas y barras
actuales y permite trabajar con categorías de egreso para Personal o Familiar.
Son ámbitos organizativos locales; no hay autenticación ni permisos multiusuario.

1. Escribe un mes `AAAA-MM`, selecciona el ámbito y pulsa **Consultar mes y ámbito**.
   Esto define tanto los presupuestos mostrados como el destino de los nuevos.
2. Elige una categoría, escribe el monto máximo entero CLP sin separadores y
   pulsa **Crear presupuesto**. Un duplicado de categoría/mes/ámbito se rechaza;
   la misma categoría puede tener límites distintos en otros meses o ámbitos.
3. Cada tarjeta muestra utilizado, máximo, porcentaje y disponible. El disponible
   puede ser negativo si se excede el límite; la barra se llena hasta el 100%.
4. **Editar límite** cambia el monto. Para cambiar categoría, mes o ámbito,
   crea el presupuesto correcto y elimina el anterior. **Eliminar** pide
   confirmación y conserva todos los movimientos asociados.
5. Los cálculos usan únicamente Egresos del mes, categoría y ámbito elegidos.
   Se recalculan al abrir la pantalla después de registrar, editar o eliminar
   un movimiento. Los ingresos nunca reducen el consumo del presupuesto.
6. Para probar alertas, configura Alimentación con límite `100000` y registra
   egresos con la misma fecha/mes y ámbito: `80000` muestra aviso ámbar desde
   80%; al llegar a `100000` indica límite alcanzado; con `100001` avisa exceso.
   Edita o elimina esos egresos y vuelve a Presupuestos para comprobar el ajuste.
7. Consulta un mes anterior para ver sus propios presupuestos. Cierra la app,
   vuelve al modo local y consulta ese mes: límites y movimientos se conservan.

Migración automática: los límites de versiones anteriores no tenían mes ni
ámbito. Al abrir la base se copian una sola vez al mes de la migración y al
ámbito Familiar, que era su comportamiento anterior. La operación es transaccional;
un fallo revierte los cambios. La tabla antigua queda como antecedente y nunca
se reimporta tras borrar un presupuesto. Los movimientos no se modifican.
En demo, crear/editar/eliminar funciona en memoria sin tocar SQLite.

## Archivo SQLite local

La app usa `Path(App.user_data_dir) / "nexo.sqlite3"`. La ruta completa se muestra
en **Hogar → Privacidad y datos → Ver información** dentro del modo local. Nunca se guarda en el código fuente.
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
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe verify_demo.py
```

Las pruebas SQLite usan bases temporales: ingresos, egresos, reapertura, edición,
eliminación, orden con empates, separación demo/local, saldos, validaciones y
fallos de almacenamiento. La verificación gráfica abre una ventana brevemente,
recorre la demo y el modo local temporal, guarda, edita, elimina y cambia de modo.
No toca tu base personal. Ambos comandos terminan con error si algo falla.

`unittest discover` incluye `test_budgets.py`: creación, edición, eliminación,
duplicados, persistencia, filtros, umbrales exactos de 80%/100%, actualización
por cambios de movimientos y migración con conservación y reversión ante fallos.
La prueba gráfica también comprueba crear, editar, cancelar y confirmar el
borrado de presupuestos y las advertencias en pantalla.

## Categorías personalizadas

En **Hogar y ajustes → Categorías**, los selectores **Ingresos/Egresos** y
**Personal/Familiar** actualizan automáticamente la lista y el formulario, sin
botón de consulta. El ámbito seleccionado queda destacado y aparece en el título
de la lista y en **Nueva categoría**. Escribe el nombre (ejemplo: Mascotas) y pulsa
**Agregar categoría**, justo debajo del campo. La confirmación aparece en el mismo
formulario. Se muestran predeterminadas y
personalizadas con su estado; no hay cuentas ni permisos multiusuario.

- Los nombres admiten de 1 a 60 caracteres. No se permiten vacíos ni duplicados
  dentro del mismo tipo y ámbito, ignorando mayúsculas y espacios sobrantes.
  Los nombres inactivos también quedan reservados.
- **Editar nombre** está disponible para categorías personalizadas. Cambia el
  catálogo para futuros registros, conservando el nombre histórico de cada
  movimiento y su identificador de categoría.
- **Desactivar** pide confirmación. La categoría desaparece de nuevos formularios,
  sin borrar movimientos. Aún puedes editar otros campos de un movimiento que
  la utilizó; su selección histórica se conserva. No hay borrado físico de categorías.
- Renombrar o desactivar se bloquea si existen presupuestos vinculados, incluso
  de meses anteriores. El mensaje explica el motivo. Los límites, cálculos y
  movimientos permanecen intactos. Las predeterminadas no se pueden renombrar.
- Nuevo movimiento y edición actualizan las opciones por tipo y ámbito. Historial
  permite filtrar también nombres antiguos e inactivos. Los presupuestos permiten
  categorías personalizadas de egreso y suman por identificador estable.
- En modo local el catálogo persiste en SQLite. En demo vive solo en memoria y
  no se copia a la base personal.

La migración automática añade `categories` y referencias `category_id` a
movimientos y presupuestos, conservando sus campos anteriores, IDs, nombres,
fechas y montos. Se ejecuta en una transacción y no vuelve a sembrar ni reactivar
categorías en aperturas posteriores. No requiere reiniciar ni borrar la base.

Para comprobarlo desde VS Code:

1. Ejecuta `main.py`, entra al modo local y crea Egreso/Personal: `Mascotas`.
2. Abre Nuevo, selecciona Egreso/Personal y registra un movimiento con Mascotas.
   Cambia a Ingreso o Familiar: Mascotas no debe ofrecerse allí.
3. Renombra Mascotas como `Cuidado animal`. El historial conserva Mascotas y los
   nuevos registros ofrecen Cuidado animal.
4. Desactiva Cuidado animal: el historial sigue intacto, pero no aparece para
   nuevos movimientos. Cierra y abre la app para comprobar su estado persistente.
5. Crea otra categoría de egreso y un presupuesto vinculado. Intenta renombrarla
   o desactivarla: ambas acciones deben bloquearse sin afectar el presupuesto.
6. Prueba un nombre vacío o duplicado y verifica el mensaje. Alterna Claro/Oscuro
   desde Apariencia para comprobar que los controles mantienen el tema.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe verify_demo.py
```

Las pruebas usan bases temporales e incluyen catálogo, duplicados, migración y
reversión ante fallos, historial, presupuestos y formularios de movimientos.

Hogar y ajustes agrupa **Mi hogar**, **Categorías**, **Apariencia** y **Privacidad
y datos** con iconos y descripciones. Mi hogar permite guardar el nombre;
Apariencia conserva el cambio inmediato. En **Privacidad y datos → Ver información**
puedes consultar la ruta SQLite y las limitaciones locales, o los integrantes
ficticios si estás en demo. Presupuestos y cambio de modo siguen disponibles.

Para probar los filtros, crea una categoría Egreso/Personal, cambia a Ingresos y
Familiar (debe desaparecer), y vuelve a Egresos/Personal (reaparece). Desactívala
y comprueba que el historial sigue intacto. **Activar** permite volver a usarla,
previa confirmación, conservando el mismo ID e historial. Cierra y abre el modo
local y comprueba su estado. No se cambia el esquema ni se reinicia la base.

## Organización de módulos

- `main.py`: punto de entrada.
- `nexo/app.py`: pantallas, elección de modo, edición, confirmación de borrado y errores.
- `nexo/widgets.py`: componentes visuales y colores, conservados.
- `nexo/data.py`: demo, categorías, validaciones compartidas y cálculos.
- `nexo/storage.py`: tablas automáticas, consultas parametrizadas y transacciones SQLite.
- `nexo/budgets.py`: validación mensual, consumo por categoría y estados de alerta.
- `nexo/categories.py`: normalización y catálogo de categorías para la demo.
- `nexo/category_ui.py`: administración con formularios y confirmaciones.
- `test_categories.py`: catálogo, migraciones y referencias históricas.
- `test_budgets.py`: reglas de presupuesto y migración segura en bases temporales.
- `test_storage.py`: pruebas aisladas de persistencia.
- `verify_demo.py`: comprobaciones gráficas y de regresión.

Android/iOS conservan la interfaz adaptable; esta entrega se verifica en Windows.
No incluye paquetes ni pruebas en dispositivos. Android requiere Buildozer en
Linux/WSL2 y iOS una cadena de compilación en macOS.
