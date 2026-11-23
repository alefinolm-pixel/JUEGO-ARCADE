# PIXEL FIGHTERS

Juego de lucha para mini maquina arcade. Te haces una foto y aparece un munyeco
pixel-art que se te parece (piel, pelo, gafas, barba, color de ropa...).

## Instalar

```
pip install -r requirements.txt
copy .env.example .env      (en Linux/Raspberry: cp .env.example .env)
python main.py
```

## Como funciona la creacion del luchador

1. La camara detecta la cara y recorta **cabeza + hombros** (se ve el largo del pelo y la ropa).
2. `rasgos.py` manda la foto a la IA de **vision** (OpenAI o Gemini) y le pide un JSON:
   `{"piel": "#c48a5c", "pelo_largo": "largo", "gafas": "normales", "ropa_color": "#d03050", ...}`
   Si no hay internet/clave, lo estima en local con OpenCV (colores bien; gafas y largo aproximados).
3. `avatar.py` dibuja el munyeco con esos rasgos, en pixel art, con todas sus poses.
4. Pantalla **PERSONALIZA**: el jugador elige **CUERPO** (agil / equilibrado / fuerte,
   cambia la silueta Y las estadisticas) y **TRAJE** (karate / boxeo / ninja / calle).
   Si lleva gafas, su especial es el **RAYO FACIAL** (sale de las gafas).
5. Se guarda `data/characters/<id>/meta.json` (rasgos, cuerpo, traje...). **La foto se borra.**

## Probar la IA sin abrir el juego

```
python probar_ia.py una_foto_tuya.jpg
```
Muestra lo que responde OpenAI, Gemini y el modo local, con el **error real** de cada uno,
y guarda `data/tmp/avatar_<proveedor>.png` para comparar.

## Controles

Un jugador contra la maquina (CPU). Vale el joystick (WASD) o las flechas:

| Mover | Saltar | Golpe | Especial | Bloquear |
|---|---|---|---|---|
| A / D (o flechas) | W (o arriba) | F (o K) | G (o L) | mantener hacia atras |

Rondas: gana quien gane 2. 60 segundos por ronda (si se acaba, gana quien tenga mas % de vida).
Modo arcade: cada victoria seguida sube la RACHA y el nivel de la CPU (1 a 5).
El rival se sortea entre todos los luchadores.

## Dificultad y escenarios

Al pulsar JUGAR se elige la dificultad. Cada una tiene su escenario y su musica:

| Dificultad | Escenario | CPU |
|---|---|---|
| NORMAL | Cafeteria retro anos 80 (neon, ajedrez, furgoneta de comida) | nivel 1-2 |
| DIFICIL | Noche gotica (catedral, luna, murcielagos, relampagos) | nivel 3-4 |
| EXPERTO | Estacion espacial: espadas de energia y cascos alien | nivel 5-6 |

Los escenarios estan en `escenarios.py` (pixel art dibujado por codigo). La fuente de
letras es propia: `fuente_pixel.py`.

## Sonidos

Se sintetizan solos (no hacen falta archivos). Para usar los tuyos, crea
`assets/sonidos/<nombre>.wav` (o .ogg) con el mismo nombre: `golpe`, `golpe_fuerte`, `aire`,
`bloqueo`, `salto`, `carga`, `proyectil`, `rayo`, `trueno`, `sismo`, `estrella`, `ko`,
`victoria`, `cuenta`, `lucha`, `foto`, `menu_mover`, `menu_ok`, `menu_atras`.
Musica: `assets/musica/menu.ogg` y `assets/musica/pelea.ogg`.

## Archivos

| Archivo | Que hace |
|---|---|
| `teclado.py` | Teclado en pantalla para escribir el nombre con joystick y botones |
| `escenarios.py` | Los 3 escenarios de pelea |
| `fuente_pixel.py` | Fuente de letras pixel propia y rotulos con degradado |
| `ia_cpu.py` | Inteligencia del rival (niveles 1-5) |
| `rasgos.py` | Foto -> rasgos (OpenAI / Gemini / local) |
| `avatar.py` | Rasgos + cuerpo + traje -> munyeco pixel-art con poses |
| `probar_camara.py` | `python probar_camara.py 192.168.1.133 192.168.1.181` dice por que falla cada movil |
| `fighter.py` | Fisica, golpe, bloqueo, empuje, dibujo con efectos |
| `especiales.py` | Los 7 ataques especiales |
| `efectos.py` | Particulas, chispas, temblor, hitstop, numeros de dano |
| `sonido.py` | Efectos de sonido y musica chiptune |
| `scenes.py` | Menu, seleccion, pelea (rondas/HUD) y crear luchador |
| `roster.py` | Personajes base y guardado de los creados |
