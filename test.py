from SimulinkParser import SimulinkParser
parser = SimulinkParser()
x = parser.fcn_parse_model("C:\Work\ModelDiffTool\L3DrvMon_MDCE_SHELL.slx")
y = parser.fcn_find_block(x,"SID","724")
print(x)