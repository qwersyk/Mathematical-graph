from .extensions import NewelleExtension
from typing import List
import math
import threading
from gi.repository import Gtk, GLib, cairo


class GraphGeneratorExtension(NewelleExtension):
    name = "Graph Generator"
    id = "graph"

    def __init__(self, a, b, c) -> None:
        super().__init__(a, b, c)
        # Load extension settings
        try:
            self.tick_count = int(self.get_setting("tick_count") or 7)
        except Exception:
            self.tick_count = 7
        try:
            self.zoom_factor = float(self.get_setting("zoom_factor") or 0.8)
        except Exception:
            self.zoom_factor = 0.8
        try:
            self.pan_fraction = float(self.get_setting("pan_fraction") or 0.1)
        except Exception:
            self.pan_fraction = 0.1
        self.show_axes = (self.get_setting("show_axes") or "true").lower() == "true"
        try:
            self.grid_density = int(self.get_setting("grid_density") or 20)
        except Exception:
            self.grid_density = 20
        self.show_bounding_box = (self.get_setting("show_bounding_box") or "false").lower() == "true"
        self.fixed_range = (self.get_setting("fixed_range") or "false").lower() == "true"
        # repeat_mode: "off", "horizontal", "vertical", "both"
        self.repeat_mode = self.get_setting("repeat_mode") or "off"

    # No install method is provided for this extension

    def get_replace_codeblocks_langs(self) -> List[str]:
        return ["graph"]

    def get_extra_settings(self):
        return [
            {
                "key": "tick_count",
                "title": "Number of Tick Labels",
                "description": "Number of tick labels to display on each axis (e.g., 7)",
                "type": "entry",
                "default": "7"
            },
            {
                "key": "zoom_factor",
                "title": "Zoom Factor",
                "description": "Zoom factor for each zoom action (e.g., 0.8 for zoom in, >1 for zoom out)",
                "type": "entry",
                "default": "0.8"
            },
            {
                "key": "pan_fraction",
                "title": "Pan Fraction",
                "description": "Fraction of the view range to pan for each pan action (e.g., 0.1 for 10%)",
                "type": "entry",
                "default": "0.1"
            },
            {
                "key": "show_axes",
                "title": "Always Show Axes",
                "description": "Force drawing of axes even when 0 is not in view",
                "type": "combo",
                "values": [("true", "True"), ("false", "False")],
                "default": "true"
            },
            {
                "key": "grid_density",
                "title": "Grid Density (px)",
                "description": "Spacing in pixels for drawing grid lines",
                "type": "entry",
                "default": "20"
            },
            {
                "key": "show_bounding_box",
                "title": "Show Bounding Box",
                "description": "Draw a dashed rectangle representing the global bounds",
                "type": "combo",
                "values": [("true", "True"), ("false", "False")],
                "default": "false"
            },
            {
                "key": "fixed_range",
                "title": "Fixed Global Range",
                "description": "Lock view to global bounds (disable dynamic panning/zooming)",
                "type": "combo",
                "values": [("true", "True"), ("false", "False")],
                "default": "false"
            },
            {
                "key": "repeat_mode",
                "title": "Repeat Mode",
                "description": "Repeat graphs when panned (options: off, horizontal, vertical, both)",
                "type": "combo",
                "values": [("off", "Off"), ("horizontal", "Horizontal"), ("vertical", "Vertical"), ("both", "Both")],
                "default": "off"
            }
        ]

    def get_additional_prompts(self) -> List[dict]:
        return [
            {
                "key": "graph",
                "setting_name": "graph",
                "title": "Generate Graph",
                "description": (
                    "Generate interactive graphs from mathematical functions with a transparent background "
                    "that adapts to light or dark themes. Multiple functions (separated by newlines) will be overlaid "
                    "on a single coordinate system using different colors. Hover over the graph to see a magnetized point "
                    "that snaps to nearby graph points or the origin. Use the zoom and pan buttons above to navigate.\n"
                    "Important settings control tick label count, grid density, fixed display range, and repeat mode."
                ),
                "editable": True,
                "show_in_settings": True,
                "default": True,
                "text": (
                    "To generate a graph, use the syntax:\n```graph\n<function_str>\n```\n"
                    "Enter one or more valid Python mathematical expressions (e.g., 'sin(x)', 'x**2', or 'log(x+1)').\n"
                    "Separate multiple functions with a newline."
                )
            }
        ]

    def get_gtk_widget(self, codeblock: str, lang: str) -> Gtk.Widget | None:
        # Capture settings
        tick_count = self.tick_count
        zoom_factor = self.zoom_factor
        pan_fraction = self.pan_fraction
        show_axes = self.show_axes
        grid_density = self.grid_density
        show_bounding_box = self.show_bounding_box
        fixed_range = self.fixed_range
        repeat_mode = self.repeat_mode

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Control panel for zoom and pan
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        zoom_in_btn = Gtk.Button.new_with_label("Zoom In")
        zoom_out_btn = Gtk.Button.new_with_label("Zoom Out")
        pan_left_btn = Gtk.Button.new_with_label("←")
        pan_right_btn = Gtk.Button.new_with_label("→")
        pan_up_btn = Gtk.Button.new_with_label("↑")
        pan_down_btn = Gtk.Button.new_with_label("↓")
        ctrl_box.append(zoom_in_btn)
        ctrl_box.append(zoom_out_btn)
        ctrl_box.append(pan_left_btn)
        ctrl_box.append(pan_right_btn)
        ctrl_box.append(pan_up_btn)
        ctrl_box.append(pan_down_btn)
        outer_box.append(ctrl_box)

        spinner = Gtk.Spinner.new()
        spinner.start()
        outer_box.append(spinner)

        drawing_area = Gtk.DrawingArea.new()
        drawing_area.set_content_width(400)
        drawing_area.set_content_height(400)
        drawing_area.graphs = None
        drawing_area.graph_bounds = None
        drawing_area.view_bounds = None
        drawing_area.hover_info = None
        outer_box.append(drawing_area)

        coords_label = Gtk.Label.new("Coordinates:")
        outer_box.append(coords_label)

        def draw_func(area: Gtk.DrawingArea, ctx: cairo.Context, width: int, height: int, user_data):
            settings_gtk = Gtk.Settings.get_default()
            dark_theme = settings_gtk.get_property("gtk-application-prefer-dark-theme")
            if dark_theme:
                grid_color = (0.4, 0.4, 0.4, 1)
                axes_color = (1, 1, 1, 1)
                text_color = (1, 1, 1, 1)
                palette = [
                    (0.4, 0.8, 1.0, 1),
                    (1.0, 0.6, 0.6, 1),
                    (0.6, 1.0, 0.6, 1),
                    (1.0, 0.8, 1.0, 1)
                ]
            else:
                grid_color = (0.9, 0.9, 0.9, 1)
                axes_color = (0, 0, 0, 1)
                text_color = (0.2, 0.2, 0.2, 1)
                palette = [
                    (0.2, 0.6, 1.0, 1),
                    (1.0, 0.4, 0.4, 1),
                    (0.4, 1.0, 0.4, 1),
                    (0.8, 0.2, 1.0, 1)
                ]

            ctx.set_operator(cairo.Operator.SOURCE)
            ctx.set_source_rgba(0, 0, 0, 0)
            ctx.paint()
            ctx.set_operator(cairo.Operator.OVER)

            # Draw grid using grid_density setting.
            ctx.set_source_rgba(*grid_color)
            ctx.set_line_width(0.5)
            for i in range(0, width, grid_density):
                ctx.move_to(i, 0)
                ctx.line_to(i, height)
            for i in range(0, height, grid_density):
                ctx.move_to(0, i)
                ctx.line_to(width, i)
            ctx.stroke()

            if drawing_area.graphs is None:
                ctx.set_source_rgba(*text_color)
                ctx.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
                ctx.set_font_size(20)
                message = "Loading..."
                extents = ctx.text_extents(message)
                ctx.move_to((width - extents.width) / 2, (height + extents.height) / 2)
                ctx.show_text(message)
                return

            # Compute global bounds from graphs.
            all_x, all_y = [], []
            for graph in drawing_area.graphs:
                for pt in graph["points"]:
                    all_x.append(pt[0])
                    all_y.append(pt[1])
            if all_x and all_y:
                global_min_x, global_max_x = min(all_x), max(all_x)
                global_min_y, global_max_y = min(all_y), max(all_y)
            else:
                global_min_x, global_max_x, global_min_y, global_max_y = -10, 10, -10, 10

            margin = 0.1
            x_range = max(abs(global_max_x - global_min_x), 1)
            y_range = max(abs(global_max_y - global_min_y), 1)
            global_min_x -= margin * x_range
            global_max_x += margin * x_range
            global_min_y -= margin * y_range
            global_max_y += margin * y_range
            drawing_area.graph_bounds = (global_min_x, global_max_x, global_min_y, global_max_y)

            # If fixed_range is enabled, lock view_bounds to global bounds.
            if drawing_area.view_bounds is None or fixed_range:
                drawing_area.view_bounds = drawing_area.graph_bounds
            view_min_x, view_max_x, view_min_y, view_max_y = drawing_area.view_bounds

            def transform(x, y):
                tx = ((x - view_min_x) / (view_max_x - view_min_x)) * width
                ty = height - ((y - view_min_y) / (view_max_y - view_min_y)) * height
                return tx, ty

            ctx.set_source_rgba(*axes_color)
            ctx.set_line_width(2)
            if show_axes or (view_min_y <= 0 <= view_max_y):
                x_axis_start = transform(view_min_x, 0)
                x_axis_end = transform(view_max_x, 0)
                ctx.move_to(*x_axis_start)
                ctx.line_to(*x_axis_end)
                ctx.stroke()
            if show_axes or (view_min_x <= 0 <= view_max_x):
                y_axis_start = transform(0, view_min_y)
                y_axis_end = transform(0, view_max_y)
                ctx.move_to(*y_axis_start)
                ctx.line_to(*y_axis_end)
                ctx.stroke()

            # Draw graphs with optional repeat mode.
            def draw_single_graph(graph, offset_x=0, offset_y=0):
                pts = graph["points"]
                color = palette[graph.get("color_index", 0) % len(palette)]
                ctx.set_source_rgba(*color)
                ctx.set_line_width(3)
                first_point = True
                prev_y = None
                for pt in pts:
                    x_val, y_val = pt
                    tx, ty = transform(x_val + offset_x, y_val + offset_y)
                    if first_point:
                        ctx.move_to(tx, ty)
                        first_point = False
                    else:
                        if prev_y is not None and abs(y_val - prev_y) > (view_max_y - view_min_y) / 4:
                            ctx.stroke()
                            ctx.move_to(tx, ty)
                        else:
                            ctx.line_to(tx, ty)
                    prev_y = y_val
                ctx.stroke()

            # Draw original graphs.
            for idx, graph in enumerate(drawing_area.graphs):
                graph["color_index"] = idx
                draw_single_graph(graph)

            # If repeat mode is enabled, draw additional copies.
            if repeat_mode != "off":
                dx = global_max_x - global_min_x
                dy = global_max_y - global_min_y
                offsets = []
                if repeat_mode in ("horizontal", "both"):
                    offsets += [(-dx, 0), (dx, 0)]
                if repeat_mode in ("vertical", "both"):
                    offsets += [(0, -dy), (0, dy)]
                # For "both" also draw diagonal copies.
                if repeat_mode == "both":
                    offsets += [(-dx, -dy), (-dx, dy), (dx, -dy), (dx, dy)]
                for off in offsets:
                    for graph in drawing_area.graphs:
                        draw_single_graph(graph, offset_x=off[0], offset_y=off[1])

            # Optionally, draw the bounding box for global bounds.
            if show_bounding_box:
                ctx.set_source_rgba(*axes_color)
                ctx.set_line_width(1)
                ctx.set_dash([4.0, 4.0])
                top_left = transform(global_min_x, global_max_y)
                bottom_right = transform(global_max_x, global_min_y)
                ctx.rectangle(top_left[0], top_left[1],
                              bottom_right[0] - top_left[0],
                              bottom_right[1] - top_left[1])
                ctx.stroke()
                ctx.set_dash([])

            # Draw tick labels.
            ctx.set_source_rgba(*text_color)
            ctx.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
            ctx.set_font_size(12)
            for i in range(tick_count):
                val = view_min_x + i * ((view_max_x - view_min_x) / (tick_count - 1))
                tx = (i / (tick_count - 1)) * width
                ctx.move_to(tx, height - 5)
                ctx.line_to(tx, height)
                ctx.stroke()
                label = f"{val:.2f}"
                extents = ctx.text_extents(label)
                ctx.move_to(tx - extents.width / 2, height - 7)
                ctx.show_text(label)
            for i in range(tick_count):
                val = view_min_y + i * ((view_max_y - view_min_y) / (tick_count - 1))
                ty = height - (i / (tick_count - 1)) * height
                ctx.move_to(0, ty)
                ctx.line_to(5, ty)
                ctx.stroke()
                label = f"{val:.2f}"
                extents = ctx.text_extents(label)
                ctx.move_to(7, ty + extents.height / 2)
                ctx.show_text(label)

            # Draw magnetic hover point.
            if drawing_area.hover_info:
                pix_x, pix_y = drawing_area.hover_info['pixel']
                ctx.set_source_rgba(*text_color)
                ctx.arc(pix_x, pix_y, 6, 0, 2 * math.pi)
                ctx.fill()

        drawing_area.set_draw_func(draw_func, None)

        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", lambda ctrl, x, y: on_motion(x, y))
        drawing_area.add_controller(motion_controller)

        def on_motion(x, y):
            width = drawing_area.get_allocated_width()
            height = drawing_area.get_allocated_height()
            if drawing_area.view_bounds is None or drawing_area.graphs is None:
                coords_label.set_text(f"Coordinates: Pixel ({x:.0f}, {y:.0f})")
                drawing_area.hover_info = None
                drawing_area.queue_draw()
                return
            view_min_x, view_max_x, view_min_y, view_max_y = drawing_area.view_bounds
            math_x = view_min_x + (x / width) * (view_max_x - view_min_x)
            math_y = view_max_y - (y / height) * (view_max_y - view_min_y)

            def transform(x_val, y_val):
                tx = ((x_val - view_min_x) / (view_max_x - view_min_x)) * width
                ty = height - ((y_val - view_min_y) / (view_max_y - view_min_y)) * height
                return tx, ty

            threshold = 10
            snap_candidate = None
            min_dist = threshold
            for graph in drawing_area.graphs:
                for pt in graph["points"]:
                    pt_x, pt_y = pt
                    pix_pt = transform(pt_x, pt_y)
                    dist = math.hypot(pix_pt[0] - x, pix_pt[1] - y)
                    if dist < min_dist:
                        min_dist = dist
                        snap_candidate = (pt_x, pt_y, pix_pt[0], pix_pt[1])
            origin_pix = transform(0, 0)
            dist_origin = math.hypot(origin_pix[0] - x, origin_pix[1] - y)
            if dist_origin < min_dist:
                snap_candidate = (0, 0, origin_pix[0], origin_pix[1])
            if snap_candidate:
                s_math_x, s_math_y, s_pix_x, s_pix_y = snap_candidate
                drawing_area.hover_info = {"math": (s_math_x, s_math_y), "pixel": (s_pix_x, s_pix_y)}
                coords_label.set_text(
                    f"Snapped: ({s_math_x:.2f}, {s_math_y:.2f}) | Pixel: ({s_pix_x:.0f}, {s_pix_y:.0f})")
            else:
                drawing_area.hover_info = None
                coords_label.set_text(f"Coordinates: ({math_x:.2f}, {math_y:.2f}) | Pixel: ({x:.0f}, {y:.0f})")
            drawing_area.queue_draw()

        def zoom_view(factor):
            if drawing_area.view_bounds is None:
                return
            min_x, max_x, min_y, max_y = drawing_area.view_bounds
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            new_range_x = (max_x - min_x) * factor / 2
            new_range_y = (max_y - min_y) * factor / 2
            drawing_area.view_bounds = (
                center_x - new_range_x,
                center_x + new_range_x,
                center_y - new_range_y,
                center_y + new_range_y,
            )
            drawing_area.queue_draw()

        def pan_view(delta_x, delta_y):
            if drawing_area.view_bounds is None:
                return
            min_x, max_x, min_y, max_y = drawing_area.view_bounds
            drawing_area.view_bounds = (
                min_x + delta_x,
                max_x + delta_x,
                min_y + delta_y,
                max_y + delta_y,
            )
            drawing_area.queue_draw()

        zoom_in_btn.connect("clicked", lambda btn: zoom_view(zoom_factor))
        zoom_out_btn.connect("clicked", lambda btn: zoom_view(1 / zoom_factor))

        def do_pan(direction):
            min_x, max_x, min_y, max_y = drawing_area.view_bounds
            shift_x = (max_x - min_x) * pan_fraction
            shift_y = (max_y - min_y) * pan_fraction
            if direction == "left":
                pan_view(-shift_x, 0)
            elif direction == "right":
                pan_view(shift_x, 0)
            elif direction == "up":
                pan_view(0, shift_y)
            elif direction == "down":
                pan_view(0, -shift_y)

        pan_left_btn.connect("clicked", lambda btn: do_pan("left"))
        pan_right_btn.connect("clicked", lambda btn: do_pan("right"))
        pan_up_btn.connect("clicked", lambda btn: do_pan("up"))
        pan_down_btn.connect("clicked", lambda btn: do_pan("down"))

        def compute_graph():
            try:
                expressions = [expr.strip() for expr in codeblock.strip().splitlines() if expr.strip()]
                graphs = []
                x_values = [i / 20 for i in range(-200, 201)]
                for expr in expressions:
                    points = []
                    safe_locals = {
                        "sin": math.sin,
                        "cos": math.cos,
                        "tan": math.tan,
                        "sqrt": math.sqrt,
                        "log": math.log,
                        "abs": abs,
                        "pi": math.pi,
                        "e": math.e,
                    }
                    for x in x_values:
                        safe_locals["x"] = x
                        try:
                            y = eval(expr, {"__builtins__": None}, safe_locals)
                            if isinstance(y, (int, float)) and not math.isinf(y) and not math.isnan(y):
                                points.append((x, y))
                        except Exception:
                            continue
                    graphs.append({"expr": expr, "points": points})

                def update_ui():
                    if spinner.get_parent():
                        spinner.stop()
                        outer_box.remove(spinner)
                    drawing_area.graphs = graphs
                    if fixed_range:
                        drawing_area.view_bounds = drawing_area.graph_bounds
                    drawing_area.queue_draw()
                    return False

                GLib.idle_add(update_ui)
            except Exception as e:
                def update_ui_error():
                    if spinner.get_parent():
                        spinner.stop()
                        outer_box.remove(spinner)
                    error_label = Gtk.Label.new(f"Error: {str(e)}")
                    outer_box.append(error_label)
                    return False

                GLib.idle_add(update_ui_error)

        thread = threading.Thread(target=compute_graph, daemon=True)
        thread.start()

        return outer_box