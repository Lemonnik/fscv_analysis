import matplotlib.pyplot as plt
import peakutils
import plotly.express as px
import random
from scipy import sparse
from scipy.ndimage import uniform_filter
from scipy.sparse.linalg import spsolve


class DopamineData:
    def __init__(self):
        '''
            Инициализация структуры
        '''
        self.first_peaks = {}
        self.second_peaks = {}
        self.difference_2d = None  # для разницы пиков
        self.difference_2d_wo_baseline = None  # для разницы пиков (без бэйзлайна)\
        self.graph_data = {}  # Для инфы по графикам. {(lambda, p, method) : (conc_w_baseline, baseline, conc_wo_baseline)}
        self.da_conc1 = None       # площадь под пиком
        self.da_conc2 = None       # разница на 170
        self.additional_info = {}
        self.err = {}
        self.stimuli_times = []

        self.time_step = None


    def add_data(self, t, p1, p2, info, err):
        '''
            Добавить данные (пики, инфа, ошибки) для таймпоинта t
        '''
        self.first_peaks[t] = p1
        self.second_peaks[t] = p2
        self.additional_info[t] = info
        self.err[t] = err


    def _transform_data(self, X, interval_min=-0.4, interval_max=1.3):
        '''
            Трансформировать данные в массиве, чтобы изменить диапазон
        '''
        # Это выравнивает в целом, по глобальному минимальному значению
        X_std = (X - X.min()) / (X.max() - X.min())
        X_scaled = X_std * (interval_max - interval_min) + interval_min

        return X_scaled


    def _get_difference(self):
        '''
            Получить разницу двух пиков (по всей длинне в 500)
        '''
        difference_2d = np.empty((len(self.first_peaks.keys()), 500))

        for i, t in enumerate(sorted(self.first_peaks.keys())):
            peak1 = np.array(self.first_peaks[t])
            peak2 = np.array(self.second_peaks[t])
            # peak_dif = self._transform_data(peak1) - self._transform_data(peak2)  # _transform_data!!
            peak_dif = peak1 * 0.0168 - peak2 * 0.0168
            difference_2d[i] = peak_dif

        return difference_2d


    def _preprocess_data(self, window_size=151):
        '''
            Предобработка данных перед отрисовкой
            151 -- при усреднении берётся "(window_size-1)/2" точек до и столько же после
            Если чётное -- то "после" берётся на одну меньше
            Для 151 -- 75 до, сама точка, 75 после
        '''
        if self.difference_2d is None:
            self.difference_2d = self._get_difference()

        # Оконный фильтр для сглаживания шума
        window_sum_2d = uniform_filter(self.difference_2d, mode='nearest', axes = 0, size = window_size)

        # отрезать первые и последние 100 пиков (чтобы работал slidingWindow)
        # и отрезать начало пика (20:) потому что там хвост и какой-то шум
        window_sum_2d_cropped = window_sum_2d[100:-100, 20:]
        first_part_of_data = np.mean(window_sum_2d_cropped[:100,], axis=0)  # усредняем сигнал до первого стимула (на самом деле просто начальный кусочек)
        window_sum_2d_cropped = window_sum_2d_cropped - first_part_of_data  # ещё можно было бы всё до первого стимула сделать равным средним ДОДЕЛАТЬ


        # Если пики (на 170 (150-20)) уходят в минус -- инвертируем
        if sum(window_sum_2d_cropped[:, 150]) < 0:
            print('[LOG] Reversed sign')
            window_sum_2d_cropped = -window_sum_2d_cropped

        # Усредняем площади под пиками -- их будем строить (от 50 до 250, учитывая что вычитали 20 пишем 30:230)
        da_conc1 = np.sum(window_sum_2d_cropped[:, 30:230], axis=1)
        da_conc2 = window_sum_2d_cropped[:, 150]
        self.da_conc1 = da_conc1
        self.da_conc2 = da_conc2

        return   # ?????????


    def _baseline_als(self, y, lam, p, niter=10):
        '''
            Функция для вычитания бэйзлайна
        '''
        L = len(y)
        D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = spsolve(Z, w*y)
            w = p * (y > z) + (1-p) * (y < z)
        return z


    def _remeber_graph_data(self, lam, p, method, what_to_save):
        '''
            # Для инфы по графикам.
            {(lambda, p, method) : (conc_w_baseline, baseline, conc_wo_baseline)}

            СЕЙЧАС ПОКА СОХРАНЯЕТСЯ 1 ПОСЛЕДНИЙ (ЧТОБЫ ПОТОМ ВЫВЕСТИ В ФАЙЛ)
            НО МОЖНО СДЕЛАТЬ ЧТОБЫ ВСЕ НАРИСОВАННЫЕ ХЭШИРОВАЛИСЬ
        '''
        hash_info = (lam, p, method)
        # if hash_info not in self.graph_data.keys():
        # self.graph_data[hash_info] = what_to_save
        self.graph_data[1] = what_to_save

        return self.graph_data


    def save_data(self, filename='graph.csv'):
        '''
            tp -- time point
            ПЕРЕДАВАТЬ В ФУНКЦИЮ ТАКЖЕ ЛЯМБДУ И Р, и тип метода
            Или как или что?
            По умолчанию буде для diff метода
        '''
        if self.graph_data is None:
            print('Сначала нарисуйте график, который хотите сохранить')
            return False

        with open(filename, 'w') as f:
            f.write('Time, conc, baseline, conc_wo_baseline\n')
            for t,cw,b,cwo in zip(dopamineData.graph_data[1][0],
                                  dopamineData.graph_data[1][1],
                                  dopamineData.graph_data[1][2],
                                  dopamineData.graph_data[1][3]):
                f.write(', '.join([str(t), str(cw), str(b), str(cwo)]))
                f.write('\n')

        return True



    def test_baseline_correction(self, lam=10**9, p=0.01, with_stimuli=False, corrected_only=False, method='diff'):
        '''
            Можно потестить разные p и lambda
            method = {'diff', 'peak'}
        '''
        if self.da_conc1 is None or self.da_conc2 is None:
            _ = self._preprocess_data()


        # Выбор метода обсчёта
        if method not in ['diff', 'peak']:
            method = 'diff'
            print(f'Опечатка в написании метода. Был выбран метод по умолчанию (diff)')
        if method == 'diff':
            da_conc = self.da_conc1
        if method == 'peak':
            da_conc = self.da_conc2

        x = sorted(self.first_peaks.keys())
        x = [(num-x[0])/1000/60 for num in x]                            # ПЕРЕВОД ИЗ МИЛИСЕКУНД В МИНУТЫ

        baseline = self._baseline_als(da_conc, lam=lam, p=p)
        # baseline = peakutils.baseline(da_conc)  # так себе работает

        if corrected_only:
            fig = px.line(x = x[100:-100],    # НЕ ДОЛЖНО БЫТЬ КОНСТАНТ!!!
                          y=da_conc - baseline + abs(np.min(da_conc - baseline)),  # + abs(np.min(da_conc - baseline)) чтобы сделать выше нуля
                          render_mode='webg1',
                          )
        else:
            fig = px.line(x = x[100:-100],    # НЕ ДОЛЖНО БЫТЬ КОНСТАНТ!!!
                          y=[da_conc,
                             baseline,
                             da_conc - baseline + abs(np.min(da_conc - baseline))],
                          render_mode='webg1',
                          )

        # СОХРАНИТЬ данные по графику
        self._remeber_graph_data(lam, p, method, (x[100:-100], da_conc, baseline, da_conc - baseline + abs(np.min(da_conc - baseline))))


        if with_stimuli:
            # отрисовка стимулов
            # (код для их чтения снизу)
            for xc in self.stimuli_times:
                # ЕЩЁ НАДО ПРИБАВИТЬ 100 СТО ПЕРВЫХ ТОЧЕК (+ т.к. начало сдвинулось вправо считай)
                # А шаг между точками 100мс
                # stimuli_times -- не время, а номер стимула!
                try:
                    stimulus_time = x[xc-100]          # УБРАТЬ КОНСТАНТЫ; берём xc-100 стимул и помечаем
                                                       # и переводим в минуты
                                                       # НОМЕРА СТИМУЛОВ ВРОДЕ КАК ПРИВЯЗАНЫ К НОМЕРАМ ПИКОВ ДОФАМИНА
                except:
                    print(f'Стимул с номером {xc} не был нарисован')
                    continue
                fig.add_vline(x = stimulus_time,
                            line_width = 0.5,
                            opacity = 1,
                            line_dash = "dash",
                            line_color = "red")

        try:
            rename = {'wide_variable_0': 'Conc', 'wide_variable_1': 'Baseline'}
            for line in fig.data:
                line.name = rename.get(line.name, line.name)
        except:
            pass

        fig.update_layout(
            title=dict(text=f'Dopamine data for {file_name}',   # !!!!!!!
                    font=dict(size=20),
                    x=0.5,
                    xanchor='center'),
            xaxis_title="Time (min)",
            yaxis_title="DA conc (a.u.)"
            )

        fig.update_xaxes(
            rangeslider_visible = True,
            )

        fig.update_yaxes(
            autorange = True,
            fixedrange = False
        )

        fig.show()


    def draw_some_peaks(self):
        '''
            Нарисовать картинку рандомных пиков
        '''
        rand_time = random.choice(list(self.first_peaks.keys()))
        n_points = len(self.first_peaks[rand_time])
        xpoints = range(rand_time, rand_time + n_points)
        ypoints1 = self.first_peaks[rand_time]
        ypoints2 = self.second_peaks[rand_time]

        fig = px.line(y = [ypoints1, ypoints2],
                     width = 1000,
                     height = 800)

        fig.update_layout(
            title=dict(text=f'Peaks for time point = {rand_time//1000} s',
                    font=dict(size=20),
                    x=0.5,
                    xanchor='center'),
            xaxis_title="a.u.",
            yaxis_title="a.u."
        )

        try:
            rename = {'wide_variable_0': 'First Peak', 'wide_variable_1': 'Second Peak'}
            for line in fig.data:
                line.name = rename.get(line.name, line.name)
        except:
            pass

        # https://plotly.com/python/v3/insets/ -- так можно попробовать сделать inset zoom

        fig.show()
