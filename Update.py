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

import configparser
import os
import shutil
import sys
import zipfile

backup_switch = False
resource = {'TBM_Main.py': 'TBM_Main.py',
            'TBM_CYCLE.py': 'TBM_CYCLE.py',
            'TBM_CLASS.py': 'TBM_CLASS.py',
            'TBM_SPLIT.py': 'TBM_SPLIT.py',
            'TBM_REPORT.py': 'TBM_REPORT.py',
            'TBM.py': 'TBM.py',
            'TBM Pre-Process.py': 'TBM Pre-Process.py',
            'config.ini': 'Resource\\config\\config.ini',
            'STSONG.TTF': 'Resource\\fonts\\STSONG.TTF',
            '程序说明.docx': 'Resource\\helps\\程序说明.docx',
            '程序说明.pdf': 'Resource\\helps\\程序说明.pdf',
            'cover.png': 'Resource\\images\\cover.png'}


def replace_info(**Var):
    name = Var['file_path'].split('\\')[-1]
    backup_file(file_path=Var['file_path'], now_vision=Var['now_vision'])
    with open(Var['file_path'], 'r', encoding="utf-8") as F:
        lines = F.readlines()
    local = 0
    with open(Var['file_path'], 'w', encoding="utf-8") as f_w:
        for num, line in enumerate(lines):
            if num == 5:
                line = line[:11] + Var['new_modify'] + line[30:]
            if Var['target_message'] in line:
                line = line.replace(Var['target_message'], Var['new_message'])
                print('-> \033[0;33mReplace information from %s Successfully! Location: %s lines\033[0m'
                      % (name, local + 1))
            local += 1
            f_w.write(line)


def delete_info(**Var):
    name = Var['file_path'].split('\\')[-1]
    backup_file(file_path=Var['file_path'], now_vision=Var['now_vision'])
    with open(Var['file_path'], 'r', encoding="utf-8") as f:
        datafile = f.readlines()
    local = 0
    for line in datafile:
        if Var['target_message'] in line:
            print('-> \033[0;33mDelete information from %s Successfully! Location: %s lines\033[0m' % (name, local + 1))
            break
        local += 1
    with open(Var['file_path'], 'r', encoding="utf-8") as old_file:
        with open(Var['file_path'], 'r+', encoding="utf-8") as new_file:
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
    with open(Var['file_path'], 'r', encoding="utf-8") as F:
        lines = F.readlines()
    with open(Var['file_path'], 'w', encoding="utf-8") as f_w:
        for num, line in enumerate(lines):
            if num == 5:
                line = line[:11] + Var['new_modify'] + line[30:]
            f_w.write(line)


def add_info(**Var):
    name = Var['file_path'].split('\\')[-1]
    backup_file(file_path=Var['file_path'], now_vision=Var['now_vision'])
    with open(Var['file_path'], 'r', encoding="utf-8") as f:
        datafile = f.readlines()
    local = 0
    for line in datafile:
        if Var['target_message'] in line:
            break
        local += 1
    with open(Var['file_path'], 'r', encoding="utf-8") as f:
        lines = f.readlines()
        lines.insert(local + 1, Var['new_message'] + '\n')
        s = ''.join(lines)
    with open(Var['file_path'], 'w', encoding="utf-8") as f:
        f.write(s)
    with open(Var['file_path'], 'r', encoding="utf-8") as F:
        lines = F.readlines()
    with open(Var['file_path'], 'w', encoding="utf-8") as f_w:
        for num, line in enumerate(lines):
            if num == 5:
                line = line[:11] + Var['new_modify'] + line[30:]
            f_w.write(line)
    print('-> \033[0;33mAdd information to %s Successfully! Location: %s lines\033[0m' % (name, local + 2))


def update_file(**Var):
    backup_file(file_path=Var['file_path'], now_vision=Var['now_vision'])
    name = Var['file_path'].split('\\')[-1]
    file = os.path.abspath(os.path.join(Var['file_path'], os.path.pardir))
    now_file = Var['file_path']  # 当前文件夹路径
    new_file = os.path.join(file, '__Update__', '%s' % name)
    shutil.copyfile(new_file, now_file)  # 更新新文件
    print(
        '-> \033[0;33mUpdate %s Successfully! Version: %s ->-> %s\033[0m' % (
        name, Var['now_vision'], Var['new_vision']))


def add_file(**Var):
    name = Var['file_path'].split('\\')[-1]
    file = os.path.abspath(os.path.join(Var['file_path'], os.path.pardir))
    now_file = Var['file_path']  # 当前文件夹路径
    new_file = os.path.join(file, '__Update__', '%s' % name)
    shutil.copyfile(new_file, now_file)  # 更新新文件
    print('-> \033[0;33mAdded %s successfully! Version: %s\033[0m' % (name, Var['new_vision']))


def delete_file(**Var):
    backup_file(file_path=Var['file_path'], now_vision=Var['now_vision'])
    name = Var['file_path'].split('\\')[-1]
    now_file = Var['file_path']  # 当前文件夹路径
    os.remove(now_file)
    print('-> \033[0;33mDelete %s successfully! Version: %s\033[0m' % (name, Var['now_vision']))


def backup_file(**Var):
    global backup_switch
    backup_switch = True
    name = os.path.splitext(os.path.basename(Var['file_path']))[0] + ' %s.bak' % Var['now_vision']
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
    now_file = Var['file_path']  # 当前文件夹路径
    backups_file = os.path.join(root_path, 'Resource', 'backups', name)
    if not os.path.exists(os.path.abspath(os.path.join(backups_file, os.path.pardir))):
        os.makedirs(os.path.abspath(os.path.join(backups_file, os.path.pardir)))  # 创建文件夹
    shutil.copyfile(now_file, backups_file)  # 备份旧文件


