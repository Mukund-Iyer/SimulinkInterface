import SimulinkInterface

class SimulinkParser:
    def __init__(self,path):
        self.Model = SimulinkInterface.SimulinkModel(path)

    def find_system(self,prop, value):
        return self.Model.find_system(self.Model.block_list,prop,value)