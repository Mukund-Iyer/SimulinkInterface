import shutil
import xml.etree.ElementTree as eT
import os
import zipfile
from graphviz import Digraph

class SimulinkModel:
    def __init__(self, model_path):
        self.__model_path = model_path
        self.__tempFolderPath = os.path.join(os.getcwd(), "temp")
        file_path_list = self.__util_unzip_files()
        for file_path in file_path_list:
            if file_path.endswith("system_root.xml"):
                self.tree = eT.parse(file_path)
                break
        sp = SimulinkParser(self.tree, self.__tempFolderPath)
        if os.path.isdir(self.__tempFolderPath):
            shutil.rmtree(self.__tempFolderPath)
        self.block_list = sp.blocks
        self.connection_list = sp.connections
        self.GraphingObject = GraphingInterface(self.block_list, self.connection_list)

    def __util_unzip_files(self):
        file_path_list = []

        with zipfile.ZipFile(self.__model_path, 'r') as zip_ref:
            zip_ref.extractall(self.__tempFolderPath)
            extracted_files = zip_ref.filelist

        for file in extracted_files:
            file_path_list.append(os.path.join(self.__tempFolderPath, file.filename.replace("/", "\\")))

        return file_path_list

class SimulinkParser:
    def __init__(self,input_tree,temp_folder_path):
        self.tree = input_tree
        self.tempFolderPath = temp_folder_path
        self.blocks,self.connections = self.__util_parse_tree(self.tree.getroot())

    def __util_parse_tree(self,element,parent="root"):
        block_list = element.findall("Block")
        conn_list = self.__util_find_conns(element)
        new_block_list = []
        for block in block_list:
            simulink_block = self.__util_blk_info(block)
            simulink_block["Parent_SID"] = parent
            new_block_list.append(simulink_block)
        return new_block_list,conn_list

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
            if mask_detection.find("Type") is not None:
                temp["Mask_Type"] = mask_detection.find("Type").text
            if mask_detection.find("Help") is not None:
                temp["Mask_Help"] = mask_detection.find("Help").text
            mask_param = mask_detection.find("MaskParameter")
            if mask_param is not None:
                mask_param_value = mask_param.find("Value").text
                mask_param = mask_param.attrib
                mask_param = {f"Mask_Parameter_{key}": value for key, value in mask_param.items()}
                mask_param["Mask_Parameter_Value"] = mask_param_value
                temp = temp | mask_param

        if system_ref_detect is not None:
            ref = list(system_ref_detect.attrib.values())[0]
            tree_output = eT.parse(self.__util_find_file(ref + ".xml"))
            temp["children"],temp["child_conns"] = self.__util_parse_tree(tree_output.getroot(),temp["SID"])

        if port_detect is not None:
            params = port_detect.findall("P")
            for param in params:
                temp["Port_" + list(param.attrib.values())[0]] = param.text
        return temp

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
                        temp["Branch_" + branch_param.attrib['Name']].append(branch_param.text.split("#")[0])
                    else:
                        temp["Branch_" + branch_param.attrib['Name']].append(branch_param.text.split("#")[0])
                else:
                    temp["Branch_" + branch_param.attrib['Name']] = branch_param.text.split("#")[0]
        if nested_branch_detect:
            for branch in nested_branch_detect:
                temp = self.__util_branch_handling(branch,temp)
        return temp

    def __util_find_conns(self,element):
        line_list = element.findall("Line")
        conn_list = []
        for line in line_list:
            temp = {}
            params = line.findall("P")
            branches = line.findall("Branch")
            for param in params:
                if param.attrib['Name'] == "Src" or param.attrib['Name'] == "Dst":
                    temp[param.attrib['Name']] = param.text.split("#")[0]

            if branches:
                for branch in branches:
                    temp = self.__util_branch_handling(branch,temp)

            conn_list.append(temp)
        return conn_list

    def __util_find_file(self, target_file_name:str):
        for root, dirs, files in os.walk(self.tempFolderPath):
            if target_file_name in files:
                return os.path.join(root, target_file_name)
        return None