def Unpack_file(target_path, file):
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
    zip_file = os.path.join(root_path, '__Update__', 'Resource.zip')
    if os.path.exists(zip_file):
        if os.path.exists(os.path.join(root_path, resource[file])):
            backup_file(file_path=os.path.join(root_path, resource[file]),
                        now_vision='%s' % os.path.splitext(file)[-1])
            os.remove(os.path.join(root_path, resource[file]))
        ZF = zipfile.ZipFile(zip_file, mode='r')
        for num, name in enumerate(ZF.namelist()):
            new_name = name.encode('cp437').decode('gbk')  # 解决中文乱码问题
            if os.path.basename(new_name) == file:
                ZF.extract(name, target_path)  # 解压到zip目录文件下
                os.rename(os.path.join(target_path, name), os.path.join(target_path, new_name))
                print('-> \033[0;33mUpdate %s Successfully!\033[0m' % file)


def Update():
    now_version, now_modify, new_version, new_modify, update_info = {}, {}, {}, {}, []  # 当前版本信息
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
    update_path = os.path.join(root_path, '__Update__')
    for version, modify, Dir in zip([now_version, new_version], [now_modify, new_modify], [root_path, update_path]):
        for py_file in os.listdir(Dir):  # 获取当前版本信息
            if os.path.splitext(py_file)[-1] == '.py':
                file_path = os.path.join(Dir, py_file)
                with open(file_path, 'r', encoding="utf-8") as F:
                    for lines in F.readlines()[3:10]:
                        if 'Version' in lines:
                            version.update({py_file: lines[14:19]})
                        if 'Date' in lines:
                            modify.update({py_file: lines[11:30]})
    parser = configparser.ConfigParser()
    parser.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Update_INF.ini'), encoding='utf-8')  # 读取文件
    for info in parser.sections():
        Operate_File, Operate_Type = parser[info]['OPERATE-FILE'], parser[info]['OPERATE-TYPE']
        Now_Version, New_Version = parser[info]['NOW-VERSION'], parser[info]['NEW-VERSION']
        Now_Modify, New_Modify = parser[info]['NOW-MODIFY'], parser[info]['NEW-MODIFY']
        Target_Messages, New_Messages = parser[info]['TARGET-MESSAGES'], parser[info]['NEW-MESSAGES']
        path = os.path.join(root_path, Operate_File)
        try:
            if now_modify[Operate_File] < Now_Modify or now_version[Operate_File] < Now_Version:
                Now_Version, Now_Modify = now_version[Operate_File], now_modify[Operate_File]
        except KeyError:
            pass
        try:
            if Operate_Type == 'update-file':
                if new_version[Operate_File] == New_Version:
                    if os.path.exists(Operate_File):
                        if now_version[Operate_File] < New_Version:
                            update_file(file_path=path, now_vision=Now_Version, new_vision=New_Version,
                                        now_modify=Now_Modify)
                            update_info += ['%-20s: %s' % (Operate_File, info) for
                                            info in parser[info]['INFORMATION'].split('；')]
                    else:
                        add_file(file_path=path, new_vision=New_Version)
                        update_info += ['%-20s: %s' % (Operate_File, info) for
                                        info in parser[info]['INFORMATION'].split('；')]
            elif Operate_Type == 'replace-file':
                root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
                zip_file = os.path.join(root_path, '__Update__', 'Resource.zip')
                if os.path.exists(zip_file):
                    Unpack_file(target_path=root_path, file=Operate_File)
                    update_info += ['%-20s: %s' % (Operate_File, info) for
                                    info in parser[info]['INFORMATION'].split('；')]
            elif Operate_Type == 'delete-file':
                if os.path.exists(path):
                    delete_file(file_path=path, now_vision=Now_Version, now_modify=Now_Modify)
                    update_info += ['%-20s: %s' % (Operate_File, info) for
                                    info in parser[info]['INFORMATION'].split('；')]
            elif Operate_Type == 'add-info':
                if now_modify[Operate_File] < New_Modify:
                    add_info(file_path=path, target_message=Target_Messages, new_message=New_Messages,
                             now_vision=Now_Version, now_modify=Now_Modify, new_modify=New_Modify)
                    update_info += ['%-20s: %s' % (Operate_File, info) for
                                    info in parser[info]['INFORMATION'].split('；')]
            elif Operate_Type == 'delete-info':
                if now_modify[Operate_File] < New_Modify:
                    delete_info(file_path=path, target_message=Target_Messages, new_message=New_Messages,
                                now_vision=Now_Version, now_modify=Now_Modify, new_modify=New_Modify)
                    update_info += ['%-20s: %s' % (Operate_File, info) for
                                    info in parser[info]['INFORMATION'].split('；')]
            elif Operate_Type == 'replace-info':
                if now_modify[Operate_File] < New_Modify:
                    replace_info(file_path=path, target_message=Target_Messages, new_message=New_Messages,
                                 now_vision=Now_Version, now_modify=Now_Modify, new_modify=New_Modify)
                    update_info += ['%-20s: %s' % (Operate_File, info) for
                                    info in parser[info]['INFORMATION'].split('；')]
        except KeyError:
            pass
    if update_info:
        print('-> \033[0;33m更新内容:\033[0m')
        for i, inf in enumerate(update_info):
            print('   \033[0;33m%-3d  %s\033[0m' % (i + 1, inf))
    if backup_switch:
        print('-> \033[0;33mHistory Program backed up to folder[...\\Resource\\backups\\], '
              'You can recovery it here!\033[0m')
    if update_info:
        print('-> \033[0;32mUpdate complete, Please Restart the program!\033[0m')
        shutil.rmtree(os.path.join(root_path, '__Update__'))  # 更新完成，删除相关文件记录
        sys.exit()


Update()
