from flask import Flask
import ghhops_server as hs

import rhino3dm
from utils import get_mesh_by_grey_map

# register hops app as middleware
app = Flask(__name__)
hops = hs.Hops(app)

@hops.component(
    "/greymesh",
    name="GreyMesh",
    description="Generate mesh based on grey map",
    icon="",
    inputs=[
        hs.HopsNumber("height", "h", "Height factor", default=0.2),
    ],
    outputs=[
        hs.HopsMesh("M", "M", "Mesh generated based on grey map"),
    ],
)
def generate_mesh_by_grep_map(height_factor):
    mesh = get_mesh_by_grey_map(height_factor)
    return mesh

if __name__ == "__main__":
    app.run(debug=True)