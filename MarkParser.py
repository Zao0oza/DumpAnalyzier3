import argparse
import xml.etree.cElementTree as ET
import json


parser = argparse.ArgumentParser(description='парсер дампа ebus в json формате, выделяет комманды из мануала, '
                                             'на выходе список исползованных комманд и список коммнад с timestmap')
parser.add_argument('-dump', type=str, default='ebus.json', help='путь к файлу с дампом')
parser.add_argument('-manual', type=str, default='LAN_UPD_211222_Mark1215C.xml', help='путь к файлу с коммандами')

args = parser.parse_args()

tree = ET.parse(args.manual)
command_dict = {}
timestamp_dict = {}
with open(args.dump) as f:
    string = f.read()
    dumps = json.loads(string)


def parser(dumps, tree):
    for i in dumps:
        if i['_source']["layers"].get("gvcp", False):
            for j in i['_source']["layers"]["gvcp"].keys():
                if "Command Header" in j:
                    if i['_source']["layers"]["gvcp"][j].get("gvcp.bootstrap.custom.register.write", False):
                        res = i['_source']["layers"]["gvcp"][j]["gvcp.bootstrap.custom.register.write"]
                        res = res[:2] + res[-4::].upper()
                        text_reg = './/*[{http://www.genicam.org/GenApi/Version_1_0}Address="%s"]' % res
                        result_reg = tree.find(text_reg)
                        if result_reg:
                            text = './/*[{http://www.genicam.org/GenApi/Version_1_0}Integer]/*[@Name="%s"]' % result_reg.get(
                                "Name")[0:-3]
                            result = tree.find(text)
                            if result:
                                command_dict[result.get("Name")] = {x.tag[43:]: x.text for x in tree.find(text)}
                                timestamp_dict[i['_source']["layers"]["frame"]['frame.time_relative']] = [result.get("Name"),command_dict[result.get("Name")]['Description']]
    with open(args.dump[0:-5] + '_command.txt', 'w') as file:
        for k, v in command_dict.items():
            file.write(str(k) + ' ' + str(v) + '\n')
    with open(args.dump[0:-5] + '_timestamp.txt', 'w') as file:
        for k, v in timestamp_dict.items():
            file.write(str(k) + ' ' + str(v) + '\n')
    print('finished')
parser(dumps, tree)

