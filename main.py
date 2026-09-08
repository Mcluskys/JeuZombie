import asyncio
import random
import sys
import pygame

# ------------------------------------------------------------
# Zombie Memory - version Web / smartphone compatible Pygbag
# ------------------------------------------------------------
# Audio web : configuration légère.
pygame.mixer.pre_init(
    frequency=24000,
    size=-16,
    channels=1,
    buffer=4096,
)
pygame.init()

try:
    AUDIO_OK = pygame.mixer.get_init() is not None
except pygame.error:
    AUDIO_OK = False

WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zombie Memory Game")
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (50, 150, 50)

font_big = pygame.font.Font("assets/cartoon.ttf", 58)
font_medium = pygame.font.Font("assets/cartoon.ttf", 36)
font_small = pygame.font.Font("assets/cartoon.ttf", 24)
font_riddle = pygame.font.Font("assets/cartoon.ttf", 30)

background = pygame.image.load("assets/background.png").convert()
background = pygame.transform.scale(background, (WIDTH, HEIGHT))

zombie = pygame.image.load("assets/zombie.png").convert_alpha()
zombie_attack = pygame.image.load("assets/zombie_attack.png").convert_alpha()
zombie_ko = pygame.image.load("assets/zombie_ko.png").convert_alpha()
phylactere = pygame.image.load("assets/phylactere.png").convert_alpha()

actions = {
    "coup_pied": pygame.image.load("assets/coup_pied.png").convert_alpha(),
    "coup_genou": pygame.image.load("assets/coup_genou.png").convert_alpha(),
    "gifle": pygame.image.load("assets/gifle.png").convert_alpha(),
    "coup_tete": pygame.image.load("assets/coup_tete.png").convert_alpha(),
    "croche_pied": pygame.image.load("assets/croche_pied.png").convert_alpha(),
    "coup_poing": pygame.image.load("assets/coup_poing.png").convert_alpha(),
}


# ------------------------------------------------------------
# CACHE GRAPHIQUE
# Toutes les transformations coûteuses sont faites UNE SEULE FOIS.
# Dans le navigateur, smoothscale/rotozoom à chaque frame peut faire
# rater le temps réel audio et provoquer des grésillements.
# ------------------------------------------------------------
dark_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
dark_overlay.fill((0, 0, 0, 85))

zombie_normal = pygame.transform.smoothscale(
    zombie,
    (
        int(zombie.get_width() * (int(HEIGHT * 0.34) / zombie.get_height())),
        int(HEIGHT * 0.34),
    ),
)

def fit_image(img, max_w, max_h):
    scale = min(max_w / img.get_width(), max_h / img.get_height())
    return pygame.transform.smoothscale(
        img,
        (max(1, int(img.get_width() * scale)), max(1, int(img.get_height() * scale))),
    )

zombie_ko_large = fit_image(zombie_ko, WIDTH * 0.55, HEIGHT * 0.70)
zombie_attack_large = fit_image(zombie_attack, WIDTH * 0.52, HEIGHT * 0.76)
zombie_final = fit_image(zombie_ko, WIDTH * 0.40, HEIGHT * 0.38)

action_sequence_imgs = {
    key: pygame.transform.smoothscale(img, (190, 190))
    for key, img in actions.items()
}
action_button_imgs = {
    key: pygame.transform.smoothscale(img, (142, 142))
    for key, img in actions.items()
}
action_button_big_imgs = {
    key: pygame.transform.smoothscale(img, (158, 158))
    for key, img in actions.items()
}

music_started = False
music_sound = None
music_channel = None
zombie_sound = None

if AUDIO_OK:
    try:
        # Les sons sont décodés une fois en mémoire.
        # Cela évite au navigateur de décoder la musique en continu pendant le jeu.
        music_sound = pygame.mixer.Sound("assets/musique.ogg")
        music_sound.set_volume(0.35)

        zombie_sound = pygame.mixer.Sound("assets/cri_zombie.ogg")
        zombie_sound.set_volume(0.65)
    except (pygame.error, FileNotFoundError):
        AUDIO_OK = False
        music_sound = None
        zombie_sound = None


def start_music_after_user_action():
    """Démarre la musique après la première interaction utilisateur."""
    global music_started, music_channel
    if AUDIO_OK and not music_started and music_sound:
        try:
            music_channel = music_sound.play(loops=-1)
            music_started = True
        except pygame.error:
            pass


