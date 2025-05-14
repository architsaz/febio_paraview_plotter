# run this script by pvpython (not python3)
# for access to the camera view :
# view = GetActiveView()
# print("CameraPosition:", view.CameraPosition)
# print("CameraFocalPoint:", view.CameraFocalPoint)
# print("CameraViewUp:", view.CameraViewUp)
# print("CameraParallelScale:", view.CameraParallelScale)
from paraview.simple import *
import os
import shutil
import sys
import re
import json

def sanitize_filename(name):
    # Replace anything not alphanumeric or underscore with underscore
    return re.sub(r'[^\w\-_.]', '_', name)

# Set your data directory and output directory  
dir_runfebio = "/dagon1/achitsaz/runfebio/" 
if len(sys.argv) > 2:
    vtk_dir = sys.argv[1]
    CameraView_dir = sys.argv[2]
    colormap_dir = sys.argv[3]
else:
    print("Error: No argument provided.", file=sys.stderr) 
    exit()

# Check the existence of files 
try:
    with open(vtk_dir, "r") as file:
        vtk_content = file.readlines()  
except FileNotFoundError:
    print(f"Error: {vtk_dir} not found.", file=sys.stderr)
    exit()

try:
    with open(CameraView_dir, "r") as file:
        CameraView_content = file.readlines()  
except FileNotFoundError:
    print(f"Error: {CameraView_dir} not found.", file=sys.stderr)
    exit()
try:
    with open(colormap_dir, "r") as file:
        colormap_dir_content = file.readlines()  
except FileNotFoundError:
    print(f"Error: {colormap_dir} not found.", file=sys.stderr)
    exit()    

# Output directory
output_dir = vtk_dir.replace(".vtk", "") + "/"
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)

# load camera view and colormap configuration files   
with open(CameraView_dir, "r") as f:
    cameraview_config = json.load(f)
with open(colormap_dir, "r") as f:
    fields_config = json.load(f) 
                         
# Load vtk data
reader = LegacyVTKReader(FileNames=[vtk_dir])
reader.UpdatePipeline()

# Create a render view explicitly
view = CreateRenderView()
display = Show(reader, view)  # Link reader to view
Render()

# Get scalar fields
point_arrays = reader.PointData.keys()
cell_arrays = reader.CellData.keys()

# point_arrays = []
# cell_arrays = ["uni/bi_region"]
print (f"* Found below fields in the {vtk_dir}")
print("PointData:", point_arrays)
print("CellData:", cell_arrays)

all_fields = [('POINT_DATA', name) for name in point_arrays] + \
             [('CELL_DATA', name) for name in cell_arrays]

# Iterate through fields
for data_type, field_name in all_fields:
    try:
        display = GetDisplayProperties(reader)
        ColorBy(display, (data_type, field_name))
        # Load transfer functions
        colorLUT = GetColorTransferFunction(field_name)

        field_cfg = fields_config.get(field_name, None)
        if field_cfg:
            if field_cfg["type"] == "categorical":
                print(field_name)
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
            colorLUT.RescaleTransferFunctionToDataRange(reader, field_name)
            opacityTF = GetOpacityTransferFunction(field_name)
            opacityTF.RescaleTransferFunctionToDataRange(reader, field_name)

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
    for name, params in cameraview_config.items():
        view.CameraPosition = params["CameraPosition"]
        view.CameraFocalPoint = params["CameraFocalPoint"]
        view.CameraViewUp = params["CameraViewUp"]
        view.CameraParallelScale = params["CameraParallelScale"]
        Render()
        field_name = sanitize_filename(field_name)
        out_name = f"{field_name}_{name}.png"
        out_path = os.path.join(output_dir, out_name)
        SaveScreenshot(out_path, view, ImageResolution=[3840, 2880])

    # clean bar legend
    display.SetScalarBarVisibility(view, False)    

# Cleanup
Delete(reader)
del reader

