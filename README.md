# Liga Pokémon TCG · Resultados

Sitio web para publicar los resultados de la liga de la tienda (fechas de liga, cups,
challenges y eventos especiales) a partir de los `.tdf` que exporta TOM.

## Puesta en marcha (local)

```bash
python -m venv .venv && source .venv/bin/activate    # o un entorno conda
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Sitio: http://localhost:8000 · Administración: http://localhost:8000/admin/

## Cargar resultados

Desde la web (con usuario staff): menú **Cargar .tdf**.

Desde la terminal, varios archivos de una vez:

```bash
python manage.py importar_tdf resultados/*.tdf --liga "Cuarta Liga Paraná"
python manage.py importar_tdf cup_octubre.tdf --tipo cup          # no suma a la liga
```

Si corregís algo en TOM y volvés a exportar, usá `--reemplazar` (o el tilde en la web).

## Reglamento de puntos

Se configura por liga en el admin (*Temporadas*): puntos por participar, por ganar,
por empatar y si el bye suma. Por defecto: participar 1, ganar +3, empatar +1, y el bye
suma 4 (3 por victoria y 1 por participación). En V-E-D, los porcentajes y la racha, el bye cuenta como victoria. La derrota asignada por TOM (código 8) no suma.
Solo los torneos de tipo *Fecha de liga* suman a la tabla.

## Estadísticas de la tabla

- **% Vic.**: partidas ganadas sobre jugadas (el bye cuenta como victoria).
- **Rend.**: puntos de partida obtenidos sobre los posibles (victoria 3, empate 1).
- **Prom.**: puntos de liga por fecha jugada.
- **Mejor**: mejor puesto final en una fecha. No cuentan las divisiones con
  menos de 4 jugadores (`MINIMO_JUGADORES_DIVISION` en `servicios.py`), para que un Junior
  solo en su división no figure como ganador de la fecha.
- **Racha**: mayor cantidad de victorias seguidas en la temporada (el bye cuenta como victoria).

Los porcentajes se marcan en gris para quienes jugaron menos de la mitad de las partidas
del que más jugó, y esos jugadores no compiten en el destacado de mejor porcentaje.

## Estructura

```
torneos/
  tdf_parser.py   lectura del XML de TOM (Python puro, sin Django)
  servicios.py    importación a la base y cálculo de la tabla acumulada
  models.py       Temporada, Torneo, Jugador, Participacion, Partida
  views.py        páginas públicas + carga de .tdf
  tests.py        pruebas del parser y del puntaje
  management/commands/importar_tdf.py
```

Códigos de resultado del `.tdf`: 1 gana J1, 2 gana J2, 3 empate, 5 bye, 8 derrota asignada.
Las fechas de nacimiento no se importan.

## La tabla en SQL puro (para clase)

```sql
WITH lados AS (
  SELECT jugador1_id AS jugador_id, resultado, 1 AS es_j1, torneo_id FROM torneos_partida
  UNION ALL
  SELECT jugador2_id, resultado, 0, torneo_id FROM torneos_partida WHERE jugador2_id IS NOT NULL
)
SELECT j.nombre || ' ' || j.apellido AS jugador,
       COUNT(DISTINCT l.torneo_id)    AS fechas,
       SUM(CASE
             WHEN l.resultado = 5 THEN 4                                  -- bye
             WHEN l.resultado = 8 THEN 0                                  -- derrota asignada
             WHEN l.resultado = 3 THEN 2                                  -- empate
             WHEN (l.resultado = 1 AND l.es_j1 = 1)
               OR (l.resultado = 2 AND l.es_j1 = 0) THEN 4                -- victoria
             ELSE 1                                                       -- derrota
           END) AS puntos
FROM lados l
JOIN torneos_jugador j ON j.id = l.jugador_id
JOIN torneos_torneo  t ON t.id = l.torneo_id
WHERE t.temporada_id = 1 AND t.tipo = 'liga'
GROUP BY j.id
ORDER BY puntos DESC;
```

## Publicar en PythonAnywhere (resumen)

1. Subí el proyecto (git clone) y creá un virtualenv con `pip install -r requirements.txt`.
2. En la pestaña *Web*, creá una app Django manual apuntando a `config/wsgi.py`.
3. Variables de entorno en el WSGI: `DJANGO_SECRET_KEY` (clave larga y secreta),
   `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=tuusuario.pythonanywhere.com`.
4. `python manage.py migrate`, `createsuperuser` y `collectstatic`; mapeá `/static/` a `staticfiles/`.
5. Respaldá `db.sqlite3` periódicamente.

## Próximas etapas

- Cuentas de jugadores vinculadas a su POP ID (con aprobación del admin).
- Carga de mazos con elección de 1 o 2 cartas principales (arquetipo).
- Estadísticas por arquetipo e imagen del mazo con TCGdex.
