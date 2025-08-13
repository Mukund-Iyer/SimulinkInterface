SimulinkParser
================

SimulinkParser is a Python utility designed to parse Simulink model files (.slx) exported as .zip archives containing XML representations of block diagrams. It extracts detailed block-level information, including parameters, masks, and subsystem hierarchies.

Features
--------
- ✅ Unzips Simulink model archives
- ✅ Parses XML files to extract block attributes
- ✅ Handles masked blocks and subsystem references
- ✅ Recursively parses nested subsystems
- ✅ Cleans up temporary files automatically

Requirements
------------
- Python 3.6+
- No external dependencies (uses standard libraries: os, shutil, zipfile, xml.etree.ElementTree)

Usage
-----
    from simulink_parser import SimulinkParser
    parser = SimulinkParser()
    block_data = parser.fcn_parse_model("path/to/simulink_model.zip")

#block_data is a list of dictionaries containing block information

Output Structure
----------------
Each block is represented as a dictionary with keys such as:
- Name, SID, BlockType, etc. (from XML attributes)
- Parameters (Gain, SampleTime, etc.)
- Mask details:
  - Mask_Type
  - Mask_Help
  - Mask_Parameter_*
- Subsystem children (if any) under 'children' key

File Structure Expectations
---------------------------
The .zip file should contain:
- system_root.xml (entry point)
- Additional .xml files for subsystems (referenced by block attributes)

Temporary Folder
----------------
All extracted files are stored in a temporary folder named 'temp' located in the same directory as the script. This folder is automatically cleaned up when the parser object is deleted.

Example
-------
    parser = SimulinkParser()
    blocks = parser.fcn_parse_model("model.zip")
    for block in blocks:
      print(block["Name"], block.get("Gain", "N/A"))

License
-------
This project is released under the MIT License.
