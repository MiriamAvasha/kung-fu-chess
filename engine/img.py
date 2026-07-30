from __future__ import annotations

import pathlib
import time

import cv2
import numpy as np

# Local OpenCV loop pacing (kept here to avoid circular imports with view/).
ANIMATION_MAX_FRAME_MS = 50
ANIMATION_ACTIVE_DELAY_MS = 16
ANIMATION_IDLE_DELAY_MS = 30
EXIT_KEYS = (27, ord('q'))


class Img:
    def __init__(self):
        self.img = None

    def copy(self):
        if self.img is None:
            raise ValueError("Image not loaded.")
        duplicate = Img()
        duplicate.img = self.img.copy()
        return duplicate

    def read(
        self,
        path: str | pathlib.Path,
        size: tuple[int, int] | None = None,
        keep_aspect: bool = False,
        interpolation: int = cv2.INTER_AREA,
    ) -> "Img":
        path = str(path)
        self.img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if self.img is None:
            raise FileNotFoundError(f"Cannot load image: {path}")

        if size is not None:
            target_w, target_h = size
            h, w = self.img.shape[:2]

            if keep_aspect:
                scale = min(target_w / w, target_h / h)
                new_w, new_h = int(w * scale), int(h * scale)
            else:
                new_w, new_h = target_w, target_h

            self.img = cv2.resize(self.img, (new_w, new_h), interpolation=interpolation)

        return self

    def _match_channels(self, other_img):
        """Ensure both images share a channel layout; prefer keeping alpha."""
        if self.img is None or other_img.img is None:
            raise ValueError("Both images must be loaded before drawing.")

        if self.img.shape[2] == other_img.img.shape[2]:
            return
        if self.img.shape[2] == 4 and other_img.img.shape[2] == 3:
            other_img.img = cv2.cvtColor(other_img.img, cv2.COLOR_BGR2BGRA)
        elif self.img.shape[2] == 3 and other_img.img.shape[2] == 4:
            self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2BGRA)

    def draw_on(self, other_img, x, y):
        self._match_channels(other_img)

        h, w = self.img.shape[:2]
        H, W = other_img.img.shape[:2]

        if y + h > H or x + w > W:
            raise ValueError("Logo does not fit at the specified position.")

        roi = other_img.img[y:y + h, x:x + w]

        if self.img.shape[2] == 4:
            alpha = self.img[..., 3] / 255.0
            for channel in range(3):
                roi[..., channel] = (
                    (1.0 - alpha) * roi[..., channel]
                    + alpha * self.img[..., channel]
                )
            if roi.shape[2] == 4:
                roi[..., 3] = np.clip(
                    roi[..., 3] + self.img[..., 3] * (1.0 - roi[..., 3] / 255.0),
                    0,
                    255,
                ).astype(np.uint8)
        else:
            other_img.img[y:y + h, x:x + w] = self.img

    def draw_on_clipped(self, other_img, x, y):
        self._match_channels(other_img)

        h, w = self.img.shape[:2]
        canvas_h, canvas_w = other_img.img.shape[:2]
        destination_x = max(0, x)
        destination_y = max(0, y)
        source_x = max(0, -x)
        source_y = max(0, -y)
        draw_width = min(w - source_x, canvas_w - destination_x)
        draw_height = min(h - source_y, canvas_h - destination_y)
        if draw_width <= 0 or draw_height <= 0:
            return self

        sprite = self.img[
            source_y:source_y + draw_height,
            source_x:source_x + draw_width,
        ]
        roi = other_img.img[
            destination_y:destination_y + draw_height,
            destination_x:destination_x + draw_width,
        ]
        if sprite.shape[2] == 4:
            alpha = sprite[..., 3].astype(np.float32) / 255.0
            blended = roi.astype(np.float32)
            for channel in range(3):
                blended[..., channel] = (
                    (1.0 - alpha) * blended[..., channel]
                    + alpha * sprite[..., channel]
                )
            if blended.shape[2] == 4:
                blended[..., 3] = np.clip(
                    blended[..., 3]
                    + sprite[..., 3].astype(np.float32)
                    * (1.0 - blended[..., 3] / 255.0),
                    0,
                    255,
                )
            roi[:] = np.clip(blended, 0, 255).astype(np.uint8)
        else:
            roi[:] = sprite
        return self

    def put_text(self, txt, x, y, font_size, color=(255, 255, 255, 255), thickness=1):
        if self.img is None:
            raise ValueError("Image not loaded.")
        cv2.putText(
            self.img,
            txt,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_size,
            color,
            thickness,
            cv2.LINE_AA,
        )

    def put_centered_text(
        self,
        txt,
        center_x,
        center_y,
        font_size,
        color=(255, 255, 255, 255),
        thickness=1,
    ):
        if self.img is None:
            raise ValueError("Image not loaded.")
        (text_width, text_height), baseline = cv2.getTextSize(
            txt,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_size,
            thickness,
        )
        self.put_text(
            txt,
            center_x - text_width // 2,
            center_y + (text_height - baseline) // 2,
            font_size,
            color,
            thickness,
        )
        return self

    def draw_rectangle(self, x, y, width, height, color, thickness=1):
        if self.img is None:
            raise ValueError("Image not loaded.")
        if width <= 0 or height <= 0:
            raise ValueError("Rectangle dimensions must be positive.")
        if thickness < 0:
            return self.fill_rectangle(x, y, width, height, color)
        cv2.rectangle(
            self.img,
            (x, y),
            (x + width - 1, y + height - 1),
            color,
            thickness,
        )
        return self

    def fill_rectangle(self, x, y, width, height, color):
        if self.img is None:
            raise ValueError("Image not loaded.")
        if width <= 0 or height <= 0:
            raise ValueError("Rectangle dimensions must be positive.")
        canvas_h, canvas_w = self.img.shape[:2]
        left = max(0, x)
        top = max(0, y)
        right = min(canvas_w, x + width)
        bottom = min(canvas_h, y + height)
        if right <= left or bottom <= top:
            return self
        channels = self.img.shape[2]
        fill = list(color[:channels])
        while len(fill) < channels:
            fill.append(255)
        self.img[top:bottom, left:right] = fill
        return self

    def fill_rectangle_alpha(self, x, y, width, height, color, alpha=0.55):
        if self.img is None:
            raise ValueError("Image not loaded.")
        if width <= 0 or height <= 0:
            raise ValueError("Rectangle dimensions must be positive.")
        canvas_h, canvas_w = self.img.shape[:2]
        left = max(0, x)
        top = max(0, y)
        right = min(canvas_w, x + width)
        bottom = min(canvas_h, y + height)
        if right <= left or bottom <= top:
            return self

        roi = self.img[top:bottom, left:right]
        blend = max(0.0, min(1.0, float(alpha)))
        overlay = np.array(color[:3], dtype=np.float32)
        blended = roi.astype(np.float32)
        for channel in range(3):
            blended[..., channel] = (
                (1.0 - blend) * blended[..., channel] + blend * overlay[channel]
            )
        roi[:] = np.clip(blended, 0, 255).astype(np.uint8)
        return self

    def draw_circle(self, center_x, center_y, radius, color, thickness=-1):
        if self.img is None:
            raise ValueError("Image not loaded.")
        if radius <= 0:
            raise ValueError("Circle radius must be positive.")
        cv2.circle(
            self.img,
            (center_x, center_y),
            radius,
            color,
            thickness,
            cv2.LINE_AA,
        )
        return self

    def show(self):
        if self.img is None:
            raise ValueError("Image not loaded.")
        cv2.imshow("Image", self.img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def show_interactive(self, on_left_click, window_name="Image"):
        if self.img is None:
            raise ValueError("Image not loaded.")

        current_image = [self]

        def handle_mouse(event, x, y, _flags, _context):
            if event != cv2.EVENT_LBUTTONDOWN:
                return
            updated_image = on_left_click(x, y)
            if updated_image is None:
                return
            if updated_image.img is None:
                raise ValueError("Updated image is not loaded.")
            current_image[0] = updated_image
            cv2.imshow(window_name, updated_image.img)

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, handle_mouse)
        cv2.imshow(window_name, current_image[0].img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def show_animation_loop(
        self,
        make_frame,
        on_left_click,
        on_tick,
        is_animating,
        window_name="Image",
    ):
        if self.img is None:
            raise ValueError("Image not loaded.")

        current_image = [self]
        needs_redraw = [False]

        def handle_mouse(event, x, y, _flags, _context):
            if event != cv2.EVENT_LBUTTONDOWN:
                return
            on_left_click(x, y)
            needs_redraw[0] = True

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, handle_mouse)
        cv2.imshow(window_name, current_image[0].img)
        last_frame_time = time.perf_counter()

        try:
            while True:
                now = time.perf_counter()
                elapsed_ms = min(
                    ANIMATION_MAX_FRAME_MS,
                    max(0, int((now - last_frame_time) * 1000)),
                )
                last_frame_time = now

                was_animating = is_animating()
                on_tick(elapsed_ms)
                if needs_redraw[0] or was_animating or is_animating():
                    updated_image = make_frame()
                    if updated_image is None or updated_image.img is None:
                        raise ValueError("Updated image is not loaded.")
                    current_image[0] = updated_image
                    cv2.imshow(window_name, updated_image.img)
                    needs_redraw[0] = False

                delay_ms = (
                    ANIMATION_ACTIVE_DELAY_MS
                    if is_animating()
                    else ANIMATION_IDLE_DELAY_MS
                )
                key = cv2.waitKey(delay_ms) & 0xFF
                if key in EXIT_KEYS:
                    break
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            cv2.destroyAllWindows()
