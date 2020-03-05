# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Yorik van Havre <yorik@uncreated.net>              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""POV-Ray renderer for FreeCAD"""

# This file can also be used as a template to add more rendering engines.
# You will need to make sure your file is named with a same name (case
# sensitive)
# That you will use everywhere to describe your renderer, ex: Appleseed or
# Povray


# A render engine module must contain the following functions:
#
# write_camera(pos,rot,up,target, name)
#   returns a string containing an openInventor camera string in renderer
#   format
#
# write_object(view,mesh,color,alpha)
#   returns a string containing a RaytracingView object in renderer format
#
# render(project,prefix,external,output,width,height)
#   renders the given project
#   external means if the user wishes to open the render file in an external
#   application/editor or not. If this is not supported by your renderer, you
#   can simply ignore it
#
# Additionally, you might need/want to add:
#   Preference page items, that can be used in your functions below
#   An icon under the name Renderer.svg (where Renderer is the name of your
#   Renderer


# POV-Ray specific (tip):
# Please note that POV-Ray coordinate system appears to be different from
# FreeCAD's one (z and y permuted)
# See here: https://www.povray.org/documentation/3.7.0/t2_2.html#t2_2_1_1

import os
import re
from textwrap import dedent

import FreeCAD as App


def write_camera(pos, rot, updir, target, name):
    """Compute a string in the format of POV-Ray, that represents a camera"""

    # This is where you create a piece of text in the format of
    # your renderer, that represents the camera.

    snippet = """
    // Generated by FreeCAD (http://www.freecadweb.org/)
    // Declares camera '{n}'
    #declare cam_location = <{p.x},{p.z},{p.y}>;
    #declare cam_look_at  = <{t.x},{t.z},{t.y}>;
    #declare cam_sky      = <{u.x},{u.z},{u.y}>;
    #declare cam_angle    = 45;
    camera {{
        location  cam_location
        look_at   cam_look_at
        sky       cam_sky
        angle     cam_angle
        right     x*800/600
    }}\n"""

    return dedent(snippet).format(n=name, p=pos, t=target, u=updir)


def write_object(viewobj, mesh, color, alpha):
    """Compute a string in the format of POV-Ray, that represents a FreeCAD
    object
    """

    # This is where you write your object/view in the format of your
    # renderer. "obj" is the real 3D object handled by this project, not
    # the project itself. This is your only opportunity
    # to write all the data needed by your object (geometry, materials, etc)
    # so make sure you include everything that is needed

    snippet = """
    // Generated by FreeCAD (http://www.freecadweb.org/)
    // Declares object '{name}'
    #declare {name} = mesh2 {{
        vertex_vectors {{
            {len_vertices},
            {vertices}
        }}
        normal_vectors {{
            {len_normals},
            {normals}
        }}
        face_indices {{
            {len_indices},
            {indices}
        }}
    }}  // {name}

    // Instance to render {name}
    object {{ {name}
        texture {{
            pigment {{
                color rgb {color}
            }}
            finish {{StdFinish}}
        }}
    }}  // {name}\n"""

    colo = "<{},{},{}>".format(*color)
    vrts = ["<{0.x},{0.z},{0.y}>".format(v) for v in mesh.Topology[0]]
    nrms = ["<{0.x},{0.z},{0.y}>".format(n) for n in mesh.getPointNormals()]
    inds = ["<{},{},{}>".format(*i) for i in mesh.Topology[1]]

    return dedent(snippet).format(name=viewobj.Name,
                                  len_vertices=len(vrts),
                                  vertices="\n        ".join(vrts),
                                  len_normals=len(nrms),
                                  normals="\n        ".join(nrms),
                                  len_indices=len(inds),
                                  indices="\n        ".join(inds),
                                  color=colo)


def write_pointlight(view, location, color, power):
    """Compute a string in the format of POV-Ray, that represents a
    PointLight object
    """
    # this is where you write the renderer-specific code
    # to export the point light in the renderer format

    # Note: power is of no use for POV-Ray, as light intensity is determined
    # by RGB (see POV-Ray documentation)
    snippet = """
    // Generated by FreeCAD (http://www.freecadweb.org/)
    // Declares point light {0}
    light_source {{
        <{1.x},{1.z},{1.y}>
        color rgb<{2[0]},{2[1]},{2[2]}>
    }}\n"""

    return dedent(snippet).format(view.Name, location, color)


def render(project, prefix, external, output, width, height):
    """Run POV-Ray

    Params:
    - project:  the project to render
    - prefix:   a prefix string for call (will be inserted before path to Lux)
    - external: a boolean indicating whether to call UI (true) or console
                (false) version of Lux
    - width:    rendered image width, in pixels
    - height:   rendered image height, in pixels

    Return: path to output image file
    """

    # Here you trigger a render by firing the renderer
    # executable and passing it the needed arguments, and
    # the file it needs to render

    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")

    prefix = params.GetString("Prefix", "")
    if prefix:
        prefix += " "

    rpath = params.GetString("PovRayPath", "")
    if not rpath:
        App.Console.PrintError("Unable to locate renderer executable. "
                               "Please set the correct path in "
                               "Edit -> Preferences -> Render")
        return ""

    args = params.GetString("PovRayParameters", "")
    if args:
        args += " "
    if "+W" in args:
        args = re.sub(r"\+W[0-9]+", "+W{}".format(width), args)
    else:
        args = args + "+W{} ".format(width)
    if "+H" in args:
        args = re.sub(r"\+H[0-9]+", "+H{}".format(height), args)
    else:
        args = args + "+H{} ".format(height)
    if output:
        args = args + "+O{} ".format(output)

    cmd = prefix + rpath + " " + args + project.PageResult
    App.Console.PrintMessage("Renderer command: %s\n" % cmd)
    os.system(cmd)

    return output if output else os.path.splitext(project.PageResult)[0]+".png"
