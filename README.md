SimulinkInterface
================

SimulinkInterface is a Python utility designed to parse Simulink model files (.slx). It extracts detailed block-level information, including parameters, masks, and subsystem hierarchies. It also has generates interactive SVG files that emulates Simulink model viewer.

Features
--------
- ✅ Parses .slx files to extract block attributes
- ✅ Handles masked blocks and subsystem references
- ✅ Cleans up temporary files automatically
- ✅ Generates SVG files for all layers of model linked to each other.

Requirements
------------
- Python 3.10+
- Install GraphViz (or) download GraphViz binaries, modify the Environment variable "Path" to include path to "bin" folder of the downloaded GraphViz binaries.
- Uses other standard libraries such as: os, shutil, zipfile, xml.etree.ElementTree)

Usage
-----
    import SimulinkInterface
    model = SimulinkInterface.SimulinkModel("path/to/simulink_model.slx")

Output Structure
----------------
A Python object will be created that contains the following:
- block_list
- connection_list

Each block in block_list is represented as a dictionary with keys such as:
- Name, SID, BlockType, etc. (from XML attributes)
- Parameters (Gain, SampleTime, etc.)
- Mask details:
  - Mask_Type
  - Mask_Help
  - Mask_Parameter_*
- Subsystem children (if any) under 'children' key
- Connections of children under 'child_conns' key

Each connection in connection_list is basically a list of all connections between source and destination block in the top layer.

Apart from the object creation in code, a folder named 'output' will be created with several SVG files. The root.svg is the root of the Simulink model provided.

File Structure Expectations
---------------------------
The input Simulink file should be of extension .slx. Currently, this solution does not support .mdl files.

Temporary Folder
----------------
All extracted files are stored in a temporary folder named 'temp' located in the same directory as the script. This folder is automatically cleaned up when the object is deleted or undergoes garbage collection.

Example
-------
    import SimulinkInterface
    model = SimulinkInterface.SimulinkModel("path/to/simulink_model.slx")
    for block in model.block_list:
      print(block["Name"], block.get("Gain", "N/A"))

License
-------
This project is licensed under the MIT License.
This project also includes components developed by:
- AT&T and the GraphViz community, which are licensed under the Eclipse Public License (EPL). 

Please refer to the respective licenses for more details.