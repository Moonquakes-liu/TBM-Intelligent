#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_Main for python                                            *
# * Version:  2.0.0                                                          *
# * Date:     2022-10-20 20:00:00                                            *
# * Last update: 2022-10-16 00:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os
import shutil
import sys
import time
import urllib.request
import zipfile
import pandas as pd


def Check_Update():
    """用于检查文件更新， 请勿修改"""
    Temp_path, Network, update = '__temp__\\', True, False  # 临时文件存放位置，是否连接到网络
    New_File_URL = 'https://github.com/Moonquakes-liu/TBM-Intelligent/archive/refs/heads/'
    if not os.path.exists(Temp_path):
        os.mkdir(Temp_path)
    filepath = os.path.join(Temp_path, 'main.zip')
    try:
        urllib.request.urlretrieve(New_File_URL + 'main.zip', filepath)
    except urllib.error.URLError:
        print('\033[0;31mInternet connection failed, unable to check for updates!!!\033[0m')
        Network = False
    if Network:
        zipfile.ZipFile(filepath, 'r').extract('TBM-Intelligent-main/Update.py', Temp_path)
        current_path = os.path.dirname(os.path.abspath(__file__))  # 当前文件夹路径
        new_file_name = current_path + '\\__temp__\\TBM-Intelligent-main\\Update.py'  # 下载的新文件名称
        shutil.copyfile(new_file_name, os.path.join(current_path + '\\__temp__', 'Update.py'))  # 更新新文件
        from __temp__.Update import Update

        
# 在检查更新前建议先备份之前的py文件
Check_Update()  # 检查更新模块，请勿修改！！！


start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
print('\033[0;33m请将原始数据放在{ ...\\RawDataSet }下!!!\033[0m')
Root_Path = os.path.dirname(os.path.abspath(__file__))  # 文件存放根目录（可修改）
IN_Folder = ['RawDataSet']
Out_Folder = ['TBM_CYCLE-AllDataSet', 'TBM_CYCLE-KeyDataSet', 'Class-Data', 'ML-Data', 'TBM_SPLIT-ML2-Data',
              'TBM_SPLIT-A-ML2-Data', 'TBM_REPORT-Pdf-Data', 'TBM_REPORT-Pic']  # 生成目录
for folder in Out_Folder:
    if not os.path.exists(os.path.join(Root_Path, folder)):
        os.makedirs(os.path.join(Root_Path, folder))  # 创建文件夹
# 文件夹路径赋值
Raw_Data_Input = os.path.join(Root_Path, IN_Folder[0])  # 原始数据
Cycle_Data_Output = os.path.join(Root_Path, Out_Folder[0])  # 分割好的循环段数据
Key_Data_Output = os.path.join(Root_Path, Out_Folder[1])  # 仅保留破岩关键数据的单个循环段数据
Class_Data_Output = os.path.join(Root_Path, Out_Folder[2])  # 异常的数据
ML_Data_Output = os.path.join(Root_Path, Out_Folder[3])  # 用于机器学习的数据集
ML2_Data_Output = os.path.join(Root_Path, Out_Folder[4])  # 降噪后的数据集
A_ML2_Data_Output = os.path.join(Root_Path, Out_Folder[5])  # 内部段分割的数据集
Pdf_Data_Output = os.path.join(Root_Path, Out_Folder[6])  # 数据汇编
Pic_Data_Output = os.path.join(Root_Path, Out_Folder[7])  # 数据绘图


"""写一段文字，程序的使用说明：1.plot_parameters_TBM，TBM_REPORT调用的时候应该根据自己的目标选择相应的Output"""
# ->->模块1：循环段分割<-<-
Par_name = ['导向盾首里程', '日期', '刀盘转速', '推进给定速度']  # (桩号、日期、刀盘转速、推进速度设定值)请勿修改顺序
TBM_CYCLE().read_file(Raw_Data_Input, Cycle_Data_Output, 100, Par_name)  # 循环段分割

# ->->模块2：提取破岩关键数据<-<-
key_name = ['导向盾首里程', '日期', '刀盘扭矩', '刀盘贯入度', '刀盘给定转速', '刀盘转速', '推进给定速度', '推进速度(nn/M)', '总推力',
            '推进压力', '冷水泵压力', '控制泵压力', '撑紧压力', '左撑靴位移', '右撑靴位移', '主机皮带机速度', '顶护盾压力', '左侧护盾压力',
            '右侧护盾压力', '顶护盾位移', '左侧护盾位移', '右侧护盾位移', '推进泵电机电流', '推进位移']  # 待提取的关键参数
key_parameter_extraction(Cycle_Data_Output, Key_Data_Output, key_name)  # 破岩关键数据提取

# ->->模块3：数据分类<-<-

# ->->模块4：异常1数据清理<-<-

# ->->模块5：异常2数据清理<-<-

# ->->模块6：合并形成机器学习数据集<-<-

# ->->模块7：数据降噪<-<-
butter_worth_filter(Key_Data_Output, ML2_Data_Output)

# ->->模块8：内部段分割<-<-
Par_name = ['推进位移', '推进速度(nn/M)', '刀盘贯入度', '推进给定速度']  # (推进位移、推进速度、刀盘贯入度、推进速度设定值)请勿修改顺序
Out_dir = ['\\Free running', '\\Loading', '\\Boring', '\\Loading and Boring', '\\Boring cycle']
TBM_SPLIT().data_Split(Key_Data_Output, A_ML2_Data_Output, Par_name, Out_dir)

# ->->模块10：数据绘图<-<-
Par_name = ['刀盘转速', '刀盘给定转速', '推进速度(nn/M)', '推进给定速度', '刀盘扭矩', '总推力']  # （要绘制的掘进参数）请勿修改顺序
plot_parameters_TBM(Key_Data_Output, Pic_Data_Output, Par_name)

# ->->模块9：数据汇编<-<-
Par_name = ['导向盾首里程', '日期', '推进位移']  # （桩号、日期、推进位移）请勿修改顺序
TBM_REPORT().cre_pdf(Cycle_Data_Output, Pic_Data_Output, Pdf_Data_Output, Par_name)
