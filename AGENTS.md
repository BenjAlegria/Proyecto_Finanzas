# Instrucciones para Codex — Nexo Finanzas

Lee `docs/PRODUCTO.md` antes de modificar código. Trabaja en pasos pequeños, explica archivos cambiados y cómo probarlos. No implementes funciones fuera del MVP sin consultar. No introduzcas credenciales reales ni datos financieros privados en el repositorio. Prioriza seguridad, privacidad, pruebas y accesibilidad. Antes de instalar dependencias o modificar la arquitectura, presenta el plan.

## Tecnología inicial
- App Android-first y escritorio: Python + Kivy (KivyMD opcional, verificar compatibilidad).
- Backend multiusuario: Python + FastAPI, API HTTPS.
- Base de datos servidor: PostgreSQL o MySQL (decisión pendiente). SQLite solo para prototipos locales sin datos reales.
- No conectar directamente la app móvil a la base de datos; usar API autenticada.
- Para APK Android: Buildozer en Linux/WSL2.

## Primera tarea
Crear solo un prototipo ejecutable de la app Kivy con navegación y datos ficticios, sin credenciales ni backend. Pantallas: acceso, panel familiar, mis finanzas privadas, movimientos, nuevo movimiento, presupuestos y ajustes. Mostrar claramente que es demo. Entregar instrucciones para Windows.
