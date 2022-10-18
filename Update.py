# -*- coding: utf-8 -*-
import os


def replace(name, tar_mess, replace_mess):
    file_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    with open(file_name, "r", encoding="utf-8") as F:
        lines = F.readlines()
    with open(file_name, "w", encoding="utf-8") as f_w:
        for line in lines:
            if tar_mess in line:
                line = line.replace(tar_mess, replace_mess)
            f_w.write(line)


def Update():
    f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'update_inf'), encoding="utf-8")
    txt = []
    for Lines in f:
        txt.append(Lines.strip())
    for new_line in txt:
        new_line = str(new_line)
        replace(new_line.split('->')[0], new_line.split('->')[1], new_line.split('->')[2])
