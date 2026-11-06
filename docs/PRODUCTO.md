# Nexo Finanzas — Definición inicial del producto

## Objetivo
Aplicación móvil para que una familia controle gastos e ingresos mensuales y administre mejor el presupuesto, con movimientos personales privados y movimientos familiares compartidos.

## Etapa local actual

- Dos modos separados: demostración ficticia en memoria y personal local en SQLite.
- El modo local empieza sin movimientos ni presupuestos y conserva los cambios en el directorio de datos de Kivy; permite registrar, editar y eliminar movimientos.
- Un único usuario local, sin cuenta ni autenticación. Los ámbitos Personal y Familiar son organizativos y sus saldos se calculan por separado.
- La base local no está cifrada. No hay permisos entre integrantes ni sincronización; las reglas multiusuario siguientes son objetivos del futuro backend.
- Los registros y las bases personales nunca se incluyen en el repositorio. Las pruebas usan datos ficticios en directorios temporales.

## Usuarios y privacidad
- Cada persona tiene su propia cuenta.
- Una persona puede pertenecer a un hogar familiar.
- Cada movimiento es personal (solo visible para su propietario) o familiar (visible a miembros autorizados del hogar).
- El administrador del hogar NO puede leer movimientos personales ajenos.
- Los ingresos personales no se contabilizan automáticamente como dinero familiar.
- Las autorizaciones se comprueban en el servidor en cada operación, nunca solo en la interfaz.

## MVP
1. Registro e inicio de sesión.
2. Crear hogar e invitar integrantes.
3. Registrar ingresos y gastos personales o familiares: monto CLP, fecha, categoría, descripción, autor y ámbito.
4. Historial con filtros y operaciones de edición/borrado autorizadas.
5. Panel mensual de ingresos/gastos/saldo registrado, con separación clara de personal/familiar.
6. Presupuestos familiares por categoría y avisos dentro de la aplicación cuando se superen.
7. Administrar integrantes y permisos.
8. Interfaz usable en Android y escritorio, accesible y legible.

## Fuera del MVP
Conexiones bancarias, pagos automáticos, IA, lectura OCR de boletas, metas de ahorro avanzadas y notificaciones externas. Adjuntar boletas se evaluará para una iteración posterior.

## Pantallas iniciales
- Bienvenida / iniciar sesión / registro.
- Panel familiar: presupuesto restante, ingresos y gastos familiares, categorías y movimientos recientes.
- Mis finanzas: resumen y movimientos privados del usuario.
- Historial: filtros por mes, categoría y ámbito.
- Nuevo movimiento: gasto/ingreso, personal/familiar, monto, fecha, categoría y descripción.
- Presupuestos: límites mensuales por categoría, progreso y alertas visuales.
- Hogar y ajustes: integrantes, invitaciones, preferencias.

## Requerimientos no funcionales
- CLP sin decimales por defecto; fechas locales de Chile.
- Contraseñas con hash robusto, sesiones/tokens seguros, HTTPS, validación del lado servidor, consultas parametrizadas, controles anti abuso y pruebas de aislamiento entre hogares.
- Evitar registrar contraseñas, tokens o montos reales en logs.
- Diseño móvil primero, contrastes legibles, soporte a tamaños de pantalla distintos.

## Pendientes de decisión
- ¿Un único hogar para la familia o varios hogares independientes para otras familias?
- ¿Backend PostgreSQL o MySQL y dónde se alojará?
- ¿Reglas exactas para edición de movimientos familiares de otros integrantes?
- ¿Quién puede configurar los presupuestos familiares?
- ¿Nombre definitivo de la app y estilo visual?

## Orden de desarrollo
1. Prototipo Kivy con datos ficticios y navegación.
2. Validar pantallas y flujo con la familia.
3. Diseñar API y modelo de datos con permisos.
4. Implementar autenticación y hogar.
5. Implementar movimientos y reportes.
6. Implementar presupuestos y pruebas de privacidad.
7. Compilar APK Android con WSL2 y Buildozer.