def spaced_text(text):
    return "   ".join(text.upper())


def draw_background():
    screen.blit(background, (0, 0))
    screen.blit(dark_overlay, (0, 0))


def draw_victory_counter(victories):
    txt = font_medium.render(f"Victoires : {victories}/4", True, GREEN)
    screen.blit(txt, txt.get_rect(center=(WIDTH // 2, 45)))


def draw_zombie():
    screen.blit(zombie_normal, zombie_normal.get_rect(center=(WIDTH // 2, 220)))


def draw_welcome(button_rect):
    draw_background()
    title = font_big.render(spaced_text("Zombie Memory"), True, WHITE)
    subtitle = font_medium.render("Teste ta mémoire et bats le zombie !", True, WHITE)
    tip = font_small.render("Sur smartphone : joue de préférence en mode paysage", True, WHITE)

    screen.blit(title, title.get_rect(center=(WIDTH // 2, 190)))
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 280)))
    screen.blit(tip, tip.get_rect(center=(WIDTH // 2, 335)))

    mouse = pygame.mouse.get_pos()
    color = GREEN if button_rect.collidepoint(mouse) else DARK_GREEN
    pygame.draw.rect(screen, color, button_rect, border_radius=22)
    pygame.draw.rect(screen, WHITE, button_rect, 4, border_radius=22)
    txt = font_medium.render("JOUER", True, BLACK)
    screen.blit(txt, txt.get_rect(center=button_rect.center))


def draw_sequence_action(victories, action):
    draw_background()
    draw_victory_counter(victories)
    draw_zombie()
    img = action_sequence_imgs[action]
    screen.blit(img, img.get_rect(center=(WIDTH // 2, 550)))
    msg = font_small.render("Mémorise la séquence...", True, WHITE)
    screen.blit(msg, msg.get_rect(center=(WIDTH // 2, 405)))


def draw_action_buttons(clicked_action, click_timer):
    """2 rangées de 3 grosses cartes, plus confortables au doigt."""
    rects = {}
    card_size = 150
    x_spacing = 45
    y_spacing = 22
    total_w = 3 * card_size + 2 * x_spacing
    start_x = WIDTH // 2 - total_w // 2
    start_y = 370

    for i, (key, img) in enumerate(actions.items()):
        col = i % 3
        row = i // 3
        x = start_x + col * (card_size + x_spacing)
        y = start_y + row * (card_size + y_spacing)
        base_rect = pygame.Rect(x, y, card_size, card_size)

        # Fond sombre + contour : améliore la lisibilité sur téléphone.
        pygame.draw.rect(screen, (15, 15, 15), base_rect, border_radius=18)
        pygame.draw.rect(screen, (220, 220, 220), base_rect, 3, border_radius=18)

        scaled = action_button_imgs[key]
        rect = scaled.get_rect(center=base_rect.center)

        if key == clicked_action and pygame.time.get_ticks() - click_timer < 250:
            pygame.draw.rect(
                screen, (0, 255, 0),
                base_rect.inflate(14, 14),
                5,
                border_radius=22,
            )
            scaled = action_button_big_imgs[key]
            rect = scaled.get_rect(center=base_rect.center)

        screen.blit(scaled, rect)
        rects[key] = base_rect

    return rects


def draw_input(victories, clicked_action, click_timer, progress):
    draw_background()
    draw_victory_counter(victories)
    draw_zombie()
    msg = font_small.render(f"À toi !  {progress}/3", True, WHITE)
    screen.blit(msg, msg.get_rect(center=(WIDTH // 2, 340)))
    return draw_action_buttons(clicked_action, click_timer)


def draw_ko(elapsed, duration):
    draw_background()
    # Animation très légère sans rotozoom/smoothscale à chaque frame.
    y = HEIGHT // 2 + (6 if (elapsed // 90) % 2 else -6)
    screen.blit(zombie_ko_large, zombie_ko_large.get_rect(center=(WIDTH // 2, y)))


def draw_attack(elapsed, duration):
    draw_background()
    # Petit tremblement horizontal sans recalculer l'image.
    x = WIDTH // 2 + (10 if (elapsed // 70) % 2 else -10)
    screen.blit(zombie_attack_large, zombie_attack_large.get_rect(center=(x, HEIGHT // 2)))


def draw_final():
    draw_background()
    lines = [
        "Félicitation, tu es prêt à combattre les zombies!",
    ]
    line_spacing = 39
    start_y = 55
    for i, line in enumerate(lines):
        if line:
            text = font_riddle.render(line, True, WHITE)
            screen.blit(text, text.get_rect(center=(WIDTH // 2, start_y + i * line_spacing)))

    screen.blit(
        zombie_final,
        zombie_final.get_rect(midbottom=(WIDTH // 2, HEIGHT - 12)),
    )


def reset_round():
    return random.sample(list(actions.keys()), 3), []


# Sur certains navigateurs mobiles, un seul toucher peut produire
# FINGERDOWN puis un MOUSEBUTTONDOWN synthétique.
_last_finger_time = -10000

def pointer_from_event(event):
    """Retourne une seule position par clic/toucher."""
    global _last_finger_time

    now = pygame.time.get_ticks()

    if event.type == pygame.FINGERDOWN:
        _last_finger_time = now
        return int(event.x * WIDTH), int(event.y * HEIGHT)

    if event.type == pygame.MOUSEBUTTONDOWN:
        # Ignore les clics souris générés automatiquement par un toucher.
        if getattr(event, "touch", False):
            return None
        # Sécurité supplémentaire pour les navigateurs qui n'exposent
        # pas correctement l'attribut "touch".
        if now - _last_finger_time < 500:
            return None
        return event.pos

    return None


async def main():
    victories = 0
    sequence, player_sequence = reset_round()
    clicked_action = None
    click_timer = 0

    state = "welcome"
    state_started = pygame.time.get_ticks()
    sequence_index = 0
    rects = {}
    button_rect = pygame.Rect(WIDTH // 2 - 180, 420, 360, 95)

    running = True
    while running:
        now = pygame.time.get_ticks()

        # ---------- événements ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            pos = pointer_from_event(event)
            if pos is None:
                continue

            if state == "welcome" and button_rect.collidepoint(pos):
                start_music_after_user_action()
                sequence, player_sequence = reset_round()
                sequence_index = 0
                state = "sequence_show"
                state_started = now

            elif state == "input":
                for action, rect in rects.items():
                    if rect.collidepoint(pos):
                        clicked_action = action
                        click_timer = now
                        player_sequence.append(action)

                        if len(player_sequence) >= 3:
                            if player_sequence == sequence:
                                victories += 1
                                state = "ko"
                                state_started = now
                            else:
                                if zombie_sound:
                                    try:
                                        zombie_sound.play()
                                    except pygame.error:
                                        pass
                                state = "attack"
                                state_started = now
                        break

        # ---------- mise à jour / dessin ----------
        if state == "welcome":
            draw_welcome(button_rect)

        elif state == "sequence_show":
            draw_sequence_action(victories, sequence[sequence_index])
            if now - state_started >= 1200:
                state = "sequence_gap"
                state_started = now

        elif state == "sequence_gap":
            draw_background()
            draw_victory_counter(victories)
            draw_zombie()
            if now - state_started >= 300:
                sequence_index += 1
                if sequence_index >= len(sequence):
                    state = "input"
                    state_started = now
                    player_sequence = []
                    clicked_action = None
                else:
                    state = "sequence_show"
                    state_started = now

        elif state == "input":
            rects = draw_input(victories, clicked_action, click_timer, len(player_sequence))

        elif state == "ko":
            duration = 900
            draw_ko(now - state_started, duration)
            if now - state_started >= duration:
                if victories >= 4:
                    state = "final"
                else:
                    sequence, player_sequence = reset_round()
                    sequence_index = 0
                    clicked_action = None
                    state = "sequence_show"
                    state_started = now

        elif state == "attack":
            duration = 1100
            draw_attack(now - state_started, duration)
            if now - state_started >= duration:
                if zombie_sound:
                    zombie_sound.stop()
                sequence, player_sequence = reset_round()
                sequence_index = 0
                clicked_action = None
                state = "sequence_show"
                state_started = now

        elif state == "final":
            draw_final()

        pygame.display.flip()

        # Pygbag/Emscripten est déjà cadencé par le navigateur.
        # Un clock.tick() bloquant peut affamer l'audio WebAssembly.
        if sys.platform != "emscripten":
            clock.tick(60)

        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
