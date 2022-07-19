# -*- coding: utf-8 -*-

import argparse
import xml.etree.cElementTree as ET
import json

parser = argparse.ArgumentParser(description='парсер дампа ebus в json формате, выделяет комманды из мануала, '
                                             'на выходе список исползованных комманд и список коммнад с timestmap')
parser.add_argument('-dump', type=str, default='viewier/single_gvcp.json', help='путь к файлу с дампом')
parser.add_argument('-manual', type=str, default='LAN_UPD_211222_Mark1215C.xml', help='путь к файлу с коммандами')

args = parser.parse_args()
formula = set()
tree = ET.parse(args.manual)
command_dict = {}
simple_comand_dict = {}

timestamp_dict = {}
with open(args.dump) as f:
    string = f.read()
    dumps = json.loads(string)

result = tree.find(
    './*[{http://www.genicam.org/GenApi/Version_1_1}StructReg]//*[@Comment="%s"]' % 'RemoveParameterLimitInqReg')

features_dict={}
with open('mer_features', 'r') as f:
    for string in f:
        s=string.split("#")
        name=s[0].split('=')
        features_dict[name[0]]=[name[1].replace(" ",''),s[1]]

def parser(dumps, tree, manual):
    for x in tree.findall('.//*{http://www.genicam.org/GenApi/Version_1_1}Formula'):
        formula.add(x.text)
    if manual == 'MER2-2000-19U3C(FCE22010010).XML':
        protocol = "u3v"
    elif 'Mark' in manual:
        protocol = "gvcp"
    begin, finished, begin_gvsp, finished_gvsp, simple_comands = None, None, None, None, None
    counter, counter_gvsp = 0, 0
    for i in dumps:
        res = ''
        value = None
        try:
            timestamp_time = float(i['_source']["layers"]["frame"]['frame.time_relative'])
        except:
            timestamp_time = 0
        if i['_source']["layers"].get("udp", False) and not i['_source']["layers"].get(protocol, False) and not \
                i['_source']["layers"].get("gvsp", False):
            if not begin:
                begin = timestamp_time
            finished = timestamp_time
            counter += 1
        elif i['_source']["layers"].get("gvsp", False):
            if not begin_gvsp:
                begin_gvsp = timestamp_time
            finished_gvsp = timestamp_time
            counter_gvsp += 1
        elif i['_source']["layers"].get(protocol, False):
            for j in i['_source']["layers"][protocol].keys():
                if "Command" in j or 'Acknowledge' in j:
                    if i['_source']["layers"][protocol][j].get("gvcp.bootstrap.custom.register.write", False):
                        res = i['_source']["layers"][protocol][j]["gvcp.bootstrap.custom.register.write"]
                    elif i['_source']["layers"][protocol][j].get("gvcp.bootstrap.custom.register.read", False):
                        res = i['_source']["layers"][protocol][j]["gvcp.bootstrap.custom.register.read"]
                    elif i['_source']["layers"][protocol][j].get("gvcp.cmd.readreg.bootstrapregister", False):
                        res = i['_source']["layers"][protocol][j]["gvcp.cmd.readreg.bootstrapregister"]
                        if i['_source']["layers"][protocol][j].get("gvcp.bootstrap.control.switchoverenable") == '1':
                            value = 'OpenAccess'
                        elif i['_source']["layers"][protocol][j].get("gvcp.bootstrap.control.controlaccess") == "1":
                            value = 'ControlAccess'
                        elif i['_source']["layers"][protocol][j].get("gvcp.bootstrap.control.exclusiveaccess") == "1":
                            value = 'ExclusiveAccess'
                        else:
                            value=44
                    else:
                        timestamp_items = j
                        for key in i['_source']["layers"][protocol][j].keys():
                            if 'gvcp.bootstrap' in key:
                                timestamp_items = [j.split(':')[1], i['_source']["layers"][protocol][j][key]]

                    res = res[:2] + res[-4::].upper()
                    text_reg = './/*[{http://www.genicam.org/GenApi/Version_1_0}Address="%s"]' % res
                    result_reg = tree.find(text_reg)
                    if result_reg:
                        text = './/*[{http://www.genicam.org/GenApi/Version_1_0}Integer]/*[@Name="%s"]' % result_reg.get(
                            "Name")[0:-3]
                        result = tree.find(text)
                        if result:
                            if 'WRITE' in j.split(':')[1]:
                                value = i['_source']["layers"]["gvcp"][j].get(
                                    "gvcp.bootstrap.custom.register.write_tree")
                                value = value['gvcp.bootstrap.custom.register.value']
                            elif 'READ' in j.split(':')[1]:
                                value = i['_source']["layers"]["gvcp"][j].get(
                                    "gvcp.bootstrap.custom.register.read_value")
                            command_dict[result.get("Name")] = {x.tag.split('}')[1]: x.text for x in tree.find(text)}
                            timestamp_items = [j.split(':')[1],{"address":res},
                                               {"value": int(value.split('x')[1].upper(), 16) if value else None},
                                               {result.get("Name"): command_dict[result.get("Name")].get('Description')}
                                               ]
                            simple_comands=[j.split(':')[1],result.get("Name"),{"address":res},
                                               {"value": int(value.split('x')[1].upper(), 16) if value else None}]
                            if simple_comands:
                                simple_comand_dict[timestamp_time] = simple_comands
                                simple_comands = None

                    else:
                        for key in i['_source']["layers"][protocol][j].keys():
                            if 'gvcp.bootstrap' in key:
                                timestamp_items = {
                                    j.split(':')[1]: {i['_source']["layers"][protocol][j][key]}}
                elif 'scd' in j or 'ccd' in j:
                    res = i['_source']["layers"][protocol][j].get('u3v.gencp.custom_addr', None)
                    if res:
                        res = res[:2] + res[-8::].upper()
                    elif i['_source']["layers"][protocol][j].get('u3v.gencp.address', None):
                        res = i['_source']["layers"][protocol][j].get('u3v.gencp.address', None)
                        res = res[:2] + res[-8::].upper()
                    result_reg = tree.find('.//*[{http://www.genicam.org/GenApi/Version_1_1}Address="%s"]' % res)
                    if not result_reg:
                        for f in formula:
                            if str(res) in f:
                                result_reg = tree.find(
                                    './/*[{http://www.genicam.org/GenApi/Version_1_1}Formula="%s"]' % f)
                                formula_res = f
                                break

                    if result_reg:
                        text = './/*[{http://www.genicam.org/GenApi/Version_1_1}Integer]/*[@Name="%s"]' % result_reg.get(
                            "Name")
                        if tree.find(text):
                            result = tree.find(text)
                        else:
                            result = tree.find(
                                './/*[{http://www.genicam.org/GenApi/Version_1_1}StructReg]//*[@Comment="%s"]' % result_reg.get(
                                    "Name"))

                        if result:
                            value = i['_source']["layers"][protocol][j].get("u3v.gencp.custom_data", None)
                            command_dict[result.get("Name")] = {x.tag.split('}')[1]: x.text for x in
                                                                tree.find(text)}
                            if value:
                                string = ''
                                value = int(string.join(value.split(':')[::-1]), 16)
                                timestamp_items = [j,
                                                   {"value": value},
                                                   {result.get("Name"): command_dict[result.get("Name")]}
                                                   ]
                                simple_comands = ['read' if "read" in j else 'write', result.get("Name"), {"value": value},
                                                  command_dict[result.get("Name")].get('Description') if command_dict[
                                                      result.get("Name")].get('Description') else None, {"address":res}]
                            else:
                                if formula_res:
                                    timestamp_items = [j,
                                                       result.get("Name"),
                                                       {'formula': formula_res}
                                                       ]
                                    simple_comands = ['read' if "read" in j else 'write', result.get("Name"),{"address":res},
                                                      formula_res,]
                                else:
                                    timestamp_items = [j,
                                                       result.get("Name")
                                                       ]
                                    simple_comands = ['read' if "read" in j else 'write', result.get("Name"),{"address":res}]


                    else:
                        timestamp_items = [j, i['_source']["layers"][protocol][j]]
                        # timestamp_items = None
                        simple_comands = [j, i['_source']["layers"][protocol][j]]
                elif 'stream_leader' in j:
                    timestamp_items = i['_source']["layers"][protocol][j]
                    simple_comands = i['_source']["layers"][protocol][j]

                else:
                    timestamp_items = j
                    simple_comands = i['_source']["layers"][protocol][j]
                if begin and finished:
                    if begin == finished:
                        timestamp_dict[finished] = 'UDP'
                    else:
                        timestamp_dict[begin] = 'UDP_BEGIN'
                        timestamp_dict[finished] = {"UDP_FINISHED": counter}
                if begin_gvsp and finished_gvsp:
                    if begin_gvsp == finished_gvsp:
                        timestamp_dict[finished_gvsp] = 'GVSP'
                    else:
                        timestamp_dict[begin_gvsp] = 'GVSP_BEGIN'
                        timestamp_dict[finished_gvsp] = {"GVSP_FINISHED": counter_gvsp}
                begin, finished, begin_gvsp, finished_gvsp, formula_res, result_reg,res = None, None, None, None, None, None, None
                counter, counter_gvsp = 0, 0

                timestamp_dict[timestamp_time] = timestamp_items
                if simple_comands:
                    simple_comand_dict[timestamp_time] = simple_comands
        else:
            timestamp_dict[timestamp_time] = "USB"

    with open(args.dump[0:-5] + '_command.txt', 'w') as file:
        for k in sorted(timestamp_dict.keys()):
            string = ""
            for j in timestamp_dict[k]:
                if j:
                    string += str(j) + ' '
            file.write(string + '\n')
    with open(args.dump[0:-5] + '_simple_command.txt', 'w') as file:

        for k in sorted(simple_comand_dict.keys()):
            string = ""
            for j in simple_comand_dict[k]:
                if j:
                    string += str(j) + ' '
            file.write(string + '\n')
    with open(args.dump[0:-5] + '_timestamp.txt', 'w') as file:
        for k in sorted(timestamp_dict.keys()):
            file.write(str(k) + ' ' + str(timestamp_dict[k]) + '\n')
    print("Finished")


parser(dumps, tree, args.manual)
