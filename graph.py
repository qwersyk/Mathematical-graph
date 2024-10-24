from .extensions import NewelleExtension
from .extra import install_module
from gi.repository import GdkPixbuf, Gtk


class GraphGeneratorExtension(NewelleExtension):
    name = "Function Graph Generator"
    id = "function-graph"

    def get_replace_codeblocks_langs(self) -> list:
        return ["generate-graph"]

    def install(self):
        install_module("matplotlib", self.pip_path)

    def get_additional_prompts(self) -> list:
        return [
            {
                "key": "generate-graph",
                "setting_name": "generate-graph",
                "title": "Generate Graph",
                "description": "Generate graphs from mathematical functions",
                "editable": True,
                "show_in_settings": True,
                "default": True,
                "text": "You can generate graphs using: \n```generate-graph\nfunction_str\n```. "
                        "Use valid Python expressions (e.g., 'sin(x)', 'x**2')."
            }
        ]

    def get_gtk_widget(self, codeblock: str, lang: str) -> Gtk.Widget | None:
        from threading import Thread

        box = Gtk.Box()
        spinner = Gtk.Spinner(spinning=True)
        box.append(spinner)
        image = Gtk.Image()
        image.set_size_request(400, 400)
        box.append(image)

        thread = Thread(target=self.generate_graph, args=(codeblock, image, spinner, box))
        thread.start()
        return box

    def generate_graph(self, function_str: str, image: Gtk.Image, spinner: Gtk.Spinner, box: Gtk.Box):
        import matplotlib.pyplot as plt
        import math
        filename = f'graph_{function_str.replace("*", "_").replace("(", "").replace(")", "")}.png'

        try:
            x_values = [i / 10 for i in range(-100, 101)]
            y_values = [eval(function_str, {"__builtins__": None}, {
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "sqrt": math.sqrt,
                "log": math.log,
                "abs": abs,
                "pi": math.pi,
                "e": math.e,
                "x": x
            }) for x in x_values]

            plt.figure(facecolor='none')
            plt.plot(x_values, y_values)
            plt.xlabel('X')
            plt.ylabel('Y')
            plt.title(f'The graph of the function: y = {function_str}')
            plt.gca().set_facecolor('none')
            plt.gca().spines['bottom'].set_color('gray')
            plt.gca().spines['top'].set_color('gray')
            plt.gca().spines['right'].set_color('gray')
            plt.gca().spines['left'].set_color('gray')
            plt.gca().tick_params(axis='x', colors='gray')
            plt.gca().tick_params(axis='y', colors='gray')
            plt.gca().title.set_color('gray')
            plt.gca().xaxis.label.set_color('gray')
            plt.gca().yaxis.label.set_color('gray')

            plt.savefig(filename, dpi=300, transparent=True)
            plt.close()

            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            image.set_from_pixbuf(pixbuf)

            box.remove(spinner)
            box.append(image)
        except Exception as e:
            print(f"Error generating graph: {e}")
            box.remove(spinner)
            box.append(Gtk.Label(label="Error generating graph. Check the input function."))