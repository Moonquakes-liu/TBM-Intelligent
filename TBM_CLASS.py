#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_CLEAN for python                                           *
# * Version:  2.0.0                                                          *
# * Date:     2022-10-20 20:00:00                                            *
# * Last update: 2022-10-20 00:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import os


class TBM_CLASS(object):
    def __init__(self):
        self.create_dir = True  # 第一次保存文件时要创建相关文件夹
        self.parameter = []  # 过程中用到的相关参数
        self.out_path = ''  # 初始化输出路径
        self.DIR_OUT = ''  # 文件输出路径

    def create_class_Dir(self):
        """如果是第一次生成，需要创建相关文件夹"""
        if self.create_dir:
            for Dir in self.DIR_OUT:
                if not os.path.exists(self.out_path + Dir):
                    os.mkdir(self.out_path + Dir)
            self.create_dir = False

    def data_class(self, _input_path_, _out_path_, _par_name_, _dir_path_):
        """数据分类"""
        self.out_path, self.parameter, self.DIR_OUT = _out_path_, _par_name_, _dir_path_  # 输出路径、所用到的参数、文件保存子路径
        self.create_class_Dir()  # 创建文件夹
        pass


class TBM_CLEAN(object):
    def __init__(self):
        self.create_dir = True  # 第一次保存文件时要创建相关文件夹
        self.parameter = []  # 过程中用到的相关参数
        self.out_path = ''  # 初始化输出路径
        self.DIR_OUT = ''  # 文件输出路径

    def create_clean_Dir(self):
        """如果是第一次生成，需要创建相关文件夹"""
        if self.create_dir:
            for Dir in self.DIR_OUT:
                if not os.path.exists(self.out_path + Dir):
                    os.mkdir(self.out_path + Dir)
            self.create_dir = False

    def data_clean(self, _input_path_, _out_path_, _par_name_, _dir_path_):
        """异常数据清理"""
        self.out_path, self.parameter, self.DIR_OUT = _out_path_, _par_name_, _dir_path_  # 输出路径、所用到的参数、文件保存子路径
        self.create_clean_Dir()  # 创建文件夹
        pass


def ML_data(_input_path_, _out_path_):
    """合并形成机器学习数据集"""
    pass