class GraphingInterface:
    def __init__(self,block_list,connections,model_name="root"):
        self.blocks = block_list
        self.conns = connections
        self.visualize(self.conns,model_name)

    @staticmethod
    def find_block(input_block_list, prop, value):
        if input_block_list:
            for block in input_block_list:
                if prop in block and block[prop] == value:
                    return block
                if "children" in block.keys():
                    result = GraphingInterface.find_block(block["children"], prop, value)
                    if result:
                        return result
        return None

    @staticmethod
    def __util_set_node(dot,block):
        if block["BlockType"] == "Inport" or block["BlockType"] == "Outport":
            return dot.node(block["Name"], block["Name"], shape='box', style='rounded', tooltip=GraphingInterface.__get_block_val(block))
        elif block["BlockType"] == "SubSystem":
            probable_path = os.path.join(os.getcwd(), "output", block["Name"] + ".svg")
            if not os.path.isfile(probable_path):
                GraphingInterface(block["children"], block["child_conns"], block["Name"])
            return dot.node(block["Name"], block["Name"], shape='box', URL=block["Name"] + ".svg", tooltip=GraphingInterface.__get_block_val(block))
        elif block["BlockType"] == "Logic" or block["BlockType"] == "RelationalOperator":
            if "Operator" not in block.keys():
                return dot.node(block["Name"], block["Name"], shape='box', tooltip=GraphingInterface.__get_block_val(block))
            else:
                return dot.node(block["Name"], block["Operator"], shape='box', tooltip=GraphingInterface.__get_block_val(block))
        elif block["BlockType"] == "Constant":
            return dot.node(block["Name"], block["Value"], shape='box', tooltip=GraphingInterface.__get_block_val(block))
        elif block["BlockType"] == "If":
            return dot.node(block["Name"], block["BlockType"] + "\n" + block["IfExpression"], shape='box', tooltip=GraphingInterface.__get_block_val(block))
        else:
            return dot.node(block["Name"], block["Name"], shape='box', tooltip=GraphingInterface.__get_block_val(block))

    @staticmethod
    def __get_block_val(block):
        excluded_keys = {'children', 'child_conns','Mask_Help'}
        lines = (
            f"{k}: {v}"
            for k, v in block.items()
            if k not in excluded_keys and not str(k).startswith("Mask_Parameter")
        )
        return '\n'.join(lines)

    def visualize(self,connections:list,name:str):
        dot = Digraph(comment='Custom Node Shapes')
        dot.attr(rankdir='LR')

        for connection in connections:
            src_block_sid = connection["Src"]
            if "Dst" in connection.keys():
                dst_block_sids = connection["Dst"]
            else:
                dst_block_sids = connection["Branch_Dst"]
            src_block = GraphingInterface.find_block(self.blocks, "SID", src_block_sid)
            GraphingInterface.__util_set_node(dot, src_block)
            #dot.node(src_block["Name"], src_block["Name"], shape='box')
            if isinstance(dst_block_sids,list):
                for dst_blk_sid in dst_block_sids:
                    dst_block = GraphingInterface.find_block(self.blocks, "SID", dst_blk_sid)
                    GraphingInterface.__util_set_node(dot, dst_block)
                    #dot.node(dst_block["Name"], dst_block["Name"], shape='box')
                    dot.edge(src_block["Name"], dst_block["Name"],tailport='e', headport='w')
            elif isinstance(dst_block_sids,str):
                dst_block = GraphingInterface.find_block(self.blocks, "SID", dst_block_sids)
                GraphingInterface.__util_set_node(dot, dst_block)
                #dot.node(dst_block["Name"], dst_block["Name"], shape='box')
                dot.edge(src_block["Name"], dst_block["Name"],tailport='e', headport='w')
        dot.render(os.path.join(os.getcwd(),"output",name), format='svg', cleanup=True)