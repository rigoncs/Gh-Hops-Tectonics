import sys
import os
from flask import Flask

# load ghhops-server-py source from this directory
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import ghhops_server as hs

import rhino3dm
from l_system import *


# register hops app as middleware
app = Flask(__name__)
hops: hs.HopsFlask = hs.Hops(app)

@hops.component(
    "/lsystem",
    name="LSystem",
    description="Create mesh based on L-System",
    inputs=[
        hs.HopsNumber("N", "Iterations","iterations for l_system", default=4),
        hs.HopsNumber("A","Angle","angle for l_system", default=25),
        hs.HopsNumber("S","Step","step length for l_system", default=1.0)
    ],
    outputs=[
        hs.HopsPoint("Points","P","Point based on l_system"),
        hs.HopsMesh("Mesh", "M", "Mesh based on l_system"),
    ]
)
def l_system_mesh(iterations, angle, step):
    axiom = "F"
    rules = {"F": "FF+[+F-F-F]-[-F+F+F]"}
    lstring = l_system(axiom, rules, iterations)
    pts = lsystem_to_paths(lstring, angle, step)
    mesh = points_to_mesh(pts)
    return pts, mesh


@hops.component(
    "/lsystem3d",
    name="LSystem3D",
    description="Create points based on L-System",
    inputs=[
        hs.HopsNumber("N", "Iterations","iterations for l_system", default=4),
        hs.HopsNumber("A","Angle","angle for l_system", default=math.pi /6),
        hs.HopsNumber("S","Step","step length for l_system", default=1.0)
    ],
    outputs=[
        hs.HopsPoint("Points", "P", "Points based on l_system"),
        hs.HopsMesh("Mesh","M","Mesh based on l_system")
    ]
)
def l_system_mesh3d(iterations, angle, step):
    axiom = "F"
    rules = {"F": "F[+F][-F]^F[&F]"}
    pts = l_system_3d(axiom, rules, iterations, angle, step)
    mesh = points_to_mesh(pts)
    return pts, mesh


if __name__ == "__main__":
    app.run(debug=True)