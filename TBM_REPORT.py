#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_REPORT for python                                          *
# * Version:  1.0.1                                                          *
# * Date:     2022-10-13                                                      *
# * Last update: 2022-10-1                                                   *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import copy
import math
import os
import shutil
import time
import warnings
import pandas as pd
from PyPDF2 import PdfFileWriter, PdfFileReader
from fpdf import FPDF

TBM_REPORT_version = '1.0.1'  # 版本号，请勿修改！！！
warnings.filterwarnings("ignore")  # 忽略警告信息
ROCK_GRADE = {1: 'Ⅰ', 2: 'Ⅱ', 3: 'Ⅲ', 4: 'Ⅳ', 5: 'Ⅴ', 6: 'Ⅵ'}  # 定义围岩等级和与之对应的字符表达（字典类型）
KEY_NAME_EXAMPLE = [['Number', '', 'Start No', '', 'Start Time', ''], ['Rock mass', '', 'Length', '', 'End Time', '']]


class PDF(FPDF):  # 以下为修改页脚代码
    def footer(self):
        self.set_y(-2)
        self.set_font('STSONG', '', 10)
        self.cell(0, 1.0, 'Page%d' % self.page_no(), 0, 0, 'C')


class TBM_REPORT(object):
    def __init__(self):
        self.Number = 1  # 循环段编号
        self.cycles = 6  # 一页所展示的循环段数量
        self.size_font = 8  # 页面字体大小为8
        self.page_sum = 0  # 初始化总页数
        self.parameters = ['导向盾首里程', '日期', '日进尺', '围岩等级', '推进位移']  # 参数列（参数名称）
        self.temp_text_path = 'temp\\All-Data.pdf'
        self.temp_content_path = 'temp\\All-Data-content.pdf'
        self.time_val = []

    def set_page(self, left=2.0, top=2.0, right=2.0, size_font=None):
        """pdf页面和字体设置"""
        if not size_font:  # 是否自定义字体大小
            size_font = self.size_font
        _pdf_ = PDF(format='A4', unit='cm')  # 创建一个pdf，页面大小为A4，长度单位cm
        _pdf_.set_margins(left, top, right)  # 修改左页边距为2cm,上页边距为2cm,右页边距为2cm
        _pdf_.add_font('STSONG', '', 'C:/Windows/Fonts/STSONG.TTF', uni=True)  # 设置字体类型为宋体
        _pdf_.set_font('STSONG', '', size_font)  # 设置默认字体大小
        return _pdf_

    def cre_text(self, _pdf_, _text_, _pic_):
        """创建正文并写入内容"""
        _pdf_.add_page()  # 新增加一页
        per_w = (_pdf_.w - 2 * _pdf_.l_margin) / 24  # 单位列宽
        h_cell, w_cell = 0.9, [1.8, 1.3, 1.7, 1.8, 1.9, 3.5]  # 文本框高度(h_cell)和宽度(w_cell)
        h_pic, w_pic = 6.5, [12, 12]  # 图片框高度(h_pic)和宽度(w_pic)
        x_pic, y_pic = [2, 10.5, 2, 10.5, 2, 10.5], [3.9, 3.9, 12.2, 12.2, 20.5, 20.5]  # 图片水平位置(x_pic)和竖直位置(y_pic)
        _pdf_.ln(0.5)  # 换行（向下跳转0.5cm）
        for repeat in range(0, self.cycles, 2):  # 重复3次
            for row in range(3):  # 每次绘制三行（两行文本框，一行图片框）
                if row < 2:  # 绘制文本框并填充内容
                    for col in range(2 * len(w_cell)):
                        if col < 6:  # 绘制并填充1-6单元格
                            _pdf_.cell(per_w * w_cell[col], h_cell, _text_[repeat][row][col], border=1, align='C')
                        else:  # 绘制并填充7-12单元格
                            _pdf_.cell(per_w * w_cell[col-6], h_cell, _text_[repeat+1][row][col-6], border=1, align='C')
                    _pdf_.ln()  # 换行
                else:  # 绘制图片框并填充图片
                    for col in range(len(w_pic)):
                        if _pic_[repeat + col]:
                            _pdf_.image(_pic_[repeat+col], x_pic[repeat+col], y_pic[repeat+col], w=8.4, h=6.3)  # 插入图片
                        _pdf_.cell(per_w * w_pic[col], h_pic, '', border=1, align='C')  # 绘制文本框，不予填充
                    _pdf_.ln()  # 换行
        return _pdf_

    def cre_content(self, _text_):
        """创建目录并写入内容"""
        pdf_content = self.set_page(left=3.5, top=1.5, right=3.5, size_font=13)  # 创建新的pdf，并进行页面和字体设置
        pdf_content.add_page()  # 新增加一页
        per_w = (pdf_content.w - 2 * pdf_content.l_margin) / 14  # 单位列宽
        h_title, w_title = 14, 0.8  # 标题框高度(h_title)和宽度(w_title)
        h_cell, w_cell = 0.51, [1.8, 1.3, 9.7, 1.2]  # 文本框高度(h_cell)和宽度(w_cell)
        pdf_content.cell(per_w * h_title, w_title, 'CATALOGUE', align='C')  # 绘制文本框，不予填充
        pdf_content.ln()  # 换行
        pdf_content.set_font('STSONG', '', self.size_font + 1)  # 设置字体大小为7.5
        for row in range(len(_text_)):  # 绘制文本框并填充每页索引
            for col in range(len(w_cell)):
                pdf_content.cell(per_w * w_cell[col], h_cell, _text_[row][col], align='L')  # 绘制文本框，不予填充
            pdf_content.ln()  # 换行
        return pdf_content

    def cre_pdf(self, _input_file_path_, _input_pic_path_, _out_path_):
        """读取数据，并将数据转化为可识别的类型"""
        pdf_text = self.set_page(left=2.0, top=1.5, right=2.0)  # 创建新的pdf，并进行页面和字体设置
        file_name_list = os.listdir(_input_file_path_)  # 获取循环段列表
        self.page_sum = math.ceil(len(file_name_list) / self.cycles)  # 获取总页数
        key_val, pic_val, content_val = [], [], []  # 定义关键参数(key_value)、图片参数(pic_value)和目录参数(content_val)列表
        for cycle, file_name in zip([i + 1 for i in range(len(file_name_list))], file_name_list):
            TBM_Data_cycle = pd.read_csv(os.path.join(_input_file_path_, file_name), encoding='gb2312')  # 读取文件
            TBM_Data_cycle_values = TBM_Data_cycle.loc[:, self.parameters].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
            value = copy.deepcopy(KEY_NAME_EXAMPLE)  # 复制一个标题模板，准备填充数据
            value[0][1] = ('%00005d' % self.Number)  # 获取循环段编号(Num)
            value[0][3] = '%sm' % round(TBM_Data_cycle_values[0][0], 1)  # 获取桩号记录
            value[0][5] = TBM_Data_cycle_values[0][1]  # 获取开始时间(Time_beg)
            value[1][1] = ''  # 获取围岩等级(Rock_Mass)
            value[1][3] = '%4sm' % round((TBM_Data_cycle_values[-1][4]-TBM_Data_cycle_values[0][4])/1000, 2)  # 获取掘进长度记录
            value[1][5] = TBM_Data_cycle_values[-1][1]  # 获取结束时间(Time_end)
            pic_val.append(os.path.join(_input_pic_path_, file_name[:-4] + '.png'))  # 添加图片参数(pic_value)数值
            key_val.append(value)  # 添加关键参数(pic_value)数值
            if (not cycle % 6) or (cycle == len(file_name_list)):  # 以6个为一组,剩余不足6个也输出
                page_num_beg, page_num_end = key_val[0][0][1], key_val[-1][0][1]
                if cycle == len(file_name_list):  # 若生成的pdf最后一页信息填充不全，可用空值进行替代
                    for fill in range(6 - len(key_val)):
                        key_val.append(copy.deepcopy(KEY_NAME_EXAMPLE)), pic_val.append(None)
                content_val.append(['%s-%s' % (page_num_beg, page_num_end),
                                    '  %s' % key_val[0][0][3][:-1], '.' * 136, 'Page %d' % math.ceil(cycle / 6)])  # 目录
                start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                pdf_text = self.cre_text(pdf_text, key_val, pic_val)  # 此函数可完成创建文本框和图片框以及添加数据和图片等功能
                end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                key_val, pic_val = [], []  # 对变量进行初始化， 便于进行下一次操作
                self.visual(cycle, start, end)
            self.Number += 1
        if not os.path.exists('temp\\'):
            os.makedirs('temp\\')
        self.cre_content(content_val).output(self.temp_content_path, 'F')
        pdf_text.output(self.temp_text_path, 'F')  # pdf保存
        self.MergePDF(_out_path_)
        self.visual(-1, None, None)

    def visual(self, cycle, start, end):
        """可视化输出"""
        if cycle != -1:
            time_diff = int(end - start)  # 执行一个文件所需的时间
            self.time_val.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
            mean_time = int(sum(self.time_val) / len(self.time_val))  # 计算平均时间
            sum_time = round(sum(self.time_val) / 3600, 2)  # 计算程序执行的总时间
            print('\r', '->->', '[第%d页 / 共%d页]  ' % (math.ceil(cycle / 6), self.page_sum), '[所用时间%ds / 平均时间%ds]'
                  % (time_diff, mean_time), '  ', '\033[0;33m累积时间:%6.2f小时\033[0m' % sum_time, end='')
        else:
            sum_time = round(sum(self.time_val) / 3600, 2)  # 计算程序执行的总时间
            print('\r', ' ->->', '\033[0;32mPDF generation completed, , which took %6.2f hours\033[0m' % sum_time)

    def MergePDF(self,  _out_path_):
        """合并目录pdf和正文pdf"""
        output = PdfFileWriter()
        outputPages = 0
        pdf_ = [open(self.temp_content_path, "rb"), open(self.temp_text_path, "rb")]
        for file in pdf_:
            Input = PdfFileReader(file)  # 读取源PDF文件
            pageCount = Input.getNumPages()
            outputPages += pageCount  # 获得源PDF文件中页面总数
            for iPage in range(pageCount):
                output.addPage(Input.getPage(iPage))  # 分别将page添加到输出output中
        outputStream = open(os.path.join(_out_path_, 'TBM-Data.pdf'), "wb")
        output.write(outputStream)  # 写入到目标PDF文件
        outputStream.close(), pdf_[0].close(), pdf_[1].close()  # 关闭读取的文件
        shutil.rmtree(self.temp_content_path[:4])  # 递归删除文件夹，即：删除非空文件夹
