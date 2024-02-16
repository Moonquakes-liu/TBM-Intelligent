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
import time
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


def Update(Object):
    Object.show_info(message=f'Check environment...', Type='info')
    Object.percentage(value=0)
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = configparser.ConfigParser()
    parser.read(os.path.join(root_path, 'md5'), encoding='utf-8')  # 读取文件
    version = parser.get('program', 'version')
    backup_path = os.path.join(root_path, 'backup')
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    backup_path_temp = os.path.join(root_path, 'backup', 'temp')
    name = f'backup v{version} {datetime.today().strftime("%Y-%m-%d")}.bak'
    with zipfile.ZipFile(os.path.join(root_path, 'temp', 'ROM', 'Resources.zip'), mode='r') as zips:
        files_num = len(zips.namelist()) + 1
        zips.extract('md5', os.path.join(root_path, 'temp', 'ROM'))
        parser = configparser.ConfigParser()
        parser.read(os.path.join(root_path, 'temp', 'ROM', 'md5'), encoding='utf-8')  # 读取文件
        Object.show_info(message=f'Check environment successful!', Type='info')
        Object.percentage(value=5)
        for index, file in enumerate(zips.infolist()):
            target_file = os.path.join(root_path, file.filename)
            # noinspection PyBroadException
            try:
                for section in parser.sections():
                    if (section != 'program') and (parser.get(section, 'file') == os.path.basename(target_file)):
                        raw_md5 = parser.get(section, 'md5')
                        check_md5 = calculate_file_checksum(target_file)
                        if raw_md5 != check_md5:
                            Object.show_info(message=f'File < {target_file} > verification failure!', Type='error')
                            Object.percentage(value=5 + index * 90 / files_num + 90 / files_num / 2)
                            continue
            except Exception:
                Object.show_info(message=f'File < {target_file} > verification failure!', Type='error')
                Object.percentage(value=5 + index * 90 / files_num + 90 / files_num / 2)
                continue
            Object.show_info(message=f'Checking file < {target_file} successful!', Type='info')
            Object.percentage(value=5 + index * 90 / files_num)
            # noinspection PyBroadException
            try:
                if os.path.exists(target_file):
                    target_path = os.path.join(backup_path_temp, file.filename)
                    if not os.path.exists(os.path.dirname(target_path)):
                        os.makedirs(os.path.dirname(target_path))
                    shutil.copy(target_file, target_path)
                    with zipfile.ZipFile(os.path.join(backup_path, name), 'w') as backup_zip:
                        for root, dirs, files in os.walk(backup_path_temp):  # 遍历文件夹下的所有文件
                            for file in files:
                                backup_zip.write(os.path.join(root, file),
                                                 arcname=os.path.relpath(os.path.join(root, file), backup_path_temp))
                    Object.show_info(message=f'Backup file < {target_file} > successful!', Type='info')
                    Object.percentage(value=5 + index * 90 / files_num + 90 / files_num / 3)
                    #os.remove(target_file)
                    # rar_ref.extract(member.filename, current_path)
                    Object.show_info(message=f'Update file < {target_file} > successful!', Type='info')
                    Object.percentage(value=5 + index * 90 / files_num + 90 / files_num / 3)
            except Exception:
                Object.show_info(message=f'Update file < {target_file} > failure!', Type='error')
            time.sleep(0.5)
        if os.path.exists(backup_path_temp):
            shutil.rmtree(backup_path_temp)
        Object.show_info(message=f'Clean up left files successful！', Type='info')
        Object.percentage(value=100)
        Object.finish(message='升级完成！')
