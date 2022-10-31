#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ****************************************************************************
# * Software: TBM_REPORT for python                                          *
# * Version:  3.0.0                                                          *
# * Date:     2022-10-31 20:00:00                                            *
# * Last update: 2022-10-28 20:00:00                                         *
# * License:  LGPL v1.0                                                      *
# * Maintain address https://pan.baidu.com/s/1SKx3np-9jii3Zgf1joAO4A         *
# * Maintain code STBM                                                       *
# ****************************************************************************

import copy
import math
import os
import shutil
import sys
import time
import warnings
import pandas as pd
import psutil
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table
from reportlab.lib.units import mm
from PyPDF2 import PdfFileWriter, PdfFileReader
from matplotlib import pyplot as plt


HISTORY = "最后更改时间:2022-10-31  修改人:刘建国  修改内容:暂无"  # 每次修改后添加修改人、修改时间和改动的功能


warnings.filterwarnings("ignore")  # 忽略警告信息
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体
plt.rcParams['axes.unicode_minus'] = False  # 坐标轴的负号正常显示
plt.rcParams.update({'font.size': 17})  # 设置字体大小
pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/STSONG.TTF'))
ROCK_GRADE = {1: 'Ⅰ', 2: 'Ⅱ', 3: 'Ⅲ', 4: 'Ⅳ', 5: 'Ⅴ', 6: 'Ⅵ'}  # 定义围岩等级和与之对应的字符表达（字典类型）
KEY_NAME_EXAMPLE = [['Number', '', 'Start No', '', 'Start Time', ''], ['Rock mass', '', 'Length', '', 'End Time', '']]
CONTENT_EXAMPLE = {'beg': '', 'end': '', 'mileage': '', 'page': 0}
PARAMETERS = ['导向盾首里程', '日期', '推进位移']
TIME_VAL = []  # 初始化时间存储


