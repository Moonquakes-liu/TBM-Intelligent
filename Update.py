# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: Update_TBM for python                                          *
# * Version:  1.0.0                                                          *
# * Date:     2022-10-20 20:00:00                                            *
# * Last update: 2022-10-19 00:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os
import shutil
import sys
import zipfile


new_version = False


def replace(file_path, tar_mess, replace_mess):
    with open(file_path, 'r', encoding="utf-8") as F:
        lines = F.readlines()
    with open(file_path, 'w', encoding="utf-8") as f_w:
        for line in lines:
            if tar_mess in line:
                line = line.replace(tar_mess, replace_mess)
            f_w.write(line)


def delete(file_path, tar_mess, del_mess):
    with open(file_path, 'r', encoding="utf-8") as f:
        datafile = f.readlines()
    local = 0
    for line in datafile:
        if tar_mess in line:
            break
        local += 1
    with open(file_path, 'r', encoding="utf-8") as old_file:
        with open(file_path, 'r+', encoding="utf-8") as new_file:
            current_line = 0
            while current_line < local:
                old_file.readline()
                current_line += 1
            seek_point = old_file.tell()
            new_file.seek(seek_point, 0)
            old_file.readline()
            next_line = old_file.readline()
            while next_line:
                new_file.write(next_line)
                next_line = old_file.readline()
            new_file.truncate()


def add(file_path, tar_mess, add_mess):
    with open(file_path, 'r', encoding="utf-8") as f:
        datafile = f.readlines()
    local = 0
    for line in datafile:
        if tar_mess in line:
            break
        local += 1
    with open(file_path, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        lines.insert(local + 1, add_mess + '\n')
        s = ''.join(lines)
    with open(file_path, 'w', encoding="utf-8") as f:
        f.write(s)


def backup_file(name, old_vision):
    current_path = os.path.dirname(os.path.abspath(__file__))[:-10]  # ?????????????????????
    old_program_path = current_path + '\\Old-Programs'  # ?????????????????????
    old_file_name = os.path.join(old_program_path, '%s version%s.py' % (name[:-3], old_vision))  # ???????????????????????????
    if not os.path.exists(old_program_path):
        os.makedirs(old_program_path)  # ???????????????
    shutil.copyfile(os.path.join(current_path, name), old_file_name)  # ???????????????


def update_file(name, now_vision, new_vision):
    # zipfile.ZipFile(os.path.join(path, 'main.zip'), 'r').extract('TBM-Intelligent-main/%s' % name, path)
    current_path = os.path.dirname(os.path.abspath(__file__))[:-10]  # ?????????????????????
    new_file_name = os.path.join(current_path, '__Update__', '%s' % name)  # ????????????????????????
    shutil.copyfile(new_file_name, os.path.join(current_path, name))  # ???????????????
    print(' ->->', '\033[0;33mUpdate %s Successfully! Version: %s ->-> %s\033[0m' % (name, now_vision, new_vision))


def add_file(name, new_vision, path):
    zipfile.ZipFile(os.path.join(path, 'main.zip'), 'r').extract('TBM-Intelligent-main/%s' % name, path)
    current_path = os.path.dirname(os.path.abspath(__file__))[:-8]  # ?????????????????????
    new_file_name = current_path + '\\__temp__\\TBM-Intelligent-main\\%s' % name  # ????????????????????????
    shutil.copyfile(new_file_name, os.path.join(current_path, name))  # ???????????????
    print(' ->->', '\033[0;33mAdded %s successfully! Version: %s\033[0m' % (name, new_vision))


def Update():
    global new_version
    # Temp_path = '__Update__\\'  # ????????????????????????
    # filepath = os.path.join(Temp_path, 'main.zip')
    # zipfile.ZipFile(filepath, 'r').extract('TBM-Intelligent-main/Update_INF', Temp_path)
    # current_path = os.path.dirname(os.path.abspath(__file__))  # ?????????????????????
    # new_file_name = current_path + '\\TBM-Intelligent-main\\Update_INF'  # ????????????????????????
    # shutil.copyfile(new_file_name, os.path.join(current_path, 'Update_INF'))  # ???????????????
    now_version, modify_time = {}, {}  # ??????????????????
    for py_file in os.listdir(os.path.dirname(os.path.abspath(__file__))[:-10]):  # ????????????????????????
        if '.py' in py_file:
            for lines in open(py_file, encoding='utf-8'):
                if 'Version' in lines:
                    now_version.update({py_file: lines[14:19]})
                    break
            for lines in open(py_file, encoding='utf-8'):
                if '# * Date:' in lines:
                    modify_time.update({py_file: lines[14:33]})
                    break
    f = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Update_INF'), encoding="utf-8")
    txt = []
    for Lines in f:
        txt.append(Lines.strip())
    for new_line in txt:
        new_line = str(new_line).split('->->')
        file_name = os.path.join(os.path.dirname(os.path.abspath(__file__))[:-8], new_line[1])
        if new_line[0] == 'add':
            if modify_time[new_line[1]] < new_line[2]:
                add(file_name, new_line[3], new_line[4])
                new_version = True
        elif new_line[0] == 'del':
            if modify_time[new_line[1]] < new_line[2]:
                delete(file_name, new_line[3], new_line[4])
                new_version = True
        elif new_line[0] == 'rep':
            if modify_time[new_line[1]] < new_line[2]:
                replace(file_name, new_line[3], new_line[4])
                new_version = True
        elif new_line[0] == 'rec':
            if new_line[1] in now_version:
                if now_version[new_line[1]] < new_line[2]:
                    backup_file(new_line[1], now_version[new_line[1]])
                    update_file(new_line[1], now_version[new_line[1]], new_line[2])
                    new_version = True
            else:
                add_file(new_line[1], new_line[2], Temp_path)
                new_version = True
        else:
            print('\033[0;31mUnable to check for updates!!!\033[0m')
    f.close()
    # shutil.rmtree(Temp_path)
    if new_version:
        print(' ->->',
              '\033[0;32mThe Raw program has been saved to "...\\Old-Programs", Please restart the program!!!\033[0m')
        sys.exit()


Update()
