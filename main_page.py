from flask import Flask, flash, request, redirect, render_template, session
from werkzeug.utils import secure_filename
from dopamineAnalysis import DopamineData
from parseFile import readDAdata
import os
from plotly import utils
from json import dumps


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.route("/", methods=["GET", "POST"])
@app.route("/submit", methods=["GET", "POST"])
def submit():
    information = None
    #     information = request.form

    if request.method == 'GET':
        return render_template("index.html", data=information)
    else:
        # If button pressed without file selection
        if 'daFile' not in request.files:
            flash('No file part')
            return redirect(request.url)
            return render_template("index.html", data=information)
        # If there was a file selection, but no file selected
        if not request.files['daFile']:
            flash('No file selected')
            return redirect(request.url)
            return render_template("index.html", data=information)



        # https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
        # ВОзможно имеет смысл добавить secure filenames если выкладывать на сервер
        f = request.files['daFile']
        try:
            flash(f'Trying to open file {f.filename}')
            dopamineData = readDAdata(f)
        except Exception as error:
            flash(f'Exception occured: {error}')
        else:
            flash('File opened successfully')

        fig = dopamineData.test_baseline_correction(lam=10**9, 
                                                    p=0.01, 
                                                    with_stimuli=True, 
                                                    corrected_only=False, 
                                                    method='diff')
        flash('Graph created')

        fig_to_json = dumps(fig, cls=utils.PlotlyJSONEncoder)


        # добавить прогресс бар на рендер картинки https://jquery.com/

        # return redirect(request.url)
        return render_template("graph.html", pub_lines_JSON=all_pub_json)

    return redirect(request.url)
    return render_template("index.html", data=information)

    
if __name__ == "__main__":
    app.run(debug = True)



# Вывести интерактивный график
# https://stackoverflow.com/questions/63616028/how-to-integrate-plotly-express-chart-to-flask-app

# Сессии могут быть полезны для сохранения предыдущих и их быстрого вывода
# https://www.techwithtim.net/tutorials/flask/sessions
