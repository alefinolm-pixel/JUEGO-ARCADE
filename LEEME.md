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

Un jugador contra la maquina (CPU), o contra otra arcade en MULTIJUGADOR.
Vale el joystick (WASD) o las flechas:

| Mover | Saltar | Golpe | Especial | Bloquear |
|---|---|---|---|---|
| A / D (o flechas) | W (o arriba) | F (o K) | G (o L) | mantener hacia atras |

Rondas: gana quien gane 2. 60 segundos por ronda (si se acaba, gana quien tenga mas % de vida).
Modo arcade: cada victoria seguida sube la RACHA y el nivel de la CPU (1 a 5).
El rival se sortea entre todos los luchadores.

## Multijugador (arcade contra arcade)

Menu > **MULTIJUGADOR**. Las dos maquinas tienen que estar en la **misma red** (misma WiFi o
el mismo router por cable).

1. En una arcade: **CREAR PARTIDA** -> eliges luchador y escenario. La pantalla muestra su
   nombre y su **IP** (p. ej. `192.168.1.20`) y se queda esperando.
2. En la otra: **UNIRSE A PARTIDA** -> eliges luchador -> la partida aparece sola en la lista
   (se anuncia por la red). Si no aparece, **ESCRIBIR IP A MANO** con el joystick.
3. Pantalla VS y a pelear. Quien crea la partida es P1 (izquierda) y el otro P2 (derecha)
   en las dos pantallas; encima de tu barra pone **TU**. Al final, si los dos pulsan F, revancha.

Los luchadores creados con la camara viajan a la otra arcade (solo sus rasgos, nunca la foto)
y no se guardan alli.

**Como va por dentro** (`red.py`): las dos arcades simulan la misma pelea y solo se mandan los
botones de cada fotograma (lockstep). Lo que pulsas se aplica 3 fotogramas despues (50 ms),
lo justo para que llegue a la otra maquina. Cada segundo se comprueba que las dos ven lo mismo
y, si no, se corrige solo. Con cable de red va mejor que por WiFi.

Opciones en `.env` (todas opcionales):

| Variable | Para que | Por defecto |
|---|---|---|
| `RED_NOMBRE` | nombre de esta arcade en la lista de partidas | nombre del equipo |
| `RED_IP` | IP de la otra arcade, ya escrita al elegir ESCRIBIR IP | (la ultima usada) |
| `RED_PUERTO` | puerto TCP (los anuncios van por el siguiente, en UDP) | 50505 |
| `RED_RETARDO` | fotogramas de retardo de los controles (2 con cable, 4-5 si la WiFi va mal) | 3 |

Para saber la IP de la Raspberry tambien vale `hostname -I` en un terminal. Conviene fijarla
en el router (IP reservada / DHCP estatico) para que no cambie.

### Como probarlo sin tener dos arcades

1. **Prueba automatica (sin pantalla):** `python probar_red.py` -> dos "arcades" en este PC,
   conectadas de verdad por la red interna, pelean bot contra bot y comprueba que las dos ven
   exactamente lo mismo. Debe acabar en `TODO OK`. `python probar_red.py --lag 40` simula una
   red lenta.
2. **Dos ventanas en el mismo PC:** abre dos terminales en la carpeta del juego:
   - `python main.py --ventana` -> MULTIJUGADOR > CREAR PARTIDA (aqui juegas tu)
   - `python main.py --ventana --bot` -> MULTIJUGADOR > UNIRSE (eliges la partida de la lista,
     o IP `127.0.0.1`). En esa ventana tu luchador lo maneja la CPU, asi peleas contra ella.
   Para moverte por los menus de una ventana, haz clic en ella primero.
3. **PC + Raspberry (o dos PCs)** en la misma WiFi: igual que el punto 2 pero cada uno en su
   maquina. En Windows, la primera vez sale un aviso del cortafuegos: dale a **Permitir**
   (redes privadas). Debe ser la **misma version del juego** en las dos maquinas.

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
| `red.py` | Conexion entre arcades: anuncio de partidas, TCP, botones por fotograma |
| `escena_red.py` | Pantallas de MULTIJUGADOR y la pelea en red |
| `probar_red.py` | Prueba del multijugador en un solo PC, sin pantalla |
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
