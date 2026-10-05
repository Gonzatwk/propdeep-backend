# Skills de diseño para Claude Code

Copias sin modificar de skills de terceros, para que cualquier sesión de Claude Code que trabaje en `web/` las tenga disponibles.

| Skill | Origen | Commit | Licencia |
|---|---|---|---|
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (`.claude/skills/impeccable`) | `ce14139` (v4.5.0) | Apache 2.0 |
| `emil-design-eng`, `animate`, `review-animations`, `improve-animations`, `find-animation-opportunities`, `animation-vocabulary`, `mobile-native`, `break-ui` | [emilkowalski/skills](https://github.com/emilkowalski/skills) | `e8a175d` | MIT |
| `design-taste-frontend` (taste-skill v2), `redesign-existing-projects` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (`skills/taste-skill`, `skills/redesign-skill`) | `ce26fc2` | MIT |

De Emil Kowalski se dejan fuera las skills de Swift, Expo/React Native, Sonner, `pick-ui-library` y `prototype`, que no aplican a la web actual. De taste-skill solo se incluyen la skill principal y la de rediseño; las carpetas se renombran al `name` de su frontmatter.

Notas:
- `impeccable` usa un lanzador (`scripts/impeccable`, o `scripts/impeccable.cmd` en Windows) que la primera vez descarga su motor desde las releases de GitHub del autor y comprueba su SHA-256.
- Para actualizar, vuelve a copiar la carpeta desde el repositorio de origen y cambia el commit de esta tabla.
