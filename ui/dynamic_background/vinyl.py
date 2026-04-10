from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

import pygame

from core.动态背景 import (
    DynamicBackgroundBase,
    DynamicBackgroundContext,
    clamp,
    clamp_int,
    ease_out_cubic,
    lerp,
)


class VinylDynamicBackground(DynamicBackgroundBase):
    mode_name = "唱片"
    _STATE_ENTER_DURATION = 3.0
    _STATE_LEAVE_DURATION = 0.9
    _STATE4_ASTRONAUT_BURST_COMBO_STEP = 50
    _FRAME_CENTER_OFFSET_X = 0
    _FRAME_CENTER_OFFSET_Y = -3.43
    _RECORD_SIZE_RATIO_X = 0.235
    _RECORD_SIZE_RATIO_Y = 0.42
    _RECORD_SIZE_MIN = 220
    _RECORD_SIZE_MAX = 460
    _RECORD_ROTATION_SPEED = 56.0

    _SIDE_LINE_CONFIGS = (
        {"asset": "矩形长.png", "offset": -0.21, "travel": 0.24, "duration": 6.8, "delay": -3.8, "width_scale": 0.31},
        {"asset": "矩形短.png", "offset": -0.10, "travel": 0.17, "duration": 5.1, "delay": -1.7, "width_scale": 0.14},
        {"asset": "矩形最短.png", "offset": 0.00, "travel": 0.12, "duration": 4.4, "delay": -0.9, "width_scale": 0.08},
        {"asset": "矩形短.png", "offset": 0.11, "travel": 0.18, "duration": 5.8, "delay": -2.4, "width_scale": 0.16},
        {"asset": "矩形最短.png", "offset": 0.23, "travel": 0.14, "duration": 4.9, "delay": -2.1, "width_scale": 0.08},
    )

    def __init__(self, resource_root: str = "", runtime_root: str = "", project_root: str = ""):
        super().__init__(resource_root=resource_root, runtime_root=runtime_root, project_root=project_root)
        self._warp_stars: List[Dict[str, float]] = []
        self._particles: List[Dict[str, float]] = []
        self._machine_reveal: float = 0.0
        self._astronaut_reveal: float = 0.0
        self._astronaut_reentry: float = 1.0
        self._frame_reveal: float = 0.0
        self._combo_state: int = 1
        self._state4_next_burst_combo: int = 200

    def reset(self):
        self._warp_stars = []
        self._particles = []
        self._machine_reveal = 0.0
        self._astronaut_reveal = 0.0
        self._astronaut_reentry = 1.0
        self._frame_reveal = 0.0
        self._combo_state = 1
        self._state4_next_burst_combo = 200

    def _resolve_combo_state(self, combo: int) -> int:
        value = int(max(0, combo))
        if value >= 150:
            return 4
        if value >= 100:
            return 3
        if value >= 50:
            return 2
        return 1

    def _particle_profile(self, combo_state: int) -> Dict[str, float]:
        table = (
            {"target": 36, "speed_min": 42.0, "speed_max": 96.0, "size_min": 1.0, "size_max": 2.4},
            {"target": 48, "speed_min": 48.0, "speed_max": 116.0, "size_min": 1.1, "size_max": 2.6},
            {"target": 60, "speed_min": 58.0, "speed_max": 138.0, "size_min": 1.2, "size_max": 3.0},
            {"target": 72, "speed_min": 66.0, "speed_max": 160.0, "size_min": 1.3, "size_max": 3.4},
        )
        return dict(table[max(0, min(len(table) - 1, combo_state - 1))])

    def _warp_star_target(self, combo_state: int) -> int:
        return (160, 176, 192, 208)[max(0, min(3, combo_state - 1))]

    def _reset_warp_star(self, star: Dict[str, float], *, far_spawn: bool = False):
        spawn_min = 0.72 if bool(far_spawn) else 0.18
        star["x"] = random.uniform(-1.04, 1.04)
        star["y"] = random.uniform(-0.68, 0.68)
        star["z"] = random.uniform(spawn_min, 1.0)
        star["prev_z"] = float(star["z"])
        star["speed"] = random.uniform(0.72, 1.28)
        star["size_bias"] = random.uniform(0.8, 1.35)
        star["twinkle"] = random.uniform(0.75, 1.35)

    def _sync_warp_stars(self, combo_state: int):
        target = int(self._warp_star_target(combo_state))
        while len(self._warp_stars) < target:
            star: Dict[str, float] = {}
            self._reset_warp_star(star, far_spawn=False)
            self._warp_stars.append(star)
        if len(self._warp_stars) > target:
            del self._warp_stars[target:]

    def _update_warp_stars(self, delta_time: float, combo_state: int, screen_size: Tuple[int, int]):
        width, height = screen_size
        center_x = float(width) * 0.5
        center_y = float(height) * 0.5
        scale = float(min(width, height)) * 0.84
        speed_base = 0.27 + (combo_state - 1) * 0.022
        self._sync_warp_stars(combo_state)
        for star in self._warp_stars:
            previous_z = float(star.get("z", 1.0))
            star["prev_z"] = previous_z
            star["z"] = previous_z - float(delta_time) * speed_base * float(star.get("speed", 1.0))
            current_z = float(star["z"])
            if current_z <= 0.085:
                self._reset_warp_star(star, far_spawn=True)
                continue
            screen_x = center_x + (float(star["x"]) / current_z) * scale
            screen_y = center_y + (float(star["y"]) / current_z) * scale
            margin = 48.0
            if screen_x < -margin or screen_x > float(width) + margin or screen_y < -margin or screen_y > float(height) + margin:
                self._reset_warp_star(star, far_spawn=True)

    def _step_reveal(self, current: float, target: float, delta_time: float) -> float:
        current = clamp(float(current), 0.0, 1.0)
        target = clamp(float(target), 0.0, 1.0)
        delta_time = max(0.0, float(delta_time))
        if target > current:
            duration = max(0.001, float(self._STATE_ENTER_DURATION))
            return min(target, current + delta_time / duration)
        if target < current:
            duration = max(0.001, float(self._STATE_LEAVE_DURATION))
            return max(target, current - delta_time / duration)
        return current

    def _spawn_particle(
        self,
        origin_x: float,
        origin_y: float,
        profile: Dict[str, float],
        spread: float = 18.0,
        scale: float = 1.0,
        *,
        color: Tuple[int, int, int] = (255, 255, 255),
        halo_color: Optional[Tuple[int, int, int]] = None,
        layer: str = "base",
        life_scale: float = 1.0,
        size_scale: float = 1.0,
    ):
        angle = random.random() * math.tau
        speed = lerp(profile["speed_min"], profile["speed_max"], random.random()) * float(scale)
        acceleration = lerp(14.0, 30.0, random.random()) * float(scale)
        particle_color = tuple(int(max(0, min(255, v))) for v in color)
        particle_halo_color = halo_color if halo_color is not None else particle_color
        self._particles.append(
            {
                "x": float(origin_x) + (random.random() - 0.5) * float(spread),
                "y": float(origin_y) + (random.random() - 0.5) * float(spread),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "ax": math.cos(angle) * acceleration,
                "ay": math.sin(angle) * acceleration,
                "life": 0.0,
                "max_life": lerp(0.85, 1.45, random.random()) * float(max(0.2, life_scale)),
                "size": lerp(profile["size_min"], profile["size_max"], random.random()) * float(max(0.2, size_scale)),
                "flicker": lerp(0.7, 1.5, random.random()),
                "color": particle_color,
                "halo_color": tuple(int(max(0, min(255, v))) for v in particle_halo_color),
                "layer": str(layer or "base"),
            }
        )

    def _emit_burst(
        self,
        count: int,
        origin_x: float,
        origin_y: float,
        profile: Dict[str, float],
        spread: float = 20.0,
        scale: float = 1.0,
        *,
        color: Tuple[int, int, int] = (255, 255, 255),
        halo_color: Optional[Tuple[int, int, int]] = None,
        layer: str = "base",
        life_scale: float = 1.0,
        size_scale: float = 1.0,
    ):
        for _ in range(int(max(0, count))):
            self._spawn_particle(
                origin_x,
                origin_y,
                profile,
                spread=spread,
                scale=scale,
                color=color,
                halo_color=halo_color,
                layer=layer,
                life_scale=life_scale,
                size_scale=size_scale,
            )

    def _update_particles(self, delta_time: float, combo_state: int, center_x: float, center_y: float):
        for index in range(len(self._particles) - 1, -1, -1):
            particle = self._particles[index]
            particle["life"] += float(delta_time)
            if particle["life"] >= particle["max_life"]:
                self._particles.pop(index)
                continue
            particle["vx"] += particle["ax"] * float(delta_time)
            particle["vy"] += particle["ay"] * float(delta_time)
            particle["x"] += particle["vx"] * float(delta_time)
            particle["y"] += particle["vy"] * float(delta_time)

    def _emit_astronaut_highlight_burst(
        self,
        profile: Dict[str, float],
        screen_size: Tuple[int, int],
        record_half: float,
        *,
        strength: float = 1.0,
    ):
        metrics = self._get_astronaut_metrics(screen_size, record_half)
        center_y = float(metrics["center_y"])
        left_center_x = float(metrics["left_center_x"])
        right_center_x = float(metrics["right_center_x"])
        left_inner_x = float(metrics["left_inner_x"])
        right_inner_x = float(metrics["right_inner_x"])
        left_outer_x = float(metrics["left_outer_x"])
        right_outer_x = float(metrics["right_outer_x"])
        burst_strength = max(0.65, float(strength))
        for origin_x, origin_y in (
            (left_outer_x, center_y),
            (left_inner_x, center_y - 8.0),
            (right_inner_x, center_y - 8.0),
            (right_outer_x, center_y),
        ):
            self._emit_burst(
                int(round(10 * burst_strength)),
                origin_x,
                origin_y,
                profile,
                spread=14.0 + 4.0 * burst_strength,
                scale=1.04 + 0.10 * burst_strength,
                color=(255, 255, 255),
                halo_color=(255, 188, 188),
                layer="astronaut",
                life_scale=1.00,
                size_scale=1.18 * burst_strength,
            )
            self._emit_burst(
                int(round(14 * burst_strength)),
                origin_x,
                origin_y,
                profile,
                spread=28.0 + 6.0 * burst_strength,
                scale=1.28 + 0.14 * burst_strength,
                color=(255, 244, 244),
                halo_color=(255, 92, 92),
                layer="astronaut",
                life_scale=1.28,
                size_scale=1.56 * burst_strength,
            )
        for origin_x in (left_center_x, right_center_x):
            self._emit_burst(
                int(round(6 * burst_strength)),
                origin_x,
                center_y,
                profile,
                spread=44.0 + 8.0 * burst_strength,
                scale=1.46 + 0.14 * burst_strength,
                color=(255, 252, 252),
                halo_color=(255, 68, 68),
                layer="astronaut",
                life_scale=1.52,
                size_scale=2.05 * burst_strength,
            )

    def _tick_state4_astronaut_bursts(
        self,
        combo: int,
        combo_state: int,
        profile: Dict[str, float],
        screen_size: Tuple[int, int],
        record_half: float,
    ):
        if combo_state < 4:
            self._state4_next_burst_combo = 200
            return
        current_combo = int(max(0, combo))
        while current_combo >= int(self._state4_next_burst_combo):
            self._emit_astronaut_highlight_burst(
                profile,
                screen_size,
                record_half,
                strength=1.25,
            )
            self._astronaut_reentry = 0.0
            self._state4_next_burst_combo += int(self._STATE4_ASTRONAUT_BURST_COMBO_STEP)

    def _get_record_size(
        self,
        size: Tuple[int, int],
        *,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
    ) -> int:
        width, height = size
        target = min(
            float(width) * float(self._RECORD_SIZE_RATIO_X),
            float(height) * float(self._RECORD_SIZE_RATIO_Y),
        )
        minimum = int(self._RECORD_SIZE_MIN if minimum is None else minimum)
        maximum = int(self._RECORD_SIZE_MAX if maximum is None else maximum)
        return clamp_int(target, minimum, max(minimum, maximum))

    def _get_record_rotation_phase(self, now: float) -> float:
        phase = math.fmod(float(now) * float(self._RECORD_ROTATION_SPEED), 360.0)
        if phase < 0.0:
            phase += 360.0
        return phase

    def _get_record_renderer_angle(self, now: float) -> float:
        return self._get_record_rotation_phase(now)

    def _get_record_surface_angle(self, now: float) -> float:
        return -self._get_record_rotation_phase(now)

    def update(self, context: DynamicBackgroundContext):
        delta_time = clamp(float(context.delta_time or 0.0), 0.0, 0.05)
        combo_state = self._resolve_combo_state(context.combo)
        profile = self._particle_profile(combo_state)
        width, height = context.screen_size
        center_x = float(width) * 0.5
        center_y = float(height) * 0.5
        record_size = self._get_record_size((width, height))
        record_half = float(record_size) * 0.5

        if combo_state != int(self._combo_state):
            self._emit_burst(
                int(max(10, round(profile["target"] * 0.32))),
                center_x,
                center_y,
                profile,
                spread=24.0,
                scale=1.04,
            )
            if combo_state >= 3 and int(self._combo_state) < 3:
                self._emit_astronaut_highlight_burst(
                    profile,
                    (width, height),
                    record_half,
                    strength=1.0,
                )
                self._astronaut_reentry = 0.0
            if combo_state >= 4 and int(self._combo_state) < 4:
                self._emit_astronaut_highlight_burst(
                    profile,
                    (width, height),
                    record_half,
                    strength=1.25,
                )
                self._astronaut_reentry = 0.0
                current_combo = int(max(0, context.combo))
                step = int(max(1, self._STATE4_ASTRONAUT_BURST_COMBO_STEP))
                self._state4_next_burst_combo = max(200, ((current_combo // step) + 1) * step)

        self._machine_reveal = self._step_reveal(
            self._machine_reveal,
            1.0 if combo_state >= 2 else 0.0,
            delta_time,
        )
        self._astronaut_reveal = self._step_reveal(
            self._astronaut_reveal,
            1.0 if combo_state >= 3 else 0.0,
            delta_time,
        )
        if combo_state >= 3:
            self._astronaut_reentry = min(1.0, float(self._astronaut_reentry) + float(delta_time) / 0.86)
        else:
            self._astronaut_reentry = 1.0
        self._frame_reveal = self._step_reveal(
            self._frame_reveal,
            1.0 if combo_state >= 4 else 0.0,
            delta_time,
        )
        self._combo_state = combo_state
        self._update_warp_stars(delta_time, combo_state, context.screen_size)
        self._update_particles(delta_time, combo_state, center_x, center_y)
        self._tick_state4_astronaut_bursts(
            int(context.combo or 0),
            combo_state,
            profile,
            (width, height),
            record_half,
        )

    def _draw_particles(self, renderer, layer: Optional[str] = None):
        for particle in self._particles:
            particle_layer = str(particle.get("layer", "base"))
            if layer is not None and particle_layer != str(layer):
                continue
            progress = clamp(float(particle["life"]) / max(0.001, float(particle["max_life"])), 0.0, 1.0)
            is_astronaut_layer = particle_layer == "astronaut"
            wave = 0.90 + math.sin(float(particle["life"]) * 10.0 * float(particle["flicker"])) * (0.10 if is_astronaut_layer else 0.16)
            alpha = clamp((1.0 - progress) * wave, 0.0, 1.0)
            outer_alpha = clamp_int(alpha * (54.0 if is_astronaut_layer else 0.0), 0, 255)
            halo_alpha = clamp_int(alpha * (132.0 if is_astronaut_layer else 64.0), 0, 255)
            core_alpha = clamp_int(alpha * 255.0, 0, 255)
            core_size = clamp_int(float(particle["size"]) + progress * (2.2 if is_astronaut_layer else 1.4), 1, 7 if is_astronaut_layer else 5)
            halo_size = clamp_int(float(particle["size"]) + progress * (8.6 if is_astronaut_layer else 5.2), 3 if is_astronaut_layer else 2, 18 if is_astronaut_layer else 10)
            outer_size = clamp_int(halo_size + (6 if is_astronaut_layer else 0) + progress * (4.0 if is_astronaut_layer else 0.0), halo_size, 24 if is_astronaut_layer else halo_size)
            x = int(round(float(particle["x"])))
            y = int(round(float(particle["y"])))
            halo_color = tuple(int(max(0, min(255, v))) for v in particle.get("halo_color", (255, 255, 255)))
            core_color = tuple(int(max(0, min(255, v))) for v in particle.get("color", (255, 255, 255)))
            if is_astronaut_layer and outer_alpha > 2:
                self._set_draw_color(renderer, halo_color, outer_alpha)
                try:
                    renderer.fill_rect(pygame.Rect(int(x - outer_size // 2), int(y - outer_size // 2), int(outer_size), int(outer_size)))
                except Exception:
                    pass
            self._set_draw_color(renderer, halo_color, halo_alpha)
            try:
                renderer.fill_rect(pygame.Rect(int(x - halo_size // 2), int(y - halo_size // 2), int(halo_size), int(halo_size)))
            except Exception:
                pass
            self._set_draw_color(renderer, core_color, core_alpha)
            try:
                renderer.fill_rect(pygame.Rect(int(x - core_size // 2), int(y - core_size // 2), int(core_size), int(core_size)))
            except Exception:
                pass

    def _draw_warp_stars(self, renderer, screen_size: Tuple[int, int], now: float):
        width, height = screen_size
        center_x = float(width) * 0.5
        center_y = float(height) * 0.5
        scale = float(min(width, height)) * 0.84
        for star in self._warp_stars:
            current_z = max(0.001, float(star.get("z", 1.0)))
            previous_z = max(current_z, float(star.get("prev_z", current_z)))
            x = center_x + (float(star.get("x", 0.0)) / current_z) * scale
            y = center_y + (float(star.get("y", 0.0)) / current_z) * scale
            prev_x = center_x + (float(star.get("x", 0.0)) / previous_z) * scale
            prev_y = center_y + (float(star.get("y", 0.0)) / previous_z) * scale
            if x < -24.0 or x > float(width) + 24.0 or y < -24.0 or y > float(height) + 24.0:
                continue
            depth = clamp(1.0 - current_z, 0.0, 1.0)
            twinkle = 0.88 + 0.12 * math.sin(float(now) * (2.6 + float(star.get("twinkle", 1.0))) + float(star.get("size_bias", 1.0)))
            alpha = clamp_int((76.0 + depth * 172.0) * twinkle, 0, 255)
            if alpha <= 2:
                continue
            self._set_draw_color(renderer, (255, 255, 255), clamp_int(alpha * 0.78, 0, 255))
            try:
                renderer.draw_line((int(round(prev_x)), int(round(prev_y))), (int(round(x)), int(round(y))))
            except Exception:
                pass
            size = clamp_int(1.0 + depth * 2.6 * float(star.get("size_bias", 1.0)), 1, 5)
            halo_size = clamp_int(size + 2 + depth * 2.0, 2, 8)
            self._set_draw_color(renderer, (255, 255, 255), clamp_int(alpha * 0.26, 0, 255))
            try:
                renderer.fill_rect(
                    pygame.Rect(
                        int(round(x - halo_size * 0.5)),
                        int(round(y - halo_size * 0.5)),
                        int(halo_size),
                        int(halo_size),
                    )
                )
            except Exception:
                pass
            self._set_draw_color(renderer, (255, 255, 255), alpha)
            try:
                renderer.fill_rect(
                    pygame.Rect(
                        int(round(x - size * 0.5)),
                        int(round(y - size * 0.5)),
                        int(size),
                        int(size),
                    )
                )
            except Exception:
                pass

    def _generated_spotlight(self, key: str, size: Tuple[int, int], color: Tuple[int, int, int]):
        cache_key = f"generated:spotlight:{key}:{size[0]}:{size[1]}:{color[0]}:{color[1]}:{color[2]}"
        old = self._surface_cache.get(cache_key, None)
        if old is not None:
            return old
        width, height = size
        surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        for index in range(9, 0, -1):
            ratio = float(index) / 9.0
            alpha = clamp_int((ratio ** 2.0) * 28.0, 0, 255)
            points = [
                (0, 0),
                (int(width * (0.24 + 0.58 * ratio)), int(height * (0.06 + 0.16 * ratio))),
                (int(width * (0.06 + 0.16 * ratio)), int(height * (0.24 + 0.58 * ratio))),
            ]
            try:
                pygame.draw.polygon(surface, (*color, alpha), points)
            except Exception:
                continue
        try:
            pygame.draw.circle(surface, (255, 238, 238, 54), (0, 0), int(max(width, height) * 0.10))
        except Exception:
            pass
        self._surface_cache[cache_key] = surface
        return surface

    def _draw_background_layer(self, renderer, screen_size: Tuple[int, int]):
        width, height = screen_size
        surface = self._load_image("asset:bg", "UI-img", "动态背景", "唱片", "素材", "背景.png")
        texture = self._get_texture(renderer, "asset:bg", surface)
        if texture is None or surface is None:
            return
        src_w = max(1, surface.get_width())
        src_h = max(1, surface.get_height())
        scale = max(float(width) / float(src_w), float(height) / float(src_h))
        draw_w = clamp_int(src_w * scale, 1, max(src_w, width * 2))
        draw_h = clamp_int(src_h * scale, 1, max(src_h, height * 2))
        self._draw_texture(
            texture,
            (int((width - draw_w) * 0.5), int((height - draw_h) * 0.5), int(draw_w), int(draw_h)),
            alpha=255,
        )

    def _draw_corner_spotlights(self, renderer, screen_size: Tuple[int, int], now: float):
        width, height = screen_size
        spot_surface = self._generated_spotlight("red", (384, 320), (255, 72, 72))
        spot_texture = self._get_texture(renderer, "generated:spotlight:red", spot_surface)
        if spot_texture is None:
            return
        def _beam_intensity(time_value: float, cycle: float, phase_offset: float) -> float:
            phase = ((float(time_value) + float(phase_offset)) / max(0.001, float(cycle))) % 1.0
            if phase < 0.18:
                return ease_out_cubic(phase / 0.18)
            if phase < 0.34:
                return 1.0
            if phase < 0.56:
                return 1.0 - ease_out_cubic((phase - 0.34) / 0.22)
            return 0.0

        pulse_left = _beam_intensity(now, 4.8, 0.0)
        pulse_right = _beam_intensity(now, 5.2, 1.65)
        if pulse_left <= 0.001 and pulse_right <= 0.001:
            return
        draw_w = clamp_int(width * 0.34, 260, 560)
        draw_h = clamp_int(height * 0.42, 180, 380)
        if pulse_left > 0.001:
            self._draw_texture(
                spot_texture,
                (float(-width * 0.05), float(-height * 0.05), float(draw_w), float(draw_h)),
                alpha=clamp_int(170.0 * pulse_left, 0, 255),
            )
        if pulse_right > 0.001:
            self._draw_texture(
                spot_texture,
                (float(width - draw_w + width * 0.05), float(height - draw_h + height * 0.05), float(draw_w), float(draw_h)),
                alpha=clamp_int(162.0 * pulse_right, 0, 255),
                flip_x=True,
                flip_y=True,
            )

    def _draw_core_glow(self, renderer, center_x: int, center_y: int, size: int, now: float):
        cache_key = "generated:core"
        old = self._surface_cache.get(cache_key, None)
        if old is None:
            surface = pygame.Surface((192, 192), pygame.SRCALPHA, 32)
            center = (96, 96)
            for index in range(12, 0, -1):
                ratio = float(index) / 12.0
                alpha = clamp_int((ratio ** 2.1) * 28.0, 0, 255)
                try:
                    pygame.draw.circle(surface, (255, 88, 72, alpha), center, int(92 * ratio))
                except Exception:
                    continue
            self._surface_cache[cache_key] = surface
            old = surface
        texture = self._get_texture(renderer, cache_key, old)
        if texture is None:
            return
        pulse = 0.56 + 0.18 * math.sin(float(now) * 2.1)
        self._draw_texture(texture, (int(center_x - size // 2), int(center_y - size // 2), int(size), int(size)), alpha=clamp_int(190.0 * pulse, 0, 255))

    def _draw_center_bars(self, renderer, screen_size: Tuple[int, int], record_half: float):
        reveal = ease_out_cubic(self._machine_reveal)
        if reveal <= 0.01:
            return
        width, height = screen_size
        center_x = int(width * 0.5)
        center_y = int(height * 0.5)
        gap = float(max(12.0, record_half - 6.0))
        texture = self._get_texture(
            renderer,
            "asset:line-long",
            self._load_image("asset:line-long", "UI-img", "动态背景", "唱片", "素材", "矩形长.png"),
        )
        surface = self._load_image("asset:line-long", "UI-img", "动态背景", "唱片", "素材", "矩形长.png")
        if texture is None or surface is None:
            return
        max_width = clamp_int(width * 0.74, 220, 1480)
        draw_width = clamp_int(max_width * max(0.08, reveal), 8, max_width)
        draw_height = clamp_int(draw_width * (surface.get_height() / max(1, surface.get_width())), 6, 18)
        alpha = clamp_int(255.0 * reveal, 0, 255)
        self._draw_texture(
            texture,
            (int(center_x - gap - draw_width), int(center_y - draw_height * 0.5), int(draw_width), int(draw_height)),
            alpha=alpha,
            flip_x=True,
        )
        self._draw_texture(
            texture,
            (int(center_x + gap), int(center_y - draw_height * 0.5), int(draw_width), int(draw_height)),
            alpha=alpha,
        )

    def _draw_side_lines(self, renderer, screen_size: Tuple[int, int], now: float, record_half: float):
        reveal = ease_out_cubic(self._machine_reveal)
        if reveal <= 0.01:
            return
        width, height = screen_size
        center_x = float(width) * 0.5
        center_y = float(height) * 0.5
        start_gap = float(max(12.0, record_half - 6.0))
        asset_cache = {}
        for config in self._SIDE_LINE_CONFIGS:
            asset = str(config["asset"])
            if asset not in asset_cache:
                surface = self._load_image(f"asset:{asset}", "UI-img", "动态背景", "唱片", "素材", asset)
                texture = self._get_texture(renderer, f"asset:{asset}", surface)
                asset_cache[asset] = (surface, texture)
            surface, texture = asset_cache[asset]
            if surface is None or texture is None:
                continue

            progress = (float(now) + float(config["delay"])) / max(0.001, float(config["duration"]))
            progress = progress - math.floor(progress)
            if progress < 0.12:
                scale = lerp(0.22, 1.0, progress / 0.12)
                alpha_scale = progress / 0.12
            else:
                scale = 1.0
                alpha_scale = 1.0
            if progress > 0.80:
                alpha_scale *= clamp((1.0 - progress) / 0.20, 0.0, 1.0)
            alpha = clamp_int(255.0 * alpha_scale * reveal, 0, 255)
            if alpha <= 2:
                continue

            base_width = clamp_int(width * float(config["width_scale"]), 65, 640)
            travel = float(width) * float(config["travel"]) * reveal
            draw_width = clamp_int(base_width * scale, 16, base_width)
            draw_height = clamp_int(draw_width * (surface.get_height() / max(1, surface.get_width())), 6, 20)
            y = int(round(center_y + float(height) * float(config["offset"]) - draw_height * 0.5))
            offset = travel * progress
            left_x = int(round(center_x - start_gap - draw_width - offset))
            right_x = int(round(center_x + start_gap + offset))

            self._draw_texture(texture, (left_x, y, int(draw_width), int(draw_height)), alpha=alpha, flip_x=True)
            self._draw_texture(texture, (right_x, y, int(draw_width), int(draw_height)), alpha=alpha)

    def _draw_machine_and_record(self, renderer, screen_size: Tuple[int, int], now: float):
        width, height = screen_size
        center_x = int(width * 0.5)
        center_y = int(height * 0.5)
        record_size = self._get_record_size(screen_size)
        record_half = float(record_size) * 0.5
        machine_progress = ease_out_cubic(self._machine_reveal)

        self._draw_core_glow(renderer, center_x, center_y, clamp_int(record_size * 0.68, 120, 220), now)
        self._draw_center_bars(renderer, screen_size, record_half)

        machine_alpha = clamp_int(235.0 * machine_progress, 0, 255)
        machine_width = clamp_int(record_size * 1.12, 248, 430)
        for key, filename, anchor_y in (
            ("asset:machine-bottom", "唱片机-下.png", center_y + record_half - 4.0),
            ("asset:machine-top", "唱片机-上.png", center_y - record_half + 4.0),
        ):
            surface = self._load_image(key, "UI-img", "动态背景", "唱片", "素材", filename)
            texture = self._get_texture(renderer, key, surface)
            if texture is None or surface is None or machine_alpha <= 2:
                continue
            draw_width = int(machine_width)
            draw_height = clamp_int(draw_width * (surface.get_height() / max(1, surface.get_width())), 10, 220)
            hidden_shift = lerp(record_half * 0.82, 0.0, machine_progress)
            if "top" in key:
                anchor_y += hidden_shift
            else:
                anchor_y -= hidden_shift
            self._draw_texture(
                texture,
                (
                    float(center_x - draw_width * 0.5),
                    float(anchor_y - draw_height * 0.5),
                    float(draw_width),
                    float(draw_height),
                ),
                alpha=machine_alpha,
            )

        record_surface = self._load_image("asset:record", "UI-img", "动态背景", "唱片", "素材", "唱片.png")
        record_texture = self._get_texture(renderer, "asset:record", record_surface)
        if record_texture is not None:
            self._draw_texture(
                record_texture,
                (float(center_x - record_size * 0.5), float(center_y - record_size * 0.5), float(record_size), float(record_size)),
                alpha=255,
                angle=self._get_record_renderer_angle(now),
            )

        return {"center_x": center_x, "center_y": center_y, "record_half": record_half}

    def _draw_actor(
        self,
        renderer,
        texture_key: str,
        filename: str,
        center_x: float,
        center_y: float,
        width: int,
        height: int,
        reveal: float,
        direction: int,
        now: float,
        with_outline: bool,
    ):
        surface = self._load_image(texture_key, "UI-img", "动态背景", "唱片", "素材", filename)
        texture = self._get_texture(renderer, texture_key, surface)
        if texture is None or reveal <= 0.01:
            return
        settle = ease_out_cubic(clamp(float(getattr(self, "_astronaut_reentry", 1.0)), 0.0, 1.0))
        flash = 1.0 - settle
        breathe_scale = 1.0 + math.sin(float(now) * 1.18 + (0.0 if direction < 0 else 1.05)) * 0.010 * reveal
        scale = (0.94 + reveal * 0.06) * breathe_scale * lerp(0.96, 1.0, settle)
        draw_width = clamp_int(width * scale, 8, max(8, int(round(width * 1.08))))
        draw_height = clamp_int(height * scale, 8, max(8, int(round(height * 1.08))))
        dst = (
            float(center_x - draw_width * 0.5),
            float(center_y - draw_height * 0.5),
            float(draw_width),
            float(draw_height),
        )
        alpha = clamp_int(255.0 * reveal * (0.62 + 0.38 * settle), 0, 255)
        if flash > 0.01:
            aura_pad = 10.0 + flash * 18.0
            aura_alpha = clamp_int((18.0 + 78.0 * flash) * reveal, 0, 255)
            self._draw_texture(
                texture,
                (float(dst[0] - aura_pad), float(dst[1] - aura_pad), float(dst[2] + aura_pad * 2.0), float(dst[3] + aura_pad * 2.0)),
                alpha=aura_alpha,
                color=(255, 76, 76),
            )
        if with_outline:
            outline_alpha = clamp_int((92.0 + 70.0 * (0.5 + 0.5 * math.sin(float(now) * 1.7)) + 86.0 * flash) * reveal, 0, 255)
            outline_offset = 2.0 + flash * 2.2
            for dx, dy in ((-outline_offset, 0.0), (outline_offset, 0.0), (0.0, -outline_offset), (0.0, outline_offset)):
                self._draw_texture(
                    texture,
                    (float(dst[0] + dx), float(dst[1] + dy), float(dst[2]), float(dst[3])),
                    alpha=outline_alpha,
                    color=(255, 84, 84),
                )
            glow_alpha = clamp_int((56.0 + 64.0 * (0.5 + 0.5 * math.sin(float(now) * 1.7)) + 108.0 * flash) * reveal, 0, 255)
            glow_pad = 7.0 + flash * 12.0
            self._draw_texture(
                texture,
                (float(dst[0] - glow_pad), float(dst[1] - glow_pad), float(dst[2] + glow_pad * 2.0), float(dst[3] + glow_pad * 2.0)),
                alpha=glow_alpha,
                color=(255, 72, 72),
            )
        self._draw_texture(texture, dst, alpha=alpha)

    def _get_astronaut_metrics(self, screen_size: Tuple[int, int], record_half: float) -> Dict[str, float]:
        width, height = screen_size
        center_x = float(width) * 0.5
        center_y = float(height) * 0.5
        stage4_boost = ease_out_cubic(clamp(float(getattr(self, "_frame_reveal", 0.0)), 0.0, 1.0))
        astronaut_scale = lerp(1.08, 1.32, stage4_boost)
        record_overlap = lerp(record_half * 0.18, record_half * 0.25, stage4_boost)
        left_width = clamp_int(width * 0.170 * astronaut_scale, 176, 420)
        right_width = clamp_int(width * 0.170 * astronaut_scale, 176, 420)
        left_center_x = center_x - record_half - left_width * 0.5 + min(width * 0.018, 26.0) + record_overlap
        right_center_x = center_x + record_half + right_width * 0.5 - min(width * 0.016, 24.0) - record_overlap
        return {
            "center_y": center_y,
            "left_width": float(left_width),
            "right_width": float(right_width),
            "left_center_x": left_center_x,
            "right_center_x": right_center_x,
            "left_inner_x": left_center_x + left_width * 0.18,
            "right_inner_x": right_center_x - right_width * 0.18,
            "left_outer_x": left_center_x - left_width * 0.10,
            "right_outer_x": right_center_x + right_width * 0.10,
        }

    def _draw_astronauts(self, renderer, screen_size: Tuple[int, int], record_half: float, now: float):
        reveal = ease_out_cubic(self._astronaut_reveal)
        if reveal <= 0.01:
            return
        metrics = self._get_astronaut_metrics(screen_size, record_half)
        stage4_active = self._frame_reveal > 0.01
        left_texture_key = "asset:astronaut-left-outline" if stage4_active else "asset:astronaut-left"
        right_texture_key = "asset:astronaut-right-outline" if stage4_active else "asset:astronaut-right"
        left_filename = "宇航员左侧-带描边.png" if stage4_active else "宇航员左侧.png"
        right_filename = "宇航员右侧-带描边.png" if stage4_active else "宇航员右侧.png"
        left_width = int(metrics["left_width"])
        right_width = int(metrics["right_width"])
        left_surface = self._load_image(left_texture_key, "UI-img", "动态背景", "唱片", "素材", left_filename)
        right_surface = self._load_image(right_texture_key, "UI-img", "动态背景", "唱片", "素材", right_filename)
        left_height = clamp_int(left_width * (left_surface.get_height() / max(1, left_surface.get_width())) if left_surface else left_width, 40, 520)
        right_height = clamp_int(right_width * (right_surface.get_height() / max(1, right_surface.get_width())) if right_surface else right_width, 40, 520)
        center_y = float(metrics["center_y"])
        self._draw_actor(renderer, left_texture_key, left_filename, float(metrics["left_center_x"]), center_y, left_width, left_height, reveal, -1, now, stage4_active)
        self._draw_actor(renderer, right_texture_key, right_filename, float(metrics["right_center_x"]), center_y, right_width, right_height, reveal, 1, now + 1.6, stage4_active)

    def _draw_frame(self, renderer, screen_size: Tuple[int, int], center_x: float, center_y: float, now: float):
        reveal = ease_out_cubic(self._frame_reveal)
        if reveal <= 0.01:
            return
        width, height = screen_size
        surface = self._load_image("asset:frame", "UI-img", "动态背景", "唱片", "素材", "框线.png")
        texture = self._get_texture(renderer, "asset:frame", surface)
        if texture is None or surface is None:
            return
        source_width = max(1, int(surface.get_width()))
        source_height = max(1, int(surface.get_height()))
# 框线大小
        frame_scale = 0.6
        cover_scale = max(float(width) / float(source_width), float(height) / float(source_height)) * frame_scale
        target_width = clamp_int(float(source_width) * cover_scale, 1, max(width, source_width * 4))
        target_height = clamp_int(float(source_height) * cover_scale, 1, max(height, source_height * 4))
        frame_offset_x = float(self._FRAME_CENTER_OFFSET_X) * (float(target_width) / float(source_width))
        frame_offset_y = float(self._FRAME_CENTER_OFFSET_Y) * (float(target_height) / float(source_height))

        pulse = 0.58 + 0.36 * (0.5 + 0.5 * math.sin(float(now) * 1.53))
        self._draw_texture(
            texture,
            (
                int(center_x - target_width * 0.5 + frame_offset_x),
                int(center_y - target_height * 0.5 + frame_offset_y),
                int(target_width),
                int(target_height),
            ),
            alpha=clamp_int(255.0 * pulse * reveal, 0, 255),
        )

    def _draw_foot(self, renderer, screen_size: Tuple[int, int]):
        width, height = screen_size
        surface = self._load_image("asset:foot", "UI-img", "动态背景", "唱片", "素材", "foot.png")
        texture = self._get_texture(renderer, "asset:foot", surface)
        if texture is None or surface is None:
            return
        draw_width = int(width + 2)
        draw_height = clamp_int(draw_width * (surface.get_height() / max(1, surface.get_width())), 16, height)
        self._draw_texture(texture, (-1, int(height - draw_height), int(draw_width), int(draw_height)), alpha=255)

    def render(self, context: DynamicBackgroundContext):
        renderer = context.renderer
        if renderer is None:
            return
        width, height = context.screen_size
        combo_state = self._resolve_combo_state(context.combo)
        record_size = self._get_record_size((width, height))
        record_half = float(record_size) * 0.5

        self._draw_background_layer(renderer, context.screen_size)
        self._draw_warp_stars(renderer, context.screen_size, context.now)
        self._draw_corner_spotlights(renderer, context.screen_size, context.now)
        self._draw_particles(renderer, "base")
        self._draw_side_lines(renderer, context.screen_size, context.now, record_half)
        rig_info = self._draw_machine_and_record(renderer, context.screen_size, context.now)
        self._draw_frame(renderer, context.screen_size, float(rig_info["center_x"]), float(rig_info["center_y"]), context.now)
        self._draw_particles(renderer, "astronaut")
        self._draw_astronauts(renderer, context.screen_size, rig_info["record_half"], context.now)
        self._draw_foot(renderer, context.screen_size)

    def _get_preview_scaled_surface(
        self,
        cache_key: str,
        source_surface: Optional[pygame.Surface],
        size: Tuple[int, int],
        *,
        cover: bool = False,
    ) -> Optional[pygame.Surface]:
        if source_surface is None:
            return None
        target_width = max(1, int(size[0]))
        target_height = max(1, int(size[1]))
        full_key = f"preview:{cache_key}:{target_width}:{target_height}:{int(bool(cover))}"
        cached = self._surface_cache.get(full_key, None)
        if isinstance(cached, pygame.Surface):
            return cached
        source_width = max(1, int(source_surface.get_width()))
        source_height = max(1, int(source_surface.get_height()))
        if bool(cover):
            scale = max(float(target_width) / float(source_width), float(target_height) / float(source_height))
        else:
            scale = min(float(target_width) / float(source_width), float(target_height) / float(source_height))
        draw_width = max(1, int(round(float(source_width) * scale)))
        draw_height = max(1, int(round(float(source_height) * scale)))
        try:
            scaled = pygame.transform.smoothscale(source_surface, (draw_width, draw_height)).convert_alpha()
        except Exception:
            try:
                scaled = pygame.transform.scale(source_surface, (draw_width, draw_height)).convert_alpha()
            except Exception:
                scaled = None
        self._surface_cache[full_key] = scaled
        return scaled

    def _draw_warp_stars_to_surface(self, target_surface: pygame.Surface, now: float):
        width, height = target_surface.get_size()
        center_x = float(width) * 0.5
        center_y = float(height) * 0.5
        scale = float(min(width, height)) * 0.84
        if not self._warp_stars:
            self._sync_warp_stars(1)
        for star in self._warp_stars:
            current_z = max(0.001, float(star.get("z", 1.0)))
            previous_z = max(current_z, float(star.get("prev_z", current_z)))
            x = center_x + (float(star.get("x", 0.0)) / current_z) * scale
            y = center_y + (float(star.get("y", 0.0)) / current_z) * scale
            prev_x = center_x + (float(star.get("x", 0.0)) / previous_z) * scale
            prev_y = center_y + (float(star.get("y", 0.0)) / previous_z) * scale
            if x < -24.0 or x > float(width) + 24.0 or y < -24.0 or y > float(height) + 24.0:
                continue
            depth = clamp(1.0 - current_z, 0.0, 1.0)
            twinkle = 0.88 + 0.12 * math.sin(float(now) * (2.6 + float(star.get("twinkle", 1.0))) + float(star.get("size_bias", 1.0)))
            alpha = clamp_int((76.0 + depth * 172.0) * twinkle, 0, 255)
            if alpha <= 2:
                continue
            try:
                pygame.draw.line(
                    target_surface,
                    (255, 255, 255, clamp_int(alpha * 0.72, 0, 255)),
                    (int(round(prev_x)), int(round(prev_y))),
                    (int(round(x)), int(round(y))),
                    max(1, clamp_int(1.0 + depth * 1.3, 1, 3)),
                )
            except Exception:
                pass
            halo_size = clamp_int(3.0 + depth * 4.0, 2, 9)
            core_size = clamp_int(1.0 + depth * 2.4, 1, 5)
            try:
                pygame.draw.rect(
                    target_surface,
                    (255, 255, 255, clamp_int(alpha * 0.22, 0, 255)),
                    pygame.Rect(
                        int(round(x - halo_size * 0.5)),
                        int(round(y - halo_size * 0.5)),
                        int(halo_size),
                        int(halo_size),
                    ),
                )
            except Exception:
                pass
            try:
                pygame.draw.rect(
                    target_surface,
                    (255, 255, 255, alpha),
                    pygame.Rect(
                        int(round(x - core_size * 0.5)),
                        int(round(y - core_size * 0.5)),
                        int(core_size),
                        int(core_size),
                    ),
                )
            except Exception:
                pass

    def _draw_particles_to_surface(self, target_surface: pygame.Surface):
        for particle in self._particles:
            progress = clamp(float(particle["life"]) / max(0.001, float(particle["max_life"])), 0.0, 1.0)
            wave = 0.84 + math.sin(float(particle["life"]) * 10.0 * float(particle["flicker"])) * 0.16
            alpha = clamp((1.0 - progress) * wave, 0.0, 1.0)
            halo_alpha = clamp_int(alpha * 54.0, 0, 255)
            core_alpha = clamp_int(alpha * 255.0, 0, 255)
            core_size = clamp_int(float(particle["size"]) + progress * 1.2, 1, 5)
            halo_size = clamp_int(float(particle["size"]) + progress * 4.8, 2, 10)
            x = int(round(float(particle["x"])))
            y = int(round(float(particle["y"])))
            try:
                pygame.draw.rect(
                    target_surface,
                    (255, 255, 255, halo_alpha),
                    pygame.Rect(int(x - halo_size // 2), int(y - halo_size // 2), int(halo_size), int(halo_size)),
                )
            except Exception:
                pass
            try:
                pygame.draw.rect(
                    target_surface,
                    (255, 255, 255, core_alpha),
                    pygame.Rect(int(x - core_size // 2), int(y - core_size // 2), int(core_size), int(core_size)),
                )
            except Exception:
                pass

    def render_preview_surface(
        self,
        target_surface: pygame.Surface,
        target_rect: Optional[pygame.Rect] = None,
        *,
        now: float = 0.0,
    ) -> bool:
        if not isinstance(target_surface, pygame.Surface):
            return False
        rect = target_rect.copy() if isinstance(target_rect, pygame.Rect) else target_surface.get_rect()
        rect = rect.clip(target_surface.get_rect())
        if rect.w <= 0 or rect.h <= 0:
            return False
        use_subsurface = True
        try:
            preview_surface = target_surface.subsurface(rect)
            preview_surface.fill((6, 10, 18))
        except Exception:
            use_subsurface = False
            preview_surface = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA, 32)
            preview_surface.fill((6, 10, 18, 255))

        background_surface = self._load_image("asset:bg", "UI-img", "动态背景", "唱片", "素材", "背景.png")
        background_scaled = self._get_preview_scaled_surface("asset:bg:cover", background_surface, rect.size, cover=True)
        if isinstance(background_scaled, pygame.Surface):
            preview_surface.blit(
                background_scaled,
                (
                    int((rect.w - background_scaled.get_width()) * 0.5),
                    int((rect.h - background_scaled.get_height()) * 0.5),
                ),
            )

        self._draw_warp_stars_to_surface(preview_surface, float(now))
        self._draw_particles_to_surface(preview_surface)

        record_surface = self._load_image("asset:record", "UI-img", "动态背景", "唱片", "素材", "唱片.png")
        if isinstance(record_surface, pygame.Surface):
            record_size = self._get_record_size(
                rect.size,
                minimum=72,
                maximum=max(72, min(rect.w, rect.h)),
            )
            scaled_record = self._get_preview_scaled_surface(
                f"asset:record:preview:{record_size}",
                record_surface,
                (record_size, record_size),
                cover=False,
            )
            try:
                rotated = pygame.transform.rotozoom(
                    scaled_record if isinstance(scaled_record, pygame.Surface) else record_surface,
                    self._get_record_surface_angle(now),
                    1.0 if isinstance(scaled_record, pygame.Surface) else float(record_size) / float(max(1, record_surface.get_width())),
                ).convert_alpha()
            except Exception:
                rotated = None
            if isinstance(rotated, pygame.Surface):
                preview_surface.blit(
                    rotated,
                    (
                        int(preview_surface.get_width() * 0.5 - rotated.get_width() * 0.5),
                        int(preview_surface.get_height() * 0.5 - rotated.get_height() * 0.5),
                    ),
                )

        foot_surface = self._load_image("asset:foot", "UI-img", "动态背景", "唱片", "素材", "foot.png")
        if isinstance(foot_surface, pygame.Surface) and rect.h >= 120:
            foot_scaled = self._get_preview_scaled_surface("asset:foot:width", foot_surface, (rect.w + 2, rect.h), cover=False)
            if isinstance(foot_scaled, pygame.Surface):
                preview_surface.blit(foot_scaled, (-1, rect.h - foot_scaled.get_height()))

        if bool(use_subsurface):
            return True
        try:
            target_surface.blit(preview_surface, rect.topleft)
            return True
        except Exception:
            return False
