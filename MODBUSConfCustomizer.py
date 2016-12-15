import sys
import os
import xml.etree.ElementTree
import re
import json

config = {"SRC": "<<place a path for source file here>>",
          "DST": "<<place a path for destination file here>>",
          "CMD": {"CMD_NAME": "<<Command name>>",
                  "PARAM_NAME1": "<<Command parameter 1 value>>",
                  "PARAM_NAME2": "<<Command parameter 2 value>>"
                  }
          }


def read_cmd():
    if len(sys.argv) < 2:
        print("Error: not enough parameters.")
        exit()

    if not os.path.exists(sys.argv[1]):
        print("Error: settings file does not exist")
        exit()

    return sys.argv[1]


def read_config(file_path):
    global config
    with open(file_path, "r") as config_file:
        config = json.load(fp=config_file)
    return


def process_xml():
    tree = xml.etree.ElementTree.parse(config["SRC"])
    read_element(tree.getroot())

    if config.get("CMD") is not None and config["CMD"].get("RESULT"):
        print("Command {0} resulted with {1}".format(config["CMD"]["NAME"], config["CMD"]["RESULT"]))

    if config.get("DST") is not None:
        tree.write(config["DST"], encoding="utf-8", xml_declaration=True)


def read_element(element):
    check_command(element)
    for child in element:
        read_element(child)


def check_command(element):
    command = config["CMD"]
    if command["NAME"] == "CountIf":
        count_if(command, element)
    if command["NAME"] == "ChangeIf":
        change_if(command, element)
    pass


def change_if(command, element):
    pass


def count_if(command, element):
    if command.get("RESULT") is None:
        command["RESULT"] = 0

    if command.get("AND") is not None:
        block = command["AND"]
        if block.get("TAG") is not None and element.tag != block["TAG"]:
            return
        if block.get("ATTR") is not None:
            attributes = block["ATTR"]
            for attr in attributes:
                if element.attrib.get(attr) is None:
                    return
            if attributes.get("Value") is not None:
                if False == check_value(element, attributes["Value"]):
                    return

        command["RESULT"] += 1
    if command.get("OR") is not None:
        block = command["OR"]
        pass
    pass


def check_value(element, value_requirements):
    if element.attrib.get("Id") is None or element.attrib.get("Type") is None:
        return False  # invalid property format
    if element.attrib["Id"] == "5000" and element.attrib["Type"] == "String":
        return check_address(element.attrib["Value"], value_requirements)
    return False


def check_address(address, address_requirements):
    parsed_address = parse_address(address)
    for item in address_requirements:
        if parsed_address.get(item) is None or parsed_address[item] != address_requirements[item]:
            return False
    return True


def parse_address(address):
    result = dict()
    re_param = re.compile("\w+=\((\w+[ -]?)+\)")
    find_result = re.finditer(re_param, address)
    for match in find_result:
        address_item = match.group()
        address_item = address_item.replace("(", "")
        address_item = address_item.replace(")", "")
        res = address_item.split("=")
        result[res[0]] = res[1]
    return result


def main():
#    with open("D:\\config.json", "w") as json_cfg:
#        json.dump(config, json_cfg, indent=4, separators=(',', ': '))

    read_config(read_cmd())
    process_xml()

main()
exit()
