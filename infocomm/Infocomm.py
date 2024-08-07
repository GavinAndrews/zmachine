from Processor import Processor
from infocomm.AbbreviationTable import AbbreviationTable
from infocomm.ObjectTable import ObjectTable
from infocomm.PropertyTable import PropertyTable

fileName = "../data/ZORK1.DAT"

with open(fileName, mode='rb') as file:  # b is important -> binary
    fileContent = file.read()


ZVERSION_version = int.from_bytes(fileContent[0:1], 'little')
ZVERSION_mode = fileContent[1]
ZORKID = int.from_bytes(fileContent[2:4], 'big')
ENDLOD = int.from_bytes(fileContent[4:6], 'big')
START = int.from_bytes(fileContent[6:8], 'big')
VOCAB = int.from_bytes(fileContent[8:10], 'big')
OBJECT = int.from_bytes(fileContent[10:12], 'big')
GLOBALS = int.from_bytes(fileContent[12:14], 'big')
PURBOT = int.from_bytes(fileContent[0x000E:0x0010], 'big')
FLAGS = fileContent[16:18]
SERIAL = fileContent[18:24]
FWORDS = int.from_bytes(fileContent[0x0018:0x0018+2], 'big')
PLENTH = int.from_bytes(fileContent[26:28], 'big')
PCHKSUM = int.from_bytes(fileContent[28:30], 'big')

print(ZVERSION_version, ZVERSION_mode)
print(ZORKID)
print(ENDLOD)
print(START)
print(f"VOCAB: {VOCAB:04X}")
print(f"OBJECT: {OBJECT:04X}")
print(f"GLOBALS: {GLOBALS:04X}")
print(f"PURBOT: {PURBOT:04X}")

print(FLAGS)
print(SERIAL)
print(f"FWORDS: {FWORDS:04X}")  # AKA Abbreviations
print(f"PLENTH: {PLENTH:04X}")
print(f"PCHKSUM: {PCHKSUM:04X}")

abbreviationTable = AbbreviationTable(start_location=FWORDS, memory=fileContent)
for i in range(0, 96):
    print("|"+abbreviationTable.toString(i)+"|")

objectTable = ObjectTable(start_location=OBJECT, memory=fileContent, abbreviations=abbreviationTable)
property_table = PropertyTable(memory=fileContent)
property_entry = property_table.find(0x0BCB)
property_entry.describe()

# for i in range(1, 250+1):
#     obj = objectTable.find(i)
#     print(f"{i:3} \"{obj.description()}\"")
#     obj.dump_properties()

processor = Processor(memory=fileContent, start=START)
processor.next_instruction()
processor.next_instruction()
