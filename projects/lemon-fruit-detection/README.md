# Contador Agrícola PRO — detección de limones

Aplicación web para cámara y conteo acumulativo por árbol mediante un modelo YOLO convertido a ONNX. La inferencia se ejecuta en el navegador con ONNX Runtime Web y el conteo se guarda en `localStorage` del dispositivo.

## Falta un archivo necesario

El código busca `./best.onnx`. El HTML incluido **no funcionará como detector hasta incorporar el modelo real** con el nombre exacto `best.onnx` en esta misma carpeta. No se ha creado un modelo de reemplazo. Antes de añadirlo a GitHub, comprueba tamaño, licencia/derechos de uso y que no contenga materiales confidenciales. Si excede los límites de GitHub, estudia Git LFS o alojamiento apropiado.

## Ejecución

Sirve la carpeta por HTTPS o `localhost`; los navegadores normalmente no permiten acceso a cámara desde un sitio HTTP no seguro. La aplicación solicita cámara y procesa los fotogramas en el cliente. Los registros de especies, árboles y cantidades quedan en el almacenamiento local del navegador y no se sincronizan automáticamente.

## Dependencias y límites

- ONNX Runtime Web se descarga desde jsDelivr; el código configura sus archivos WASM desde esa CDN.
- No se detectaron claves de API, contraseñas ni tokens en el HTML proporcionado.
- El postprocesamiento está escrito para una salida YOLO concreta (`[1,5,8400]`). Debe validarse contra el modelo real antes de presentar el conteo como fiable.
- El sistema acumula tracks mediante proximidad de centroides; en paneos reales puede contar frutos dos veces o perder detecciones. Debe validarse experimentalmente con datos de campo.
