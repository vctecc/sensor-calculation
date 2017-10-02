"""
Программа для расчета окон солнечного датчика.
Необходимо сделать верхнее меню(для чего пока не понятно)
Добавить вывод лога расчетов, возможно в отдельный фаил
Потом подцеплять сами библиотеки для отрисовки графиков, если их нет
"""

import collections
import glob
import os
from tkinter import Tk, Text, Toplevel
from tkinter.ttk import Label, Entry, Frame, Button
from tkinter.messagebox import askyesno, showinfo
from tkinter.filedialog import *
import threading
from math import *

# Импортируем один из пакетов Matplotlib
import pylab
# Импортируем пакет со вспомогательными функциями
from matplotlib import mlab

# TODO необходимо сделать нормальый вывод данных в лог
# TODO I have a very good idea with this
FIELDS = {'azimut': ('Угловые поля фотодатчика по азимуту:', 'A1=', 'A2='),
          'zenit': ('Угловые поля фотодатчика по зениту:', 'F1=', 'F2='),
          'coords': ('Координаты фотодатчика:', 'X=', 'Y=', 'Z='),
          'radius': ('Радиус:', 'R=')}
appname = 'Solar sensor 1.0'


class MainWindow(Tk):
    """
    Класс базового окна, наследует все возможности Tk и переназначает метод закрятия для выдачи окна предупреждения
    """

    def __init__(self):
        Tk.__init__(self)

    def destroy(self):
        if askyesno('!!!', 'Выйти из программы?'):
            Tk.quit(self)


class DataLog(Frame):
    def __init__(self, name):
        Frame.__init__(self)
        Label(text=name, justify='left').pack(fill='x')
        self.log = Text(height=10, width=50)
        self.log.pack(fill='x')

    def insert(self, *data):
        for part in data:
            self.log.insert('end', part)
            self.log.insert('end', '\n')


class DataDigitalField(Frame):
    """
    Класс генерирует стандартное окно полей ввода и позволяет получаеть  из него данные.
    """

    def __init__(self, name, *args):
        Frame.__init__(self)
        self.field_list = list()
        Label(text=name).pack(side='top')
        field = Frame(self)
        field.pack()

        for name in args:
            # помещаем виджет на master-field
            Label(master=field, text=name).pack(side='left')
            # добавляем элементы из полей
            self.field_list.append(Entry(master=field))
            # (длина строки-1 в списке)
            self.field_list[len(self.field_list) - 1].pack(side='left')

    def get(self):
        """
        Получает данные из поля и пытается преобразовать в число.
        """
        data = list()

        for field in self.field_list:
            num = self.to_digit(field.get())
            if num:
                data.append(num)
            else:
                return False

        return data

    def insert(self, data):
        """
        Ожидает на вход список переменных, которые заносит в ячейки данных
        """
        for field in self.field_list:
            if data:
                field.insert(0, data.pop(0))

    def clear(self):
        for field in self.field_list:
            field.delete(0)

    @staticmethod
    def to_digit(data):
        """
        Работает только для преобразования строки в число. Иначе негарантируемое поведение.
        Проверяет можно ли преобразовать в целочисленное. Если да,возвращает число.
        В противном случае пробует преобразовать в вещественное.
        При ошибке возвращает False.
        """

        try:
            data = int(data)
        except ValueError:
            try:
                data = float(data)

            except ValueError:
                return False

        except Exception:
            return False

        return data


