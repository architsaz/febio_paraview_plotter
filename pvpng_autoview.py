# run this script by pvpython (not python3) from path: ~/ParaView-5.12.0-MPI-Linux-Python3.10-x86_64/bin/pvpython

from paraview.simple import *
import argparse
import numpy as np
import subprocess
import math
import os
import shutil
import sys
import re
import json

def sanitize_filename(name):
    # Replace anything not alphanumeric or underscore with underscore
    return re.sub(r'[^\w\-_.]', '_', name)

# Create the argument parser
parser = argparse.ArgumentParser(
    description="Visualize and optionally save animation or frames from VTK data with optional programmable filter."
)

# Required positional arguments
parser.add_argument("vtk_file", help="Path to the input VTK file.")
parser.add_argument("mask_file", help="Path to the mask VTK file which included relems field.")
parser.add_argument("colormap_json", help="Path to the JSON file defining the colormap.")
parser.add_argument("n_frames", type=int, help="Number of frames to generate.")

# Optional flags
parser.add_argument("--anim", action="store_true", help="If set, save animation instead of individual frame images.")
parser.add_argument("--outdir", type=str, default=None, help="Optional output directory for saved results.")
parser.add_argument("--cam", dest="CameraView", type=str, default=None, help="Optional to define camera view in JSON format for rendering picture (NOT anim).")
parser.add_argument("--case", dest="case_name", type=str, default=None, help="Required for cameraview option, specified case_name inside camera view file.")

# Optional programmable filter
parser.add_argument(
    "-pf", "--pf",
    dest="programmable_filter",
    type=str,
    help="Path to a programmable filter Python script. If provided, it will be applied to the pipeline."
)

# Parse arguments
args = parser.parse_args()

# Assign arguments to variables
vtk_dir = args.vtk_file
mask_dir = args.mask_file
colormap_dir = args.colormap_json
n_frames = args.n_frames
save_anim = args.anim
output_dir = args.outdir

# Programmable filter logic
used_pf = args.programmable_filter is not None
pf_script_path = args.programmable_filter if used_pf else None
used_cameraview = args.CameraView is not None
cameraview_path = args.CameraView if used_cameraview else None
if save_anim and used_cameraview :
    print(f"Error: Camera View files option can just used for the rendering picture not anim.", file=sys.stderr)
    exit()
used_casename = args.case_name is not None
case_name = args.case_name if used_casename else None
if used_cameraview and not case_name :
    print(f"Error: To scpecified the camera view propertics in JSON file, case_name required.", file=sys.stderr)
    exit()  
# Check the existence of files 
try:
    with open(vtk_dir, "r") as file:
        vtk_content = file.readlines()  
except FileNotFoundError:
    print(f"Error: {vtk_dir} not found.", file=sys.stderr)
    exit()
try:
    with open(mask_dir, "r") as file:
        mask_content = file.readlines()  
except FileNotFoundError:
    print(f"Error: {mask_dir} not found.", file=sys.stderr)
    exit()
# Load and check colormap JSON
try:
    with open(colormap_dir, "r") as f:
        fields_config = json.load(f)
except FileNotFoundError:
    print(f"Error: {colormap_dir} not found.", file=sys.stderr)
    exit()
except json.JSONDecodeError:
    print(f"Error: Failed to parse JSON in {colormap_dir}.", file=sys.stderr)
    exit()
if used_cameraview:       
    try:
        with open(cameraview_path, "r") as f:
            cameraview_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: {cameraview_path} not found.", file=sys.stderr)
        exit()
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON in {cameraview_path}.", file=sys.stderr)
        exit()    
# Output directory
if not output_dir:
    output_dir = vtk_dir.replace(".vtk", "")
if save_anim:
    output_dir = os.path.join(output_dir, "anim")
else:
    output_dir = os.path.join(output_dir, "pic")
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)            
# Load vtk data
reader1 = LegacyVTKReader(FileNames=[vtk_dir])    # Main geometry + stress fields
reader2 = LegacyVTKReader(FileNames=[mask_dir])   # Region mask with "relems" field

appended = AppendAttributes(Input=[reader2, reader1])
appended.UpdatePipeline()

cell_centers = CellCenters(Input=appended)
cell_centers.UpdatePipeline()

if not used_cameraview:
    # Get point data
    centroids = servermanager.Fetch(cell_centers).GetPoints()
    centroids_np = np.array([centroids.GetPoint(i) for i in range(centroids.GetNumberOfPoints())])
    # Get 'relems' array
    relems_array = servermanager.Fetch(appended).GetCellData().GetArray("relems")
    relems_np = np.array([relems_array.GetValue(i) for i in range(relems_array.GetNumberOfTuples())])

    dome_centroid = centroids_np[relems_np == 16].mean(axis=0)
    body_centroid = centroids_np[relems_np == 8].mean(axis=0)
    neck_centroid = centroids_np[relems_np == 4].mean(axis=0)

    focal = body_centroid
    axis_vector = dome_centroid - neck_centroid
    axis_vector /= np.linalg.norm(axis_vector)

    # Choose an arbitrary vector not parallel to axis
    v = np.array([1, 0, 0])
    if np.allclose(np.cross(axis_vector, v), 0):
        v = np.array([0, 1, 0])
        
    # Orthogonal vector to axis
    u = np.cross(axis_vector, v)
    u = u / np.linalg.norm(u)

    # Camera radius (e.g., 1.5 × aneurysm size)
    radius = 1.5 * np.linalg.norm(dome_centroid - neck_centroid)
    base_vector = radius * u

