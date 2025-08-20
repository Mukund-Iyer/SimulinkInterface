import shutil
import xml.etree.ElementTree as eT
import os
import zipfile

class SimulinkParser:
    def __init__(self,path):
        self.Model = SimulinkModel(path)

    def find_system(self,prop, value):
        return SimulinkModel.find_system(self.Model.block_list,prop,value)

class SimulinkModel:
    def __init__(self,model_path):
        self.tempFolderPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        file_path_list = self.__util_unzip_files(model_path)
        for file_path in file_path_list:
            if file_path.endswith("system_root.xml"):
                tree_output = eT.parse(file_path)
                self.block_list = SimulinkModel.__util_parse_tree(tree_output.getroot())

    def __del__(self):
        if os.path.isdir(self.tempFolderPath):
            shutil.rmtree(self.tempFolderPath)

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

    @staticmethod
    def __util_parse_tree(element):
        block_list = element.findall("Block")
        new_block_list = []
        for block in block_list:
            simulink_block = SimulinkBlock(block)
            new_block_list.append(simulink_block.details)
        return new_block_list

    @staticmethod
    def find_system(input_block_list,prop, value):
        if input_block_list:
            for block in input_block_list:
                if prop in block and block[prop] == value:
                    return block
                if "children" in block.keys():
                    result = SimulinkModel.find_system(block["children"], prop, value)
                    if result:
                        return result
        return None

class SimulinkBlock:
    def __init__(self,block):
        self.tempFolderPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        self.details = self.__util_blk_info(block)

    def __util_find_file(self, target_file_name):
        for root, dirs, files in os.walk(self.tempFolderPath):
            if target_file_name in files:
                return os.path.join(root, target_file_name)
        return None

    def __util_read_tree(self,element):
        block_list = element.findall("Block")
        new_block_list = []
        for block in block_list:
            new_block_list.append(self.__util_blk_info(block))
        return new_block_list

    def __util_blk_info(self, block):
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
            tree_output = eT.parse(self.__util_find_file(ref + ".xml"))
            temp["children"] = self.__util_read_tree(tree_output.getroot())

        if port_detect is not None:
            params = port_detect.findall("P")
            for param in params:
                temp["Port_" + list(param.attrib.values())[0]] = param.text
        return temp

class SimulinkConnection:
    def __init__(self,element):
        self.connections = self.fcn_find_conns(element)

    def __util_branch_handling(self,branch,temp):
        branch_params = branch.findall("P")
        nested_branch_detect = branch.findall("Branch")
        for branch_param in branch_params:
            if branch_param.attrib['Name'] == "Src" or branch_param.attrib['Name'] == "Dst":
                if "Branch_" + branch_param.attrib['Name'] in temp:
                    if isinstance(temp["Branch_" + branch_param.attrib['Name']], str):
                        temp_var = temp["Branch_" + branch_param.attrib['Name']]
                        temp["Branch_" + branch_param.attrib['Name']] = []
                        temp["Branch_" + branch_param.attrib['Name']].append(temp_var)
                        temp["Branch_" + branch_param.attrib['Name']].append(branch_param.text)
                    else:
                        temp["Branch_" + branch_param.attrib['Name']].append(branch_param.text)
                else:
                    temp["Branch_" + branch_param.attrib['Name']] = branch_param.text
        if nested_branch_detect:
            for branch in nested_branch_detect:
                temp = self.__util_branch_handling(branch,temp)
        return temp

    def fcn_find_conns(self,element):
        line_list = element.findall("Line")
        conn_list = []
        for line in line_list:
            temp = {}
            params = line.findall("P")
            branches = line.findall("Branch")
            for param in params:
                if param.attrib['Name'] == "Src" or param.attrib['Name'] == "Dst":
                    temp[param.attrib['Name']] = param.text

            if branches:
                for branch in branches:
                    temp = self.__util_branch_handling(branch,temp)

            conn_list.append(temp)
        return conn_list