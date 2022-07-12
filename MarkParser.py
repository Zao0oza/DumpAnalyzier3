# -*- coding: utf-8 -*-

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
    begin, finished, begin_gvsp, finished_gvsp = None, None, None, None
    counter, counter_gvsp = 0, 0
    for i in dumps:
        res = ''
        value = None
        try:
            timestamp_time = float(i['_source']["layers"]["frame"]['frame.time_relative'])
        except:
            timestamp_time = 0
        if i['_source']["layers"].get("udp", False) and not i['_source']["layers"].get("gvcp", False) and not \
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
        elif i['_source']["layers"].get("gvcp", False):
            for j in i['_source']["layers"]["gvcp"].keys():
                if "Command" or 'Acknowledge' in j:
                    if i['_source']["layers"]["gvcp"][j].get("gvcp.bootstrap.custom.register.write", False):
                        res = i['_source']["layers"]["gvcp"][j]["gvcp.bootstrap.custom.register.write"]
                    elif i['_source']["layers"]["gvcp"][j].get("gvcp.bootstrap.custom.register.read", False):
                        res = i['_source']["layers"]["gvcp"][j]["gvcp.bootstrap.custom.register.read"]
                    else:
                        timestamp_items = j.split(':')[1]
                        for key in i['_source']["layers"]["gvcp"][j].keys():
                            if 'gvcp.bootstrap' in key:
                                timestamp_items = [j.split(':')[1], i['_source']["layers"]["gvcp"][j][key]]
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
                            timestamp_items = [j.split(':')[1],
                                               {"value": int(value.split('x')[1].upper(), 16) if value else None},
                                               {result.get("Name"): command_dict[result.get("Name")].get('Description')}
                                               ]

                    else:
                        for key in i['_source']["layers"]["gvcp"][j].keys():
                            if 'gvcp.bootstrap' in key:
                                timestamp_items = {
                                    j.split(':')[1]: {i['_source']["layers"]["gvcp"][j][key]}}
                else:
                    timestamp_items = j.split(':')[1]
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
                begin, finished, begin_gvsp, finished_gvsp = None, None, None, None
                counter, counter_gvsp = 0, 0
                timestamp_dict[timestamp_time] = timestamp_items

    with open(args.dump[0:-5] + '_command.txt', 'w') as file:
        for k in sorted(command_dict.keys()):
            file.write(str(k) + ' ' + str(command_dict[k]) + '\n')
    with open(args.dump[0:-5] + '_timestamp.txt', 'w') as file:
        for k in sorted(timestamp_dict.keys()):
            file.write(str(k) + ' ' + str(timestamp_dict[k]) + '\n')
    print("Finished")

parser(dumps, tree)
