# run this script by pvpython (not python3)
from paraview.simple import *
import os

# # Set your data directory and output directory
# data_dir = "/path/to/your/vtk/files"
# output_dir = "/path/to/output/images"
# os.makedirs(output_dir, exist_ok=True)

# # Define camera views (position, focal_point, view_up)
# camera_views = [
#     ((1, 0, 0), (0, 0, 0), (0, 0, 1)),  # View from X
#     ((0, 1, 0), (0, 0, 0), (0, 0, 1)),  # View from Y
#     ((0, 0, 1), (0, 0, 0), (0, 1, 0)),  # View from Z
#     ((1, 1, 1), (0, 0, 0), (0, 0, 1)),  # Isometric
# ]

# # Get all .vtk files
# vtk_files = [f for f in os.listdir(data_dir) if f.endswith(".vtk")]

# for vtk_file in vtk_files:
#     vtk_path = os.path.join(data_dir, vtk_file)
#     case_name = os.path.splitext(vtk_file)[0]
    
#     # Load the data
#     reader = LegacyVTKReader(FileNames=[vtk_path])
#     Show(reader)
#     Render()

#     # Get scalar fields
#     point_arrays = reader.PointData.keys()

#     for field_name in point_arrays:
#         ColorBy(GetDisplayProperties(reader), ('POINT_DATA', field_name))
#         ResetScalarRange()
#         Render()

#         for i, (pos, fp, vu) in enumerate(camera_views):
#             view = GetActiveView()
#             view.CameraPosition = pos
#             view.CameraFocalPoint = fp
#             view.CameraViewUp = vu
#             view.ResetCamera()
#             Render()

#             out_name = f"{case_name}_{field_name}_view{i+1}.png"
#             out_path = os.path.join(output_dir, out_name)
#             SaveScreenshot(out_path, view, ImageResolution=[1024, 768])

#     # Cleanup
#     Delete(reader)
#     del reader
