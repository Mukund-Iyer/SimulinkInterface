from SimulinkInterface import SimulinkParser
parser = SimulinkParser("C:\Work\ModelDiffTool\L3DrvMon_MDCE_SHELL.slx")
x = parser.find_system("SID", "724")
print(x)