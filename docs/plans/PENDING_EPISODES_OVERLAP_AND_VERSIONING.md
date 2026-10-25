# Plan: solapamiento, versiones y grabaciones de episodios NTN

Estado: implementado y verificado. Decisiones: 2 s compartidos por UI y script,
regeneracion mediante `--include-generated`, seleccion y orden de grabaciones
editables antes de confirmar.

## Resultado de implementacion

- Intro activa durante 2 s, limitada por la duracion disponible. Outro sin
  cambios, incluido su solapamiento de 1 s. UI y timeline actualizados.
- Entradas por extension, exclusion de finales exactos, orden natural y
  seleccion mediante Enter para todas o indices como `3,1`.
- Regeneracion opt-in, sufijos locales y reserva exclusiva sin sobrescritura.
- 226 pruebas aprobadas y 29 subcasos aprobados en la imagen reconstruida;
  4 pruebas PowerShell omitidas porque ese ejecutable no esta en el contenedor.
- Prueba sintetica via CLI y API reales: intro 5 s, voz 10 s, resultado 13 s,
  ambas frecuencias presentes en el intervalo de solapamiento. Regeneracion
  versionada y finales previos conservados.
- Docker reconstruido y actualizado tras comprobar cola vacia y bloqueo de
  render disponible. Endpoint activo confirma `intro_voice_overlap: true`;
  `voice_outro_overlap` conserva su valor anterior.
- Configuracion actualizada mediante ConfigManager, comprobando que los demas
  ajustes permanecen iguales. No se han generado episodios reales ni modificado
  grabaciones de OneDrive.

## Diagnostico verificado

1. El servidor local devuelve `intro_voice_overlap: false` y
   `voice_outro_overlap: true` en `folder_episode_settings`.
   La [configuracion persistida](../../core/config.json) coincide.
2. El [procesador](../../features/audio_processor.py) usa `overlap_ms = 1000`
   tanto para intro como para outro. Activar la casilla actual solo proporciona
   un segundo, no los dos segundos solicitados.
3. El [servicio](../../features/episode_service.py) transmite la configuracion
   guardada al procesador. El script no activa el solapamiento por su cuenta.
4. El [descubrimiento](../../features/episode_discovery.py) solo acepta nombres
   tipo `Recording` / `Recoding`, en M4A, MP3 o WAV. Exige base e indices
   consecutivos, y considera finales nombres mas amplios que los solicitados,
   incluidos `nt580.mp3` y `ntn580_final.mp3`.
5. La propiedad `pending` excluye carpetas con finales. El
   [script](../../scripts/ntn-create-pending.py) solo permite seleccionar
   pendientes y siempre solicita `ntn<numero>.mp3`.
6. La [descarga](../../features/episode_client.py) rechaza colisiones.
   Los trabajos de carpetas ya tienen directorios aislados en el
   [servidor](../../features/episode_api.py); un archivo anterior en el
   directorio plano del servidor no es la colision local que hay que resolver.

No se ha analizado una grabacion concreta. Un silencio inicial puede retrasar
la primera palabra audible incluso despues de corregir el posicionamiento:
`trim_silence` tambien esta desactivado. No se propone activarlo automaticamente.

## 1. Solapamiento intro-voz de dos segundos

- Separar las duraciones: intro-voz de 2000 ms; voz-outro conserva 1000 ms.
  No cambiar una constante compartida y alterar accidentalmente el outro.
- Mantener el booleano existente. Si esta desactivado, conservar concatenacion
  sin solapamiento. Para este flujo, activar y guardar `intro_voice_overlap`
  mediante el mecanismo de configuracion existente.
- Con la opcion activa, usar
  `min(2000, duracion_intro_ms, duracion_voz_ms)` y colocar la voz en
  `duracion_intro_ms - solapamiento_ms`.
- Conservar la superposicion real de ambas pistas, sin introducir crossfade,
  fades de voz ni recortes de palabras.
- Actualizar etiquetas, resumen de configuracion, timeline, logs y documentacion
  que afirmen un segundo de solapamiento de intro. Conservar las firmas actuales
  si no hace falta modificarlas.
- No agregar un parametro configurable de duracion: el requisito es fijo, 2 s.

## 2. Descubrimiento de grabaciones por extension

- Revisar solo archivos inmediatos de las carpetas de episodio ya admitidas.
  Mantener el cliente sin dependencias de audio ni decodificacion durante listado.
