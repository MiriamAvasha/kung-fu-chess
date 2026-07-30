from img import Img
from view import view_constants as vc


class ImageView:
    """Displays an image produced by the Renderer."""

    @staticmethod
    def show(image: Img):
        image.show()

    @staticmethod
    def run(make_frame, on_left_click, on_tick, is_animating):
        image = make_frame()
        image.show_animation_loop(
            make_frame,
            on_left_click,
            on_tick,
            is_animating,
            window_name=vc.WINDOW_NAME,
        )