# added programmable Filter option to the pipeline of Paraview
if used_pf:
    pf = ProgrammableFilter(Input=appended)
    if os.path.exists(pf_script_path):
        with open(pf_script_path, "r") as f:
            pf.Script = f.read()
    else:
        print(f"Error: {pf_script_path} not found.", file=sys.stderr)
        sys.exit(1)
    pf.UpdatePipeline()
else:
    pf = appended
# Create a render view explicitly
view = CreateRenderView()
display = Show(pf, view)  # Link reader to view
Render()

# Get scalar fields
point_arrays = pf.PointData.keys()
cell_arrays = pf.CellData.keys()

print (f"* Found below fields in the {vtk_dir}")
print("PointData:", point_arrays)
print("CellData:", cell_arrays)

all_fields = [('POINT_DATA', name) for name in point_arrays] + \
             [('CELL_DATA', name) for name in cell_arrays]

# Iterate through fields
for data_type, field_name in all_fields:
    if field_name not in fields_config.get("fields_to_render", None) and "UQ" not in field_name:
        continue
    try:
        display = GetDisplayProperties(pf)
        ColorBy(display, (data_type, field_name))
        # Load transfer functions
        colorLUT = GetColorTransferFunction(field_name)

        field_cfg = fields_config.get(field_name, None)
        if field_cfg:
            if field_cfg["type"] == "categorical":
                # Handle categorical fields
                colorLUT.InterpretValuesAsCategories = 1
                
                # Set Annotations and Colors
                annotations = field_cfg["annotations"]
                flat_annotations = []
                for val, label in annotations.items():
                    flat_annotations.extend([val, label])
                colorLUT.Annotations = flat_annotations

                # Set IndexedColors (flatten the list of RGB triplets)
                flat_colors = [c for triplet in field_cfg["colors"] for c in triplet]
                colorLUT.IndexedColors = flat_colors

            elif field_cfg["type"] == "continuous":    
                vmin, vmax = field_cfg["range"]
                colorLUT.RescaleTransferFunction(vmin, vmax)
                opacityTF = GetOpacityTransferFunction(field_name)
                opacityTF.RescaleTransferFunction(vmin, vmax)   

        else:
            # Default: continuous color map
            colorLUT.RescaleTransferFunctionToDataRange(pf, field_name)
            opacityTF = GetOpacityTransferFunction(field_name)
            opacityTF.RescaleTransferFunctionToDataRange(pf, field_name)

        display.SetScalarBarVisibility(view, True)
        scalar_bar = GetScalarBar(colorLUT, view)
        scalar_bar.Title = field_name
        scalar_bar.ComponentTitle = ""
        scalar_bar.TitleFontSize = 7
        scalar_bar.LabelFontSize = 5
        scalar_bar.Position = [0.85, 0.05]
        scalar_bar.ScalarBarLength = 0.3

    except Exception as e:
        print(f"Skipping {field_name} ({data_type}) due to error: {e}")
        continue
    if used_cameraview:
        for name, params in cameraview_config.get(case_name).items():
            view.CameraPosition = params["CameraPosition"]
            view.CameraFocalPoint = params["CameraFocalPoint"]
            view.CameraViewUp = params["CameraViewUp"]
            view.CameraParallelScale = params["CameraParallelScale"]
            Render()
            safe_field = sanitize_filename(field_name)
            img_file = os.path.join(output_dir, f"{safe_field}_{name}.png")
            SaveScreenshot(img_file, view, ImageResolution=[3840, 2880])

    else:    
        for i in range(n_frames):
            theta = 2 * math.pi * i / n_frames
            rot_axis = axis_vector
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            cross = np.cross(rot_axis, base_vector)
            dot = np.dot(rot_axis, base_vector)
            rotated = base_vector * cos_t + cross * sin_t + rot_axis * dot * (1 - cos_t)

            cam_pos = focal + rotated
            view.CameraPosition = cam_pos
            view.CameraFocalPoint = focal
            view.CameraViewUp = axis_vector  # consistent roll


            Render()
            safe_field = sanitize_filename(field_name)
            img_file = os.path.join(output_dir, f"{safe_field}_view_{i:03d}.png")
            SaveScreenshot(img_file, view, ImageResolution=[3840, 2880])
    if save_anim:
        bash_command = "/dagon1/achitsaz/app/ffmpeg-7.0.2-amd64-static/ffmpeg -framerate 24 -i "
        bash_command = bash_command+f"{output_dir}/{safe_field}_view_%03d.png"+" -c:v libx264 -pix_fmt yuv420p "+f"{output_dir}/{safe_field}.mp4"
        result = subprocess.run(bash_command, shell=True, capture_output=True, text=True)
        bash_command = f"rm {output_dir}/{safe_field}_*.png"
        result = subprocess.run(bash_command, shell=True, capture_output=True, text=True)

    # clean bar legend
    display.SetScalarBarVisibility(view, False)    

# Cleanup
Delete(pf)
del pf




