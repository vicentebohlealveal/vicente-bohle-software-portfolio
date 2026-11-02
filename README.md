# Kong.3d — Inventario de taller

Aplicación web para organizar gaveteros/compartimentos de un taller, localizar componentes y gestionar el inventario desde una interfaz visual. La versión principal es un archivo HTML con JavaScript y CSS embebidos; usa SheetJS y Supabase mediante CDN para exportación y sincronización opcional.

## Ejecutar

Esta copia de portafolio está sanitizada: la URL y la publishable key de tu instancia real no se distribuyen; la conexión a Supabase debe configurarse por separado si se desea probar la sincronización. Para evitar exponer datos de tu instancia personal, la URL y la publishable key se han sustituido por marcadores (`PEGA_AQUI_TU_URL` y `PEGA_AQUI_TU_PUBLISHABLE_KEY`).

1. Crea/configura tu propio proyecto Supabase y revisa las políticas RLS de la tabla antes de conectar la aplicación.
2. Reemplaza esos marcadores en `index.html` con la URL y la publishable key de tu proyecto. Nunca coloques una `service_role` key ni una secret key en el código de navegador.
3. Abre `index.html` en un navegador moderno.

La sincronización en la nube no funcionará hasta completar la configuración; las bibliotecas de CDN requieren Internet. El formulario de acceso recoge la contraseña en tiempo de ejecución y la entrega al SDK de Supabase Auth; esta carpeta no contiene tu contraseña ni la persiste en el código.

## Seguridad y datos

Esta copia no incluye una exportación del inventario real ni credenciales de acceso. Antes de publicar cambios, revisa las políticas de acceso y nunca subas contraseñas, tokens privados ni datos internos del taller.