- Aceptar nombres arbitrarios y extensiones de audio admitidas por la aplicacion:
  MP3, WAV, M4A, OGG, FLAC, AAC, AIFF y WMA, sin distinguir mayusculas.
- Reconocer finales con el patron exacto `^ntn\d+(?:-\d{2,})?\.mp3$`,
  sin distinguir mayusculas. Incluye `ntn123.mp3`, `ntn123-01.mp3`,
  `ntn123-02.mp3` y versiones superiores a 99.
- Los finales nunca entran en la mezcla. Conservar advertencia y bloqueo si un
  final tiene un numero NTN diferente al de la carpeta.
- Fuera de ese patron, todo audio es una posible grabacion, incluso nombres
  como `ntn123_final.mp3` o una voz limpia descargada anteriormente. Mostrar
  todos los candidatos antes de subirlos: esta es una consecuencia importante
  de la regla solicitada, no inferir que son finales por contener "ntn".
- Reemplazar el bloqueo por base ausente, huecos e indices duplicados por orden
  natural determinista, conservando base, `(2)`, `(3)` y colocando 2 antes de 10.
  Usar nombre completo como desempate estable. No ordenar por fecha de OneDrive.
- Permitir ajustar el orden o excluir candidatos antes de confirmar, para no
  mezclar musica, duplicados o derivados por accidente.

## 3. Regeneracion y nombres sin sobrescritura

- Mantener el comando actual limitado a pendientes. Agregar
  `--include-generated` para mostrar tambien carpetas con finales y grabaciones,
  identificando claramente que se trata de una regeneracion.
- Separar "pendiente" de "seleccionable para regenerar"; no redefinir `pending`
  para que un episodio terminado aparezca como pendiente.
- Destino inicial: `ntn123.mp3`. Si existe, elegir `ntn123-01.mp3`, luego
  `ntn123-02.mp3`, etc., tomando el primer sufijo libre.
- No incrementar el numero de episodio ni cambiar el comportamiento del API
  antiguo de nombres RSS y del cliente PowerShell.
- Elegir el nombre en la carpeta local antes de renderizar y enviarlo al servidor.
  MP3, transcripcion, voz limpia e informe deben compartir el mismo nombre base.
- Considerar tambien colisiones de los artefactos asociados al elegir nombre.
  Conservar la comprobacion de cambios de carpeta tras la confirmacion.
- Reservar el nombre mediante creacion exclusiva y un marcador por destino.
  Liberarlo al terminar o cancelar; informar reservas existentes, sin borrarlas
  a ciegas ni asumir que son abandonadas.
- Mantener publicacion sin reemplazo. Si un proceso ajeno crea el destino durante
  el render, no regenerar ni sobrescribir: informar el conflicto y conservar
  las referencias del resultado del servidor para recuperarlo.

## 4. Validacion y despliegue

- Audio sintetico: comprobar posicion de ambas senales y duracion, no solo logs.
  Con intro de 5 s y voz de 10 s, sin outro, voz desde 3 s y total de 13 s.
- Cubrir opcion desactivada, intro/voz menores de 2 s, intro ausente, silencio
  inicial y outro activo/inactivo, manteniendo su solapamiento de 1 s.
- Descubrimiento: nombres arbitrarios, extensiones y mayusculas, finales base y
  versionados, numero ajeno, huecos de indices, orden 2/10 y archivos no audio.
- CLI: listado sin Docker, regeneracion opt-in, exclusion de finales, orden y
  seleccion de entradas, confirmacion y cancelacion sin uploads.
- Nombres: base ocupada, varias versiones, huecos, mas de 99, sidecars ocupados,
  reserva concurrente, descarga parcial y colision durante el render.
- Verificar que el servidor recibe el nombre versionado y devuelve todos sus
  artefactos con ese nombre; conservar pruebas del API antiguo.
- Actualizar la [guia Docker](../DOCKER.md) y los textos de UI afectados.
- Reconstruir Docker explicitamente cuando no haya trabajos ejecutandose.
  Comprobar configuracion activa y validar el flujo completo con audio sintetico.
  No generar episodios reales ni tocar OneDrive sin seleccion del usuario.

Baseline ejecutado durante el analisis:
`python -m pytest tests\test_episode_discovery.py tests\test_episode_pending_cli.py -q`

Resultado inicial: 65 pruebas aprobadas. Validaban el comportamiento previo,
no los cambios propuestos. En esa fase no se modificaron configuracion,
grabaciones ni episodios finales.
