bl_info = {
    "name": "Workload Mode Render Bridge",
    "author": "FA3 / Workload Mode",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "System",
    "description": "Reports render lifecycle to standalone Workload Mode without making Blender an FA3 application.",
    "category": "System",
}
import os
import subprocess
import uuid

_ACTIVE = None

def _call(*args):
    try:
        subprocess.run(["workmodectl", *args], check=False, close_fds=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass

def _start(_scene):
    global _ACTIVE
    if _ACTIVE:
        return
    _ACTIVE = "blender-render-" + uuid.uuid4().hex
    _call("register", "RENDER", _ACTIVE, "COORDINATED", str(os.getpid()))

def _stop(_scene):
    global _ACTIVE
    if not _ACTIVE:
        return
    _call("release", _ACTIVE)
    _ACTIVE = None

def register():
    import bpy
    for collection, fn in (
        (bpy.app.handlers.render_init, _start),
        (bpy.app.handlers.render_complete, _stop),
        (bpy.app.handlers.render_cancel, _stop),
    ):
        if fn not in collection:
            collection.append(fn)

def unregister():
    import bpy
    for collection, fn in (
        (bpy.app.handlers.render_init, _start),
        (bpy.app.handlers.render_complete, _stop),
        (bpy.app.handlers.render_cancel, _stop),
    ):
        if fn in collection:
            collection.remove(fn)
    if _ACTIVE:
        _stop(None)
