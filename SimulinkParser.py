import os
import shutil
import zipfile
import xml.etree.ElementTree as ET

class SimulinkParser:
    def __init__(self):
        self.tempFolderPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),"temp")
        self.__util_init_temp()

    def __del__(self):
        self.__util_cleanup_temp()

    def __util_find_file(self, target_file_name):
        for root, dirs, files in os.walk(self.tempFolderPath):
            if target_file_name in files:
                return os.path.join(root, target_file_name)
        return None

    def __util_init_temp(self):
        if os.path.exists(self.tempFolderPath):
            shutil.rmtree(self.tempFolderPath)  # Correct way to delete a folder
        os.makedirs(self.tempFolderPath, exist_ok=True)

    def __util_cleanup_temp(self):
        if os.path.exists(self.tempFolderPath):
            shutil.rmtree(self.tempFolderPath)

    def __util_unzip_files(self, file_path):
        file_path_list = []

        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(self.tempFolderPath)
            extracted_files = zip_ref.filelist

        for file in extracted_files:
            file_path_list.append(os.path.join(self.tempFolderPath,file.filename.replace("/","\\")))

        return file_path_list

    def __util_blk_info(self,block):
        temp = block.__copy__()
        # Collect the first set of attributes of the Simulink block
        temp = temp.attrib
        # Get all parameters of the Block
        parameters = block.findall("P")
        # Get Mask of the Block
        mask_detection = block.find("Mask")
        # Get link to another system, if Subsystem Block
        system_ref_detect = block.find("System")
        # Get Port Details
        port_detect = block.find("Port")
        for parameter in parameters:
            temp[list(parameter.attrib.values())[0]] = parameter.text
        if mask_detection is not None:
            temp["Mask_Type"] = mask_detection.find("Type").text
            temp["Mask_Help"] = mask_detection.find("Help").text
            mask_param = mask_detection.find("MaskParameter")
            mask_param_value = mask_param.find("Value").text
            mask_param = mask_param.attrib
            mask_param = {f"Mask_Parameter_{key}": value for key, value in mask_param.items()}
            mask_param["Mask_Parameter_Value"] = mask_param_value
            temp = temp | mask_param

        if system_ref_detect is not None:
            ref = list(system_ref_detect.attrib.values())[0]
            tree_output = ET.parse(self.__util_find_file(ref + ".xml"))
            temp["children"] = self.__util_read_tree(tree_output.getroot())

        if port_detect is not None:
            params = port_detect.findall("P")
            for param in params:
                temp["Port_" + list(param.attrib.values())[0]] = param.text
        return temp

    def __util_read_tree(self,element):
        block_list = element.findall("Block")
        new_block_list = []
        for block in block_list:
            new_block_list.append(self.__util_blk_info(block))
        return new_block_list

    def fcn_find_block(self, block_list, prop, value):
        if block_list:
            for block in block_list:
                if prop in block and block[prop] == value:
                    return block
                if "children" in block.keys():
                    result = self.fcn_find_block(block["children"],prop,value)
                    if result:
                        return result
        return None

    def fcn_parse_model(self,file_path):
        file_path_list = self.__util_unzip_files(file_path)
        for file_path in file_path_list:
            if file_path.endswith("system_root.xml"):
                tree_output = ET.parse(file_path)
                block_list = self.__util_read_tree(tree_output.getroot())
                return block_list