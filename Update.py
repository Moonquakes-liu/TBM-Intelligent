# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: Update_TBM for python                                          *
# * Version:  1.0.6                                                          *
# * Date:     2022-10-20 20:00:00                                            *
# * Last update: 2022-10-19 00:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import configparser
import os
import io
import shutil
import sys
import zipfile
import hashlib
from tkinter import messagebox, Tk
from datetime import datetime


def calculate_file_checksum(file, algorithm="md5"):
    ha_sher = hashlib.new(algorithm)  # 使用指定的哈希算法初始化哈希对象
    with open(file, 'rb') as f:  # 打开文件并逐块更新哈希对象
        for chunk in iter(lambda: f.read(4096), b''):  # 每次读取4KB数据
            ha_sher.update(chunk)
    check_sum = ha_sher.hexdigest()  # 获取最终的校验码
    return check_sum


def Update():
    # noinspection PyBroadException
    try:
        current_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(current_path, 'Programs', 'Windows.py'), 'r', encoding='utf-8') as file:
            lines = file.readlines()
            current_version = lines[4][14:19]
        backup_path = os.path.join(current_path, 'backup')
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        name = f'backup v{current_version} {datetime.today().strftime("%Y-%m-%d")}.bak'
        different_count = 0
        parser = configparser.ConfigParser()
        parser.read(os.path.join(current_path, 'temp', 'MD5'), encoding='GBK')  # 读取文件
        for model in parser.sections():
            if model == 'program':
                continue
            file = parser.get(model, 'file')
            check_md5 = calculate_file_checksum(os.path.join(current_path, 'temp', file))
            if check_md5 != parser.get(model, 'md5'):
                different_count += 1
        if different_count <= 0:
            files_to_add = []
            with zipfile.ZipFile(os.path.join(current_path, 'temp', 'Resources.zip'), mode='r') as rar_ref:
                for member in rar_ref.infolist():
                    target_file = os.path.join(current_path, member.filename)
                    if os.path.exists(target_file):
                        files_to_add.append(target_file)
                        with zipfile.ZipFile(os.path.join(backup_path, name), 'w') as zip_ref:
                            for file in files_to_add:
                                zip_ref.write(file, arcname=os.path.relpath(file, current_path))
                        os.remove(target_file)
                    rar_ref.extract(member.filename, current_path)
    except Exception as e:
        root = Tk()  # 创建一个 Tkinter 根窗口
        root.withdraw()  # 隐藏根窗口，只显示文件夹选择对话框
        messagebox.showwarning(title='警告', message=f'更新文件非法，更新失败！{e}')  # 消息提醒弹


Update()