class SolarMain(MainWindow):
    def __init__(self):

        MainWindow.__init__(self)
        self.title(appname)

        # список размещенных на форме полей ввода
        data_fields = self.make_fields()

        # Размещение окна журнала операция
        self.data_log = DataLog('Результаты расчета:')
        self.data_log.pack()

        Button(text='Расчитать', command=lambda: self.run(data_fields)).pack(side=BOTTOM)
        Button(text='По умолчанию', command=lambda: self.default(data_fields)).pack(side=BOTTOM)
        Button(text='График', command=lambda: self.create_chart(data_fields)).pack(side=BOTTOM)

    @staticmethod
    def make_fields():
        """
        Генерация полей ввода данных и размещение их в окне программы
        :return: кортеж из созданных полей
        """

        azimut = DataDigitalField('Угловые поля фотодатчика по азимуту:', 'A1=', 'A2=')
        azimut.pack()
        zenit = DataDigitalField('Угловые поля фотодатчика по зениту:', 'F1=', 'F2=')
        zenit.pack()
        coord = DataDigitalField('Координаты фотодатчика:', 'X=', 'Y=', 'Z=')
        coord.pack()
        radius = DataDigitalField('Радиус:', 'R=')
        radius.pack()

        return azimut, zenit, coord, radius

    @staticmethod
    def default(fields):
        #  F1=  26.7 F2=  94.3 A1=  -4.3 A2=  20.7 R=  39 x1= 9 y1= 2 z1= 8
        initial_data = ([-4.3, 20.7], [26.7, 94.3], [9, 2, 8], [39])

        for f in fields:
            d = initial_data[fields.index(f)]
            f.insert(d)

    @staticmethod
    def get_param(fields):
        """
        Извлекает данные их полей ввода и  преобразует в единый список.
        :params обобщеный список данных из полей ввода
        """
        params = list()
        # Return True if arg1 in itarable
        if isinstance(fields, collections.Iterable):
            for field in fields:
                data = field.get()

                if isinstance(data, collections.Iterable):
                    for num in data:
                        params.append(num)
                else:
                    params.append(data)
        else:
            num = fields.get()
            if num:
                params.append(num)

        return params

    def print(self, *data):
        self.data_log.insert(data)

    def run(self, list_of_params):
        """
        Запрашивает данные из списка параметров. 
        Проверяет корректность введенных данных.
        В случае неверных занчений выдает окно об ошибке.
        Если ввод корректен, вызывает расчет.
        Если в процессе расчета есть выводятся математические ошибки, выводится сообще.
        """

        data = self.get_param(list_of_params)
        if False in data:
            showinfo(title='Error', message=u'Некорректно введеные данные!')
        else:
            try:
                self.calculate(data)
            except Exception:
                showinfo(title='Error', message=u'Некорректно введеные данные!')

    @staticmethod
    def calculate(data):

        A1, A2, F1, F2, x1, y1, z1, radius = data
        stepF = 34
        stepA = A2 - A1
        # TODO Возможно тут стоит использовать целочисленное деление вместо округляения?
        Fit = round((F2 - F1) / stepF)
        Ait = round((A2 - A1) / stepA)

        points = {'x1': [], 'y1': [], 'x2': [], 'y2': []}

        for k in range(Ait + 1):
            for i in range(Fit + 1):
                F = F1 + stepF * i
                A = A1 + stepA * k

                # Его направляющие косинусы в сферических координатах (1):
                lK = cos(radians(F))
                mK = sin(radians(F)) * cos(radians(A))
                nK = sin(radians(F)) * sin(radians(A))
                a = pow((mK / lK), 2) + 1
                b = -2 * (pow((mK / lK), 2) * x1 - (mK / lK) * y1)
                c = pow(((mK / lK) * x1 - y1), 2) - pow(radius, 2)

                if F > 90:
                    X = (-0.5 * b - sqrt(pow(0.5 * b, 2) - a * c)) / a
                elif F < 90:
                    X = (-0.5 * b + sqrt(pow(0.5 * b, 2) - a * c)) / a
                Xc = X
                Yc = mK * (Xc - x1) / lK + y1
                Zc = (Xc - x1) * nK / lK + z1
                # Yр, Xp - координаты точки на рзвертке цилиндра
                # 2-ой Переход от цилиндра к плоскости
                # Развернем цилиндр в плоскость, паралельную ZOY, при этом Yc сохраняется, те
                Yр = Zc
                L = degrees(atan(Xc / Yc))
                # Координаты вдоль развертки окружности цилиндра
                Xp = (2 * pi * radius * L) / 360
                print('F= ', F, 'A= ', A, 'R= ', radius, 'Xc= ', Xc, 'Yc= ', Yc, 'Zc= ', Zc, 'Xp= ', Xp, 'Yр= ', Yр)

                if k / 2 == 0:
                    points['x1'].append(Xp)
                    points['y1'].append(Yр)
                else:
                    points['x2'].append(Xp)
                    points['y2'].append(Yр)

        return points

    def create_chart(self, list_of_params):
        data = self.get_param(list_of_params)
        points = self.calculate(data)

        lx = [min(points.get('x1'))] + [min(points.get('x2'))]
        ly = [min(points.get('y1'))] + [max(points.get('y2'))]
        rx = [max(points.get('x1'))] + [max(points.get('x2'))]
        ry = [max(points.get('y1'))] + [min(points.get('y2'))]

        pylab.plot(lx, ly)
        pylab.plot(rx, ry)
        pylab.plot(points.get('x1'), points.get('y1'))
        pylab.plot(points.get('x2'), points.get('y2'))
        # Покажем окно с нарисованным графиком
        pylab.show()


if __name__ == '__main__':
    solar = SolarMain()
    solar.mainloop()