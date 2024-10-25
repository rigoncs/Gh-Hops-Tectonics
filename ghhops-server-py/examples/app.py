"""Hops flask middleware example"""
import sys
import os
from flask import Flask

# load ghhops-server-py source from this directory
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import ghhops_server as hs

import rhino3dm


# register hops app as middleware
app = Flask(__name__)
hops: hs.HopsFlask = hs.Hops(app)


# flask app can be used for other stuff directly
@app.route("/help")
def help():
    return "Welcome to Grashopper Hops for CPython!"


@app.route("/update", methods=["POST"])
def update():
    return "Update example!"


# /solve is a builtin method and can not be overrriden
@app.route("/solve", methods=["GET", "POST"])
def solve():
    return "Oh oh! this should not happen!"


@hops.component(
    "/binmult",
    inputs=[hs.HopsNumber("A"), hs.HopsNumber("B")],
    outputs=[hs.HopsNumber("Multiply")],
)
def BinaryMultiply(a: float, b: float):
    return a * b


@hops.component(
    "/add",
    name="Add",
    nickname="Add",
    description="Add numbers with CPython",
    inputs=[
        hs.HopsNumber("A", "A", "First number"),
        hs.HopsNumber("B", "B", "Second number"),
    ],
    outputs=[
        hs.HopsNumber("Sum", "S", "A + B"),
        hs.HopsNumber("Multi", "M", "A * B"),
    ],
)
def add(a: float, b: float):
    return a + b, a * b


@hops.component(
    "/pointat",
    name="PointAt",
    nickname="PtAt",
    description="Get point along curve",
    icon="pointat.png",
    inputs=[
        hs.HopsCurve("Curve", "C", "Curve to evaluate"),
        hs.HopsNumber("t", "t", "Parameter on Curve to evaluate"),
    ],
    outputs=[hs.HopsPoint("P", "P", "Point on curve at t")],
)
def pointat(curve: rhino3dm.Curve, t=0.0):
    return curve.PointAt(t)


@hops.component(
    "/srf4pt",
    name="4Point Surface",
    nickname="Srf4Pt",
    description="Create ruled surface from four points",
    inputs=[
        hs.HopsPoint("Corner A", "A", "First corner"),
        hs.HopsPoint("Corner B", "B", "Second corner"),
        hs.HopsPoint("Corner C", "C", "Third corner"),
        hs.HopsPoint("Corner D", "D", "Fourth corner"),
    ],
    outputs=[hs.HopsSurface("Surface", "S", "Resulting surface")],
)
def ruled_surface(
    a: rhino3dm.Point3d,
    b: rhino3dm.Point3d,
    c: rhino3dm.Point3d,
    d: rhino3dm.Point3d,
):
    edge1 = rhino3dm.LineCurve(a, b)
    edge2 = rhino3dm.LineCurve(c, d)
    return rhino3dm.NurbsSurface.CreateRuledSurface(edge1, edge2)


@hops.component(
    "/test.IntegerOutput",
    name="tIntegerOutput",
    nickname="tIntegerOutput",
    description="Add numbers with CPython and Test Integer output.",
    inputs=[
        hs.HopsInteger("A", "A", "First number"),
        hs.HopsInteger("B", "B", "Second number"),
    ],
    outputs=[hs.HopsInteger("Sum", "S", "A + B")],
)
def test_IntegerOutput(a, b):
    return a + b


if __name__ == "__main__":
    app.run(debug=True)