class TBM_REPORT(object):
    def __init__(self):
        self.size_font = 8  # 页面字体大小为8
        self.type_font = 'SimSun'  # 页面字体类型
        self.current_page = 1  # 用于存储当前页
        self.parameters = PARAMETERS  # 参数列（参数名称）
        self.out_path = ''  # 初始化输出路径

    def create_report_Dir(self):
        """如果是第一次生成，需要创建相关文件夹，如果文件夹存在，则清空"""
        if not os.path.exists(self.out_path):
            os.mkdir(self.out_path)
        else:
            shutil.rmtree(self.out_path)
            os.mkdir(self.out_path)

    def add_footer_info(self, Object):
        """添加每页页脚"""
        Object.setFont(self.type_font, self.size_font)  # 设置字体类型及大小
        Object.setFillColor(colors.black)  # 设置字体颜色
        Object.drawString(105 * mm, 10 * mm, f'Page%d' % self.current_page)  # 页脚信息
        self.current_page += 1  # 页脚信息自增

    def add_text_info(self, Object, _Inf_):
        """添加正文信息"""
        format_data = []  # 用于存储页面信息
        for row in range(3):  # 对_Inf_信息转换为符合要求的形式
            format_data.append(_Inf_[2 * row][0] + _Inf_[2 * row + 1][0])
            format_data.append(_Inf_[2 * row][1] + _Inf_[2 * row + 1][1])
            format_data.append(['' for _ in range(12)])
        Cell_w = [13*mm, 9*mm, 12*mm, 13*mm, 13*mm, 25*mm, 13*mm, 9*mm, 12*mm, 13*mm, 13*mm, 25*mm]  # 表格列宽信息
        Cell_h = [8*mm, 8*mm, 68*mm, 8*mm, 8*mm, 68*mm, 8*mm, 8*mm, 68*mm]  # 表格行高信息
        sheet = Table(format_data, colWidths=Cell_w, rowHeights=Cell_h,  # 创建表格并写入信息
                      style={("FONT", (0, 0), (-1, -1), self.type_font, self.size_font),  # 字体
                             ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色
                             ('SPAN', (0, 2), (5, 2)), ('SPAN', (6, 2), (-1, 2)), ('SPAN', (0, 5), (5, 5)),  # 合并单元格
                             ('SPAN', (6, 5), (-1, 5)), ('SPAN', (0, 8), (5, 8)), ('SPAN', (6, 8), (-1, 8)),  # 合并单元格
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 左右上下居中
                             ('INNERGRID', (0, 0), (-1, -1), 0.7, colors.black),  # 内部框线
                             ('BOX', (0, 0), (-1, -1), 0.7, colors.black)})  # 外部框线
        sheet.wrapOn(Object, 0, 0)  # 将sheet添加到Canvas中
        sheet.drawOn(Object, 20 * mm, 24 * mm)  # 将sheet添加到Canvas中

    def add_content_info(self, Object, _Inf_):
        """添加目录信息"""
        format_data = [['CATALOGUE']]  # 用于存储目录信息
        for row in range(50):
            if row < len(_Inf_):
                format_data.append(['%s-%s' % (_Inf_[row]['beg'], _Inf_[row]['end']),  # 每页起始-结束的循环段编号
                                    '', '%7.1f' % float(_Inf_[row]['mileage']),  # 每页起始桩号
                                    '.' * 150, 'Page %d' % _Inf_[row]['page']])  # 每页页码
            else:
                format_data.append(['', '', '', '', ''])  # 不足50页时相关记录用空值代替
        Cell_w = [16*mm, 3*mm, 10*mm, 95*mm, 12*mm]  # 表格列宽信息
        sheet = Table(format_data, colWidths=Cell_w, rowHeights=5.1 * mm, style={
            ("FONT", (0, 0), (-1, 0), self.type_font, self.size_font + 5),  # 目录标题字体
            ("FONT", (0, 1), (-1, -1), self.type_font, self.size_font),  # 目录正文字体
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),  # 字体颜色
            ('SPAN', (0, 0), (-1, 0)),  # 合并单元格
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')})  # 左右上下居中
        sheet.argH[0] = 8*mm  # 调整目录名称行高
        sheet.wrapOn(Object, 0, 0)  # 将sheet添加到Canvas中
        sheet.drawOn(Object, 36*mm, 25*mm)  # 将sheet添加到Canvas中

    def add_pic_info(self, Object, _Pic_):
        """添加图片信息"""
        pic_x, pic_y = [21*mm, 106*mm], [193*mm, 109*mm, 25*mm]  # 图片位置信息
        for row in range(3):
            for col in range(2):
                Image = _Pic_[2 * row + col]  # 读取图片
                if Image:  # 若路径有效，则添加图片
                    Object.drawImage(image=Image, x=pic_x[col], y=pic_y[row], width=83*mm, height=66*mm, anchor='c')

    def cre_pdf(self, _input_file_, _input_pic_, _out_path_, _par_name_, History=False):
        """读取数据，并将数据转化为可识别的类型"""
        if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
        if (not _input_file_) or (not _input_pic_) or (not _out_path_) or (not _par_name_):  # 检查传入参数是否正常
            print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
            sys.exit()
        self.parameters, self.out_path = _par_name_, _out_path_  # 保存相关参数和输出路径
        self.create_report_Dir()  # 创建文件夹
        text_path = os.path.join(self.out_path, 'text.pdf')
        content_path = os.path.join(self.out_path, 'content.pdf')
        pdf_text = Canvas(filename=text_path, pagesize=None, bottomup=1, pageCompression=1, encrypt=None)  # 创建pdf
        pdf_content = Canvas(filename=content_path, pagesize=None, bottomup=1, pageCompression=1, encrypt=None)  # 创建pdf
        file_name_list = os.listdir(_input_file_)  # 获取循环段列表
        key_val, pic_val, key_content = [], [], []  # 定义关键参数(key_value)、图片参数(pic_value)列表
        for cycle, file_name in zip([i + 1 for i in range(len(file_name_list))], file_name_list):
            Data_cycle = pd.read_csv(os.path.join(_input_file_, file_name), encoding='gb2312')  # 读取文件
            Data_cycle_values = Data_cycle.loc[:, self.parameters].values  # 提取与掘进状态判定有关的参数，并对其类型进行转换，以提高程序执行速度
            text_value, content_value = copy.deepcopy(KEY_NAME_EXAMPLE), copy.deepcopy(CONTENT_EXAMPLE)  # 复制一个模板，准备填充数据
            text_value[0][1] = ('%00005d' % cycle)  # 获取循环段编号(Num)
            text_value[0][3] = '%sm' % round(Data_cycle_values[0][0], 1)  # 获取桩号记录
            text_value[0][5] = Data_cycle_values[0][1]  # 获取开始时间(Time_beg)
            text_value[1][1] = ''  # 获取围岩等级(Rock_Mass)
            text_value[1][3] = '%4.2fm' % round((Data_cycle_values[-1][2] - Data_cycle_values[0][2]) / 1000, 2)  # 掘进长度
            text_value[1][5] = Data_cycle_values[-1][1]  # 获取结束时间(Time_end)
            pic_val.append(os.path.join(_input_pic_, file_name[:-4] + '.png'))  # 添加图片参数(pic_value)数值
            key_val.append(text_value)  # 添加关键参数(pic_value)数值
            if (not cycle % 6) or (cycle == len(file_name_list)):  # 以6个为一组,剩余不足6个也输出
                start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                content_value['beg'], content_value['end'] = key_val[0][0][1], key_val[-1][0][1]  # 目录信息
                content_value['mileage'], content_value['page'] = key_val[0][0][3][:-1], self.current_page  # 目录信息
                key_content.append(content_value)
                if cycle == len(file_name_list):  # 若生成的pdf最后一页信息填充不全，可用空值进行替代
                    for fill in range(6 - len(key_val)):
                        key_val.append(copy.deepcopy(KEY_NAME_EXAMPLE)), pic_val.append(None)
                else:
                    pdf_text.showPage()  # 新增一页
                self.add_text_info(pdf_text, key_val)  # 绘制表格
                self.add_pic_info(pdf_text, pic_val)  # 添加图片
                self.add_footer_info(pdf_text)  # 绘制页脚
                key_val, pic_val = [], []  # 对变量进行初始化， 便于进行下一次操作
                if (self.current_page - 1) % 50 == 0 or (cycle == len(file_name_list)):
                    self.add_content_info(pdf_content, key_content)
                    key_content = []  # 对变量进行初始化， 便于进行下一次操作
                    pdf_content.showPage()  # 新增一页
                end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
                visual('PDF generation', cycle=math.ceil(cycle / 6),
                       Sum=math.ceil(len(file_name_list) / 6), start=start, end=end, Clear=False)
        pdf_text.save(), pdf_content.save()  # pdf保存
        self.MergePDF(content=content_path, text=text_path)  # 合并目录和正文
        visual('PDF generation', cycle=-1, Clear=True)

    def MergePDF(self, **kwargs):
        """合并目录和正文成为一个PDF"""
        output = PdfFileWriter()
        outputPages = 0  # 最终pdf页数
        _Pdf_ = [open(kwargs['content'], "rb"), open(kwargs['text'], "rb")]
        for file in _Pdf_:
            Input = PdfFileReader(file)  # 读取源PDF文件
            pageCount = Input.getNumPages()
            outputPages += pageCount  # 获得源PDF文件中页面总数
            for iPage in range(pageCount):
                output.addPage(Input.getPage(iPage))  # 分别将page添加到输出output中
        outputStream = open(os.path.join(self.out_path, 'TBM-Data.pdf'), "wb")
        output.write(outputStream)  # 写入到目标PDF文件
        outputStream.close(), _Pdf_[0].close(), _Pdf_[1].close()  # 关闭读取的文件
        os.remove(kwargs['content']), os.remove(kwargs['text'])


def plot_parameters_TBM(_input_path_, _out_path_, Par_name, History=False):
    """完成对掘进参数（n, n_set, V, V_set, F, T）的绘图"""
    if History: print('\n', '='*100, '\n', HISTORY, '\n', '='*100, '\n')  # 打印文件修改记录
    # ['刀盘转速', '刀盘给定转速', '推进速度(nn/M)', '推进给定速度', '刀盘扭矩', '总推力']
    if (not _input_path_) or (not _out_path_) or (not Par_name):  # 检查传入参数是否正常
        print('->-> %s' % os.path.basename(__file__), '\033[0;31mParameters abnormal, Please check!!!\033[0m')
        sys.exit()
    if not os.path.exists(_out_path_):
        os.mkdir(_out_path_)
    else:
        shutil.rmtree(_out_path_)
        os.mkdir(_out_path_)
    try:
        Index_Path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Index-File.csv')  # 索引文件存放根目录
        data_Index = pd.read_csv(Index_Path, encoding='gb2312')  # 读取文件
        data_Index_value, data_Index_name = data_Index.values, list(data_Index)
        col_location = [data_Index_name.index('循环段'), data_Index_name.index('上升段起点'),
                        data_Index_name.index('稳定段起点'), data_Index_name.index('稳定段终点')]
    except FileNotFoundError:
        Index_Path, data_Index_value, col_location = [], [], []
    file_name_list = os.listdir(_input_path_)  # 获取输入文件夹下的所有文件名，并将其保存
    for num, file_name in zip([i + 1 for i in range(len(file_name_list))], file_name_list):  # 遍历每个文件
        start = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        TBM_Data_cycle = pd.read_csv(os.path.join(_input_path_, file_name), encoding='gb2312')  # 读取文件
        x = [i for i in range(TBM_Data_cycle.shape[0])]  # 'Time'
        y_n = TBM_Data_cycle.loc[:, Par_name[0]]  # '刀盘转速'
        y_n_set = TBM_Data_cycle.loc[:, Par_name[1]]  # '刀盘转速设定'
        y_V = TBM_Data_cycle.loc[:, Par_name[2]]  # '推进速度'
        y_V_set = TBM_Data_cycle.loc[:, Par_name[3]]  # '推进速度设定'
        y_T = TBM_Data_cycle.loc[:, Par_name[4]]  # '刀盘总扭矩'
        y_F = TBM_Data_cycle.loc[:, Par_name[5]]  # '推进总推力'
        plt.figure(figsize=(10, 8), dpi=120)  # 设置画布大小（10cm x 8cm）及分辨率（dpi=120）
        plt.scatter(x, y_n, label="n", color='mediumblue', marker='+')
        plt.scatter(x, y_n_set, label="n_set", color='k', marker='_')
        plt.scatter(x, y_V / 10, label="V/10", color='y', marker='.', s=100)
        plt.scatter(x, y_V_set / 10, label="V_set/10", color='saddlebrown', marker='.', s=50)
        plt.legend(bbox_to_anchor=(0.36, 1.1), loc=9, borderaxespad=-1, ncol=2, columnspacing=2, frameon=False,
                   fontsize=18, markerscale=1.5)
        plt.ylabel("刀盘转速、推进速度及其设定值", fontsize=20, labelpad=10)
        plt.xlabel("时间/s", fontsize=20)
        plt.twinx()
        plt.scatter(x, y_T, label="T", color='deeppink', marker='^', s=30)
        plt.scatter(x, y_F / 2, label="F/2", color='c', marker='v', s=30)
        plt.legend(bbox_to_anchor=(0.77, 1.1), loc=9, borderaxespad=-1.1, ncol=1, columnspacing=2, frameon=False,
                   fontsize=18, markerscale=1.5)
        plt.ylabel("刀盘推力、刀盘扭矩", fontsize=20, labelpad=10)
        if Index_Path:
            plt.axvline(x=data_Index_value[int(file_name[:5]) - 1][col_location[1]], c="r", ls="-.")
            plt.axvline(x=data_Index_value[int(file_name[:5]) - 1][col_location[2]], c="r", ls="-.")
            plt.axvline(x=data_Index_value[int(file_name[:5]) - 1][col_location[3]], c="r", ls="-.")
        plt.savefig(os.path.join(_out_path_, file_name[:-4] + '.png'), dpi=120, format='png', bbox_inches='tight')
        plt.close()
        end = time.time()  # 获取当前时刻时间（用于计算程序执行时间）
        visual('Drawing pic', cycle=num, Sum=len(file_name_list), start=start, end=end, Clear=False)
    visual('Drawing pic', cycle=-1, Clear=True)


def visual(Print, **kwargs):
    """可视化输出"""
    global TIME_VAL
    p = psutil.Process(os.getpid())
    cpu_percent = p.cpu_percent()  # CPU占用
    mem_percent = p.memory_percent()  # 内存占用
    if kwargs['cycle'] != -1:
        time_diff = kwargs['end'] - kwargs['start']  # 执行一个文件所需的时间
        TIME_VAL.append(time_diff)  # 对每个时间差进行保存，用于计算平均时间
        mean_time = sum(TIME_VAL) / len(TIME_VAL)  # 计算平均时间
        sum_time = round(sum(TIME_VAL) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '[第%d个 / 共%d个]  ' % (kwargs['cycle'], kwargs['Sum']), '[所用时间%ds / 平均时间%ds]'
              % (int(time_diff), int(mean_time)), ' ', '[CPU占用: %4.2f%%  内存占用: %4.2f%%]'
              % (cpu_percent, mem_percent), '  ', '\033[0;33m累积时间:%6.3f小时\033[0m' % sum_time, end='')
    else:
        sum_time = round(sum(TIME_VAL) / 3600, 3)  # 计算程序执行的总时间
        print('\r', '->->', '\033[0;32m%s completed, which took %6.3f hours\033[0m' % (Print, sum_time))
    if kwargs['Clear']:
        TIME_VAL = []
