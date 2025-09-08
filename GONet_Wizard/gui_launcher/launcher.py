from GONet_Wizard import commands

# GONet_Wizard/gui_launcher/launcher.py
import webview, os
from flask import Flask, render_template, request, jsonify
import glob

from GONet_Wizard import commands
import GONet_Wizard.settings as settings
from GONet_Wizard.gui_launcher.api import WebviewAPI

app = Flask(
    __name__,
    template_folder=os.path.join(settings.ROOT, "gui_launcher", "templates"),
    static_folder=settings.STATIC
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cmd/<cmd>")
def command_page(cmd):
    form_path = f"forms/{cmd}.html"
    try:
        return render_template("form_page.html", form_template=form_path, command_name=cmd)
    except:
        return f"<p>Unknown command: {cmd}</p>"

@app.route("/run", methods=["POST"])
def run_command():
    args = request.get_json()
    try:
        cmd = args.pop("command", None)
        msg = dispatch_command(cmd, args)
        return jsonify({"status": "success", "message": msg})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def _expand(filenames: str):
    expanded = []
    for item in filenames.split(","):
        expanded += glob.glob(item) or [item]
    return expanded

def dispatch_command(cmd: str, args: dict) -> str:
    if cmd == "show":
        commands.show_gonet_files(_expand(args["filenames"]), args.get("save"), "red" in args, "green" in args, "blue" in args)
        return "Show executed."
    elif cmd == "show_meta":
        commands.show_metadata(_expand(args["filenames"]))
        return "Metadata shown."
    elif cmd == "dashboard":
        commands.run()
        return "Dashboard launched."
    elif cmd == "connect_snap":
        commands.take_snapshot(args["gonet_ip"], args.get("config_file"))
        return "Snapshot sent."
    elif cmd == "connect_terminate":
        commands.terminate_imaging(args["gonet_ip"])
        return "Imaging terminated."
    elif cmd == "extract":
        commands.extract_counts_from_GONet(
            _expand(args["filenames"]),
            "red" in args,
            "green" in args,
            "blue" in args,
            args.get("shape"),
            args.get("center"),
            args.get("radius"),
            args.get("sides"),
            args.get("inner_radius"),
            args.get("outer_radius"),
            args.get("angles", "-180,180"),
            args.get("output")
        )
        return "Extract executed."
    return "Unknown command."

def start():
    api = WebviewAPI()
    webview.create_window("GONet Launcher", app, js_api=api)
    webview.start()

if __name__ == "__main__":
    start()
