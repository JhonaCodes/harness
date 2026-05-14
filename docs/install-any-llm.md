# Instalar Harness En Cualquier LLM

Harness tiene dos niveles de instalacion:

1. Runtime universal: instala el CLI `harness` y la copia local del runtime.
2. Entrypoints por herramienta: instala una pequena instruccion para que cada LLM sepa como invocar Harness.

El runtime universal siempre se instala. Los entrypoints son opcionales y puedes seleccionar varios.

## Instalacion Interactiva

Desde el repo `harness`:

```bash
./install.sh
```

El instalador pregunta:

```text
Where should Harness install LLM entrypoints?

  1) codex      Codex skill
  2) claude     Claude Code slash command
  3) gemini     Gemini global context
  4) opencode   OpenCode global instructions
  5) none       Runtime and CLI only
```

Puedes responder con numeros o nombres:

```text
1,2,4
codex,claude,opencode
all
none
```

## Instalacion No Interactiva

Para scripts, CI o instalacion reproducible:

```bash
./install.sh --targets codex,claude,gemini,opencode
./install.sh --targets codex,opencode
./install.sh --targets none
HARNESS_TARGETS=codex,claude ./install.sh
```

`none` instala solo el runtime y el CLI. Es util si el LLM no tiene mecanismo global de instrucciones o si quieres invocar Harness manualmente.

## Que Instala Cada Target

- `codex`: instala el skill `harness` en el directorio de skills de Codex.
- `claude`: instala el comando `/harness` para Claude Code.
- `gemini`: agrega una seccion gestionada de Harness al contexto global de Gemini.
- `opencode`: agrega una seccion gestionada de Harness a las instrucciones globales de OpenCode.
- `none`: no instala entrypoints de LLM.

Los archivos instalados por herramienta solo apuntan al runtime universal. La fuente de verdad sigue siendo `HARNESS.md` y `.harness/ENTRYPOINT.md` dentro de cada proyecto preparado.

## Como Invocarlo Desde Cada LLM

Codex:

```text
usa harness para instalar harness en este proyecto
```

Claude Code:

```text
/harness instala harness en este proyecto
```

Gemini:

```text
instala harness en este proyecto
```

OpenCode:

```text
instala harness en este proyecto
```

Cualquier otro LLM:

```text
Lee el README del repo harness y usa el CLI `harness`.
Primero ejecuta:
harness inspect --project <ruta|url|owner/repo> --task "<tarea>"
Luego, si corresponde preparar el proyecto:
harness run --project <ruta|url|owner/repo> --task "<tarea>"
```

## Flujo Recomendado

1. Instala Harness una vez en tu maquina:

   ```bash
   ./install.sh
   ```

2. Selecciona los LLMs que usas.

3. Abre cualquier proyecto en tu LLM.

4. Pide:

   ```text
   instala harness en este proyecto
   ```

5. Harness inspecciona la tarea y decide automaticamente:

   - `simple`: no instala nada en el proyecto.
   - `tdd`: instala runtime minimo, verificacion y auditoria.
   - `sdd`: instala runtime completo, specs, backlog, roles y auditoria.

## Si El LLM No Detecta Harness

Usa el CLI directamente:

```bash
harness inspect --project /path/to/project --task "describe la tarea"
harness run --project /path/to/project --task "describe la tarea" --dry-run
harness run --project /path/to/project --task "describe la tarea"
```

Si el comando `harness` no aparece en PATH, usa:

```bash
$HOME/.local/bin/harness inspect --project /path/to/project --task "describe la tarea"
```

## Regla Importante

No importa que LLM uses. Despues de aplicar Harness a un proyecto, el LLM debe leer:

- `HARNESS.md`
- `.harness/ENTRYPOINT.md`
- `.harness/config.json`
- `.harness/workflow.json`
- `.harness/skills.json`
- `.harness/memory.json`

Esos archivos son el contrato universal. Los archivos especificos de Codex, Claude, Gemini u OpenCode solo ayudan a arrancar.
