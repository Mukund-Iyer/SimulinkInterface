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
        self.GraphingObject = GraphingInterface(self.block_list)

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
        self.blocks = self.__util_parse_tree(self.tree.getroot())

    def __util_parse_tree(self,element,parent="root"):
        block_list = element.findall("Block")
        conn_list = self.__util_find_all_conns(element)
        new_block_list = []
        for block in block_list:
            simulink_block = self.__util_blk_info(block,conn_list)
            simulink_block["Parent_SID"] = parent
            new_block_list.append(simulink_block)
        return new_block_list

    def __util_blk_info(self, block, connections):
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
            temp["Mask"] = {}
            if mask_detection.find("Type") is not None:
                temp["Mask"]["Type"] = mask_detection.find("Type").text
            if mask_detection.find("Help") is not None:
                temp["Mask"]["Help"] = mask_detection.find("Help").text
            mask_param = mask_detection.find("MaskParameter")
            if mask_param is not None:
                temp["Mask"]["Parameter"] = mask_param.attrib
                temp["Mask"]["Parameter"]["Value"] = mask_param.find("Value").text
        if system_ref_detect is not None:
            ref = list(system_ref_detect.attrib.values())[0]
            tree_output = eT.parse(self.__util_find_file(ref + ".xml"))
            temp["children"] = self.__util_parse_tree(tree_output.getroot(),temp["SID"])
        if port_detect is not None:
            params = port_detect.findall("P")
            for param in params:
                temp["Port_" + list(param.attrib.values())[0]] = param.text
        in_ports, out_ports = self.__util_find_conns(temp["SID"], connections)
        temp["ports"] = {}
        temp["ports"]["In"] = in_ports
        temp["ports"]["Out"] = out_ports

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

    def __util_find_all_conns(self, element):
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

    def __util_find_conns(self, block_sid:str, connections):
        inputs = []
        outputs = []
        for connection in connections:
            if connection["Src"] == block_sid and "Dst" in connection.keys():
                outputs.append(connection["Dst"])
            elif connection["Src"] == block_sid and "Branch_Dst" in connection.keys():
                outputs = outputs + connection["Branch_Dst"]
            if "Dst" in connection.keys() and connection["Dst"] == block_sid:
                inputs.append(connection["Src"])
            elif "Branch_Dst" in connection.keys() and block_sid in connection["Branch_Dst"]:
                inputs.append(connection["Src"])
        return inputs, outputs

    def __util_find_file(self, target_file_name:str):
        for root, dirs, files in os.walk(self.tempFolderPath):
            if target_file_name in files:
                return os.path.join(root, target_file_name)
        return None

class GraphingInterface:
    def __init__(self,block_list,model_name="root"):
        self.blocks = block_list
        self.__generate_model(model_name)

    @staticmethod
    def __generate_label(block):
        in_label = ""
        out_label = ""
        match (block["BlockType"]):
            case "Inport" | "Outport":
                if "Port" in block.keys():
                    label = "Port_" + block["Port"]
                else:
                    label = "Port_1"
            case "SubSystem":
                label = block["Name"]
            case "Logic" | "RelationalOperator":
                if "Operator" not in block.keys():
                    label = block["Name"]
                else:
                    label = "Operator(" + block["Operator"] + ")"
            case "Constant":
                label = "-C-"
            case "If":
                label = "If(" + block["IfExpression"] + ")"
            case "BusCreator" | "BusSelector":
                label = block["BlockType"]
            case _:
                label = block["Name"]

        for iterator in range(0,len(block["ports"]["In"])):
            in_label += "<in" + str(iterator) + "> In " + str(iterator) + " |"
        if in_label != "":
            in_label = "{" + in_label[:-2] + "}"
        for iterator in range(0, len(block["ports"]["Out"])):
            out_label += "<out" + str(iterator) + "> Out " + str(iterator) + " |"
        if out_label != "":
            out_label = "{" + out_label[:-2] + "}"

        if in_label != "" and out_label != "":
            label = "{ " + in_label + " | " + label + " | " + out_label + " }"
        elif out_label != "":
            label = "{ " + label + " | " + out_label + " }"
        elif in_label != "":
            label = "{ " + in_label + " | " + label + " }"

        return label

    @staticmethod
    def __util_create_node(dot,block):
        tooltip_value = GraphingInterface.__get_block_val(block)
        label = GraphingInterface.__generate_label(block)
        match(block["BlockType"]):
            case "Inport" | "Outport":
                dot.node(block["SID"], label, shape='record', style='rounded', tooltip = tooltip_value)
            case "SubSystem":
                probable_path = os.path.join(os.getcwd(), "output", block["SID"] + ".svg")
                if not os.path.isfile(probable_path):
                    GraphingInterface(block["children"], block["SID"])
                dot.node(block["SID"], label, shape='record', height='3', URL=probable_path,tooltip=tooltip_value)
            case _:
                dot.node(block["SID"], label, shape='record', tooltip=tooltip_value)

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
    def __get_block_val(block):
        excluded_keys = {'children'}
        lines = (
            f"{k}: {v}"
            for k, v in block.items()
            if k not in excluded_keys
        )
        return '\n'.join(lines)

    def __generate_model(self,name):
        dot = Digraph(comment='Custom Node Shapes')
        dot.attr(rankdir='LR')

        for block in self.blocks:
            GraphingInterface.__util_create_node(dot,block)

        added_edges = set()

        for block in self.blocks:
            for i, src in enumerate(block["ports"]["In"]):
                edge = (src, block["SID"], "in", i)
                if edge not in added_edges:
                    dot.edge(src + ":out" + str(i), block["SID"] + ":in" + str(i))#, tailport='e', headport='w')
                    added_edges.add(edge)

            for i, dst in enumerate(block["ports"]["Out"]):
                edge = (block["SID"], dst, "out", i)
                if edge not in added_edges:
                    dot.edge(block["SID"] + ":out" + str(i), dst + ":in" + str(i))#, tailport='e', headport='w')
                    added_edges.add(edge)

        """
        for block in self.blocks:
            in_count = 0
            out_count = 0
            for iterator in range(0,len(block["ports"]["In"])):
                dot.edge(block["ports"]["In"][iterator] + ":out" + str(in_count), block["SID"] + ":" + "in" + str(iterator), tailport='e', headport='w')
                in_count += 1
            for iterator in range(0,len(block["ports"]["Out"])):
                dot.edge(block["SID"] + ":" + "out" + str(iterator),block["ports"]["Out"][iterator] + ":in" + str(out_count), tailport='e', headport='w')
                out_count += 1
        """
        dot.render(os.path.join(os.getcwd(),"output",name), format='svg', cleanup=True)
        print("")