import sys
import os
import xml.etree.ElementTree
import re
import json


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
    if config.get("CMD") is None:
        print("No commands provided. Nothing to execute.")
        return

    # executing only independent commands
    commands = config["CMD"]

    execute_commands(tree.getroot(), commands)

    if config.get("CMD") is not None:
        for command in config["CMD"]:
            print("Command {0}".format(command["TYPE"]))
            if command.get("DESCR") is not None:
                print("\tDescription: \"{0}\"".format(command["DESCR"]))
            print("\tResulted with {0}".format(command["RESULT"]))

    if config.get("DST") is not None:
        tree.write(config["DST"], encoding="utf-8", xml_declaration=True)


def execute_commands(element, commands):
    for cmd in commands:
        curr_cmd = commands[cmd]
        if curr_cmd.get("DEPENDS") is None:
            if curr_cmd.get("RESULT") is None:
                print("Processing \"{0}\" element with \"{1}\" command.".format(element.tag, commands[cmd]["TYPE"]))
                process_element_with_command(element, commands[cmd])
        elif curr_cmd.get("RESULT") is None:
            dependent_not_executed_commands = dict()
            for dep_cmd in curr_cmd["DEPENDS"]:
                if config["CMD"][dep_cmd].get("RESULT") is None:
                    dependent_not_executed_commands[dep_cmd] = commands[dep_cmd]

            execute_commands(element, dependent_not_executed_commands)

            print("Processing \"{0}\" element with \"{1}\" command.".format(element.tag, commands[cmd]["TYPE"]))
            process_element_with_command(element, commands[cmd])


def process_element_with_command(element, command_cfg):
    execute_command_on_element(command_cfg, element)
    for child in element:
        process_element_with_command(child, command_cfg)


def execute_command_on_element(command_cfg, element):
    if command_cfg["TYPE"] == "CountIf":
        exec_count_if_on_element(command_cfg, element)
    if command_cfg["TYPE"] == "ChangeIf":
        exec_change_if_on_element(command_cfg, element)


def exec_change_if_on_element(command, element):
    if command.get("RESULT") is None:
        command["RESULT"] = 0

    if command.get("CHANGES") is None:
        raise Exception("Invalid structure of ChangeIf command.")

    numbers = list(command["CHANGES"].keys())
    numbers.sort()
    for number in numbers:
        if command.get("AND") is not None and type(command.get("AND")) == dict:
            if process_and(command.get("AND"), element):
                if change_element(command["CHANGES"][number], element):
                    command["RESULT"] += 1


def change_element(change, element):
    if change.get("TARGET") is None or change.get("OPERATIONS") is None or change.get("ELEMENTS_TO_APPLY") is None:
        return False

    if change["TARGET"].get("ATTRIBUTE") is not None:
        if element.attrib.get(change["TARGET"]["ATTRIBUTE"]) is None:
            return False
        return change_attribute(change, element)
    if change["TARGET"].get("TAG") is not None:
        return change_tag(change, element)
    return False


def change_attribute(change, element):
    attribute_name = change["TARGET"]["ATTRIBUTE"]
    operations = change["OPERATIONS"]

    # непонятно надо ли сортировать ключи или же словарь уже упорядочен по индексу?????
    operation_keys = list(operations.keys())
    operation_keys.sort()
    for key in operation_keys:
        operation = operations[key]
        if operation.get("MODE") is None:
            raise Exception("Invalid OPERATION format.")
        if operation["MODE"] == "ERASE_SYMBOLS":
            if operation.get("ORIGIN") is None or operation.get("COUNT") is None:
                raise Exception("Invalid ERASE_SYMBOLS OPERATION format.")
            if operation["ORIGIN"] == "END":
                element.attrib[attribute_name] = element.attrib[attribute_name][0: len(element.attrib[attribute_name]) - operation["COUNT"]]
        if operation["MODE"] == "APPEND":
            if operation.get("DATA") is None:
                raise Exception("Invalid APPEND OPERATION format.")
            element.attrib[attribute_name] += operation["DATA"]

    return True


def change_tag(change, element):
    raise Exception("TAG changing is not implemented")


def exec_count_if_on_element(command, element):
    if command.get("RESULT") is None:
        command["RESULT"] = 0

    if command.get("AND") is not None:
        block = command["AND"]
        if type(block) == dict:
            if not process_and(block, element):
                return
        else:
            return
    elif command.get("OR") is not None:
        block = command["OR"]
        if type(block) == dict:
            if not process_or(block, element):
                return
        else:
            return
    else:
        return

    command["RESULT"] += 1


def check_value(element, value_requirements):
    if element.attrib.get("Id") is None or element.attrib.get("Type") is None:
        return False  # invalid property format
    if element.attrib["Id"] == "5000" and element.attrib["Type"] == "String":
        return check_address(element.attrib["Value"], value_requirements)
    return False


def check_address(address, address_requirements):
    parsed_address = parse_address(address)
    for item in address_requirements:
        if parsed_address.get(item) is not None:
            item_val = address_requirements[item]
            if type(item_val) == str:
                if parsed_address[item] != item_val:
                    return False
            elif not process_value(parsed_address[item], item_val):
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


def process_and(and_block, element):
    if and_block.get("TAG") is not None:
        if type(and_block["TAG"]) == str:
            if element.tag != and_block["TAG"]:
                return False
        elif not process_value(element.tag, and_block["TAG"]):
            return False

    if and_block.get("ATTR") is not None:
        attributes = and_block["ATTR"]
        for attr in attributes:
            if element.attrib.get(attr) is None:
                return False
            if type(attributes[attr]) == str:
                if attributes[attr] != element.attrib[attr]:
                    return False
            elif not process_value(element.attrib[attr], attributes[attr]):
                return False

        if attributes.get("Value") is not None:
            if not check_value(element, attributes["Value"]):
                return False
    return True


def process_or(or_block, element):
    raise Exception("The OR statement is not implemented yet!")


def process_value(value, operation_and_values):
    if type(operation_and_values) != dict:
        return True  # not applicable
    if len(operation_and_values) != 1:
        return True  # not applicable

    keys = list(operation_and_values.keys())
    keys.sort()
    if not("EQ" in keys or "NEQ" in keys or "LT" in keys or "GT" in keys or "GTEQ" in keys or "LTEQ" in keys):
        return True  # not applicable

    if "EQ" in keys:
        for val in operation_and_values["EQ"]:
            if val == value:
                return True
    elif "NEQ" in keys:
        for val in operation_and_values["EQ"]:
            if val == value:
                return False
        return True
    elif "LT" in keys:
        print("Error: operation LT(less then) does not implemented for values.")
    elif "GT" in keys:
        print("Error: operation GT(greater then) does not implemented for values.")
    elif "GTEQ" in keys:
        print("Error: operation GTEQ(greater then or equals) does not implemented for values.")
    elif "LTEQ" in keys:
        print("Error: operation LTEQ(less then or equals) does not implemented for values.")

    return False


def main():
    read_config(read_cmd())
    process_xml()

main()
exit()
